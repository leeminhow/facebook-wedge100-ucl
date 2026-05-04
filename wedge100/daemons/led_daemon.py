#!/usr/bin/env python3
"""
wedge100/daemons/led_daemon.py
───────────────────────────────
LED 자동 제어 데몬.

기능:
  - 3초마다 전체 포트 링크 상태 폴링 (ps ce)
  - QSFP 존재 여부 / 속도에 따라 LED 자동 설정
  - 4-lane 포트별 독립 LED 제어
    · 1x100G:  포트당 1개 LED (4레인 묶음)
    · 2x50G:   포트당 2개 LED
    · 4x25G:   포트당 4개 LED (각 레인 독립)
  - DB의 blink 요청 확인 → LED 깜빡이기 (WebUI 포트 인디케이터)
  - DB에 현재 포트/트랜시버 상태 갱신 (WebUI 소비용)

LED 색상 정책:
  트랜시버 없음 / 링크 DOWN  → OFF
  100G UP                     → GREEN
  50G  UP                     → AQUA (청록)
  40G  UP                     → BLUE
  25G  UP                     → YELLOW
  10G  UP                     → PURPLE
  Admin DOWN                  → RED (잠깐 점등 후 OFF)

systemd 서비스: wedge100-led.service
"""

import logging
import os
import re
import signal
import subprocess
import sys
import time
import threading
from typing import Optional

import mysql.connector

sys.path.insert(0, "/usr/local/wedge100-nos")

from wedge100.config import (
    FP_TO_CE, CE_TO_FP, ALL_FP_PORTS,
    SPEED_LED_COLOR, BIN_DIR,
)
from wedge100.bcm.sdk import BCMSdk, BCMError

# ── 설정 ────────────────────────────────────────────────────────────
POLL_INTERVAL   = 3      # 포트 상태 폴링 주기 (초)
BLINK_ON_MS     = 300    # 깜빡이기 ON 시간 (ms)
BLINK_OFF_MS    = 300    # 깜빡이기 OFF 시간 (ms)
COUNTER_INTERVAL = 300   # 카운터 히스토리 저장 주기 (초)

DB_CONFIG = {
    "host":     "localhost",
    "user":     "wedge100",
    "password": "wedge100nos!",
    "database": "wedge100nos",
}

# LED RAM 레이아웃 (Broadcom Tomahawk 12-bit LED µC)
# 각 CE 포트는 3바이트 할당. ce0=offset 0, ce1=offset 3, ...
# sub-lane은 해당 CE offset에서 lane 비트를 분리하여 제어.
_LED_BASE   = 0x00
_BYTES_PER  = 3

_COLOR_BITS: dict[str, tuple[int, int]] = {
    "off":    (0x00, 0x00),
    "green":  (0x02, 0x00),
    "blue":   (0x00, 0x02),
    "red":    (0x04, 0x00),
    "yellow": (0x06, 0x00),
    "purple": (0x04, 0x02),
    "aqua":   (0x02, 0x02),
    "white":  (0x06, 0x02),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LED] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("/var/log/wedge100-led.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("led_daemon")


# ── DB 헬퍼 ─────────────────────────────────────────────────────────

class DB:
    def __init__(self):
        self._conn = None

    def connect(self):
        self._conn = mysql.connector.connect(**DB_CONFIG)
        self._conn.autocommit = True

    def execute(self, sql: str, params=None):
        try:
            cur = self._conn.cursor(dictionary=True)
            cur.execute(sql, params or ())
            return cur
        except mysql.connector.errors.OperationalError:
            self.connect()
            cur = self._conn.cursor(dictionary=True)
            cur.execute(sql, params or ())
            return cur

    def fetchall(self, sql: str, params=None) -> list:
        return self.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params=None) -> Optional[dict]:
        return self.execute(sql, params).fetchone()


# ── LED 제어 ─────────────────────────────────────────────────────────

