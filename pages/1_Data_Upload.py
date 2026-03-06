import streamlit as st
import pandas as pd
import io
from datetime import datetime

from utils import (
    preprocess_df,
    extract_table_any_excel,
    load_csv_any_encoding,
    parse_html_tables,
    read_excel_with_smart_header
)

st.set_page_config(page_title="S&OP System - Data Upload", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #EEF2F7; }
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; padding-left: 2rem; padding-right: 2rem; max-width: 100%; }
[data-testid="stSidebar"] { background: #0B1E3F !important; border-right: none; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebarNav"] { padding: 0.5rem; }
[data-testid="stSidebarNav"] a { border-radius: 8px; padding: 0.55rem 0.9rem !important; margin-bottom: 2px; font-size: 0.875rem; font-weight: 500; color: #94A3B8 !important; display: block; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.08) !important; color: #E2E8F0 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(37,99,235,0.3) !important; color: #FFFFFF !important; font-weight: 600; border-left: 3px solid #3B82F6; }
[data-testid="stSidebarNav"] span { color: inherit !important; }
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.9rem 1.1rem; box-shadow: 0 1px 3px rgba(15,23,42,0.04); }
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 800 !important; color: #0F172A !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; font-weight: 600 !important; color: #64748B !important; }
.stButton > button { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 600; font-size: 0.875rem; padding: 0.5rem 1.1rem; transition: background 0.15s; }
.stButton > button:hover { background-color: #1D4ED8; }
[data-testid="stSelectbox"] > div > div { border-radius: 8px; border-color: #CBD5E1; font-size: 0.875rem; }
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: transparent; border-bottom: 2px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] { height: 40px; background: #F8FAFC; border-radius: 8px 8px 0 0; color: #64748B; font-weight: 600; font-size: 0.85rem; padding: 8px 16px; border: 1px solid #E2E8F0; border-bottom: none; }
.stTabs [aria-selected="true"] { background: #FFFFFF !important; color: #2563EB !important; border-bottom: 2px solid #2563EB !important; }
hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.2rem 0; }
h1 { font-size: 1.5rem !important; font-weight: 700 !important; color: #1E293B !important; margin-bottom: 0.3rem !important; }
h2 { font-size: 1.2rem !important; font-weight: 700 !important; color: #1E293B !important; }
h3 { font-size: 1rem !important; font-weight: 700 !important; color: #374151 !important; }
</style>""", unsafe_allow_html=True)

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
# 세션 저장소 초기화 (계층형)
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
def load_file_bytes(file_bytes: bytes, filename: str):
    """
    반환 형태:
    - 단일 시트 → {"파일명": DataFrame}
    - 다중 시트 → {"파일명_시트명": DataFrame, ...}
    """
    lower = filename.lower()
    result = {}

    # =========================
    # CSV (기존 유지)
    # =========================
    if lower.endswith(".csv"):
        df = load_csv_any_encoding(file_bytes)
        df = preprocess_df(df)
        result[filename] = df
        return result

    # =========================
    # Excel (xlsx / xls) ✅ 여기 변경
    # =========================
    if lower.endswith((".xlsx", ".xls")):
        try:
            xls = pd.ExcelFile(io.BytesIO(file_bytes))

            for sheet_name in xls.sheet_names:
                # 🔥 핵심 변경 포인트
                df = read_excel_with_smart_header(
                    file_bytes,
                    sheet_name=sheet_name,
                    scan_rows=80,   # 필요 시 늘려도 됨
                )
                df = preprocess_df(df)

                # 파일명_시트명.xlsx 형태
                base = filename.replace(".xlsx", "").replace(".xls", "")
                new_name = f"{base}_{sheet_name}.xlsx"
                result[new_name] = df

            return result

        except Exception as e:
            # =========================
            # xls + html fallback (기존 유지)
            # =========================
            df = parse_html_tables(file_bytes)
            df = preprocess_df(df)
            result[filename] = df
            return result

    raise ValueError(f"지원하지 않는 파일 형식: {filename}")


# -----------------------------
# 로드 실행 버튼
# -----------------------------
st.write("업로드된 파일을 읽어 DataFrame으로 변환합니다. (브라우저 세션 동안 유지)")

if st.button("✅ 업로드 파일 로드"):
    with st.spinner("파일 로딩 중..."):
        for f in uploaded_files:
            try:
                loaded = load_file_bytes(f.getvalue(), f.name)

                # 🔥 시트별 dict 풀어서 저장
                for new_filename, df in loaded.items():
                    st.session_state["dfs"][target_year][target_month][new_filename] = df

            except Exception as e:
                errors.append((f.name, str(e)))

    if errors:
        st.error("일부 파일 로딩 실패")
        for name, msg in errors:
            st.write(f"- **{name}**: {msg}")
    else:
        st.success("모든 파일 로딩 완료! 이제 다음 페이지로 이동하세요.")

# -----------------------------
# 현재 세션 DF 요약 (3단 계층 반영)
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