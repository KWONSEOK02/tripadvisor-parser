import streamlit as st
import pandas as pd
import json
import io

# 1. 지표명 매핑 (괄호 안의 원래 이름을 괄호 밖의 이름으로 변환)
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

# 2. 엑셀에 나타날 최종 컬럼 순서 설정
# 일자, 지점명을 가장 앞에 배치
FINAL_ORDER = ['일자', '지점명'] + list(COLUMN_MAP.values())

st.set_page_config(page_title="트립어드바이저 실적 분석기", layout="wide")

st.title("📊 트립어드바이저 실적 데이터 변환 도구")
st.markdown("HAR 파일을 업로드하면 지정된 지표들을 정리하여 엑셀로 변환해 드립니다.")

uploaded_file = st.file_uploader("HAR 파일을 여기에 끌어다 놓으세요", type=['har'])

if uploaded_file is not None:
    try:
        har_data = json.load(uploaded_file)
        rows = []
        
        # HAR 파일 내의 모든 entry를 순회하며 데이터 추출
        for entry in har_data.get('log', {}).get('entries', []):
            response = entry.get('response', {})
            content = response.get('content', {})
            
            if 'text' in content:
                try:
                    data_json = json.loads(content['text'])
                    
                    # 'EventResponses' 또는 유사한 구조에서 데이터 추출 (트립어드바이저 API 구조에 따라 조정)
                    # 여기서는 일반적인 트래픽 데이터 추출 로직을 가정합니다.
                    if isinstance(data_json, dict) and 'timeSeries' in data_json:
                        # 지점명 추출 (파일에 있다면 포함)
                        branch_name = data_json.get('locationName') or data_json.get('propertyName') or "알 수 없음"
                        
                        for item in data_json['timeSeries']:
                            row = {'일자': item.get('date'), '지점명': branch_name}
                            
                            # COLUMN_MAP에 정의된 지표들 추출
                            for raw_key, friendly_name in COLUMN_MAP.items():
                                row[friendly_name] = item.get(raw_key)
                            
                            rows.append(row)
                except:
                    continue

        if rows:
            df = pd.DataFrame(rows)

            # 일자 형식 통일 및 오름차순 정렬
            if '일자' in df.columns:
                df['일자'] = pd.to_datetime(df['일자']).dt.strftime('%Y-%m-%d')
                df = df.drop_duplicates(subset=['일자', '지점명']).sort_values(by='일자', ascending=True)

            # 요청하신 순서대로 컬럼 재배치 (파일에 없는 컬럼은 제외)
            existing_cols = [col for col in FINAL_ORDER if col in df.columns]
            df = df[existing_cols]

            # 화면 표시 및 다운로드
            st.success(f"✅ 총 {len(df)}일치의 실적 데이터를 추출했습니다.")
            st.dataframe(df, use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Tripadvisor_Report')
                
                # 헤더 서식
                workbook = writer.book
                worksheet = writer.sheets['Tripadvisor_Report']
                header_format = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

            st.download_button(
                label="📥 변환된 엑셀 파일 다운로드",
                data=output.getvalue(),
                file_name="tripadvisor_performance_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("분석 가능한 실적 데이터를 찾지 못했습니다. 올바른 HAR 파일인지 확인해 주세요.")

    except Exception as e:
        st.error(f"파일 처리 중 오류가 발생했습니다: {e}")