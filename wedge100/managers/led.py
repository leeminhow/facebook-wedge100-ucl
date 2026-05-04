"""
wedge100/managers/led.py
-------------------------
QSFP 포트 LED 제어 관리자.

zip 안의 .soc 파일들을 그대로 활용:
  - 12_bits_LED_GREEN.soc   전체 포트 초록
  - 12_bits_LED_BLUE.soc    전체 파랑
  - 12_bits_LED_RED.soc     전체 빨강
  - 12_bits_LED_YELLOW.soc  전체 노랑
  - 12_bits_LED_PURPLE.soc  전체 보라
  - 12_bits_LED_AQUA.soc    전체 청록
  - 12_bits_LED_OFF.soc     전체 소등
  - led_port.soc / 12_bits_LED_port_integrator.soc  포트별 제어

포트별 LED 제어:
  BCM Tomahawk LED 마이크로컨트롤러(μC)는 SOC의 LED 데이터 RAM을
  통해 각 포트의 색상을 독립 제어할 수 있다.
  구체적인 비트 레이아웃은 ASIC LED µC 코드에 따르며,
  'ledup' / 'led' SOC 커맨드로 RAM을 직접 조작한다.
"""

import logging
import os
from typing import Optional

from wedge100.config import (
    FP_TO_CE, LED_SOC_FILES, SPEED_LED_COLOR, BIN_DIR,
    validate_fp_port,
)
from wedge100.bcm.sdk import BCMSdk, run_soc_file

logger = logging.getLogger(__name__)

# LED RAM 주소 상수 (12-bit 모드, Wedge100 12_bits_LED 시리즈 기반)
# 각 포트는 3바이트(12비트 × 2 색상채널 + 패딩) 할당
# 정확한 오프셋은 led_port.soc 참조
_LED_RAM_BASE = 0x00
_BYTES_PER_PORT = 3

# 색상 비트 패턴 (R/G/B 인코딩, ASIC LED µC 코드 기반)
_COLOR_BITS = {
    "off":    (0x00, 0x00),  # (high_byte, low_byte)
    "green":  (0x02, 0x00),
    "blue":   (0x00, 0x02),
    "red":    (0x04, 0x00),
    "yellow": (0x06, 0x00),  # Red + Green
    "purple": (0x04, 0x02),  # Red + Blue
    "aqua":   (0x02, 0x02),  # Green + Blue
    "white":  (0x06, 0x02),  # All
}


class LEDManager:
    """Wedge 100 LED 제어 관리자."""

    def __init__(self):
        self._current_colors: dict[int, str] = {}  # fp_port → color

    # ─── 전체 포트 LED ────────────────────────────────────────────────────────

    def set_all(self, color: str) -> None:
        """
        전체 포트 LED 색상을 일괄 설정한다.

        Args:
            color: "green" | "blue" | "red" | "yellow" | "purple" | "aqua" | "off"
        """
        color = color.lower()
        if color not in LED_SOC_FILES:
            raise ValueError(
                f"지원하지 않는 색상: '{color}'. "
                f"가능: {list(LED_SOC_FILES.keys())}"
            )

        soc_path = LED_SOC_FILES[color]
        if not os.path.isfile(soc_path):
            raise FileNotFoundError(
                f"LED SOC 파일을 찾을 수 없음: {soc_path}\n"
                f"accton bin 경로가 올바른지 확인하세요."
            )

        run_soc_file(soc_path)
        for fp in FP_TO_CE:
            self._current_colors[fp] = color
        logger.info("전체 LED → %s", color)

    def set_off(self) -> None:
        """전체 LED 소등."""
        self.set_all("off")

    # ─── 포트별 LED ───────────────────────────────────────────────────────────

    def set_port(self, fp_port: int, color: str) -> None:
        """
        특정 포트의 LED 색상을 설정한다.

        Broadcom LED µC RAM을 직접 쓰는 방식을 사용한다.
        ledup 커맨드: ledup write <offset> <value>

        Args:
            fp_port: Front Panel 포트 번호 (1-32)
            color: "green" | "blue" | "red" | ... | "off"
        """
        validate_fp_port(fp_port)
        color = color.lower()
        if color not in _COLOR_BITS:
            raise ValueError(f"지원하지 않는 색상: '{color}'")

        ce_idx = FP_TO_CE[fp_port]
        offset = _LED_RAM_BASE + ce_idx * _BYTES_PER_PORT
        hi, lo = _COLOR_BITS[color]

        cmds = [
            f"ledup write {offset} {hi:#04x}",
            f"ledup write {offset + 1} {lo:#04x}",
        ]
        with BCMSdk() as sdk:
            for cmd in cmds:
                sdk.cmd(cmd)

        self._current_colors[fp_port] = color
        logger.info("포트 %d LED → %s", fp_port, color)

    def set_ports(self, fp_ports: list[int], color: str) -> None:
        """여러 포트를 동일한 색상으로 설정한다."""
        color = color.lower()
        if color not in _COLOR_BITS:
            raise ValueError(f"지원하지 않는 색상: '{color}'")

        ce_offsets = []
        for fp in fp_ports:
            validate_fp_port(fp)
            ce_idx = FP_TO_CE[fp]
            offset = _LED_RAM_BASE + ce_idx * _BYTES_PER_PORT
            ce_offsets.append((fp, offset))

        hi, lo = _COLOR_BITS[color]
        with BCMSdk() as sdk:
            for fp, offset in ce_offsets:
                sdk.cmd(f"ledup write {offset} {hi:#04x}")
                sdk.cmd(f"ledup write {offset + 1} {lo:#04x}")
                self._current_colors[fp] = color

        logger.info("%d개 포트 LED → %s", len(fp_ports), color)

    # ─── 속도 자동 매핑 ──────────────────────────────────────────────────────

    def apply_speed_mode(self, port_statuses: list) -> None:
        """
        포트 링크 속도에 따라 LED 색상을 자동 설정한다.
          100G → green
          50G  → aqua
          40G  → blue
          25G  → yellow
          10G  → purple
          down → off

        Args:
            port_statuses: PortStatus 객체 리스트 (PortManager.get_status() 결과)
        """
        # 포트별 색상 수집
        port_color_map: dict[str, list[int]] = {}
        for ps in port_statuses:
            if not ps.fp_port:
                continue
            if not ps.link:
                color = SPEED_LED_COLOR["down"]
            else:
                color = SPEED_LED_COLOR.get(ps.speed or "", "off")
            port_color_map.setdefault(color, []).append(ps.fp_port)

        # 색상별 일괄 처리 (소켓 연결 최소화)
        for color, ports in port_color_map.items():
            try:
                self.set_ports(ports, color)
            except Exception as e:
                logger.warning("speed-mode LED 설정 실패 (color=%s): %s", color, e)

        logger.info("speed-mode LED 적용 완료")

    # ─── 상태 조회 ────────────────────────────────────────────────────────────

    def get_status(self) -> dict[int, str]:
        """현재 기록된 LED 색상 상태를 반환한다 (소프트웨어 상태)."""
        return dict(self._current_colors)

    def get_port_color(self, fp_port: int) -> str:
        """특정 포트의 현재 LED 색상을 반환한다."""
        validate_fp_port(fp_port)
        return self._current_colors.get(fp_port, "unknown")
