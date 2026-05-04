# wedge100-nos

**Accton Wedge 100 (32×100G) 홈랩용 NOS**

ONL(Open Network Linux) 위에서 동작하는 경량 CLI 기반 스위치 제어 도구.  
Facebook/Accton 진단 패키지(`accton.zip`)의 BCM SDK를 재활용해 구현했다.

---

## 지원 기능

| 기능 | 상태 | 설명 |
|------|------|------|
| 포트 속도 설정 | ✅ | 100G / 40G / 50G / 25G / 10G |
| Breakout | ✅ | 1x100G / 2x50G / 4x25G / 4x10G |
| FEC (RS-FEC CL91) | ✅ | 포트별 ON / OFF |
| 포트 Enable/Disable | ✅ | |
| 포트 TX/RX 카운터 | ✅ | 조회 및 초기화 |
| QSFP 트랜시버 정보 | ✅ | 벤더, 파트번호, DOM |
| LED 제어 | ✅ | 전체 / 포트별 / 속도-모드 자동 |
| VLAN | ✅ | 생성/삭제, 포트 추가/제거, 상태 영속화 |
| FAN 모니터링 | ✅ | RPM, 듀티 사이클 |
| 온도 모니터링 | ✅ | lm75 7개 센서 |
| PSU 상태 | ✅ | Present / Power OK |
| SNMP | ✅ | net-snmp extend 방식 |

---

## 아키텍처

```
[ wedge CLI ] ←── Click 기반 명령어 인터페이스
      │
      ▼
[ managers/ ]   port.py / led.py / vlan.py / hw.py
      │
      ▼
[ bcm/sdk.py ]  TCP 소켓 → netserve (port 9090)
      │
      ▼
[ bcm.user + netserve ]   Broadcom SDK (accton.zip 바이너리)
      │
      ▼
[ BCM56960 Tomahawk ASIC ]  32×100G QSFP28
```

**핵심 원리:** `bcm.user`가 ASIC을 초기화하고 `netserve`를 통해 TCP 소켓으로  
SOC 셸을 노출한다. 이 프로젝트는 해당 소켓에 SOC 커맨드를 전송해 스위치를 제어한다.

---

## 사전 조건

| 항목 | 요구사항 |
|------|----------|
| 하드웨어 | Accton Wedge 100 (32×100G, BCM56960) |
| OS | ONL (Open Network Linux) |
| Python | 3.10 이상 |
| 바이너리 | `accton.zip` → `/usr/local/accton/` 압축 해제 |
| 패키지 | `python3-click`, `snmpd` (net-snmp) |

---

## 설치

```bash
# 1. accton.zip 압축 해제
sudo unzip accton.zip -d /usr/local/accton

# 2. wedge100-nos 설치
git clone https://github.com/yourname/wedge100-nos
cd wedge100-nos
sudo bash install.sh

# 3. 서비스 시작 (bcm.user가 먼저 실행된 상태여야 함)
sudo systemctl start wedge100-nos

# 또는 직접 실행
sudo python3 scripts/startup.py
```

---

## CLI 사용법

### 포트 관리

```bash
# 전체 포트 상태 조회
wedge port show

# 특정 포트 상태
wedge port show 1

# 포트 속도 설정
wedge port set 1 speed 100G
wedge port set 5 speed 25G

# Breakout (100G → 4×25G)
wedge port breakout 1 4x25G

# Breakout 해제 (→ 1×100G)
wedge port breakout 1 1x100G

# 포트 활성화 / 비활성화
wedge port enable 1
wedge port disable 3

# FEC 설정
wedge port fec 1 on
wedge port fec 1 off

# 카운터 조회
wedge port counters 1

# 카운터 초기화
wedge port counters --clear
```

### LED 제어

```bash
# 전체 LED 색상 설정
wedge led set all green
wedge led set all off

# 특정 포트 LED
wedge led set 1 blue
wedge led set 5 red

# 속도-모드: 링크 속도에 따라 색상 자동 적용
#   100G → 초록 / 50G → 청록 / 40G → 파랑 / 25G → 노랑 / 10G → 보라 / DOWN → 소등
wedge led speed-mode

# 현재 LED 상태 확인
wedge led show
```

### VLAN 관리

