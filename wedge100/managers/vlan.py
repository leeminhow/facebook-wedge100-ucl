"""
wedge100/managers/vlan.py
--------------------------
VLAN 관리자.

기능:
  - VLAN 생성 / 삭제
  - 포트 추가 / 제거 (tagged / untagged)
  - VLAN 상태 조회
  - JSON 파일로 상태 영속화 (재부팅 후 복구용)

BCM SOC VLAN 커맨드 예시:
  vlan create 100 pbm=ce0,ce1,ce2
  vlan add 100 pbm=ce3
  vlan adduntagged 100 pbm=ce3
  vlan remove 100 pbm=ce3
  vlan destroy 100
  vlan show
"""

import json
import logging
import os
from typing import Optional

from wedge100.config import (
    FP_TO_CE, validate_fp_port, VLAN_STATE_FILE,
)
from wedge100.bcm.sdk import BCMSdk
from wedge100.bcm import soc_commands as soc

logger = logging.getLogger(__name__)

VLAN_ID_MIN = 1
VLAN_ID_MAX = 4094
DEFAULT_VLAN = 1


class VLANEntry:
    """단일 VLAN 데이터 클래스."""

    def __init__(self, vid: int, name: str = ""):
        self.vid = vid
        self.name = name or f"VLAN{vid:04d}"
        self.tagged_ports: list[int] = []    # fp_port 번호 리스트
        self.untagged_ports: list[int] = []

    def to_dict(self) -> dict:
        return {
            "vid": self.vid,
            "name": self.name,
            "tagged_ports": sorted(self.tagged_ports),
            "untagged_ports": sorted(self.untagged_ports),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VLANEntry":
        v = cls(d["vid"], d.get("name", ""))
        v.tagged_ports = d.get("tagged_ports", [])
        v.untagged_ports = d.get("untagged_ports", [])
        return v


class VLANManager:
    """Wedge 100 VLAN 관리자."""

    def __init__(self, state_file: str = VLAN_STATE_FILE):
        self._state_file = state_file
        self._vlans: dict[int, VLANEntry] = {}
        self._load_state()

    # ─── VLAN 생성 / 삭제 ────────────────────────────────────────────────────

    def create(
        self,
        vid: int,
        name: str = "",
        tagged_ports: Optional[list[int]] = None,
        untagged_ports: Optional[list[int]] = None,
    ) -> VLANEntry:
        """
        VLAN을 생성한다.

        Args:
            vid: VLAN ID (1-4094)
            name: VLAN 이름 (선택)
            tagged_ports: Tagged 포트 목록 (Front Panel 번호)
            untagged_ports: Untagged 포트 목록
        """
        self._validate_vid(vid)
        if vid in self._vlans:
            raise ValueError(f"VLAN {vid}가 이미 존재합니다.")

        tagged = tagged_ports or []
        untagged = untagged_ports or []
        all_ports = list(set(tagged + untagged))

        for fp in all_ports:
            validate_fp_port(fp)

        ce_indices = [FP_TO_CE[fp] for fp in all_ports]
        untagged_ces = [FP_TO_CE[fp] for fp in untagged]

        with BCMSdk() as sdk:
            cmds = soc.vlan_create(vid, ce_indices, untagged=False)
            for cmd in cmds:
                sdk.cmd(cmd)
            # Untagged 설정
            if untagged_ces:
                ubm = ",".join(f"ce{i}" for i in untagged_ces)
                sdk.cmd(f"vlan adduntagged {vid} pbm={ubm}")

        entry = VLANEntry(vid, name)
        entry.tagged_ports = [fp for fp in tagged if fp not in untagged]
        entry.untagged_ports = untagged
        self._vlans[vid] = entry
        self._save_state()
        logger.info("VLAN %d 생성 완료 (tagged=%s, untagged=%s)", vid, tagged, untagged)
        return entry

    def delete(self, vid: int) -> None:
        """VLAN을 삭제한다."""
        self._validate_vid(vid)
        if vid == DEFAULT_VLAN:
            raise ValueError("기본 VLAN 1은 삭제할 수 없습니다.")
        if vid not in self._vlans:
            raise KeyError(f"VLAN {vid}가 존재하지 않습니다.")

        with BCMSdk() as sdk:
            sdk.cmd(soc.vlan_destroy(vid))

        del self._vlans[vid]
        self._save_state()
        logger.info("VLAN %d 삭제 완료", vid)

    # ─── 포트 추가 / 제거 ────────────────────────────────────────────────────

    def add_port(self, vid: int, fp_port: int, tagged: bool = True) -> None:
        """VLAN에 포트를 추가한다."""
        self._validate_vid(vid)
        validate_fp_port(fp_port)
        if vid not in self._vlans:
            raise KeyError(f"VLAN {vid}가 존재하지 않습니다.")

        ce_idx = FP_TO_CE[fp_port]
        with BCMSdk() as sdk:
            for cmd in soc.vlan_add_port(vid, ce_idx, tagged):
                sdk.cmd(cmd)

        entry = self._vlans[vid]
        if tagged:
            if fp_port not in entry.tagged_ports:
                entry.tagged_ports.append(fp_port)
        else:
            if fp_port not in entry.untagged_ports:
                entry.untagged_ports.append(fp_port)

        self._save_state()
        mode = "tagged" if tagged else "untagged"
        logger.info("VLAN %d에 포트 %d 추가 (%s)", vid, fp_port, mode)

    def remove_port(self, vid: int, fp_port: int) -> None:
        """VLAN에서 포트를 제거한다."""
        self._validate_vid(vid)
        validate_fp_port(fp_port)
        if vid not in self._vlans:
            raise KeyError(f"VLAN {vid}가 존재하지 않습니다.")

        ce_idx = FP_TO_CE[fp_port]
        with BCMSdk() as sdk:
            for cmd in soc.vlan_remove_port(vid, ce_idx):
                sdk.cmd(cmd)

        entry = self._vlans[vid]
        entry.tagged_ports = [p for p in entry.tagged_ports if p != fp_port]
        entry.untagged_ports = [p for p in entry.untagged_ports if p != fp_port]

        self._save_state()
        logger.info("VLAN %d에서 포트 %d 제거", vid, fp_port)

    # ─── 조회 ─────────────────────────────────────────────────────────────────

    def show(self, vid: Optional[int] = None) -> dict[int, VLANEntry]:
        """VLAN 상태를 반환한다. vid=None이면 전체."""
        if vid is not None:
            if vid not in self._vlans:
                raise KeyError(f"VLAN {vid}가 존재하지 않습니다.")
            return {vid: self._vlans[vid]}
        return dict(self._vlans)

    def exists(self, vid: int) -> bool:
        return vid in self._vlans

    # ─── 상태 영속화 ─────────────────────────────────────────────────────────

    def _save_state(self) -> None:
        """현재 VLAN 상태를 JSON 파일에 저장한다."""
        os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
        data = {vid: v.to_dict() for vid, v in self._vlans.items()}
        with open(self._state_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug("VLAN 상태 저장: %s", self._state_file)

    def _load_state(self) -> None:
        """JSON 파일에서 VLAN 상태를 복구한다."""
        if not os.path.isfile(self._state_file):
            logger.debug("VLAN 상태 파일 없음. 초기 상태로 시작.")
            return
        try:
            with open(self._state_file) as f:
                data = json.load(f)
            self._vlans = {
                int(vid): VLANEntry.from_dict(v)
                for vid, v in data.items()
            }
            logger.info("VLAN 상태 복구: %d개 VLAN", len(self._vlans))
        except Exception as e:
            logger.warning("VLAN 상태 파일 읽기 실패: %s", e)

    def replay_to_asic(self) -> None:
        """
        저장된 VLAN 설정을 ASIC에 재적용한다.
        재부팅 후 bcm.user 초기화 완료 시 호출.
        """
        if not self._vlans:
            return
        logger.info("VLAN %d개를 ASIC에 재적용 중...", len(self._vlans))
        with BCMSdk() as sdk:
            for vid, entry in self._vlans.items():
                all_fps = entry.tagged_ports + entry.untagged_ports
                ce_indices = [FP_TO_CE[fp] for fp in all_fps]
                untagged_ces = [FP_TO_CE[fp] for fp in entry.untagged_ports]

                for cmd in soc.vlan_create(vid, ce_indices):
                    sdk.cmd(cmd)
                if untagged_ces:
                    ubm = ",".join(f"ce{i}" for i in untagged_ces)
                    sdk.cmd(f"vlan adduntagged {vid} pbm={ubm}")

    # ─── 유틸 ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_vid(vid: int) -> None:
        if not (VLAN_ID_MIN <= vid <= VLAN_ID_MAX):
            raise ValueError(f"VLAN ID {vid}는 유효 범위({VLAN_ID_MIN}-{VLAN_ID_MAX}) 밖입니다.")
