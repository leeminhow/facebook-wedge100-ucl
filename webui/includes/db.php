<?php
// webui/includes/db.php
// MySQL 연결 및 공용 유틸리티

define('DB_HOST', 'localhost');
define('DB_USER', 'wedge100');
define('DB_PASS', 'wedge100nos!');
define('DB_NAME', 'wedge100nos');

function db(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $pdo = new PDO(
                "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
                DB_USER, DB_PASS,
                [
                    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                    PDO::ATTR_PERSISTENT         => true,
                ]
            );
        } catch (PDOException $e) {
            http_response_code(500);
            die(json_encode(['error' => 'DB 연결 실패: ' . $e->getMessage()]));
        }
    }
    return $pdo;
}

// CLI 래퍼: wedge 커맨드 실행
function wedge_cmd(string $cmd): array {
    $full = "PYTHONPATH=/usr/local/wedge100-nos /usr/local/bin/wedge " . escapeshellcmd($cmd) . " 2>&1";
    $output = shell_exec($full);
    return ['output' => $output ?? '', 'cmd' => $cmd];
}

// JSON 응답
function json_ok(mixed $data): void {
    header('Content-Type: application/json');
    echo json_encode(['ok' => true, 'data' => $data]);
    exit;
}

function json_err(string $msg, int $code = 400): void {
    http_response_code($code);
    header('Content-Type: application/json');
    echo json_encode(['ok' => false, 'error' => $msg]);
    exit;
}

// 정수 입력 검증
function req_int(string $key, int $min = 0, int $max = PHP_INT_MAX): int {
    $val = isset($_POST[$key]) ? (int)$_POST[$key] : (isset($_GET[$key]) ? (int)$_GET[$key] : null);
    if ($val === null || $val < $min || $val > $max) {
        json_err("파라미터 오류: $key (범위: $min-$max)");
    }
    return $val;
}

function req_str(string $key, array $allowed = []): string {
    $val = trim($_POST[$key] ?? $_GET[$key] ?? '');
    if ($val === '') json_err("파라미터 없음: $key");
    if ($allowed && !in_array($val, $allowed, true)) {
        json_err("파라미터 오류: $key = $val");
    }
    return $val;
}
