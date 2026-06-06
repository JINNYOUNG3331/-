import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def start_analysis():
    # 1. 인증 및 시트 초기화
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    sheet.clear()
    sheet.append_row(["섹터", "종목", "현재가", "RSI", "판정", "진입가", "목표가(%)", "손절가"])
    
    # 2. 전체 리스트 읽기
    with open('nasdaq_list.txt', 'r') as f:
        tickers = f.read().split()
    
    candidates = []
    
    # 3. 전체 전수 조사 (RSI 20~35 조건 만족 종목 수집)
    for ticker in tickers:
        try:
            ticker = ticker.replace("^", "-").replace("/", "-")
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if df.empty: continue
            
            rsi = calculate_rsi(df['Close']).iloc[-1]
            
            if 20 <= rsi <= 35:
                price = df['Close'].iloc[-1]
                info = stock.info
                candidates.append({
                    'sector': info.get('sector', 'N/A'),
                    'ticker': ticker, 
                    'price': price, 
                    'rsi': rsi, 
                    'info': info
                })
        except: continue
        time.sleep(0.1) # 서버 부하 방지용 짧은 대기

    # 4. RSI가 낮은 순(가장 강력한 매수 자리)으로 15개 선별
    final_15 = sorted(candidates, key=lambda x: x['rsi'])[:15]
    
    # 5. 결과 시트 작성
    for c in final_15:
        price = c['price']
        wall_target = c['info'].get('targetMeanPrice', price * 1.15)
        # 내 전략 반영: 월가 평균 + 15% 상승분의 평균값
        my_target = (wall_target + (price * 1.15)) / 2
        profit_pct = ((my_target - price) / price) * 100
        
        sheet.append_row([
            c['sector'], c['ticker'], f"${price:.2f}", round(c['rsi'], 2), 
            "★강력매수(바닥권)" if c['rsi'] < 25 else "매수(기술적반등)", 
            f"${price*1.01:.2f}", f"{profit_pct:.1f}% (${my_target:.2f})", f"${price*0.92:.2f}"
        ])

if __name__ == "__main__":
    start_analysis()
