"""
FRED API 数据采集器 — 采集美联储经济数据。
覆盖：美债收益率、通胀预期、高收益利差、联邦基金利率、汇率、消费者信心等。

修改：弃用 fredapi 库，改用 requests 直接调用 FRED API，
     以获得代理/SSL 的完全控制权。
"""

import logging
import os
from datetime import timedelta

import pandas as pd

from collector.base import FactorCollector
from collector.http_utils import get_shared_session
from collector.registry import VALIDATION_RANGES, get_factors_by_collector

logger = logging.getLogger("oilrisk.collector.fred")

FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"


class FredCollector(FactorCollector):
    """FRED API 数据源采集器（直接 HTTP 请求，支持代理）。"""

    def __init__(self):
        factors = get_factors_by_collector("fred")
        factor_keys = list(factors.keys())
        super().__init__(name="fred", source="fred", factor_keys=factor_keys)
        self._factors = factors
        self._api_key = os.environ.get("FRED_API_KEY", "")
        if not self._api_key:
            self.logger.warning("FRED_API_KEY 未设置，FRED 采集器将无法工作")

    def _fetch_series(self, series_id: str, start: str, end: str) -> float | None:
        """通过 FRED REST API 获取指定 series 在 [start, end] 内的最新值。"""
        session = get_shared_session()
        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
            "sort_order": "desc",
            "limit": 5,
        }

        try:
            resp = session.get(FRED_API_BASE, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            observations = data.get("observations", [])
            for obs in observations:
                val_str = obs.get("value", ".")
                if val_str != ".":
                    try:
                        return float(val_str)
                    except (ValueError, TypeError):
                        continue

            return None

        except Exception as e:
            self.logger.error("[fred] 采集失败: series=%s, error=%s", series_id, e)
            return None

    def collect(self, date_str: str) -> dict[str, float | None]:
        """
        采集指定日期的 FRED 因子数据。
        FRED 数据可能有 1-2 天延迟，会自动取最近可用值。
        """
        if not self._api_key:
            self.logger.error("[fred] FRED_API_KEY 未配置")
            return {k: None for k in self.factor_keys}

        target_date = pd.Timestamp(date_str)
        start = (target_date - timedelta(days=10)).strftime("%Y-%m-%d")
        end = target_date.strftime("%Y-%m-%d")

        result: dict[str, float | None] = {k: None for k in self.factor_keys}

        # 按 series_id 分组
        series_factors: dict[str, list[str]] = {}
        for fk, meta in self._factors.items():
            sid = meta["series_id"]
            if sid not in series_factors:
                series_factors[sid] = []
            series_factors[sid].append(fk)

        for series_id, fk_list in series_factors.items():
            value = self._fetch_series(series_id, start, end)

            if value is None:
                self.logger.warning("[fred] 无数据: series=%s, date=%s", series_id, date_str)
                continue

            for fk in fk_list:
                if fk in VALIDATION_RANGES:
                    lo, hi = VALIDATION_RANGES[fk]
                    if not (lo <= value <= hi):
                        self.logger.warning(
                            "[fred] 超范围告警: %s=%.4f (范围 [%.1f, %.1f])",
                            fk, value, lo, hi,
                        )
                result[fk] = value

        return result
