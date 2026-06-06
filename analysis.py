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
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    sheet.clear()
    
    headers = ["종목", "현재가", "RSI", "기술적 분석(AI)", "진입 적정가", "매도가(목표)", "손절가"]
    sheet.append_row(headers)
    
    # [핵심] 테마 구분 없이, 분석할 모든 종목 리스트 (이 리스트에 원하는 모든 나스닥 종목을 넣으세요)
    all_tickers = [
        "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "NFLX", 
        "AMD", "INTC", "MU", "AVGO", "QCOM", "TXN", "ADI",
        "META", "PEP", "COST", "CSCO", "CMCSA", "ADBE", "PYPL"
    ]
    
    for ticker in all_tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            info = stock.info
            price = df['Close'].iloc[-1]
            rsi = calculate_rsi(df['Close']).iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]

            # 사용자님 전략: RSI 30~40 구간 분석
            if 30 <= rsi < 40:
                analysis = "강력매수(전략구간)"
                entry_price = price
            elif rsi < 30:
                analysis = "매수(단기과매도)"
                entry_price = price
            elif rsi >= 65:
                analysis = "매도대기(과열)"
                entry_price = "-"
            else:
                analysis = "관망"
                entry_price = "-"

            target_price = info.get('targetMeanPrice', price * 1.15)
            stop_loss = price * 0.95

            row = [ticker, f"${price:.2f}", round(rsi, 2), analysis,
                   str(entry_price) if entry_price != "-" else "-",
                   f"${target_price:.2f}", f"${stop_loss:.2f}"]
            sheet.append_row(row)
            time.sleep(0.5) # 더 많은 종목을 처리하기 위해 간격 조정
        except Exception:
            continue
    print("✨ 전체 나스닥 종목 딥 분석 완료!")

if __name__ == "__main__":
    start_analysis()