class LEDController:
    """BCM SDK ledup 커맨드로 포트별 레인 LED 제어."""

    # 현재 LED 상태 캐시 (불필요한 SOC 커맨드 방지)
    _cache: dict[tuple[int, int], str] = {}  # (ce_idx, lane) → color

    def set(self, sdk: BCMSdk, ce_idx: int, lane: int, color: str) -> bool:
        """
        특정 CE 포트의 레인 LED 색상 설정.

        Args:
            ce_idx: CE 채널 인덱스 (0-31)
            lane:   레인 번호 (0-3)
            color:  색상 문자열
        """
        if self._cache.get((ce_idx, lane)) == color:
            return False  # 변화 없음

        offset = _LED_BASE + ce_idx * _BYTES_PER
        # 레인별 오프셋 보정 (서브레인은 CE 오프셋 + lane)
        # Tomahawk LED µC에서 sub-lane 처리:
        # 1x100G: offset → 포트 전체 (lane 무시)
        # 4x25G:  ce_idx + lane → 별도 논리 포트이므로 ce_idx 자체가 다름
        # 따라서 lane은 breakout 시에만 의미있고, ce_idx는 이미 서브포트 번호
        hi, lo = _COLOR_BITS.get(color, (0x00, 0x00))
        try:
            sdk.cmd(f"ledup write {offset} {hi:#04x}")
            sdk.cmd(f"ledup write {offset + 1} {lo:#04x}")
            self._cache[(ce_idx, lane)] = color
            return True
        except BCMError as e:
            log.warning("LED 설정 실패 ce%d lane%d: %s", ce_idx, lane, e)
            return False

    def set_all_off(self, sdk: BCMSdk):
        """모든 LED 소등."""
        soc_path = f"{BIN_DIR}/12_bits_LED_OFF.soc"
        if os.path.isfile(soc_path):
            sdk.load_soc_file(soc_path)
            self._cache.clear()


# ── 포트 상태 파서 ───────────────────────────────────────────────────

def parse_ps_output(raw: str) -> dict[int, dict]:
    """
    'ps ce' 출력을 파싱한다.
    반환: {ce_idx: {link, speed, duplex}}
    """
    result = {}
    pattern = re.compile(
        r"^(ce\d+)\s+(up|down)\s+(\S+)\s+(\S+)",
        re.MULTILINE | re.IGNORECASE,
    )
    for m in pattern.finditer(raw):
        ce_name, link_str, speed_raw, duplex = m.groups()
        ce_idx = int(ce_name.replace("ce", ""))
        speed = None if speed_raw == "-" else speed_raw.upper()
        if speed:
            # "100000" → "100G" 변환
            try:
                mbps = int(speed.replace("G","000").replace("M",""))
                if speed.isdigit():
                    speed = f"{int(speed)//1000}G"
            except ValueError:
                pass
        result[ce_idx] = {
            "link":   link_str.lower() == "up",
            "speed":  speed,
            "duplex": duplex,
        }
    return result


# ── 트랜시버 존재 확인 ────────────────────────────────────────────────

