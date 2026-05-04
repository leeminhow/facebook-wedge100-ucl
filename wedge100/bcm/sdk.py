"""
wedge100/bcm/sdk.py
-------------------
BCM SDK netserve TCP 소켓 래퍼.

Broadcom bcm.user + netserve 구조:
  1. 부팅 시 bcm.user가 ASIC 초기화 후 netserve를 통해 SOC 셸을 TCP로 노출
  2. 이 모듈은 해당 소켓에 연결하여 SOC 커맨드를 전송/수신
  3. netserve는 각 커맨드 실행 후 "BCM.0> " 프롬프트를 보냄

사용법:
    sdk = BCMSdk()
    with sdk:
        output = sdk.cmd("ps ce")      # 포트 상태 조회
        sdk.load_soc_file("/path/to/led.soc")
"""

import socket
import time
import logging
import os
from typing import Optional

from wedge100.config import (
    NETSERVE_HOST, NETSERVE_PORT,
    NETSERVE_PROMPT, NETSERVE_TIMEOUT, NETSERVE_RETRIES,
)

logger = logging.getLogger(__name__)


class BCMError(Exception):
    """BCM SDK 통신 오류."""
    pass


class BCMSdk:
    """
    BCM SDK netserve 소켓 클라이언트.
    컨텍스트 매니저(with 문)로 사용하는 것을 권장한다.
    """

    def __init__(
        self,
        host: str = NETSERVE_HOST,
        port: int = NETSERVE_PORT,
        timeout: float = NETSERVE_TIMEOUT,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._buf = ""

    # ─── 연결 관리 ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """netserve에 연결하고 초기 프롬프트를 수신한다."""
        for attempt in range(1, NETSERVE_RETRIES + 1):
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(self.timeout)
                self._sock.connect((self.host, self.port))
                # 초기 프롬프트 소비
                self._read_until_prompt()
                logger.debug("BCM SDK netserve 연결 완료 (%s:%d)", self.host, self.port)
                return
            except (socket.error, BCMError) as e:
                logger.warning("BCM netserve 연결 시도 %d/%d 실패: %s", attempt, NETSERVE_RETRIES, e)
                self._sock = None
                if attempt < NETSERVE_RETRIES:
                    time.sleep(1)
        raise BCMError(
            f"BCM netserve ({self.host}:{self.port}) 에 연결할 수 없습니다.\n"
            "bcm.user와 netserve가 실행 중인지 확인하세요."
        )

    def disconnect(self) -> None:
        """소켓 연결 종료."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
            self._buf = ""
            logger.debug("BCM SDK netserve 연결 해제")

    def __enter__(self) -> "BCMSdk":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.disconnect()

    # ─── 커맨드 실행 ──────────────────────────────────────────────────────────

    def cmd(self, command: str) -> str:
        """
        SOC 커맨드를 전송하고 응답 문자열을 반환한다.

        Args:
            command: SOC 셸 커맨드 (예: "ps ce", "port ce0 speed=100000")
        Returns:
            커맨드 실행 결과 문자열 (프롬프트 제외)
        Raises:
            BCMError: 소켓 연결 오류
        """
        if not self._sock:
            raise BCMError("BCM SDK에 연결되어 있지 않습니다. connect()를 먼저 호출하세요.")

        command = command.strip()
        if not command or command.startswith("#"):
            return ""  # 빈 줄 / 주석 무시

        logger.debug("SOC> %s", command)
        try:
            self._sock.sendall((command + "\n").encode("ascii", errors="replace"))
            response = self._read_until_prompt()
        except socket.timeout:
            raise BCMError(f"커맨드 타임아웃: '{command}'")
        except socket.error as e:
            raise BCMError(f"소켓 오류: {e}")

        # 에코된 커맨드 줄 제거
        lines = response.splitlines()
        if lines and command in lines[0]:
            lines = lines[1:]
        result = "\n".join(lines).strip()

        logger.debug("응답: %s", result[:200])
        return result

    def cmd_multi(self, commands: list[str]) -> dict[str, str]:
        """여러 커맨드를 순차 실행하고 {command: output} 딕셔너리를 반환한다."""
        results = {}
        for c in commands:
            results[c] = self.cmd(c)
        return results

    def load_soc_file(self, path: str) -> int:
        """
        .soc 파일을 읽어 각 줄을 순차적으로 SOC 커맨드로 전송한다.

        Returns:
            실행된 커맨드 수
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"SOC 파일을 찾을 수 없음: {path}")

        count = 0
        with open(path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.cmd(line)
                    count += 1
        logger.info("SOC 파일 실행 완료: %s (%d개 커맨드)", path, count)
        return count

    # ─── 내부 유틸 ────────────────────────────────────────────────────────────

    def _read_until_prompt(self) -> str:
        """소켓에서 BCM 프롬프트가 나올 때까지 데이터를 읽는다."""
        data = self._buf
        while NETSERVE_PROMPT not in data:
            try:
                chunk = self._sock.recv(4096).decode("ascii", errors="replace")
            except socket.timeout:
                raise BCMError("응답 대기 중 타임아웃 (프롬프트 미수신)")
            if not chunk:
                raise BCMError("netserve가 연결을 닫았습니다.")
            data += chunk

        idx = data.index(NETSERVE_PROMPT)
        # 프롬프트 이후 남은 데이터는 버퍼에 보관
        self._buf = data[idx + len(NETSERVE_PROMPT):]
        return data[:idx]


# ─── 편의 함수 (싱글 커맨드용) ────────────────────────────────────────────────

def run_soc_cmd(command: str) -> str:
    """단일 SOC 커맨드를 실행하고 결과를 반환한다. (빠른 일회성 사용)"""
    with BCMSdk() as sdk:
        return sdk.cmd(command)


def run_soc_file(path: str) -> int:
    """단일 .soc 파일을 실행한다. (빠른 일회성 사용)"""
    with BCMSdk() as sdk:
        return sdk.load_soc_file(path)
