#!/usr/bin/env python3
"""
snmp_agents/fan_speed.py
------------------------
FAN RPM을 SNMP extend로 노출.

/etc/snmp/snmpd.conf:
  extend wedgeFanSpeed /usr/local/wedge100-nos/snmp_agents/fan_speed.py

출력 형식:
  FAN=1 FRONT_RPM=12500 REAR_RPM=11800 DUTY=80 PRESENT=YES
"""

import sys
sys.path.insert(0, "/usr/local/wedge100-nos")

try:
    from wedge100.managers.hw import HWManager
    hw = HWManager()
    fans = hw.get_fan_status()
    for f in fans:
        present = "YES" if f.present else "NO"
        print(f"FAN={f.fan_id} FRONT_RPM={f.rpm_front} REAR_RPM={f.rpm_rear} "
              f"DUTY={f.duty_pct} PRESENT={present}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
