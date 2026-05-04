"""
wedge100/config.py
------------------
Wedge 100 (32x100G) 전역 상수 및 포트 매핑 테이블.

포트 매핑 출처: bin/config.bcm, bin/port_map (accton.zip)
  - Front Panel Port 1..32  ↔  Broadcom CE channel index 0..31
  - 4개 Tile (Tile 0~3), 각 8포트

BCE 채널(ce)은 BCM SDK/SOC 커맨드에서 사용하는 포트 이름이다.
  예) ce0 = Front Panel Port 6
      ce29 = Front Panel Port 1
"""

# ─── netserve 연결 정보 ────────────────────────────────────────────────────────
NETSERVE_HOST = "127.0.0.1"
NETSERVE_PORT = 9090
NETSERVE_PROMPT = "BCM.0> "
NETSERVE_TIMEOUT = 10      # 초
NETSERVE_RETRIES = 3

# ─── 경로 ─────────────────────────────────────────────────────────────────────
ACCTON_BASE    = "/usr/local/accton"
BIN_DIR        = f"{ACCTON_BASE}/bin"
SOC_LED_DIR    = BIN_DIR                     # *.soc 파일 위치
QSFP_EEPROM_BIN = f"{BIN_DIR}/wedge100_qsfp_eeprom"
VLAN_STATE_FILE = "/var/lib/wedge100-nos/vlan_state.json"
LOG_FILE        = "/var/log/wedge100-nos.log"

# ─── Front Panel Port → CE 채널 매핑 ──────────────────────────────────────────
# config.bcm 주석 기준:
#   "Front panel port N lane 1 is at logical port L (ceX)"
# Tile 0: FP 1-4 (물리 배치상 ce28-31), FP 5-12 (ce0-7)
# Tile 1: FP 13-20  (ce8-15)
# Tile 2: FP 21-28  (ce16-23)
# Tile 3: FP 29-32  (ce24-27)  + FP 1-4 상단 ce28-31

FP_TO_CE: dict[int, int] = {
    1: 29,   2: 28,   3: 31,   4: 30,
    5:  1,   6:  0,   7:  3,   8:  2,
    9:  5,  10:  4,  11:  7,  12:  6,
   13:  9,  14:  8,  15: 11,  16: 10,
   17: 13,  18: 12,  19: 15,  20: 14,
   21: 17,  22: 16,  23: 19,  24: 18,
   25: 21,  26: 20,  27: 23,  28: 22,
   29: 25,  30: 24,  31: 27,  32: 26,
}

CE_TO_FP: dict[int, int] = {v: k for k, v in FP_TO_CE.items()}

ALL_FP_PORTS: list[int] = list(range(1, 33))   # 1..32
ALL_CE_CHANNELS: list[int] = list(range(0, 32)) # ce0..ce31

# ─── 포트 속도 정의 ───────────────────────────────────────────────────────────
# (SOC speed 값, 레인 수)
SPEED_MAP: dict[str, tuple[int, int]] = {
    "100G":  (100000, 4),
    "40G":   (40000,  4),
    "50G":   (50000,  2),
    "25G":   (25000,  1),
    "10G":   (10000,  1),
}

# ─── Breakout 모드 ─────────────────────────────────────────────────────────────
# 키: 사용자 입력 문자열
# 값: (서브포트 수, 각 서브포트 속도, 레인 수)
BREAKOUT_MAP: dict[str, tuple[int, str, int]] = {
    "1x100G": (1, "100G", 4),
    "2x50G":  (2, "50G",  2),
    "4x25G":  (4, "25G",  1),
    "4x10G":  (4, "10G",  1),
    "1x40G":  (1, "40G",  4),
}

# ─── LED 색상 → .soc 파일 ──────────────────────────────────────────────────────
LED_SOC_FILES: dict[str, str] = {
    "green":  f"{BIN_DIR}/12_bits_LED_GREEN.soc",
    "blue":   f"{BIN_DIR}/12_bits_LED_BLUE.soc",
    "red":    f"{BIN_DIR}/12_bits_LED_RED.soc",
    "yellow": f"{BIN_DIR}/12_bits_LED_YELLOW.soc",
    "purple": f"{BIN_DIR}/12_bits_LED_PURPLE.soc",
    "aqua":   f"{BIN_DIR}/12_bits_LED_AQUA.soc",
    "off":    f"{BIN_DIR}/12_bits_LED_OFF.soc",
}

# 속도별 자동 LED 색상 (speed-mode 명령용)
SPEED_LED_COLOR: dict[str, str] = {
    "100G": "green",
    "50G":  "aqua",
    "40G":  "blue",
    "25G":  "yellow",
    "10G":  "purple",
    "down": "off",
}

# ─── FEC 설정 파일 ────────────────────────────────────────────────────────────
FEC_DIR = f"{BIN_DIR}/bcm_fec"

# ─── CAUI 설정 파일 ──────────────────────────────────────────────────────────
CAUI_DIR = f"{BIN_DIR}/bcm_caui"

# ─── BMC / 하드웨어 sysfs 경로 ───────────────────────────────────────────────
# Wedge100에서 ONL 기준 실제 경로 (커널 버전에 따라 달라질 수 있음)
FAN_SYSFS_PATTERNS = [
    "/sys/bus/i2c/devices/*/fan*_input",          # hwmon via i2c
    "/sys/class/hwmon/hwmon*/fan*_input",
]
TEMP_SYSFS_PATTERNS = [
    "/sys/bus/i2c/drivers/lm75/*/temp1_input",
    "/sys/bus/i2c/devices/*/temp1_input",
]
PSU_I2C_BUS = 7
PSU_MUX_ADDR = 0x70

# ─── QSFP 관련 ───────────────────────────────────────────────────────────────
QSFP_EEPROM_SYSFS = "/sys/bus/i2c/devices/{bus}-{addr:04x}/eeprom"
# Wedge100 QSFP I2C 버스 매핑 (포트 1-16: 버스 2-17, 17-32: 버스 18-33 추정)
# 실제 하드웨어에서 확인 필요
QSFP_I2C_BASE_BUS = 2

# ─── 유틸리티 ─────────────────────────────────────────────────────────────────
def validate_fp_port(port: int) -> None:
    """Front Panel 포트 번호 유효성 검사."""
    if port not in FP_TO_CE:
        raise ValueError(f"유효하지 않은 포트 번호: {port} (범위: 1-32)")

def fp_to_ce_name(port: int) -> str:
    """Front Panel 포트 번호 → 'ceN' 문자열 반환."""
    validate_fp_port(port)
    return f"ce{FP_TO_CE[port]}"

def ce_name_to_fp(ce_name: str) -> int:
    """'ceN' 문자열 → Front Panel 포트 번호 반환."""
    idx = int(ce_name.replace("ce", ""))
    return CE_TO_FP[idx]
