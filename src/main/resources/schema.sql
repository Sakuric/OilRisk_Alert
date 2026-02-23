-- ============================================
-- Schema for OilRisk-Alert (H2 Database)
-- ============================================

DROP TABLE IF EXISTS alert;
DROP TABLE IF EXISTS risk_factor;
DROP TABLE IF EXISTS risk_index;

CREATE TABLE risk_index (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    risk_index DECIMAL(5,2) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    oil_price DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE risk_factor (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    factor_name VARCHAR(50) NOT NULL,
    factor_name_zh VARCHAR(50) NOT NULL,
    category VARCHAR(20) NOT NULL,
    "value" DECIMAL(10,4),
    shap_value DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE alert (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    level VARCHAR(10) NOT NULL,
    risk_index DECIMAL(5,2) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL,
    trigger_factor VARCHAR(50),
    trigger_factor_zh VARCHAR(50),
    summary VARCHAR(500),
    summary_en VARCHAR(500),
    detail TEXT,
    ai_report TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
