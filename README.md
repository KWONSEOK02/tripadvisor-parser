🏨 TripAdvisor 리포트 자동 생성기 (HAR 기반)

트립어드바이저(TripAdvisor) HAR 파일을 업로드하고 지점명만 입력하면,
AI가 운영 지표를 자동으로 추출·정리해 엑셀 리포트로 생성해주는 도구입니다.

✔️ 별도 설정 불필요 (Zero-Config)
✔️ HAR 구조가 달라도 자동 탐색
✔️ 실패 시 자동 재시도 포함

✨ 주요 기능
1. Zero-Config HAR 자동 분석

사용자는 HAR 파일 업로드 + 지점명 입력만 하면 됩니다.
내부적으로 다음 순서로 자동 탐색(Fallback) 을 수행합니다.

/data/graphql/ids 엔드포인트

URL에 graphql 포함된 응답

응답 본문에 RsOwnerMetrics_ 지표 키 포함 여부

모든 경우에 대해 2xx 응답 + JSON + 지표 payload 조건을 만족하는 항목만 사용합니다.

2. 지표 응답 자동 압축 (토큰 최적화)

HAR 전체가 아니라 응답 본문(response.content.text) 만 사용

RsOwnerMetrics_* 관련 데이터만 남겨 불필요한 GraphQL payload 제거

AI 입력 토큰을 최소화해 속도·안정성 개선

3. AI 기반 지표 추출 (안정화 처리 포함)

Gemini 모델을 사용해 일자별 운영 지표를 구조화된 데이터로 변환합니다.

✔ 안정성 설계

JSON 배열만 추출해서 파싱

일시적인 AI 응답 오류 발생 시 최대 2회 자동 재시도

실패한 경우에도 UX는 자연스럽게 유지

4. 결과 자동 정리 & 엑셀 다운로드

일자 기준 정렬

중복 제거

누락값은 0으로 보정

즉시 엑셀(.xlsx) 다운로드 가능

📊 추출 지표 목록
지표명
일자
지점명
Listing impressions
Unique page views
Average bubble rating
Average ranking
Direct referrals
Booking clicks
New reviews
Average booking length
Average booking lead time
🧭 사용 방법

트립어드바이저 관리자 페이지에서 HAR 파일 저장

본 앱에서 HAR 파일 업로드

지점명 입력

[분석 시작] 버튼 클릭

결과 미리보기 확인 후 엑셀 다운로드

🛡️ 안정성 & UX 설계 포인트

사용자는 필터 조건이나 기술 설정을 전혀 알 필요 없음

데이터 탐색·전처리·재시도는 모두 내부에서 자동 처리

고급 사용자를 위해 필터 기준은 고급 정보(선택)에만 노출

“설정은 숨기고, 불안감만 줄이는 UX”를 목표로 설계되었습니다.

🛠️ 기술 스택

Frontend / App: Streamlit

AI 모델: Google Gemini (병렬 처리 지원)

데이터 처리: Python (pandas)

입력 데이터: HAR (HTTP Archive)

출력 형식: Excel (.xlsx)

🚀 현재 상태

 Zero-Config 자동 필터링

 HAR 구조 변화 대응

 AI 파싱 실패 자동 재시도

 엑셀 리포트 생성

 (선택) 대시보드 시각화

 (선택) 다지점 비교 리포트

📌 한 줄 요약

“HAR 파일만 있으면, 트립어드바이저 운영 데이터를 클릭 몇 번으로 엑셀 리포트로 만들어주는 자동화 도구”