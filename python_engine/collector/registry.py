"""
因子注册表 — 定义所有因子的采集参数映射。
factor_key → {collector, 数据源参数, column_name, frequency, priority}
"""

# ═══════════════════════════════════════
# 因子注册表
# ═══════════════════════════════════════

FACTOR_REGISTRY: dict[str, dict] = {
    # ──────────────────────────────────────
    # P0: 核心日频因子（三模型均使用）
    # ──────────────────────────────────────

    # WTI 原油期货
    "WTI_CLOSE": {
        "collector": "yfinance",
        "ticker": "CL=F",
        "field": "Close",
        "column_name": "Price_WTI_WTI期货_close",
        "frequency": "daily",
        "priority": "P0",
    },
    "WTI_OPEN": {
        "collector": "yfinance",
        "ticker": "CL=F",
        "field": "Open",
        "column_name": "Price_WTI_WTI期货_open",
        "frequency": "daily",
        "priority": "P0",
    },
    "WTI_HIGH": {
        "collector": "yfinance",
        "ticker": "CL=F",
        "field": "High",
        "column_name": "Price_WTI_WTI期货_high",
        "frequency": "daily",
        "priority": "P0",
    },
    "WTI_LOW": {
        "collector": "yfinance",
        "ticker": "CL=F",
        "field": "Low",
        "column_name": "Price_WTI_WTI期货_low",
        "frequency": "daily",
        "priority": "P0",
    },
    "WTI_VOLUME": {
        "collector": "yfinance",
        "ticker": "CL=F",
        "field": "Volume",
        "column_name": "Price_WTI_WTI期货_volume",
        "frequency": "daily",
        "priority": "P0",
    },

    # VIX 恐慌指数
    "VIX_INDEX": {
        "collector": "yfinance",
        "ticker": "^VIX",
        "field": "Close",
        "column_name": "Risk_VIX_VIX恐慌指数_VIX_Index",
        "frequency": "daily",
        "priority": "P0",
    },
    "VIX_VALUE": {
        "collector": "yfinance",
        "ticker": "^VIX",
        "field": "Close",
        "column_name": "Risk_VIX_情绪组_VIX__Value",
        "frequency": "daily",
        "priority": "P0",
    },

    # OVX 原油波动率
    "OVX_VALUE": {
        "collector": "yfinance",
        "ticker": "^OVX",
        "field": "Close",
        "column_name": "Risk_VIX_情绪组_OVX__Value",
        "frequency": "daily",
        "priority": "P0",
    },

    # 标普500
    "SP500_CLOSE": {
        "collector": "yfinance",
        "ticker": "^GSPC",
        "field": "Close",
        "column_name": "Macro_SP500_标普500指数_SP500_Close",
        "frequency": "daily",
        "priority": "P0",
    },

    # 美元指数
    "USD_INDEX": {
        "collector": "yfinance",
        "ticker": "DX-Y.NYB",
        "field": "Close",
        "column_name": "美元指数_日频",
        "frequency": "daily",
        "priority": "P0",
    },

    # CRB 商品指数（使用 DBC ETF 作为替代，^CRB 已退市）
    "CRB_INDEX": {
        "collector": "yfinance",
        "ticker": "DBC",
        "field": "Close",
        "column_name": "CRB现货指数_日频",
        "frequency": "daily",
        "priority": "P0",
    },

    # 美债10年收益率 (FRED)
    "US_10Y_YIELD": {
        "collector": "fred",
        "series_id": "DGS10",
        "column_name": "Macro_Yield_美债10年收益率_US_10Y_Treasury_Yield",
        "frequency": "daily",
        "priority": "P0",
    },

    # 10年通胀预期 (FRED)
    "T10YIE": {
        "collector": "fred",
        "series_id": "T10YIE",
        "column_name": "Macro_CPI_10年期通胀预期_T10YIE",
        "frequency": "daily",
        "priority": "P0",
    },

    # ──────────────────────────────────────
    # P1: 重要日频因子（XGBoost / Stacking 使用）
    # ──────────────────────────────────────

    # Brent 原油期货
    "BRENT_CLOSE": {
        "collector": "yfinance",
        "ticker": "BZ=F",
        "field": "Close",
        "column_name": "Price_Brent_布伦特原油期货_close",
        "frequency": "daily",
        "priority": "P1",
    },
    "BRENT_VOLUME": {
        "collector": "yfinance",
        "ticker": "BZ=F",
        "field": "Volume",
        "column_name": "Price_Brent_布伦特原油期货_volume",
        "frequency": "daily",
        "priority": "P1",
    },

    # RBOB 汽油期货
    "RBOB_CLOSE": {
        "collector": "yfinance",
        "ticker": "RB=F",
        "field": "Close",
        "column_name": "Price_RBOB_RBOB汽油期货_close",
        "frequency": "daily",
        "priority": "P1",
    },
    "RBOB_VOLUME": {
        "collector": "yfinance",
        "ticker": "RB=F",
        "field": "Volume",
        "column_name": "Price_RBOB_RBOB汽油期货_volume",
        "frequency": "daily",
        "priority": "P1",
    },

    # 取暖油期货
    "HEATING_OIL_CLOSE": {
        "collector": "yfinance",
        "ticker": "HO=F",
        "field": "Close",
        "column_name": "Price_Fuel_取暖油期货_close",
        "frequency": "daily",
        "priority": "P1",
    },
    "HEATING_OIL_VOLUME": {
        "collector": "yfinance",
        "ticker": "HO=F",
        "field": "Volume",
        "column_name": "Price_Fuel_取暖油期货_volume",
        "frequency": "daily",
        "priority": "P1",
    },

    # 天然气期货
    "NATGAS_CLOSE": {
        "collector": "yfinance",
        "ticker": "NG=F",
        "field": "Close",
        "column_name": "Price_Gas_天然气期货_close",
        "frequency": "daily",
        "priority": "P1",
    },
    "NATGAS_VOLUME": {
        "collector": "yfinance",
        "ticker": "NG=F",
        "field": "Volume",
        "column_name": "Price_Gas_天然气期货_volume",
        "frequency": "daily",
        "priority": "P1",
    },

    # 黄金
    "GOLD_VALUE": {
        "collector": "yfinance",
        "ticker": "GC=F",
        "field": "Close",
        "column_name": "情绪组_GOLD_Value",
        "frequency": "daily",
        "priority": "P1",
    },

    # 高收益利差 (FRED)
    "HY_SPREAD": {
        "collector": "fred",
        "series_id": "BAMLH0A0HYM2",
        "column_name": "情绪组_HY_S_Value",
        "frequency": "daily",
        "priority": "P1",
    },

    # 美债2年收益率 (FRED)
    "US_2Y_YIELD": {
        "collector": "fred",
        "series_id": "DGS2",
        "column_name": "Macro_Yield_美债2年收益率_US_2Y_Treasury_Yield",
        "frequency": "daily",
        "priority": "P1",
    },

    # 联邦基金利率 (FRED)
    "FED_FUNDS_RATE": {
        "collector": "fred",
        "series_id": "DFF",
        "column_name": "联邦基金利率_EFFR",
        "frequency": "daily",
        "priority": "P1",
    },

    # 欧元兑美元 (FRED)
    "EURUSD": {
        "collector": "fred",
        "series_id": "DEXUSEU",
        "column_name": "Macro_ExchangeRate_EURUSD一欧_DEXUSEU",
        "frequency": "daily",
        "priority": "P1",
    },

    # ──────────────────────────────────────
    # P2: 周频/月频因子
    # ──────────────────────────────────────

    # 库欣库存 (EIA - 周频)
    "CUSHING_INVENTORY": {
        "collector": "eia",
        "series_id": "PET.WCSSTUS1.W",
        "column_name": "Supply_Inventory_US_Cushing__Value (库存)",
        "frequency": "weekly",
        "priority": "P2",
    },

    # 美国商业原油库存 (EIA - 周频)
    "US_CRUDE_INVENTORY": {
        "collector": "eia",
        "series_id": "PET.WCESTUS1.W",
        "column_name": "US_Crude_Oil_Commercial_Inventory_kbbl (库存)",
        "frequency": "weekly",
        "priority": "P2",
    },

    # 美国汽油库存 (EIA - 周频)
    "US_GASOLINE_INVENTORY": {
        "collector": "eia",
        "series_id": "PET.WGTSTUS1.W",
        "column_name": "US_Motor_Gasoline_Inventory_kbbl (天然气价格)",
        "frequency": "weekly",
        "priority": "P2",
    },

    # 炼厂开工率 (EIA - 周频)
    "REFINERY_UTILIZATION": {
        "collector": "eia",
        "series_id": "PET.WPULEUS3.W",
        "column_name": "Supply_Refinery_Refinery_Value (炼厂开工率)",
        "frequency": "weekly",
        "priority": "P2",
    },

    # 美国产量 (EIA - 周频)
    "US_PRODUCTION": {
        "collector": "eia",
        "series_id": "PET.WCRFPUS2.W",
        "column_name": "Supply_Production_US_US_Field_Value (产量)",
        "frequency": "weekly",
        "priority": "P2",
    },

    # 美国消费者信心 (FRED - 月频)
    "US_CONSUMER_SENTIMENT": {
        "collector": "fred",
        "series_id": "UMCSENT",
        "column_name": "Demand_PMI_美国制造业PMI_US_Consumer_Sentiment",
        "frequency": "monthly",
        "priority": "P2",
    },

    # ──────────────────────────────────────
    # P3: 替代采集因子（地缘/情绪）
    # ──────────────────────────────────────

    # 地缘政治综合评分 (GDELT)
    "GEOPOLITICS_SCORE": {
        "collector": "gdelt",
        "column_name": "Risk_Geopolitics_地缘政治事件综合评分",
        "frequency": "daily",
        "priority": "P3",
    },

    # 新闻情感指数 (GDELT)
    "NEWS_SENTIMENT": {
        "collector": "gdelt",
        "column_name": "Risk_Sentiment_新闻情感指数__News_Sentiment",
        "frequency": "daily",
        "priority": "P3",
    },

    # 俄乌冲突 (GDELT)
    "GEO_RUSSIA_UKRAINE": {
        "collector": "gdelt",
        "column_name": "Risk_Geopolitics_俄乌冲突",
        "frequency": "daily",
        "priority": "P3",
    },

    # 中东局势 (GDELT)
    "GEO_MIDDLE_EAST": {
        "collector": "gdelt",
        "column_name": "Risk_Geopolitics_中东局势_伊朗_沙特_也门",
        "frequency": "daily",
        "priority": "P3",
    },

    # 红海航运危机 (GDELT)
    "GEO_RED_SEA": {
        "collector": "gdelt",
        "column_name": "Risk_Geopolitics_红海航运危机_也门胡塞武装",
        "frequency": "daily",
        "priority": "P3",
    },

    # GPR 指数 (GDELT 近似)
    "GPR_INDEX": {
        "collector": "gdelt",
        "column_name": "Risk_Geopolitics_情绪组_GPR__Value",
        "frequency": "daily",
        "priority": "P3",
    },
}


