import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import io

# 1. 여러 API 키를 관리하는 함수
def get_gemini_response(prompt, api_keys):
    """API 키 목록을 순회하며 성공할 때까지 요청을 시도합니다."""
    last_error = None
    for key in api_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = e
            continue  # 현재 키가 실패하면 다음 키로 이동
    raise last_error

st.set_page_config(page_title="AI 트립어드바이저 데이터 변환기 Pro", layout="wide")
st.title("🤖 AI 기반 트립어드바이저 데이터 변환기 (Multi-API)")

# 2. Secrets에서 여러 키 불러오기
api_keys = []
if "GEMINI_API_KEY_1" in st.secrets:
    api_keys.append(st.secrets["GEMINI_API_KEY_1"])
if "GEMINI_API_KEY_2" in st.secrets:
    api_keys.append(st.secrets["GEMINI_API_KEY_2"])

if not api_keys:
    st.error("❌ API 키가 등록되지 않았습니다. .streamlit/secrets.toml을 확인해 주세요.")
    st.stop()

uploaded_file = st.file_uploader("HAR 파일을 업로드하세요", type=['har'])

if uploaded_file:
    # 3. 데이터 추출 및 필터링
    har_data = json.load(uploaded_file)
    relevant_texts = []
    for entry in har_data.get('log', {}).get('entries', []):
        text = entry.get('response', {}).get('content', {}).get('text', '')
        if "RsOwnerMetrics" in text or "EventResponses" in text:
            relevant_texts.append(text)
    
    full_text = "\n".join(relevant_texts)[:40000]

    if st.button("AI 분석 시작 (엑셀 생성)"):
        with st.spinner("Gemini 2.5가 데이터를 정밀 분석 중입니다 (필드 10개)..."):
            # 4. 10개 필드 매핑 가이드가 포함된 프롬프트
            prompt = f"""
            첨부한 텍스트에서 트립어드바이저 호텔 실적 데이터를 일별로 추출해서 JSON 배열로 만들어줘.
            
            추출할 10개 지표:
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
            
            반드시 아래 예시와 같은 순수한 JSON 배열 형식으로만 대답해:
            예시: [{{ "일자": "2024-01-01", "Listing impressions": 120, "Average booking lead time": 131.5 }}]
            
            텍스트: {full_text}
            """
            
            try:
                # 멀티 키 함수 호출
                result_text = get_gemini_response(prompt, api_keys)
                
                # 5. JSON 파싱 및 표 변환
                clean_json = result_text.replace('```json', '').replace('```', '').strip()
                json_data = json.loads(clean_json)
                df = pd.DataFrame(json_data)
                
                if not df.empty:
                    st.success(f"✅ 데이터 추출 완료! (사용된 키 개수: {len(api_keys)}개)")
                    st.dataframe(df, use_container_width=True)
                    
                    # 엑셀 다운로드 생성
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False)
                    st.download_button("📥 엑셀 다운로드", output.getvalue(), "tripadvisor_full_report.xlsx")
                else:
                    st.error("추출된 데이터가 없습니다.")
                    
            except Exception as e:
                st.error(f"❌ 모든 API 키 시도 실패: {str(e)}")