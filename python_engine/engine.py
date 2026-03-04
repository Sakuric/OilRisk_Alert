"""
OilRisk-Alert 推理引擎 — 封装 LSTM / XGBoost / Stacking 三模型
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
import shap

warnings.filterwarnings("ignore")

# ── 路径配置 ──
MODEL_DIR = os.environ.get(
    "MODEL_DIR",
    os.path.join(os.path.dirname(__file__), "..", "OilRisk_System"),
)
DATA_PATH = os.environ.get(
    "DATA_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "Final_Oil_Dataset_Cleaned.csv"),
)

# ── LSTM 列名映射（与训练代码完全一致）──
LSTM_COLS = {
    "target": "Price_WTI_WTI期货_close",
    "crb": "CRB现货指数_日频",
    "sp500": "Macro_SP500_标普500指数_SP500_Close",
    "tips": "Macro_CPI_10年期通胀预期_T10YIE",
    "hy": "情绪组_HY_S_Value",
    "vix": "Risk_VIX_情绪组_VIX__Value",
    "ovx": "Risk_VIX_情绪组_OVX__Value",
    "cushing": "Supply_Inventory_US_Cushing__Value (库存)",
    "opec": "Supply_Production_OPEC_OPEC每月原油_OPEC石油输出国组织",
    "saudi": "Supply_Production_OPEC_OPEC每月原油_沙特阿拉伯",
    "russia": "Supply_Production_OPEC_非OPEC国家原_俄罗斯联邦",
    "cn_pmi": "Demand_PMI_中国制造业PMI_China_Manufacturing_PMI",
    "eu_pmi": "Demand_PMI_欧元区制造业PM_Eurozone_Manufacturing_PMI",
    "us_sentiment": "Demand_PMI_美国制造业PMI_US_Consumer_Sentiment",
}

TARGET_COL = "Price_WTI_WTI期货_close"
LOOKBACK = 30
HORIZON = 5

MARKET_STATE_COLS = [
    "Risk_VIX_VIX恐慌指数_VIX_Index",
    "Risk_VIX_情绪组_OVX__Value",
    "Macro_Yield_美债10年收益率_US_10Y_Treasury_Yield",
    "美元指数_日频",
    "Risk_Sentiment_新闻情感指数__News_Sentiment",
    "Risk_Geopolitics_地缘政治事件综合评分",
    "Macro_SP500_标普500指数_SP500_Close",
]

FACTOR_CATEGORY_MAP = {
    "vix": "FINANCIAL", "ovx": "FINANCIAL", "hy": "FINANCIAL",
    "spread": "FINANCIAL", "credit": "FINANCIAL",
    "sentiment": "SENTIMENT", "news": "SENTIMENT",
    "gpr": "GEOPOLITICAL", "geopolitics": "GEOPOLITICAL",
    "opec": "SUPPLY_DEMAND", "supply": "SUPPLY_DEMAND",
    "production": "SUPPLY_DEMAND", "inventory": "SUPPLY_DEMAND",
    "cushing": "SUPPLY_DEMAND", "rig": "SUPPLY_DEMAND",
    "demand": "SUPPLY_DEMAND", "pmi": "MACRO",
    "gdp": "MACRO", "cpi": "MACRO", "yield": "MACRO",
    "treasury": "MACRO", "dollar": "MACRO", "exchange": "MACRO",
    "sp500": "MACRO", "macro": "MACRO",
}


def _classify_factor(name: str) -> str:
    low = name.lower()
    for kw, cat in FACTOR_CATEGORY_MAP.items():
        if kw in low:
            return cat
    return "OTHER"


# ── PyTorch LSTM 模型定义（与训练代码完全一致）──
class LSTMTrendExpert(nn.Module):
    def __init__(self, n_feat, units, dropout, bidir=False):
        super().__init__()
        nd = 2 if bidir else 1
        self.lstms = nn.ModuleList()
        in_sz = n_feat
        for u in units:
            self.lstms.append(nn.LSTM(in_sz, u, batch_first=True, bidirectional=bidir))
            in_sz = u * nd
        self.bn = nn.BatchNorm1d(in_sz)
        self.drop = nn.Dropout(dropout)
        self.fc_price = nn.Sequential(nn.Linear(in_sz, 32), nn.ReLU())
        self.fc_cls = nn.Sequential(nn.Linear(in_sz, 16), nn.ReLU())
        self.hp = nn.Linear(32, 1)
        self.hb = nn.Linear(16, 1)

    def forward(self, x):
        for lstm in self.lstms:
            x, _ = lstm(x)
        x = self.drop(self.bn(x[:, -1, :]))
        return (
            self.hp(self.fc_price(x)).squeeze(-1),
            torch.sigmoid(self.hb(self.fc_cls(x))).squeeze(-1),
        )


def _build_lstm_features(df: pd.DataFrame) -> pd.DataFrame:
    """复现 LSTM load_and_engineer 的特征工程。"""
    target = LSTM_COLS["target"]
    price = df[target]
    feat = pd.DataFrame(index=df.index)

    feat["price"] = price
    for k in ["crb", "sp500", "tips", "hy", "vix", "ovx", "cushing"]:
        col = LSTM_COLS[k]
        if col in df.columns:
            feat[k] = df[col]

    for k in ["opec", "saudi", "russia", "cn_pmi", "eu_pmi", "us_sentiment"]:
        col = LSTM_COLS[k]
        if col in df.columns:
            monthly_chg = df[col].resample("ME").last().diff()
            feat[f"{k}_chg"] = monthly_chg.reindex(df.index, method="ffill")

    feat["ma5"] = price.rolling(5).mean()
    feat["ma20"] = price.rolling(20).mean()
    feat["ma60"] = price.rolling(60).mean()
    feat["dev_ma5"] = (price - feat["ma5"]) / (feat["ma5"] + 1e-8)
    feat["dev_ma20"] = (price - feat["ma20"]) / (feat["ma20"] + 1e-8)
    feat["dev_ma60"] = (price - feat["ma60"]) / (feat["ma60"] + 1e-8)
    feat["mom5"] = np.log(price / price.shift(5).replace(0, np.nan))
    feat["mom20"] = np.log(price / price.shift(20).replace(0, np.nan))
    feat["hvol20"] = np.log(price / price.shift(1)).rolling(20).std()
    if "cushing" in feat.columns:
        feat["cushing_chg5"] = feat["cushing"].diff(5)

    feat["mom_accel"] = feat["mom5"] - feat["mom5"].shift(3)
    if "vix" in feat.columns:
        feat["vix_chg3"] = feat["vix"].pct_change(3)
    if "ovx" in feat.columns:
        feat["ovx_chg3"] = feat["ovx"].pct_change(3)

    feat["y_price"] = price.shift(-HORIZON)
    feat["y_label"] = (feat["y_price"] > price).astype(int)
    feat = feat.dropna()
    return feat


class OilRiskEngine:
    """加载全部模型，提供 predict_daily / predict_backtest 方法。"""

    def __init__(self):
        self.device = torch.device("cpu")

        # 加载预处理器
        self.lstm_feat_cols = joblib.load(os.path.join(MODEL_DIR, "feature_cols.pkl"))
        self.price_scaler = joblib.load(os.path.join(MODEL_DIR, "price_scaler.pkl"))
        self.feat_scaler = joblib.load(os.path.join(MODEL_DIR, "feat_scaler.pkl"))

        # 排除标签列
        self._fc = [c for c in self.lstm_feat_cols if c not in {"y_price", "y_label", "next_return", "risk"}]

        # 加载 LSTM
        self.lstm_model = LSTMTrendExpert(len(self._fc), [128, 64], 0.2)
        self.lstm_model.load_state_dict(
            torch.load(os.path.join(MODEL_DIR, "best_lstm.pt"), map_location=self.device, weights_only=True)
        )
        self.lstm_model.eval()

        # 加载 XGBoost
        self.xgb_model = joblib.load(os.path.join(MODEL_DIR, "xgb_wti_shock_model.pkl"))
        if hasattr(self.xgb_model, "feature_names_in_"):
            self.xgb_features = list(self.xgb_model.feature_names_in_)
        else:
            self.xgb_features = self.xgb_model.get_booster().feature_names

        # 加载 Stacking meta learner
        meta_payload = joblib.load(os.path.join(MODEL_DIR, "meta_ridge_model.pkl"))
        self.ridge = meta_payload["model"]
        self.ridge_scaler = meta_payload["scaler"]
        self.high_thresh = meta_payload["high_thresh"]
        self.low_thresh = meta_payload["low_thresh"]

        # 预计算 XGBoost SHAP (TreeExplainer)
        self.xgb_explainer = shap.TreeExplainer(self.xgb_model)

        # 预加载数据
        self.df_raw, self.df_feat, self.df_ffill = self._load_data()

    def _load_data(self):
        df_orig = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
        date_col = next((c for c in df_orig.columns if "date" in c.lower()), "Date")
        df_orig[date_col] = pd.to_datetime(df_orig[date_col])
        df_orig = df_orig.sort_values(date_col).set_index(date_col)

        df_ffill = df_orig.ffill().bfill()
        wti_valid_idx = df_orig[df_orig[TARGET_COL].notna()].index
        df_valid = df_ffill.loc[wti_valid_idx].copy()

        df_feat = _build_lstm_features(df_valid)
        df_raw = df_orig.loc[df_feat.index].copy()
        df_raw = df_raw.ffill().bfill()

        return df_raw, df_feat, df_ffill

    # ── LSTM 推理 ──
    def _lstm_predict_single(self, df_feat_segment, idx):
        """对 df_feat_segment 中 idx 位置做 LSTM 推理，返回 (pred_price, up_prob)。"""
        feat_arr = np.zeros((len(df_feat_segment), len(self._fc)), dtype=np.float32)
        for i, col in enumerate(self._fc):
            if col in df_feat_segment.columns:
                feat_arr[:, i] = pd.to_numeric(
                    df_feat_segment[col], errors="coerce"
                ).fillna(0).values

        feat_scaled = self.feat_scaler.transform(feat_arr)
        start = idx - LOOKBACK
        if start < 0:
            pad = np.zeros((-start, feat_scaled.shape[1]), dtype=np.float32)
            window = np.vstack([pad, feat_scaled[:idx]])
        else:
            window = feat_scaled[start:idx]

        X = window[np.newaxis].astype(np.float32)
        with torch.no_grad():
            pp, pb = self.lstm_model(torch.from_numpy(X).to(self.device))
        pred_scaled = float(pp.cpu().numpy()[0])
        up_prob = float(pb.cpu().numpy()[0])
        pred_price = float(self.price_scaler.inverse_transform([[pred_scaled]])[0][0])
        return pred_price, up_prob

    # ── XGBoost 推理 ──
    def _xgb_predict(self, row_df):
        X = pd.DataFrame(index=row_df.index)
        for col in self.xgb_features:
            X[col] = row_df[col] if col in row_df.columns else np.nan
        return float(self.xgb_model.predict(X.values)[0])

    def _xgb_predict_batch(self, df_segment):
        X = pd.DataFrame(index=df_segment.index)
        for col in self.xgb_features:
            X[col] = df_segment[col] if col in df_segment.columns else np.nan
        return self.xgb_model.predict(X.values)

    # ── SHAP 值计算 ──
    def _compute_shap(self, row_df):
        X = pd.DataFrame(index=[0])
        for col in self.xgb_features:
            X[col] = float(row_df[col].iloc[0]) if col in row_df.columns else 0.0
        sv = self.xgb_explainer.shap_values(X)
        shap_vals = sv[0] if isinstance(sv, list) else sv[0]
        pairs = list(zip(self.xgb_features, shap_vals))
        pairs.sort(key=lambda p: abs(p[1]), reverse=True)
        top = pairs[:5]
        result = []
        for name, sv_val in top:
            raw_val = float(X[name].iloc[0])
            result.append({
                "name": name,
                "shap_value": round(float(sv_val), 6),
                "value": round(raw_val, 4),
                "category": _classify_factor(name),
            })
        return result

    # ── Stacking 推理 ──
    def _stacking_predict(self, market_state, lstm_impl_return, xgb_risk):
        x = np.array([*market_state, lstm_impl_return, xgb_risk]).reshape(1, -1)
        pred_pct = float(self.ridge.predict(self.ridge_scaler.transform(x))[0])
        zone = (
            "高风险" if pred_pct <= self.high_thresh
            else "低风险" if pred_pct >= self.low_thresh
            else "中风险"
        )
        return pred_pct, zone

    # ═══════════════════════════════════════
    # 公共 API
    # ═══════════════════════════════════════

    def predict_daily(self):
        """读取 CSV 最新数据，调用三个模型，返回完整预测结果。"""
        df_raw = self.df_raw
        df_feat = self.df_feat

        # LSTM
        loc = len(df_feat) - 1
        current_price = float(df_feat["price"].iloc[-1])
        lstm_pred_price, lstm_up_prob = self._lstm_predict_single(df_feat, loc)
        lstm_impl_return = (lstm_pred_price - current_price) / current_price
        lstm_direction = "上涨" if lstm_up_prob >= 0.5 else "下跌"

        # XGBoost
        xgb_risk_score = self._xgb_predict(df_raw.iloc[[-1]])

        # SHAP
        top_factors = self._compute_shap(df_raw.iloc[[-1]])

        # Stacking
        market_state = df_raw[MARKET_STATE_COLS].iloc[-1].fillna(0).values.astype(float)
        pred_return_pct, risk_zone = self._stacking_predict(
            market_state, lstm_impl_return, xgb_risk_score
        )

        # 风险分数
        risk_score = 50 - (pred_return_pct * 10)
        risk_score = max(0, min(100, risk_score))
        level = "High" if risk_score >= 70 else "Low" if risk_score < 40 else "Medium"

        last_date = str(df_feat.index[-1].date())

        return {
            "dashboard": {
                "score": round(risk_score, 2),
                "level": level,
                "date": last_date,
            },
            "expert_signals": {
                "lstm_pred_price": round(lstm_pred_price, 2),
                "lstm_up_prob": round(lstm_up_prob, 4),
                "lstm_direction": lstm_direction,
                "xgb_risk_score": round(xgb_risk_score, 6),
            },
            "top_factors": top_factors,
            "prediction": {
                "predicted_return_pct": round(pred_return_pct, 3),
                "risk_zone": risk_zone,
            },
        }

    def predict_backtest(self, start_date: str, end_date: str, model: str):
        """
        对 [start_date, end_date] 区间做回测。
        model: "XGBoost" | "LSTM" | "Stacking"
        """
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        df_raw = self.df_raw
        df_feat = self.df_feat

        mask = (df_raw.index >= start) & (df_raw.index <= end)
        seg_raw = df_raw.loc[mask]
        if seg_raw.empty:
            return {"error": "No data in given date range"}

        seg_feat = df_feat.loc[df_feat.index.isin(seg_raw.index)]

        dates_out = []
        actual_out = []
        predicted_out = []

        if model == "XGBoost":
            # XGBoost 预测 risk（下跌风险），转换为价格预测
            xgb_preds = self._xgb_predict_batch(seg_raw)
            for i, (date, row) in enumerate(seg_raw.iterrows()):
                price = float(row[TARGET_COL])
                # risk = max(0, -next_return)，所以 predicted_next_price ≈ price * (1 - risk)
                pred_price = price * (1 - xgb_preds[i])
                dates_out.append(str(date.date()))
                actual_out.append(round(price, 2))
                predicted_out.append(round(pred_price, 2))

        elif model == "LSTM":
            feat_all_idx = df_feat.index
            for date in seg_feat.index:
                loc = feat_all_idx.get_loc(date)
                current_price = float(df_feat["price"].iloc[loc])
                pred_price, _ = self._lstm_predict_single(df_feat, loc)
                dates_out.append(str(date.date()))
                actual_out.append(round(current_price, 2))
                predicted_out.append(round(pred_price, 2))

        elif model == "Stacking":
            feat_all_idx = df_feat.index
            xgb_preds = self._xgb_predict_batch(seg_raw)
            seg_raw_dates = list(seg_raw.index)
            for i, date in enumerate(seg_raw.index):
                price = float(seg_raw.loc[date, TARGET_COL])
                if date in feat_all_idx:
                    loc = feat_all_idx.get_loc(date)
                    lstm_pred, _ = self._lstm_predict_single(df_feat, loc)
                    impl_ret = (lstm_pred - price) / (price + 1e-8)
                else:
                    impl_ret = 0.0
                market_state = seg_raw[MARKET_STATE_COLS].loc[date].fillna(0).values.astype(float)
                pred_pct, _ = self._stacking_predict(market_state, impl_ret, xgb_preds[i])
                pred_price = price * (1 + pred_pct / 100)
                dates_out.append(str(date.date()))
                actual_out.append(round(price, 2))
                predicted_out.append(round(pred_price, 2))
        else:
            return {"error": f"Unknown model: {model}"}

        # 计算指标
        act_arr = np.array(actual_out)
        pred_arr = np.array(predicted_out)
        n = len(act_arr)

        mae = float(np.mean(np.abs(act_arr - pred_arr)))

        # 方向准确率
        if n > 1:
            actual_dir = np.diff(act_arr)
            pred_dir = np.diff(pred_arr)
            dir_match = np.sum((actual_dir >= 0) == (pred_dir >= 0))
            direction_accuracy = float(dir_match / (n - 1))
        else:
            direction_accuracy = 0.0

        # 命中率（预测值与实际值偏差 < 5% 视为命中）
        pct_error = np.abs(act_arr - pred_arr) / (act_arr + 1e-8)
        hit_count = int(np.sum(pct_error < 0.05))
        hit_rate = float(hit_count / n)

        return {
            "dates": dates_out,
            "actual": [float(x) for x in actual_out],
            "predicted": [float(x) for x in predicted_out],
            "mae": float(round(mae, 2)),
            "hitRate": float(round(hit_rate, 4)),
            "directionAccuracy": float(round(direction_accuracy, 4)),
        }