def get_factors_by_collector(collector_type: str) -> dict[str, dict]:
    """按采集器类型筛选因子。"""
    return {
        k: v for k, v in FACTOR_REGISTRY.items()
        if v["collector"] == collector_type
    }


def get_factors_by_frequency(frequency: str) -> dict[str, dict]:
    """按频率筛选因子。"""
    return {
        k: v for k, v in FACTOR_REGISTRY.items()
        if v["frequency"] == frequency
    }


def get_factors_by_priority(priority: str) -> dict[str, dict]:
    """按优先级筛选因子。"""
    return {
        k: v for k, v in FACTOR_REGISTRY.items()
        if v["priority"] == priority
    }


# ── 数据校验范围 ──
VALIDATION_RANGES: dict[str, tuple[float, float]] = {
    "WTI_CLOSE": (10.0, 200.0),
    "WTI_OPEN": (10.0, 200.0),
    "WTI_HIGH": (10.0, 200.0),
    "WTI_LOW": (10.0, 200.0),
    "VIX_INDEX": (5.0, 90.0),
    "VIX_VALUE": (5.0, 90.0),
    "OVX_VALUE": (5.0, 150.0),
    "SP500_CLOSE": (1000.0, 10000.0),
    "USD_INDEX": (70.0, 130.0),
    "BRENT_CLOSE": (10.0, 200.0),
    "GOLD_VALUE": (500.0, 8000.0),
    "US_10Y_YIELD": (0.0, 15.0),
    "T10YIE": (-2.0, 10.0),
    "HY_SPREAD": (0.0, 25.0),
    "US_2Y_YIELD": (0.0, 15.0),
    "FED_FUNDS_RATE": (0.0, 20.0),
}
