import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import io

# 1. API 키 설정
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("❌ 'GEMINI_API_KEY'를 찾을 수 없습니다. .streamlit/secrets.toml 파일을 확인해 주세요.")
    st.stop()

model = genai.GenerativeModel('gemini-2.5-flash')

st.title("AI 기반 트립어드바이저 데이터 변환기")

uploaded_file = st.file_uploader("HAR 파일을 업로드하세요", type=['har'])

if uploaded_file:
    # 2. 데이터 추출 및 필터링
    har_data = json.load(uploaded_file)
    relevant_texts = []
    for entry in har_data.get('log', {}).get('entries', []):
        text = entry.get('response', {}).get('content', {}).get('text', '')
        # 핵심 키워드가 포함된 응답만 수집
        if "RsOwnerMetrics" in text or "EventResponses" in text:
            relevant_texts.append(text)
    
    full_text = "\n".join(relevant_texts)[:40000]

    if st.button("AI 분석 시작 (엑셀 생성)"):
            with st.spinner("Gemini 2.5가 10개의 지표를 정밀 분석 중입니다..."):
                # 프롬프트에 10개 항목을 명시적으로 모두 기재합니다.
                prompt = f"""
                첨부한 텍스트에서 트립어드바이저 호텔 실적 데이터를 일별로 추출해서 JSON 배열로 만들어줘.
                
                반드시 아래 10개 필드를 모두 포함해야 해(데이터가 전부 0이여도 필드는 10여야함):
                1. 일자: groupDimensionValue 또는 Date (YYYY-MM-DD)
                2. Listing impressions: LISTING_IMPRESSION_COUNT
                3. Unique page views: UNIQUE_VISIT_COUNT
                4. Average bubble rating: BUBBLE_RATING
                5. Average ranking: RANKING
                6. Direct referrals: HOTEL_REFERRAL_CLICK_COUNT
                7. Booking clicks: HOTEL_BOOKINGS_CLICK_COUNT
                8. New reviews: REVIEW_COUNT
                9. Average booking length: HOTEL_SEARCH_TRIP_LENGTH_AVERAGE
                10. Average booking lead time: HOTEL_SEARCH_LEAD_TIME_AVERAGE
                
                결과는 오직 JSON 배열 형식으로만 대답해:
                예시: [{{ "일자": "2024-01-01", "Listing impressions": 120, ..., "Average booking lead time": 131.5 }}]
                
                텍스트: {full_text}
                """
            
            try:
                response = model.generate_content(prompt)
                # 4. JSON 파싱 및 표 변환
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                json_data = json.loads(clean_json)
                df = pd.DataFrame(json_data)
                
                if not df.empty:
                    st.success("데이터 추출 완료!")
                    st.dataframe(df)
                    
                    # 엑셀 다운로드 생성
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False)
                    st.download_button("📥 엑셀 다운로드", output.getvalue(), "tripadvisor_report.xlsx")
                else:
                    st.error("추출된 데이터가 없습니다.")
                    
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")