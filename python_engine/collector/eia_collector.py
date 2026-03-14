"""
EIA API 数据采集器 — 采集美国能源信息署数据。
覆盖 P2 周频因子：库欣库存、商业原油库存、汽油库存、炼厂开工率、美国产量。

修改：使用共享 HTTP session（支持代理 + SSL 重试）。
"""

import logging
import os

from collector.base import FactorCollector
from collector.http_utils import get_shared_session
from collector.registry import get_factors_by_collector

logger = logging.getLogger("oilrisk.collector.eia")


class EiaCollector(FactorCollector):
    """EIA API v2 数据源采集器。"""

    def __init__(self):
        factors = get_factors_by_collector("eia")
        factor_keys = list(factors.keys())
        super().__init__(name="eia", source="eia", factor_keys=factor_keys)
        self._factors = factors

        self._api_key = os.environ.get("EIA_API_KEY", "")
        if not self._api_key:
            self.logger.warning("EIA_API_KEY 未设置，EIA 采集器将无法工作")

    def _fetch_series(self, series_id: str, date_str: str) -> float | None:
        """调用 EIA API v2 获取单个 series 的最新值。"""
        if not self._api_key:
            return None

        parts = series_id.split(".")
        if len(parts) != 3:
            self.logger.error("[eia] 无效 series_id 格式: %s", series_id)
            return None

        session = get_shared_session()

        # EIA API v2
        try:
            url = "https://api.eia.gov/v2/seriesid/" + series_id
            params = {
                "api_key": self._api_key,
                "num": 5,
            }
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "response" in data and "data" in data["response"]:
                records = data["response"]["data"]
                if records:
                    for rec in records:
                        val = rec.get("value")
                        if val is not None:
                            return float(val)

            # 备用：v1 API
            return self._fetch_series_v1(series_id)

        except Exception as e:
            self.logger.error("[eia] API v2 请求失败: series=%s, error=%s", series_id, e)
            return self._fetch_series_v1(series_id)

    def _fetch_series_v1(self, series_id: str) -> float | None:
        """备用：EIA 旧版 API。"""
        session = get_shared_session()
        try:
            url = "https://api.eia.gov/series/"
            params = {
                "api_key": self._api_key,
                "series_id": series_id,
                "num": 5,
            }
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "series" in data and data["series"]:
                series_data = data["series"][0].get("data", [])
                if series_data:
                    return float(series_data[0][1])
        except Exception as e:
            self.logger.error("[eia] v1 API 也失败: series=%s, error=%s", series_id, e)
        return None

    def collect(self, date_str: str) -> dict[str, float | None]:
        """采集指定日期的 EIA 因子数据。"""
        if not self._api_key:
            self.logger.error("[eia] EIA_API_KEY 未配置")
            return {k: None for k in self.factor_keys}

        result: dict[str, float | None] = {k: None for k in self.factor_keys}

        for fk, meta in self._factors.items():
            series_id = meta["series_id"]
            try:
                value = self._fetch_series(series_id, date_str)
                if value is not None:
                    result[fk] = value
                    self.logger.debug("[eia] %s = %.2f", fk, value)
                else:
                    self.logger.warning("[eia] 无数据: %s (series=%s)", fk, series_id)
            except Exception as e:
                self.logger.error("[eia] 采集异常: %s, error=%s", fk, e)

        return result
