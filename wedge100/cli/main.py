"""
wedge100/cli/main.py + port_cli.py 통합 파일
---------------------------------------------
Click 기반 CLI 메인 진입점 및 port 서브커맨드.

사용법:
  wedge port show              # 전체 포트 상태
  wedge port show 1            # 포트 1 상태
  wedge port set 1 speed 100G  # 포트 1 → 100G
  wedge port breakout 1 4x25G  # 포트 1 → 4x25G 분할
  wedge port enable 1
  wedge port disable 1
  wedge port fec 1 on
  wedge port counters 1
  wedge port counters --clear
"""

import sys
import logging
import click

from wedge100.managers.port import PortManager
from wedge100.managers.led import LEDManager
from wedge100.managers.vlan import VLANManager
from wedge100.managers.hw import HWManager
from wedge100.config import SPEED_MAP, BREAKOUT_MAP, LED_SOC_FILES

# ─── 로깅 설정 ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

# ─── 공통 스타일 헬퍼 ─────────────────────────────────────────────────────────

def _ok(msg: str) -> None:
    click.echo(click.style("✓ ", fg="green") + msg)

def _err(msg: str) -> None:
    click.echo(click.style("✗ ", fg="red") + msg, err=True)

def _warn(msg: str) -> None:
    click.echo(click.style("! ", fg="yellow") + msg)

def _header(title: str) -> None:
    click.echo(click.style(f"\n{'─' * 70}", fg="bright_black"))
    click.echo(click.style(f"  {title}", bold=True))
    click.echo(click.style(f"{'─' * 70}", fg="bright_black"))


# ─── 루트 그룹 ───────────────────────────────────────────────────────────────

@click.group()
@click.version_option("0.1.0", prog_name="wedge")
def wedge():
    """
    \b
    Wedge 100 NOS CLI
    ─────────────────────────────────────────
    Accton/Facebook Wedge 100 (32x100G) 스위치 제어 도구.
    BCM SDK (netserve) 기반으로 동작합니다.

    \b
    서브커맨드:
      port    포트 설정 및 상태 조회
      led     LED 색상 제어
      vlan    VLAN 관리
      show    종합 상태 조회
    """
    pass


# ─── port 커맨드 그룹 ─────────────────────────────────────────────────────────

@wedge.group()
def port():
    """QSFP 포트 설정 및 상태 조회."""
    pass


@port.command("show")
@click.argument("port_num", type=int, required=False, metavar="[PORT]")
def port_show(port_num):
    """
    포트 상태를 출력한다.

    \b
    예시:
      wedge port show        # 전체 포트
      wedge port show 1      # 포트 1
    """
    mgr = PortManager()
    try:
        statuses = mgr.get_status(port_num)
    except Exception as e:
        _err(f"포트 상태 조회 실패: {e}")
        sys.exit(1)

    _header("포트 상태")
    fmt = "{:>4}  {:>6}  {:>6}  {:>6}  {:>7}  {:>6}"
    click.echo(fmt.format("PORT", "CE", "LINK", "SPEED", "DUPLEX", "LANES"))
    click.echo("─" * 46)

    for s in statuses:
        link_colored = (
            click.style("UP  ", fg="green")
            if s.link
            else click.style("DOWN", fg="red")
        )
        speed_str = s.speed or "-"
        duplex_str = s.duplex or "-"
        line = fmt.format(
            s.fp_port or "-",
            s.ce_name,
            "",  # 색상 문자열은 별도 처리
            speed_str,
            duplex_str,
            s.lanes,
        )
        # 링크 상태 삽입
        parts = line.split()
        click.echo(
            f"  {parts[0]:>3}  {parts[1]:>6}  {link_colored}  "
            f"{speed_str:>6}  {duplex_str:>6}  {parts[-1]:>5}"
        )


