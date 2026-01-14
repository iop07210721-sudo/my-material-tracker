import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# 定義物料代碼
COMMODITIES = {
    'Gold (黃金)': 'GC=F',
    'Crude Oil (原油)': 'CL=F',
    'Copper (銅)': 'HG=F',
    'Silver (白銀)': 'SI=F'
}

def get_trend_emoji(change):
    if change > 0: return "🔺"
    elif change < 0: return "🔻"
    return "➖"

def send_discord_notification(message):
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        print("⚠️ 未設定 Discord Webhook，跳過通知")
        return

    data = {
        "content": message,
        "username": "物料趨勢機器人",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2534/2534204.png" # 金幣圖示
    }
    
    try:
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            print("✅ Discord 通知發送成功")
        else:
            print(f"❌ Discord 通知失敗: {response.status_code}")
    except Exception as e:
        print(f"❌ 發送錯誤: {e}")

def fetch_and_notify():
    # 準備通知標題
    date_str = datetime.now().strftime('%Y-%m-%d')
    report_msg = f"**📊 國際物料趨勢報告 - {date_str}**\n--------------------------------\n"
    
    results = []
    
    for name, ticker in COMMODITIES.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="5d")
            
            if len(hist) < 2: continue

            latest = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = latest - prev
            change_pct = (change / prev) * 100
            trend = get_trend_emoji(change)
            
            # 格式化每一行訊息
            line = f"{trend} **{name}**: {latest:.2f} (變動: {change_pct:.2f}%)\n"
            print(line.strip()) # 印在 Log
            report_msg += line  # 加入通知訊息
            
        except Exception as e:
            print(f"❌ {name} 資料抓取失敗")

    # 加入結尾
    report_msg += "--------------------------------\n*資料來源: Yahoo Finance*"
    
    # 發送通知
    send_discord_notification(report_msg)

if __name__ == "__main__":
    fetch_and_notify()