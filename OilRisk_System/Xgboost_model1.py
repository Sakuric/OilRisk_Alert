# =========================================================
# 冲击专家模型 —— XGBoost 非线性冲击预测
# =========================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib

from sklearn.model_selection import TimeSeriesSplit
from scipy.stats import spearmanr
from xgboost import XGBRegressor

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# =========================================================
# 1. 读取数据
# =========================================================

df = pd.read_csv("Final_Oil_Dataset_Cleaned.csv")

date_col = [c for c in df.columns if "date" in c.lower()][0]
df[date_col] = pd.to_datetime(df[date_col])
df = df.sort_values(date_col).reset_index(drop=True)

print("数据形状:", df.shape)

# =========================================================
# 2. 使用 WTI 收盘价构造“冲击风险目标”
# =========================================================

wti_candidates = [
    c for c in df.columns
    if "wti" in c.lower()
    and any(k in c for k in ["收盘", "close", "结算"])
    and not any(k in c.lower() for k in ["volume", "成交", "持仓"])
]

print("WTI 候选列:", wti_candidates)

if len(wti_candidates) == 0:
    raise ValueError("未识别到 WTI 收盘价列，请检查列名")

wti_col = wti_candidates[0]
print("使用 WTI 收盘价列:", wti_col)

df["next_return"] = df[wti_col].shift(-1) / df[wti_col] - 1

df["risk"] = (-df["next_return"]).clip(lower=0)

df = df.dropna(subset=["risk"]).reset_index(drop=True)

print("risk(下跌风险强度) 非零比例:", (df["risk"] > 0).mean())
print("risk 分位数:",
      "p50", df["risk"].quantile(0.5),
      "p90", df["risk"].quantile(0.9),
      "p95", df["risk"].quantile(0.95),
      "p99", df["risk"].quantile(0.99))

# =========================================================
# 3. 特征
# =========================================================

X_all = df.select_dtypes(include=[np.number]).copy()

drop_cols = [wti_col, "next_return", "risk"]
X_all = X_all.drop(
    columns=[c for c in drop_cols if c in X_all.columns],
    errors="ignore"
)

shock_keywords = [
    "ovx", "vix", "hy", "spread", "credit",
    "risk", "panic", "stress",
    "sentiment", "news", "gpr",
    "diff", "delta", "change", "return", "vol"
]

shock_cols = [
    c for c in X_all.columns
    if any(k in c.lower() for k in shock_keywords)
]

print(f"冲击相关特征数: {len(shock_cols)}")

X = X_all[shock_cols].copy()
y = df["risk"]

print("可用数值特征数:", X.shape[1])

# =========================================================
# 4. 时间序列交叉验证
# =========================================================

tscv = TimeSeriesSplit(n_splits=5)
oof_pred = np.zeros(len(y))

print("\n开始时间序列交叉验证...")

for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model = XGBRegressor(
        n_estimators=600,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        min_child_weight=5,
        objective="reg:squarederror",
        tree_method="hist",
        random_state=42
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_val)
    oof_pred[val_idx] = preds

    # 排序能力评估

    sp = spearmanr(preds, y_val).correlation

    shock_threshold = 0.02  # ★ 冲击性下跌阈值：2%
    top_k = max(1, int(0.1 * len(preds)))

    # 真实冲击事件
    event = (y_val.values >= shock_threshold).astype(int)

    top_idx = np.argsort(preds)[-top_k:]

    hit_rate = event[top_idx].mean()
    base_rate = event.mean()
    lift = hit_rate / base_rate if base_rate > 0 else np.nan

    print(
        f"Fold {fold} Spearman: {sp:.4f} | "
        f"Top10% 冲击命中率: {hit_rate:.3f} "
        f"(基准 {base_rate:.3f}, Lift {lift:.2f})"
    )

# =========================================================
# 5. 全样本训练最终模型
# =========================================================

final_model = XGBRegressor(
    n_estimators=600,
    max_depth=4,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    min_child_weight=5,
    objective="reg:squarederror",
    tree_method="hist",
    random_state=42
)

final_model.fit(X, y)
joblib.dump(final_model, "xgb_wti_shock_model.pkl")

print("\n模型已保存为 xgb_wti_shock_model.pkl")

# =========================================================
# 6. 特征重要性（Gain）
# =========================================================

booster = final_model.get_booster()
imp = booster.get_score(importance_type="gain")

imp_df = (
    pd.DataFrame({"feature": imp.keys(), "gain": imp.values()})
    .sort_values("gain", ascending=False)
)

plt.figure(figsize=(10, 6))
imp_df.head(20).sort_values("gain").plot(
    x="feature", y="gain", kind="barh", legend=False
)
plt.title("WTI 冲击专家 - 特征重要性（Gain Top20）")
plt.tight_layout()
plt.savefig("xgb_wti_feature_importance.png", dpi=200)
plt.show()

print("特征重要性图已保存为 xgb_wti_feature_importance.png")
print("\n===== WTI 冲击专家模型构建完成 =====")