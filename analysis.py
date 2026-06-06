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
        hist_1y = stock.history(period="1y")
        if len(hist_1y) < 200: return None
        
        current_price = hist_1y['Close'].iloc[-1]
        avg_1y = hist_1y['Close'].mean()
        avg_vol_20 = hist_1y['Volume'].rolling(window=20).mean().iloc[-1]
        current_vol = hist_1y['Volume'].iloc[-1]
        
        # 수정된 필터링: 거래량 65%, RSI 45로 완화
        if current_price < avg_1y * 0.95 or (current_vol / avg_vol_20) < 0.65: return None
        rsi = calculate_rsi(hist_1y['Close']).iloc[-1]
        if not (20 <= rsi <= 45): return None
        
        news = stock.news
        score = sum(1 for item in news[:5] if any(w in item['title'].lower() for w in ['growth', 'innovation', 'approval', 'partnership', 'beat']))
        score = min(score, 3)
        
        if score == 3: grade = "강력 매수"
        elif score >= 1: grade = "매수"
        else: grade = "중립"
        
        atr = (hist_1y['High'] - hist_1y['Low']).rolling(window=14).mean().iloc[-1]
        entry = min(current_price, hist_1y['Close'].rolling(window=20).mean().iloc[-1])
        
        return {
            'sector': stock.info.get('sector', 'N/A'), 'ticker': ticker, 
            'price': current_price, 'rsi': round(rsi, 1), 'vol': f"{(current_vol/avg_vol_20)*100:.0f}%",
            'grade': grade, 'entry': entry, 'tp': entry + (atr * 3), 'sl': entry - (atr * 1.5)
        }
    except: return None

def start_analysis():
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    sheet.clear()
    sheet.append_row(["섹터", "종목", "현재가", "RSI", "거래량강도", "매수등급", "매수가", "익절가", "손절가"])
    
    with open('nasdaq_list.txt', 'r') as f: tickers = f.read().split()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(analyze_smart_ticker, tickers))
    
    valid_results = [r for r in results if r is not None]
    # '강력 매수' 우선 정렬
    valid_results.sort(key=lambda x: (x['grade'] == '강력 매수', x['grade'] == '매수'), reverse=True)
    final_list = valid_results[:15]
    
    for c in final_list:
        sheet.append_row([c['sector'], c['ticker'], f"${c['price']:.2f}", c['rsi'], c['vol'], 
                          c['grade'], f"${c['entry']:.2f}", f"${c['tp']:.2f}", f"${c['sl']:.2f}"])

if __name__ == "__main__":
    start_analysis()
