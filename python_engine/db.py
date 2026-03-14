"""
OilRisk-Alert 数据库访问层
使用 SQLAlchemy + PyMySQL 实现 MySQL 连接池和 CRUD 操作。
"""

import json
import logging
import os
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logger = logging.getLogger("oilrisk.db")

# ── 数据库配置（从环境变量读取，有默认值）──
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "oilrisk")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "123456")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

Base = declarative_base()

# ── ORM 模型 ──


class FactorRealtime(Base):
    __tablename__ = "factor_realtime"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    factor_key = Column(String(100), nullable=False)
    column_name = Column(String(255), nullable=False)
    value = Column(Numeric(20, 6))
    source = Column(String(50), nullable=False)
    frequency = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CollectionLog(Base):
    __tablename__ = "collection_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_date = Column(Date, nullable=False)
    source = Column(String(50), nullable=False)
    status = Column(Enum("SUCCESS", "PARTIAL", "FAILED"), nullable=False)
    factors_total = Column(Integer, default=0)
    factors_ok = Column(Integer, default=0)
    factors_failed = Column(Integer, default=0)
    error_detail = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)


class SystemState(Base):
    __tablename__ = "system_state"

    state_key = Column(String(100), primary_key=True)
    state_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ── 连接池管理 ──

_engine = None
_SessionFactory = None


