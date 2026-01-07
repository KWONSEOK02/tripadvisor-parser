import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime

# 1. 지표명 매핑 (사용자 요청: 괄호 밖의 이름으로 변경)
COLUMN_MAP = {
    'LISTING_IMPRESSION_COUNT': 'Listing impressions',
    'UNIQUE_VISIT_COUNT': 'Unique page views',
    'BUBBLE_RATING': 'Average bubble rating',
    'RANKING': 'Average ranking',
    'HOTEL_REFERRAL_CLICK_COUNT': 'Direct referrals',
    'HOTEL_BOOKINGS_CLICK_COUNT': 'Booking clicks',
    'REVIEW_COUNT': 'New reviews',
    'HOTEL_SEARCH_TRIP_LENGTH_AVERAGE': 'Average booking length',
    'HOTEL_SEARCH_LEAD_TIME_AVERAGE': 'Average booking lead time'
}

# 2. 최종 컬럼 순서 설정
FINAL_ORDER = ['일자', '지점명'] + list(COLUMN_MAP.values())

st.set_page_config(page_title="트립어드바이저 실적 분석기", layout="wide")

st.title("📊 트립어드바이저 실적 데이터 변환 도구")
st.info("HAR 파일에서 데이터를 추출하여 요청하신 형식으로 정렬 및 변환합니다.")

uploaded_file = st.file_uploader("HAR 파일을 업로드하세요", type=['har'])

if uploaded_file is not None:
    try:
        har_data = json.load(uploaded_file)
        all_rows = []
        
        # HAR 파일의 entries 순회
        for entry in har_data.get('log', {}).get('entries', []):
            # 응답 본문 확인
            response_text = entry.get('response', {}).get('content', {}).get('text', '')
            if not response_text:
                continue
                
            try:
                data_json = json.loads(response_text)
                
                # 'EventResponses'가 있고 데이터가 비어있지 않은 경우 탐색
                if isinstance(data_json, dict) and data_json.get('EventResponses'):
                    events = data_json['EventResponses']
                    
                    # 지점명 추출: 파일 내 locationId나 다른 정보를 활용
                    # HAR 내 URL에서 locationId 추출 시도
                    url = entry.get('request', {}).get('url', '')
                    loc_id = "Unknown"
                    if "locationId=" in url:
                        loc_id = url.split("locationId=")[1].split("&")[0]

                    for event in events:
                        # 날짜 정보 (Date 혹은 date 키 확인)
                        raw_date = event.get('Date') or event.get('date')
                        if not raw_date:
                            continue
                            
                        # 행 데이터 생성
                        row = {
                            '일자': raw_date,
                            '지점명': loc_id  # 파일에 명확한 이름이 없으면 ID로 표시
                        }
                        
                        # 지표 매핑 (Metrics 객체 안에 있거나 평면 구조일 경우 모두 대응)
                        metrics_source = event.get('Metrics', event)
                        for raw_key, friendly_name in COLUMN_MAP.items():
                            row[friendly_name] = metrics_source.get(raw_key, 0)
                        
                        all_rows.append(row)
            except json.JSONDecodeError:
                continue

        if all_rows:
            df = pd.DataFrame(all_rows)
            
            # 1. 일자 형식 정리 (ISO 형식을 YYYY-MM-DD로)
            df['일자'] = pd.to_datetime(df['일자']).dt.strftime('%Y-%m-%d')
            
            # 2. 중복 제거 (여러 API 호출에서 겹치는 데이터 제거)
            df = df.drop_duplicates(subset=['일자', '지점명'])
            
            # 3. 오름차순 정렬 (날짜 기준)
            df = df.sort_values(by='일자', ascending=True)

            # 4. 컬럼 순서 고정 및 없는 컬럼 생성 (0으로 채움)
            for col in FINAL_ORDER:
                if col not in df.columns:
                    df[col] = 0
            
            df = df[FINAL_ORDER]

            # 결과 출력
            st.success(f"✅ 총 {len(df)}일치의 데이터를 성공적으로 추출했습니다.")
            st.dataframe(df, use_container_width=True)

            # 엑셀 변환
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Report')
                
                # 서식 지정
                workbook = writer.book
                worksheet = writer.sheets['Report']
                header_format = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

            st.download_button(
                label="📥 변환된 엑셀 다운로드",
                data=output.getvalue(),
                file_name=f"Tripadvisor_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("⚠️ 데이터 추출 실패: 업로드한 HAR 파일에 유효한 실적 데이터(EventResponses)가 포함되어 있지 않습니다. 트립어드바이저 페이지에서 차트가 로드된 것을 확인한 후 다시 추출해 주세요.")

    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")