def check_transceiver_present(fp_port: int) -> tuple[bool, dict]:
    """
    QSFP EEPROM 읽기로 트랜시버 존재 여부 확인.
    반환: (present, info_dict)
    """
    eeprom_bin = f"{BIN_DIR}/wedge100_qsfp_eeprom"
    if not os.path.isfile(eeprom_bin):
        # 바이너리 없으면 sysfs로 폴백
        return _check_transceiver_sysfs(fp_port)

    try:
        result = subprocess.run(
            [eeprom_bin, str(fp_port)],
            timeout=2, capture_output=True, text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False, {}
        info = _parse_qsfp_output(result.stdout)
        return True, info
    except Exception:
        return False, {}


def _check_transceiver_sysfs(fp_port: int) -> tuple[bool, dict]:
    """sysfs EEPROM 파일로 트랜시버 존재 확인."""
    # Wedge100 QSFP I2C 버스 매핑 (추정: 포트 1 → i2c-2, 포트 32 → i2c-33)
    bus = fp_port + 1
    eeprom_path = f"/sys/bus/i2c/devices/{bus}-0050/eeprom"
    try:
        with open(eeprom_path, "rb") as f:
            data = f.read(16)
        if len(data) < 8 or all(b == 0 or b == 0xFF for b in data):
            return False, {}
        # SFF-8636 바이트 0: identifier
        id_byte = data[0]
        connector = {0x0C: "QSFP+", 0x11: "QSFP28", 0x0D: "QSFP28"}.get(id_byte, "QSFP")
        return True, {"connector_type": connector}
    except (OSError, IOError):
        return False, {}


def _parse_qsfp_output(raw: str) -> dict:
    """wedge100_qsfp_eeprom 출력 파싱."""
    info = {}
    patterns = {
        "vendor":         r"Vendor\s*Name\s*:\s*(.+)",
        "part_number":    r"Part\s*Number\s*:\s*(.+)",
        "serial":         r"Serial\s*Number\s*:\s*(.+)",
        "connector_type": r"Connector\s*Type\s*:\s*(.+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, raw, re.IGNORECASE)
        if m:
            info[key] = m.group(1).strip()
    for key, pat in [
        ("temp_celsius", r"Temperature\s*:\s*([\-\d.]+)"),
        ("tx_power_dbm", r"Tx\s*Power\s*:\s*([\-\d.]+)"),
        ("rx_power_dbm", r"Rx\s*Power\s*:\s*([\-\d.]+)"),
    ]:
        m = re.search(pat, raw, re.IGNORECASE)
        if m:
            info[key] = float(m.group(1))
    return info


# ── 메인 데몬 ────────────────────────────────────────────────────────

class LEDDaemon:
    def __init__(self):
        self.db  = DB()
        self.led = LEDController()
        self._running = True
        self._blink_ports: dict[int, float] = {}  # port_id → expire_time
        self._blink_state: dict[int, bool]  = {}  # port_id → on/off
        self._last_counter_save = 0.0

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT,  self._handle_signal)

    def _handle_signal(self, *_):
        log.info("종료 신호 수신")
        self._running = False

    # ── 메인 루프 ─────────────────────────────────────────────────

    def run(self):
        log.info("LED 데몬 시작")
        self.db.connect()

        # 시작 시 전체 LED 소등
        try:
            with BCMSdk() as sdk:
                self.led.set_all_off(sdk)
        except BCMError as e:
            log.warning("초기 LED OFF 실패: %s", e)

        # 깜빡이기 스레드
        blink_thread = threading.Thread(target=self._blink_loop, daemon=True)
        blink_thread.start()

        while self._running:
            try:
                self._poll_cycle()
            except BCMError as e:
                log.error("BCM 통신 오류: %s. 재시도 대기 10초.", e)
                time.sleep(10)
            except Exception as e:
                log.exception("예상치 못한 오류: %s", e)
                time.sleep(5)
            time.sleep(POLL_INTERVAL)

        log.info("LED 데몬 종료")

    # ── 한 번의 폴링 사이클 ───────────────────────────────────────

    def _poll_cycle(self):
        with BCMSdk() as sdk:
            raw = sdk.cmd("ps ce")
            port_states = parse_ps_output(raw)

            for fp_port in ALL_FP_PORTS:
                ce_idx = FP_TO_CE[fp_port]
                ps     = port_states.get(ce_idx, {})
                link   = ps.get("link", False)
                speed  = ps.get("speed")

                # 트랜시버 확인
                present, xcvr_info = check_transceiver_present(fp_port)

                # DB 업데이트 (포트 상태)
                self._update_port_state(fp_port, ce_idx, link, speed, present)

                # 트랜시버 DB 업데이트
                if present and xcvr_info:
                    self._update_transceiver(fp_port, xcvr_info)
                elif not present:
                    self._update_transceiver_absent(fp_port)

                # breakout 상태 확인
                breakout = self._get_breakout(fp_port)

                # LED 색상 결정 및 적용
                # (blink 중인 포트는 blink_loop가 담당)
                if fp_port not in self._blink_ports:
                    self._apply_led(sdk, fp_port, ce_idx, link, speed,
                                   present, breakout, port_states)

        # LLDP 이웃 갱신 (매 폴링마다)
        self._update_lldp()

        # 카운터 히스토리 저장 (COUNTER_INTERVAL 마다)
        now = time.time()
        if now - self._last_counter_save >= COUNTER_INTERVAL:
            self._save_counters()
            self._last_counter_save = now

    # ── LED 적용 ──────────────────────────────────────────────────

    def _apply_led(
        self, sdk: BCMSdk,
        fp_port: int, ce_idx: int,
        link: bool, speed: Optional[str],
        present: bool, breakout: str,
        all_states: dict,
    ):
        """
        포트 상태에 따라 LED 색상 결정 후 적용.

        breakout 모드별 레인 처리:
          1x100G  → ce_idx 1개 LED
          2x50G   → ce_idx, ce_idx+1 (2개)
          4x25G   → ce_idx, ce_idx+1, ce_idx+2, ce_idx+3 (4개)
        """
        num_lanes = {"1x100G": 1, "1x40G": 1, "2x50G": 2, "4x25G": 4, "4x10G": 4}.get(breakout, 1)

        for lane in range(num_lanes):
            sub_ce = ce_idx + lane if num_lanes > 1 else ce_idx
            sub_ps = all_states.get(sub_ce, {})
            sub_link  = sub_ps.get("link", False)
            sub_speed = sub_ps.get("speed")

            if not present:
                color = "off"
            elif not sub_link:
                color = "off"
            else:
                color = SPEED_LED_COLOR.get(sub_speed or "", "green")

            changed = self.led.set(sdk, sub_ce, lane, color)
            if changed:
                self._update_led_state_db(fp_port, lane, color)

    # ── 깜빡이기 루프 ────────────────────────────────────────────

    def _blink_loop(self):
        """별도 스레드에서 깜빡이기 요청 처리."""
        while self._running:
            # DB에서 blink 요청 확인
            try:
                rows = self.db.fetchall(
                    "SELECT port_id, blink_until FROM led_state "
                    "WHERE blink=1 AND lane=0"
                )
                now = time.time()

                # 새로운 blink 포트 등록
                current_blink = set()
                for row in rows:
                    pid = row["port_id"]
                    exp = row["blink_until"]
                    if exp and exp.timestamp() > now:
                        current_blink.add(pid)
                        if pid not in self._blink_ports:
                            self._blink_ports[pid] = exp.timestamp()
                            self._blink_state[pid] = True
                    else:
                        # 만료됨 → 해제
                        self.db.execute(
                            "UPDATE led_state SET blink=0, blink_until=NULL "
                            "WHERE port_id=%s", (pid,)
                        )

                # 만료된 blink 포트 제거
                expired = [p for p in self._blink_ports if p not in current_blink]
                for pid in expired:
                    del self._blink_ports[pid]
                    self._blink_state.pop(pid, None)
                    # 원래 상태로 복원 (다음 폴링 사이클에서 자동 처리)

                # 활성 blink 포트 LED 토글
                if self._blink_ports:
                    try:
                        with BCMSdk() as sdk:
                            for pid in list(self._blink_ports.keys()):
                                ce_idx = FP_TO_CE.get(pid)
                                if ce_idx is None:
                                    continue
                                on = self._blink_state.get(pid, True)
                                color = "white" if on else "off"
                                self.led.set(sdk, ce_idx, 0, color)
                                self._blink_state[pid] = not on
                    except BCMError:
                        pass

            except Exception as e:
                log.debug("blink 루프 오류: %s", e)

            # ON/OFF 주기에 따라 대기
            time.sleep(BLINK_ON_MS / 1000)

    # ── DB 업데이트 ───────────────────────────────────────────────

    def _update_port_state(
        self, fp_port, ce_idx, link, speed, xcvr_present
    ):
        self.db.execute(
            """INSERT INTO port_state (port_id, ce_name, link, speed)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 link=%s, speed=%s, updated_at=NOW()""",
            (fp_port, f"ce{ce_idx}", link, speed, link, speed),
        )

    def _update_transceiver(self, fp_port: int, info: dict):
        self.db.execute(
            """INSERT INTO transceiver
               (port_id, present, connector_type, vendor, part_number,
                serial, temp_celsius, tx_power_dbm, rx_power_dbm)
               VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 present=1,
                 connector_type=VALUES(connector_type),
                 vendor=VALUES(vendor),
                 part_number=VALUES(part_number),
                 serial=VALUES(serial),
                 temp_celsius=VALUES(temp_celsius),
                 tx_power_dbm=VALUES(tx_power_dbm),
                 rx_power_dbm=VALUES(rx_power_dbm),
                 updated_at=NOW()""",
            (
                fp_port,
                info.get("connector_type"),
                info.get("vendor"),
                info.get("part_number"),
                info.get("serial"),
                info.get("temp_celsius"),
                info.get("tx_power_dbm"),
                info.get("rx_power_dbm"),
            ),
        )

    def _update_transceiver_absent(self, fp_port: int):
        self.db.execute(
            "UPDATE transceiver SET present=0, updated_at=NOW() WHERE port_id=%s",
            (fp_port,),
        )

    def _update_led_state_db(self, fp_port: int, lane: int, color: str):
        self.db.execute(
            """INSERT INTO led_state (port_id, lane, color)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE color=%s, updated_at=NOW()""",
            (fp_port, lane, color, color),
        )

    def _get_breakout(self, fp_port: int) -> str:
        row = self.db.fetchone(
            "SELECT breakout FROM port_state WHERE port_id=%s", (fp_port,)
        )
        return row["breakout"] if row else "1x100G"

    # ── LLDP ─────────────────────────────────────────────────────

    def _update_lldp(self):
        """lldpcli 출력 파싱 후 DB 갱신."""
        try:
            result = subprocess.run(
                ["lldpcli", "show", "neighbors", "detail"],
                timeout=5, capture_output=True, text=True,
            )
            if result.returncode != 0:
                return
            neighbors = self._parse_lldp(result.stdout)
            for fp_port, nbr in neighbors.items():
                self.db.execute(
                    """INSERT INTO lldp_neighbor
                       (local_port, chassis_id, chassis_name, port_id, port_desc, system_desc, ttl)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE
                         chassis_id=VALUES(chassis_id),
                         chassis_name=VALUES(chassis_name),
                         port_id=VALUES(port_id),
                         port_desc=VALUES(port_desc),
                         system_desc=VALUES(system_desc),
                         ttl=VALUES(ttl),
                         updated_at=NOW()""",
                    (
                        fp_port,
                        nbr.get("chassis_id"),
                        nbr.get("chassis_name"),
                        nbr.get("port_id"),
                        nbr.get("port_desc"),
                        nbr.get("system_desc"),
                        nbr.get("ttl"),
                    ),
                )
        except FileNotFoundError:
            pass  # lldpcli 미설치
        except Exception as e:
            log.debug("LLDP 갱신 오류: %s", e)

    def _parse_lldp(self, raw: str) -> dict[int, dict]:
        """lldpcli show neighbors detail 출력 파싱."""
        neighbors = {}
        # 인터페이스별 블록 분리
        blocks = re.split(r"^Interface:\s+", raw, flags=re.MULTILINE)
        for block in blocks[1:]:
            lines = block.strip().splitlines()
            if not lines:
                continue
            iface_line = lines[0]  # "ce0, via: LLDP, RID: 1, Time: ..."
            ce_m = re.match(r"(ce\d+)", iface_line)
            if not ce_m:
                continue
            ce_name = ce_m.group(1)
            ce_idx = int(ce_name.replace("ce", ""))
            fp_port = CE_TO_FP.get(ce_idx, 0)
            if not fp_port:
                continue

            nbr = {}
            for line in lines:
                line = line.strip()
                if line.startswith("ChassisID:"):
                    nbr["chassis_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("SysName:"):
                    nbr["chassis_name"] = line.split(":", 1)[1].strip()
                elif line.startswith("PortID:"):
                    nbr["port_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("PortDescr:"):
                    nbr["port_desc"] = line.split(":", 1)[1].strip()
                elif line.startswith("SysDescr:"):
                    nbr["system_desc"] = line.split(":", 1)[1].strip()[:255]
                elif line.startswith("TTL:"):
                    try:
                        nbr["ttl"] = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
            neighbors[fp_port] = nbr
        return neighbors

    # ── 카운터 히스토리 ───────────────────────────────────────────

    def _save_counters(self):
        """포트 카운터를 DB에 저장."""
        from wedge100.managers.port import PortManager
        mgr = PortManager()
        for fp_port in ALL_FP_PORTS:
            try:
                c = mgr.get_counters(fp_port)
                self.db.execute(
                    """INSERT INTO counter_history
                       (port_id, rx_packets, tx_packets, rx_bytes, tx_bytes, rx_errors)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (
                        fp_port,
                        c["rx_packets"], c["tx_packets"],
                        c["rx_bytes"],   c["tx_bytes"],
                        c["rx_errors"],
                    ),
                )
            except Exception:
                pass


# ── 진입점 ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("오류: root 권한으로 실행하세요")
        sys.exit(1)
    LEDDaemon().run()
