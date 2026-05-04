# Facebook Wedge100-32X User Control Layer
Turn your dust-collecting Facebook Wedge100 32X at home or the office into a half-functional 100G switch for your homelab.

A lightweight experimental Network Operating System for the **Accton / Facebook Wedge100** built directly on top of the **Broadcom BCM56960 diagnostic runtime**.
This project provides a practical standalone control plane for home lab and experimental deployments without requiring a full SONiC / FBOSS stack.

**Why?)** The wedge100**BF**-32X which is equipped with the Intel Barefoot Tofino, has reliable SONiC support. However, the wedge100-32X, featuring the Broadcom Tomahawk ASIC, has very poor SONiC support, and the ONL + FBOSS combination is also unsuitable for use as a standalone network switch.

**How?)** Edgecore provides the Accton Diag OS for testing the wedge100-32x. This file includes a command set for controlling most of the BCM56960 ASIC, and allows testing or reading of components such as the FAN, LED (Addressable RGB LED), and PSU. The goal is to use this to enable control via the CLI or to smoothly manage the web UI, just like a typical data center network switch.



---

## Overview

Wedge100 NOS is designed for users who want to run the Wedge100 as a fully manageable standalone switch using:

* Port configuration
* VLAN management
* LED control
* Hardware telemetry
* Web-based management UI
* Python CLI/API control

Instead of implementing a full switch abstraction layer, this project directly wraps the Broadcom SDK diagnostic environment.

Architecture:

```text
WebUI
  ↓
PHP API
  ↓
wedge CLI
  ↓
Python managers
  ↓
netserve
  ↓
bcm.user
  ↓
BCM56960 ASIC
```

---

## Features

### Port Management

* Enable / disable ports
* Speed configuration
* Breakout mode
* FEC configuration
* Link state monitoring

### VLAN

* VLAN creation / deletion
* Tagged / untagged membership
* Port VLAN assignment

### LED Control

* Port LED state control
* Activity indication
* Link visualization

### Hardware Monitoring

* Temperature monitoring
* Fan RPM
* Platform telemetry
* Sensor health status

### Web Management

* Port map visualization
* Real-time status updates
* Hardware health dashboard
* Operational controls

### Backend Reliability

* BCM command serialization
* Hardware state verification
* Health monitoring
* Startup self-test
* Structured logging

---

## Hardware Support

Currently targeted hardware:

* **Accton AS5712-54X**
* **Facebook Wedge100**
* Broadcom **BCM56960 Tomahawk**

This project is tightly optimized for this platform.

It is **not intended to be a generic NOS**.

---

## Requirements

### Runtime Environment

Recommended:

* Accton diagnostic image

Supported with manual setup:

* Open Network Linux (ONL)

---

### Required Components

Broadcom runtime:

* `linux-kernel-bde.ko`
* `linux-user-bde.ko`
* `bcm.user`
* `netserve`

Platform files:

* `config.bcm`
* `rc.soc`
* LED microcode

---

## Installation

### 1. Load Broadcom modules

```bash
insmod linux-kernel-bde.ko
insmod linux-user-bde.ko
```

---

### 2. Start BCM runtime

```bash
./bcm.user
```

---

### 3. Start netserve

```bash
./netserve
```

---

### 4. Install Python backend

```bash
pip3 install -r requirements.txt
```

---

### 5. Start backend

```bash
python3 startup.py
```

---

### 6. Launch WebUI

Configure Apache / PHP and point document root to:

```text
webui/
```

---

## Usage

### CLI

Port control:

```bash
wedge port enable 1
wedge port disable 1
```

Set speed:

```bash
wedge port speed 1 100G
```

Configure VLAN:

```bash
wedge vlan create 100
wedge vlan add 100 1 tagged
```

LED control:

```bash
wedge led set 1 green
```

System health:

```bash
wedge health
```

---

### WebUI

Available after deployment:

```text
http://<switch-ip>/
```

Provides:

* Port dashboard
* VLAN configuration
* Hardware telemetry
* Health monitoring
* System diagnostics

---

## Startup Flow

```text
Boot
 ↓
Load BDE modules
 ↓
Start bcm.user
 ↓
Start netserve
 ↓
Startup self-test
 ↓
Backend initialization
 ↓
WebUI ready
```

---

## Reliability Design

This project prioritizes operational correctness.

Implemented safeguards:

### Command Serialization

All Broadcom commands are globally serialized.

---

### Hardware State Verification

Configuration changes are verified against actual ASIC state before commit.

---

### Health Monitoring

Backend continuously validates:

* BCM responsiveness
* netserve availability
* Sensor access
* Database integrity

---

### Stale State Detection

Cached hardware state includes TTL validation.

---

## Logging

Logs:

```text
/var/log/wedge100-nos.log
```

Includes:

* Commands executed
* Hardware responses
* Timing
* Errors
* Health events

---

## Development Philosophy

This is intentionally **not SONiC**.

Instead of:

* Redis orchestration
* Large daemon ecosystems
* Heavy abstraction layers

This project favors:

* Direct hardware control
* Minimal latency
* Platform-specific optimization
* Practical home lab usability

Think of it as:

**Broadcom diag runtime with a modern control plane.**

---

## Limitations

Current constraints:

* Single-platform support
* Broadcom diagnostic runtime dependency
* No distributed control plane
* Experimental BGP / mirror support

---

## Roadmap

Planned improvements:

* Improved telemetry
* Better optical diagnostics
* FRR integration refinement
* Enhanced WebUI analytics
* Safer startup validation
* Configuration persistence improvements

---

## Contributing

Contributions are welcome, especially for:

* BCM56960 platform refinement
* Hardware telemetry improvements
* WebUI enhancements
* Stability fixes

---

## Disclaimer

This software directly manipulates switch ASIC state.

Incorrect configuration may:

* Disrupt forwarding
* Disable ports
* Misconfigure LEDs
* Affect thermal management

Use on production systems at your own risk.

---

## License

MIT License

---

## Acknowledgements

Built on top of:

* Accton diagnostic runtime
* Broadcom SDK tools
* Open Network Linux
* The Wedge100 hardware platform

---

## Status

**Experimental but functional**

Suitable for:

* Home labs
* Reverse engineering
* Platform experimentation
* Educational use

Not yet recommended for production deployment.