@port.command("set")
@click.argument("port_num", type=int, metavar="PORT")
@click.argument("attribute", type=click.Choice(["speed"]), metavar="ATTR")
@click.argument("value", metavar="VALUE")
def port_set(port_num, attribute, value):
    """
    포트 속성을 설정한다.

    \b
    예시:
      wedge port set 1 speed 100G
      wedge port set 1 speed 40G
      wedge port set 1 speed 25G
    """
    mgr = PortManager()
    if attribute == "speed":
        value = value.upper()
        if value not in SPEED_MAP:
            _err(f"지원하지 않는 속도: {value}. 가능: {', '.join(SPEED_MAP.keys())}")
            sys.exit(1)
        try:
            mgr.set_speed(port_num, value)
            _ok(f"포트 {port_num} 속도 → {value}")
        except Exception as e:
            _err(str(e))
            sys.exit(1)


@port.command("breakout")
@click.argument("port_num", type=int, metavar="PORT")
@click.argument("mode", type=click.Choice(list(BREAKOUT_MAP.keys())), metavar="MODE")
def port_breakout(port_num, mode):
    """
    포트 Breakout 모드를 설정한다.

    \b
    모드:
      1x100G   기본 100G (분할 없음)
      2x50G    2개 50G 서브포트로 분할
      4x25G    4개 25G 서브포트로 분할
      4x10G    4개 10G 서브포트로 분할
      1x40G    40G 단일 포트

    \b
    예시:
      wedge port breakout 1 4x25G
      wedge port breakout 1 1x100G
    """
    mgr = PortManager()
    try:
        mgr.set_breakout(port_num, mode)
        _ok(f"포트 {port_num} breakout → {mode}")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@port.command("enable")
@click.argument("port_num", type=int, metavar="PORT")
def port_enable(port_num):
    """포트를 활성화한다."""
    mgr = PortManager()
    try:
        mgr.enable(port_num)
        _ok(f"포트 {port_num} 활성화")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@port.command("disable")
@click.argument("port_num", type=int, metavar="PORT")
def port_disable(port_num):
    """포트를 비활성화한다."""
    mgr = PortManager()
    try:
        mgr.disable(port_num)
        _ok(f"포트 {port_num} 비활성화")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@port.command("fec")
@click.argument("port_num", type=int, metavar="PORT")
@click.argument("state", type=click.Choice(["on", "off"]), metavar="on|off")
def port_fec(port_num, state):
    """
    RS-FEC (CL91) 설정을 변경한다.

    \b
    예시:
      wedge port fec 1 on
      wedge port fec 1 off
    """
    mgr = PortManager()
    enable = state == "on"
    try:
        mgr.set_fec(port_num, enable)
        _ok(f"포트 {port_num} FEC → {state.upper()}")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@port.command("counters")
@click.argument("port_num", type=int, required=False, metavar="[PORT]")
@click.option("--clear", is_flag=True, help="카운터 초기화")
def port_counters(port_num, clear):
    """
    포트 TX/RX 카운터를 조회하거나 초기화한다.

    \b
    예시:
      wedge port counters 1
      wedge port counters --clear
    """
    mgr = PortManager()
    if clear:
        try:
            mgr.clear_counters(port_num)
            target = f"포트 {port_num}" if port_num else "전체 포트"
            _ok(f"{target} 카운터 초기화 완료")
        except Exception as e:
            _err(str(e))
            sys.exit(1)
        return

    if port_num is None:
        _err("포트 번호를 지정하거나 --clear 옵션을 사용하세요.")
        sys.exit(1)

    try:
        c = mgr.get_counters(port_num)
    except Exception as e:
        _err(str(e))
        sys.exit(1)

    _header(f"포트 {port_num} 카운터")
    click.echo(f"  RX Packets : {c['rx_packets']:>15,}")
    click.echo(f"  RX Bytes   : {c['rx_bytes']:>15,}")
    click.echo(f"  RX Errors  : {c['rx_errors']:>15,}")
    click.echo(f"  RX Drops   : {c['rx_drops']:>15,}")
    click.echo(f"  TX Packets : {c['tx_packets']:>15,}")
    click.echo(f"  TX Bytes   : {c['tx_bytes']:>15,}")
    click.echo(f"  TX Errors  : {c['tx_errors']:>15,}")


