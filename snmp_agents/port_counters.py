#!/usr/bin/env python3
"""
snmp_agents/port_counters.py
-----------------------------
포트 TX/RX 카운터를 SNMP extend로 노출.

/etc/snmp/snmpd.conf:
  extend wedgePortCounters /usr/local/wedge100-nos/snmp_agents/port_counters.py

출력 형식:
  PORT=1 RX_PKT=100000 TX_PKT=99000 RX_BYTES=128000000 TX_BYTES=126000000 RX_ERR=0 TX_ERR=0
"""

import sys
sys.path.insert(0, "/usr/local/wedge100-nos")

try:
    from wedge100.managers.port import PortManager
    from wedge100.config import ALL_FP_PORTS
    mgr = PortManager()
    for port in ALL_FP_PORTS:
        try:
            c = mgr.get_counters(port)
            print(
                f"PORT={port} "
                f"RX_PKT={c['rx_packets']} TX_PKT={c['tx_packets']} "
                f"RX_BYTES={c['rx_bytes']} TX_BYTES={c['tx_bytes']} "
                f"RX_ERR={c['rx_errors']} TX_ERR={c['tx_errors']}"
            )
        except Exception:
            print(f"PORT={port} RX_PKT=0 TX_PKT=0 RX_BYTES=0 TX_BYTES=0 RX_ERR=0 TX_ERR=0")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
