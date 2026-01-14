import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# 設定 Matplotlib 在後台執行
matplotlib.use('Agg')

# === 參數設定 ===
COMMODITIES = {
    'Gold (黃金)': 'GC=F',
    'Crude Oil (原油)': 'CL=F',
    'Copper (銅)': 'HG=F',
    'Silver (白銀)': 'SI=F'
}
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
PREDICT_DAYS = 30 

# === AI 預測核心函數 ===
def predict_future_trend(df):
    # 準備數據
    df = df.reset_index()
    # 確保抓到正確的日期欄位名稱 (有些版本是 Date, 有些是 index)
    date_col = 'Date' if 'Date' in df.columns else 'index'
    
    df['Date_Num'] = df.index
    X = df[['Date_Num']].values
    y = df['Close'].values

    # 建立模型 (3次多項式回歸)
    poly = PolynomialFeatures(degree=3)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)

    # 產生未來數據
    last_index = df['Date_Num'].iloc[-1]
    future_indexes = np.arange(last_index + 1, last_index + 1 + PREDICT_DAYS).reshape(-1, 1)
    future_poly = poly.transform(future_indexes)
    future_prices = model.predict(future_poly)
    
    # 整理日期 (基於最後一天往後推)
    last_date = df[date_col].iloc[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, PREDICT_DAYS + 1)]
    
    return future_dates, future_prices

def find_best_timing(dates, prices):
    min_idx = np.argmin(prices)
    max_idx = np.argmax(prices)
    
    return {
        "buy_date": dates[min_idx].strftime('%Y-%m-%d'),
        "buy_price": np.min(prices),
        "sell_date": dates[max_idx].strftime('%Y-%m-%d'),
        "sell_price": np.max(prices)
    }

# === 基礎數據函數 ===
def analyze_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y") 
    if len(df) < 50: return None
    
    # 🔥🔥🔥 關鍵修正：強制移除時區資訊，解決 Matplotlib 報錯 🔥🔥🔥
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # 計算 RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

# === 畫圖函數 ===
def generate_chart(name, df, future_dates, future_prices, prediction_info):
    plt.figure(figsize=(10, 6))
    
    # 畫圖
    plt.plot(df.index, df['Close'], label='歷史價格', color='black', alpha=0.6)
    plt.plot(future_dates, future_prices, label='AI 預測走勢', color='red', linestyle='--', linewidth=2)
    
    # 標示點
    plt.scatter(prediction_info['buy_date'], prediction_info['buy_price'], color='green', s=100, zorder=5, label='建議買點')
    plt.scatter(prediction_info['sell_date'], prediction_info['sell_price'], color='red', s=100, zorder=5, label='建議賣點')

    plt.title(f"{name} - AI 趨勢預測 (未來30天)")
    plt.legend(loc='upper left')
    plt.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    return buf

# === 發送通知 ===
def send_discord_msg(name, current_price, prediction, image_buf):
    if not WEBHOOK_URL: return

    trend_text = "⚖️ 震盪整理"
    if prediction['sell_price'] > current_price * 1.05:
        trend_text = "🚀 看漲 (Bullish)"
    elif prediction['buy_price'] < current_price * 0.95:
        trend_text = "📉 看跌 (Bearish)"

    description = f"""
    **現價:** ${current_price:.2f}
    **AI 趨勢分析:** {trend_text}
    
    🔮 **未來 30 天操作建議:**
    🟢 **最佳買點:** {prediction['buy_date']} (預估 ${prediction['buy_price']:.2f})
    🔴 **最佳賣點:** {prediction['sell_date']} (預估 ${prediction['sell_price']:.2f})
    """

    payload = {
        "username": "AI 未來預言家",
        "embeds": [{
            "title": f"📈 {name} 未來預測報告",
            "description": description,
            "color": 0x5865F2,
            "footer": {"text": "⚠️ 預測僅供學術研究，投資有賺有賠"}
        }]
    }
    
    files = {'file': ('chart.png', image_buf, 'image/png')}
    
    try:
        import json
        requests.post(WEBHOOK_URL, data={'payload_json': json.dumps(payload)}, files=files)
        print(f"✅ {name} 預測報告已發送")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

# === 主程式 ===
def main():
    # 字型設定 (嘗試載入下載的字型檔)
    try:
        font_path = 'NotoSansTC-Regular.otf'
        fm.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = ['Noto Sans CJK TC']
    except Exception:
        print("⚠️ 無法載入中文字型，將使用預設字型")

    plt.rcParams['axes.unicode_minus'] = False # 解決負號

    print("啟動 AI 預測引擎 (V4.1)...")
    
    for name, ticker in COMMODITIES.items():
        try:
            df = analyze_data(ticker)
            if df is None: continue
            
            future_dates, future_prices = predict_future_trend(df)
            prediction_info = find_best_timing(future_dates, future_prices)
            chart_img = generate_chart(name, df, future_dates, future_prices, prediction_info)
            
            current_price = df['Close'].iloc[-1]
            send_discord_msg(name, current_price, prediction_info, chart_img)
            
        except Exception as e:
            print(f"❌ 預測 {name} 時發生錯誤: {e}")

if __name__ == "__main__":
    main()