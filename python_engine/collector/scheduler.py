"""
APScheduler 任务编排 — 定时采集因子数据并触发推理。

调度策略:
- 日频: 周一至周五 06:00 (Asia/Shanghai) — yfinance + FRED
- 周频: 每周四 06:00 — EIA 数据
- 月频: 每月 2 日 06:00 — 月频因子
- GDELT: 每日 12:00 — 地缘/情绪数据

新增:
- backfill_range(): 回填指定日期范围的历史数据
- detect_and_backfill(): 自动检测缺口并回填
"""

import logging
import time
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import db
from collector.registry import FACTOR_REGISTRY, get_factors_by_collector
from collector.yfinance_collector import YFinanceCollector
from collector.fred_collector import FredCollector
from collector.eia_collector import EiaCollector
from collector.gdelt_collector import GdeltCollector

logger = logging.getLogger("oilrisk.scheduler")

# 全局调度器实例
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 全局采集器实例（延迟初始化）
_yf_collector: YFinanceCollector | None = None
_fred_collector: FredCollector | None = None
_eia_collector: EiaCollector | None = None
_gdelt_collector: GdeltCollector | None = None

# 引擎引用（由 app.py 注入）
_engine_ref = None


def set_engine_ref(engine):
    """由 app.py 调用，注入 OilRiskEngine 引用。"""
    global _engine_ref
    _engine_ref = engine


def _get_collectors():
    """延迟初始化采集器。"""
    global _yf_collector, _fred_collector, _eia_collector, _gdelt_collector
    if _yf_collector is None:
        _yf_collector = YFinanceCollector()
    if _fred_collector is None:
        _fred_collector = FredCollector()
    if _eia_collector is None:
        _eia_collector = EiaCollector()
    if _gdelt_collector is None:
        _gdelt_collector = GdeltCollector()
    return _yf_collector, _fred_collector, _eia_collector, _gdelt_collector


def _get_previous_trading_day() -> str:
    """获取前一个交易日日期字符串。简化逻辑：跳过周末。"""
    today = date.today()
    # 尝试使用 pandas_market_calendars，失败则用简单逻辑
    try:
        import pandas_market_calendars as mcal
        import pandas as pd
        nyse = mcal.get_calendar("NYSE")
        end = pd.Timestamp(today)
        start = end - pd.Timedelta(days=10)
        schedule = nyse.schedule(start_date=start, end_date=end)
        if not schedule.empty:
            last_trading = schedule.index[-1]
            # 如果今天是交易日且还没到收盘，用前一天
            if last_trading.date() == today:
                if len(schedule) > 1:
                    return str(schedule.index[-2].date())
            return str(last_trading.date())
    except Exception:
        pass

    # 回退：简单跳过周末
    d = today - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return str(d)


def _get_trading_days(start_date: date, end_date: date) -> list[str]:
    """获取指定范围内的交易日列表。"""
    try:
        import pandas_market_calendars as mcal
        import pandas as pd
        nyse = mcal.get_calendar("NYSE")
        schedule = nyse.schedule(
            start_date=pd.Timestamp(start_date),
            end_date=pd.Timestamp(end_date),
        )
        return [str(d.date()) for d in schedule.index]
    except Exception:
        pass

    # 回退：排除周末
    days = []
    d = start_date
    while d <= end_date:
        if d.weekday() < 5:
            days.append(str(d))
        d += timedelta(days=1)
    return days


def _write_factors_to_db(
    collector_name: str,
    factor_data: dict[str, float | None],
    target_date: str,
) -> tuple[int, int, dict]:
    """将采集结果写入 DB。返回 (成功数, 失败数, 失败详情)。"""
    records = []
    failed = {}
    ok_count = 0
    fail_count = 0

    for fk, value in factor_data.items():
        if fk not in FACTOR_REGISTRY:
            continue
        meta = FACTOR_REGISTRY[fk]
        if value is not None:
            records.append({
                "date": datetime.strptime(target_date, "%Y-%m-%d").date(),
                "factor_key": fk,
                "column_name": meta["column_name"],
                "value": value,
                "source": meta["collector"],
                "frequency": meta["frequency"],
            })
            ok_count += 1
        else:
            fail_count += 1
            failed[fk] = "采集返回 None"

    if records:
        written = db.batch_upsert_factors(records)
        if written == 0:
            # 批量写入失败，全部算失败
            fail_count += ok_count
            ok_count = 0

    return ok_count, fail_count, failed


