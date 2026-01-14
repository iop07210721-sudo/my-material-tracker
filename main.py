import yfinance as yf
import pandas as pd
import requests
import os
import matplotlib
import matplotlib.pyplot as plt
import io
from datetime import datetime

# 設定 Matplotlib 在後台執行
matplotlib.use('Agg')

# === 設定中文字型 (關鍵修改) ===
# 告訴 matplotlib 優先使用 Noto Sans CJK TC (思源黑體繁體中文)
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
# 解決負號 '-' 顯示為方塊的問題
plt.rcParams['axes.unicode_minus'] = False

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
    color = 0x808080 

    if rsi < 30:
        signal = "🟢 強力買入 (超賣)"
        color = 0x00FF00
    elif rsi > 70:
        signal = "🔴 建議賣出 (超買)"
        color = 0xFF0000
    elif sma5 > sma20 and row['Open'] < sma20:
        signal = "🔵 黃金交叉 (轉多)"
        color = 0x0000FF
    elif sma5 < sma20 and row['Open'] > sma20:
        signal = "🟠 死亡交叉 (轉空)"
        color = 0xFFA500

    return signal, color

# === 畫圖函數 (修改為中文標籤) ===
def generate_chart(name, df):
    plt.figure(figsize=(10, 5))
    
    # 修改這裡：label 改成中文
    plt.plot(df.index, df['Close'], label='價格', color='black', alpha=0.5)
    
    # 修改這裡：label 改成中文
    plt.plot(df.index, df['SMA_20'], label='20日均線 (趨勢)', color='orange', linestyle='--')
    
    # 修改這裡：標題改成中文
    plt.title(f"{name} - 近6個月趨勢分析")
    
    plt.legend(loc='upper left') # 將圖例移到左上角，避免擋住線圖
    plt.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100) # 增加 dpi 讓文字更清晰
    buf.seek(0)
    plt.close()
    return buf

# === 發送通知 (含圖片) ===
def send_discord_msg(name, data, signal, color, image_buf):
    if not WEBHOOK_URL: return

    price = data['Close']
    rsi = data['RSI']
    
    description = f"""
    **現價:** ${price:.2f}
    **RSI:** {rsi:.1f}
    **分析:** {signal}
    """

    payload = {
        "username": "AI 分析師",
        "embeds": [{
            "title": f"📊 {name} 分析報告",
            "description": description,
            "color": color,
            "footer": {"text": f"更新時間: {datetime.now().strftime('%Y-%m-%d')}"}
        }]
    }

    files = {
        'file': ('chart.png', image_buf, 'image/png')
    }
    
    try:
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
    print("啟動中文圖表分析引擎...")
    for name, ticker in COMMODITIES.items():
        try:
            df = analyze_data(ticker)
            if df is None: continue
            latest = df.iloc[-1]
            signal, color = get_signal(latest)
            chart_img = generate_chart(name, df)
            send_discord_msg(name, latest, signal, color, chart_img)
        except Exception as e:
            print(f"❌ 處理 {name} 時發生錯誤: {e}")

if __name__ == "__main__":
    main()