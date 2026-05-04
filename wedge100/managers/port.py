"""
wedge100/managers/port.py
--------------------------
QSFP 포트 설정 / 상태 관리자.

주요 기능:
  - 포트 속도 설정 (100G / 40G / 50G / 25G / 10G)
  - Breakout 모드 (4x25G, 2x50G, 1x100G, 4x10G)
  - 포트 enable / disable
  - 포트 상태 조회 (링크 up/down, 속도, FEC)
  - TX/RX 카운터 조회 및 초기화
  - FEC (RS-FEC CL91) 설정

ps 출력 파싱 예시 (BCM Tomahawk):
  ce0     up   100G  FD   NONE  NONE  NONE NONE  NONE  NONE  10
  ce1     down   -   -    -     -     -    -     -     -      0
"""

import re
import logging
from typing import Optional

from wedge100.config import (
    FP_TO_CE, CE_TO_FP, ALL_FP_PORTS,
    SPEED_MAP, BREAKOUT_MAP, validate_fp_port,
)
from wedge100.bcm.sdk import BCMSdk
from wedge100.bcm import soc_commands as soc

logger = logging.getLogger(__name__)


class PortStatus:
    """단일 포트 상태 데이터 클래스."""

    def __init__(
        self,
        fp_port: int,
        ce_idx: int,
        link: bool,
        speed: Optional[str],
        duplex: Optional[str],
        fec: Optional[str],
        lanes: int,
    ):
        self.fp_port = fp_port
        self.ce_idx = ce_idx
        self.ce_name = f"ce{ce_idx}"
        self.link = link
        self.speed = speed
        self.duplex = duplex
        self.fec = fec
        self.lanes = lanes

    def __repr__(self) -> str:
        state = "UP" if self.link else "DOWN"
        spd = self.speed or "-"
        return f"<Port fp={self.fp_port} ce={self.ce_name} {state} {spd}>"

    def to_dict(self) -> dict:
        return {
            "port": self.fp_port,
            "ce": self.ce_name,
            "link": self.link,
            "speed": self.speed,
            "duplex": self.duplex,
            "fec": self.fec,
            "lanes": self.lanes,
        }


