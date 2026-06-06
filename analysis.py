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
    
    # 딥 분석 헤더
    headers = ["테마", "종목", "현재가", "RSI", "기술적 분석(AI)", "진입 적정가", "매도가(목표)", "손절가"]
    sheet.append_row(headers)
    
    # 나스닥 전체 종목을 테마별로 그룹화하여 관리 (사용자가 이 리스트를 관리함)
    market_data = {
        "기술주": ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "NFLX"],
        "반도체": ["AMD", "INTC", "MU", "AVGO", "QCOM", "TXN", "ADI"],
        "2차전지/전기차": ["TSLA", "ALB", "QS", "LCID", "RIVN", "PLL", "SQM"]
        # 필요시 여기에 테마와 종목을 계속 확장하세요
    }
    
    for theme, tickers in market_data.items():
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period="6mo")
                info = stock.info
                price = df['Close'].iloc[-1]
                rsi = calculate_rsi(df['Close']).iloc[-1]
                
                # [전략] RSI 45 미만 기준 적용
                if rsi < 45:
                    analysis = "매수 타겟(RSI 45미만)"
                    entry_price = price
                elif rsi >= 65:
                    analysis = "매도대기(과열구간)"
                    entry_price = "-"
                else:
                    analysis = "관망"
                    entry_price = "-"

                target_price = info.get('targetMeanPrice', price * 1.15)
                stop_loss = price * 0.95

                row = [theme, ticker, f"${price:.2f}", round(rsi, 2), analysis,
                       str(entry_price) if entry_price != "-" else "-",
                       f"${target_price:.2f}", f"${stop_loss:.2f}"]
                sheet.append_row(row)
                time.sleep(0.5)
            except Exception:
                continue
    print("✨ 나스닥 전체 테마별 딥 분석 완료!")

if __name__ == "__main__":
    start_analysis()
