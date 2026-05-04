# wedge100/__init__.py
"""
wedge100-nos
────────────
Accton Wedge 100 (32x100G, BCM Tomahawk) 홈랩용 NOS.

주요 모듈:
  wedge100.bcm.sdk          → BCM netserve 소켓 통신
  wedge100.bcm.soc_commands → SOC 커맨드 문자열 빌더
  wedge100.managers.port    → 포트 설정/상태 관리
  wedge100.managers.led     → LED 색상 제어
  wedge100.managers.vlan    → VLAN 관리
  wedge100.managers.hw      → FAN/PSU/온도/QSFP 관리
  wedge100.cli.main         → Click CLI 진입점
"""

__version__ = "0.1.0"
__author__  = "wedge100-nos contributors"
