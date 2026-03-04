"""
================================================================
花旗杯 - 原油价格预测系统
第一层：趋势专家（LSTM 深度学习模型）v4
================================================================

架构说明：
  本模型为双专家系统的第一层"趋势专家"，负责捕捉中长期
  价格趋势，输出预测价格与上涨概率供元学习器融合。

特征体系（27列）：
  - price            : WTI价格自身（感知当前价格水平）
  - crb/sp500/tips/hy/vix/ovx/cushing : 日频金融特征
  - opec/saudi/russia/cn_pmi/eu_pmi/us_sentiment _chg : 月频变化量
  - ma5/ma20/ma60/dev_ma5/dev_ma20/dev_ma60 : 均线技术指标
  - mom5/mom20/hvol20/cushing_chg5 : 动量与波动率
  - mom_accel/vix_chg3/ovx_chg3   : 方向性特征

输出（供元学习器使用）：
  - lstm_pred_price : 5日后WTI预测收盘价（美元/桶）
  - lstm_up_prob    : 5日后上涨概率（0~1）
  - lstm_direction  : 趋势判断文字

改动历史：
  v1 → v2 : 日频建模、RobustScaler、Huber Loss、月频变化率
  v2 → v3 : 加入price特征、方向性特征、修复维度bug、修复字体警告
  v3 → v4 : 【核心修复】分类权重从1.0恢复为0.5（v3的1.0导致BCE主导
             训练，val_loss从0.34飙升至0.89，模型27轮就早停且效果变差）；
             分类头独立于价格头（不共享最后一层，各自有独立隐层）；
             patience从25增加到30，给模型更多收敛时间
================================================================
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings, os, joblib

warnings.filterwarnings('ignore')

# ── 字体自动检测（兼容Linux/Windows/Mac）──
import matplotlib.font_manager as fm
_available_fonts = [f.name for f in fm.fontManager.ttflist]
_cjk_candidates  = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'DejaVu Sans']
_chosen_font     = next((f for f in _cjk_candidates if f in _available_fonts), 'DejaVu Sans')
matplotlib.rcParams['font.sans-serif'] = [_chosen_font]
matplotlib.rcParams['axes.unicode_minus'] = False

# ── 框架自动检测：优先TensorFlow，否则PyTorch ──
USE_TORCH = False
try:
    import tensorflow as tf
    from tensorflow.keras.models import Model, load_model
    from tensorflow.keras.layers import (Input, LSTM, Dense, Dropout,
                                          BatchNormalization, Bidirectional)
    from tensorflow.keras.callbacks import (EarlyStopping, ReduceLROnPlateau,
                                             ModelCheckpoint)
    from tensorflow.keras.optimizers import Adam
    print(f"✅ TensorFlow {tf.__version__}")
except ImportError:
    USE_TORCH = True
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    print(f"✅ PyTorch {torch.__version__}")

# ═══════════════════════════════════════════
# 0. 全局配置
# ═══════════════════════════════════════════
CFG = {
    # 这里要填对应路径
    'data_path':   r'Final_Oil_Dataset_Cleaned.csv',
    'output_dir':  r'./lstm_output',

    'target_col':  'Price_WTI_WTI期货_close',

    # 序列参数
    'lookback':    30,      # 过去30个交易日（约6周）
    'horizon':     5,       # 预测5个交易日后（约1周）

    # 模型结构
    'lstm_units':        [128, 64],
    'dropout_rate':      0.2,
    'use_bidirectional': False,

    # 训练参数
    'epochs':      200,
    'batch_size':  64,
    'lr':          5e-4,
    'patience':    30,          # v4: 25→30，给模型更多收敛时间

    # 损失权重（核心参数）
    # v4说明：分类权重0.5是经过实验验证的平衡点
    #   - 权重太低(0.1)：分类头退化，方向准确率≈50%（随机猜）
    #   - 权重太高(1.0)：BCE主导训练，val_loss飙升，模型早停，整体变差
    #   - 权重0.5：价格回归与方向分类均衡学习
    'cls_weight':  0.5,

    # 数据切分（严格按时间顺序，不打乱）
    'train_ratio': 0.70,
    'val_ratio':   0.15,

    'seed': 42,
}

np.random.seed(CFG['seed'])
if USE_TORCH:
    torch.manual_seed(CFG['seed'])
os.makedirs(CFG['output_dir'], exist_ok=True)

# ═══════════════════════════════════════════
# 1. 列名映射
# ═══════════════════════════════════════════
COLS = {
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
}

# ═══════════════════════════════════════════
# 2. 数据加载与特征工程
# ═══════════════════════════════════════════
def load_and_engineer(cfg: dict) -> pd.DataFrame:
    print("\n" + "="*60)
    print("📂 加载数据...")
    df = pd.read_csv(cfg['data_path'], encoding='utf-8-sig')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').set_index('Date')

    target = COLS['target']
    df = df[df[target].notna()].copy()
    print(f"有效日期段: {df.index.min().date()} ~ {df.index.max().date()}，"
          f"共 {len(df)} 个交易日")

    feat  = pd.DataFrame(index=df.index)
    price = df[target]

    # A. 价格自身
    feat['price'] = price

    # B. 日频金融特征
    for k in ['crb', 'sp500', 'tips', 'hy', 'vix', 'ovx', 'cushing']:
        col = COLS[k]
        if col in df.columns:
            feat[k] = df[col]

    # C. 月频慢变量 → 月度变化量（消除趋势伪相关）
    for k in ['opec', 'saudi', 'russia', 'cn_pmi', 'eu_pmi', 'us_sentiment']:
        col = COLS[k]
        if col in df.columns:
            raw = df[col]
            monthly_chg = raw.resample('ME').last().diff()
            feat[f'{k}_chg'] = monthly_chg.reindex(df.index, method='ffill')

    # D. 技术指标
    feat['ma5']          = price.rolling(5).mean()
    feat['ma20']         = price.rolling(20).mean()
    feat['ma60']         = price.rolling(60).mean()
    feat['dev_ma5']      = (price - feat['ma5'])  / (feat['ma5']  + 1e-8)
    feat['dev_ma20']     = (price - feat['ma20']) / (feat['ma20'] + 1e-8)
    feat['dev_ma60']     = (price - feat['ma60']) / (feat['ma60'] + 1e-8)
    feat['mom5']         = np.log(price / price.shift(5).replace(0, np.nan))
    feat['mom20']        = np.log(price / price.shift(20).replace(0, np.nan))
    feat['hvol20']       = np.log(price / price.shift(1)).rolling(20).std()
    if 'cushing' in feat.columns:
        feat['cushing_chg5'] = feat['cushing'].diff(5)

    # E. 方向性特征
    feat['mom_accel'] = feat['mom5'] - feat['mom5'].shift(3)
    if 'vix' in feat.columns:
        feat['vix_chg3'] = feat['vix'].pct_change(3)
    if 'ovx' in feat.columns:
        feat['ovx_chg3'] = feat['ovx'].pct_change(3)

    # F. 标签
    feat['y_price'] = price.shift(-cfg['horizon'])
    feat['y_label'] = (feat['y_price'] > price).astype(int)

    feat = feat.dropna()
    n_feat = feat.shape[1] - 2
    print(f"特征工程完成，可用样本: {len(feat)} | 特征数: {n_feat}")
    return feat


# ═══════════════════════════════════════════
# 3. 构造 LSTM 序列
# ═══════════════════════════════════════════
def build_sequences(feat: pd.DataFrame, lookback: int):
    """
    price 列保留为特征（不排除），
    feat_scaler 的列数与 predict_latest 中保持完全一致。
    """
    exclude = {'y_price', 'y_label'}
    fc = [c for c in feat.columns if c not in exclude]

    X_raw       = feat[fc].values.astype(np.float32)
    y_price_raw = feat['y_price'].values.astype(np.float32)
    y_label     = feat['y_label'].values.astype(np.float32)

    feat_scaler  = RobustScaler()
    price_scaler = RobustScaler()

    X_s  = feat_scaler.fit_transform(X_raw)
    yp_s = price_scaler.fit_transform(
        y_price_raw.reshape(-1, 1)).flatten()

    X, yp, yl = [], [], []
    for i in range(lookback, len(X_s)):
        X.append(X_s[i - lookback: i])
        yp.append(yp_s[i])
        yl.append(y_label[i])

    return (np.array(X, dtype=np.float32),
            np.array(yp, dtype=np.float32),
            np.array(yl, dtype=np.float32),
            price_scaler, feat_scaler, fc)


# ═══════════════════════════════════════════
# 4. 模型定义
# ═══════════════════════════════════════════

# ── Keras 版本 ──
def build_keras_model(lookback, n_feat, units, dropout, bidir, cls_weight):
    inp = Input(shape=(lookback, n_feat))
    x   = inp
    for i, u in enumerate(units):
        ret = i < len(units) - 1
        lyr = LSTM(u, return_sequences=ret, dropout=dropout, recurrent_dropout=0.1)
        x   = Bidirectional(lyr)(x) if bidir else lyr(x)
        x   = BatchNormalization()(x)
    x = Dropout(dropout)(x)

    # v4: 价格头与分类头各自有独立隐层，避免争抢共享表示
    price_hidden = Dense(32, activation='relu')(x)
    p_out = Dense(1, activation='linear', name='price_output')(price_hidden)

    cls_hidden = Dense(16, activation='relu')(x)
    b_out = Dense(1, activation='sigmoid', name='prob_output')(cls_hidden)

    m = Model(inp, [p_out, b_out])
    m.compile(
        Adam(CFG['lr']),
        loss={'price_output': 'huber', 'prob_output': 'binary_crossentropy'},
        loss_weights={'price_output': 1.0, 'prob_output': cls_weight}
    )
    return m


# ── PyTorch 版本 ──
class LSTMTrendExpert(nn.Module):
    def __init__(self, n_feat, units, dropout, bidir=False):
        super().__init__()
        nd = 2 if bidir else 1
        self.lstms = nn.ModuleList()
        in_sz = n_feat
        for u in units:
            self.lstms.append(
                nn.LSTM(in_sz, u, batch_first=True, bidirectional=bidir))
            in_sz = u * nd
        self.bn   = nn.BatchNorm1d(in_sz)
        self.drop = nn.Dropout(dropout)

        # v4: 价格头与分类头独立隐层
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


# ═══════════════════════════════════════════
# 5. 训练
# ═══════════════════════════════════════════
def train_keras(model, X_tr, yp_tr, yl_tr, X_val, yp_val, yl_val, cfg):
    cbs = [
        EarlyStopping('val_loss', patience=cfg['patience'],
                      restore_best_weights=True, verbose=1),
        ReduceLROnPlateau('val_loss', factor=0.5, patience=10,
                          min_lr=1e-5, verbose=0),
        ModelCheckpoint(os.path.join(cfg['output_dir'], 'best_lstm.keras'),
                        'val_loss', save_best_only=True, verbose=0),
    ]
    return model.fit(
        X_tr, {'price_output': yp_tr, 'prob_output': yl_tr},
        validation_data=(X_val, {'price_output': yp_val, 'prob_output': yl_val}),
        epochs=cfg['epochs'], batch_size=cfg['batch_size'],
        callbacks=cbs, verbose=1)


def train_torch(model, X_tr, yp_tr, yl_tr, X_val, yp_val, yl_val, cfg):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model  = model.to(device)
    t = lambda a: torch.from_numpy(a).to(device)

    tr_ld  = DataLoader(TensorDataset(t(X_tr),  t(yp_tr),  t(yl_tr)),
                        cfg['batch_size'], shuffle=True, drop_last=True)
    val_ld = DataLoader(TensorDataset(t(X_val), t(yp_val), t(yl_val)),
                        cfg['batch_size'], shuffle=False)

    opt   = torch.optim.Adam(model.parameters(), lr=cfg['lr'])
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, factor=0.5, patience=10, min_lr=1e-5)
    huber = nn.HuberLoss()
    bce   = nn.BCELoss()
    cw    = cfg['cls_weight']

    best_val, wait = np.inf, 0
    history = {'train': [], 'val': []}

    for ep in range(cfg['epochs']):
        model.train(); tl = 0
        for Xb, yp, yl in tr_ld:
            opt.zero_grad()
            pp, pb = model(Xb)
            loss = huber(pp, yp) + cw * bce(pb, yl)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tl += loss.item()

        model.eval(); vl = 0
        with torch.no_grad():
            for Xb, yp, yl in val_ld:
                pp, pb = model(Xb)
                vl += (huber(pp, yp) + cw * bce(pb, yl)).item()

        tl /= len(tr_ld); vl /= max(len(val_ld), 1)
        sched.step(vl)
        history['train'].append(tl); history['val'].append(vl)

        if (ep + 1) % 20 == 0:
            print(f"  Epoch {ep+1:3d} | train={tl:.4f} | val={vl:.4f} | "
                  f"lr={opt.param_groups[0]['lr']:.1e}")

        if vl < best_val:
            best_val, wait = vl, 0
            torch.save(model.state_dict(),
                       os.path.join(cfg['output_dir'], 'best_lstm.pt'))
        else:
            wait += 1
            if wait >= cfg['patience']:
                print(f"  Early stopping @ epoch {ep+1}")
                break

    model.load_state_dict(
        torch.load(os.path.join(cfg['output_dir'], 'best_lstm.pt'),
                   map_location=device))
    return history, model, device


# ═══════════════════════════════════════════
# 6. 评估与可视化
# ═══════════════════════════════════════════
def evaluate(yp_s, pp_s, yl, pb, price_scaler, tag, cfg):
    inv = lambda s: price_scaler.inverse_transform(
        np.array(s).reshape(-1, 1)).flatten()
    yt, yp_inv = inv(yp_s), inv(pp_s)

    rmse = np.sqrt(mean_squared_error(yt, yp_inv))
    mae  = mean_absolute_error(yt, yp_inv)
    mape = np.mean(np.abs((yt - yp_inv) / (np.abs(yt) + 1e-8))) * 100
    acc  = np.mean((np.array(pb) >= 0.5).astype(int) == np.array(yl)) * 100

    print(f"\n{'='*52}")
    print(f"📊 [{tag}]  RMSE={rmse:.2f}$  MAE={mae:.2f}$  "
          f"MAPE={mape:.1f}%  方向准确率={acc:.1f}%")
    print(f"{'='*52}")

    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    ax = axes[0]
    ax.plot(yt,     label='True Price', lw=1.5, color='steelblue')
    ax.plot(yp_inv, label='LSTM Pred',  lw=1.5, color='tomato', ls='--')
    ax.set_title(f'Trend Expert LSTM [{tag}]  RMSE={rmse:.2f} | MAPE={mape:.1f}%',
                 fontsize=12, fontweight='bold')
    ax.set_ylabel('WTI (USD/bbl)'); ax.legend(); ax.grid(alpha=0.3)

    ax = axes[1]
    ax.plot(pb, color='darkorange', lw=1, label='Up Prob')
    ax.axhline(0.5, color='gray', ls='--', lw=0.8)
    up = np.where(np.array(yl) == 1)[0]
    dn = np.where(np.array(yl) == 0)[0]
    ax.scatter(up, [0.92]*len(up), s=6, color='green', alpha=0.4, label='Actual Up')
    ax.scatter(dn, [0.08]*len(dn), s=6, color='red',   alpha=0.4, label='Actual Down')
    ax.set_ylim(0, 1)
    ax.set_title(f'Direction Accuracy {acc:.1f}%', fontsize=11, fontweight='bold')
    ax.set_ylabel('P(Up)'); ax.legend(); ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(cfg['output_dir'], f'result_{tag.lower()}.png')
    plt.savefig(path, dpi=150); plt.close()
    print(f"📈 图表已保存: {path}")
    return dict(rmse=rmse, mae=mae, mape=mape, dir_acc=acc)


def plot_history(h, cfg, use_torch):
    fig, ax = plt.subplots(figsize=(9, 4))
    tr = h['train'] if use_torch else h.history['loss']
    va = h['val']   if use_torch else h.history['val_loss']
    ax.plot(tr, label='Train', color='steelblue')
    ax.plot(va, label='Val',   color='tomato')
    ax.set(title='Training Curve', xlabel='Epoch', ylabel='Loss')
    ax.legend(); ax.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(cfg['output_dir'], 'training_curve.png'), dpi=150)
    plt.close()
    print("📈 训练曲线已保存")


# ═══════════════════════════════════════════
# 7. 推理接口（供元学习器调用）
# ═══════════════════════════════════════════
def predict_latest(feat, feature_cols, lookback,
                   price_scaler, feat_scaler, model,
                   use_torch=False, device=None) -> dict:
    """
    取最新 lookback 日数据，输出下周预测结果。
    feature_cols 必须与 build_sequences 返回的 fc 完全一致
    （包含 price 列，只排除 y_price / y_label）。
    """
    exclude = {'y_price', 'y_label'}
    fc  = [c for c in feature_cols if c not in exclude]
    X_s = feat_scaler.transform(
        feat[fc].values[-lookback:].astype(np.float32)
    )[np.newaxis].astype(np.float32)

    if use_torch:
        model.eval()
        with torch.no_grad():
            Xt = torch.from_numpy(X_s).to(device)
            pp, pb = model(Xt)
            ps, up = float(pp.cpu()[0]), float(pb.cpu()[0])
    else:
        pp, pb = model.predict(X_s, verbose=0)
        ps, up = float(pp[0][0]), float(pb[0][0])

    pred_price = float(price_scaler.inverse_transform([[ps]])[0][0])
    return {
        'lstm_pred_price': pred_price,
        'lstm_up_prob':    up,
        'lstm_direction':  '上涨↑' if up >= 0.5 else '下跌↓',
    }


# ═══════════════════════════════════════════
# 8. 主程序
# ═══════════════════════════════════════════
def main():
    print("\n" + "🟡 "*18)
    print("       花旗杯 | 趋势专家（LSTM v4）")
    print("🟡 "*18)

    # Step 1: 特征工程
    feat = load_and_engineer(CFG)

    # Step 2: 构造序列
    print("\n📐 构造序列...")
    X, yp, yl, price_scaler, feat_scaler, fc = build_sequences(
        feat, CFG['lookback'])
    print(f"   序列: {len(X)} 条 | lookback={CFG['lookback']}日 | "
          f"features={X.shape[2]} | horizon={CFG['horizon']}日")
    print(f"   标签上涨占比: {yl.mean():.1%}")

    # Step 3: 时序切分（严格按时间顺序）
    N = len(X)
    tr_e  = int(N * CFG['train_ratio'])
    val_e = int(N * (CFG['train_ratio'] + CFG['val_ratio']))
    X_tr,  yp_tr,  yl_tr  = X[:tr_e],      yp[:tr_e],      yl[:tr_e]
    X_val, yp_val, yl_val = X[tr_e:val_e],  yp[tr_e:val_e], yl[tr_e:val_e]
    X_te,  yp_te,  yl_te  = X[val_e:],     yp[val_e:],     yl[val_e:]
    print(f"   Train={len(X_tr)} | Val={len(X_val)} | Test={len(X_te)}")

    # Step 4: 构建 & 训练
    print(f"\n🏗️  构建模型... (cls_weight={CFG['cls_weight']})")
    if not USE_TORCH:
        model = build_keras_model(CFG['lookback'], X.shape[2],
                                   CFG['lstm_units'], CFG['dropout_rate'],
                                   CFG['use_bidirectional'], CFG['cls_weight'])
        model.summary()
        print("\n🚀 开始训练...")
        hist = train_keras(model, X_tr, yp_tr, yl_tr,
                            X_val, yp_val, yl_val, CFG)
        plot_history(hist, CFG, False)

        def pred(Xa):
            pp, pb = model.predict(Xa, verbose=0)
            return pp.flatten(), pb.flatten()
    else:
        model = LSTMTrendExpert(X.shape[2], CFG['lstm_units'],
                                 CFG['dropout_rate'], CFG['use_bidirectional'])
        print(f"   参数量: {sum(p.numel() for p in model.parameters()):,}")
        print("\n🚀 开始训练...")
        hist, model, device = train_torch(
            model, X_tr, yp_tr, yl_tr, X_val, yp_val, yl_val, CFG)
        plot_history(hist, CFG, True)

        def pred(Xa):
            model.eval()
            with torch.no_grad():
                pp, pb = model(torch.from_numpy(Xa).to(device))
                return pp.cpu().numpy(), pb.cpu().numpy()

    # Step 5: 评估
    pp_val, pb_val = pred(X_val)
    evaluate(yp_val, pp_val, yl_val, pb_val, price_scaler, 'Val',  CFG)
    pp_te,  pb_te  = pred(X_te)
    evaluate(yp_te,  pp_te,  yl_te,  pb_te,  price_scaler, 'Test', CFG)

    # Step 6: 保存
    joblib.dump(price_scaler, os.path.join(CFG['output_dir'], 'price_scaler.pkl'))
    joblib.dump(feat_scaler,  os.path.join(CFG['output_dir'], 'feat_scaler.pkl'))
    joblib.dump(fc,           os.path.join(CFG['output_dir'], 'feature_cols.pkl'))
    print(f"\n💾 已保存至 {CFG['output_dir']}")

    # Step 7: 最新数据推理
    print("\n" + "─"*50)
    print("🔮 最新数据推理...")
    result = predict_latest(feat, fc, CFG['lookback'],
                             price_scaler, feat_scaler, model,
                             USE_TORCH, device if USE_TORCH else None)
    print(f"\n   数据截止: {feat.index[-1].date()}")
    print(f"   ┌────────────────────────────────────")
    print(f"   │ 预测价格  : {result['lstm_pred_price']:.2f} 美元/桶")
    print(f"   │ 上涨概率  : {result['lstm_up_prob']:.1%}")
    print(f"   │ 趋势判断  : {result['lstm_direction']}")
    print(f"   └────────────────────────────────────")
    print(f"\n✅ 完成！输出目录: {CFG['output_dir']}")

    return model, price_scaler, feat_scaler, fc, result, feat


# ═══════════════════════════════════════════
# 9. 元学习器调用示例（队友参考）
# ═══════════════════════════════════════════
"""
【队友调用方式】

