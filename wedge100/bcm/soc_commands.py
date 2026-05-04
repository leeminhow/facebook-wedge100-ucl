"""
wedge100/bcm/soc_commands.py
-----------------------------
BCM SOC 셸 커맨드 문자열 생성 헬퍼.

각 함수는 SOC 커맨드 문자열(들)을 반환한다.
실제 전송은 BCMSdk.cmd() 가 담당.

참고 파일:
  - bin/rc.soc              (포트 초기화 패턴)
  - bin/bcm_caui/caui.txt   (CAUI / 100G 설정)
  - bin/bcm_fec/fec_*.txt   (FEC on/off)
  - bin/port_100G_40G_10G_ango.cint
"""

from wedge100.config import SPEED_MAP, FP_TO_CE


# ─── 포트 커맨드 ──────────────────────────────────────────────────────────────

def port_speed(ce_idx: int, speed_str: str) -> list[str]:
    """
    단일 포트 속도 설정 커맨드 목록 반환.
    speed_str: "100G" | "40G" | "50G" | "25G" | "10G"
    """
    speed_kbps, lanes = SPEED_MAP[speed_str]
    ce = f"ce{ce_idx}"
    return [
        f"port {ce} speed={speed_kbps} lanes={lanes} an=0",
        f"port {ce} enable=true",
    ]


def port_breakout(ce_idx: int, mode: str) -> list[str]:
    """
    Breakout 모드 설정 커맨드 목록.
    mode: "1x100G" | "2x50G" | "4x25G" | "4x10G" | "1x40G"
    """
    from wedge100.config import BREAKOUT_MAP
    num_sub, speed_str, lanes = BREAKOUT_MAP[mode]
    speed_kbps, _ = SPEED_MAP[speed_str]
    cmds = []

    if num_sub == 1:
        # 분할 해제 (기본 100G 또는 40G)
        ce = f"ce{ce_idx}"
        cmds += [
            f"port {ce} speed={speed_kbps} lanes=4 an=0",
            f"port {ce} enable=true",
        ]
    else:
        # 분할: ce_idx 기반 서브포트 생성
        # Tomahawk에서 4-lane QSFP28은 ce_base + 0,1,2,3 서브포트로 분할
        # 단, 논리 포트 번호 계산 필요 (각 ce는 4레인이므로 +0..+3)
        sub_ces = [f"ce{ce_idx + i}" for i in range(num_sub)]
        for sce in sub_ces:
            cmds += [
                f"port {sce} speed={speed_kbps} lanes={lanes} an=0",
                f"port {sce} enable=true",
            ]
    return cmds


def port_enable(ce_idx: int, enable: bool = True) -> str:
    """포트 enable/disable 커맨드."""
    state = "true" if enable else "false"
    return f"port ce{ce_idx} enable={state}"


def port_autoneg(ce_idx: int, enable: bool = True) -> str:
    """Auto-negotiation 설정 커맨드."""
    state = 1 if enable else 0
    return f"port ce{ce_idx} an={state}"


def port_status(ce_idx: int | None = None) -> str:
    """
    포트 상태 조회 커맨드.
    ce_idx=None 이면 전체 ce 포트 조회.
    """
    target = f"ce{ce_idx}" if ce_idx is not None else "ce"
    return f"ps {target}"


def port_counters(ce_idx: int) -> list[str]:
    """포트 TX/RX 카운터 조회 커맨드."""
    ce = f"ce{ce_idx}"
    return [
        f"show counters {ce}",
    ]


def port_clear_counters(ce_idx: int | None = None) -> str:
    """포트 카운터 초기화."""
    target = f"ce{ce_idx}" if ce_idx is not None else "ce"
    return f"clear counters {target}"


# ─── FEC 커맨드 ───────────────────────────────────────────────────────────────

def fec_enable(ce_idx: int, enable: bool = True) -> list[str]:
    """
    RS-FEC (CL91) 설정 커맨드 목록.
    bin/bcm_fec/fec_ceN_on.txt 패턴 참조.
    """
    fec_val = "BCM_PORT_PHY_CONTROL_FEC_ON" if enable else "BCM_PORT_PHY_CONTROL_FEC_OFF"
    return [
        f"print bcm_port_phy_control_set(0, {_ce_to_logical(ce_idx)}, "
        f"BCM_PORT_PHY_CONTROL_FORWARD_ERROR_CORRECTION_CL91, {fec_val});"
    ]


def _ce_to_logical(ce_idx: int) -> int:
    """CE 인덱스 → BCM 논리 포트 번호 (대략적 계산, rc.soc 패턴 기반)."""
    # Tomahawk에서 ce0→port1, ce1→port5, ... ce_n → port(4n+1)
    # 단 ce28-31은 port119,123,127,131 (Tile 0 상단)
    special = {28: 119, 29: 123, 30: 127, 31: 131}
    if ce_idx in special:
        return special[ce_idx]
    return ce_idx * 4 + 1


# ─── VLAN 커맨드 ──────────────────────────────────────────────────────────────

def vlan_create(vid: int, ce_indices: list[int], untagged: bool = False) -> list[str]:
    """VLAN 생성 및 포트 추가 커맨드."""
    pbm = ",".join(f"ce{i}" for i in ce_indices)
    ubm = pbm if untagged else ""
    cmds = [f"vlan create {vid} pbm={pbm}"]
    if ubm:
        cmds.append(f"vlan adduntagged {vid} pbm={ubm}")
    return cmds


def vlan_destroy(vid: int) -> str:
    """VLAN 삭제 커맨드."""
    return f"vlan destroy {vid}"


def vlan_add_port(vid: int, ce_idx: int, tagged: bool = True) -> list[str]:
    """VLAN에 포트 추가 커맨드."""
    ce = f"ce{ce_idx}"
    cmds = [f"vlan add {vid} pbm={ce}"]
    if not tagged:
        cmds.append(f"vlan adduntagged {vid} pbm={ce}")
    return cmds


def vlan_remove_port(vid: int, ce_idx: int) -> list[str]:
    """VLAN에서 포트 제거 커맨드."""
    ce = f"ce{ce_idx}"
    return [
        f"vlan removeuntagged {vid} pbm={ce}",
        f"vlan remove {vid} pbm={ce}",
    ]


def vlan_show(vid: int | None = None) -> str:
    """VLAN 상태 조회 커맨드."""
    return f"vlan show {vid}" if vid else "vlan show"


# ─── CAUI / PHY 커맨드 (100G용) ──────────────────────────────────────────────

def caui_init(ce_idx: int) -> list[str]:
    """
    CAUI (100GBASE-CR4) 초기화 커맨드.
    bin/bcm_caui/caui_ceN.txt 패턴 참조.
    """
    ce = f"ce{ce_idx}"
    return [
        f"port {ce} if=CAUI",
        f"port {ce} speed=100000",
        f"phy control {ce} DriverCurrent=0x8",
    ]


def all_ports_status() -> str:
    """전체 포트 상태 요약 커맨드."""
    return "ps ce"