# ─── led 커맨드 그룹 ──────────────────────────────────────────────────────────

@wedge.group()
def led():
    """QSFP 포트 LED 색상 제어."""
    pass


@led.command("set")
@click.argument("target", metavar="all|PORT")
@click.argument("color", type=click.Choice(list(LED_SOC_FILES.keys())), metavar="COLOR")
def led_set(target, color):
    """
    LED 색상을 설정한다.

    \b
    예시:
      wedge led set all green
      wedge led set all off
      wedge led set 1 blue
      wedge led set 5 red

    \b
    색상: green, blue, red, yellow, purple, aqua, off
    """
    mgr = LEDManager()
    if target.lower() == "all":
        try:
            mgr.set_all(color)
            _ok(f"전체 LED → {color}")
        except Exception as e:
            _err(str(e))
            sys.exit(1)
    else:
        try:
            port_num = int(target)
            mgr.set_port(port_num, color)
            _ok(f"포트 {port_num} LED → {color}")
        except ValueError:
            _err(f"대상 오류: '{target}' (all 또는 포트 번호 1-32)")
            sys.exit(1)
        except Exception as e:
            _err(str(e))
            sys.exit(1)


@led.command("speed-mode")
def led_speed_mode():
    """
    포트 링크 속도에 따라 LED 색상을 자동 설정한다.

    \b
    색상 매핑:
      100G → 초록(green)
      50G  → 청록(aqua)
      40G  → 파랑(blue)
      25G  → 노랑(yellow)
      10G  → 보라(purple)
      DOWN → 소등(off)
    """
    port_mgr = PortManager()
    led_mgr = LEDManager()
    try:
        statuses = port_mgr.get_status()
        led_mgr.apply_speed_mode(statuses)
        _ok("speed-mode LED 적용 완료")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@led.command("show")
def led_show():
    """현재 LED 색상 상태를 출력한다 (소프트웨어 상태 기준)."""
    mgr = LEDManager()
    status = mgr.get_status()
    _header("LED 상태")
    if not status:
        click.echo("  (설정된 LED 없음)")
        return
    for fp_port in sorted(status.keys()):
        color = status[fp_port]
        color_styled = click.style(f"{color:>8}", fg=_color_to_ansi(color))
        click.echo(f"  포트 {fp_port:>2} : {color_styled}")


def _color_to_ansi(color: str) -> str:
    mapping = {
        "green": "green", "blue": "blue", "red": "red",
        "yellow": "yellow", "purple": "magenta", "aqua": "cyan",
        "off": "bright_black", "white": "white",
    }
    return mapping.get(color, "white")


# ─── vlan 커맨드 그룹 ─────────────────────────────────────────────────────────

@wedge.group()
def vlan():
    """VLAN 생성, 삭제, 포트 관리."""
    pass


@vlan.command("create")
@click.argument("vid", type=int, metavar="VID")
@click.option("--name", default="", help="VLAN 이름")
@click.option("--ports", default="", help="Tagged 포트 목록 (예: 1,2,3)")
@click.option("--untagged-ports", default="", help="Untagged 포트 목록")
def vlan_create(vid, name, ports, untagged_ports):
    """
    VLAN을 생성한다.

    \b
    예시:
      wedge vlan create 100
      wedge vlan create 200 --name "서버망" --ports 1,2,3
      wedge vlan create 300 --untagged-ports 5,6
    """
    mgr = VLANManager()

    def _parse_ports(s):
        if not s:
            return []
        return [int(p.strip()) for p in s.split(",") if p.strip()]

    tagged = _parse_ports(ports)
    untagged = _parse_ports(untagged_ports)

    try:
        entry = mgr.create(vid, name, tagged, untagged)
        _ok(f"VLAN {vid} ({entry.name}) 생성 완료")
        if tagged:
            click.echo(f"  Tagged 포트: {tagged}")
        if untagged:
            click.echo(f"  Untagged 포트: {untagged}")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@vlan.command("delete")
