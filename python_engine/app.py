"""
OilRisk-Alert Python 推理服务 (FastAPI)
启动: uvicorn app:app --host 0.0.0.0 --port 5000
"""

from dotenv import load_dotenv
load_dotenv()

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from engine import OilRiskEngine

logger = logging.getLogger("oilrisk")
logging.basicConfig(level=logging.INFO)

engine: OilRiskEngine | None = None
_collect_lock = threading.Lock()
_collect_running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    logger.info("Loading models...")
    engine = OilRiskEngine()
    logger.info("Models loaded successfully")

    # 启动 APScheduler
    try:
        from collector.scheduler import (
            start_scheduler, set_engine_ref, collect_all,
            detect_and_backfill,
        )
        set_engine_ref(engine)
        start_scheduler()
        logger.info("APScheduler started")

        # 启动时自动检测缺口并回填
        if os.environ.get("BACKFILL_ON_STARTUP", "true").lower() == "true":
            logger.info("Checking for data gaps...")
            try:
                from collector.scheduler import detect_data_gaps
                gaps = detect_data_gaps(lookback_days=90)
                if gaps:
                    logger.info("Found %d missing trading days, starting backfill...", len(gaps))
                    detect_and_backfill(lookback_days=90)
                else:
                    logger.info("No data gaps detected")
            except Exception as e:
                logger.error("Startup backfill failed: %s", e)

        # 启动时是否立即采集一次
        if os.environ.get("COLLECT_ON_STARTUP", "false").lower() == "true":
            logger.info("COLLECT_ON_STARTUP=true, running initial collection...")
            try:
                collect_all()
            except Exception as e:
                logger.error("Startup collection failed: %s", e)
    except Exception as e:
        logger.warning("Scheduler setup failed (non-fatal): %s", e)

    yield

    # 停止调度器
    try:
        from collector.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    engine = None


app = FastAPI(title="OilRisk Prediction Engine", lifespan=lifespan)


class BacktestRequest(BaseModel):
    startDate: str
    endDate: str
    model: str  # "XGBoost" | "LSTM" | "Stacking"


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": engine is not None}


@app.post("/predict/daily")
def predict_daily():
    if engine is None:
        raise HTTPException(503, "Engine not initialized")
    try:
        # 先从 DB 加载最新因子数据，合并到历史数据后再推理
        result = engine.reload_from_db()
        # 持久化推理结果到 risk_index + risk_factor 表
        if result:
            try:
                import db
                db.persist_prediction(result)
            except Exception as e:
                logger.error("persist_prediction failed: %s", e)
        return result
    except Exception as e:
        logger.exception("predict_daily failed")
        raise HTTPException(500, str(e))


@app.get("/shap/factors")
def shap_factors():
    if engine is None:
        raise HTTPException(503, "Engine not initialized")
    try:
        return engine.get_all_shap_factors()
    except Exception as e:
        logger.exception("shap_factors failed")
        raise HTTPException(500, str(e))


