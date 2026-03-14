"""
数据采集器基类 — 提供重试、超时、日志标准化。
"""

import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger("oilrisk.collector")


class FactorCollector(ABC):
    """
    采集器基类。每个子类实现 collect() 方法采集指定日期数据。

    属性:
        name: 采集器名称（用于日志标识）
        source: 数据来源标识（yfinance/fred/eia/gdelt）
        factor_keys: 该采集器负责的因子 key 列表
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 5  # 秒（指数退避基数）

    def __init__(self, name: str, source: str, factor_keys: list[str]):
        self.name = name
        self.source = source
        self.factor_keys = factor_keys
        self.logger = logging.getLogger(f"oilrisk.collector.{name}")

    @abstractmethod
    def collect(self, date_str: str) -> dict[str, float | None]:
        """
        采集指定日期的因子数据。

        Args:
            date_str: 日期字符串，格式 "YYYY-MM-DD"

        Returns:
            {factor_key: value} 字典，失败的 key 值为 None。
        """
        ...

    def collect_with_retry(self, date_str: str) -> dict[str, float | None]:
        """带重试的采集入口。3 次重试，指数退避。"""
        for attempt in range(self.MAX_RETRIES):
            try:
                result = self.collect(date_str)
                if result:
                    ok_count = sum(1 for v in result.values() if v is not None)
                    self.logger.info(
                        "[%s] 采集完成: %d/%d 因子成功 (date=%s)",
                        self.name, ok_count, len(result), date_str,
                    )
                return result
            except Exception as e:
                wait = self.RETRY_DELAY * (2 ** attempt)
                if attempt < self.MAX_RETRIES - 1:
                    self.logger.warning(
                        "[%s] 第 %d 次采集失败，%ds 后重试: %s",
                        self.name, attempt + 1, wait, e,
                    )
                    time.sleep(wait)
                else:
                    self.logger.error(
                        "[%s] 采集彻底失败（已重试 %d 次）: %s",
                        self.name, self.MAX_RETRIES, e,
                    )
                    return {k: None for k in self.factor_keys}

        # 理论上不会到这里，但做防御性返回
        return {k: None for k in self.factor_keys}
