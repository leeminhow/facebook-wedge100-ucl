"""
wedge100/managers/lldp.py
--------------------------
LLDP (Link Layer Discovery Protocol) 관리자.

LLDP란?
  인접 네트워크 장비(스위치, 서버 NIC 등)가 서로 자신을 광고하는 프로토콜.
  "이 포트에 어떤 장비가 연결됐는지" 를 자동으로 알 수 있다.
  예) 포트 5에 연결된 장비가 "서버-A eth0, Dell PowerEdge R740" 임을 표시.

요구사항: lldpd 데몬 실행 중
  sudo apt-get install lldpd
  sudo systemctl enable --now lldpd

  lldpd는 ONL에서 ce0..ce31 인터페이스를 자동 감지한다.
"""

import json
import logging
import re
import subprocess
from typing import Optional

from wedge100.config import FP_TO_CE, CE_TO_FP

log = logging.getLogger(__name__)


class LLDPNeighbor:
    """LLDP 이웃 장비 정보."""

    def __init__(self, fp_port: int):
        self.fp_port    = fp_port
        self.chassis_id   = ""
        self.chassis_name = ""
        self.port_id      = ""
        self.port_desc    = ""
        self.system_desc  = ""
        self.capabilities: list[str] = []
        self.mgmt_ip: Optional[str] = None
        self.ttl = 0

    def to_dict(self) -> dict:
        return {
            "port":          self.fp_port,
            "chassis_id":    self.chassis_id,
            "chassis_name":  self.chassis_name,
            "port_id":       self.port_id,
            "port_desc":     self.port_desc,
            "system_desc":   self.system_desc[:80] if self.system_desc else "",
            "capabilities":  self.capabilities,
            "mgmt_ip":       self.mgmt_ip,
            "ttl":           self.ttl,
        }


class LLDPManager:
    """LLDP 이웃 관리자."""

    def get_neighbors(self) -> list[LLDPNeighbor]:
        """
        현재 LLDP 이웃 목록을 반환한다.
        lldpcli를 호출해 실시간 조회.
        """
        # JSON 형식으로 조회 시도
        try:
            result = subprocess.run(
                ["lldpcli", "-f", "json", "show", "neighbors"],
                timeout=5, capture_output=True, text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return self._parse_json(result.stdout)
        except FileNotFoundError:
            pass
        except Exception as e:
            log.debug("lldpcli JSON 실패: %s", e)

        # 텍스트 형식 폴백
        try:
            result = subprocess.run(
                ["lldpcli", "show", "neighbors", "detail"],
                timeout=5, capture_output=True, text=True,
            )
            if result.returncode == 0:
                return self._parse_text(result.stdout)
        except FileNotFoundError:
            log.warning("lldpcli 미설치. 'apt-get install lldpd' 실행 필요")
        except Exception as e:
            log.error("LLDP 조회 오류: %s", e)

        return []

    def get_neighbor(self, fp_port: int) -> Optional[LLDPNeighbor]:
        """특정 포트의 LLDP 이웃을 반환한다."""
        nbrs = self.get_neighbors()
        for n in nbrs:
            if n.fp_port == fp_port:
                return n
        return None

    def is_running(self) -> bool:
        """lldpd 데몬 실행 여부 확인."""
        result = subprocess.run(
            ["pgrep", "lldpd"], capture_output=True
        )
        return result.returncode == 0

    # ── 파싱 ────────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> list[LLDPNeighbor]:
        """lldpcli -f json 출력 파싱."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        neighbors = []
        iface_list = data.get("lldp", {}).get("interface", [])
        if isinstance(iface_list, dict):
            iface_list = [iface_list]

        for iface in iface_list:
            for iface_name, iface_data in iface.items():
                ce_m = re.match(r"ce(\d+)", iface_name)
                if not ce_m:
                    continue
                ce_idx = int(ce_m.group(1))
                fp_port = CE_TO_FP.get(ce_idx, 0)
                if not fp_port:
                    continue

                nbr = LLDPNeighbor(fp_port)
                chassis = iface_data.get("chassis", {})
                port    = iface_data.get("port", {})

                if isinstance(chassis, list) and chassis:
                    chassis = chassis[0]
                if isinstance(port, list) and port:
                    port = port[0]

                for cname, cdata in (chassis.items() if isinstance(chassis, dict) else []):
                    nbr.chassis_name = cname
                    if isinstance(cdata, dict):
                        nbr.chassis_id  = cdata.get("id", {}).get("value", "")
                        mgmt = cdata.get("mgmt-ip", "")
                        nbr.mgmt_ip = mgmt if mgmt else None
                        caps = cdata.get("capability", [])
                        if isinstance(caps, list):
                            nbr.capabilities = [
                                c.get("type", "") for c in caps
                                if c.get("enabled")
                            ]
                    break

                if isinstance(port, dict):
                    nbr.port_id   = port.get("id", {}).get("value", "")
                    nbr.port_desc = port.get("descr", "")
                    nbr.ttl = port.get("ttl", 0)

                neighbors.append(nbr)
        return neighbors

    def _parse_text(self, raw: str) -> list[LLDPNeighbor]:
        """lldpcli show neighbors detail 텍스트 파싱."""
        neighbors = []
        blocks = re.split(r"^Interface:\s+", raw, flags=re.MULTILINE)
        for block in blocks[1:]:
            lines = block.strip().splitlines()
            if not lines:
                continue
            ce_m = re.match(r"(ce\d+)", lines[0])
            if not ce_m:
                continue
            ce_idx = int(ce_m.group(1).replace("ce", ""))
            fp_port = CE_TO_FP.get(ce_idx, 0)
            if not fp_port:
                continue

            nbr = LLDPNeighbor(fp_port)
            for line in lines:
                line = line.strip()
                if "ChassisID:" in line:
                    nbr.chassis_id = line.split(":", 1)[1].strip()
                elif "SysName:" in line:
                    nbr.chassis_name = line.split(":", 1)[1].strip()
                elif "PortID:" in line:
                    nbr.port_id = line.split(":", 1)[1].strip()
                elif "PortDescr:" in line:
                    nbr.port_desc = line.split(":", 1)[1].strip()
                elif "SysDescr:" in line:
                    nbr.system_desc = line.split(":", 1)[1].strip()[:255]
                elif "MgmtIP:" in line:
                    nbr.mgmt_ip = line.split(":", 1)[1].strip()
                elif "TTL:" in line:
                    try:
                        nbr.ttl = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif "Capability:" in line:
                    cap = line.split(":", 1)[1].strip()
                    if "enabled" in cap.lower():
                        nbr.capabilities.append(cap.split()[0])
            neighbors.append(nbr)
        return neighbors