@app.post("/predict/backtest")
def predict_backtest(req: BacktestRequest):
    if engine is None:
        raise HTTPException(503, "Engine not initialized")
    valid_models = {"XGBoost", "LSTM", "Stacking"}
    if req.model not in valid_models:
        raise HTTPException(400, f"model must be one of: {valid_models}")
    try:
        result = engine.predict_backtest(req.startDate, req.endDate, req.model)
    except Exception as e:
        logger.exception("predict_backtest failed")
        raise HTTPException(500, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════
# 数据采集相关接口
# ═══════════════════════════════════════


@app.post("/collect/trigger")
def collect_trigger():
    """手动触发全量采集 + 推理（后台异步执行，立即返回）。"""
    global _collect_running
    if engine is None:
        raise HTTPException(503, "Engine not initialized")

    with _collect_lock:
        if _collect_running:
            return {
                "status": "already_running",
                "message": "A collection task is already running. Check /collect/status for progress.",
            }
        _collect_running = True

    # 标记系统状态为 RUNNING
    try:
        import db as _db
        _db.set_system_state("last_collection_status", "RUNNING")
    except Exception:
        pass

    def _background_collect():
        global _collect_running
        try:
            from collector.scheduler import collect_all
            result = collect_all()
            logger.info("Background collect completed: %s", result.get("status", "UNKNOWN"))
        except Exception as e:
            logger.exception("Background collect_trigger failed")
            try:
                import db as _db2
                _db2.set_system_state("last_collection_status", "FAILED")
            except Exception:
                pass
        finally:
            _collect_running = False

    thread = threading.Thread(target=_background_collect, daemon=True)
    thread.start()

    return {
        "status": "started",
        "message": "Collection started in background. Poll /collect/status for results.",
    }


@app.get("/collect/status")
def collect_status():
    """查询最近一次采集状态。"""
    try:
        import db

        last_collection_time = db.get_system_state("last_collection_time") or ""
        last_collection_status = db.get_system_state("last_collection_status") or "INIT"
        last_prediction_time = db.get_system_state("last_prediction_time") or ""
        data_date = db.get_system_state("data_date") or ""

        # 计算下次调度时间
        next_scheduled = ""
        try:
            from collector.scheduler import scheduler
            jobs = scheduler.get_jobs()
            if jobs:
                next_runs = [j.next_run_time for j in jobs if j.next_run_time]
                if next_runs:
                    next_scheduled = str(min(next_runs).strftime("%Y-%m-%dT%H:%M:%S"))
        except Exception:
            pass

        # 因子覆盖率统计
        from collector.registry import FACTOR_REGISTRY, get_factors_by_frequency
        daily_factors = get_factors_by_frequency("daily")
        weekly_factors = get_factors_by_frequency("weekly")
        monthly_factors = get_factors_by_frequency("monthly")

        # 查询实际可用因子数
        daily_available = 0
        weekly_available = 0
        monthly_available = 0

        if data_date:
            from datetime import datetime
            try:
                dt = datetime.strptime(data_date, "%Y-%m-%d").date()
                latest = db.get_latest_factors(dt)
                for fk in latest:
                    meta = FACTOR_REGISTRY.get(fk, {})
                    freq = meta.get("frequency", "")
                    if freq == "daily":
                        daily_available += 1
                    elif freq == "weekly":
                        weekly_available += 1
                    elif freq == "monthly":
                        monthly_available += 1
            except Exception:
                pass

        return {
            "last_collection_time": last_collection_time,
            "last_collection_status": last_collection_status,
            "last_prediction_time": last_prediction_time,
            "data_date": data_date,
            "next_scheduled": next_scheduled,
            "factors_coverage": {
                "daily": {"total": len(daily_factors), "available": daily_available},
                "weekly": {"total": len(weekly_factors), "available": weekly_available},
                "monthly": {"total": len(monthly_factors), "available": monthly_available},
            },
        }
    except ImportError:
        return {
            "last_collection_time": "",
            "last_collection_status": "UNAVAILABLE",
            "last_prediction_time": "",
            "data_date": "",
            "next_scheduled": "",
            "factors_coverage": {},
        }
    except Exception as e:
        logger.exception("collect_status failed")
        raise HTTPException(500, str(e))


@app.get("/collect/log")
def collect_log(limit: int = Query(default=20, ge=1, le=100)):
    """查询采集日志。"""
    try:
        import db
        logs = db.get_collection_logs(limit=limit)
        return logs
    except ImportError:
        return []
    except Exception as e:
        logger.exception("collect_log failed")
        raise HTTPException(500, str(e))


class BackfillRequest(BaseModel):
    startDate: str
    endDate: str


@app.post("/collect/backfill")
def collect_backfill(req: BackfillRequest):
    """
    手动触发指定日期范围的历史数据回填。
    会对范围内每个交易日依次执行全量采集。
    """
    if engine is None:
        raise HTTPException(503, "Engine not initialized")
    try:
        from collector.scheduler import backfill_range
        result = backfill_range(req.startDate, req.endDate)
        return result
    except Exception as e:
        logger.exception("collect_backfill failed")
        raise HTTPException(500, str(e))


@app.get("/collect/gaps")
def collect_gaps(lookback_days: int = Query(default=90, ge=1, le=365)):
    """检测最近 N 天内的数据缺口。"""
    try:
        from collector.scheduler import detect_data_gaps
        missing = detect_data_gaps(lookback_days)
        return {
            "lookback_days": lookback_days,
            "missing_count": len(missing),
            "missing_dates": missing,
        }
    except Exception as e:
        logger.exception("collect_gaps failed")
        raise HTTPException(500, str(e))


@app.post("/collect/auto-backfill")
def collect_auto_backfill(lookback_days: int = Query(default=90, ge=1, le=365)):
    """自动检测缺口并回填。"""
    if engine is None:
        raise HTTPException(503, "Engine not initialized")
    try:
        from collector.scheduler import detect_and_backfill
        result = detect_and_backfill(lookback_days)
        return result
    except Exception as e:
        logger.exception("collect_auto_backfill failed")
        raise HTTPException(500, str(e))
