"""
wedge100/managers/bgp.py
-------------------------
BGP (Border Gateway Protocol) 관리자.
FRRouting (vtysh) 기반.

요구사항:
  sudo apt-get install frr
  /etc/frr/daemons 에서 bgpd=yes 로 변경
  sudo systemctl restart frr

vtysh 커맨드:
  router bgp <AS>
  bgp router-id <IP>
  neighbor <IP> remote-as <AS>
  show bgp summary
  show bgp neighbors
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class BGPSummaryEntry:
    peer_ip:     str
    remote_as:   int
    state:       str          # "Established" | "Active" | "Idle" | ...
    uptime:      str          # "00:05:23"
    prefix_count: int = 0
    msg_rcvd:    int = 0
    msg_sent:    int = 0


@dataclass
class BGPNeighborDetail:
    peer_ip:        str
    remote_as:      int
    local_as:       int
    state:          str
    uptime:         str
    hold_time:      int = 90
    keepalive:      int = 30
    prefixes_rcvd:  int = 0
    prefixes_sent:  int = 0
    bgp_version:    int = 4
    remote_router_id: str = ""
    description:    str = ""


class BGPManager:
    """BGP 설정 및 상태 관리자 (FRRouting vtysh 기반)."""

    def is_available(self) -> bool:
        """FRRouting이 설치되어 있고 BGP 데몬이 실행 중인지 확인."""
        result = subprocess.run(
            ["which", "vtysh"], capture_output=True
        )
        if result.returncode != 0:
            return False
        result2 = subprocess.run(
            ["pgrep", "bgpd"], capture_output=True
        )
        return result2.returncode == 0

    # ── vtysh 실행 헬퍼 ──────────────────────────────────────────

    def _vtysh(self, *commands: str, config_mode: bool = False) -> str:
        """
        vtysh 커맨드를 실행하고 결과를 반환한다.
        config_mode=True: 'configure terminal' 진입 후 실행
        """
        if not self.is_available():
            raise RuntimeError(
                "FRRouting(vtysh)이 실행 중이지 않습니다.\n"
                "sudo apt-get install frr && sudo systemctl start frr"
            )

        if config_mode:
            cmd_list = ["configure terminal"] + list(commands) + ["end", "write"]
        else:
            cmd_list = list(commands)

        cmd_str = " ; ".join(cmd_list)
        result = subprocess.run(
            ["vtysh", "-c", cmd_str],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"vtysh 오류: {result.stderr.strip()}")
        return result.stdout

    # ── BGP 설정 ─────────────────────────────────────────────────

    def configure(self, local_as: int, router_id: str) -> None:
        """BGP 기본 설정 (AS 번호, Router ID)."""
        self._vtysh(
            f"router bgp {local_as}",
            f"bgp router-id {router_id}",
            config_mode=True,
        )
        log.info("BGP 설정: AS=%d, router-id=%s", local_as, router_id)

    def add_neighbor(
        self,
        peer_ip: str,
        remote_as: int,
        description: str = "",
    ) -> None:
        """BGP 이웃(피어)을 추가한다."""
        # AS 번호 먼저 조회
        local_as = self._get_local_as()
        if not local_as:
            raise RuntimeError("BGP가 설정되지 않았습니다. configure()를 먼저 실행하세요.")

        cmds = [
            f"router bgp {local_as}",
            f"neighbor {peer_ip} remote-as {remote_as}",
        ]
        if description:
            cmds.append(f"neighbor {peer_ip} description {description}")

        self._vtysh(*cmds, config_mode=True)
        log.info("BGP 이웃 추가: %s (AS%d)", peer_ip, remote_as)

    def remove_neighbor(self, peer_ip: str) -> None:
        """BGP 이웃을 제거한다."""
        local_as = self._get_local_as()
        if not local_as:
            raise RuntimeError("BGP가 설정되지 않았습니다.")
        self._vtysh(
            f"router bgp {local_as}",
            f"no neighbor {peer_ip}",
            config_mode=True,
        )
        log.info("BGP 이웃 제거: %s", peer_ip)

    def advertise_network(self, network: str) -> None:
        """BGP로 네트워크를 광고한다."""
        local_as = self._get_local_as()
        if not local_as:
            raise RuntimeError("BGP가 설정되지 않았습니다.")
        self._vtysh(
            f"router bgp {local_as}",
            f"network {network}",
            config_mode=True,
        )
        log.info("BGP 네트워크 광고: %s", network)

    # ── BGP 상태 조회 ─────────────────────────────────────────────

    def show_summary(self) -> list[BGPSummaryEntry]:
        """BGP 피어 요약 상태를 반환한다."""
        try:
            raw = self._vtysh("show bgp summary")
            return self._parse_summary(raw)
        except RuntimeError as e:
            log.warning("BGP summary 조회 실패: %s", e)
            return []

    def show_neighbor(self, peer_ip: Optional[str] = None) -> list[BGPNeighborDetail]:
        """BGP 이웃 상세 정보를 반환한다."""
        cmd = f"show bgp neighbors {peer_ip}" if peer_ip else "show bgp neighbors"
        try:
            raw = self._vtysh(cmd)
            return self._parse_neighbors(raw)
        except RuntimeError as e:
            log.warning("BGP neighbors 조회 실패: %s", e)
            return []

    def show_routes(self) -> str:
        """BGP 라우팅 테이블을 반환한다."""
        try:
            return self._vtysh("show bgp ipv4 unicast")
        except RuntimeError as e:
            return f"오류: {e}"

    def show_running_config(self) -> str:
        """BGP 실행 중인 설정을 반환한다."""
        try:
            return self._vtysh("show running-config bgpd")
        except RuntimeError:
            try:
                return self._vtysh("show running-config")
            except RuntimeError as e:
                return f"오류: {e}"

    # ── 파싱 ─────────────────────────────────────────────────────

    def _parse_summary(self, raw: str) -> list[BGPSummaryEntry]:
        """show bgp summary 출력 파싱."""
        entries = []
        # 피어 줄 패턴: IP AS MsgRcvd MsgSent ... State/PfxRcd
        peer_pattern = re.compile(
            r"^(\d+\.\d+\.\d+\.\d+)\s+4\s+(\d+)\s+(\d+)\s+(\d+)"
            r"\s+\S+\s+\S+\s+(\S+)\s+(\S+)",
            re.MULTILINE,
        )
        for m in peer_pattern.finditer(raw):
            peer_ip, remote_as, msg_rcvd, msg_sent, uptime, state_or_pfx = m.groups()
            try:
                prefix_count = int(state_or_pfx)
                state = "Established"
            except ValueError:
                prefix_count = 0
                state = state_or_pfx

            entries.append(BGPSummaryEntry(
                peer_ip=peer_ip,
                remote_as=int(remote_as),
                state=state,
                uptime=uptime,
                prefix_count=prefix_count,
                msg_rcvd=int(msg_rcvd),
                msg_sent=int(msg_sent),
            ))
        return entries

    def _parse_neighbors(self, raw: str) -> list[BGPNeighborDetail]:
        """show bgp neighbors 출력 파싱."""
        neighbors = []
        # 피어별 블록 분리
        blocks = re.split(r"^BGP neighbor is ", raw, flags=re.MULTILINE)
        for block in blocks[1:]:
            lines = block.splitlines()
            if not lines:
                continue

            ip_m = re.match(r"(\d+\.\d+\.\d+\.\d+)", lines[0])
            if not ip_m:
                continue
            peer_ip = ip_m.group(1)

            nbr = BGPNeighborDetail(
                peer_ip=peer_ip,
                remote_as=0, local_as=0,
                state="Unknown", uptime="-",
            )

            for line in lines:
                if "remote AS" in line:
                    m = re.search(r"remote AS (\d+)", line)
                    if m:
                        nbr.remote_as = int(m.group(1))
                    m2 = re.search(r"local AS (\d+)", line)
                    if m2:
                        nbr.local_as = int(m2.group(1))
                elif "BGP state =" in line:
                    m = re.search(r"BGP state = (\w+)", line)
                    if m:
                        nbr.state = m.group(1)
                    m2 = re.search(r"up for ([\d:]+)", line)
                    if m2:
                        nbr.uptime = m2.group(1)
                elif "Remote router-id" in line:
                    m = re.search(r"Remote router-id ([\d.]+)", line)
                    if m:
                        nbr.remote_router_id = m.group(1)
                elif "Description:" in line:
                    nbr.description = line.split(":", 1)[1].strip()
                elif "prefixes received" in line.lower():
                    m = re.search(r"(\d+)\s+prefixes received", line)
                    if m:
                        nbr.prefixes_rcvd = int(m.group(1))

            neighbors.append(nbr)
        return neighbors

    def _get_local_as(self) -> Optional[int]:
        """현재 설정된 로컬 AS 번호 조회."""
        try:
            raw = self._vtysh("show bgp summary")
            m = re.search(r"local AS number (\d+)", raw)
            if m:
                return int(m.group(1))
            # 다른 패턴
            m2 = re.search(r"BGP router identifier .+, local AS number (\d+)", raw)
            if m2:
                return int(m2.group(1))
        except Exception:
            pass
        return None
