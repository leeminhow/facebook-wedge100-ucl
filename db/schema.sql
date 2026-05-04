-- ============================================================
-- wedge100-nos MySQL 스키마
-- 파일: db/schema.sql
-- 실행: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS wedge100nos
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE wedge100nos;

-- ── 포트 현재 상태 (LED 데몬이 주기적으로 갱신) ─────────────────
CREATE TABLE IF NOT EXISTS port_state (
    port_id      TINYINT UNSIGNED NOT NULL,   -- Front Panel 1-32
    ce_name      VARCHAR(8)  NOT NULL,         -- ce0..ce31
    link         TINYINT(1)  NOT NULL DEFAULT 0,
    speed        VARCHAR(8)  NULL,             -- 100G, 50G, 25G, 10G, NULL
    duplex       VARCHAR(4)  NULL,
    breakout     VARCHAR(8)  NOT NULL DEFAULT '1x100G',
    fec_enabled  TINYINT(1)  NOT NULL DEFAULT 1,
    admin_up     TINYINT(1)  NOT NULL DEFAULT 1,
    -- 서브 레인 링크 (breakout 4x25G / 2x50G 시 사용)
    lane0_link   TINYINT(1)  NOT NULL DEFAULT 0,
    lane1_link   TINYINT(1)  NOT NULL DEFAULT 0,
    lane2_link   TINYINT(1)  NOT NULL DEFAULT 0,
    lane3_link   TINYINT(1)  NOT NULL DEFAULT 0,
    updated_at   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (port_id)
) ENGINE=InnoDB;

-- ── QSFP 트랜시버 정보 (LED 데몬이 주기적으로 갱신) ─────────────
CREATE TABLE IF NOT EXISTS transceiver (
    port_id        TINYINT UNSIGNED NOT NULL,
    present        TINYINT(1) NOT NULL DEFAULT 0,
    connector_type VARCHAR(16) NULL,          -- QSFP28, QSFP+, SFP+
    vendor         VARCHAR(32) NULL,
    part_number    VARCHAR(32) NULL,
    serial         VARCHAR(32) NULL,
    wavelength_nm  SMALLINT   NULL,
    temp_celsius   DECIMAL(5,2) NULL,
    tx_power_dbm   DECIMAL(6,2) NULL,
    rx_power_dbm   DECIMAL(6,2) NULL,
    updated_at     TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP
                   ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (port_id)
) ENGINE=InnoDB;

-- ── LED 상태 및 깜빡이기 요청 (WebUI → LED 데몬) ────────────────
CREATE TABLE IF NOT EXISTS led_state (
    port_id    TINYINT UNSIGNED NOT NULL,
    lane       TINYINT UNSIGNED NOT NULL DEFAULT 0,  -- 0-3
    color      VARCHAR(16) NOT NULL DEFAULT 'off',
    blink      TINYINT(1)  NOT NULL DEFAULT 0,        -- WebUI 포트 인디케이터
    blink_until DATETIME   NULL,                      -- 깜빡이기 만료 시간
    override   TINYINT(1)  NOT NULL DEFAULT 0,        -- 수동 색상 고정 여부
    updated_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
               ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (port_id, lane)
) ENGINE=InnoDB;

-- ── VLAN ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vlan (
    vid        SMALLINT UNSIGNED NOT NULL,
    name       VARCHAR(32) NOT NULL DEFAULT '',
    created_at TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vid)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS vlan_port (
    vid      SMALLINT UNSIGNED NOT NULL,
    port_id  TINYINT UNSIGNED  NOT NULL,
    tagged   TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (vid, port_id),
    FOREIGN KEY (vid) REFERENCES vlan(vid) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── 포트 미러링 (SPAN) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mirror_session (
    session_id   TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name         VARCHAR(32) NOT NULL DEFAULT '',
    src_port     TINYINT UNSIGNED NOT NULL,   -- 원본 포트
    dst_port     TINYINT UNSIGNED NOT NULL,   -- 목적지 포트 (캡처)
    direction    ENUM('ingress','egress','both') NOT NULL DEFAULT 'both',
    active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id)
) ENGINE=InnoDB;

-- ── BGP 설정 ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bgp_config (
    id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    local_as    INT UNSIGNED NOT NULL,
    router_id   VARCHAR(16) NOT NULL,
    enabled     TINYINT(1)  NOT NULL DEFAULT 1,
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bgp_neighbor (
    id          SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    bgp_id      TINYINT UNSIGNED NOT NULL,
    peer_ip     VARCHAR(16) NOT NULL,
    remote_as   INT UNSIGNED NOT NULL,
    description VARCHAR(64) NULL,
    enabled     TINYINT(1)  NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    FOREIGN KEY (bgp_id) REFERENCES bgp_config(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── 포트 카운터 히스토리 (5분 단위 저장) ─────────────────────────
CREATE TABLE IF NOT EXISTS counter_history (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    port_id     TINYINT UNSIGNED NOT NULL,
    rx_packets  BIGINT UNSIGNED NOT NULL DEFAULT 0,
    tx_packets  BIGINT UNSIGNED NOT NULL DEFAULT 0,
    rx_bytes    BIGINT UNSIGNED NOT NULL DEFAULT 0,
    tx_bytes    BIGINT UNSIGNED NOT NULL DEFAULT 0,
    rx_errors   INT UNSIGNED    NOT NULL DEFAULT 0,
    recorded_at TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_port_time (port_id, recorded_at)
) ENGINE=InnoDB;

-- ── LLDP 이웃 (LED 데몬이 lldpcli 파싱 후 저장) ─────────────────
CREATE TABLE IF NOT EXISTS lldp_neighbor (
    local_port   TINYINT UNSIGNED NOT NULL,
    chassis_id   VARCHAR(64) NULL,
    chassis_name VARCHAR(64) NULL,
    port_id      VARCHAR(64) NULL,
    port_desc    VARCHAR(128) NULL,
    system_desc  VARCHAR(256) NULL,
    ttl          SMALLINT    NULL,
    updated_at   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (local_port)
) ENGINE=InnoDB;

-- ── 초기 데이터 삽입 ─────────────────────────────────────────────
INSERT IGNORE INTO port_state (port_id, ce_name)
SELECT n, CONCAT('ce', n-1)
FROM (
  SELECT (a.N + b.N*10 + 1) AS n
  FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION
        SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION
        SELECT 8 UNION SELECT 9) a,
       (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3) b
) nums
WHERE n BETWEEN 1 AND 32;

INSERT IGNORE INTO transceiver (port_id)
SELECT n FROM (
  SELECT (a.N + b.N*10 + 1) AS n
  FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION
        SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION
        SELECT 8 UNION SELECT 9) a,
       (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3) b
) nums WHERE n BETWEEN 1 AND 32;

INSERT IGNORE INTO led_state (port_id, lane)
SELECT p.port_id, l.lane
FROM (SELECT port_id FROM port_state) p
CROSS JOIN (SELECT 0 AS lane UNION SELECT 1 UNION SELECT 2 UNION SELECT 3) l;

-- ── DB 사용자 생성 ────────────────────────────────────────────────
-- (필요에 따라 비밀번호 변경)
CREATE USER IF NOT EXISTS 'wedge100'@'localhost' IDENTIFIED BY 'wedge100nos!';
GRANT ALL PRIVILEGES ON wedge100nos.* TO 'wedge100'@'localhost';
FLUSH PRIVILEGES;