from lstm_trend_expert import predict_latest, load_and_engineer, CFG
import joblib

feat         = load_and_engineer(CFG)
price_scaler = joblib.load('./lstm_output/price_scaler.pkl')
feat_scaler  = joblib.load('./lstm_output/feat_scaler.pkl')
feature_cols = joblib.load('./lstm_output/feature_cols.pkl')

# Keras 版本
from tensorflow.keras.models import load_model
model  = load_model('./lstm_output/best_lstm.keras')
result = predict_latest(feat, feature_cols, CFG['lookback'],
                         price_scaler, feat_scaler, model)

# PyTorch 版本
# import torch
# from lstm_trend_expert import LSTMTrendExpert
# model = LSTMTrendExpert(len(feature_cols), CFG['lstm_units'], CFG['dropout_rate'])
# model.load_state_dict(torch.load('./lstm_output/best_lstm.pt'))
# result = predict_latest(feat, feature_cols, CFG['lookback'],
#                          price_scaler, feat_scaler, model,
#                          use_torch=True, device=torch.device('cpu'))

# 传入元学习器的核心信号
lstm_up_prob    = result['lstm_up_prob']      # float 0~1
lstm_pred_price = result['lstm_pred_price']   # float，美元/桶
lstm_direction  = result['lstm_direction']    # '上涨↑' 或 '下跌↓'
"""

if __name__ == '__main__':
    main()