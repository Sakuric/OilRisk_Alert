"""
OilRisk-Alert Python 推理服务 (FastAPI)
启动: uvicorn app:app --host 0.0.0.0 --port 5000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from engine import OilRiskEngine

logger = logging.getLogger("oilrisk")
logging.basicConfig(level=logging.INFO)

engine: OilRiskEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    logger.info("Loading models...")
    engine = OilRiskEngine()
    logger.info("Models loaded successfully")
    yield
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
        return engine.predict_daily()
    except Exception as e:
        logger.exception("predict_daily failed")
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