class PortManager:
    """Wedge 100 포트 관리자."""

    # ─── 속도 설정 ────────────────────────────────────────────────────────────

    def set_speed(self, fp_port: int, speed_str: str) -> None:
        """
        포트 속도를 설정한다.

        Args:
            fp_port: Front Panel 포트 번호 (1-32)
            speed_str: "100G" | "40G" | "50G" | "25G" | "10G"
        """
        validate_fp_port(fp_port)
        if speed_str not in SPEED_MAP:
            raise ValueError(f"지원하지 않는 속도: {speed_str}. 가능: {list(SPEED_MAP.keys())}")

        ce_idx = FP_TO_CE[fp_port]
        cmds = soc.port_speed(ce_idx, speed_str)

        with BCMSdk() as sdk:
            for cmd in cmds:
                sdk.cmd(cmd)
        logger.info("포트 %d (ce%d) 속도 설정: %s", fp_port, ce_idx, speed_str)

    # ─── Breakout ─────────────────────────────────────────────────────────────

    def set_breakout(self, fp_port: int, mode: str) -> None:
        """
        포트 Breakout 모드를 설정한다.

        Args:
            fp_port: Front Panel 포트 번호 (1-32)
            mode: "1x100G" | "2x50G" | "4x25G" | "4x10G" | "1x40G"

        주의:
            Breakout 시 인접 CE 채널이 영향받을 수 있다.
            Tomahawk 구조상 QSFP 한 포트 = 4 SerDes 레인 = ce_base 한 개 (4레인 묶음).
            4x25G/4x10G 분할 시 ce_base 하나가 4개의 1레인 논리포트로 나뉜다.
        """
        validate_fp_port(fp_port)
        if mode not in BREAKOUT_MAP:
            raise ValueError(f"지원하지 않는 모드: {mode}. 가능: {list(BREAKOUT_MAP.keys())}")

        ce_idx = FP_TO_CE[fp_port]
        cmds = soc.port_breakout(ce_idx, mode)

        with BCMSdk() as sdk:
            for cmd in cmds:
                sdk.cmd(cmd)
        logger.info("포트 %d (ce%d) breakout: %s", fp_port, ce_idx, mode)

    # ─── Enable / Disable ─────────────────────────────────────────────────────

    def set_enable(self, fp_port: int, enable: bool = True) -> None:
        """포트를 활성화 또는 비활성화한다."""
        validate_fp_port(fp_port)
        ce_idx = FP_TO_CE[fp_port]
        with BCMSdk() as sdk:
            sdk.cmd(soc.port_enable(ce_idx, enable))
        state = "활성화" if enable else "비활성화"
        logger.info("포트 %d (ce%d) %s", fp_port, ce_idx, state)

    def enable(self, fp_port: int) -> None:
        self.set_enable(fp_port, True)

    def disable(self, fp_port: int) -> None:
        self.set_enable(fp_port, False)

    # ─── FEC ──────────────────────────────────────────────────────────────────

    def set_fec(self, fp_port: int, enable: bool = True) -> None:
        """RS-FEC (CL91) 설정."""
        validate_fp_port(fp_port)
        ce_idx = FP_TO_CE[fp_port]
        cmds = soc.fec_enable(ce_idx, enable)
        with BCMSdk() as sdk:
            for cmd in cmds:
                sdk.cmd(cmd)
        state = "ON" if enable else "OFF"
        logger.info("포트 %d FEC %s", fp_port, state)

    # ─── 상태 조회 ────────────────────────────────────────────────────────────

    def get_status(self, fp_port: Optional[int] = None) -> list[PortStatus]:
        """
        포트 상태를 조회한다.

        Args:
            fp_port: None이면 전체 포트 조회
        Returns:
            PortStatus 리스트
        """
        if fp_port is not None:
            validate_fp_port(fp_port)
            ce_idx = FP_TO_CE[fp_port]
        else:
            ce_idx = None

        with BCMSdk() as sdk:
            raw = sdk.cmd(soc.port_status(ce_idx))

        return self._parse_ps_output(raw)

    def get_counters(self, fp_port: int) -> dict:
        """포트 TX/RX 카운터를 조회한다."""
        validate_fp_port(fp_port)
        ce_idx = FP_TO_CE[fp_port]
        cmds = soc.port_counters(ce_idx)
        with BCMSdk() as sdk:
            raw = sdk.cmd(cmds[0])
        return self._parse_counters(raw, fp_port)

    def clear_counters(self, fp_port: Optional[int] = None) -> None:
        """포트 카운터를 초기화한다."""
        ce_idx = FP_TO_CE[fp_port] if fp_port else None
        with BCMSdk() as sdk:
            sdk.cmd(soc.port_clear_counters(ce_idx))

    # ─── 출력 파싱 ────────────────────────────────────────────────────────────

    def _parse_ps_output(self, raw: str) -> list[PortStatus]:
        """
        BCM 'ps ce' 출력을 파싱한다.

        예시 줄:
          ce0     up   100G  FD   NONE  NONE  NONE NONE  NONE  NONE  10
          ce1     down   -   -    -     -     -    -     -     -      0
        """
        results = []
        # ce 로 시작하는 줄만 파싱
        pattern = re.compile(
            r"^(ce\d+)\s+(up|down)\s+(\S+)\s+(\S+)",
            re.MULTILINE | re.IGNORECASE,
        )
        for m in pattern.finditer(raw):
            ce_name, link_str, speed_raw, duplex = m.groups()
            ce_idx = int(ce_name.replace("ce", ""))

            # 속도 정규화: "100G" → "100G", "-" → None
            speed = None if speed_raw == "-" else speed_raw.upper()
            if speed and not speed.endswith("G"):
                # 숫자만 있으면 Mbps → "100G" 변환
                try:
                    mbps = int(speed)
                    speed = f"{mbps // 1000}G" if mbps >= 1000 else f"{mbps}M"
                except ValueError:
                    pass

            fp_port = CE_TO_FP.get(ce_idx, 0)
            results.append(PortStatus(
                fp_port=fp_port,
                ce_idx=ce_idx,
                link=link_str.lower() == "up",
                speed=speed,
                duplex="FD" if duplex.upper() == "FD" else duplex,
                fec=None,   # 별도 조회 필요
                lanes=4,    # 기본값; breakout 시 변경
            ))

        # fp_port 기준 정렬
        results.sort(key=lambda s: s.fp_port or 99)
        return results

    def _parse_counters(self, raw: str, fp_port: int) -> dict:
        """카운터 출력 파싱."""
        counters = {
            "port": fp_port,
            "rx_packets": 0,
            "tx_packets": 0,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "rx_errors": 0,
            "tx_errors": 0,
            "rx_drops": 0,
        }
        # 패턴: "RX_UC_PKTS.ce0    :          12345"
        patterns = {
            "rx_packets": r"RX_UC_PKTS.*?:\s*(\d+)",
            "tx_packets": r"TX_UC_PKTS.*?:\s*(\d+)",
            "rx_bytes":   r"RX_BYTES.*?:\s*(\d+)",
            "tx_bytes":   r"TX_BYTES.*?:\s*(\d+)",
            "rx_errors":  r"RX_FCS_ERR.*?:\s*(\d+)",
        }
        for key, pat in patterns.items():
            m = re.search(pat, raw, re.IGNORECASE)
            if m:
                counters[key] = int(m.group(1))
        return counters
