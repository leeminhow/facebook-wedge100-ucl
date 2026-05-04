#!/usr/bin/env python3
"""
snmp_agents/temperature.py
--------------------------
온도 센서를 SNMP extend로 노출.

/etc/snmp/snmpd.conf:
  extend wedgeTemperature /usr/local/wedge100-nos/snmp_agents/temperature.py

출력 형식:
  SENSOR=1 LABEL=Switch_ASIC_Near CELSIUS=42.5 STATUS=OK
"""

import sys
sys.path.insert(0, "/usr/local/wedge100-nos")

try:
    from wedge100.managers.hw import HWManager
    hw = HWManager()
    temps = hw.get_temperatures()
    for t in temps:
        label = t.label.replace(" ", "_")
        print(f"SENSOR={t.sensor_id} LABEL={label} CELSIUS={t.celsius:.1f} STATUS={t.status}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
