#!/usr/bin/env python3
"""
scripts/shutdown.py
-------------------
Wedge 100 NOS 종료 시 정리 작업.
systemd ExecStop 으로 호출됨.
"""

import logging
import sys
import subprocess

sys.path.insert(0, "/usr/local/wedge100-nos")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("shutdown")


def main():
    log.info("Wedge 100 NOS 종료 중...")

    # LED 전체 OFF
    try:
        from wedge100.managers.led import LEDManager
        led = LEDManager()
        led.set_all("off")
        log.info("  ✓ LED 전체 OFF")
    except Exception as e:
        log.warning("  LED OFF 실패: %s", e)

    # bcm.user 종료 (선택적 - ONL 재부팅 시 필요)
    # subprocess.run(["pkill", "-f", "bcm.user"], capture_output=True)

    log.info("✓ 종료 완료")


if __name__ == "__main__":
    main()
