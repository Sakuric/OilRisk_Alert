"""
================================================================
油价预测 Stacking 集成模型 — 全日频版本
================================================================

数据频率统一：日频（与 LSTM、XGBoost 训练完全一致）

架构：
  第1层（已训练好，只做推断）：
    LSTM    → pred_price(5天后) → impl_return = (pred-current)/current
              正负都有，负责"方向+幅度"
    XGBoost → xgb_risk = max(0, -next_return_5d)
              专注下跌风险强度，负责"极端下跌预警"

  第2层 Ridge 元学习器（本脚本训练）：
    输入：市场状态特征(7) + lstm_impl_return(1) + xgb_risk(1) = 9维
    目标：next_return_5d × 100（%，5个交易日后涨跌幅）
    输出：pred_return → 高/中/低风险区间

  数据划分：70/15/15 按日频样本数（与 LSTM 训练一致）

输入文件（均在 D:/花旗杯比赛/ 根目录）：
  Final_Oil_Dataset_Cleaned.csv
  xgb_risk_model.pkl       → {"model":..., "feature_cols":[...]}
  best_lstm.pt / best_lstm.keras
  price_scaler.pkl
  feat_scaler.pkl
  feature_cols.pkl

输出文件：
  meta_ridge_model.pkl
  stacking_test_predictions.csv
  stacking_plots/*.png
================================================================
"""

import numpy as np
import pandas as pd
import joblib
import os
import warnings
import matplotlib
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

warnings.filterwarnings("ignore")
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ─────────────────────────────────────────────
# 路径配置（全部在根目录）
# ─────────────────────────────────────────────
BASE_DIR = r"."

