# prompts.py

def get_extraction_prompt(hotel_name, full_text):
    return f"""
            당신은 트립어드바이저 HAR 파일 데이터 추출 전문가입니다. 
            제공된 텍스트 데이터에서 아래의 기술적 필드들을 매핑하여 지정된 한글/영문 지표명으로 변환하고 JSON 배열 형식으로 응답하세요.

            ### 1. 필드 매핑 규칙 (중요):
            텍스트 데이터 내의 기술적 명칭을 아래의 추출 지표명(Key)으로 반드시 변환하세요.
            - 'groupDimensionValue' 또는 'Date' (YYYY-MM-DD 형식) -> **일자**
            - 'LISTING_IMPRESSION_COUNT' -> **Listing impressions**
            - 'UNIQUE_VISIT_COUNT' -> **Unique page views**
            - 'BUBBLE_RATING' -> **Average bubble rating**
            - 'RANKING' -> **Average ranking**
            - 'HOTEL_REFERRAL_CLICK_COUNT' -> **Direct referrals**
            - 'HOTEL_BOOKINGS_CLICK_COUNT' -> **Booking clicks**
            - 'REVIEW_COUNT' -> **New reviews**
            - 'HOTEL_SEARCH_TRIP_LENGTH_AVERAGE' -> **Average booking length**
            - 'HOTEL_SEARCH_LEAD_TIME_AVERAGE' -> **Average booking lead time**

            ### 2. 데이터 정제 규칙:
            1. **지점명 삽입**: 모든 데이터 객체에 "지점명" 키를 추가하고 값으로 "{hotel_name}"을 넣으세요.
            2. **Null 처리**: 수치 데이터가 없거나 null, NaN, 빈 값인 경우 반드시 숫자 **0**으로 표기하세요.
            3. **케이스 준수**: 추출 지표명(Key)은 위에서 지정한 대로 대소문자와 띄어쓰기를 정확히 유지하세요. 절대 'snake_case'로 변환하지 마세요.
            4. **응답 형식**: 설명 없이 오직 JSON 배열 데이터만 출력하세요.

            ### 3. 최종 출력 JSON 키 목록:
            - 일자
            - 지점명
            - Listing impressions
            - Unique page views
            - Average bubble rating
            - Average ranking
            - Direct referrals
            - Booking clicks
            - New reviews
            - Average booking length
            - Average booking lead time

            ### 응답 예시:
            [
              {{
                "일자": "2024-01-01",
                "지점명": "{hotel_name}",
                "Listing impressions": 120,
                "Unique page views": 5,
                "Average bubble rating": 4.5,
                "Average ranking": 10,
                "Direct referrals": 2,
                "Booking clicks": 1,
                "New reviews": 0,
                "Average booking length": 2,
                "Average booking lead time": 15
              }}
            ]

            분석할 데이터:
            {full_text}
            """