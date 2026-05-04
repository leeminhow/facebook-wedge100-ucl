#!/usr/bin/env python3
"""
scripts/startup.py
------------------
Wedge 100 NOS 초기화 데몬.

부팅 순서:
  1. BCM 커널 모듈 로드 (linux-kernel-bde.ko, linux-user-bde.ko)
  2. bcm.user + netserve 백그라운드 실행
  3. rc.soc 로드 → ASIC 포트 초기화
  4. LED 초기화 (모두 OFF)
  5. VLAN 상태 복구 (JSON → ASIC 재적용)
  6. SNMP 데몬 시작 확인

systemd 서비스로 등록하여 사용:
  sudo systemctl enable wedge100-nos
  sudo systemctl start wedge100-nos

또는 직접 실행:
  sudo python3 /usr/local/wedge100-nos/scripts/startup.py
"""

import logging
import os
import subprocess
import sys
import time

# 프로젝트 루트를 path에 추가
sys.path.insert(0, "/usr/local/wedge100-nos")

from wedge100.config import ACCTON_BASE, BIN_DIR
from wedge100.bcm.sdk import BCMSdk, BCMError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/var/log/wedge100-nos.log"),
    ],
)
log = logging.getLogger("startup")

# ── 경로 상수 ──────────────────────────────────────────────────────────────────
KERNEL_BDE  = f"{BIN_DIR}/linux-kernel-bde.ko"
USER_BDE    = f"{BIN_DIR}/linux-user-bde.ko"
BCM_USER    = f"{BIN_DIR}/bcm.user"
RC_SOC      = f"{BIN_DIR}/rc.soc"
NETSERVE    = f"{BIN_DIR}/netserve"
LED_OFF_SOC = f"{BIN_DIR}/12_bits_LED_OFF.soc"

NETSERVE_PORT = 9090
NETSERVE_READY_WAIT = 15   # bcm.user 초기화 대기 시간 (초)


# ── 단계별 초기화 함수 ─────────────────────────────────────────────────────────

def step_load_kernel_modules() -> bool:
    """BCM BDE 커널 모듈 로드."""
    log.info("[1/6] BCM 커널 모듈 로드 중...")
    for mod_path in [KERNEL_BDE, USER_BDE]:
        if not os.path.isfile(mod_path):
            log.error("  모듈 파일 없음: %s", mod_path)
            return False

        mod_name = os.path.basename(mod_path).replace(".ko", "")
        # 이미 로드됐는지 확인
        result = subprocess.run(["lsmod"], capture_output=True, text=True)
        if mod_name in result.stdout:
            log.info("  %s 이미 로드됨 (스킵)", mod_name)
            continue

        ret = subprocess.run(
            ["insmod", mod_path],
            capture_output=True, text=True
        )
        if ret.returncode != 0:
            log.error("  %s 로드 실패: %s", mod_path, ret.stderr.strip())
            return False
        log.info("  ✓ %s 로드 완료", mod_name)

    return True


