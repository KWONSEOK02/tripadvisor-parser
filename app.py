import streamlit as st
import pandas as pd
import json
import io

# 페이지 설정
st.set_page_config(page_title="트립어드바이저 데이터 변환기", layout="wide")

st.title("📊 트립어드바이저 HAR ➡️ 엑셀 변환 도구")
st.markdown("개발자 도구에서 저장한 **HAR 파일**을 업로드하면 일별 데이터를 정리해 드립니다.")

uploaded_file = st.file_uploader("HAR 파일을 여기에 끌어다 놓으세요", type=['har'])

if uploaded_file is not None:
    try:
        # 1. HAR 파일 읽기
        har_data = json.load(uploaded_file)
        all_rows = []

        # 2. 데이터 추출 로직
        for entry in har_data['log']['entries']:
            # 데이터가 포함된 API 응답 찾기 (URL에 'ids' 혹은 'page_view' 포함 여부 확인)
            if 'ids' in entry['request']['url'] or 'page_view' in entry['request']['url']:
                content = entry['response']['content'].get('text')
                
                if content:
                    raw_json = json.loads(content)
                    
                    # 리스트 형태의 데이터 순회
                    for item in raw_json:
                        if 'groupDimensionValue' in item:  # 날짜 정보가 있는 항목
                            row = {'날짜': item['groupDimensionValue']}
                            
                            # metrics 리스트 안에 있는 개별 지표들을 컬럼으로 변환
                            # 예: [{'metricType': 'RANKING', 'metricValue': 95}, ...]
                            for m in item.get('metrics', []):
                                metric_name = m.get('metricType')
                                metric_value = m.get('metricValue')
                                row[metric_name] = metric_value
                            
                            all_rows.append(row)

        if all_rows:
            # 3. 데이터프레임 생성 및 정렬
            df = pd.DataFrame(all_rows).drop_duplicates(subset=['날짜'])
            df = df.sort_values(by='날짜', ascending=False)
            
            # 4. 화면 표시
            st.success(f"총 {len(df)}일치 데이터를 찾았습니다!")
            st.dataframe(df, use_container_width=True)

            # 5. 엑셀 다운로드 기능
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Performance')
            
            st.download_button(
                label="📥 엑셀 파일로 다운로드",
                data=output.getvalue(),
                file_name="tripadvisor_daily_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("파일에서 유효한 데이터를 찾지 못했습니다. 올바른 HAR 파일인지 확인해주세요.")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")