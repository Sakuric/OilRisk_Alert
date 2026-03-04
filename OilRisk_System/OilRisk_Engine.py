# =================================================================
# OilRisk-Alert 终极集成引擎 (终极形态：完美契合队友原生接口)
# =================================================================
import joblib
import torch
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# 导入队友完美的原生接口
from LSTM import LSTMTrendExpert, predict_latest, load_and_engineer, CFG
from stacking最终 import predict_one_step

class OilRiskSystem:
    def __init__(self):
        print("⚙️ 正在启动 OilRisk-Alert 多源专家分诊系统...")
        self.lstm_feat_cols = joblib.load('feature_cols.pkl')
        self.price_scaler = joblib.load('price_scaler.pkl')
        self.feat_scaler = joblib.load('feat_scaler.pkl')
        
        # 强制用 CPU
        self.device = torch.device('cpu')
        self.lstm_model = LSTMTrendExpert(len(self.lstm_feat_cols), CFG['lstm_units'], CFG['dropout_rate'])
        self.lstm_model.load_state_dict(torch.load('best_lstm.pt', map_location=self.device))
        self.lstm_model.eval()
        
        self.xgb_model = joblib.load('xgb_wti_shock_model.pkl')
        print("✅ 系统初始化完成，随时可以开始预测！")

    def predict_today(self, df_raw):
        # ==========================================
        # 1. 调用 LSTM (使用队友的原生参数名)
        # ==========================================
        feat_df = load_and_engineer(CFG) 
        lstm_res = predict_latest(
            feat=feat_df, 
            feature_cols=self.lstm_feat_cols, 
            lookback=CFG['lookback'],
            price_scaler=self.price_scaler, 
            feat_scaler=self.feat_scaler, 
            model=self.lstm_model, 
            use_torch=True,       # <--- 队友真正的参数名！
            device=self.device    # <--- 告诉它在 CPU 上跑
        )
        
        current_price = feat_df['price'].iloc[-1]
        # 使用队友返回的字典键名 'lstm_pred_price'
        lstm_impl_return = (lstm_res['lstm_pred_price'] - current_price) / current_price
        
        # ==========================================
        # 2. 调用 XGBoost
        # ==========================================
        if hasattr(self.xgb_model, 'feature_names_in_'):
            xgb_features = self.xgb_model.feature_names_in_
        else:
            xgb_features = self.xgb_model.get_booster().feature_names
            
        xgb_input = df_raw[xgb_features].iloc[-1:]
        xgb_risk_score = float(self.xgb_model.predict(xgb_input)[0])
        
        gain_importance = self.xgb_model.get_booster().get_score(importance_type="gain")
        top_factors = sorted([{"name": k, "value": v} for k, v in gain_importance.items()], 
                             key=lambda x: x['value'], reverse=True)[:5]
        
        # ==========================================
        # 3. 调用 Stacking
        # ==========================================
        market_state_cols = [
            "Risk_VIX_VIX恐慌指数_VIX_Index", "Risk_VIX_情绪组_OVX__Value",
            "Macro_Yield_美债10年收益率_US_10Y_Treasury_Yield", "美元指数_日频",
            "Risk_Sentiment_新闻情感指数__News_Sentiment", "Risk_Geopolitics_地缘政治事件综合评分",
            "Macro_SP500_标普500指数_SP500_Close"
        ]
        market_state = df_raw[market_state_cols].iloc[-1].fillna(0).values.astype(float)
        
        final_result = predict_one_step(
            market_state=market_state,
            lstm_impl_return=lstm_impl_return,
            xgb_risk=xgb_risk_score
        )
        
        # ==========================================
        # 4. 生成 JSON
        # ==========================================
        risk_score = 50 - (final_result['pred_return_pct'] * 10)
        risk_score = max(0, min(100, risk_score)) 
        
        return {
            "status": "success",
            "dashboard": {
                "score": round(risk_score, 2),
                "level": final_result['risk_zone'] 
            },
            "expert_signals": {
                "lstm_impl_return": f"{lstm_impl_return*100:.2f}%",
                "lstm_direction": lstm_res['lstm_direction'], # <--- 队友返回的涨跌方向
                "xgb_risk_score": round(xgb_risk_score, 4)
            },
            "top_factors": top_factors,
            "prediction": {
                "predicted_return_pct": final_result['pred_return_pct']
            }
        }

if __name__ == "__main__":
    engine = OilRiskSystem()
    df = pd.read_csv('Final_Oil_Dataset_Cleaned.csv', encoding='utf-8-sig')
    date_col = [c for c in df.columns if "date" in c.lower()][0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).set_index(date_col)
    df = df.ffill().bfill() 
    
    today_json = engine.predict_today(df)
    
    import json
    print("\n🎉 "*10)
    print("📦 后端接口 JSON 响应成功！")
    print("🎉 "*10)
    print(json.dumps(today_json, indent=4, ensure_ascii=False))