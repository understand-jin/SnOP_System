import streamlit as st
import pandas as pd
import io
from datetime import datetime

from utils import (
    preprocess_df,
    extract_table_any_excel,
    load_csv_any_encoding,
    parse_html_tables,
)

st.set_page_config(page_title="S&OP System - Data Upload", layout="wide")
st.title("📥 데이터 업로드")

st.markdown(
    """
- 엑셀(.xlsx / .xls)과 CSV 파일을 업로드하면  
- **표 영역 자동 추출 + 헤더 자동 보정**을 적용하여  
- DataFrame으로 변환 후 세션에 저장합니다.
"""
)



# -----------------------------
# 업로드 UI
# -----------------------------
uploaded_files = st.file_uploader(
    "엑셀/CSV 업로드 (.xlsx / .xls / .csv) — 개수 제한 없음",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

# -----------------------------
# 세션 저장소 초기화
# -----------------------------
# --- 🚀 [추가] 월 선택 UI ---
st.divider() # 시각적 구분선
col1, col2 = st.columns([1, 2])
with col1:
    # 현재 월을 기본값으로 설정 (예: 1월)
    target_month = st.selectbox(
        "📅 데이터 기준 월 선택",
        options=[f"{i}월" for i in range(1, 13)],
        index=datetime.now().month - 1  # 현재 달을 기본값으로
    )
st.caption(f"선택된 **{target_month}** 폴더 안에 데이터가 저장됩니다.")
# ----------------------------

# 1. 먼저 'dfs'라는 큰 가방이 있는지 확인하고 없으면 만듭니다.
if "dfs" not in st.session_state:
    st.session_state["dfs"] = {}

# 2. 'dfs' 가방 안에 선택한 '월' 폴더가 있는지 확인하고 없으면 만듭니다.
if target_month not in st.session_state["dfs"]:
    st.session_state["dfs"][target_month] = {}

if not uploaded_files:
    st.info("파일을 업로드하면, 다음 페이지에서 DF를 확인/시각화할 수 있어요.")
    st.stop()

errors = []

# -----------------------------
# 핵심 로딩 함수
# -----------------------------
@st.cache_data(show_spinner=False)
def load_file_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()

    # CSV
    if lower.endswith(".csv"):
        df = load_csv_any_encoding(file_bytes)
        return preprocess_df(df)

    # XLSX
    if lower.endswith(".xlsx"):
        df = extract_table_any_excel(
            file_bytes,
            filename
        )
        return preprocess_df(df)

    # XLS (정상 + MIME/HTML fallback)
    if lower.endswith(".xls"):
        try:
            df = extract_table_any_excel(
                file_bytes,
                filename
            )
            return preprocess_df(df)
        except Exception:
            df = parse_html_tables(file_bytes)
            return preprocess_df(df)

    raise ValueError(f"지원하지 않는 파일 형식: {filename}")

# -----------------------------
# 로드 실행 버튼
# -----------------------------
st.write("업로드된 파일을 읽어 DataFrame으로 변환합니다. (브라우저 세션 동안 유지)")

if st.button("✅ 업로드 파일 로드"):
    with st.spinner("파일 로딩 중..."):
        for f in uploaded_files:
            try:
                df = load_file_bytes(f.getvalue(), f.name)
                st.session_state["dfs"][target_month][f.name] = df
            except Exception as e:
                errors.append((f.name, str(e)))

    if errors:
        st.error("일부 파일 로딩 실패")
        for name, msg in errors:
            st.write(f"- **{name}**: {msg}")
    else:
        st.success("모든 파일 로딩 완료! 이제 '테이블 관리' 또는 '시각화' 페이지로 이동하세요.")

# -----------------------------
# 현재 세션 DF 요약
# -----------------------------
with st.expander("📦 현재 세션에 저장된 DF 목록", expanded=False):
    all_dfs = st.session_state.get("dfs", {})
    
    if not all_dfs or all(not v for v in all_dfs.values()):
        st.write("아직 저장된 DF가 없습니다.")
    else:
        # 월별로 어떤 파일들이 들어있는지 리스트로 만듭니다.
        summary_data = []
        for month, files in all_dfs.items():
            for filename, df in files.items():
                summary_data.append({
                    "데이터 기준 월": month,
                    "파일명": filename,
                    "행(Rows)": len(df),
                    "열(Cols)": df.shape[1]
                })
        
        if summary_data:
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