def get_engine():
    """获取或创建 SQLAlchemy Engine（连接池）。"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
        )
        logger.info("Database engine created: %s:%s/%s", DB_HOST, DB_PORT, DB_NAME)
    return _engine


def get_session() -> Session:
    """获取一个新的数据库 Session。使用方自行管理 commit/close。"""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory()


# ── 因子数据 CRUD ──


def upsert_factor(
    dt: date,
    factor_key: str,
    column_name: str,
    value: float | None,
    source: str,
    frequency: str,
) -> bool:
    """插入或更新单条因子数据。成功返回 True。"""
    session = get_session()
    try:
        existing = (
            session.query(FactorRealtime)
            .filter_by(date=dt, factor_key=factor_key)
            .first()
        )
        if existing:
            existing.value = value
            existing.column_name = column_name
            existing.source = source
            existing.frequency = frequency
            existing.updated_at = datetime.now()
        else:
            record = FactorRealtime(
                date=dt,
                factor_key=factor_key,
                column_name=column_name,
                value=value,
                source=source,
                frequency=frequency,
            )
            session.add(record)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error("upsert_factor failed [%s/%s]: %s", dt, factor_key, e)
        return False
    finally:
        session.close()


def batch_upsert_factors(records: list[dict]) -> int:
    """
    批量写入因子数据。
    records: [{"date", "factor_key", "column_name", "value", "source", "frequency"}, ...]
    返回成功写入条数。
    """
    if not records:
        return 0

    session = get_session()
    success_count = 0
    try:
        for rec in records:
            existing = (
                session.query(FactorRealtime)
                .filter_by(date=rec["date"], factor_key=rec["factor_key"])
                .first()
            )
            if existing:
                existing.value = rec.get("value")
                existing.column_name = rec["column_name"]
                existing.source = rec["source"]
                existing.frequency = rec["frequency"]
                existing.updated_at = datetime.now()
            else:
                session.add(FactorRealtime(**rec))
            success_count += 1
        session.commit()
        logger.info("batch_upsert_factors: %d records written", success_count)
    except Exception as e:
        session.rollback()
        logger.error("batch_upsert_factors failed: %s", e)
        success_count = 0
    finally:
        session.close()
    return success_count


def get_latest_factors(dt: date | None = None) -> dict[str, dict]:
    """
    获取指定日期全部因子，默认取最新日期。
    返回: {factor_key: {"value": float, "date": date, "column_name": str, ...}}
    """
    session = get_session()
    try:
        if dt is None:
            row = session.query(FactorRealtime.date).order_by(
                FactorRealtime.date.desc()
            ).first()
            if row is None:
                return {}
            dt = row[0]

        rows = session.query(FactorRealtime).filter_by(date=dt).all()
        result = {}
        for r in rows:
            result[r.factor_key] = {
                "value": float(r.value) if r.value is not None else None,
                "date": r.date,
                "column_name": r.column_name,
                "source": r.source,
                "frequency": r.frequency,
            }
        return result
    except Exception as e:
        logger.error("get_latest_factors failed: %s", e)
        return {}
    finally:
        session.close()


def get_all_factors_since(start_date: date) -> dict[date, dict[str, float]]:
    """
    获取 factor_realtime 中 start_date 之后所有日期的因子数据。
    返回: {date: {column_name: value, ...}, ...}
    """
    session = get_session()
    try:
        rows = (
            session.query(FactorRealtime)
            .filter(FactorRealtime.date >= start_date)
            .order_by(FactorRealtime.date.asc())
            .all()
        )
        result: dict[date, dict[str, float]] = {}
        for r in rows:
            dt = r.date
            if dt not in result:
                result[dt] = {}
            if r.value is not None and r.column_name:
                result[dt][r.column_name] = float(r.value)
        logger.info("get_all_factors_since(%s): %d dates, %d records", start_date, len(result), len(rows))
        return result
    except Exception as e:
        logger.error("get_all_factors_since failed: %s", e)
        return {}
    finally:
        session.close()


def get_factor_dates(start_date: date, end_date: date) -> set[str]:
    """
    查询 factor_realtime 表中在 [start_date, end_date] 范围内
    已有数据的日期集合（至少有5条因子数据的日期才算有效）。
    """
    session = get_session()
    try:
        from sqlalchemy import func
        rows = (
            session.query(FactorRealtime.date)
            .filter(FactorRealtime.date >= start_date)
            .filter(FactorRealtime.date <= end_date)
            .group_by(FactorRealtime.date)
            .having(func.count(FactorRealtime.id) >= 5)
            .all()
        )
        return {str(r[0]) for r in rows}
    except Exception as e:
        logger.error("get_factor_dates failed: %s", e)
        return set()
    finally:
        session.close()


# ── 采集日志 ──


def insert_collection_log(
    run_date: date,
    source: str,
    status: str,
    factors_total: int = 0,
    factors_ok: int = 0,
    factors_failed: int = 0,
    error_detail: dict | None = None,
    duration_ms: int | None = None,
) -> int | None:
    """写入一条采集日志，返回日志 ID。"""
    session = get_session()
    try:
        log = CollectionLog(
            run_date=run_date,
            source=source,
            status=status,
            factors_total=factors_total,
            factors_ok=factors_ok,
            factors_failed=factors_failed,
            error_detail=json.dumps(error_detail, ensure_ascii=False) if error_detail else None,
            duration_ms=duration_ms,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log.id
    except Exception as e:
        session.rollback()
        logger.error("insert_collection_log failed: %s", e)
        return None
    finally:
        session.close()


def get_collection_logs(limit: int = 20) -> list[dict]:
    """查询最近 N 条采集日志。"""
    session = get_session()
    try:
        rows = (
            session.query(CollectionLog)
            .order_by(CollectionLog.created_at.desc())
            .limit(limit)
            .all()
        )
        result = []
        for r in rows:
            result.append({
                "id": r.id,
                "run_date": str(r.run_date),
                "source": r.source,
                "status": r.status,
                "factors_total": r.factors_total,
                "factors_ok": r.factors_ok,
                "factors_failed": r.factors_failed,
                "error_detail": json.loads(r.error_detail) if r.error_detail else None,
                "duration_ms": r.duration_ms,
                "created_at": str(r.created_at) if r.created_at else None,
            })
        return result
    except Exception as e:
        logger.error("get_collection_logs failed: %s", e)
        return []
    finally:
        session.close()


# ── 系统状态 ──


def get_system_state(key: str) -> str | None:
    """读取系统状态值。"""
    session = get_session()
    try:
        row = session.query(SystemState).filter_by(state_key=key).first()
        return row.state_value if row else None
    except Exception as e:
        logger.error("get_system_state failed [%s]: %s", key, e)
        return None
    finally:
        session.close()


def set_system_state(key: str, value: str) -> bool:
    """设置系统状态值（upsert）。"""
    session = get_session()
    try:
        row = session.query(SystemState).filter_by(state_key=key).first()
        if row:
            row.state_value = value
            row.updated_at = datetime.now()
        else:
            session.add(SystemState(state_key=key, state_value=value))
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error("set_system_state failed [%s]: %s", key, e)
        return False
    finally:
        session.close()


# ── 推理结果持久化（risk_index / risk_factor） ──


def upsert_risk_index(
    dt: date,
    risk_index_val: float,
    risk_level: str,
    oil_price: float | None = None,
) -> bool:
    """
    将推理结果写入 risk_index 表（upsert by date）。
    前端 RiskOverview、时间序列图表均从此表读取。
    """
    session = get_session()
    try:
        row = session.execute(
            text("SELECT id FROM risk_index WHERE `date` = :dt"),
            {"dt": dt},
        ).fetchone()

        if row:
            session.execute(
                text("""
                    UPDATE risk_index
                    SET risk_index = :ri, risk_level = :rl, oil_price = :op
                    WHERE `date` = :dt
                """),
                {"ri": risk_index_val, "rl": risk_level, "op": oil_price, "dt": dt},
            )
        else:
            session.execute(
                text("""
                    INSERT INTO risk_index (`date`, risk_index, risk_level, oil_price)
                    VALUES (:dt, :ri, :rl, :op)
                """),
                {"dt": dt, "ri": risk_index_val, "rl": risk_level, "op": oil_price},
            )
        session.commit()
        logger.info("upsert_risk_index: date=%s, score=%.2f, level=%s", dt, risk_index_val, risk_level)
        return True
    except Exception as e:
        session.rollback()
        logger.error("upsert_risk_index failed: %s", e)
        return False
    finally:
        session.close()


def upsert_risk_factors(dt: date, top_factors: list[dict]) -> int:
    """
    将 SHAP top factors 写入 risk_factor 表。
    top_factors: [{"name", "shap_value", "value", "category"}, ...]
    """
    if not top_factors:
        return 0

    session = get_session()
    count = 0
    try:
        session.execute(
            text("DELETE FROM risk_factor WHERE `date` = :dt"),
            {"dt": dt},
        )

        for f in top_factors:
            name = f.get("name", "")
            name_zh = f.get("name_zh", name)
            category = f.get("category", "OTHER")
            value = f.get("value")
            shap_val = f.get("shap_value")

            session.execute(
                text("""
                    INSERT INTO risk_factor (`date`, factor_name, factor_name_zh, category, `value`, shap_value)
                    VALUES (:dt, :fn, :fnz, :cat, :val, :shap)
                """),
                {
                    "dt": dt, "fn": name, "fnz": name_zh,
                    "cat": category, "val": value, "shap": shap_val,
                },
            )
            count += 1

        session.commit()
        logger.info("upsert_risk_factors: date=%s, %d factors written", dt, count)
    except Exception as e:
        session.rollback()
        logger.error("upsert_risk_factors failed: %s", e)
        count = 0
    finally:
        session.close()
    return count


def persist_prediction(prediction_result: dict) -> bool:
    """
    将 predict_daily() 的完整结果持久化到 risk_index + risk_factor 表。
    同时根据风险阈值自动生成预警记录到 alert 表。
    """
    if not prediction_result:
        return False

    dashboard = prediction_result.get("dashboard", {})
    score = dashboard.get("score")
    level = dashboard.get("level")
    date_str = dashboard.get("date")

    if score is None or level is None or date_str is None:
        logger.warning("persist_prediction: incomplete dashboard data")
        return False

    dt = datetime.strptime(date_str, "%Y-%m-%d").date()

    oil_price = None
    expert = prediction_result.get("expert_signals", {})
    if "lstm_pred_price" in expert:
        oil_price = expert["lstm_pred_price"]

    ok1 = upsert_risk_index(dt, float(score), level, oil_price)

    top_factors = prediction_result.get("top_factors", [])
    ok2 = upsert_risk_factors(dt, top_factors) > 0 if top_factors else True

    # 自动生成预警记录
    try:
        _auto_generate_alert(dt, float(score), level, top_factors)
    except Exception as e:
        logger.error("auto_generate_alert failed: %s", e)

    return ok1 and ok2


def _auto_generate_alert(
    dt: date,
    risk_score: float,
    risk_level: str,
    top_factors: list[dict],
) -> None:
    """
    根据风险阈值自动生成预警记录。
    - High: risk_score >= 65
    - Medium: risk_score >= 45
    - Low: risk_score >= 30
    已存在同日同级别预警则跳过。
    """
    if risk_score < 30:
        return

    if risk_score >= 65:
        alert_level = "High"
    elif risk_score >= 45:
        alert_level = "Medium"
    else:
        alert_level = "Low"

    session = get_session()
    try:
        # 检查同日是否已有该级别预警
        existing = session.execute(
            text("SELECT id FROM alert WHERE `date` = :dt AND level = :lv LIMIT 1"),
            {"dt": dt, "lv": alert_level},
        ).fetchone()
        if existing:
            return

        # 获取 top factor 信息
        trigger_factor = ""
        trigger_factor_zh = ""
        if top_factors:
            tf = top_factors[0]
            trigger_factor = tf.get("name", "")
            trigger_factor_zh = tf.get("name_zh", trigger_factor)

        summary_zh = f"风险指数达到 {risk_score:.1f}，触发{alert_level}级预警。主导因子: {trigger_factor_zh or trigger_factor}"
        summary_en = f"Risk index reached {risk_score:.1f}, triggering {alert_level} alert. Key factor: {trigger_factor}"

        detail = json.dumps({
            "risk_score": risk_score,
            "risk_level": risk_level,
            "top_factors": top_factors[:5] if top_factors else [],
        }, ensure_ascii=False)

        session.execute(
            text("""
                INSERT INTO alert (`date`, level, risk_index, trigger_type,
                                   trigger_factor, trigger_factor_zh,
                                   summary, summary_en, detail)
                VALUES (:dt, :lv, :ri, :tt, :tf, :tfz, :sm, :sme, :det)
            """),
            {
                "dt": dt, "lv": alert_level, "ri": risk_score,
                "tt": "THRESHOLD", "tf": trigger_factor, "tfz": trigger_factor_zh,
                "sm": summary_zh, "sme": summary_en, "det": detail,
            },
        )
        session.commit()
        logger.info("Auto-generated %s alert for date=%s, score=%.1f", alert_level, dt, risk_score)
    except Exception as e:
        session.rollback()
        logger.error("_auto_generate_alert failed: %s", e)
    finally:
        session.close()
