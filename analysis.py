import yfinance as yf
import pandas_ta as ta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import time

def start_analysis():
    # 1. 인증 및 시트 연결
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    
    # 2. 파일 ID로 시트 연결
    spreadsheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo")
    sheet = spreadsheet.worksheet("시트1")
    sheet.clear()
    
    # 3. 분석 대상 종목 (테마 리스트 추가 필요)
    themes = {"기술주": ["AAPL", "MSFT", "NVDA"]} # 여기에 종목 추가하세요
    
    headers = ["종목", "현재가", "RSI", "기술적 분석(AI)", "진입 적정가", "매도가(목표)", "손절가"]
    sheet.append_row(headers)

    for theme_name, tickers in themes.items():
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period="6mo")
                info = stock.info
                price = df['Close'].iloc[-1]
                rsi = ta.rsi(df['Close'], length=14).iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]

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
                continue

if __name__ == "__main__":
    start_analysis()
