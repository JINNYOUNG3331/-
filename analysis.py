import yfinance as yf
import pandas as pd
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
    
    # 시트 연결
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    sheet.clear()
    
    # 분석 종목
    themes = {"기술주": ["AAPL", "MSFT", "NVDA"]} 
    headers = ["종목", "현재가", "RSI", "기술적 분석(AI)", "진입 적정가", "매도가(목표)", "손절가"]
    sheet.append_row(headers)

    for ticker in themes["기술주"]:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            info = stock.info
            price = df['Close'].iloc[-1]
            rsi = calculate_rsi(df['Close']).iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]

            # 전략 로직
            entry_price = price if rsi <= 35 else "-"
            target_price = info.get('targetMeanPrice', price * 1.15)
            stop_loss = price * 0.95

            if rsi <= 35 and price < ma20: analysis = "강력매수(저점매집구간)"
            elif rsi <= 35: analysis = "매수(단기과매도)"
            elif rsi >= 65: analysis = "매도대기(과열구간)"
            else: analysis = "관망"

            row = [ticker, f"${price:.2f}", round(rsi, 2), analysis,
                   f"${entry_price:.2f}" if entry_price != "-" else "-",
                   f"${target_price:.2f}", f"${stop_loss:.2f}"]
            sheet.append_row(row)
            time.sleep(1)
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    start_analysis()
