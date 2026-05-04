<?php
// webui/index.php
// Wedge 100 NOS – WebUI (SX6036 스타일)
?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Wedge 100 NOS – Management Console</title>
<style>
/* ── 리셋 & 기본 ──────────────────────────────────────────────── */
*{box-sizing:border-box;margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;}
body{background:#fff;color:#333;font-size:12px;}
button{cursor:pointer;}

/* ── 최상단 헤더 ──────────────────────────────────────────────── */
.top-header{
  background:linear-gradient(to bottom,#5c1111,#a84444);
  height:60px;display:flex;justify-content:space-between;align-items:center;
  padding:0 20px;color:#fff;position:relative;overflow:hidden;
}
.top-header::before{
  content:"";position:absolute;top:0;left:20%;
  width:200px;height:100%;background:rgba(255,255,255,.05);transform:skewX(-45deg);
}
.logo-area{display:flex;align-items:center;gap:10px;z-index:1;}
.logo-icon{font-size:28px;font-weight:bold;letter-spacing:-2px;color:#fff;
  display:flex;align-items:baseline;font-family:'Times New Roman',serif;}
.logo-icon span{font-size:38px;margin-right:4px;}
.logo-text-main{font-size:20px;font-weight:bold;}
.logo-text-sub{font-size:9px;letter-spacing:1px;color:rgba(255,255,255,.75);}
.header-info{text-align:right;z-index:1;}
.header-title{font-size:15px;font-weight:bold;margin-bottom:4px;}
.user-info{font-size:11px;display:flex;gap:12px;justify-content:flex-end;align-items:center;}
.user-info span{font-weight:bold;}
.user-info a{color:#fff;text-decoration:none;opacity:.8;}
.user-info a:hover{opacity:1;text-decoration:underline;}

/* ── 상태 바 ──────────────────────────────────────────────────── */
.status-bar{
  background:#e8ecef;padding:4px 20px;font-size:11px;color:#444;
  display:flex;justify-content:space-between;align-items:center;
  border-bottom:1px solid #ccc;
}
.status-bar .icon-box{
  display:inline-block;width:14px;height:14px;background:#ddd;
  border:1px solid #999;vertical-align:middle;margin-right:4px;
  text-align:center;line-height:14px;font-weight:bold;font-size:10px;
}
.status-left,.status-right{display:flex;gap:20px;align-items:center;}

/* ── 탭 네비게이션 ────────────────────────────────────────────── */
.nav-tabs{
  background:linear-gradient(to bottom,#f9f9f9,#dcdcdc);
  display:flex;border-bottom:2px solid #a66666;flex-wrap:wrap;
}
.tab{
  padding:7px 16px;font-size:12px;cursor:pointer;color:#333;
  border-right:1px solid #ccc;border-top:1px solid #ddd;
  background:linear-gradient(to bottom,#fdfdfd,#e5e5e5);
  user-select:none;white-space:nowrap;
}
.tab:hover{background:linear-gradient(to bottom,#fff,#efefef);}
.tab.active{
  background:linear-gradient(to bottom,#eccfcf,#d8a7a7);
  border-top:2px solid #9d1717;color:#660000;font-weight:bold;
  border-bottom:2px solid #d8a7a7;margin-bottom:-2px;
}
.tab.disabled{color:#aaa;cursor:default;}

/* ── 섹션 헤더 ────────────────────────────────────────────────── */
.section-header{
  background:#9d1717;color:#fff;padding:5px 20px;font-size:12px;
  display:flex;justify-content:space-between;align-items:center;
}
.info-icon{
  display:inline-block;width:14px;height:14px;background:#fff;color:#9d1717;
  border-radius:50%;text-align:center;line-height:14px;font-size:10px;
  font-weight:bold;margin-left:6px;cursor:help;
}

/* ── 메인 레이아웃 ────────────────────────────────────────────── */
.main-layout{display:flex;min-height:calc(100vh - 160px);}
.sidebar{width:140px;background:#f4f4f4;border-right:1px solid #ddd;flex-shrink:0;}
.side-menu{list-style:none;padding:6px 0;}
.side-menu li{padding:7px 14px;cursor:pointer;color:#660000;font-size:12px;border-left:3px solid transparent;}
.side-menu li:hover{background:#e8e8e8;}
.side-menu li.active{background:#f5d6d6;border-left:3px solid #9d1717;font-weight:bold;}
.content-area{flex:1;padding:0;overflow:hidden;}

/* ── 스위치 하드웨어 패널 ────────────────────────────────────── */
.switch-container{padding:10px 16px 6px;}
.switch-hardware{
  background:linear-gradient(to bottom,#fdfdfd,#e0e0e0);
  border:2px solid #aaa;border-radius:6px;padding:10px 14px;
  box-shadow:0 3px 8px rgba(0,0,0,.15);position:relative;
}
.switch-grille-top,.switch-grille-bottom{
  height:5px;
  background-image:radial-gradient(#666 35%,transparent 36%);
  background-size:6px 6px;
  margin-bottom:4px;
}
.switch-grille-bottom{margin-top:4px;margin-bottom:0;}
.switch-content{display:flex;align-items:center;gap:10px;}
.switch-left-panel{display:flex;flex-direction:column;gap:4px;align-items:center;}
.rj45-stack{display:flex;flex-direction:column;gap:2px;}
.rj45{width:18px;height:14px;background:#222;border-radius:2px;border:1px solid #000;
  box-shadow:inset 0 2px 4px rgba(0,0,0,.8);}
.usb-port{width:6px;height:14px;background:#111;border:1px solid #444;border-radius:1px;}
.switch-ports-area{display:flex;flex-wrap:wrap;gap:4px;flex:1;}

/* ── 포트 블록 ────────────────────────────────────────────────── */
.port-block{display:flex;flex-direction:column;gap:2px;background:#e8e8e8;
  padding:3px;border-radius:3px;border:1px solid #ccc;}
.port-row{display:flex;gap:2px;}

/* ── QSFP 포트 아이콘 ─────────────────────────────────────────── */
.qsfp-port{
  width:36px;height:28px;background:#2a2a2a;border-radius:3px;
  border:1px solid #111;box-shadow:inset 0 2px 4px rgba(0,0,0,.7);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  cursor:pointer;position:relative;transition:border-color .15s;
  gap:2px;
}
.qsfp-port:hover{border-color:#9d1717;box-shadow:0 0 5px rgba(157,23,23,.5);}
.qsfp-port.link-up{border-color:#4a4a4a;}
.qsfp-port.selected{border:2px solid #ff4444;box-shadow:0 0 6px rgba(255,68,68,.6);}

/* ── 4-Lane LED 행 ────────────────────────────────────────────── */
.lane-leds{display:flex;gap:2px;}
.lane-led{
  width:6px;height:6px;border-radius:50%;background:#222;
  box-shadow:none;transition:background .2s,box-shadow .2s;
  border:1px solid #444;
}
.lane-led.green {background:#4CAF50;box-shadow:0 0 4px #4CAF50;}
.lane-led.aqua  {background:#00BCD4;box-shadow:0 0 4px #00BCD4;}
.lane-led.blue  {background:#2196F3;box-shadow:0 0 4px #2196F3;}
.lane-led.yellow{background:#FFC107;box-shadow:0 0 4px #FFC107;}
.lane-led.purple{background:#9C27B0;box-shadow:0 0 4px #9C27B0;}
.lane-led.red   {background:#f44336;box-shadow:0 0 4px #f44336;}
.lane-led.white {background:#fff;   box-shadow:0 0 5px #fff;}
.lane-led.off   {background:#222;   box-shadow:none;}
.lane-led.blink {animation:blink-anim .4s infinite;}

@keyframes blink-anim{0%,100%{opacity:1;}50%{opacity:.1;}}

/* ── 포트 번호 라벨 ───────────────────────────────────────────── */
.port-num{font-size:8px;color:#aaa;line-height:1;}
.port-speed-tag{font-size:7px;color:#777;line-height:1;}
.pull-tab{width:14px;height:3px;background:#cddc39;border-radius:1px;margin-top:2px;}

/* ── 포트 번호 레이블 아래쪽 ──────────────────────────────────── */
.port-labels{display:flex;flex-wrap:wrap;gap:4px;padding:2px 3px;}
.port-label-block{display:flex;flex-direction:column;gap:2px;background:#e8e8e8;
  padding:2px 3px;border-radius:3px;}
.port-label-row{display:flex;gap:2px;}
.port-label{width:36px;text-align:center;font-size:9px;color:#666;}

/* ── 정보 패널 ────────────────────────────────────────────────── */
.info-panels{display:flex;gap:0;border-top:1px solid #ddd;flex-wrap:wrap;}
.info-panel{
  flex:1;min-width:300px;padding:10px 14px;border-right:1px solid #ddd;
}
.info-panel:last-child{border-right:none;}
.info-panel h3{
  font-size:11px;font-weight:bold;color:#9d1717;margin-bottom:8px;
  padding-bottom:4px;border-bottom:1px solid #e0c0c0;
  text-transform:uppercase;letter-spacing:.5px;
}

/* ── 트랜시버 그리드 ──────────────────────────────────────────── */
.transceiver-grid{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;}
.transceiver-grid .key{color:#660000;font-weight:bold;white-space:nowrap;}
.transceiver-grid .val{color:#333;word-break:break-all;}
.transceiver-absent{color:#aaa;font-style:italic;padding:6px 0;}

/* ── 테이블 공통 ──────────────────────────────────────────────── */
table{width:100%;border-collapse:collapse;font-size:11px;}
th{background:linear-gradient(to bottom,#ba1f1f,#9d1717);color:#fff;
  padding:5px 8px;text-align:left;font-weight:bold;white-space:nowrap;}
td{padding:4px 8px;border-bottom:1px solid #eee;vertical-align:middle;}
tr:hover td{background:#fdf0f0;}
tr:nth-child(even) td{background:#fafafa;}
tr:nth-child(even):hover td{background:#fdf0f0;}

/* ── 뱃지 ────────────────────────────────────────────────────── */
.badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold;}
.badge-up   {background:#e8f5e9;color:#2e7d32;border:1px solid #a5d6a7;}
.badge-down {background:#fce4ec;color:#b71c1c;border:1px solid #ef9a9a;}
.badge-warn {background:#fff8e1;color:#e65100;border:1px solid #ffcc80;}
.badge-blue {background:#e3f2fd;color:#0d47a1;border:1px solid #90caf9;}
.badge-gray {background:#f5f5f5;color:#616161;border:1px solid #bdbdbd;}

/* ── 버튼 ────────────────────────────────────────────────────── */
.btn{padding:4px 10px;border-radius:3px;border:1px solid #999;font-size:11px;cursor:pointer;
  transition:background .15s;}
.btn-primary{background:linear-gradient(to bottom,#ba1f1f,#9d1717);color:#fff;border-color:#7a1111;}
.btn-primary:hover{background:linear-gradient(to bottom,#cc2222,#aa1818);}
.btn-secondary{background:linear-gradient(to bottom,#fdfdfd,#e0e0e0);color:#333;}
.btn-secondary:hover{background:#ececec;}
.btn-sm{padding:2px 7px;font-size:10px;}
.btn-danger{background:linear-gradient(to bottom,#e53935,#b71c1c);color:#fff;border-color:#7f0000;}
.btn-danger:hover{background:#c62828;}

/* ── 폼 ──────────────────────────────────────────────────────── */
.form-row{display:flex;gap:8px;align-items:center;margin-bottom:6px;flex-wrap:wrap;}
.form-row label{font-size:11px;color:#660000;font-weight:bold;white-space:nowrap;min-width:80px;}
select,input[type=text],input[type=number]{
  padding:3px 6px;border:1px solid #ccc;border-radius:3px;font-size:11px;
  background:#fdfdfd;outline:none;
}
select:focus,input:focus{border-color:#9d1717;}

/* ── 탭 컨텐츠 ────────────────────────────────────────────────── */
.tab-content{display:none;padding:10px 14px;}
.tab-content.active{display:block;}

/* ── 상단 도구 바 ─────────────────────────────────────────────── */
.toolbar{
  display:flex;align-items:center;gap:8px;padding:6px 14px;
  background:#f9f3f3;border-bottom:1px solid #e0c0c0;flex-wrap:wrap;
}
.toolbar-label{font-size:11px;color:#660000;font-weight:bold;}

/* ── 상태 표시 dot ────────────────────────────────────────────── */
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;vertical-align:middle;margin-right:4px;}
.dot-green{background:#4CAF50;box-shadow:0 0 3px #4CAF50;}
.dot-red  {background:#f44336;}
.dot-gray {background:#9e9e9e;}

/* ── 모달 ────────────────────────────────────────────────────── */
.modal-overlay{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;
  justify-content:center;align-items:center;
}
.modal-overlay.show{display:flex;}
.modal{
  background:#fff;border-radius:6px;box-shadow:0 8px 32px rgba(0,0,0,.3);
  min-width:380px;max-width:520px;max-height:90vh;overflow-y:auto;
}
.modal-header{
  background:linear-gradient(to bottom,#ba1f1f,#9d1717);color:#fff;
  padding:10px 16px;border-radius:6px 6px 0 0;
  display:flex;justify-content:space-between;align-items:center;
}
.modal-header h2{font-size:13px;font-weight:bold;}
.modal-close{background:none;border:none;color:#fff;font-size:18px;cursor:pointer;padding:0 4px;line-height:1;}
.modal-body{padding:14px 16px;}
.modal-footer{padding:10px 16px;border-top:1px solid #eee;display:flex;gap:8px;justify-content:flex-end;}

/* ── 알림 토스트 ──────────────────────────────────────────────── */
#toast{
  position:fixed;bottom:20px;right:20px;background:#333;color:#fff;
  padding:8px 16px;border-radius:4px;font-size:12px;z-index:9999;
  opacity:0;transition:opacity .3s;pointer-events:none;max-width:300px;
}
#toast.show{opacity:1;}
#toast.toast-ok{background:#2e7d32;}
#toast.toast-err{background:#b71c1c;}

/* ── 포트 상세 사이드바 ───────────────────────────────────────── */
.port-detail-sidebar{
  width:260px;flex-shrink:0;background:#fdfdfd;border-left:1px solid #ddd;
  padding:10px;overflow-y:auto;display:none;
}
.port-detail-sidebar.show{display:block;}
.pds-title{font-size:12px;font-weight:bold;color:#9d1717;margin-bottom:8px;
  border-bottom:1px solid #e0c0c0;padding-bottom:4px;}

/* ── 터미널-스타일 출력 ───────────────────────────────────────── */
.terminal{
  background:#111;color:#0f0;font-family:monospace;font-size:11px;
  padding:8px;border-radius:3px;min-height:60px;white-space:pre-wrap;
  word-break:break-all;max-height:200px;overflow-y:auto;
}

/* ── 하드웨어 게이지 ─────────────────────────────────────────── */
.gauge-bar{
  height:8px;background:#eee;border-radius:4px;overflow:hidden;margin:2px 0;
}
.gauge-fill{height:100%;border-radius:4px;transition:width .5s;}
.gauge-green{background:#4CAF50;}
.gauge-yellow{background:#FFC107;}
.gauge-red{background:#f44336;}

/* ── BGP 상태 색상 ────────────────────────────────────────────── */
.bgp-established{color:#2e7d32;font-weight:bold;}
.bgp-active{color:#e65100;}
.bgp-idle{color:#b71c1c;}

/* ── 반응형 ──────────────────────────────────────────────────── */
@media(max-width:900px){
  .main-layout{flex-direction:column;}
  .sidebar{width:100%;display:flex;overflow-x:auto;}
  .side-menu{display:flex;padding:0;}
  .side-menu li{white-space:nowrap;border-left:none;border-bottom:3px solid transparent;}
  .side-menu li.active{border-bottom:3px solid #9d1717;border-left:none;}
}
</style>
</head>
<body>

<!-- ── 헤더 ──────────────────────────────────────────────────────── -->
<header class="top-header">
  <div class="logo-area">
    <div class="logo-icon"><span>W</span></div>
    <div class="logo-text">
      <span class="logo-text-main">Accton</span>
      <span class="logo-text-sub">WEDGE 100 NOS</span>
    </div>
  </div>
  <div class="header-info">
    <div class="header-title">Wedge 100 NOS – Management Console</div>
    <div class="user-info">
      <div>Host: <span id="hdr-host">wedge100</span></div>
      <div>User: <span>admin</span></div>
      <div id="hdr-uptime" style="font-size:10px;opacity:.8;"></div>
    </div>
  </div>
</header>

<!-- ── 상태 바 ────────────────────────────────────────────────────── -->
<div class="status-bar">
  <div class="status-left">
    <div><span class="icon-box">W</span> Standalone Mode</div>
    <div id="sb-asic"><span class="dot dot-gray"></span>ASIC: 확인 중...</div>
    <div id="sb-led-daemon"><span class="dot dot-gray"></span>LED Daemon: -</div>
  </div>
  <div class="status-right">
    <div>🌡️ <span id="sb-temp">-</span></div>
    <div>💨 <span id="sb-fan">-</span></div>
    <div>🔌 <span id="sb-psu">-</span></div>
    <div style="font-size:10px;color:#888;" id="sb-updated">-</div>
  </div>
</div>

<!-- ── 탭 네비게이션 ──────────────────────────────────────────────── -->
<nav class="nav-tabs" id="main-nav">
  <div class="tab active" data-tab="ports">Ports</div>
  <div class="tab" data-tab="vlan">VLAN</div>
  <div class="tab" data-tab="lldp">LLDP</div>
  <div class="tab" data-tab="mirror">Port Mirror</div>
  <div class="tab" data-tab="bgp">BGP</div>
  <div class="tab" data-tab="hardware">Hardware</div>
</nav>

<!-- ── 섹션 헤더 ──────────────────────────────────────────────────── -->
<div class="section-header">
  <div id="section-title">Ports Information <span class="info-icon" title="포트 상태 및 트랜시버 정보">i</span></div>
  <div style="font-size:11px;cursor:pointer;text-decoration:underline;" onclick="refreshAll()">↻ 새로고침</div>
</div>

<!-- ── 메인 레이아웃 ──────────────────────────────────────────────── -->
<div class="main-layout">

  <!-- 사이드바 메뉴 -->
  <aside class="sidebar">
    <ul class="side-menu" id="side-menu">
      <li class="active" data-tab="ports">Ports</li>
      <li data-tab="vlan">VLAN</li>
      <li data-tab="lldp">LLDP Neighbors</li>
      <li data-tab="mirror">Port Mirror</li>
      <li data-tab="bgp">BGP Routing</li>
      <li data-tab="hardware">Hardware</li>
    </ul>
  </aside>

  <!-- 컨텐츠 영역 -->
  <div class="content-area">

    <!-- ══════════════════════════════════════════════════
         TAB: PORTS
    ══════════════════════════════════════════════════ -->
    <div class="tab-content active" id="tab-ports">

      <!-- 스위치 하드웨어 패널 -->
      <div class="switch-container">
        <div class="switch-hardware">
          <div class="switch-grille-top"></div>
          <div class="switch-content">
            <div class="switch-left-panel">
              <div class="rj45-stack">
                <div class="rj45" title="Management RJ45"></div>
                <div class="rj45"></div>
              </div>
              <div class="usb-port" title="USB"></div>
            </div>
            <div>
              <div class="switch-ports-area" id="port-icons"></div>
              <div class="port-labels" id="port-labels"></div>
            </div>
          </div>
          <div class="switch-grille-bottom"></div>
        </div>
      </div>

      <!-- 포트 도구 바 -->
      <div class="toolbar">
        <span class="toolbar-label">선택 포트:</span>
        <span id="selected-port-label" style="color:#9d1717;font-weight:bold;">없음</span>
        <select id="sel-speed">
          <option value="">-- 속도 --</option>
          <option>100G</option><option>40G</option>
          <option>50G</option><option>25G</option><option>10G</option>
        </select>
        <button class="btn btn-primary btn-sm" onclick="applySpeed()">속도 적용</button>
        <select id="sel-breakout">
          <option value="">-- Breakout --</option>
          <option>1x100G</option><option>2x50G</option>
          <option>4x25G</option><option>4x10G</option><option>1x40G</option>
        </select>
        <button class="btn btn-primary btn-sm" onclick="applyBreakout()">적용</button>
        <button class="btn btn-secondary btn-sm" onclick="portAction('enable')">Enable</button>
        <button class="btn btn-secondary btn-sm" onclick="portAction('disable')">Disable</button>
        <button class="btn btn-secondary btn-sm" onclick="portFec('on')">FEC ON</button>
        <button class="btn btn-secondary btn-sm" onclick="portFec('off')">FEC OFF</button>
        <div style="margin-left:auto;display:flex;gap:6px;align-items:center;">
          <select id="sel-led-color">
            <option value="">-- LED 색상 --</option>
            <option>green</option><option>blue</option><option>red</option>
            <option>yellow</option><option>purple</option><option>aqua</option><option>off</option>
          </select>
          <button class="btn btn-primary btn-sm" onclick="applyLed()">LED 설정</button>
          <button class="btn btn-secondary btn-sm" onclick="ledBlink()" title="포트 표시등 깜빡이기">📍 Locate</button>
          <button class="btn btn-secondary btn-sm" onclick="ledSpeedMode()">Speed-Mode</button>
        </div>
      </div>

      <!-- 포트 테이블 + 사이드 상세 -->
      <div style="display:flex;">
        <div style="flex:1;overflow-x:auto;">
          <table id="port-table">
            <thead>
              <tr>
                <th>포트</th><th>CE</th><th>링크</th><th>속도</th>
                <th>Breakout</th><th>FEC</th><th>트랜시버</th>
                <th>온도</th><th>Tx/Rx(dBm)</th><th>LLDP 이웃</th>
              </tr>
            </thead>
            <tbody id="port-tbody"></tbody>
          </table>
        </div>
        <!-- 포트 상세 사이드바 -->
        <div class="port-detail-sidebar" id="port-detail">
          <div class="pds-title" id="pds-title">포트 상세</div>
          <div id="pds-content"></div>
        </div>
      </div>
    </div><!-- /tab-ports -->

    <!-- ══════════════════════════════════════════════════
         TAB: VLAN
    ══════════════════════════════════════════════════ -->
    <div class="tab-content" id="tab-vlan">
      <div class="toolbar">
        <span class="toolbar-label">VLAN 관리</span>
        <button class="btn btn-primary btn-sm" onclick="showModal('vlan-create-modal')">+ VLAN 생성</button>
      </div>
      <table id="vlan-table">
        <thead>
          <tr><th>VID</th><th>이름</th><th>Tagged 포트</th><th>Untagged 포트</th><th>작업</th></tr>
        </thead>
        <tbody id="vlan-tbody"></tbody>
      </table>
    </div>

    <!-- ══════════════════════════════════════════════════
         TAB: LLDP
    ══════════════════════════════════════════════════ -->
    <div class="tab-content" id="tab-lldp">
      <div class="toolbar">
        <span class="toolbar-label">LLDP 이웃 장비</span>
        <span style="font-size:10px;color:#888;">lldpd 데몬이 실행 중이어야 합니다.</span>
        <button class="btn btn-secondary btn-sm" style="margin-left:auto;" onclick="loadLldp()">↻ 새로고침</button>
      </div>
      <table id="lldp-table">
        <thead>
          <tr><th>로컬 포트</th><th>이웃 장비명</th><th>Chassis ID</th>
              <th>이웃 포트</th><th>포트 설명</th><th>관리 IP</th><th>링크 속도</th></tr>
        </thead>
        <tbody id="lldp-tbody"></tbody>
      </table>
    </div>

    <!-- ══════════════════════════════════════════════════
         TAB: MIRROR
    ══════════════════════════════════════════════════ -->
    <div class="tab-content" id="tab-mirror">
      <div class="toolbar">
        <span class="toolbar-label">포트 미러링 (SPAN)</span>
        <button class="btn btn-primary btn-sm" onclick="showModal('mirror-create-modal')">+ 세션 생성</button>
      </div>
      <table id="mirror-table">
        <thead>
          <tr><th>세션 ID</th><th>이름</th><th>원본 포트</th><th>목적지 포트</th><th>방향</th><th>상태</th><th>작업</th></tr>
        </thead>
        <tbody id="mirror-tbody"></tbody>
      </table>
      <div style="padding:10px 14px;font-size:11px;color:#888;border-top:1px solid #eee;margin-top:8px;">
        <strong>※ 주의:</strong> 목적지 포트는 일반 트래픽 전달이 불가능합니다.
        BCM Tomahawk 기준 최대 4개 세션 동시 지원.
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════
         TAB: BGP
    ══════════════════════════════════════════════════ -->
    <div class="tab-content" id="tab-bgp">
      <div class="toolbar">
        <span class="toolbar-label">BGP (FRRouting)</span>
        <button class="btn btn-primary btn-sm" onclick="showModal('bgp-neighbor-modal')">+ 이웃 추가</button>
        <button class="btn btn-secondary btn-sm" onclick="loadBgp()">↻ 새로고침</button>
      </div>
      <div style="display:flex;gap:0;flex-wrap:wrap;">
        <div style="flex:1;min-width:300px;padding:10px 14px;border-right:1px solid #ddd;">
          <h3 style="font-size:11px;font-weight:bold;color:#9d1717;margin-bottom:8px;text-transform:uppercase;">BGP Summary</h3>
          <div class="terminal" id="bgp-summary-output">(FRRouting vtysh 대기 중...)</div>
        </div>
        <div style="flex:1;min-width:300px;padding:10px 14px;">
          <h3 style="font-size:11px;font-weight:bold;color:#9d1717;margin-bottom:8px;text-transform:uppercase;">BGP Routes</h3>
          <div class="terminal" id="bgp-routes-output"></div>
        </div>
      </div>
      <div style="padding:10px 14px;border-top:1px solid #eee;">
        <h3 style="font-size:11px;font-weight:bold;color:#9d1717;margin-bottom:8px;text-transform:uppercase;">Neighbor 상세</h3>
        <div class="terminal" id="bgp-nbr-output" style="max-height:300px;"></div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════
         TAB: HARDWARE
    ══════════════════════════════════════════════════ -->
    <div class="tab-content" id="tab-hardware">
      <div class="toolbar">
        <span class="toolbar-label">하드웨어 상태</span>
        <button class="btn btn-secondary btn-sm" style="margin-left:auto;" onclick="loadHardware()">↻ 새로고침</button>
      </div>
      <div class="info-panels">
        <div class="info-panel">
          <h3>온도 센서</h3>
          <div id="hw-temp"></div>
        </div>
        <div class="info-panel">
          <h3>FAN</h3>
          <div id="hw-fan"></div>
        </div>
        <div class="info-panel">
          <h3>PSU</h3>
          <div id="hw-psu"></div>
        </div>
      </div>
    </div>

  </div><!-- /content-area -->
</div><!-- /main-layout -->

<!-- ══════════════════════════════════════════════════════
     모달: VLAN 생성
══════════════════════════════════════════════════════ -->
<div class="modal-overlay" id="vlan-create-modal">
  <div class="modal">
    <div class="modal-header">
      <h2>VLAN 생성</h2>
      <button class="modal-close" onclick="hideModal('vlan-create-modal')">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-row">
        <label>VLAN ID</label>
        <input type="number" id="vc-vid" min="2" max="4094" placeholder="2-4094" style="width:80px;">
      </div>
      <div class="form-row">
        <label>이름</label>
        <input type="text" id="vc-name" placeholder="선택사항" style="width:160px;">
      </div>
      <div class="form-row">
        <label>Tagged 포트</label>
        <input type="text" id="vc-ports" placeholder="1,2,3" style="width:160px;">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="hideModal('vlan-create-modal')">취소</button>
      <button class="btn btn-primary" onclick="createVlan()">생성</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════
     모달: 미러링 세션 생성
══════════════════════════════════════════════════════ -->
<div class="modal-overlay" id="mirror-create-modal">
  <div class="modal">
    <div class="modal-header">
      <h2>포트 미러링 세션 생성</h2>
      <button class="modal-close" onclick="hideModal('mirror-create-modal')">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-row">
        <label>이름</label>
        <input type="text" id="mc-name" placeholder="선택사항" style="width:160px;">
      </div>
      <div class="form-row">
        <label>원본 포트</label>
        <select id="mc-src"></select>
      </div>
      <div class="form-row">
        <label>목적지 포트</label>
        <select id="mc-dst"></select>
      </div>
      <div class="form-row">
        <label>방향</label>
        <select id="mc-dir">
          <option value="both">Both (양방향)</option>
          <option value="ingress">Ingress (수신)</option>
          <option value="egress">Egress (송신)</option>
        </select>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="hideModal('mirror-create-modal')">취소</button>
      <button class="btn btn-primary" onclick="createMirror()">생성</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════
     모달: BGP 이웃 추가
══════════════════════════════════════════════════════ -->
<div class="modal-overlay" id="bgp-neighbor-modal">
  <div class="modal">
    <div class="modal-header">
      <h2>BGP 이웃 추가</h2>
      <button class="modal-close" onclick="hideModal('bgp-neighbor-modal')">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-row">
        <label>Local AS</label>
        <input type="number" id="bn-local-as" placeholder="예: 65001" style="width:120px;">
      </div>
      <div class="form-row">
        <label>Peer IP</label>
        <input type="text" id="bn-peer-ip" placeholder="192.168.1.1" style="width:140px;">
      </div>
      <div class="form-row">
        <label>Remote AS</label>
        <input type="number" id="bn-remote-as" placeholder="예: 65002" style="width:120px;">
      </div>
      <div class="form-row">
        <label>설명</label>
        <input type="text" id="bn-desc" placeholder="선택사항" style="width:200px;">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="hideModal('bgp-neighbor-modal')">취소</button>
      <button class="btn btn-primary" onclick="addBgpNeighbor()">추가</button>
    </div>
  </div>
</div>

<!-- ── 토스트 알림 ─────────────────────────────────────────────── -->
<div id="toast"></div>

<script>
// ══════════════════════════════════════════════════════════════
//  전역 상태
// ══════════════════════════════════════════════════════════════
let selectedPort = null;
let allPorts = [];
let ledData  = {};   // port_id → {lane: color}
let blinkPorts = new Set();
let refreshTimer = null;

const PORT_COUNT = 32;

// ══════════════════════════════════════════════════════════════
//  초기화
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  buildPortIconGrid();
  buildPortSelects();
  setupTabs();
  loadVersionInfo();
  refreshAll();
  // 자동 갱신 5초
  refreshTimer = setInterval(refreshAll, 5000);
});

function setupTabs() {
  document.querySelectorAll('.tab, .side-menu li').forEach(el => {
    el.addEventListener('click', () => {
      const tab = el.dataset.tab;
      if (!tab) return;
      switchTab(tab);
    });
  });
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.side-menu li').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  document.querySelectorAll(`[data-tab="${tab}"]`).forEach(el => el.classList.add('active'));
  const content = document.getElementById('tab-' + tab);
  if (content) content.classList.add('active');

  const titles = {
    ports:'Ports Information', vlan:'VLAN Management',
    lldp:'LLDP Neighbors', mirror:'Port Mirroring (SPAN)',
    bgp:'BGP Routing (FRRouting)', hardware:'Hardware Status',
  };
  document.getElementById('section-title').innerHTML =
    (titles[tab] || tab) + ' <span class="info-icon">i</span>';

  // 탭별 데이터 로드
  if (tab === 'lldp')     loadLldp();
  if (tab === 'mirror')   loadMirror();
  if (tab === 'bgp')      loadBgp();
  if (tab === 'hardware') loadHardware();
  if (tab === 'vlan')     loadVlan();
}

// ══════════════════════════════════════════════════════════════
//  포트 아이콘 그리드 구성 (스위치 하드웨어 패널)
//  Wedge100 레이아웃: 상단 홀수, 하단 짝수 (2행 × 16열)
// ══════════════════════════════════════════════════════════════
function buildPortIconGrid() {
  const area   = document.getElementById('port-icons');
  const labels = document.getElementById('port-labels');
  area.innerHTML = '';
  labels.innerHTML = '';

  // 16 블록 × 2포트 (상:홀수, 하:짝수)
  for (let blk = 0; blk < 16; blk++) {
    const topPort = blk * 2 + 1;   // 1,3,5,...31
    const botPort = blk * 2 + 2;   // 2,4,6,...32

    const block = document.createElement('div');
    block.className = 'port-block';

    const rowTop = document.createElement('div');
    rowTop.className = 'port-row';
    rowTop.appendChild(makePortIcon(topPort));
    block.appendChild(rowTop);

    const rowBot = document.createElement('div');
    rowBot.className = 'port-row';
    rowBot.appendChild(makePortIcon(botPort));
    block.appendChild(rowBot);

    area.appendChild(block);

    // 번호 레이블
    const lblBlock = document.createElement('div');
    lblBlock.className = 'port-label-block';
    const lblRow1 = document.createElement('div'); lblRow1.className = 'port-label-row';
    const lblRow2 = document.createElement('div'); lblRow2.className = 'port-label-row';
    const l1 = document.createElement('div'); l1.className='port-label'; l1.textContent = topPort;
    const l2 = document.createElement('div'); l2.className='port-label'; l2.textContent = botPort;
    lblRow1.appendChild(l1); lblRow2.appendChild(l2);
    lblBlock.appendChild(lblRow1); lblBlock.appendChild(lblRow2);
    labels.appendChild(lblBlock);
  }
}

function makePortIcon(portNum) {
  const el = document.createElement('div');
  el.className = 'qsfp-port';
  el.id = `port-icon-${portNum}`;
  el.dataset.port = portNum;
  el.title = `포트 ${portNum}`;

  // 4 lane LED
  const laneLeds = document.createElement('div');
  laneLeds.className = 'lane-leds';
  for (let l = 0; l < 4; l++) {
    const led = document.createElement('div');
    led.className = 'lane-led off';
    led.id = `led-${portNum}-${l}`;
    laneLeds.appendChild(led);
  }
  el.appendChild(laneLeds);

  // 포트 번호
  const num = document.createElement('div');
  num.className = 'port-num';
  num.textContent = portNum;
  el.appendChild(num);

  // pull-tab
  const pull = document.createElement('div');
  pull.className = 'pull-tab';
  el.appendChild(pull);

  el.addEventListener('click', () => selectPort(portNum));
  return el;
}

function buildPortSelects() {
  ['mc-src','mc-dst'].forEach(id => {
    const sel = document.getElementById(id);
    for (let i = 1; i <= PORT_COUNT; i++) {
      const o = document.createElement('option');
      o.value = i; o.textContent = `포트 ${i}`;
      sel.appendChild(o);
    }
  });
}

// ══════════════════════════════════════════════════════════════
//  포트 선택
// ══════════════════════════════════════════════════════════════
function selectPort(portNum) {
  // 이전 선택 해제
  if (selectedPort) {
    document.getElementById(`port-icon-${selectedPort}`)?.classList.remove('selected');
  }
  selectedPort = portNum;
  document.getElementById(`port-icon-${portNum}`)?.classList.add('selected');
  document.getElementById('selected-port-label').textContent = `포트 ${portNum}`;

  // 상세 사이드바 표시
  const pdata = allPorts.find(p => p.port_id == portNum);
  showPortDetail(pdata);
}

function showPortDetail(pdata) {
  const sidebar = document.getElementById('port-detail');
  const content = document.getElementById('pds-content');
  const title   = document.getElementById('pds-title');

  if (!pdata) { sidebar.classList.remove('show'); return; }
  sidebar.classList.add('show');
  title.textContent = `포트 ${pdata.port_id} 상세`;

  const link = pdata.link == 1 ? '<span class="badge badge-up">UP</span>' : '<span class="badge badge-down">DOWN</span>';
  const xcvr = pdata.xcvr_present == 1;

  content.innerHTML = `
    <div class="transceiver-grid" style="margin-bottom:8px;">
      <div class="key">링크</div><div class="val">${link}</div>
      <div class="key">속도</div><div class="val">${pdata.speed || '-'}</div>
      <div class="key">Breakout</div><div class="val">${pdata.breakout || '1x100G'}</div>
      <div class="key">FEC</div><div class="val">${pdata.fec_enabled?'ON':'OFF'}</div>
      <div class="key">CE 채널</div><div class="val">${pdata.ce_name}</div>
    </div>
    <div class="pds-title" style="margin-top:8px;">트랜시버</div>
    ${xcvr ? `
    <div class="transceiver-grid">
      <div class="key">타입</div><div class="val">${pdata.connector_type||'-'}</div>
      <div class="key">벤더</div><div class="val">${pdata.vendor||'-'}</div>
      <div class="key">파트</div><div class="val" style="font-size:10px;">${pdata.part_number||'-'}</div>
      <div class="key">시리얼</div><div class="val" style="font-size:10px;">${pdata.serial||'-'}</div>
      ${pdata.temp_celsius!=null?`<div class="key">온도</div><div class="val">${parseFloat(pdata.temp_celsius).toFixed(1)}°C</div>`:''}
      ${pdata.tx_power_dbm!=null?`<div class="key">Tx 파워</div><div class="val">${parseFloat(pdata.tx_power_dbm).toFixed(2)} dBm</div>`:''}
      ${pdata.rx_power_dbm!=null?`<div class="key">Rx 파워</div><div class="val">${parseFloat(pdata.rx_power_dbm).toFixed(2)} dBm</div>`:''}
    </div>` : '<div class="transceiver-absent">트랜시버 없음</div>'}
    ${pdata.lldp_neighbor ? `
    <div class="pds-title" style="margin-top:8px;">LLDP 이웃</div>
    <div class="transceiver-grid">
      <div class="key">장비명</div><div class="val">${pdata.lldp_neighbor}</div>
      <div class="key">포트</div><div class="val">${pdata.lldp_port||'-'}</div>
    </div>` : ''}
    <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:4px;">
      <button class="btn btn-secondary btn-sm" onclick="portAction('enable')">Enable</button>
      <button class="btn btn-secondary btn-sm" onclick="portAction('disable')">Disable</button>
      <button class="btn btn-secondary btn-sm" onclick="ledBlink()" title="LED 깜빡여 포트 찾기">📍 Locate</button>
    </div>`;
}

// ══════════════════════════════════════════════════════════════
//  데이터 로드 & 갱신
// ══════════════════════════════════════════════════════════════
function refreshAll() {
  loadPorts();
  loadLeds();
  updateStatusBar();
}

function loadPorts() {
  api('ports').then(data => {
    if (!data.ok) return;
    allPorts = data.data;
    renderPortTable(allPorts);
    updatePortIcons(allPorts);
    if (selectedPort) {
      const pdata = allPorts.find(p => p.port_id == selectedPort);
      showPortDetail(pdata);
    }
  });
}

function loadLeds() {
  api('leds').then(data => {
    if (!data.ok) return;
    ledData = {};
    blinkPorts.clear();
    data.data.forEach(row => {
      if (!ledData[row.port_id]) ledData[row.port_id] = {};
      ledData[row.port_id][row.lane] = row.color;
      if (row.blink) blinkPorts.add(parseInt(row.port_id));
    });
    applyLedDisplay();
  });
}

function applyLedDisplay() {
  for (let port = 1; port <= PORT_COUNT; port++) {
    const ld = ledData[port] || {};
    const isBlink = blinkPorts.has(port);
    for (let lane = 0; lane < 4; lane++) {
      const ledEl = document.getElementById(`led-${port}-${lane}`);
      if (!ledEl) continue;
      const color = ld[lane] || 'off';
      ledEl.className = `lane-led ${color}` + (isBlink ? ' blink' : '');
    }
  }
}

function updatePortIcons(ports) {
  ports.forEach(p => {
    const icon = document.getElementById(`port-icon-${p.port_id}`);
    if (!icon) return;
    icon.classList.toggle('link-up', p.link == 1);
    icon.title = `포트 ${p.port_id} | ${p.link==1?'UP':'DOWN'} | ${p.speed||'-'} | ${p.xcvr_present?p.connector_type||'QSFP':'미장착'}`;
  });
}

function renderPortTable(ports) {
  const tbody = document.getElementById('port-tbody');
  tbody.innerHTML = '';
  ports.forEach(p => {
    const linkBadge = p.link == 1
      ? `<span class="badge badge-up"><span class="dot dot-green"></span>UP</span>`
      : `<span class="badge badge-down">DOWN</span>`;
    const xcvrBadge = p.xcvr_present == 1
      ? `<span class="badge badge-blue">${p.connector_type||'QSFP'}</span>`
      : `<span class="badge badge-gray">없음</span>`;
    const lldp = p.lldp_neighbor
      ? `<span title="${p.lldp_port||''}">${p.lldp_neighbor}</span>` : '-';
    const temp = p.temp_celsius != null ? `${parseFloat(p.temp_celsius).toFixed(1)}°C` : '-';
    const power = (p.tx_power_dbm != null)
      ? `${parseFloat(p.tx_power_dbm).toFixed(1)} / ${parseFloat(p.rx_power_dbm??0).toFixed(1)}` : '-';

    const tr = document.createElement('tr');
    if (p.port_id == selectedPort) tr.style.background = '#fde8e8';
    tr.innerHTML = `
      <td><a href="#" style="color:#9d1717;font-weight:bold;" onclick="selectPort(${p.port_id});return false;">
        포트 ${p.port_id}</a></td>
      <td style="color:#888;">${p.ce_name}</td>
      <td>${linkBadge}</td>
      <td>${p.speed||'-'}</td>
      <td>${p.breakout||'1x100G'}</td>
      <td>${p.fec_enabled?'<span class="badge badge-blue">ON</span>':'<span class="badge badge-gray">OFF</span>'}</td>
      <td>${xcvrBadge}</td>
      <td>${temp}</td>
      <td style="font-size:10px;">${power}</td>
      <td style="font-size:10px;">${lldp}</td>`;
    tr.addEventListener('click', () => selectPort(p.port_id));
    tbody.appendChild(tr);
  });
}

function updateStatusBar() {
  api('hardware').then(d => {
    if (!d.ok) return;
    const hw = d.data;
    // 온도
    const temps = hw.temperatures || [];
    const maxTemp = temps.reduce((m,t) => Math.max(m, t.celsius||0), 0);
    document.getElementById('sb-temp').textContent = `${maxTemp.toFixed(1)}°C`;

    // FAN
    const fans = hw.fans || [];
    const fanOk = fans.every(f => f.present);
    document.getElementById('sb-fan').textContent =
      fanOk ? `FAN OK (${fans.length}개)` : 'FAN 이상!';

    // PSU
    const psus = hw.psus || [];
    const psuOk = psus.some(p => p.power_ok);
    document.getElementById('sb-psu').textContent = psuOk ? 'PSU OK' : 'PSU 이상!';

    document.getElementById('sb-updated').textContent =
      '갱신: ' + new Date().toLocaleTimeString('ko-KR');
  });

  api('version').then(d => {
    if (!d.ok) return;
    document.getElementById('hdr-uptime').textContent = d.data.uptime?.trim() || '';
  });
}

// ══════════════════════════════════════════════════════════════
//  VLAN
// ══════════════════════════════════════════════════════════════
function loadVlan() {
  api('vlans').then(d => {
    if (!d.ok) return;
    const tbody = document.getElementById('vlan-tbody');
    tbody.innerHTML = '';
    d.data.forEach(v => {
      const tagged   = v.ports.filter(p=>p.tagged==1).map(p=>`포트${p.port_id}`).join(', ')||'-';
      const untagged = v.ports.filter(p=>p.tagged==0).map(p=>`포트${p.port_id}`).join(', ')||'-';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${v.vid}</strong></td>
        <td>${v.name||'-'}</td>
        <td>${tagged}</td>
        <td>${untagged}</td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="deleteVlan(${v.vid})">삭제</button>
        </td>`;
      tbody.appendChild(tr);
    });
  });
}

function createVlan() {
  const vid  = document.getElementById('vc-vid').value;
  const name = document.getElementById('vc-name').value;
  const ports = document.getElementById('vc-ports').value;
  if (!vid) { toast('VLAN ID를 입력하세요.','err'); return; }
  apiPost('vlan_create',{vid,name,ports}).then(d=>{
    if(d.ok){ hideModal('vlan-create-modal'); loadVlan(); toast(`VLAN ${vid} 생성`); }
    else toast(d.error,'err');
  });
}

function deleteVlan(vid) {
  if (!confirm(`VLAN ${vid}를 삭제하시겠습니까?`)) return;
  apiPost('vlan_delete',{vid}).then(d=>{
    if(d.ok){ loadVlan(); toast(`VLAN ${vid} 삭제`); }
    else toast(d.error,'err');
  });
}

// ══════════════════════════════════════════════════════════════
//  LLDP
// ══════════════════════════════════════════════════════════════
function loadLldp() {
  api('lldp').then(d => {
    if (!d.ok) return;
    const tbody = document.getElementById('lldp-tbody');
    tbody.innerHTML = '';
    if (!d.data.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#aaa;padding:20px;">LLDP 이웃 없음 (lldpd 실행 확인)</td></tr>';
      return;
    }
    d.data.forEach(row => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>포트 ${row.local_port}</strong></td>
        <td>${row.chassis_name||'-'}</td>
        <td style="font-size:10px;">${row.chassis_id||'-'}</td>
        <td>${row.port_id||'-'}</td>
        <td style="font-size:10px;">${row.port_desc||'-'}</td>
        <td>${row.mgmt_ip||'-'}</td>
        <td>${row.speed||'-'}</td>`;
      tbody.appendChild(tr);
    });
  });
}

// ══════════════════════════════════════════════════════════════
//  포트 미러링
// ══════════════════════════════════════════════════════════════
function loadMirror() {
  api('mirrors').then(d => {
    if (!d.ok) return;
    const tbody = document.getElementById('mirror-tbody');
    tbody.innerHTML = '';
    if (!d.data.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#aaa;padding:20px;">세션 없음</td></tr>';
      return;
    }
    d.data.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${s.session_id}</td>
        <td>${s.name||'-'}</td>
        <td><strong>포트 ${s.src_port}</strong></td>
        <td><strong>포트 ${s.dst_port}</strong></td>
        <td><span class="badge badge-blue">${s.direction}</span></td>
        <td><span class="badge ${s.active?'badge-up':'badge-gray'}">${s.active?'Active':'Inactive'}</span></td>
        <td><button class="btn btn-danger btn-sm" onclick="deleteMirror(${s.session_id})">삭제</button></td>`;
      tbody.appendChild(tr);
    });
  });
}

function createMirror() {
  const src = document.getElementById('mc-src').value;
  const dst = document.getElementById('mc-dst').value;
  const dir = document.getElementById('mc-dir').value;
  const name = document.getElementById('mc-name').value;
  if (src === dst) { toast('원본과 목적지 포트가 달라야 합니다.','err'); return; }
  apiPost('mirror_create',{src_port:src,dst_port:dst,direction:dir,name}).then(d=>{
    if(d.ok){ hideModal('mirror-create-modal'); loadMirror(); toast('미러 세션 생성'); }
    else toast(d.error,'err');
  });
}

function deleteMirror(id) {
  if (!confirm(`세션 ${id}를 삭제하시겠습니까?`)) return;
  apiPost('mirror_delete',{session_id:id}).then(d=>{
    if(d.ok){ loadMirror(); toast(`세션 ${id} 삭제`); }
    else toast(d.error,'err');
  });
}

// ══════════════════════════════════════════════════════════════
//  BGP
// ══════════════════════════════════════════════════════════════
function loadBgp() {
  api('bgp_summary').then(d => {
    document.getElementById('bgp-summary-output').textContent =
      d.ok ? (d.data.raw||'(출력 없음)') : '오류';
  });
  api('bgp_routes').then(d => {
    document.getElementById('bgp-routes-output').textContent =
      d.ok ? (d.data.raw||'(라우팅 테이블 없음)') : '오류';
  });
  api('bgp_neighbors').then(d => {
    document.getElementById('bgp-nbr-output').textContent =
      d.ok ? (d.data.raw||'(이웃 없음)') : '오류';
  });
}

function addBgpNeighbor() {
  const local_as  = document.getElementById('bn-local-as').value;
  const peer_ip   = document.getElementById('bn-peer-ip').value;
  const remote_as = document.getElementById('bn-remote-as').value;
  const description = document.getElementById('bn-desc').value;
  if (!local_as||!peer_ip||!remote_as) { toast('필수 항목을 입력하세요.','err'); return; }
  apiPost('bgp_add_neighbor',{local_as,peer_ip,remote_as,description}).then(d=>{
    if(d.ok){ hideModal('bgp-neighbor-modal'); loadBgp(); toast('BGP 이웃 추가'); }
    else toast(d.error,'err');
  });
}

// ══════════════════════════════════════════════════════════════
//  하드웨어
// ══════════════════════════════════════════════════════════════
function loadHardware() {
  api('hardware').then(d => {
    if (!d.ok) return;
    const hw = d.data;

    // 온도
    const tempDiv = document.getElementById('hw-temp');
    if (hw.temperatures?.length) {
      tempDiv.innerHTML = hw.temperatures.map(t => {
        const pct = Math.min((t.celsius / 85) * 100, 100);
        const cls = pct > 90 ? 'gauge-red' : pct > 70 ? 'gauge-yellow' : 'gauge-green';
        const stColor = t.status==='OK'?'#2e7d32':t.status==='WARNING'?'#e65100':'#b71c1c';
        return `<div style="margin-bottom:6px;">
          <div style="display:flex;justify-content:space-between;font-size:10px;">
            <span>${t.label}</span>
            <span style="color:${stColor};font-weight:bold;">${t.celsius.toFixed(1)}°C</span>
          </div>
          <div class="gauge-bar"><div class="gauge-fill ${cls}" style="width:${pct}%"></div></div>
        </div>`;
      }).join('');
    } else { tempDiv.innerHTML = '<div class="transceiver-absent">온도 센서 데이터 없음</div>'; }

    // FAN
    const fanDiv = document.getElementById('hw-fan');
    if (hw.fans?.length) {
      fanDiv.innerHTML = hw.fans.map(f => {
        const st = f.present ? '<span class="badge badge-up">OK</span>' : '<span class="badge badge-down">없음</span>';
        return `<div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:11px;">
          <span>FAN${f.fan_id}</span>
          <span>${f.rpm_front.toLocaleString()} RPM</span>
          ${st}
        </div>`;
      }).join('');
    } else { fanDiv.innerHTML = '<div class="transceiver-absent">FAN 데이터 없음</div>'; }

    // PSU
    const psuDiv = document.getElementById('hw-psu');
    if (hw.psus?.length) {
      psuDiv.innerHTML = hw.psus.map(p => {
        const ok = p.power_ok ? '<span class="badge badge-up">OK</span>' : '<span class="badge badge-down">FAIL</span>';
        const pres = p.present ? 'Present' : '<span class="badge badge-warn">Absent</span>';
        return `<div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:11px;">
          <span>PSU${p.psu_id}</span><span>${pres}</span>${ok}
        </div>`;
      }).join('');
    } else { psuDiv.innerHTML = '<div class="transceiver-absent">PSU 데이터 없음</div>'; }
  });
}

// ══════════════════════════════════════════════════════════════
//  포트 작업
// ══════════════════════════════════════════════════════════════
function applySpeed() {
  if (!selectedPort) { toast('포트를 선택하세요.','err'); return; }
  const speed = document.getElementById('sel-speed').value;
  if (!speed) { toast('속도를 선택하세요.','err'); return; }
  apiPost('port_speed',{port:selectedPort,speed}).then(d=>{
    if(d.ok) toast(`포트 ${selectedPort} → ${speed}`);
    else toast(d.error,'err');
  });
}

function applyBreakout() {
  if (!selectedPort) { toast('포트를 선택하세요.','err'); return; }
  const mode = document.getElementById('sel-breakout').value;
  if (!mode) { toast('모드를 선택하세요.','err'); return; }
  if (!confirm(`포트 ${selectedPort} breakout → ${mode}?\n트래픽이 일시 중단됩니다.`)) return;
  apiPost('port_breakout',{port:selectedPort,mode}).then(d=>{
    if(d.ok) toast(`포트 ${selectedPort} breakout → ${mode}`);
    else toast(d.error,'err');
  });
}

function portAction(action) {
  if (!selectedPort) { toast('포트를 선택하세요.','err'); return; }
  apiPost('port_enable',{port:selectedPort,state:action}).then(d=>{
    if(d.ok) { toast(`포트 ${selectedPort} ${action}`); loadPorts(); }
    else toast(d.error,'err');
  });
}

function portFec(state) {
  if (!selectedPort) { toast('포트를 선택하세요.','err'); return; }
  apiPost('port_fec',{port:selectedPort,state}).then(d=>{
    if(d.ok) toast(`포트 ${selectedPort} FEC ${state.toUpperCase()}`);
    else toast(d.error,'err');
  });
}

// ══════════════════════════════════════════════════════════════
//  LED 작업
// ══════════════════════════════════════════════════════════════
function applyLed() {
  if (!selectedPort) { toast('포트를 선택하세요.','err'); return; }
  const color = document.getElementById('sel-led-color').value;
  if (!color) { toast('색상을 선택하세요.','err'); return; }
  apiPost('led_set',{port:selectedPort,color}).then(d=>{
    if(d.ok) { toast(`포트 ${selectedPort} LED → ${color}`); loadLeds(); }
    else toast(d.error,'err');
  });
}

function ledBlink() {
  if (!selectedPort) { toast('포트를 선택하세요.','err'); return; }
  apiPost('led_blink',{port:selectedPort,seconds:15}).then(d=>{
    if(d.ok) toast(`포트 ${selectedPort} 표시등 깜빡이기 (15초)`);
    else toast(d.error,'err');
  });
}

function ledSpeedMode() {
  apiPost('led_speed_mode',{}).then(d=>{
    if(d.ok) { toast('Speed-Mode LED 적용'); loadLeds(); }
    else toast(d.error,'err');
  });
}

function loadVersionInfo() {
  api('version').then(d => {
    if (!d.ok) return;
    document.getElementById('hdr-host').textContent =
      d.data.nos?.replace('wedge100-nos ','') || 'wedge100';
  });
}

// ══════════════════════════════════════════════════════════════
//  API 헬퍼
// ══════════════════════════════════════════════════════════════
function api(action) {
  return fetch(`api/api.php?action=${action}`)
    .then(r => r.json())
    .catch(() => ({ok:false,error:'네트워크 오류'}));
}

function apiPost(action, data) {
  const body = new URLSearchParams({action, ...data});
  return fetch('api/api.php', {method:'POST', body})
    .then(r => r.json())
    .catch(() => ({ok:false,error:'네트워크 오류'}));
}

// ══════════════════════════════════════════════════════════════
//  모달 / 토스트
// ══════════════════════════════════════════════════════════════
function showModal(id) {
  document.getElementById(id).classList.add('show');
}

function hideModal(id) {
  document.getElementById(id).classList.remove('show');
}

// 모달 외부 클릭 닫기
document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if(e.target===m) m.classList.remove('show'); });
});

let _toastTimer;
function toast(msg, type='ok') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `show toast-${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.className = '', 3000);
}
</script>
</body>
</html>
