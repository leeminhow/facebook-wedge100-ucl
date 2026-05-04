"""
wedge100/managers/hw.py
------------------------
하드웨어 상태 관리자 (FAN, PSU, 온도 센서, QSFP 존재 여부).

Wedge 100 하드웨어 접근 방식:
  - 온도: sysfs lm75 드라이버  /sys/bus/i2c/drivers/lm75/.../temp1_input
  - FAN: sysfs hwmon           /sys/class/hwmon/hwmon*/fan*_input
  - PSU: i2cget via subprocess (PSU I2C bus 7, mux 0x70)
  - QSFP 존재: wedge100_qsfp_eeprom 바이너리 또는 sysfs

온도 센서 위치 (bmc_device.py lm75 참조):
  Inlet(입구) 온도, Outlet(배출구) 온도 등 7개 lm75 센서
"""

import glob
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from wedge100.config import (
    FP_TO_CE, QSFP_EEPROM_BIN, BIN_DIR,
    PSU_I2C_BUS, PSU_MUX_ADDR,
)

logger = logging.getLogger(__name__)


# ─── 데이터 클래스 ────────────────────────────────────────────────────────────

@dataclass
class FanStatus:
    fan_id: int
    label: str
    rpm_front: int       # 전면 팬 RPM
    rpm_rear: int        # 후면 팬 RPM
    duty_pct: int        # PWM 듀티 사이클 (%)
    present: bool = True


@dataclass
class TemperatureReading:
    sensor_id: int
    label: str
    celsius: float
    warning_threshold: float = 70.0
    critical_threshold: float = 80.0

    @property
    def status(self) -> str:
        if self.celsius >= self.critical_threshold:
            return "CRITICAL"
        if self.celsius >= self.warning_threshold:
            return "WARNING"
        return "OK"


@dataclass
class PSUStatus:
    psu_id: int
    present: bool
    power_ok: bool
    input_voltage: Optional[float] = None
    output_voltage: Optional[float] = None
    input_current: Optional[float] = None
    output_current: Optional[float] = None


@dataclass
class QSFPInfo:
    fp_port: int
    present: bool
    vendor: str = ""
    part_number: str = ""
    serial: str = ""
    connector_type: str = ""   # "QSFP28", "QSFP+", "SFP+"
    wavelength: Optional[int] = None   # nm
    tx_power_dbm: Optional[float] = None
    rx_power_dbm: Optional[float] = None
    temperature: Optional[float] = None


# ─── 메인 클래스 ─────────────────────────────────────────────────────────────

