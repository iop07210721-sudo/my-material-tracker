import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# === 設定參數 ===
COMMODITIES = {
    'Gold (黃金)': 'GC=F',
    'Crude Oil (原油)': 'CL=F',
    'Copper (銅)': 'HG=F',
    'Silver (白銀)': 'SI=F'
}

# 設定 Discord Webhook (會從 GitHub Secrets 讀取)
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# === 技術分析函數 ===
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_technicals(ticker):
    # 抓取 6 個月的資料以計算指標
    stock = yf.Ticker(ticker)
    df = stock.history(period="6mo")
    
    if len(df) < 50:
        return None  # 資料不足

    # 1. 計算 RSI (14天)
    df['RSI'] = calculate_rsi(df['Close'])

    # 2. 計算均線 (短線5日, 長線20日)
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()

    return df.iloc[-1]  # 回傳最新一筆資料

def get_signal(row):
    # === 買賣邏輯核心 ===
    rsi = row['RSI']
    price = row['Close']
    sma5 = row['SMA_5']
    sma20 = row['SMA_20']

    signal = "⚖️ 觀望 (Neutral)"
    reason = "趨勢不明顯"

    # 策略 1: RSI 超買超賣策略
    if rsi < 30:
        signal = "🟢 強力買入 (Buy)"
        reason = f"RSI過低({rsi:.1f})，市場超賣"
    elif rsi > 70:
        signal = "🔴 建議賣出 (Sell)"
        reason = f"RSI過高({rsi:.1f})，市場過熱"
    
    # 策略 2: 均線交叉策略 (如果是觀望狀態，才看均線)
    elif sma5 > sma20 and row['Open'] < sma20: # 簡化版黃金交叉邏輯
        signal = "🔵 趨勢轉多 (Bullish)"
        reason = "短線突破長線阻力"
    elif sma5 < sma20 and row['Open'] > sma20:
        signal = "🟠 趨勢轉空 (Bearish)"
        reason = "跌破長線支撐"

    return signal, reason

# === 發送通知 ===
def send_discord_report(results):
    if not WEBHOOK_URL:
        print("⚠️ 沒設定 Webhook，跳過發送")
        return

    # 製作漂亮的 Discord 訊息內容
    embed_content = "**🤖 國際物料 AI 趨勢分析系統**\n"
    embed_content += f"📅 日期: {datetime.now().strftime('%Y-%m-%d')}\n"
    embed_content += "----------------------------------\n"

    for item in results:
        embed_content += f"**{item['name']}** - 現價: ${item['price']:.2f}\n"
        embed_content += f"📊 信號: **{item['signal']}**\n"
        embed_content += f"💡 原因: {item['reason']}\n"
        embed_content += f"📈 技術: RSI={item['rsi']:.1f} | MA5={item['sma5']:.1f}\n"
        embed_content += "----------------------------------\n"

    embed_content += "*⚠️ 免責聲明: 此為程式自動運算結果，僅供學術參考，非投資建議。*"

    data = {
        "content": embed_content,
        "username": "AI 分析師",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/4202/4202831.png"
    }
    requests.post(WEBHOOK_URL, json=data)

# === 主程式 ===
def main():
    analysis_results = []
    print("正在啟動 AI 分析...")

    for name, ticker in COMMODITIES.items():
        try:
            print(f"分析中: {name}...")
            latest_data = analyze_technicals(ticker)
            
            if latest_data is None:
                continue

            signal, reason = get_signal(latest_data)
            
            analysis_results.append({
                "name": name,
                "price": latest_data['Close'],
                "rsi": latest_data['RSI'],
                "sma5": latest_data['SMA_5'],
                "signal": signal,
                "reason": reason
            })
            
        except Exception as e:
            print(f"❌ 分析 {name} 時發生錯誤: {e}")

    if analysis_results:
        send_discord_report(analysis_results)
        print("✅ 分析報告已發送至 Discord")
    else:
        print("⚠️ 沒有產生任何分析結果")

if __name__ == "__main__":
    main()