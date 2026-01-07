import streamlit as st
import pandas as pd
import json
import io

# 1. 지표명 매핑 (사용자 요청 반영)
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

FINAL_ORDER = ['일자', '지점명'] + list(COLUMN_MAP.values())

st.set_page_config(page_title="트립어드바이저 실적 분석기", layout="wide")

st.title("📊 트립어드바이저 실적 데이터 변환 도구")

uploaded_file = st.file_uploader("HAR 파일을 업로드하세요", type=['har'])

if uploaded_file is not None:
    try:
        har_data = json.load(uploaded_file)
        rows = []
        
        for entry in har_data.get('log', {}).get('entries', []):
            content = entry.get('response', {}).get('content', {})
            if 'text' in content:
                try:
                    data_json = json.loads(content['text'])
                    
                    # HAR 파일 내 'EventResponses' 구조 분석
                    if isinstance(data_json, dict) and 'EventResponses' in data_json:
                        # 지점명 추출 시도 (없으면 '정보 없음' 표시)
                        branch_name = data_json.get('locationName') or "정보 없음"
                        
                        events = data_json['EventResponses']
                        for event in events:
                            # 날짜 키 확인 (보통 'Date' 또는 'date'로 들어옵니다)
                            date_val = event.get('Date') or event.get('date')
                            if not date_val:
                                continue
                                
                            row = {'일자': date_val, '지점명': branch_name}
                            
                            # 데이터가 Metrics 내부에 있을 경우와 평면 구조일 경우 모두 대응
                            metrics_data = event.get('Metrics', event)
                            
                            for raw_key, friendly_name in COLUMN_MAP.items():
                                row[friendly_name] = metrics_data.get(raw_key, 0)
                            
                            rows.append(row)
                except:
                    continue

        if rows:
            df = pd.DataFrame(rows)
            # 일자 오름차순 정렬 및 중복 제거
            df['일자'] = pd.to_datetime(df['일자']).dt.strftime('%Y-%m-%d')
            df = df.drop_duplicates(subset=['일자', '지점명']).sort_values(by='일자', ascending=True)

            # 컬럼 순서 재배치
            existing_cols = [col for col in FINAL_ORDER if col in df.columns]
            df = df[existing_cols]

            st.success(f"✅ {len(df)}건의 데이터를 성공적으로 추출했습니다.")
            st.dataframe(df, use_container_width=True)

            # 엑셀 다운로드 로직
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Performance')
            
            st.download_button(
                label="📥 엑셀 파일 다운로드",
                data=output.getvalue(),
                file_name="tripadvisor_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("⚠️ 파일 내에서 실적 데이터를 찾을 수 없습니다. 분석 탭에서 데이터가 완전히 로드된 후 HAR 파일을 다시 추출해 주세요.")

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")