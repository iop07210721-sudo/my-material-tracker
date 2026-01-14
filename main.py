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
from pandas.plotting import register_matplotlib_converters

# 1. 強制註冊轉換器 (解決 Pandas 與 Matplotlib 的溝通問題)
register_matplotlib_converters()

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

# === 核心：日期強力清洗函數 (V4.2 新增) ===
def clean_date(dt_input):
    """將任何日期格式強制轉換為無時區的 Python datetime"""
    # 先轉成 Pandas Timestamp，再轉成 Python datetime，最後移除時區
    return pd.to_datetime(dt_input).to_pydatetime().replace(tzinfo=None)

# === AI 預測核心函數 ===
def predict_future_trend(df):
    # 準備數據
    df = df.reset_index()
    
    # 建立數值化的日期 (0, 1, 2...)
    df['Date_Num'] = df.index
    X = df[['Date_Num']].values
    y = df['Close'].values

    # 建立模型 (3次多項式)
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
    # 這裡也要確保 last_date 是乾淨的
    last_date = clean_date(df['Date'].iloc[-1] if 'Date' in df.columns else df.index[-1])
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
    
    # 🔥🔥🔥 V4.2 修正：暴力清洗 Index 日期 🔥🔥🔥
    # 使用 map 強制對每一個日期執行清洗，不依賴 pandas 版本
    df.index = df.index.map(clean_date)
    
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
    
    # 🔥🔥🔥 確保 future_dates 也是乾淨的 (雙重保險) 🔥🔥🔥
    future_dates = [clean_date(d) for d in future_dates]

    # 畫圖
    plt.plot(df.index, df['Close'], label='歷史價格', color='black', alpha=0.6)
    plt.plot(future_dates, future_prices, label='AI 預測走勢', color='red', linestyle='--', linewidth=2)
    
    # 轉換日期字串回 datetime 以便畫點
    buy_dt = datetime.strptime(prediction_info['buy_date'], '%Y-%m-%d')
    sell_dt = datetime.strptime(prediction_info['sell_date'], '%Y-%m-%d')
    
    plt.scatter(buy_dt, prediction_info['buy_price'], color='green', s=100, zorder=5, label='建議買點')
    plt.scatter(sell_dt, prediction_info['sell_price'], color='red', s=100, zorder=5, label='建議賣點')

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
    # 字型設定
    try:
        font_path = 'NotoSansTC-Regular.otf'
        fm.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = ['Noto Sans CJK TC']
    except Exception:
        print("⚠️ 無法載入中文字型，將使用預設字型")

    plt.rcParams['axes.unicode_minus'] = False 

    print("啟動 AI 預測引擎 (V4.2 終極修復版)...")
    
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
            # 印出更多錯誤細節幫助除錯
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()