class HWManager:
    """Wedge 100 하드웨어 상태 관리자."""

    WEDGE100_FAN_COUNT = 5
    WEDGE100_PSU_COUNT = 2

    # 온도 센서 레이블 (bmc_device.py 기반)
    TEMP_SENSOR_LABELS = [
        "Switch ASIC Near",
        "Switch ASIC Far",
        "Inlet Left",
        "Inlet Right",
        "Outlet Left",
        "Outlet Right",
        "CPU",
    ]

    # ─── 팬 ──────────────────────────────────────────────────────────────────

    def get_fan_status(self) -> list[FanStatus]:
        """모든 팬의 RPM 및 듀티 사이클을 반환한다."""
        fans = []

        # 방법 1: sysfs hwmon
        hwmon_fans = self._read_fan_sysfs()
        if hwmon_fans:
            return hwmon_fans

        # 방법 2: sensors 커맨드
        fans = self._read_fan_sensors_cmd()
        return fans

    def _read_fan_sysfs(self) -> list[FanStatus]:
        """sysfs hwmon에서 팬 RPM을 읽는다."""
        results = []
        fan_pattern = "/sys/class/hwmon/hwmon*/fan*_input"
        fan_files = sorted(glob.glob(fan_pattern))

        # 팬 파일을 2개씩 짝지어 (전면/후면)
        fan_id = 1
        for i in range(0, len(fan_files), 2):
            if fan_id > self.WEDGE100_FAN_COUNT:
                break
            try:
                rpm_front = int(self._read_sysfs(fan_files[i]))
                rpm_rear = int(self._read_sysfs(fan_files[i + 1])) if i + 1 < len(fan_files) else 0
            except (ValueError, IndexError, OSError):
                rpm_front = rpm_rear = 0

            # 듀티 사이클은 pwm 파일에서
            duty = self._read_fan_duty(fan_id)

            results.append(FanStatus(
                fan_id=fan_id,
                label=f"FAN{fan_id}",
                rpm_front=rpm_front,
                rpm_rear=rpm_rear,
                duty_pct=duty,
                present=(rpm_front > 0 or rpm_rear > 0),
            ))
            fan_id += 1
        return results

    def _read_fan_duty(self, fan_id: int) -> int:
        """팬 PWM 듀티 사이클을 읽는다 (0-100%)."""
        pwm_patterns = [
            f"/sys/class/hwmon/hwmon*/pwm{fan_id}",
            f"/sys/bus/i2c/devices/*/pwm{fan_id}",
        ]
        for pat in pwm_patterns:
            files = glob.glob(pat)
            if files:
                try:
                    raw = int(self._read_sysfs(files[0]))
                    return int(raw * 100 / 255)
                except (ValueError, OSError):
                    pass
        return 0

    def _read_fan_sensors_cmd(self) -> list[FanStatus]:
        """sensors 커맨드로 팬 정보를 읽는다 (sysfs 실패 시 폴백)."""
        try:
            out = subprocess.check_output(
                ["sensors", "-j"], timeout=5, stderr=subprocess.DEVNULL
            ).decode()
            data = json.loads(out)
        except Exception:
            # sensors가 없거나 실패하면 더미 반환
            return [
                FanStatus(i, f"FAN{i}", 0, 0, 0, False)
                for i in range(1, self.WEDGE100_FAN_COUNT + 1)
            ]

        fans = []
        fan_id = 1
        for chip, sensors in data.items():
            for key, vals in sensors.items():
                if "fan" in key.lower() and isinstance(vals, dict):
                    rpm = int(list(vals.values())[0]) if vals else 0
                    fans.append(FanStatus(fan_id, f"FAN{fan_id}", rpm, 0, 0, rpm > 0))
                    fan_id += 1
        return fans

    # ─── 온도 ─────────────────────────────────────────────────────────────────

    def get_temperatures(self) -> list[TemperatureReading]:
        """모든 온도 센서 값을 반환한다."""
        readings = []
        pattern = "/sys/bus/i2c/drivers/lm75/*/temp1_input"
        temp_files = sorted(glob.glob(pattern))

        # 보조 패턴
        if not temp_files:
            temp_files = sorted(glob.glob("/sys/bus/i2c/devices/*/temp1_input"))

        for idx, path in enumerate(temp_files):
            try:
                raw = int(self._read_sysfs(path))
                celsius = raw / 1000.0
            except (ValueError, OSError):
                celsius = 0.0

            label = (
                self.TEMP_SENSOR_LABELS[idx]
                if idx < len(self.TEMP_SENSOR_LABELS)
                else f"Sensor{idx + 1}"
            )
            readings.append(TemperatureReading(
                sensor_id=idx + 1,
                label=label,
                celsius=celsius,
            ))

        if not readings:
            # sensors 커맨드 폴백
            readings = self._read_temp_sensors_cmd()

        return readings

    def _read_temp_sensors_cmd(self) -> list[TemperatureReading]:
        """sensors 커맨드로 온도를 읽는다."""
        try:
            out = subprocess.check_output(
                ["sensors"], timeout=5, stderr=subprocess.DEVNULL
            ).decode()
        except Exception:
            return []

        results = []
        sensor_id = 1
        for line in out.splitlines():
            m = re.search(r"([\w\s]+):\s+[+\-]?([\d.]+)°C", line)
            if m:
                label, temp_str = m.groups()
                label = self.TEMP_SENSOR_LABELS[sensor_id - 1] if sensor_id <= len(self.TEMP_SENSOR_LABELS) else label.strip()
                results.append(TemperatureReading(sensor_id, label, float(temp_str)))
                sensor_id += 1
        return results

    # ─── PSU ──────────────────────────────────────────────────────────────────

    def get_psu_status(self) -> list[PSUStatus]:
        """PSU 상태를 반환한다."""
        results = []
        # PSU I2C 주소 (bmc_device.py 기반)
        # PSU1: bus7, mux 0x70 ch0, addr 0x59 (PMBus), 0x51 (EEPROM)
        # PSU2: bus7, mux 0x70 ch1, addr 0x5a (PMBus), 0x52 (EEPROM)
        psu_configs = [
            (1, PSU_I2C_BUS, PSU_MUX_ADDR, 0, 0x59),
            (2, PSU_I2C_BUS, PSU_MUX_ADDR, 1, 0x5a),
        ]

        for psu_id, bus, mux_addr, mux_ch, pmbus_addr in psu_configs:
            status = self._read_psu_pmbus(psu_id, bus, mux_addr, mux_ch, pmbus_addr)
            results.append(status)

        return results

    def _read_psu_pmbus(
        self, psu_id: int, bus: int, mux_addr: int, mux_ch: int, pmbus_addr: int
    ) -> PSUStatus:
        """PMBus를 통해 PSU 상태를 읽는다."""
        try:
            # MUX 채널 선택
            subprocess.run(
                ["i2cset", "-f", "-y", str(bus), f"0x{mux_addr:02x}", f"0x{1 << mux_ch:02x}"],
                timeout=2, capture_output=True
            )
            # Status byte 읽기 (PMBus STATUS_WORD = 0x79)
            result = subprocess.run(
                ["i2cget", "-f", "-y", str(bus), f"0x{pmbus_addr:02x}", "0x79", "w"],
                timeout=2, capture_output=True, text=True
            )
            present = result.returncode == 0
            power_ok = present  # STATUS_WORD 파싱 단순화

            return PSUStatus(psu_id=psu_id, present=present, power_ok=power_ok)
        except Exception:
            return PSUStatus(psu_id=psu_id, present=False, power_ok=False)

    # ─── QSFP ─────────────────────────────────────────────────────────────────

    def get_qsfp_info(self, fp_port: Optional[int] = None) -> list[QSFPInfo]:
        """QSFP 트랜시버 정보를 반환한다."""
        ports = [fp_port] if fp_port else list(range(1, 33))
        results = []

        for port in ports:
            info = self._read_qsfp_eeprom(port)
            results.append(info)

        return results

    def _read_qsfp_eeprom(self, fp_port: int) -> QSFPInfo:
        """wedge100_qsfp_eeprom 바이너리로 QSFP EEPROM을 읽는다."""
        if not os.path.isfile(QSFP_EEPROM_BIN):
            return QSFPInfo(fp_port=fp_port, present=False, vendor="[바이너리 없음]")

        try:
            result = subprocess.run(
                [QSFP_EEPROM_BIN, str(fp_port)],
                timeout=3, capture_output=True, text=True
            )
            if result.returncode != 0:
                return QSFPInfo(fp_port=fp_port, present=False)

            return self._parse_qsfp_output(fp_port, result.stdout)
        except Exception as e:
            logger.debug("QSFP %d 읽기 실패: %s", fp_port, e)
            return QSFPInfo(fp_port=fp_port, present=False)

    def _parse_qsfp_output(self, fp_port: int, raw: str) -> QSFPInfo:
        """wedge100_qsfp_eeprom 출력을 파싱한다."""
        info = QSFPInfo(fp_port=fp_port, present=True)

        patterns = {
            "vendor":       r"Vendor\s*Name\s*:\s*(.+)",
            "part_number":  r"Part\s*Number\s*:\s*(.+)",
            "serial":       r"Serial\s*Number\s*:\s*(.+)",
            "connector_type": r"Connector\s*Type\s*:\s*(.+)",
        }
        for attr, pat in patterns.items():
            m = re.search(pat, raw, re.IGNORECASE)
            if m:
                setattr(info, attr, m.group(1).strip())

        # DOM 데이터
        temp_m = re.search(r"Temperature\s*:\s*([\d.]+)", raw)
        if temp_m:
            info.temperature = float(temp_m.group(1))
        tx_m = re.search(r"Tx\s*Power\s*:\s*([\-\d.]+)", raw)
        if tx_m:
            info.tx_power_dbm = float(tx_m.group(1))
        rx_m = re.search(r"Rx\s*Power\s*:\s*([\-\d.]+)", raw)
        if rx_m:
            info.rx_power_dbm = float(rx_m.group(1))

        return info

    # ─── 시스템 종합 상태 ─────────────────────────────────────────────────────

    def get_system_health(self) -> dict:
        """시스템 전체 건강 상태 요약을 반환한다."""
        fans = self.get_fan_status()
        temps = self.get_temperatures()
        psus = self.get_psu_status()

        fan_ok = all(f.present for f in fans)
        temp_ok = all(t.status == "OK" for t in temps)
        psu_ok = any(p.power_ok for p in psus)
        overall = "OK" if (fan_ok and temp_ok and psu_ok) else "WARNING"

        return {
            "overall": overall,
            "fans_ok": fan_ok,
            "temperature_ok": temp_ok,
            "psu_ok": psu_ok,
            "fans": [{"id": f.fan_id, "rpm_front": f.rpm_front, "present": f.present} for f in fans],
            "temperatures": [{"label": t.label, "celsius": t.celsius, "status": t.status} for t in temps],
            "psus": [{"id": p.psu_id, "present": p.present, "power_ok": p.power_ok} for p in psus],
        }

    # ─── 내부 유틸 ────────────────────────────────────────────────────────────

    @staticmethod
    def _read_sysfs(path: str) -> str:
        with open(path) as f:
            return f.read().strip()