@click.argument("vid", type=int, metavar="VID")
def vlan_delete(vid):
    """VLAN을 삭제한다."""
    mgr = VLANManager()
    try:
        mgr.delete(vid)
        _ok(f"VLAN {vid} 삭제 완료")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@vlan.command("add")
@click.argument("vid", type=int, metavar="VID")
@click.argument("port_num", type=int, metavar="PORT")
@click.option("--tagged/--untagged", default=True, help="Tagged 또는 Untagged 모드")
def vlan_add(vid, port_num, tagged):
    """
    VLAN에 포트를 추가한다.

    \b
    예시:
      wedge vlan add 100 5
      wedge vlan add 100 6 --untagged
    """
    mgr = VLANManager()
    try:
        mgr.add_port(vid, port_num, tagged)
        mode = "tagged" if tagged else "untagged"
        _ok(f"VLAN {vid}에 포트 {port_num} 추가 ({mode})")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@vlan.command("remove")
@click.argument("vid", type=int, metavar="VID")
@click.argument("port_num", type=int, metavar="PORT")
def vlan_remove(vid, port_num):
    """VLAN에서 포트를 제거한다."""
    mgr = VLANManager()
    try:
        mgr.remove_port(vid, port_num)
        _ok(f"VLAN {vid}에서 포트 {port_num} 제거")
    except Exception as e:
        _err(str(e))
        sys.exit(1)


@vlan.command("show")
@click.argument("vid", type=int, required=False, metavar="[VID]")
def vlan_show(vid):
    """VLAN 상태를 출력한다."""
    mgr = VLANManager()
    try:
        vlans = mgr.show(vid)
    except Exception as e:
        _err(str(e))
        sys.exit(1)

    _header("VLAN 상태")
    if not vlans:
        click.echo("  (설정된 VLAN 없음)")
        return

    for v_id, entry in sorted(vlans.items()):
        click.echo(
            f"\n  VLAN {click.style(str(v_id), bold=True):>6}  "
            f"({entry.name})"
        )
        if entry.tagged_ports:
            click.echo(f"    Tagged   : {entry.tagged_ports}")
        if entry.untagged_ports:
            click.echo(f"    Untagged : {entry.untagged_ports}")


# ─── show 커맨드 그룹 ─────────────────────────────────────────────────────────

@wedge.group()
def show():
    """스위치 종합 상태 조회."""
    pass


@show.command("ports")
def show_ports():
    """전체 포트 상태를 출력한다 (wedge port show 와 동일)."""
    ctx = click.get_current_context()
    ctx.invoke(port_show, port_num=None)


@show.command("hardware")
def show_hardware():
    """FAN, PSU, 온도를 종합 출력한다."""
    hw = HWManager()
    try:
        health = hw.get_system_health()
    except Exception as e:
        _err(f"하드웨어 상태 조회 실패: {e}")
        sys.exit(1)

    overall_color = "green" if health["overall"] == "OK" else "red"
    _header(f"시스템 상태: {click.style(health['overall'], fg=overall_color, bold=True)}")

    # 온도
    click.echo("\n  [온도 센서]")
    for t in health["temperatures"]:
        status_color = {"OK": "green", "WARNING": "yellow", "CRITICAL": "red"}.get(t["status"], "white")
        click.echo(
            f"    {t['label']:<25} {t['celsius']:>5.1f}°C  "
            f"{click.style(t['status'], fg=status_color)}"
        )

    # 팬
    click.echo("\n  [FAN]")
    for f in health["fans"]:
        present_str = click.style("OK", fg="green") if f["present"] else click.style("ABSENT", fg="red")
        click.echo(f"    FAN{f['id']}   {f['rpm_front']:>6} RPM   {present_str}")

    # PSU
    click.echo("\n  [PSU]")
    for p in health["psus"]:
        ok_str = click.style("OK", fg="green") if p["power_ok"] else click.style("FAIL", fg="red")
        pres_str = "Present" if p["present"] else "Absent"
        click.echo(f"    PSU{p['id']}   {pres_str:<10}  {ok_str}")


