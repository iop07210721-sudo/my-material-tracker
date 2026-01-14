import yfinance as yf
import pandas as pd
from datetime import datetime

# 定義我們要追蹤的國際物料代碼 (Yahoo Finance 代碼)
# GC=F: 黃金期貨, CL=F: 原油期貨, HG=F: 銅期貨, SI=F: 白銀
COMMODITIES = {
    'Gold (黃金)': 'GC=F',
    'Crude Oil (原油)': 'CL=F',
    'Copper (銅)': 'HG=F',
    'Silver (白銀)': 'SI=F'
}

def get_trend_emoji(change):
    if change > 0:
        return "🔺"
    elif change < 0:
        return "🔻"
    return "➖"

def fetch_material_data():
    print(f"--- 國際物料趨勢報告: {datetime.now().strftime('%Y-%m-%d')} ---")
    
    results = []
    
    for name, ticker in COMMODITIES.items():
        try:
            # 抓取過去 5 天的資料以計算短期趨勢
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="5d")
            
            if len(hist) < 2:
                continue

            # 取得最新價格與前一日收盤價
            latest_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            
            # 計算漲跌幅
            change = latest_price - prev_close
            change_percent = (change / prev_close) * 100
            
            trend = get_trend_emoji(change)
            
            print(f"{trend} {name}: {latest_price:.2f} (變動: {change_percent:.2f}%)")
            
            results.append({
                "Material": name,
                "Price": latest_price,
                "Change%": change_percent
            })
            
        except Exception as e:
            print(f"❌ 無法抓取 {name}: {e}")

    return results

if __name__ == "__main__":
    fetch_material_data()
    # 未來擴充：這裡可以加入程式碼將 results 存成 CSV 或發送 Line 通知