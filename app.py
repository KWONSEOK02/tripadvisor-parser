import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import io
import base64
import prompts
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

# --- [내부 로직: 사용자에게 숨겨진 자동 설정값들] ---
DEFAULT_URL_KEYWORD = "/data/graphql/ids"
DEFAULT_PREPROCESS_MODE = "response_text_compact_graphql_ids"

# -----------------------------
# HAR 전처리 유틸 (내부 자동화)
# -----------------------------
def iter_har_entries(har_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return har_data.get("log", {}).get("entries", []) or []

def safe_get(d: Any, path: List[Any], default=None):
    cur = d
    for p in path:
        try:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            elif isinstance(cur, list) and isinstance(p, int) and 0 <= p < len(cur):
                cur = cur[p]
            else:
                return default
        except Exception:
            return default
    return cur

def extract_response_text(entry: Dict[str, Any]) -> str:
    text = safe_get(entry, ["response", "content", "text"], "") or ""
    encoding = (safe_get(entry, ["response", "content", "encoding"], "") or "").lower()
    if encoding == "base64":
        try:
            return base64.b64decode(text).decode("utf-8", errors="replace")
        except Exception:
            return text
    return text

def looks_like_owner_metrics_payload(resp_text: str) -> bool:
    keywords = ["RsOwnerMetrics_", "metricType", "groupDimensionValue", "LISTING_IMPRESSION_COUNT"]
    return any(k in resp_text for k in keywords)

def compact_tripadvisor_graphql_ids_response(resp_text: str) -> str:
    try:
        payload = json.loads(resp_text)
        if not isinstance(payload, list):
            return resp_text
        compact = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            data_obj = item.get("data")
            if not isinstance(data_obj, dict):
                continue
            owner_keys = [k for k in data_obj.keys() if str(k).startswith("RsOwnerMetrics_")]
            if owner_keys:
                compact.append({"data": {k: data_obj.get(k) for k in owner_keys}})
        return json.dumps(compact, ensure_ascii=False, separators=(",", ":")) if compact else resp_text
    except Exception:
        return resp_text

# -----------------------------
# 핵심 자동 처리 함수 (Zero-Config + Fallback)
# -----------------------------
def auto_smart_filter(har_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Zero-Config 자동 탐색:
    1순위: URL에 /data/graphql/ids 포함
    2순위: URL에 graphql 포함
    3순위: 응답 본문에 RsOwnerMetrics_ 포함
    공통 조건: 2xx + JSON mime + (지표로 보이는 payload)
    """
    entries = iter_har_entries(har_data)

    def base_conditions(entry: Dict[str, Any]) -> bool:
        status = safe_get(entry, ["response", "status"], 0) or 0
        mime = (safe_get(entry, ["response", "content", "mimeType"], "") or "").lower()
        return (200 <= int(status) < 300) and ("json" in mime)

    def is_metrics_entry(entry: Dict[str, Any]) -> bool:
        resp_text = extract_response_text(entry)
        return bool(resp_text) and looks_like_owner_metrics_payload(resp_text)

    # --- 1순위: /data/graphql/ids ---
    out_1 = []
    for entry in entries:
        url = (safe_get(entry, ["request", "url"], "") or "")
        if base_conditions(entry) and (DEFAULT_URL_KEYWORD in url) and is_metrics_entry(entry):
            out_1.append(entry)
    if out_1:
        return out_1

    # --- 2순위: URL에 graphql 포함 ---
    out_2 = []
    for entry in entries:
        url = (safe_get(entry, ["request", "url"], "") or "").lower()
        if base_conditions(entry) and ("graphql" in url) and is_metrics_entry(entry):
            out_2.append(entry)
    if out_2:
        return out_2

    # --- 3순위: 응답 본문에 RsOwnerMetrics_ 포함 (URL 무관) ---
    out_3 = []
    for entry in entries:
        if base_conditions(entry):
            resp_text = extract_response_text(entry)
            if "RsOwnerMetrics_" in (resp_text or "") and is_metrics_entry(entry):
                out_3.append(entry)
    return out_3

#------------------
# JSON 배열만 추출하는 헬퍼 함수
#------------------
def extract_json_array(text: str) -> str:
    """
    Gemini 응답에서 첫 '[' 와 마지막 ']' 사이만 잘라냄
    """
    if not text:
        return ""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start : end + 1]

# -----------------------------
# Gemini 호출 로직 (병렬 처리)
# -----------------------------
def process_chunk(index: int, chunk: str, hotel_name: str, api_key: str):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = prompts.get_extraction_prompt(hotel_name, chunk)

    for attempt in range(3):  # 최초 1회 + 재시도 2회
        try:
            response = model.generate_content(prompt)

            # 1) 코드블록 제거
            text = (
                response.text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            # 2) JSON 배열만 추출
            json_text = extract_json_array(text)
            if not json_text:
                raise ValueError("JSON array not found")

            # 3) 파싱
            parsed = json.loads(json_text)

            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
            else:
                raise ValueError("Parsed JSON is not list/dict")

        except Exception:
            # 마지막 시도면 포기
            if attempt == 2:
                return []
            continue


# -----------------------------
# Streamlit UI (초간단 버전)
# -----------------------------
st.set_page_config(page_title="트립어드바이저 데이터 자동 변환기", layout="centered")
st.title("🏨 트립어드바이저 리포트 자동 생성기")
st.markdown("HAR 파일을 업로드하고 지점명만 입력하면 AI가 보고서를 만들어 드립니다.")

# API 키 자동 로드
api_keys = [st.secrets[k] for k in ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2"] if k in st.secrets]

# API 키가 없으면 안내 후 중단
if not api_keys:
    st.error("❌ Gemini API 키가 설정되어 있지 않습니다. Streamlit secrets에 GEMINI_API_KEY_1 (및 선택으로 GEMINI_API_KEY_2)를 추가해 주세요.")
    st.stop()

with st.container(border=True):
    uploaded_file = st.file_uploader("1. HAR 파일을 드래그해서 놓으세요", type=["har"])
    hotel_name_input = st.text_input("2. 지점명을 입력하세요", placeholder="예: 트립어드바이저 서울점")

with st.expander("고급 정보(선택)"):
    st.markdown(
        """
**현재 자동 필터 (Zero-Config)**  
- 1순위: `/data/graphql/ids` + (2xx) + (JSON) + (지표 키워드)  
- 2순위: URL에 `graphql` 포함 + (2xx) + (JSON) + (지표 키워드)  
- 3순위: 응답 본문에 `RsOwnerMetrics_` 포함 + (2xx) + (JSON)  

**전처리(토큰 절감)**  
- HAR 전체가 아니라 `response.content.text`(응답 본문)만 사용  
- `RsOwnerMetrics_*` 데이터만 남기도록 압축(가능한 경우)  
        """
    )

if uploaded_file and hotel_name_input:
    st.caption("자동으로 트립어드바이저 지표 응답을 찾아 압축 후 분석합니다.")
    if st.button("🚀 분석 시작 (약 1분 소요)", width='stretch', type="primary"):
        with st.status("데이터 분석 및 보고서 생성 중...", expanded=True) as status:
            har_data = json.load(uploaded_file)

            # [자동 처리 1] 스마트 필터링 (Fallback 포함)
            st.write("🔍 데이터 위치 찾는 중...")
            filtered = auto_smart_filter(har_data)

            if not filtered:
                st.error("데이터를 찾을 수 없습니다. 올바른 HAR 파일인지 확인해 주세요.")
                st.stop()

            # [자동 처리 2] 전처리 및 압축
            st.write(f"📦 데이터 압축 및 최적화 중... (발견된 항목: {len(filtered)}개)")
            parts = []
            for entry in filtered:
                txt = extract_response_text(entry)
                parts.append(compact_tripadvisor_graphql_ids_response(txt))
            full_text = "\n\n-----\n\n".join(parts)

            # [자동 처리 3] 분할 및 병렬 AI 분석
            st.write("🤖 AI 지표 추출 중 (병렬 엔진 가동)...")
            chunks = [full_text[i : i + 40000] for i in range(0, len(full_text), 40000)]
            all_data: List[Dict[str, Any]] = []

            max_workers = max(1, len(api_keys))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        process_chunk,
                        i,
                        chunk,
                        hotel_name_input,
                        api_keys[i % len(api_keys)],
                    )
                    for i, chunk in enumerate(chunks)
                ]
                for future in as_completed(futures):
                    all_data.extend(future.result())

            status.update(label="✅ 분석 완료!", state="complete", expanded=False)

        # 결과 정리 및 출력
        if all_data:
            df = pd.DataFrame(all_data)
            if "일자" in df.columns:
                df["일자"] = pd.to_datetime(df["일자"], errors="coerce").dt.strftime("%Y-%m-%d")
                df = df.dropna(subset=["일자"]).drop_duplicates(subset=["일자"]).sort_values(by="일자")
            df["지점명"] = hotel_name_input
            df = df.fillna(0)

            st.balloons()
            if "일자" in df.columns and not df.empty:
                st.success(f"총 {len(df)}일치 데이터를 추출했습니다! ({df['일자'].min()} ~ {df['일자'].max()})")
            else:
                st.success(f"총 {len(df)}건 데이터를 추출했습니다!")

            st.subheader("📊 데이터 미리보기 (최근 5일)")
            st.dataframe(df.head(5), use_container_width=True)

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)

            st.download_button(
                label="📥 엑셀 리포트 다운로드",
                data=output.getvalue(),
                file_name=f"TripAdvisor_Report_{hotel_name_input}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.error("⚠️ AI가 유효한 데이터를 반환하지 않았습니다. HAR 파일 또는 프롬프트를 확인해 주세요.")
