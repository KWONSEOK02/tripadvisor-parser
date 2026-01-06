import streamlit as st
import pandas as pd
import json
import io

# 1. 지표명 변환 및 순서 설정을 위한 매핑 사전
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

# 엑셀에 나타날 최종 컬럼 순서
FINAL_ORDER = ['일자'] + list(COLUMN_MAP.values())

st.set_page_config(page_title="트립어드바이저 실적 분석기", layout="wide")

st.title("📊 트립어드바이저 실적 데이터 변환 도구")
st.markdown("HAR 파일을 업로드하면 지정된 지표들을 정리하여 엑셀로 변환해 드립니다.")

uploaded_file = st.file_uploader("HAR 파일을 여기에 끌어다 놓으세요", type=['har'])

if uploaded_file is not None:
    try:
        har_data = json.load(uploaded_file)
        all_rows = []

        for entry in har_data['log']['entries']:
            # 데이터가 포함된 API 응답 필터링
            if 'ids' in entry['request']['url'] or 'page_view' in entry['request']['url']:
                content = entry['response']['content'].get('text')
                
                if content:
                    raw_json = json.loads(content)
                    
                    for item in raw_json:
                        if 'groupDimensionValue' in item:
                            # 기본 데이터: 일자
                            row = {'일자': item['groupDimensionValue']}
                            
                            # 지표 추출 및 명칭 변경
                            metrics = item.get('metrics', [])
                            for m in metrics:
                                m_type = m.get('metricType')
                                m_value = m.get('metricValue')
                                
                                # 요청하신 매핑 사전에 있는 지표만 가져와서 이름을 변경함
                                if m_type in COLUMN_MAP:
                                    row[COLUMN_MAP[m_type]] = m_value
                            
                            all_rows.append(row)

        if all_rows:
            # 데이터프레임 생성
            df = pd.DataFrame(all_rows)
            
            # 날짜 기준 중복 제거 및 정렬
            df = df.drop_duplicates(subset=['일자']).sort_values(by='일자', ascending=True)

            # 요청하신 순서대로 컬럼 재배치 (파일에 없는 컬럼은 제외하고 있는 것만 정렬)
            existing_cols = [col for col in FINAL_ORDER if col in df.columns]
            df = df[existing_cols]

            # 화면 표시
            st.success(f"✅ 총 {len(df)}일치의 실적 데이터를 추출했습니다.")
            st.dataframe(df, use_container_width=True)

            # 엑셀 파일 생성
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Tripadvisor_Performance')
                
                # 엑셀 상단 헤더 서식 (선택 사항)
                workbook = writer.book
                worksheet = writer.sheets['Tripadvisor_Performance']
                header_format = workbook.add_format({'bold': True, 'bg_color': '#EAF1DD', 'border': 1})
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

            st.download_button(
                label="📥 변환된 엑셀 파일 다운로드",
                data=output.getvalue(),
                file_name="tripadvisor_performance_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("파일 내에서 실적 데이터를 찾을 수 없습니다. 올바른 페이지를 캡처했는지 확인해주세요.")

    except Exception as e:
        st.error(f"변환 중 오류가 발생했습니다: {e}")