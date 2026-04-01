# 因子来源和去向文档任务记录

## 本次任务

将原 `地缘政治.md` 扩展为全量因子说明文档，并改名为 `因子来源和去向.md`。

## 关键操作

1. 核对当前在线采集源
   - `yfinance`
   - `FRED`
   - `EIA`
   - `GDELT`
2. 核对实时因子注册表
   - 以 `python_engine/collector/registry.py` 为准
3. 核对在线推理去向
   - `factor_realtime` -> `engine.reload_from_db()` -> `df_raw`
   - `MARKET_STATE_COLS` 进入 Stacking
   - LSTM 对部分原始列做特征工程
   - XGBoost 从 `df_raw` 按模型特征名取值
4. 补充历史训练层说明
   - 明确 `Final_Oil_Dataset_Cleaned.csv` 中存在比当前实时采集更完整的历史因子
   - 明确 OPEC、沙特、俄罗斯、PMI 等慢变量目前主要依赖历史数据
5. 清理旧文件
   - 删除旧 `地缘政治.md`
   - 删除旧 `memory/geo-politics-doc.md`

## 注意事项

- 不能把“当前 registry 可采集因子”与“训练期历史字段全集”混写成一回事。
- 不能把“可能被 XGBoost 使用”写成“确定被 XGBoost 使用”，除非直接核对模型特征名。
- `collect_gdelt()` 默认不触发预测，这个限制需要在文档里保留。
- 后续已追加一个重要补充：`因子来源和去向.md` 不仅要写在线采集因子，还要覆盖 `Final_Oil_Dataset_Cleaned.csv` 中的历史全量地缘政治字段和主要历史训练字段。
- 历史 CSV 独有字段的来源很多只能按列名和模型文档做“推断来源”，不能伪装成代码里已保留完整采集链路。
