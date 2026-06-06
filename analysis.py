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
    # 구글 시트 연결
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo").worksheet("시트1")
    
    # 데이터 기록 전 시트 초기화 (사용자님이 요청하신 깨끗한 상태)
    sheet.clear()
    
    # 헤더 작성
    headers = ["종목", "현재가", "RSI", "기술적 분석(AI)", "진입 적정가", "매도가(목표)", "손절가"]
    sheet.append_row(headers)
    
    # 분석 대상 종목 (사용자님의 원래 의도대로 확장 가능한 리스트)
    tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMD", "INTC"]
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            info = stock.info
            price = df['Close'].iloc[-1]
            
            # 직접 구현한 RSI 계산
            rsi = calculate_rsi(df['Close']).iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]

            # 사용자님 전략: RSI 30~40 구간 분석 로직
            if 30 <= rsi < 40:
                analysis = "강력매수(저점매집구간)"
                entry_price = price
            elif rsi < 30:
                analysis = "매수(단기과매도)"
                entry_price = price
            elif rsi >= 65:
                analysis = "매도대기(과열구간)"
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
            time.sleep(1)
        except Exception:
            continue
    print("✨ 분석 완료!")

if __name__ == "__main__":
    start_analysis()
