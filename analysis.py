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
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    sheet.clear()
    sheet.append_row(["섹터", "종목", "현재가", "RSI", "분석결과", "진입적정가", "목표가", "손절가"])
    
    # [수정된 부분] 텍스트 파일에서 리스트를 읽어옵니다.
    with open('nasdaq_list.txt', 'r') as f:
        tickers_list = f.read().split()
    
    for ticker in tickers_list:
        try:
            ticker = ticker.replace("^", "-").replace("/", "-")
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if df.empty: continue
            
            info = stock.info
            price = df['Close'].iloc[-1]
            rsi = calculate_rsi(df['Close']).iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            
            if rsi < 45:
                sector = info.get('sector', '기타')
                entry_price = min(price, ma20) * 0.98
                target_price = info.get('targetMeanPrice', price * 1.20)
                stop_loss = entry_price * 0.92
                analysis = "강력매수(저점)" if rsi < 35 else "매수타겟(과매도)"
                sheet.append_row([sector, ticker, f"${price:.2f}", round(rsi, 2), analysis,
                                  f"${entry_price:.2f}", f"${target_price:.2f}", f"${stop_loss:.2f}"])
                time.sleep(0.5)
        except:
            continue

if __name__ == "__main__":
    start_analysis()
