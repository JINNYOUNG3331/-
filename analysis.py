import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

def start_analysis():
    # 1. 인증 설정
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    
    # 2. 파일 ID를 직접 입력하여 시트 연결 (가장 확실한 방법!)
    # ID: 1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo
    spreadsheet = client.open_by_key("1PsBdZmAlG1OLX9PBgbTsKqvfE_EzpMBtzO_Ns_Eu1Wo")
    sheet = spreadsheet.worksheet("시트1")
    
    # 3. 데이터 초기화 및 작성 시작
    sheet.clear()
    
    # [이후에 작성하신 분석 로직을 여기에 그대로 붙여넣으세요]
    print("성공적으로 연결되었습니다.")

if __name__ == "__main__":
    start_analysis()
