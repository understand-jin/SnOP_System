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
- 엑셀/CSV 파일을 업로드하면 **연도별/월별 폴더**에 데이터를 분류하여 저장합니다.
- 저장 구조: `연도` > `월` > `파일명`
"""
)

# ----------------------------
# 업로드 UI
# -----------------------------
uploaded_files = st.file_uploader(
    "엑셀/CSV 업로드 (.xlsx / .xls / .csv) — 개수 제한 없음",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

# -----------------------------
# 🚀 연도 및 월 선택 UI
# -----------------------------
st.divider()
col1, col2 = st.columns(2)

with col1:
    # 2023년부터 2040년까지 선택 가능
    current_year = datetime.now().year
    target_year = st.selectbox(
        "📅 데이터 기준 연도 선택",
        options=[f"{y}년" for y in range(2023, 2041)],
        index=range(2023, 2041).index(current_year) if current_year in range(2023, 2041) else 0
    )

with col2:
    # 1월부터 12월까지 선택
    current_month = datetime.now().month
    target_month = st.selectbox(
        "📆 데이터 기준 월 선택",
        options=[f"{i}월" for i in range(1, 13)],
        index=current_month - 1
    )

st.info(f"📍 현재 설정: **{target_year} {target_month}** 폴더에 저장됩니다.")
# ----------------------------

# -----------------------------
# [수정] 세션 저장소 초기화 (계층형)
# -----------------------------
if "dfs" not in st.session_state:
    st.session_state["dfs"] = {}

# 연도 폴더 생성
if target_year not in st.session_state["dfs"]:
    st.session_state["dfs"][target_year] = {}

# 월 폴더 생성
if target_month not in st.session_state["dfs"][target_year]:
    st.session_state["dfs"][target_year][target_month] = {}

if not uploaded_files:
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
                st.session_state["dfs"][target_year][target_month][f.name] = df
            except Exception as e:
                errors.append((f.name, str(e)))

    if errors:
        st.error("일부 파일 로딩 실패")
        for name, msg in errors:
            st.write(f"- **{name}**: {msg}")
    else:
        st.success("모든 파일 로딩 완료! 이제 '테이블 관리' 또는 '시각화' 페이지로 이동하세요.")

# -----------------------------
# [수정] 현재 세션 DF 요약 (3단 계층 반영)
# -----------------------------
with st.expander("📦 전체 저장 데이터 내역 확인", expanded=False):
    all_dfs = st.session_state.get("dfs", {})
    
    if not all_dfs:
        st.write("데이터가 없습니다.")
    else:
        summary_data = []
        # 연도 -> 월 -> 파일 순으로 순회
        for year, months in all_dfs.items():
            if isinstance(months, dict):
                for month, files in months.items():
                    if isinstance(files, dict):
                        for filename, df in files.items():
                            summary_data.append({
                                "연도": year,
                                "월": month,
                                "파일명": filename,
                                "Rows": len(df) if hasattr(df, '__len__') else 0,
                                "Cols": df.shape[1] if hasattr(df, 'shape') else 0
                            })
        
        if summary_data:
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)