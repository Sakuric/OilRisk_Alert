-- ============================================
-- Schema for OilRisk-Alert (MySQL)
-- 注意：使用 CREATE TABLE IF NOT EXISTS 保留已有数据
-- ============================================

CREATE TABLE IF NOT EXISTS risk_index (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `date` DATE NOT NULL UNIQUE,
    risk_index DECIMAL(5,2) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    oil_price DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS risk_factor (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `date` DATE NOT NULL,
    factor_name VARCHAR(50) NOT NULL,
    factor_name_zh VARCHAR(50) NOT NULL,
    category VARCHAR(20) NOT NULL,
    `value` DECIMAL(16,4),
    shap_value DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS alert (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `date` DATE NOT NULL,
    level VARCHAR(10) NOT NULL,
    risk_index DECIMAL(5,2) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL,
    trigger_factor VARCHAR(50),
    trigger_factor_zh VARCHAR(50),
    summary VARCHAR(500),
    summary_en VARCHAR(500),
    detail TEXT,
    ai_report TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 实时因子采集相关表
-- ============================================

CREATE TABLE IF NOT EXISTS factor_realtime (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    `date`      DATE NOT NULL,
    factor_key  VARCHAR(100) NOT NULL COMMENT '标准化因子标识，如 WTI_CLOSE, VIX_INDEX',
    column_name VARCHAR(255) NOT NULL COMMENT '对应 CSV 原始列名',
    `value`     DECIMAL(20, 6) COMMENT '因子值',
    source      VARCHAR(50) NOT NULL COMMENT '数据来源: yfinance/fred/eia/gdelt',
    frequency   VARCHAR(10) NOT NULL COMMENT '频率: daily/weekly/monthly',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_factor (`date`, factor_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实时因子数据';

CREATE TABLE IF NOT EXISTS collection_log (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_date       DATE NOT NULL,
    source         VARCHAR(50) NOT NULL,
    status         ENUM('SUCCESS', 'PARTIAL', 'FAILED') NOT NULL,
    factors_total  INT DEFAULT 0 COMMENT '应采集因子数',
    factors_ok     INT DEFAULT 0 COMMENT '成功采集数',
    factors_failed INT DEFAULT 0 COMMENT '失败因子数',
    error_detail   TEXT COMMENT '失败因子及原因 JSON',
    duration_ms    INT COMMENT '采集耗时(ms)',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集日志';

CREATE TABLE IF NOT EXISTS system_state (
    state_key   VARCHAR(100) PRIMARY KEY,
    state_value TEXT NOT NULL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统状态键值表';

-- 预置系统状态记录
INSERT IGNORE INTO system_state (state_key, state_value) VALUES
('last_collection_time', ''),
('last_prediction_time', ''),
('last_collection_status', 'INIT'),
('data_date', '');
