#!/usr/bin/env python3
"""
snmp_agents/psu_status.py
-------------------------
PSU 상태를 SNMP extend로 노출.

/etc/snmp/snmpd.conf:
  extend wedgePsuStatus /usr/local/wedge100-nos/snmp_agents/psu_status.py

출력 형식:
  PSU=1 PRESENT=YES POWER_OK=YES
"""

import sys
sys.path.insert(0, "/usr/local/wedge100-nos")

try:
    from wedge100.managers.hw import HWManager
    hw = HWManager()
    psus = hw.get_psu_status()
    for p in psus:
        present = "YES" if p.present else "NO"
        power_ok = "YES" if p.power_ok else "NO"
        print(f"PSU={p.psu_id} PRESENT={present} POWER_OK={power_ok}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
