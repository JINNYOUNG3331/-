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
        
        # 1년 데이터 확보 (매물대 및 장기 추세 확인)
        hist_1y = stock.history(period="1y")
        if len(hist_1y) < 200: return None
        
        current_price = hist_1y['Close'].iloc[-1]
        avg_1y = hist_1y['Close'].mean()
        # 20일 평균 거래량
        avg_vol_20 = hist_1y['Volume'].rolling(window=20).mean().iloc[-1]
        current_vol = hist_1y['Volume'].iloc[-1]
        
        # [필터 1] 매물대: 1년 평균가 95% 이상 위치 (지하실 종목 컷)
        if current_price < avg_1y * 0.95: return None
        
        # [필터 2] 거래량: 20일 평균 대비 80% 이상 활성화
        vol_pct = (current_vol / avg_vol_20) * 100
        if vol_pct < 80: return None
        
        # [필터 3] RSI: 20~40 (기술적 과매도 구간)
        rsi = calculate_rsi(hist_1y['Close']).iloc[-1]
        if not (20 <= rsi <= 40): return None
        
        # 뉴스 모멘텀
        news = stock.news
        sentiment_score = sum(1 for item in news[:5] if any(w in item['title'].lower() for w in ['growth', 'innovation', 'approval', 'partnership', 'beat']))
        
        # [전략] 지능형 진입가 및 손익비
        atr = (hist_1y['High'] - hist_1y['Low']).rolling(window=14).mean().iloc[-1]
        ma_20 = hist_1y['Close'].rolling(window=20).mean().iloc[-1]
        entry_price = min(current_price, ma_20) # 현재가와 20일선 중 낮은 쪽
        
        return {
            'sector': stock.info.get('sector', 'N/A'), 'ticker': ticker, 
            'price': current_price, 'entry': entry_price, 'rsi': round(rsi, 1),
            'vol': f"{vol_pct:.0f}%", 'momentum': sentiment_score,
            'take_profit': entry_price + (atr * (2 + sentiment_score)), 
            'stop_loss': entry_price - (atr * 1.5)
        }
    except: return None

def start_analysis():
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    sheet.clear()
    sheet.append_row(["섹터", "종목", "현재가", "RSI", "거래량강도", "모멘텀", "매수가", "익절가", "손절가"])
    
    with open('nasdaq_list.txt', 'r') as f:
        tickers = f.read().split()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(analyze_smart_ticker, tickers))
    
    final_list = sorted([r for r in results if r is not None], key=lambda x: x['rsi'])[:15]
    
    for c in final_list:
        sheet.append_row([c['sector'], c['ticker'], f"${c['price']:.2f}", c['rsi'], 
                          c['vol'], c['momentum'], f"${c['entry']:.2f}", 
                          f"${c['take_profit']:.2f}", f"${c['stop_loss']:.2f}"])

if __name__ == "__main__":
    start_analysis()