```bash
# VLAN 생성
wedge vlan create 100
wedge vlan create 200 --name "서버망" --ports 1,2,3
wedge vlan create 300 --untagged-ports 5,6

# 포트 추가
wedge vlan add 100 4
wedge vlan add 100 7 --untagged

# 포트 제거
wedge vlan remove 100 4

# VLAN 목록 조회
wedge vlan show
wedge vlan show 100

# VLAN 삭제
wedge vlan delete 200
```

### 종합 상태 조회

```bash
# 전체 하드웨어 상태 (온도 + FAN + PSU)
wedge show hardware

# FAN 상태
wedge show fans

# 온도 센서
wedge show temperature

# PSU 상태
wedge show psu

# QSFP 트랜시버 정보
wedge show qsfp
wedge show qsfp 1

# 버전 정보
wedge show version
```

---

## SNMP 조회

설치 후 외부 서버에서 다음과 같이 조회한다:

```bash
# 포트 링크 상태 / 속도
snmpwalk -v2c -c public <스위치IP> \
  NET-SNMP-EXTEND-MIB::nsExtendOutput2Line."wedgePortStatus"

# FAN RPM
snmpwalk -v2c -c public <스위치IP> \
  NET-SNMP-EXTEND-MIB::nsExtendOutput2Line."wedgeFanSpeed"

# 온도
snmpwalk -v2c -c public <스위치IP> \
  NET-SNMP-EXTEND-MIB::nsExtendOutput2Line."wedgeTemperature"

# PSU
snmpwalk -v2c -c public <스위치IP> \
  NET-SNMP-EXTEND-MIB::nsExtendOutput2Line."wedgePsuStatus"

# 포트 카운터
snmpwalk -v2c -c public <스위치IP> \
  NET-SNMP-EXTEND-MIB::nsExtendOutput2Line."wedgePortCounters"
```

---

## 파일 구조

```
wedge100-nos/
├── wedge100/               # 메인 패키지
│   ├── config.py           # 포트 매핑, 경로, 상수
│   ├── bcm/
│   │   ├── sdk.py          # netserve TCP 소켓 래퍼
│   │   └── soc_commands.py # SOC 커맨드 문자열 빌더
│   ├── managers/
│   │   ├── port.py         # 포트 설정 / 상태 관리
│   │   ├── led.py          # LED 색상 제어
│   │   ├── vlan.py         # VLAN 관리 (JSON 영속화)
│   │   └── hw.py           # FAN / PSU / 온도 / QSFP
│   └── cli/
│       └── main.py         # Click CLI 진입점
├── snmp_agents/
│   ├── port_status.py      # SNMP extend: 포트 상태
│   ├── port_counters.py    # SNMP extend: 포트 카운터
│   ├── fan_speed.py        # SNMP extend: FAN RPM
│   ├── temperature.py      # SNMP extend: 온도
│   ├── psu_status.py       # SNMP extend: PSU 상태
│   └── snmpd_wedge100.conf # snmpd.conf 추가 설정
├── scripts/
│   ├── startup.py          # 부팅 초기화 (systemd ExecStart)
│   ├── shutdown.py         # 종료 정리 (systemd ExecStop)
│   └── wedge100-nos.service # systemd 유닛 파일
├── install.sh              # 설치 스크립트
├── pyproject.toml          # 패키지 메타데이터
└── README.md
```

---

## 포트 번호 체계

Front Panel 포트 1-32가 BCM CE 채널(ce0-ce31)에 매핑된다:

```
FP Port 1  → ce29    FP Port 2  → ce28
FP Port 5  → ce1     FP Port 6  → ce0
FP Port 13 → ce9     FP Port 14 → ce8
...
```

`wedge port show` 출력에서 양쪽 번호를 모두 표시한다.

---

## 향후 계획

- [ ] BGP 라우팅 (FRRouting 연동)
- [ ] LACP / 포트 본딩
- [ ] ACL (BCM FP 규칙)
- [ ] sFlow / NetFlow 샘플링
- [ ] Web 대시보드 (간단한 Flask UI)
- [ ] LLDP 이웃 정보 조회
- [ ] 포트 미러링 (SPAN)

---

## 라이센스

MIT License. BCM SDK 바이너리(`bcm.user`, `netserve` 등)는 Broadcom/Accton 소유이며  
이 프로젝트에 포함되지 않는다. `accton.zip`을 별도로 준비해야 한다.
