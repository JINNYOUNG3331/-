import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

def start_analysis():
    # 1. 구글 시트 연결 설정 (GCP_CREDENTIALS 환경 변수 사용)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 환경 변수에서 키 값을 가져와서 인증
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    
    # 2. '데이터'라는 이름의 구글 시트 연결
    spreadsheet = client.open("데이터")
    sheet = spreadsheet.sheet1
    
    # 3. 이제 'sheet' 변수가 정의되었으므로 아래 코드가 작동합니다.
    sheet.clear()
    
    # 이후 분석 로직 (기존에 작성하신 코드 내용을 아래에 그대로 두시면 됩니다)
    # ... (작성하신 나머지 코드) ...

if __name__ == "__main__":
    start_analysis()
