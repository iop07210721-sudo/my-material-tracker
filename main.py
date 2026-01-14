import yfinance as yf
import pandas as pd
import requests
import os
import matplotlib
import matplotlib.pyplot as plt
import io
from datetime import datetime

# 設定 Matplotlib 在後台執行 (重要！不然在 GitHub 上會報錯)
matplotlib.use('Agg')

# === 設定參數 ===
COMMODITIES = {
    'Gold (黃金)': 'GC=F',
    'Crude Oil (原油)': 'CL=F',
    'Copper (銅)': 'HG=F',
    'Silver (白銀)': 'SI=F'
}

WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# === 技術分析函數 ===
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="6mo")
    
    if len(df) < 50: return None

    df['RSI'] = calculate_rsi(df['Close'])
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    return df

def get_signal(row):
    rsi = row['RSI']
    sma5 = row['SMA_5']
    sma20 = row['SMA_20']
    
    signal = "⚖️ 觀望"
    color = 0x808080 # 灰色

    if rsi < 30:
        signal = "🟢 強力買入 (超賣)"
        color = 0x00FF00 # 綠色
    elif rsi > 70:
        signal = "🔴 建議賣出 (超買)"
        color = 0xFF0000 # 紅色
    elif sma5 > sma20 and row['Open'] < sma20:
        signal = "🔵 黃金交叉 (轉多)"
        color = 0x0000FF # 藍色
    elif sma5 < sma20 and row['Open'] > sma20:
        signal = "🟠 死亡交叉 (轉空)"
        color = 0xFFA500 # 橘色

    return signal, color

# === 畫圖函數 (核心新功能) ===
def generate_chart(name, df):
    # 設定畫布大小
    plt.figure(figsize=(10, 5))
    
    # 畫價格線
    plt.plot(df.index, df['Close'], label='Price', color='black', alpha=0.5)
    
    # 畫均線 (趨勢線)
    plt.plot(df.index, df['SMA_20'], label='SMA 20 (Trend)', color='orange', linestyle='--')
    
    plt.title(f"{name} - 6 Month Trend Analysis")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 將圖片存到記憶體中 (不存成檔案，比較快)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close() # 關閉畫布釋放記憶體
    return buf

# === 發送通知 (含圖片) ===
def send_discord_msg(name, data, signal, color, image_buf):
    if not WEBHOOK_URL: return

    price = data['Close']
    rsi = data['RSI']
    
    # 準備文字內容
    description = f"""
    **現價:** ${price:.2f}
    **RSI:** {rsi:.1f}
    **分析:** {signal}
    """

    # 準備 Payload
    payload = {
        "username": "AI 分析師",
        "embeds": [{
            "title": f"📊 {name} 分析報告",
            "description": description,
            "color": color,
            "footer": {"text": f"更新時間: {datetime.now().strftime('%Y-%m-%d')}"}
        }]
    }

    # 發送請求 (包含圖片檔案)
    files = {
        'file': ('chart.png', image_buf, 'image/png')
    }
    
    # 這裡有點小技巧：Discord 允許我們把圖片當附件，然後在 Payload 裡引用它
    # 但最簡單的方法是：文字歸文字，圖片歸圖片，一起傳過去
    
    try:
        # 由於 requests 傳檔案比較複雜，我們把 embed 轉成 json 字串傳送
        import json
        requests.post(
            WEBHOOK_URL, 
            data={'payload_json': json.dumps(payload)}, 
            files=files
        )
        print(f"✅ {name} 通知已發送")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

# === 主程式 ===
def main():
    print("啟動圖表分析引擎...")
    
    for name, ticker in COMMODITIES.items():
        try:
            df = analyze_data(ticker)
            if df is None: continue

            latest = df.iloc[-1]
            signal, color = get_signal(latest)
            
            # 產生圖表
            chart_img = generate_chart(name, df)
            
            # 發送 (包含圖片)
            send_discord_msg(name, latest, signal, color, chart_img)
            
        except Exception as e:
            print(f"❌ 處理 {name} 時發生錯誤: {e}")

if __name__ == "__main__":
    main()