def step_start_bcm_user() -> bool:
    """bcm.user를 백그라운드로 실행하고 netserve 대기."""
    log.info("[2/6] BCM SDK (bcm.user) 시작 중...")

    if not os.path.isfile(BCM_USER):
        log.error("  bcm.user 없음: %s", BCM_USER)
        return False

    # 이미 실행 중인지 확인
    result = subprocess.run(["pgrep", "-f", "bcm.user"], capture_output=True)
    if result.returncode == 0:
        log.info("  bcm.user 이미 실행 중 (스킵)")
        return True

    # rc.soc 경로를 인자로 전달 (-rcload 또는 직접 경로)
    proc = subprocess.Popen(
        [BCM_USER, "-rcload", RC_SOC],
        cwd=BIN_DIR,
        stdout=open("/var/log/bcm_user.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.info("  bcm.user PID=%d 시작됨", proc.pid)
    log.info("  ASIC 초기화 대기 중 (%d초)...", NETSERVE_READY_WAIT)
    time.sleep(NETSERVE_READY_WAIT)

    # netserve 포트 응답 확인
    for attempt in range(10):
        try:
            with BCMSdk() as sdk:
                resp = sdk.cmd("version")
                log.info("  ✓ netserve 응답 확인: %s", resp[:60].strip())
                return True
        except BCMError:
            log.info("  netserve 대기 중... (%d/10)", attempt + 1)
            time.sleep(2)

    log.error("  netserve 응답 없음. bcm.user 로그 확인: /var/log/bcm_user.log")
    return False


def step_load_rc_soc() -> bool:
    """
    rc.soc 을 통한 포트 초기화는 bcm.user 시작 시 자동으로 수행됨.
    여기서는 추가 SOC 커맨드만 실행한다.
    """
    log.info("[3/6] 추가 SOC 초기화 커맨드 실행 중...")
    try:
        with BCMSdk() as sdk:
            # 전체 포트 상태 한 번 확인
            out = sdk.cmd("ps ce")
            up_count = out.count(" up ")
            log.info("  ✓ 포트 상태 확인: %d개 포트 UP", up_count)
        return True
    except BCMError as e:
        log.error("  SOC 커맨드 실패: %s", e)
        return False


def step_init_leds() -> bool:
    """LED 초기화 (전체 OFF 후 속도-모드 적용)."""
    log.info("[4/6] LED 초기화 중...")
    try:
        from wedge100.bcm.sdk import run_soc_file
        if os.path.isfile(LED_OFF_SOC):
            run_soc_file(LED_OFF_SOC)
            log.info("  ✓ 전체 LED OFF 완료")
        else:
            log.warning("  LED OFF SOC 파일 없음: %s", LED_OFF_SOC)
        return True
    except Exception as e:
        log.warning("  LED 초기화 경고 (치명적이지 않음): %s", e)
        return True   # LED 실패는 치명적이지 않음


def step_restore_vlan() -> bool:
    """저장된 VLAN 설정을 ASIC에 재적용."""
    log.info("[5/6] VLAN 상태 복구 중...")
    try:
        from wedge100.managers.vlan import VLANManager
        mgr = VLANManager()
        mgr.replay_to_asic()
        log.info("  ✓ VLAN 복구 완료")
        return True
    except Exception as e:
        log.warning("  VLAN 복구 경고: %s", e)
        return True


def step_check_snmpd() -> bool:
    """snmpd 실행 확인 및 설정 적용."""
    log.info("[6/6] SNMP 데몬 확인 중...")
    result = subprocess.run(["pgrep", "snmpd"], capture_output=True)
    if result.returncode != 0:
        # snmpd 시작 시도
        ret = subprocess.run(
            ["systemctl", "start", "snmpd"],
            capture_output=True, text=True
        )
        if ret.returncode == 0:
            log.info("  ✓ snmpd 시작됨")
        else:
            log.warning("  snmpd 시작 실패 (SNMP 기능 비활성화)")
    else:
        log.info("  ✓ snmpd 이미 실행 중")
    return True


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("Wedge 100 NOS 초기화 시작")
    log.info("=" * 60)

    steps = [
        ("커널 모듈 로드",      step_load_kernel_modules),
        ("BCM SDK 시작",        step_start_bcm_user),
        ("SOC 초기화 확인",     step_load_rc_soc),
        ("LED 초기화",          step_init_leds),
        ("VLAN 상태 복구",      step_restore_vlan),
        ("SNMP 데몬 확인",      step_check_snmpd),
    ]

    failed = False
    for name, fn in steps:
        try:
            ok = fn()
        except Exception as e:
            log.error("단계 '%s' 예외: %s", name, e)
            ok = False

        if not ok:
            log.error("!!! 단계 실패: %s", name)
            failed = True
            break

    if failed:
        log.error("초기화 실패. 로그를 확인하세요.")
        sys.exit(1)
    else:
        log.info("=" * 60)
        log.info("✓ Wedge 100 NOS 초기화 완료")
        log.info("  CLI: wedge --help")
        log.info("  SNMP: snmpwalk -v2c -c public localhost \\")
        log.info("          NET-SNMP-EXTEND-MIB::nsExtendOutput2Table")
        log.info("=" * 60)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("오류: root 권한으로 실행하세요 (sudo python3 startup.py)")
        sys.exit(1)
    main()