def _run_collection(
    collectors: list,
    target_date: str,
    trigger_inference: bool = True,
) -> dict:
    """
    执行采集流程。
    返回采集结果摘要。
    """
    start_time = time.time()

    total_ok = 0
    total_fail = 0
    all_failed = {}
    source_names = []

    for collector in collectors:
        source_names.append(collector.name)
        try:
            data = collector.collect_with_retry(target_date)
            ok, fail, failed = _write_factors_to_db(collector.name, data, target_date)
            total_ok += ok
            total_fail += fail
            all_failed.update(failed)
        except Exception as e:
            logger.error("采集器 %s 执行异常: %s", collector.name, e)
            total_fail += len(collector.factor_keys)
            for fk in collector.factor_keys:
                all_failed[fk] = str(e)

    duration_ms = int((time.time() - start_time) * 1000)
    total = total_ok + total_fail

    # 确定状态
    if total_fail == 0:
        status = "SUCCESS"
    elif total_ok > 0:
        status = "PARTIAL"
    else:
        status = "FAILED"

    # 写采集日志
    source_str = "+".join(source_names)
    db.insert_collection_log(
        run_date=datetime.strptime(target_date, "%Y-%m-%d").date(),
        source=source_str,
        status=status,
        factors_total=total,
        factors_ok=total_ok,
        factors_failed=total_fail,
        error_detail=all_failed if all_failed else None,
        duration_ms=duration_ms,
    )

    # 更新系统状态
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    db.set_system_state("last_collection_time", now_str)
    db.set_system_state("last_collection_status", status)
    db.set_system_state("data_date", target_date)

    # 触发推理
    prediction_result = None
    if trigger_inference and total_ok > 0 and _engine_ref is not None:
        try:
            prediction_result = _engine_ref.reload_from_db()
            db.set_system_state("last_prediction_time", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
            logger.info("推理完成: %s", prediction_result.get("dashboard", {}) if prediction_result else "None")

            # 持久化推理结果到 risk_index + risk_factor 表
            if prediction_result:
                try:
                    db.persist_prediction(prediction_result)
                except Exception as e:
                    logger.error("推理结果持久化失败: %s", e)

        except Exception as e:
            logger.error("推理触发失败: %s", e)
    elif total_ok == 0:
        logger.warning("全部采集失败，不触发推理")

    result = {
        "status": status,
        "collection": {
            "date": target_date,
            "total": total,
            "success": total_ok,
            "failed": total_fail,
            "failed_factors": list(all_failed.keys()),
            "duration_ms": duration_ms,
        },
    }

    if prediction_result and "dashboard" in prediction_result:
        result["prediction"] = prediction_result["dashboard"]

    return result


def collect_daily():
    """日频采集任务：yfinance + FRED。"""
    logger.info("=== 日频采集任务开始 ===")
    yf, fred, _, _ = _get_collectors()
    target_date = _get_previous_trading_day()
    return _run_collection([yf, fred], target_date)


def collect_weekly():
    """周频采集任务：EIA 数据。"""
    logger.info("=== 周频采集任务开始 ===")
    _, _, eia, _ = _get_collectors()
    target_date = _get_previous_trading_day()
    return _run_collection([eia], target_date)


def collect_monthly():
    """月频采集任务：FRED 月频因子。"""
    logger.info("=== 月频采集任务开始 ===")
    _, fred, _, _ = _get_collectors()
    target_date = _get_previous_trading_day()
    return _run_collection([fred], target_date)


def collect_gdelt():
    """GDELT 地缘/情绪采集任务。"""
    logger.info("=== GDELT 采集任务开始 ===")
    _, _, _, gdelt = _get_collectors()
    target_date = _get_previous_trading_day()
    return _run_collection([gdelt], target_date, trigger_inference=False)


def collect_all() -> dict:
    """全量采集（手动触发时调用）：所有采集器。"""
    logger.info("=== 全量采集任务开始 ===")
    yf, fred, eia, gdelt = _get_collectors()
    target_date = _get_previous_trading_day()
    return _run_collection([yf, fred, eia, gdelt], target_date)


# ═══════════════════════════════════════
# 数据缺口检测与回填
# ═══════════════════════════════════════


def detect_data_gaps(lookback_days: int = 90) -> list[str]:
    """
    检测最近 lookback_days 内缺失数据的交易日。
    返回缺失日期列表（升序）。
    """
    today = date.today()
    start = today - timedelta(days=lookback_days)
    end = today - timedelta(days=1)

    trading_days = _get_trading_days(start, end)
    if not trading_days:
        return []

    existing_dates = set()
    try:
        existing_dates = db.get_factor_dates(start, end)
    except Exception as e:
        logger.error("查询已有数据日期失败: %s", e)
        return trading_days

    missing = [d for d in trading_days if d not in existing_dates]
    if missing:
        logger.info(
            "检测到 %d 个交易日数据缺口 (范围: %s ~ %s)",
            len(missing), missing[0], missing[-1],
        )
    return missing


def backfill_range(
    start_date: str,
    end_date: str,
    delay_between_days: float = 3.0,
) -> dict:
    """
    回填指定日期范围的历史数据。
    对每个交易日依次执行全量采集（带延时避免限流）。
    """
    logger.info("=== 回填任务开始: %s ~ %s ===", start_date, end_date)

    sd = datetime.strptime(start_date, "%Y-%m-%d").date()
    ed = datetime.strptime(end_date, "%Y-%m-%d").date()
    trading_days = _get_trading_days(sd, ed)

    if not trading_days:
        return {"total_days": 0, "success_days": 0, "failed_days": 0, "details": []}

    yf, fred, eia, gdelt = _get_collectors()
    all_collectors = [yf, fred, eia, gdelt]

    total = len(trading_days)
    success = 0
    failed = 0
    details = []

    for i, day_str in enumerate(trading_days):
        logger.info("[回填 %d/%d] 采集日期: %s", i + 1, total, day_str)
        try:
            # 采集 + 推理 + 持久化（每天都写入 risk_index/risk_factor）
            result = _run_collection(all_collectors, day_str, trigger_inference=True)
            ok_count = result.get("collection", {}).get("success", 0)
            if ok_count > 0:
                success += 1
            else:
                failed += 1
            details.append({
                "date": day_str,
                "status": result.get("status", "UNKNOWN"),
                "success": ok_count,
                "failed": result.get("collection", {}).get("failed", 0),
            })
        except Exception as e:
            logger.error("[回填] %s 采集异常: %s", day_str, e)
            failed += 1
            details.append({"date": day_str, "status": "ERROR", "error": str(e)})

        if i < total - 1:
            time.sleep(delay_between_days)

    # 回填完成
    if success > 0 and _engine_ref is not None:
        logger.info("回填完成，最新数据已持久化到 risk_index/risk_factor")

    logger.info(
        "=== 回填完成: %d/%d 天成功, %d 天失败 ===",
        success, total, failed,
    )
    return {
        "total_days": total,
        "success_days": success,
        "failed_days": failed,
        "details": details,
    }


def detect_and_backfill(lookback_days: int = 90) -> dict:
    """自动检测缺口并回填。"""
    missing = detect_data_gaps(lookback_days)
    if not missing:
        logger.info("无数据缺口，跳过回填")
        return {"total_days": 0, "success_days": 0, "failed_days": 0, "message": "no gaps"}
    return backfill_range(missing[0], missing[-1])


def setup_scheduler():
    """配置定时任务。"""
    # 日频：周一至周五 06:00
    scheduler.add_job(
        collect_daily,
        CronTrigger(day_of_week="mon-fri", hour=6, minute=0),
        id="daily_collect",
        replace_existing=True,
    )

    # 周频：每周四 06:00
    scheduler.add_job(
        collect_weekly,
        CronTrigger(day_of_week="thu", hour=6, minute=0),
        id="weekly_collect",
        replace_existing=True,
    )

    # 月频：每月 2 日 06:00
    scheduler.add_job(
        collect_monthly,
        CronTrigger(day=2, hour=6, minute=0),
        id="monthly_collect",
        replace_existing=True,
    )

    # GDELT：每日 12:00
    scheduler.add_job(
        collect_gdelt,
        CronTrigger(day_of_week="mon-fri", hour=12, minute=0),
        id="gdelt_collect",
        replace_existing=True,
    )

    logger.info("定时任务已配置完成")


def start_scheduler():
    """启动调度器。"""
    setup_scheduler()
    scheduler.start()
    logger.info("APScheduler 已启动")


def stop_scheduler():
    """停止调度器。"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler 已停止")