DATA_PATH         = os.path.join(BASE_DIR, "Final_Oil_Dataset_Cleaned.csv")
XGB_PATH          = os.path.join(BASE_DIR, "xgb_wti_shock_model.pkl")
LSTM_MODEL_KERAS  = os.path.join(BASE_DIR, "best_lstm.keras")
LSTM_MODEL_PT     = os.path.join(BASE_DIR, "best_lstm.pt")
PRICE_SCALER_PATH = os.path.join(BASE_DIR, "price_scaler.pkl")
FEAT_SCALER_PATH  = os.path.join(BASE_DIR, "feat_scaler.pkl")
FEAT_COLS_PATH    = os.path.join(BASE_DIR, "feature_cols.pkl")
META_PATH         = os.path.join(BASE_DIR, "meta_ridge_model.pkl")
RESULT_PATH       = os.path.join(BASE_DIR, "stacking_test_predictions.csv")
PLOT_DIR          = os.path.join(BASE_DIR, "stacking_plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# 超参数（与 LSTM 训练保持一致）
# ─────────────────────────────────────────────
LOOKBACK      = 30      # LSTM lookback（日频）
HORIZON       = 5       # 预测未来5个交易日
TRAIN_RATIO   = 0.70
VAL_RATIO     = 0.15
TARGET_COL    = "Price_WTI_WTI期货_close"
SHOCK_THRESH  = -0.02   # 5日跌幅 < -2% 算冲击事件

MARKET_STATE_COLS = [
    "Risk_VIX_VIX恐慌指数_VIX_Index",
    "Risk_VIX_情绪组_OVX__Value",
    "Macro_Yield_美债10年收益率_US_10Y_Treasury_Yield",
    "美元指数_日频",
    "Risk_Sentiment_新闻情感指数__News_Sentiment",
    "Risk_Geopolitics_地缘政治事件综合评分",
    "Macro_SP500_标普500指数_SP500_Close",
]


# ================================================================
# Step 1  数据加载
#   df_raw  → 原始全列 CSV，给 XGBoost + 市场状态特征 + 标签
#   df_feat → 复现 LSTM load_and_engineer 的27列特征，给 LSTM 推断
#   两者索引取交集，保证每一天都有对应的 XGBoost 特征和 LSTM 特征
# ================================================================

# LSTM 列名映射（与原始代码完全一致）
LSTM_COLS = {
    'target':       'Price_WTI_WTI期货_close',
    'crb':          'CRB现货指数_日频',
    'sp500':        'Macro_SP500_标普500指数_SP500_Close',
    'tips':         'Macro_CPI_10年期通胀预期_T10YIE',
    'hy':           '情绪组_HY_S_Value',
    'vix':          'Risk_VIX_情绪组_VIX__Value',
    'ovx':          'Risk_VIX_情绪组_OVX__Value',
    'cushing':      'Supply_Inventory_US_Cushing__Value (库存)',
    'opec':         'Supply_Production_OPEC_OPEC每月原油_OPEC石油输出国组织',
    'saudi':        'Supply_Production_OPEC_OPEC每月原油_沙特阿拉伯',
    'russia':       'Supply_Production_OPEC_非OPEC国家原_俄罗斯联邦',
    'cn_pmi':       'Demand_PMI_中国制造业PMI_China_Manufacturing_PMI',
    'eu_pmi':       'Demand_PMI_欧元区制造业PM_Eurozone_Manufacturing_PMI',
    'us_sentiment': 'Demand_PMI_美国制造业PMI_US_Consumer_Sentiment',
    'eu_ici':       'Demand_PMI_欧元区制造业PM_Eurozone_Manufacturing_PMI',
}


def build_lstm_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    完全复现 LSTM 的 load_and_engineer()，与训练代码保持一致。
    """
    target = LSTM_COLS['target']
    price  = df[target]
    feat   = pd.DataFrame(index=df.index)

    # A. 价格自身
    feat['price'] = price

    # B. 日频金融特征
    for k in ['crb', 'sp500', 'tips', 'hy', 'vix', 'ovx', 'cushing']:
        col = LSTM_COLS[k]
        if col in df.columns:
            feat[k] = df[col]

    # C. 月频慢变量 → 月度变化量
    for k in ['opec', 'saudi', 'russia', 'cn_pmi', 'eu_pmi', 'us_sentiment']:
        col = LSTM_COLS[k]
        if col in df.columns:
            monthly_chg = df[col].resample('ME').last().diff()
            feat[f'{k}_chg'] = monthly_chg.reindex(df.index, method='ffill')

    # eu_ici：用 eu_pmi 同列构造（月度变化量）
    eu_ici_col = LSTM_COLS['eu_ici']
    if eu_ici_col in df.columns:
        feat['eu_ici'] = df[eu_ici_col]
        monthly_chg = df[eu_ici_col].resample('ME').last().diff()
        feat['eu_ici_chg'] = monthly_chg.reindex(df.index, method='ffill')

    # D. 技术指标
    feat['ma5']      = price.rolling(5).mean()
    feat['ma20']     = price.rolling(20).mean()
    feat['ma60']     = price.rolling(60).mean()
    feat['dev_ma5']  = (price - feat['ma5'])  / (feat['ma5']  + 1e-8)
    feat['dev_ma20'] = (price - feat['ma20']) / (feat['ma20'] + 1e-8)
    feat['dev_ma60'] = (price - feat['ma60']) / (feat['ma60'] + 1e-8)
    feat['mom5']     = np.log(price / price.shift(5).replace(0, np.nan))
    feat['mom20']    = np.log(price / price.shift(20).replace(0, np.nan))
    feat['hvol20']   = np.log(price / price.shift(1)).rolling(20).std()
    if 'cushing' in feat.columns:
        feat['cushing_chg5'] = feat['cushing'].diff(5)

    # E. 方向性特征
    feat['mom_accel'] = feat['mom5'] - feat['mom5'].shift(3)
    if 'vix' in feat.columns:
        feat['vix_chg3'] = feat['vix'].pct_change(3)
    if 'ovx' in feat.columns:
        feat['ovx_chg3'] = feat['ovx'].pct_change(3)

    # F. 标签
    feat['y_price'] = price.shift(-HORIZON)
    feat['y_label'] = (feat['y_price'] > price).astype(int)

    feat = feat.dropna()
    return feat


def load_data():
    print("=" * 65)
    print("Step 1  加载数据")
    print("  df_raw  → 原始列不填充（XGBoost用，与训练一致）")
    print("  df_feat → LSTM特征工程27列（LSTM推断用）")
    print("=" * 65)

    # 读原始数据（不填充，XGBoost 训练时也没有填充）
    df_orig = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    date_col = next((c for c in df_orig.columns if "date" in c.lower()), None)
    if date_col is None:
        raise ValueError("未找到日期列")
    df_orig[date_col] = pd.to_datetime(df_orig[date_col])
    df_orig = df_orig.sort_values(date_col).set_index(date_col)

    global TARGET_COL
    if TARGET_COL not in df_orig.columns:
        cands = [c for c in df_orig.columns
                 if any(k in c.lower() for k in ["wti","brent","oil","price"])]
        if not cands:
            raise ValueError("找不到目标列")
        TARGET_COL = cands[0]

    # ffill 全量数据（供市场状态列和价格标签使用）
    df_ffill = df_orig.ffill().bfill()

    # 只保留 WTI 有真实数据的行（用原始未填充数据判断）
    wti_valid_index = df_orig[df_orig[TARGET_COL].notna()].index
    df_ffill_valid  = df_ffill.loc[wti_valid_index].copy()

    # LSTM 用过滤后的 ffill 数据做特征工程（只从WTI有数据开始）
    df_feat = build_lstm_features(df_ffill_valid)
    print(f"  df_feat 样本：{len(df_feat)}  特征列：{df_feat.shape[1]-2}  "
          f"({df_feat.index.min().date()} ~ {df_feat.index.max().date()})")

    # XGBoost 用原始未填充的数据（与训练时一致）
    df_raw = df_orig.loc[df_feat.index].copy()

    # 附加 next_return / risk 标签（用 ffill 后的价格算，避免NaN导致的异常）
    price_arr   = df_ffill.loc[df_feat.index, TARGET_COL].values.astype(float)
    next_return = np.full(len(price_arr), np.nan)
    next_return[:-HORIZON] = (
        price_arr[HORIZON:] - price_arr[:-HORIZON]
    ) / (price_arr[:-HORIZON] + 1e-8)
    df_raw["next_return"] = next_return
    df_raw["risk"]        = np.maximum(0, -next_return)
    df_raw = df_raw.dropna(subset=["next_return"]).copy()

    # df_feat 同步对齐
    df_feat = df_feat.loc[df_raw.index].copy()
    df_feat["next_return"] = df_raw["next_return"]
    df_feat["risk"]        = df_raw["risk"]

    # 市场状态列单独保存ffill版本供Ridge使用
    df_market = df_ffill.loc[df_raw.index, MARKET_STATE_COLS].copy()
    for col in MARKET_STATE_COLS:
        if col not in df_market.columns:
            df_market[col] = 0.0

    print(f"  df_raw  样本：{len(df_raw)}  列数：{df_raw.shape[1]}")
    print(f"  next_return 均值={df_raw['next_return'].mean()*100:.3f}%  "
          f"std={df_raw['next_return'].std()*100:.3f}%")
    print(f"  上涨日占比：{(df_raw['next_return']>0).mean():.1%}  "
          f"大跌(<{SHOCK_THRESH*100:.0f}%)占比："
          f"{(df_raw['next_return']<SHOCK_THRESH).mean():.1%}")

    return df_raw, df_feat, df_market


# ================================================================
# Step 2  数据集划分（以 df_raw 的索引为准，df_feat 同步切分）
# ================================================================
def split_data(df_raw, df_feat, df_market):
    N      = len(df_raw)
    tr_end = int(N * TRAIN_RATIO)
    va_end = int(N * (TRAIN_RATIO + VAL_RATIO))

    def _split(df):
        return (df.iloc[:tr_end].copy(),
                df.iloc[tr_end:va_end].copy(),
                df.iloc[va_end:].copy())

    raw_tr,  raw_va,  raw_te   = _split(df_raw)
    feat_tr, feat_va, feat_te  = _split(df_feat)
    mkt_tr,  mkt_va,  mkt_te   = _split(df_market)

    print(f"\n{'='*65}")
    print("Step 2  数据集划分（日频 70/15/15）")
    print(f"{'='*65}")
    print(f"  训练集  {len(raw_tr):>5} 天  "
          f"{raw_tr.index[0].date()} ~ {raw_tr.index[-1].date()}")
    print(f"  验证集  {len(raw_va):>5} 天  "
          f"{raw_va.index[0].date()} ~ {raw_va.index[-1].date()}")
    print(f"  测试集  {len(raw_te):>5} 天  "
          f"{raw_te.index[0].date()} ~ {raw_te.index[-1].date()}")

    return (raw_tr, raw_va, raw_te,
            feat_tr, feat_va, feat_te,
            mkt_tr, mkt_va, mkt_te)


# ================================================================
# Step 3A  XGBoost 推断
# ================================================================
def load_xgb():
    payload = joblib.load(XGB_PATH)
    if isinstance(payload, dict):
        model        = payload["model"]
        feature_cols = payload["feature_cols"]
    else:
        # 直接是模型对象
        model        = payload
        feature_cols = model.get_booster().feature_names
    print(f"\n[XGBoost] 加载成功  特征数：{len(feature_cols)}")
    return model, feature_cols


def xgb_predict(xgb_model, feature_cols, df):
    """
    XGBoost 推断。
    新版本预测目标是 next_return（涨跌幅），直接输出正负值。
    旧版本预测 risk（>=0），用 clip 保证非负。
    """
    X = df.select_dtypes(include=[np.number]).copy()
    X_out = pd.DataFrame(index=df.index)
    for col in feature_cols:
        X_out[col] = X[col] if col in X.columns else np.nan
    return xgb_model.predict(X_out.values)  # 不再 clip，允许负值


# ================================================================
# Step 3B  LSTM 推断（日频滑窗，与训练时完全一致）
# ================================================================
def load_lstm():
    price_scaler = joblib.load(PRICE_SCALER_PATH)
    feat_scaler  = joblib.load(FEAT_SCALER_PATH)
    feat_cols    = joblib.load(FEAT_COLS_PATH)
    print(f"[LSTM] feature_cols.pkl：{feat_cols}")

    # 排除标签列，只保留特征列
    feat_cols = [c for c in feat_cols
                 if c not in {"y_price", "y_label", "next_return", "risk"}]

    print(f"[LSTM] PyTorch 加载成功  特征数：{len(feat_cols)}")

    try:
        import tensorflow as tf
        model = tf.keras.models.load_model(LSTM_MODEL_KERAS)
        print(f"[LSTM] Keras 加载成功  特征数：{len(feat_cols)}")
        return model, price_scaler, feat_scaler, feat_cols, "keras"
    except (ImportError, Exception):
        import torch
        import torch.nn as nn

        class _LSTMModel(nn.Module):
            def __init__(self, n_feat):
                super().__init__()
                units = [128, 64]
                in_sz = n_feat
                self.lstms = nn.ModuleList()
                for u in units:
                    self.lstms.append(
                        nn.LSTM(in_sz, u, batch_first=True, bidirectional=False))
                    in_sz = u
                self.bn      = nn.BatchNorm1d(in_sz)
                self.drop    = nn.Dropout(0.2)
                self.fc_price = nn.Sequential(nn.Linear(in_sz, 32), nn.ReLU())
                self.fc_cls   = nn.Sequential(nn.Linear(in_sz, 16), nn.ReLU())
                self.hp = nn.Linear(32, 1)
                self.hb = nn.Linear(16, 1)

            def forward(self, x):
                for lstm in self.lstms:
                    x, _ = lstm(x)
                x = self.drop(self.bn(x[:, -1, :]))
                return (self.hp(self.fc_price(x)).squeeze(-1),
                        torch.sigmoid(self.hb(self.fc_cls(x))).squeeze(-1))

        m = _LSTMModel(len(feat_cols))
        m.load_state_dict(torch.load(LSTM_MODEL_PT, map_location="cpu"))
        m.eval()
        print(f"[LSTM] PyTorch 加载成功  特征数：{len(feat_cols)}")
        return m, price_scaler, feat_scaler, feat_cols, "torch"


def lstm_predict_df(lstm_model, price_scaler, feat_scaler,
                    feat_cols, backend, df_segment, df_feat_all):
    """
    对 df_segment 的每一天，用该天之前 LOOKBACK 天的 LSTM特征 做推断。
    df_feat_all：完整的 LSTM 特征工程数据（27列），提供滑窗上下文。
    current_price 从 df_segment 的 TARGET_COL 取（原始价格，反归一化用）。
    """
    # feat_cols 是训练时的完整列列表（28列），缺失列用0填充保证维度一致
    label_cols = {"y_price", "y_label", "next_return", "risk"}
    fc = [c for c in feat_cols if c not in label_cols]

    feat_arr = np.zeros((len(df_feat_all), len(fc)), dtype=np.float32)
    for i, col in enumerate(fc):
        if col in df_feat_all.columns:
            feat_arr[:, i] = pd.to_numeric(
                df_feat_all[col], errors="coerce").fillna(0).values

    feat_scaled = feat_scaler.transform(feat_arr)
    all_index   = df_feat_all.index

    impl_returns = []
    for date in df_segment.index:
        if date not in all_index:
            impl_returns.append(0.0)
            continue

        loc   = all_index.get_loc(date)
        start = loc - LOOKBACK
        if start < 0:
            pad    = np.zeros((-start, feat_scaled.shape[1]))
            window = np.vstack([pad, feat_scaled[:loc]])
        else:
            window = feat_scaled[start:loc]

        X = window[np.newaxis].astype(np.float32)

        if backend == "keras":
            pp, _ = lstm_model.predict(X, verbose=0)
            pred_scaled = float(pp[0][0])
        else:
            import torch
            with torch.no_grad():
                pp, _ = lstm_model(torch.FloatTensor(X))
            pred_scaled = float(pp.numpy()[0])

        pred_price    = float(price_scaler.inverse_transform([[pred_scaled]])[0][0])
        current_price = float(df_segment.loc[date, TARGET_COL])
        impl_returns.append((pred_price - current_price) / (current_price + 1e-8))

    return np.array(impl_returns)


def get_lstm_features(lstm_model, price_scaler, feat_scaler,
                      feat_cols, backend,
                      raw_tr, raw_va, raw_te, df_feat_all):
    """
    raw_tr/va/te：原始数据切片（含 TARGET_COL 用于取当前价格）
    df_feat_all ：完整 LSTM 特征工程数据（27列，用于滑窗）
    """
    print("\n[LSTM] 生成 impl_return（LSTM特征工程数据滑窗，无泄漏）...")

    impl_tr = lstm_predict_df(lstm_model, price_scaler, feat_scaler,
                               feat_cols, backend, raw_tr, df_feat_all)
    print(f"  训练集  {len(impl_tr)} 天  "
          f"均值={impl_tr.mean()*100:.3f}%  "
          f"正值占比={(impl_tr > 0).mean():.1%}")

    impl_va = lstm_predict_df(lstm_model, price_scaler, feat_scaler,
                               feat_cols, backend, raw_va, df_feat_all)
    print(f"  验证集  {len(impl_va)} 天  "
          f"均值={impl_va.mean()*100:.3f}%  "
          f"正值占比={(impl_va > 0).mean():.1%}")

    impl_te = lstm_predict_df(lstm_model, price_scaler, feat_scaler,
                               feat_cols, backend, raw_te, df_feat_all)
    print(f"  测试集  {len(impl_te)} 天  "
          f"均值={impl_te.mean()*100:.3f}%  "
          f"正值占比={(impl_te > 0).mean():.1%}")

    return impl_tr, impl_va, impl_te


# ================================================================
# Step 4  拼装元特征矩阵
# ================================================================
def build_meta_X(df_seg, df_mkt, impl_return, xgb_pred):
    """
    元特征 9 维：市场状态(7) + lstm_impl_return(1) + xgb_next_return(1)
    xgb_pred：XGBoost 预测的 next_return（涨跌幅，有正有负）
    目标：next_return × 100（%）
    """
    market      = df_mkt[MARKET_STATE_COLS].fillna(0).values.astype(float)
    impl_return = np.nan_to_num(impl_return, nan=0.0)
    xgb_r       = np.nan_to_num(xgb_pred,   nan=0.0)
    X = np.column_stack([market, impl_return, xgb_r])
    y = df_seg["next_return"].values.astype(float) * 100
    return X, y


# ================================================================
# Step 5  训练 Ridge 元学习器
# ================================================================
def train_meta_learner(X_tr, y_tr, X_va, y_va):
    print(f"\n{'='*65}")
    print("Step 5  训练 Ridge 元学习器")
    print(f"  输入：9维  目标：next_return×100（%）")
    print("=" * 65)

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)

    best_mae, best_alpha, best_model = np.inf, 1.0, None
    print(f"\n  Alpha 搜索（验证集 MAE）：")
    for alpha in [1e-4, 1e-3, 0.01, 0.1, 1.0, 10.0, 100.0]:
        ridge = Ridge(alpha=alpha)
        ridge.fit(X_tr_s, y_tr)
        pred  = ridge.predict(X_va_s)
        mae   = mean_absolute_error(y_va, pred)
        sp    = spearmanr(y_va, pred).correlation
        d_acc = ((pred > 0) == (y_va > 0)).mean()
        print(f"    alpha={alpha:<8}  MAE={mae:.3f}%  "
              f"Spearman={sp:.3f}  方向准确率={d_acc:.1%}")
        if mae < best_mae:
            best_mae, best_alpha, best_model = mae, alpha, ridge

    print(f"\n  最优 alpha={best_alpha}  Val MAE={best_mae:.3f}%")

    # 训练集 + 验证集合并重训最终模型
    scaler_final = StandardScaler()
    X_tv_s = scaler_final.fit_transform(np.vstack([X_tr, X_va]))
    y_tv   = np.concatenate([y_tr, y_va])
    final_ridge = Ridge(alpha=best_alpha)
    final_ridge.fit(X_tv_s, y_tv)

    feat_names = MARKET_STATE_COLS + ["lstm_impl_return", "xgb_risk"]
    coef_df = pd.DataFrame({
        "feature":     feat_names,
        "coefficient": final_ridge.coef_,
    }).sort_values("coefficient", ascending=False)
    print(f"\n  Ridge 特征系数（正=看涨，负=看跌，单位 %）：")
    print(coef_df.to_string(index=False))

    return final_ridge, scaler_final


def save_meta_learner(ridge, scaler, high_thresh, low_thresh):
    joblib.dump({
        "model":         ridge,
        "scaler":        scaler,
        "feature_names": MARKET_STATE_COLS + ["lstm_impl_return", "xgb_risk"],
        "target":        "next_return_5d × 100 (%)",
        "high_thresh":   high_thresh,
        "low_thresh":    low_thresh,
    }, META_PATH)
    print(f"\n[保存] 元学习器 → {META_PATH}")


# ================================================================
# Step 6  风险区间
# ================================================================
def assign_risk_zone(pred_return_pct, high_thresh, low_thresh):
    """pred_return_pct 单位为 %（已×100）"""
    zones = np.ones(len(pred_return_pct), dtype=int)
    zones[pred_return_pct <= high_thresh] = 2   # 高风险
    zones[pred_return_pct >= low_thresh]  = 0   # 低风险
    return zones


# ================================================================
# Step 7  回测评估
# ================================================================
def topk_lift(y_true_ret, y_pred_ret, k=0.10, shock=SHOCK_THRESH):
    n   = len(y_true_ret)
    m   = max(1, int(n * k))
    idx = np.argsort(y_pred_ret)[:m]
    event     = (y_true_ret <= shock).astype(int)
    hit_rate  = event[idx].mean()
    base_rate = event.mean()
    lift      = hit_rate / (base_rate + 1e-8)
    return hit_rate, base_rate, lift


def sharpe(next_ret, pred_ret_pct, high_thresh_pct, annualize=252):
    pos      = np.where(pred_ret_pct <= high_thresh_pct, -1.0, 1.0)
    strat    = next_ret * pos
    return float(strat.mean() / (strat.std() + 1e-8) * np.sqrt(annualize))


def compute_metrics(y_true_ret, y_pred_ret_pct):
    """y_true_ret：小数；y_pred_ret_pct：百分比"""
    y_pred_ret = y_pred_ret_pct / 100
    rmse    = np.sqrt(mean_squared_error(y_true_ret * 100, y_pred_ret_pct))
    mae     = mean_absolute_error(y_true_ret * 100, y_pred_ret_pct)
    sp      = spearmanr(y_true_ret, y_pred_ret).correlation
    dir_acc = ((y_pred_ret > 0) == (y_true_ret > 0)).mean()
    hit10, base10, lift10 = topk_lift(y_true_ret, y_pred_ret, k=0.10)
    hit20, _,      lift20 = topk_lift(y_true_ret, y_pred_ret, k=0.20)
    h_thresh = np.percentile(y_pred_ret_pct, 25)
    sh       = sharpe(y_true_ret, y_pred_ret_pct, h_thresh)
    return dict(rmse=rmse, mae=mae, sp=sp, dir_acc=dir_acc,
                hit10=hit10, lift10=lift10, base10=base10,
                hit20=hit20, lift20=lift20, sharpe=sh)


def evaluate_test(ridge, scaler, X_te, y_ret_te,
                  df_test, xgb_te, impl_te, high_thresh, low_thresh):
    print(f"\n{'='*65}")
    print("Step 7  测试集全面回测评估")
    print("=" * 65)

    pred_pct = ridge.predict(scaler.transform(X_te))          # 单位 %
    zones    = assign_risk_zone(pred_pct, high_thresh, low_thresh)
    zone_map = {0: "低风险🟢", 1: "中风险🟡", 2: "高风险🔴"}

    # XGBoost：直接用预测的 next_return
    xgb_pct  = xgb_te * 100
    lstm_pct = impl_te * 100

    m_xgb  = compute_metrics(y_ret_te, xgb_pct)
    m_lstm = compute_metrics(y_ret_te, lstm_pct)
    m_meta = compute_metrics(y_ret_te, pred_pct)

    # ── 对比表 ──
    print(f"\n  {'指标':<20} {'XGBoost':>10} {'LSTM':>10} {'Meta-Ridge':>12}")
    print(f"  {'─'*54}")
    rows = [
        ("RMSE (%)",       "rmse",    False),
        ("MAE (%)",        "mae",     False),
        ("Spearman",       "sp",      True),
        ("方向准确率",      "dir_acc", True),
        ("Top10% 命中率",   "hit10",   True),
        ("Top10% Lift",    "lift10",  True),
        ("Top20% 命中率",   "hit20",   True),
        ("Top20% Lift",    "lift20",  True),
        ("策略夏普比率",    "sharpe",  True),
    ]
    for label, key, higher in rows:
        vx, vl, vm = m_xgb[key], m_lstm[key], m_meta[key]
        best_val   = (max if higher else min)(vx, vl, vm)
        def fmt(v): return f"{'★':>2}{v:>8.4f}" if v == best_val else f"  {v:>8.4f}"
        print(f"  {label:<20} {fmt(vx)} {fmt(vl)} {fmt(vm)}")

    print(f"\n  Top10% 基准命中率：{m_meta['base10']:.3f}")

    # ── 风险区间分布 ──
    print(f"\n  风险区间分布（Meta-Ridge，测试集 {len(zones)} 天）：")
    for code, name in zone_map.items():
        cnt   = (zones == code).sum()
        mask  = zones == code
        shock = (y_ret_te[mask] <= SHOCK_THRESH).mean() if cnt > 0 else 0
        avg_r = y_ret_te[mask].mean() * 100 if cnt > 0 else 0
        print(f"    {name}  {cnt:>5} 天  占比 {cnt/len(zones):.1%}  "
              f"平均真实收益 {avg_r:+.3f}%  冲击命中率 {shock:.1%}")

    return pred_pct, zones, m_xgb, m_lstm, m_meta


# ================================================================
# Step 8  可视化
# ================================================================
def plot_results(df_test, pred_pct, zones, xgb_te, impl_te,
                 m_xgb, m_lstm, m_meta):
    dates  = df_test.index
    y_ret  = df_test["next_return"].values
    y_pct  = y_ret * 100
    zone_colors = {0: "#2ecc71", 1: "#f39c12", 2: "#e74c3c"}
    zone_names  = {0: "低风险", 1: "中风险", 2: "高风险"}

    # ── 图1：预测 vs 真实 & 策略收益 ──
    fig, axes = plt.subplots(3, 1, figsize=(14, 14))

    ax = axes[0]
    ax.plot(dates, y_pct,        label="真实收益(%)",    color="steelblue", lw=1.2, alpha=0.8)
    ax.plot(dates, pred_pct,     label="Meta-Ridge预测", color="tomato",    lw=1.2, ls="--")
    ax.plot(dates, impl_te * 100, label="LSTM隐含收益",  color="orange",    lw=0.8, alpha=0.6)
    ax.axhline(0, color="black", lw=0.8, ls="--")
    ax.set_title(
        f"收益预测对比（测试集）  "
        f"Meta-Ridge: MAE={m_meta['mae']:.2f}%  "
        f"方向={m_meta['dir_acc']:.1%}  Spearman={m_meta['sp']:.3f}",
        fontsize=11, fontweight="bold")
    ax.set_ylabel("5日涨跌幅 (%)"); ax.legend(); ax.grid(alpha=0.3)

    ax2 = axes[1]
    ax2.bar(range(len(zones)), y_pct,
            color=[zone_colors[z] for z in zones], alpha=0.75, width=1.0)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.axhline(SHOCK_THRESH * 100, color="red", lw=1, ls="--",
                label=f"冲击阈值 {SHOCK_THRESH*100:.0f}%")
    from matplotlib.patches import Patch
    ax2.legend(handles=[
        Patch(facecolor=zone_colors[c], label=zone_names[c]) for c in [2, 1, 0]
    ] + [plt.Line2D([0],[0], color="red", ls="--")], loc="upper right")
    ax2.set_title("风险区间标注（柱色=Meta-Ridge预测，柱高=真实收益）",
                  fontsize=11, fontweight="bold")
    ax2.set_ylabel("真实5日涨跌幅 (%)"); ax2.grid(alpha=0.3)

    ax3 = axes[2]
    high_thresh_pct = np.percentile(pred_pct, 25)
    pos         = np.where(pred_pct <= high_thresh_pct, -1.0, 1.0)
    strat_ret   = y_ret * pos
    cum_strat   = (1 + strat_ret).cumprod()
    cum_bh      = (1 + y_ret).cumprod()
    ax3.plot(dates, cum_strat, label=f"Meta-Ridge策略  夏普={m_meta['sharpe']:.2f}",
             color="tomato", lw=1.8)
    ax3.plot(dates, cum_bh,    label="Buy & Hold",
             color="steelblue", lw=1.5, ls="--")
    ax3.axhline(1, color="gray", lw=0.8, ls=":")
    ax3.set_title("策略累计收益 vs Buy & Hold", fontsize=11, fontweight="bold")
    ax3.set_ylabel("累计收益（初始=1）"); ax3.legend(); ax3.grid(alpha=0.3)

    plt.tight_layout()
    p1 = os.path.join(PLOT_DIR, "meta_ridge_evaluation.png")
    plt.savefig(p1, dpi=150, bbox_inches="tight"); plt.close()
    print(f"\n[图表] 评估图 → {p1}")

    # ── 图2：三模型散点对比 ──
    fig2, axes2 = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (pred, title, m) in zip(axes2, [
        (-xgb_te * 100, "XGBoost (-risk×100)", m_xgb),
        (impl_te * 100, "LSTM impl_return",     m_lstm),
        (pred_pct,      "Meta-Ridge",            m_meta),
    ]):
        ax.scatter(y_pct, pred, alpha=0.3, s=10, color="steelblue")
        lim = max(abs(y_pct).max(), abs(pred).max()) * 1.1
        ax.plot([-lim, lim], [-lim, lim], "r--", lw=1)
        ax.axhline(0, color="gray", lw=0.5); ax.axvline(0, color="gray", lw=0.5)
        ax.set_title(f"{title}\nSpearman={m['sp']:.3f}  方向={m['dir_acc']:.1%}",
                     fontsize=10, fontweight="bold")
        ax.set_xlabel("真实收益 (%)"); ax.set_ylabel("预测 (%)"); ax.grid(alpha=0.3)
    plt.suptitle("三模型散点对比（测试集）", fontsize=12, fontweight="bold")
    plt.tight_layout()
    p2 = os.path.join(PLOT_DIR, "scatter_comparison.png")
    plt.savefig(p2, dpi=150, bbox_inches="tight"); plt.close()
    print(f"[图表] 散点图 → {p2}")

    # ── 图3：指标柱状对比 ──
    fig3, axes3 = plt.subplots(2, 3, figsize=(15, 8))
    fig3.suptitle("三模型性能对比（测试集）", fontsize=13, fontweight="bold")
    colors = ["#3498db", "#e67e22", "#e74c3c"]
    models = ["XGBoost", "LSTM", "Meta-Ridge"]
    for ax, (title, vals, higher) in zip(axes3.flatten(), [
        ("方向准确率",   [m_xgb["dir_acc"], m_lstm["dir_acc"], m_meta["dir_acc"]], True),
        ("Spearman",    [m_xgb["sp"],       m_lstm["sp"],       m_meta["sp"]],     True),
        ("MAE (%)",     [m_xgb["mae"],      m_lstm["mae"],      m_meta["mae"]],    False),
        ("Top10% Lift", [m_xgb["lift10"],   m_lstm["lift10"],   m_meta["lift10"]], True),
        ("Top20% Lift", [m_xgb["lift20"],   m_lstm["lift20"],   m_meta["lift20"]], True),
        ("夏普比率",     [m_xgb["sharpe"],   m_lstm["sharpe"],   m_meta["sharpe"]], True),
    ]):
        bars = ax.bar(models, vals, color=colors, alpha=0.85, edgecolor="white")
        best_idx = int(np.argmax(vals)) if higher else int(np.argmin(vals))
        bars[best_idx].set_edgecolor("black"); bars[best_idx].set_linewidth(2.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + abs(max(vals, key=abs)) * 0.02,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=9)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.grid(alpha=0.3, axis="y")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    p3 = os.path.join(PLOT_DIR, "model_comparison.png")
    plt.savefig(p3, dpi=150, bbox_inches="tight"); plt.close()
    print(f"[图表] 对比图 → {p3}")


# ================================================================
# Step 9  保存结果
# ================================================================
def save_results(df_test, pred_pct, zones, xgb_te, impl_te):
    zone_map = {0: "低风险", 1: "中风险", 2: "高风险"}
    pd.DataFrame({
        "true_price":          df_test[TARGET_COL].values,
        "true_return_pct":     df_test["next_return"].values * 100,
        "xgb_risk":            xgb_te,
        "lstm_impl_return_pct": impl_te * 100,
        "meta_pred_return_pct": pred_pct,
        "risk_zone":           [zone_map[z] for z in zones],
    }, index=df_test.index).to_csv(RESULT_PATH, encoding="utf-8-sig")
    print(f"[保存] 测试集结果 → {RESULT_PATH}")


# ================================================================
# 主流程
# ================================================================
def main():
    print("\n" + "🟡 " * 22)
    print("    花旗杯 | Stacking 集成模型（全日频）")
    print("🟡 " * 22 + "\n")

    # Step 1-2
    df_raw, df_feat, df_market = load_data()
    (raw_tr, raw_va, raw_te,
     feat_tr, feat_va, feat_te,
     mkt_tr, mkt_va, mkt_te) = split_data(df_raw, df_feat, df_market)

    # Step 3
    print(f"\n{'='*65}\nStep 3  基础模型推断\n{'='*65}")

    # XGBoost 用原始未填充数据（与训练时一致）
    xgb_model, xgb_feat_cols = load_xgb()
    xgb_tr = xgb_predict(xgb_model, xgb_feat_cols, raw_tr)
    xgb_va = xgb_predict(xgb_model, xgb_feat_cols, raw_va)
    xgb_te = xgb_predict(xgb_model, xgb_feat_cols, raw_te)

    matched   = [c for c in xgb_feat_cols if c in raw_tr.columns]
    unmatched = [c for c in xgb_feat_cols if c not in raw_tr.columns]
    print(f"[XGBoost诊断] 特征匹配  命中={len(matched)}/{len(xgb_feat_cols)}  缺失={len(unmatched)}")
    print(f"[XGBoost诊断] xgb_te 分布  "
          f"min={xgb_te.min():.4f}  p25={np.percentile(xgb_te,25):.4f}  "
          f"p50={np.percentile(xgb_te,50):.4f}  p75={np.percentile(xgb_te,75):.4f}  "
          f"max={xgb_te.max():.4f}")

    # LSTM 用特征工程数据（ffill后的27列）
    lstm_model, price_scaler, feat_scaler, feat_cols, backend = load_lstm()
    label_cols   = {"y_price", "y_label", "next_return", "risk"}
    fc_diag      = [c for c in feat_cols if c not in label_cols]
    missing_cols = [c for c in fc_diag if c not in df_feat.columns]
    print(f"\n[诊断] feat_scaler 类型：{type(feat_scaler).__name__}")
    print(f"[诊断] feat_cols 共{len(fc_diag)}列  df_feat缺失列：{missing_cols if missing_cols else '无'}")

    impl_tr, impl_va, impl_te = get_lstm_features(
        lstm_model, price_scaler, feat_scaler, feat_cols, backend,
        raw_tr, raw_va, raw_te, df_feat)

    # Step 4
    print(f"\n{'='*65}\nStep 4  拼装元特征矩阵\n{'='*65}")
    print(f"[诊断] 长度检查：")
    print(f"  raw_tr={len(raw_tr)} mkt_tr={len(mkt_tr)} impl_tr={len(impl_tr)} xgb_tr={len(xgb_tr)}")
    print(f"  raw_va={len(raw_va)} mkt_va={len(mkt_va)} impl_va={len(impl_va)} xgb_va={len(xgb_va)}")
    print(f"  raw_te={len(raw_te)} mkt_te={len(mkt_te)} impl_te={len(impl_te)} xgb_te={len(xgb_te)}")
    X_tr, y_tr = build_meta_X(raw_tr, mkt_tr, impl_tr, xgb_tr)
    X_va, y_va = build_meta_X(raw_va, mkt_va, impl_va, xgb_va)
    X_te, y_te = build_meta_X(raw_te, mkt_te, impl_te, xgb_te)
    print(f"  维度  训练={X_tr.shape}  验证={X_va.shape}  测试={X_te.shape}")
    print(f"  目标均值(%)  训练={y_tr.mean():.3f}  "
          f"验证={y_va.mean():.3f}  测试={y_te.mean():.3f}")
    print(f"  目标std(%)   训练={y_tr.std():.3f}  "
          f"验证={y_va.std():.3f}  测试={y_te.std():.3f}")

    # Step 5
    ridge, scaler = train_meta_learner(X_tr, y_tr, X_va, y_va)

    pred_tv     = ridge.predict(scaler.transform(np.vstack([X_tr, X_va])))
    high_thresh = float(np.percentile(pred_tv, 25))
    low_thresh  = float(np.percentile(pred_tv, 75))
    print(f"\n  风险阈值：高风险 ≤ {high_thresh:.3f}%  低风险 ≥ {low_thresh:.3f}%")
    save_meta_learner(ridge, scaler, high_thresh, low_thresh)

    # Step 7
    y_ret_te = raw_te["next_return"].values
    pred_pct, zones, m_xgb, m_lstm, m_meta = evaluate_test(
        ridge, scaler, X_te, y_ret_te,
        raw_te, xgb_te, impl_te, high_thresh, low_thresh)

    # Step 8-9
    plot_results(raw_te, pred_pct, zones, xgb_te, impl_te,
                 m_xgb, m_lstm, m_meta)
    save_results(raw_te, pred_pct, zones, xgb_te, impl_te)

    print(f"\n✅ 完成！")
    print(f"   元学习器  → {META_PATH}")
    print(f"   结果      → {RESULT_PATH}")
    print(f"   图表      → {PLOT_DIR}")


# ================================================================
# 单步推断接口
# ================================================================
def predict_one_step(market_state: np.ndarray,
                     lstm_impl_return: float,
                     xgb_risk: float) -> dict:
    payload     = joblib.load(META_PATH)
    ridge       = payload["model"]
    scaler      = payload["scaler"]
    high_thresh = payload["high_thresh"]
    low_thresh  = payload["low_thresh"]

    x        = np.array([*market_state, lstm_impl_return, xgb_risk]).reshape(1, -1)
    pred_pct = float(ridge.predict(scaler.transform(x))[0])

    zone = ("高风险🔴" if pred_pct <= high_thresh else
            "低风险🟢" if pred_pct >= low_thresh  else "中风险🟡")
    return {"pred_return_pct": round(pred_pct, 3), "risk_zone": zone}


if __name__ == "__main__":
    main()