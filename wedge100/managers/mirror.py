"""
wedge100/managers/mirror.py
----------------------------
포트 미러링 (SPAN: Switched Port ANalyzer) 관리자.

BCM Tomahawk SOC 커맨드:
  mirror add <dest_port> pbmp=<src_port> ing=1 egr=1
  mirror delete <dest_port>
  mirror show

포트 미러링이란?
  특정 포트의 트래픽을 다른 포트(캡처 장비)로 복사.
  패킷 캡처(Wireshark 등) 또는 IDS/IPS 연동에 사용.

주의사항:
  - 미러링 목적지 포트는 일반 트래픽 전달 불가 (전용)
  - BCM Tomahawk: 동시에 최대 4개 미러 세션 지원
  - Ingress / Egress / Both 방향 선택 가능
"""

import logging
from dataclasses import dataclass
from typing import Optional

from wedge100.config import FP_TO_CE, validate_fp_port
from wedge100.bcm.sdk import BCMSdk

log = logging.getLogger(__name__)

MAX_SESSIONS = 4


@dataclass
class MirrorSession:
    session_id: int
    name: str
    src_port: int        # Front Panel 번호
    dst_port: int        # Front Panel 번호
    direction: str       # "ingress" | "egress" | "both"
    active: bool = True

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "name":       self.name,
            "src_port":   self.src_port,
            "dst_port":   self.dst_port,
            "direction":  self.direction,
            "active":     self.active,
        }


class MirrorManager:
    """포트 미러링 관리자."""

    def __init__(self):
        self._sessions: dict[int, MirrorSession] = {}
        self._next_id = 1

    def create(
        self,
        src_port: int,
        dst_port: int,
        direction: str = "both",
        name: str = "",
    ) -> MirrorSession:
        """
        미러링 세션을 생성한다.

        Args:
            src_port:  트래픽 원본 포트 (Front Panel 번호)
            dst_port:  캡처 목적지 포트 (Front Panel 번호)
            direction: "ingress" | "egress" | "both"
            name:      세션 이름 (선택)
        """
        validate_fp_port(src_port)
        validate_fp_port(dst_port)

        if src_port == dst_port:
            raise ValueError("원본 포트와 목적지 포트가 같을 수 없습니다.")
        if direction not in ("ingress", "egress", "both"):
            raise ValueError(f"방향 오류: {direction}")
        if len(self._sessions) >= MAX_SESSIONS:
            raise ValueError(f"최대 미러 세션 수({MAX_SESSIONS})에 도달했습니다.")

        src_ce = FP_TO_CE[src_port]
        dst_ce = FP_TO_CE[dst_port]

        ing = 1 if direction in ("ingress", "both") else 0
        egr = 1 if direction in ("egress",  "both") else 0

        with BCMSdk() as sdk:
            # 목적지 포트를 미러 목적지로 설정
            sdk.cmd(f"port ce{dst_ce} enable=true")
            # 미러 세션 생성
            sdk.cmd(
                f"mirror add ce{dst_ce} pbmp=ce{src_ce} "
                f"ing={ing} egr={egr}"
            )

        session = MirrorSession(
            session_id=self._next_id,
            name=name or f"mirror-{self._next_id}",
            src_port=src_port,
            dst_port=dst_port,
            direction=direction,
        )
        self._sessions[self._next_id] = session
        self._next_id += 1

        log.info(
            "미러 세션 생성: %s (포트%d→포트%d, %s)",
            session.name, src_port, dst_port, direction,
        )
        return session

    def delete(self, session_id: int) -> None:
        """미러링 세션을 삭제한다."""
        if session_id not in self._sessions:
            raise KeyError(f"세션 ID {session_id}가 존재하지 않습니다.")

        session = self._sessions[session_id]
        dst_ce = FP_TO_CE[session.dst_port]

        with BCMSdk() as sdk:
            sdk.cmd(f"mirror delete ce{dst_ce}")

        del self._sessions[session_id]
        log.info("미러 세션 %d 삭제: %s", session_id, session.name)

    def show(self, session_id: Optional[int] = None) -> list[MirrorSession]:
        """세션 목록 반환. session_id=None이면 전체."""
        if session_id is not None:
            if session_id not in self._sessions:
                raise KeyError(f"세션 ID {session_id}가 없습니다.")
            return [self._sessions[session_id]]
        return list(self._sessions.values())

    def show_hardware(self) -> str:
        """ASIC에서 직접 미러 상태 조회 (SOC mirror show)."""
        with BCMSdk() as sdk:
            return sdk.cmd("mirror show")
