"""
yfinance 数据采集器 — 采集 Yahoo Finance 日频金融数据。
覆盖 P0/P1 级别因子：WTI、Brent、VIX、OVX、SP500、美元指数、CRB、黄金等。

优化策略:
- 批量下载（yf.download）减少请求次数
- 分组请求 + 间隔延时避免 Rate Limit
- 单 ticker 回退保证部分成功
"""

import logging
import os
import time
from datetime import timedelta

import pandas as pd

from collector.base import FactorCollector
from collector.registry import VALIDATION_RANGES, get_factors_by_collector

logger = logging.getLogger("oilrisk.collector.yfinance")

# 每批最多下载的 ticker 数量
BATCH_SIZE = int(os.environ.get("YF_BATCH_SIZE", "5"))
# 批次间等待秒数
BATCH_DELAY = float(os.environ.get("YF_BATCH_DELAY", "2.0"))
# 单 ticker 回退时的间隔秒数
SINGLE_DELAY = float(os.environ.get("YF_SINGLE_DELAY", "1.5"))


class YFinanceCollector(FactorCollector):
    """yfinance 数据源采集器（批量下载 + 限流）。"""

    def __init__(self):
        factors = get_factors_by_collector("yfinance")
        factor_keys = list(factors.keys())
        super().__init__(name="yfinance", source="yfinance", factor_keys=factor_keys)
        self._factors = factors

    def _build_ticker_map(self) -> dict[str, list[tuple[str, str]]]:
        """按 ticker 分组 factor_key 和 field。"""
        ticker_factors: dict[str, list[tuple[str, str]]] = {}
        for fk, meta in self._factors.items():
            ticker = meta["ticker"]
            field = meta["field"]
            if ticker not in ticker_factors:
                ticker_factors[ticker] = []
            ticker_factors[ticker].append((fk, field))
        return ticker_factors

    def _extract_values(
        self,
        hist: pd.DataFrame,
        target_date: pd.Timestamp,
        fk_fields: list[tuple[str, str]],
        result: dict[str, float | None],
        ticker: str,
    ) -> int:
        """从历史数据中提取目标日期的值，返回成功提取数。"""
        if hist.empty:
            return 0

        # 统一去除时区
        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        valid = hist[hist.index <= target_date]
        if valid.empty:
            valid = hist

        row = valid.iloc[-1]
        extracted = 0

        for fk, field in fk_fields:
            if field in row.index and pd.notna(row[field]):
                value = float(row[field])
                if fk in VALIDATION_RANGES:
                    lo, hi = VALIDATION_RANGES[fk]
                    if not (lo <= value <= hi):
                        self.logger.warning(
                            "[yfinance] 超范围告警: %s=%.4f (范围 [%.1f, %.1f])",
                            fk, value, lo, hi,
                        )
                result[fk] = value
                extracted += 1
            else:
                self.logger.debug(
                    "[yfinance] 字段缺失: ticker=%s, field=%s", ticker, field,
                )
        return extracted

    def _batch_download(
        self,
        tickers: list[str],
        start: str,
        end: str,
        target_date: pd.Timestamp,
        ticker_factors: dict[str, list[tuple[str, str]]],
        result: dict[str, float | None],
    ) -> list[str]:
        """
        批量下载多个 ticker，返回失败的 ticker 列表。
        """
        import yfinance as yf

        failed_tickers = []

        try:
            data = yf.download(
                tickers=tickers,
                start=start,
                end=end,
                auto_adjust=True,
                threads=False,  # 单线程避免并发限流
                progress=False,
            )

            if data.empty:
                self.logger.warning("[yfinance] 批量下载无数据: %s", tickers)
                return tickers

            for ticker in tickers:
                fk_fields = ticker_factors.get(ticker, [])
                if not fk_fields:
                    continue
                try:
                    if len(tickers) == 1:
                        hist = data
                    else:
                        # 多 ticker 时 columns 是 MultiIndex
                        hist = data.xs(ticker, axis=1, level=1) if isinstance(
                            data.columns, pd.MultiIndex
                        ) else data
                    count = self._extract_values(hist, target_date, fk_fields, result, ticker)
                    if count == 0:
                        failed_tickers.append(ticker)
                except Exception as e:
                    self.logger.debug("[yfinance] 批量提取失败: ticker=%s, %s", ticker, e)
                    failed_tickers.append(ticker)

        except Exception as e:
            self.logger.warning("[yfinance] 批量下载失败: %s, 将逐个重试", e)
            failed_tickers = tickers

        return failed_tickers

    def _single_download(
        self,
        ticker: str,
        start: str,
        end: str,
        target_date: pd.Timestamp,
        fk_fields: list[tuple[str, str]],
        result: dict[str, float | None],
    ) -> bool:
        """单 ticker 下载回退，返回是否成功。"""
        import yfinance as yf

        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(start=start, end=end, auto_adjust=True)
            count = self._extract_values(hist, target_date, fk_fields, result, ticker)
            return count > 0
        except Exception as e:
            self.logger.error("[yfinance] 采集失败: ticker=%s, error=%s", ticker, e)
            return False

    def collect(self, date_str: str) -> dict[str, float | None]:
        """
        采集指定日期的 yfinance 因子数据。
        策略：先批量下载 → 失败的逐个重试（带延时）。
        """
        target_date = pd.Timestamp(date_str)
        start = (target_date - timedelta(days=5)).strftime("%Y-%m-%d")
        end = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")

        ticker_factors = self._build_ticker_map()
        all_tickers = list(ticker_factors.keys())
        result: dict[str, float | None] = {k: None for k in self.factor_keys}

        # 分批批量下载
        all_failed: list[str] = []
        for i in range(0, len(all_tickers), BATCH_SIZE):
            batch = all_tickers[i: i + BATCH_SIZE]
            self.logger.info("[yfinance] 批量下载: %s", batch)
            failed = self._batch_download(
                batch, start, end, target_date, ticker_factors, result,
            )
            all_failed.extend(failed)
            if i + BATCH_SIZE < len(all_tickers):
                time.sleep(BATCH_DELAY)

        # 对批量失败的 ticker 逐个重试
        if all_failed:
            self.logger.info("[yfinance] 逐个重试失败的 ticker: %s", all_failed)
            time.sleep(BATCH_DELAY)  # 先等一波
            for ticker in all_failed:
                fk_fields = ticker_factors.get(ticker, [])
                ok = self._single_download(
                    ticker, start, end, target_date, fk_fields, result,
                )
                if not ok:
                    self.logger.warning("[yfinance] 最终失败: ticker=%s", ticker)
                time.sleep(SINGLE_DELAY)

        return result
