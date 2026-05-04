<?php
// webui/api/api.php
// REST API 엔드포인트 (WebUI Ajax 요청 처리)

require_once __DIR__ . '/../includes/db.php';

header('Content-Type: application/json');
$action = $_GET['action'] ?? $_POST['action'] ?? '';

switch ($action) {

// ── 포트 상태 조회 ────────────────────────────────────────────────
case 'ports':
    $rows = db()->query("
        SELECT p.*, t.present AS xcvr_present,
               t.connector_type, t.vendor, t.part_number, t.serial,
               t.temp_celsius, t.tx_power_dbm, t.rx_power_dbm,
               l.chassis_name AS lldp_neighbor, l.port_desc AS lldp_port
        FROM port_state p
        LEFT JOIN transceiver t ON t.port_id = p.port_id
        LEFT JOIN lldp_neighbor l ON l.local_port = p.port_id
        ORDER BY p.port_id
    ")->fetchAll();
    json_ok($rows);

// ── 단일 포트 상태 ───────────────────────────────────────────────
case 'port':
    $pid = req_int('port', 1, 32);
    $row = db()->prepare("
        SELECT p.*, t.present AS xcvr_present, t.connector_type, t.vendor,
               t.part_number, t.serial, t.temp_celsius, t.tx_power_dbm, t.rx_power_dbm,
               l.chassis_id, l.chassis_name, l.port_id AS lldp_port_id,
               l.port_desc, l.system_desc AS lldp_sys_desc, l.mgmt_ip AS lldp_mgmt_ip
        FROM port_state p
        LEFT JOIN transceiver t ON t.port_id = p.port_id
        LEFT JOIN lldp_neighbor l ON l.local_port = p.port_id
        WHERE p.port_id = ?
    ");
    $row->execute([$pid]);
    $data = $row->fetch();
    if (!$data) json_err("포트 없음: $pid", 404);
    json_ok($data);

// ── LED 상태 전체 ────────────────────────────────────────────────
case 'leds':
    $rows = db()->query("
        SELECT port_id, lane, color, blink
        FROM led_state
        ORDER BY port_id, lane
    ")->fetchAll();
    json_ok($rows);

// ── LED 색상 설정 (WebUI → CLI) ──────────────────────────────────
case 'led_set':
    $port  = req_int('port', 1, 32);
    $color = req_str('color', ['green','blue','red','yellow','purple','aqua','off','white']);
    $r = wedge_cmd("led set $port $color");
    json_ok($r);

// ── 포트 인디케이터 (LED 깜빡이기) ───────────────────────────────
case 'led_blink':
    $port = req_int('port', 1, 32);
    $sec  = min((int)($_POST['seconds'] ?? 10), 60);
    $until = date('Y-m-d H:i:s', time() + $sec);
    $st = db()->prepare("
        UPDATE led_state SET blink=1, blink_until=?
        WHERE port_id=? AND lane=0
    ");
    $st->execute([$until, $port]);
    json_ok(['port' => $port, 'blink_until' => $until]);

// ── 포트 인디케이터 해제 ─────────────────────────────────────────
case 'led_blink_stop':
    $port = req_int('port', 1, 32);
    db()->prepare("UPDATE led_state SET blink=0, blink_until=NULL WHERE port_id=?")->execute([$port]);
    json_ok(['port' => $port]);

// ── LED speed-mode 전체 적용 ─────────────────────────────────────
case 'led_speed_mode':
    $r = wedge_cmd("led speed-mode");
    json_ok($r);

// ── 포트 속도 설정 ───────────────────────────────────────────────
case 'port_speed':
    $port  = req_int('port', 1, 32);
    $speed = req_str('speed', ['100G','40G','50G','25G','10G']);
    $r = wedge_cmd("port set $port speed $speed");
    json_ok($r);

// ── 포트 Breakout ────────────────────────────────────────────────
case 'port_breakout':
    $port = req_int('port', 1, 32);
    $mode = req_str('mode', ['1x100G','2x50G','4x25G','4x10G','1x40G']);
    // DB breakout 컬럼도 갱신
    db()->prepare("UPDATE port_state SET breakout=? WHERE port_id=?")->execute([$mode, $port]);
    $r = wedge_cmd("port breakout $port $mode");
    json_ok($r);

// ── 포트 Enable/Disable ──────────────────────────────────────────
case 'port_enable':
    $port  = req_int('port', 1, 32);
    $state = req_str('state', ['enable','disable']);
    $r = wedge_cmd("port $state $port");
    // admin_up 갱신
    db()->prepare("UPDATE port_state SET admin_up=? WHERE port_id=?")
        ->execute([$state === 'enable' ? 1 : 0, $port]);
    json_ok($r);

// ── FEC 설정 ─────────────────────────────────────────────────────
case 'port_fec':
    $port  = req_int('port', 1, 32);
    $state = req_str('state', ['on','off']);
    $r = wedge_cmd("port fec $port $state");
    db()->prepare("UPDATE port_state SET fec_enabled=? WHERE port_id=?")
        ->execute([$state === 'on' ? 1 : 0, $port]);
    json_ok($r);

// ── 포트 카운터 ──────────────────────────────────────────────────
case 'port_counters':
    $port = req_int('port', 1, 32);
    $row = db()->prepare("
        SELECT rx_packets, tx_packets, rx_bytes, tx_bytes, rx_errors, recorded_at
        FROM counter_history
        WHERE port_id = ?
        ORDER BY recorded_at DESC LIMIT 1
    ");
    $row->execute([$port]);
    $data = $row->fetch();
    json_ok($data ?: ['rx_packets'=>0,'tx_packets'=>0,'rx_bytes'=>0,'tx_bytes'=>0,'rx_errors'=>0]);

// ── 카운터 트렌드 (최근 12포인트) ───────────────────────────────
case 'counter_trend':
    $port = req_int('port', 1, 32);
    $rows = db()->prepare("
        SELECT rx_bytes, tx_bytes, recorded_at
        FROM counter_history
        WHERE port_id = ?
        ORDER BY recorded_at DESC LIMIT 12
    ");
    $rows->execute([$port]);
    json_ok(array_reverse($rows->fetchAll()));

// ── VLAN 목록 ────────────────────────────────────────────────────
case 'vlans':
    $vlans = db()->query("SELECT * FROM vlan ORDER BY vid")->fetchAll();
    foreach ($vlans as &$v) {
        $ports = db()->prepare("SELECT port_id, tagged FROM vlan_port WHERE vid=?");
        $ports->execute([$v['vid']]);
        $v['ports'] = $ports->fetchAll();
    }
    json_ok($vlans);

// ── VLAN 생성 ─────────────────────────────────────────────────────
case 'vlan_create':
    $vid  = req_int('vid', 2, 4094);
    $name = substr(trim($_POST['name'] ?? ''), 0, 32);
    $ports_str = trim($_POST['ports'] ?? '');
    $cmd = "vlan create $vid" . ($name ? " --name \"$name\"" : '');
    if ($ports_str) $cmd .= " --ports $ports_str";
    $r = wedge_cmd($cmd);
    // DB에도 저장
    db()->prepare("INSERT IGNORE INTO vlan (vid, name) VALUES (?,?)")->execute([$vid, $name]);
    json_ok($r);

// ── VLAN 삭제 ─────────────────────────────────────────────────────
case 'vlan_delete':
    $vid = req_int('vid', 2, 4094);
    $r = wedge_cmd("vlan delete $vid");
    db()->prepare("DELETE FROM vlan WHERE vid=?")->execute([$vid]);
    json_ok($r);

// ── VLAN 포트 추가 ────────────────────────────────────────────────
case 'vlan_add_port':
    $vid    = req_int('vid', 1, 4094);
    $port   = req_int('port', 1, 32);
    $tagged = ($_POST['tagged'] ?? '1') === '1';
    $cmd = "vlan add $vid $port" . ($tagged ? '' : ' --untagged');
    $r = wedge_cmd($cmd);
    db()->prepare("INSERT IGNORE INTO vlan_port (vid,port_id,tagged) VALUES (?,?,?)")
        ->execute([$vid, $port, $tagged ? 1 : 0]);
    json_ok($r);

// ── VLAN 포트 제거 ────────────────────────────────────────────────
case 'vlan_remove_port':
    $vid  = req_int('vid', 1, 4094);
    $port = req_int('port', 1, 32);
    $r = wedge_cmd("vlan remove $vid $port");
    db()->prepare("DELETE FROM vlan_port WHERE vid=? AND port_id=?")->execute([$vid, $port]);
    json_ok($r);

// ── LLDP 이웃 ────────────────────────────────────────────────────
case 'lldp':
    $rows = db()->query("
        SELECT l.*, p.speed, p.link
        FROM lldp_neighbor l
        LEFT JOIN port_state p ON p.port_id = l.local_port
        ORDER BY l.local_port
    ")->fetchAll();
    json_ok($rows);

// ── 포트 미러링 목록 ──────────────────────────────────────────────
case 'mirrors':
    $rows = db()->query("SELECT * FROM mirror_session ORDER BY session_id")->fetchAll();
    json_ok($rows);

// ── 포트 미러링 생성 ──────────────────────────────────────────────
case 'mirror_create':
    $src = req_int('src_port', 1, 32);
    $dst = req_int('dst_port', 1, 32);
    $dir = req_str('direction', ['ingress','egress','both']);
    $name = substr(trim($_POST['name'] ?? ''), 0, 32);
    if ($src === $dst) json_err("원본과 목적지 포트가 같을 수 없습니다.");
    db()->prepare("INSERT INTO mirror_session (src_port,dst_port,direction,name) VALUES (?,?,?,?)")
        ->execute([$src, $dst, $dir, $name ?: "mirror-$src-$dst"]);
    // CLI 커맨드는 향후 mirror CLI 완성 후 연동
    json_ok(['src' => $src, 'dst' => $dst, 'direction' => $dir]);

// ── 포트 미러링 삭제 ──────────────────────────────────────────────
case 'mirror_delete':
    $id = req_int('session_id', 1);
    $row = db()->prepare("SELECT * FROM mirror_session WHERE session_id=?")->execute([$id]);
    db()->prepare("DELETE FROM mirror_session WHERE session_id=?")->execute([$id]);
    json_ok(['deleted' => $id]);

// ── BGP 요약 ─────────────────────────────────────────────────────
case 'bgp_summary':
    $output = shell_exec("vtysh -c 'show bgp summary' 2>/dev/null");
    json_ok(['raw' => $output ?? '(FRRouting 미설치 또는 BGP 미설정)']);

// ── BGP 이웃 ─────────────────────────────────────────────────────
case 'bgp_neighbors':
    $output = shell_exec("vtysh -c 'show bgp neighbors' 2>/dev/null");
    json_ok(['raw' => $output ?? '']);

// ── BGP 라우팅 테이블 ────────────────────────────────────────────
case 'bgp_routes':
    $output = shell_exec("vtysh -c 'show bgp ipv4 unicast' 2>/dev/null");
    json_ok(['raw' => $output ?? '']);

// ── BGP 이웃 추가 ────────────────────────────────────────────────
case 'bgp_add_neighbor':
    $peer_ip   = filter_var($_POST['peer_ip'] ?? '', FILTER_VALIDATE_IP);
    $remote_as = (int)($_POST['remote_as'] ?? 0);
    $local_as  = (int)($_POST['local_as'] ?? 0);
    $desc      = substr(trim($_POST['description'] ?? ''), 0, 64);
    if (!$peer_ip || !$remote_as || !$local_as) json_err("peer_ip, local_as, remote_as 필수");
    $cmd = "vtysh -c 'configure terminal' -c 'router bgp $local_as'"
         . " -c 'neighbor $peer_ip remote-as $remote_as'";
    if ($desc) $cmd .= " -c 'neighbor $peer_ip description $desc'";
    $cmd .= " -c 'end' -c 'write' 2>&1";
    $out = shell_exec($cmd);
    // DB 저장
    $bgp = db()->query("SELECT id FROM bgp_config LIMIT 1")->fetch();
    if (!$bgp) {
        db()->prepare("INSERT INTO bgp_config (local_as, router_id) VALUES (?,?)")
            ->execute([$local_as, '0.0.0.0']);
        $bgp_id = db()->lastInsertId();
    } else {
        $bgp_id = $bgp['id'];
    }
    db()->prepare("INSERT INTO bgp_neighbor (bgp_id,peer_ip,remote_as,description) VALUES (?,?,?,?)")
        ->execute([$bgp_id, $peer_ip, $remote_as, $desc]);
    json_ok(['output' => $out]);

// ── 하드웨어 상태 ────────────────────────────────────────────────
case 'hardware':
    $output = shell_exec("PYTHONPATH=/usr/local/wedge100-nos python3 -c \"
import sys; sys.path.insert(0,'/usr/local/wedge100-nos')
import json
from wedge100.managers.hw import HWManager
hw = HWManager()
print(json.dumps(hw.get_system_health()))
\" 2>/dev/null");
    $data = json_decode($output ?? '{}', true);
    json_ok($data ?: ['overall'=>'UNKNOWN']);

// ── 버전 정보 ────────────────────────────────────────────────────
case 'version':
    json_ok([
        'nos'      => 'wedge100-nos v0.1.0',
        'hardware' => 'Accton Wedge 100 (32×100G)',
        'asic'     => 'BCM56960 Tomahawk',
        'bmc'      => 'OpenBMC v14.1',
        'php'      => PHP_VERSION,
        'uptime'   => shell_exec('uptime -p') ?? '',
    ]);

default:
    json_err("알 수 없는 action: $action", 404);
}
