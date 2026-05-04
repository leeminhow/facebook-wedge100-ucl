#!/usr/bin/env python3
"""
snmp_agents/port_status.py
---------------------------
net-snmp 'extend' 방식으로 포트 상태를 SNMP로 노출.

/etc/snmp/snmpd.conf 에 아래 줄 추가:
  extend wedgePortStatus /usr/local/wedge100-nos/snmp_agents/port_status.py

OID: .1.3.6.1.4.1.8072.1.3.2.4.1.2.{len}.{ascii}.{index}
snmpwalk -v2c -c public localhost NET-SNMP-EXTEND-MIB::nsExtendOutput2Table

출력 형식 (한 줄에 포트 하나):
  PORT=1 CE=ce29 LINK=UP SPEED=100G LANES=4
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, "/usr/local/wedge100-nos")

try:
    from wedge100.managers.port import PortManager
    mgr = PortManager()
    statuses = mgr.get_status()
    for s in statuses:
        link = "UP" if s.link else "DOWN"
        speed = s.speed or "NONE"
        print(f"PORT={s.fp_port} CE={s.ce_name} LINK={link} SPEED={speed} LANES={s.lanes}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
