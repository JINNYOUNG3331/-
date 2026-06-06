import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from concurrent.futures import ThreadPoolExecutor

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_smart_ticker(ticker):
    try:
        ticker = ticker.replace("^", "-").replace("/", "-")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        if len(hist) < 30: return None
        
        current_price = hist['Close'].iloc[-1]
        if current_price < 1.0: return None
        
        # [전략] 볼린저 밴드 하단 및 진입가 계산
        sma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        std20 = hist['Close'].rolling(window=20).std().iloc[-1]
        bollinger_lower = sma20 - (2 * std20)
        
        # 진입가: 볼린저 밴드 하단과 5일 이평선의 98% 중 큰 값
        entry = max(bollinger_lower, hist['Close'].rolling(window=5).mean().iloc[-1] * 0.98)
        
        atr = (hist['High'] - hist['Low']).rolling(window=14).mean().iloc[-1]
        tp = entry + (atr * 3)
        sl = entry - (atr * 1.5)
        
        # 퍼센트 계산
        tp_pct = ((tp - entry) / entry) * 100
        sl_pct = ((sl - entry) / entry) * 100
        
        # 필터링
        avg_6mo = hist['Close'].mean()
        if current_price < avg_6mo * 0.95: return None
        
        rsi = calculate_rsi(hist['Close']).iloc[-1]
        if not (20 <= rsi <= 45): return None
        
        news = stock.news
        score = sum(1 for item in news[:5] if any(w in item['title'].lower() for w in ['growth', 'innovation', 'approval', 'partnership', 'beat', 'earnings']))
        grade = "강력 매수" if score >= 3 else ("매수" if score >= 1 else "중립")
        
        return {
            'sector': stock.info.get('sector', 'N/A'), 'ticker': ticker, 
            'price': current_price, 'rsi': round(rsi, 1), 
            'grade': grade, 'entry': entry, 
            'tp': tp, 'tp_pct': tp_pct, 
            'sl': sl, 'sl_pct': sl_pct
        }
    except: return None

def start_analysis():
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    
    # 헤더 8개로 정확히 고정
    sheet.clear()
    sheet.append_row(["섹터", "종목", "현재가", "RSI", "매수등급", "매수가", "익절가", "손절가"])
    
    with open('nasdaq_list.txt', 'r') as f: tickers = f.read().split()
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(analyze_smart_ticker, tickers))
    
    valid_results = [r for r in results if r is not None]
    valid_results.sort(key=lambda x: (x['grade'] == '강력 매수', x['grade'] == '매수'), reverse=True)
    
    # 데이터 매칭 8개 유지
    for c in valid_results[:15]:
        sheet.append_row([
            c['sector'], 
            c['ticker'], 
            f"${c['price']:.2f}", 
            c['rsi'], 
            c['grade'], 
            f"${c['entry']:.2f}", 
            f"${c['tp']:.2f} ({c['tp_pct']:.1f}%)", 
            f"${c['sl']:.2f} ({c['sl_pct']:.1f}%)"
        ])

if __name__ == "__main__":
    start_analysis()