@show.command("fans")
def show_fans():
    """팬 상태를 출력한다."""
    hw = HWManager()
    fans = hw.get_fan_status()
    _header("FAN 상태")
    click.echo(f"{'FAN':>5}  {'전면 RPM':>10}  {'후면 RPM':>10}  {'듀티':>6}  상태")
    click.echo("─" * 46)
    for f in fans:
        ok = click.style("OK    ", fg="green") if f.present else click.style("ABSENT", fg="red")
        click.echo(f"  FAN{f.fan_id}  {f.rpm_front:>10,}  {f.rpm_rear:>10,}  {f.duty_pct:>5}%  {ok}")


@show.command("temperature")
def show_temperature():
    """온도 센서 상태를 출력한다."""
    hw = HWManager()
    temps = hw.get_temperatures()
    _header("온도 센서")
    for t in temps:
        color = {"OK": "green", "WARNING": "yellow", "CRITICAL": "red"}.get(t.status, "white")
        click.echo(
            f"  {t.label:<30} {t.celsius:>6.1f}°C  "
            f"{click.style(t.status, fg=color)}"
        )


@show.command("psu")
def show_psu():
    """PSU 상태를 출력한다."""
    hw = HWManager()
    psus = hw.get_psu_status()
    _header("PSU 상태")
    for p in psus:
        ok_str = click.style("OK", fg="green") if p.power_ok else click.style("FAIL", fg="red")
        pres_str = "Present" if p.present else click.style("Absent", fg="yellow")
        click.echo(f"  PSU{p.psu_id}  {pres_str:<10}  Power: {ok_str}")


@show.command("qsfp")
@click.argument("port_num", type=int, required=False, metavar="[PORT]")
def show_qsfp(port_num):
    """QSFP 트랜시버 정보를 출력한다."""
    hw = HWManager()
    qsfps = hw.get_qsfp_info(port_num)
    _header("QSFP 트랜시버")
    for q in qsfps:
        pres = click.style("Present", fg="green") if q.present else click.style("Absent", fg="bright_black")
        click.echo(f"\n  포트 {q.fp_port:>2}  {pres}")
        if q.present:
            click.echo(f"    벤더    : {q.vendor or '-'}")
            click.echo(f"    파트번호: {q.part_number or '-'}")
            click.echo(f"    시리얼  : {q.serial or '-'}")
            click.echo(f"    타입    : {q.connector_type or '-'}")
            if q.temperature is not None:
                click.echo(f"    온도    : {q.temperature:.1f}°C")
            if q.tx_power_dbm is not None:
                click.echo(f"    TX 파워 : {q.tx_power_dbm:.2f} dBm")
            if q.rx_power_dbm is not None:
                click.echo(f"    RX 파워 : {q.rx_power_dbm:.2f} dBm")


@show.command("version")
def show_version():
    """소프트웨어 버전 정보를 출력한다."""
    _header("버전 정보")
    click.echo("  wedge100-nos  v0.1.0")
    click.echo("  대상 하드웨어  : Accton Wedge 100 (32x100G)")
    click.echo("  BCM ASIC      : Broadcom BCM56960 (Tomahawk)")
    click.echo("  BMC 펌웨어    : OpenBMC v14.1")
    click.echo("  accton.zip 기반으로 구축됨")


# ─── 진입점 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    wedge()
