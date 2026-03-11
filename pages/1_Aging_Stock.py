import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils import (
    preprocess_df,
    load_csv_any_encoding,
    read_excel_with_smart_header,
    parse_html_tables
)
from inventory_utils2 import aging_inventory_preprocess

st.set_page_config(page_title="Aging Inventory Analysis", layout="wide")

###############################################################################
# 🎨 1. UI 스타일링 (Dashboard CSS)
###############################################################################
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #EEF2F7; }
.main .block-container { padding-top: 0 !important; padding-bottom: 2rem; padding-left: 2rem; padding-right: 2rem; max-width: 100%; }
/* 사이드바 */
[data-testid="stSidebar"] { background: #0B1E3F !important; border-right: none; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebarNav"] { padding: 0.5rem; }
[data-testid="stSidebarNav"] a { border-radius: 8px; padding: 0.55rem 0.9rem !important; margin-bottom: 2px; font-size: 0.875rem; font-weight: 500; color: #94A3B8 !important; display: block; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.08) !important; color: #E2E8F0 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(37,99,235,0.3) !important; color: #FFFFFF !important; font-weight: 600; border-left: 3px solid #3B82F6; }
[data-testid="stSidebarNav"] span { color: inherit !important; }
/* 메트릭 */
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.9rem 1.1rem; box-shadow: 0 1px 3px rgba(15,23,42,0.04); }
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 800 !important; color: #0F172A !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; font-weight: 600 !important; color: #64748B !important; }
/* 탭 */
.stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: transparent; border-bottom: 2px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] { height: 40px; background: #F8FAFC; border-radius: 8px 8px 0 0; color: #64748B; font-weight: 600; font-size: 0.85rem; padding: 8px 16px; border: 1px solid #E2E8F0; border-bottom: none; }
.stTabs [aria-selected="true"] { background: #FFFFFF !important; color: #2563EB !important; border-bottom: 2px solid #2563EB !important; }
/* 버튼 */
.stButton > button { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 600; font-size: 0.875rem; padding: 0.5rem 1.1rem; transition: background 0.15s; }
.stButton > button:hover { background-color: #1D4ED8; }
/* 헤더 배너 */
.dash-header { background: linear-gradient(135deg, #0B1E3F 0%, #1565C0 100%); margin: -1px -2rem 2rem -2rem; padding: 1.2rem 2.5rem; display: flex; align-items: center; justify-content: space-between; }
.dash-header-left { display: flex; align-items: center; gap: 14px; }
.dash-header-icon { width: 40px; height: 40px; background: rgba(255,255,255,0.15); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
.dash-header-title { color: #FFFFFF; font-size: 1.25rem; font-weight: 700; }
.dash-header-sub { color: #93C5FD; font-size: 0.75rem; margin-top: 2px; }
.dash-badge { background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2); color: #E0F2FE; font-size: 0.72rem; font-weight: 500; padding: 0.3rem 0.75rem; border-radius: 20px; }
.dash-badge-warn { background: rgba(251,191,36,0.2); border: 1px solid rgba(251,191,36,0.4); color: #FDE68A; }
/* 섹션 라벨 */
.section-label { font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.6rem; padding-left: 2px; }
/* 업로드 영역 */
.upload-label { font-weight: 700; color: #1E293B; font-size: 0.8rem; margin-bottom: 4px; }
.upload-section { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px; margin-bottom: 8px; }
/* 카드 */
.info-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(15,23,42,0.04); margin-bottom: 0.8rem; }
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #E2E8F0; }
hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.2rem 0; }
h1, h2, h3 { color: #1E293B !important; }
</style>
""", unsafe_allow_html=True)

# 헤더 배너
st.markdown("""
<div class="dash-header">
    <div>
        <div class="dash-header-title">Aging Inventory Analysis</div>
        <div class="dash-header-sub">부진재고 전처리 · FEFO 시뮬레이션 · 소진계획 수립</div>
    </div>
    <div style="display:flex;gap:8px;">
        <span class="dash-badge">FEFO</span>
        <span class="dash-badge dash-badge-warn">Binary Search</span>
    </div>
</div>

""", unsafe_allow_html=True)

###############################################################################
# 📅 2. 연도 및 월 선택 / 업로드 설정
###############################################################################
st.markdown('<div class="section-label">분석 기간 설정</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns([2, 2, 4])
with c1:
    current_year = datetime.now().year
    target_year = st.selectbox("연도", options=[f"{y}년" for y in range(2023, 2041)], index=range(2023, 2041).index(current_year) if current_year in range(2023, 2041) else 0)
with c2:
    current_month = datetime.now().month
    target_month = st.selectbox("월", options=[f"{i}월" for i in range(1, 13)], index=current_month - 1)

import os
target_dir = os.path.join("data", target_year, target_month)
file_std = os.path.join(target_dir, "inventory.csv")
file_sim = os.path.join(target_dir, "simulation.csv")
file_res = os.path.join(target_dir, "forecasted_inventory.csv")

# --- 캐싱된 데이터 불러오기 ---
if os.path.exists(file_std) and os.path.exists(file_sim) and os.path.exists(file_res):
    st.info(f"{target_year} {target_month}에 저장된 시뮬레이션 결과가 있어서 데이터를 자동으로 불러왔습니다.")
    try:
        if "aging_result_df" not in st.session_state or st.session_state["aging_result_df"] is None or not st.session_state.get("sim_result"):
            with st.spinner("저장된 데이터를 불러오는 중..."):
                st.session_state["aging_result_df"] = pd.read_csv(file_std)
                dt_df = pd.read_csv(file_sim)
                upd_df = pd.read_csv(file_res)
                st.session_state["sim_result"] = {"detail": dt_df, "updated": upd_df}
                st.rerun() # UI 업데이트를 위한 새로고침
    except Exception as e:
        st.warning(f"저장된 파일을 불러오는 데 실패했습니다: {e}")
        st.session_state["sim_result"] = None

# ✅ 분석에 필요한 상수 및 설정
STD_KEY = "standard_df"
COST_KEY = "cost_df"
EXP_KEY = "expiration_df"
SAL_KEY = "sales_df"
CLS_KEY = "cls_df"

INPUT_DATA_BASE = "input_data"
INPUT_DATA_ITEMS = [
    {"label": "재고개요",       "key": STD_KEY,  "folder": "재고개요"},
    {"label": "자재수불부",     "key": COST_KEY, "folder": "자재수불부"},
    {"label": "배치별유효기한", "key": EXP_KEY,  "folder": "배치별유효기한"},
    {"label": "3개월매출",      "key": SAL_KEY,  "folder": "3개월매출"},
    {"label": "대분류_소분류",  "key": CLS_KEY,  "folder": "대분류_소분류"},
]

import glob as _glob

def get_latest_file(folder_path):
    """폴더에서 가장 최근 수정된 Excel/CSV 파일 경로 반환"""
    files = []
    for pat in ("*.xlsx", "*.xls", "*.csv"):
        files.extend(_glob.glob(os.path.join(folder_path, pat)))
    return max(files, key=os.path.getmtime) if files else None

# --- 파일 현황 표시 (5개 필수 + 품절예상조회) ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="section-label">입력 데이터 현황 (input_data)</div>', unsafe_allow_html=True)

ALL_DISPLAY_ITEMS = INPUT_DATA_ITEMS + [
    {"label": "품절예상조회", "key": "stockout_df", "folder": "품절예상조회"},
]

status_cols = st.columns(len(ALL_DISPLAY_ITEMS))
all_files_found = True
found_files = {}
for i, item in enumerate(ALL_DISPLAY_ITEMS):
    folder = os.path.join(INPUT_DATA_BASE, item["folder"])
    fpath = get_latest_file(folder)
    with status_cols[i]:
        if fpath:
            fname = os.path.basename(fpath)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%m/%d %H:%M")
            st.markdown(
                f'<div class="upload-section">'
                f'<div class="upload-label">{item["label"]}</div>'
                f'<div style="font-size:0.75rem;color:#16A34A;font-weight:600;">확인</div>'
                f'<div style="font-size:0.7rem;color:#64748B;margin-top:2px;word-break:break-all;">{fname}</div>'
                f'<div style="font-size:0.68rem;color:#94A3B8;">{mtime}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            found_files[item["key"]] = fpath
        else:
            if item["key"] != "stockout_df":
                all_files_found = False
            st.markdown(
                f'<div class="upload-section" style="border-color:{"#FCA5A5" if item["key"] != "stockout_df" else "#FCD34D"};">'
                f'<div class="upload-label">{item["label"]}</div>'
                f'<div style="font-size:0.75rem;color:{"#DC2626" if item["key"] != "stockout_df" else "#92400E"};font-weight:600;">파일 없음</div>'
                f'<div style="font-size:0.7rem;color:#94A3B8;">{folder}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

if not all_files_found:
    st.warning(f"필수 파일이 없습니다. `{INPUT_DATA_BASE}/{{폴더명}}/` 경로를 확인하세요.")

# 품절예상조회 세션 저장
if "stockout_df" in found_files:
    try:
        _sp = found_files["stockout_df"]
        with open(_sp, "rb") as _sf:
            _sf_bytes = _sf.read()
        sf_df = load_csv_any_encoding(_sf_bytes) if _sp.lower().endswith(".csv") else read_excel_with_smart_header(_sf_bytes, scan_rows=80)
        if "stockout_forecast" not in st.session_state:
            st.session_state["stockout_forecast"] = {}
        st.session_state["stockout_forecast"][datetime.fromtimestamp(os.path.getmtime(_sp)).strftime("%Y-%m-%d")] = sf_df
    except Exception:
        pass

st.markdown("<hr>", unsafe_allow_html=True)

# --- 저장 및 미리보기 로직 ---
if "dfs" not in st.session_state: st.session_state["dfs"] = {}
if target_year not in st.session_state["dfs"]: st.session_state["dfs"][target_year] = {}
if target_month not in st.session_state["dfs"][target_year]: st.session_state["dfs"][target_year][target_month] = {}

###############################################################################
# ⚙️ 3. 데이터 저장 및 전처리 로직
###############################################################################

@st.cache_data(show_spinner=False)
def process_file(file_bytes, filename):
    if filename.lower().endswith(".csv"):
        return preprocess_df(load_csv_any_encoding(file_bytes))
    try:
        return preprocess_df(read_excel_with_smart_header(file_bytes, scan_rows=80))
    except:
        return preprocess_df(parse_html_tables(file_bytes))

if st.button("데이터 전처리 및 시뮬레이션 실행", use_container_width=True, type="primary"):
    if len(found_files) < 5:
        st.error(f"5개 파일이 모두 있어야 합니다. 현재 {len(found_files)}개만 확인됨.")
    else:
        with st.spinner("데이터 처리 중..."):
            for item in INPUT_DATA_ITEMS:
                fpath = found_files[item["key"]]
                with open(fpath, "rb") as _f:
                    st.session_state["dfs"][target_year][target_month][item["key"]] = process_file(_f.read(), fpath)
            
            target_dfs = st.session_state["dfs"][target_year][target_month]
            try:
                from inventory_utils2 import aging_inventory_preprocess
                
                final_df = aging_inventory_preprocess(
                    **target_dfs,
                    year_str=target_year,
                    month_str=target_month
                )

                st.text(f"{target_year} {target_month} 전처리 완료! ({len(final_df):,}행)")
                
                # --- 2. 시뮬레이션 연속 실행 ---
                st.text("FEFO 시뮬레이션을 수행 중입니다...")
                from inventory_utils2 import simulate_batches_by_product, binary_search
                detail_df, updated_df = simulate_batches_by_product(final_df)
                
                # --- 3. 이진 탐색 (판매개선율 산출) ---
                st.text("최적 판매개선율 탐색 연산 중입니다... (약 1분 소요)")
                updated_df = binary_search(final_df, updated_df)
                
                # --- 4. 파일 자동 저장 ---
                os.makedirs(target_dir, exist_ok=True)
                final_df.to_csv(file_std, index=False, encoding="utf-8-sig")
                detail_df.to_csv(file_sim, index=False, encoding="utf-8-sig")
                updated_df.to_csv(file_res, index=False, encoding="utf-8-sig")
                
                # 세션 반영
                st.session_state["aging_result_df"] = final_df
                st.session_state["sim_result"] = {"detail": detail_df, "updated": updated_df}
                
                st.success(f"전처리부터 시뮬레이션, 결과 자동 저장까지 한 번에 완료되었습니다! (배치 {len(detail_df):,}건)")
                
            except Exception as e:
                st.error(f"처리 중 오류 발생: {e}")
                import traceback
                st.expander("에러 상세 내용").code(traceback.format_exc())

st.markdown("<hr>", unsafe_allow_html=True)

###############################################################################
# 📊 4. 기간별 부진재고 리스크 현황 (시뮬레이션 결과 전)
###############################################################################

if st.session_state.get("aging_result_df") is not None:
    st.markdown('<div class="section-label">분석 대상 자재 리스크 현황 (As-Is)</div>', unsafe_allow_html=True)
    st.markdown("### 부진재고 리스크 현황")
    risk_df = st.session_state["aging_result_df"].copy()
    
    # 1) 기초 버킷 설정
    EXPIRY_COL = "유효기한"
    DAYS_COL = "남은일"
    BUCKET_COL = "유효기한구간"
    VALUE_COL = "기말금액"
    QTY_SRC_COL = "기말수량"
    SALES_COL = "3평판"
    MAT_COL = "자재코드"
    MAT_NAME_COL = "자재내역"
    
    today = pd.Timestamp.today().normalize()
    risk_df[EXPIRY_COL] = pd.to_datetime(risk_df[EXPIRY_COL], errors="coerce")
    if DAYS_COL not in risk_df.columns:
        risk_df[DAYS_COL] = (risk_df[EXPIRY_COL] - today).dt.days

    def to_bucket(days):
        if pd.isna(days): return "유효기한 없음"
        if days < 0: return "폐기확정(유효기한 지남)"
        if days < 30: return "1개월 미만"
        if days < 60: return "2개월 미만"
        if days < 90: return "3개월 미만"
        if days < 120: return "4개월 미만"
        if days < 150: return "5개월 미만"
        if days < 180: return "6개월 미만"
        if days < 210: return "7개월 미만"
        if days < 240: return "8개월 미만"
        if days < 270: return "9개월 미만"
        if days < 300: return "10개월 미만"
        if days < 330: return "11개월 미만"
        if days < 365: return "12개월 미만"
        return "12개월 이상"

    risk_df[BUCKET_COL] = risk_df[DAYS_COL].apply(to_bucket)

    # 2) UI 탭 설정 및 표시 함수 정의
    tab6, tab7, tab9, tab12 = st.tabs(["6개월 미만", "7개월 미만", "9개월 미만", "12개월 미만"])

    def display_risk_summary(target_buckets, tab_obj, title):
        with tab_obj:
            sub_df = risk_df[risk_df[BUCKET_COL].isin(target_buckets)].copy()
            if sub_df.empty:
                st.success(f"{title} 내에 해당하는 자재/배치가 없습니다.")
                return

            agg_cols = {
                QTY_SRC_COL: "sum",
                VALUE_COL: "sum",
                DAYS_COL: "min",
                EXPIRY_COL: "min",
                SALES_COL: "first",
                BUCKET_COL: "first",
            }
            # Add other columns if they exist in the dataframe to match standard_df broadly
            other_cols = ["플랜트", "특별재고", "저장위치", "단가", "대분류", "소분류"]
            for col in other_cols:
                if col in sub_df.columns:
                    agg_cols[col] = "first"

            summary = (
                sub_df.groupby([MAT_COL, MAT_NAME_COL, "배치"], dropna=False)
                .agg(agg_cols)
                .reset_index()
                .sort_values([DAYS_COL, VALUE_COL], ascending=[True, False])
            )

            c1, c2 = st.columns(2)
            c1.metric(f"{title} 대상 배치 수", f"{summary['배치'].nunique()}개")
            c2.metric("총 위험 재고 금액", f"₩{summary[VALUE_COL].sum():,.0f}")

            disp = summary.copy()
            disp[EXPIRY_COL] = pd.to_datetime(disp[EXPIRY_COL], errors="coerce").dt.strftime("%Y-%m-%d")
            disp[VALUE_COL] = disp[VALUE_COL].map(lambda x: f"{x:,.0f}")
            disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map(lambda x: f"{x:,.0f}")
            if "단가" in disp.columns:
                disp["단가"] = disp["단가"].map(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            disp[SALES_COL] = disp[SALES_COL].map(lambda x: f"{x:,.0f}" if pd.notna(x) else "")

            # The exact standard_df columns
            ordered_cols = [
                "자재코드", "자재내역", "플랜트", "특별재고", "저장위치", "배치", 
                "기말수량", "기말금액", "단가", "대분류", "소분류", 
                "유효기한", "남은일", "유효기한구간", "3평판"
            ]
            show_cols = [c for c in ordered_cols if c in disp.columns]
            
            styled_disp = disp[show_cols].style.set_properties(**{'font-weight': 'bold'})
            
            def highlight_columns(x):
                df = x.copy()
                df.loc[:, :] = ''
                for col in ['유효기한구간', '유효기한', '기말금액']:
                    if col in df.columns:
                        df.loc[:, col] = 'background-color: #fff3e0'
                return df
                
            styled_disp = styled_disp.apply(highlight_columns, axis=None)
            st.dataframe(styled_disp, use_container_width=True, height=600)

    # 3) 탭 표출 실행
    risk_base = ["폐기확정(유효기한 지남)", "1개월 미만", "2개월 미만", "3개월 미만", "4개월 미만", "5개월 미만"]
    display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
    display_risk_summary(["7개월 미만"], tab7, "7개월 미만")
    display_risk_summary(["8개월 미만", "9개월 미만"], tab9, "9개월 미만")
    display_risk_summary(["10개월 미만", "11개월 미만", "12개월 미만"], tab12, "12개월 미만")

    st.markdown("<hr>", unsafe_allow_html=True)
    
    # 4) 중점관리 대상 품목 표출 로직
    try:
        from inventory_utils2 import picking_major_management_inventory

        st.markdown('<div class="section-label">중점관리 대상 품목</div>', unsafe_allow_html=True)
        st.markdown("### 중점관리 대상 품목 현황")

        with st.spinner("중점관리 대상 품목을 분석하고 있습니다..."):
            major_management_df = picking_major_management_inventory(risk_df)

        if major_management_df is not None and not major_management_df.empty:
            # 자동 저장
            os.makedirs(target_dir, exist_ok=True)
            _major_path = os.path.join(target_dir, "major_management_inventory.csv")
            major_management_df.to_csv(_major_path, index=False, encoding="utf-8-sig")

            # 주요 컬럼 순서 정리 후 표시
            _ordered = ["자재코드", "자재내역", "대분류", "소분류", "배치",
                        "기말수량", "기말금액", "단가", "3평판",
                        "예측부진재고", "예측부진재고금액",
                        "유효기한", "남은일", "유효기한구간"]
            _show_cols = [c for c in _ordered if c in major_management_df.columns]
            # 정의되지 않은 나머지 컬럼도 뒤에 추가
            _extra = [c for c in major_management_df.columns if c not in _show_cols]
            disp_major = major_management_df[_show_cols + _extra].copy()

            # 숫자 컬럼 포맷
            def _hl_major(s):
                styles = pd.DataFrame("", index=s.index, columns=s.columns)
                for col in ["예측부진재고", "예측부진재고금액"]:
                    if col in styles.columns:
                        styles[col] = "background-color:#FEE2E2; color:#991B1B; font-weight:bold;"
                return styles

            st.dataframe(
                disp_major.reset_index(drop=True).style.apply(_hl_major, axis=None),
                use_container_width=True
            )


            col_dl, col_nav = st.columns([2, 1])
            with col_dl:
                csv_major = major_management_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    label="중점관리 대상 품목 다운로드 (CSV)",
                    data=csv_major,
                    file_name="major_management_inventory.csv",
                    mime="text/csv"
                )
            with col_nav:
                # 소진계획 입력 페이지에 필요한 데이터 session state에 저장
                st.session_state["major_management_df"] = major_management_df
                st.session_state["plan_target_dir"] = target_dir
                st.session_state["plan_target_year"] = target_year
                st.session_state["plan_target_month"] = target_month
                if st.button("소진계획 입력 →", type="primary", use_container_width=True):
                    st.switch_page("pages/2_Depletion_Plan.py")
        else:
            st.info("중점관리 대상으로 선정된 품목이 없습니다.")
    except ImportError:
        st.error("inventory_utils2 모듈에서 'picking_major_management_inventory' 함수를 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"중점관리 대상 품목 분석 중 오류가 발생했습니다: {e}")
        import traceback
        st.expander("에러 상세").code(traceback.format_exc())

    # 5) 소진율 현황 표출 (소진계획.csv × 품절예상조회)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">소진계획 대비 실적</div>', unsafe_allow_html=True)
    st.markdown("### 소진율 현황")

    try:
        from inventory_utils2 import depletion_rate as _depletion_rate

        plan_csv_path = os.path.join(target_dir, "소진계획.csv")
        stockout_folder = os.path.join(INPUT_DATA_BASE, "품절예상조회")
        stockout_fpath = get_latest_file(stockout_folder) if callable(get_latest_file) else None

        _plan_ok = os.path.exists(plan_csv_path)
        _stock_ok = stockout_fpath is not None and os.path.exists(stockout_fpath)

        c_s1, c_s2 = st.columns(2)
        c_s1.markdown(
            f'<div style="font-size:0.78rem;color:{"#16A34A" if _plan_ok else "#DC2626"};">'
            f'소진계획.csv: {"있음" if _plan_ok else "없음 — 소진계획 입력 후 저장 필요"}'
            f'</div>', unsafe_allow_html=True
        )
        c_s2.markdown(
            f'<div style="font-size:0.78rem;color:{"#16A34A" if _stock_ok else "#DC2626"};">'
            f'품절예상조회 파일: {"있음 (" + os.path.basename(stockout_fpath) + ")" if _stock_ok else "없음 — input_data/품절예상조회/ 폴더에 파일 필요"}'
            f'</div>', unsafe_allow_html=True
        )


        if _plan_ok and _stock_ok:
            df1_plan = pd.read_csv(plan_csv_path, encoding="utf-8-sig")
            with open(stockout_fpath, "rb") as _sf:
                _sf_bytes = _sf.read()
            if stockout_fpath.lower().endswith(".csv"):
                df2_stock = load_csv_any_encoding(_sf_bytes)
            else:
                df2_stock = read_excel_with_smart_header(_sf_bytes, scan_rows=80)

            with st.spinner("소진율 계산 중..."):
                rate_df = _depletion_rate(df1_plan, df2_stock)

            if rate_df is not None and not rate_df.empty:
                current_month_col = f"{pd.Timestamp.today().month}월"

                # 자재코드 단위로 집계
                chart_df = rate_df.copy()
                chart_df[current_month_col] = pd.to_numeric(chart_df.get(current_month_col, 0), errors="coerce").fillna(0)
                chart_df["당월출하"] = pd.to_numeric(chart_df.get("당월출하", 0), errors="coerce").fillna(0)

                agg_chart = (
                    chart_df.groupby(["자재코드", "자재내역"], as_index=False)
                    .agg({current_month_col: "sum", "당월출하": "sum"})
                )
                agg_chart["소진율_num"] = agg_chart.apply(
                    lambda r: r["당월출하"] / r[current_month_col] if r[current_month_col] > 0 else 0, axis=1
                )
                agg_chart["소진율_pct"] = (agg_chart["소진율_num"] * 100).round(1)

                # 요약 메트릭 (상단)
                mc1, mc2, mc3, mc4 = st.columns(4)
                total_plan   = agg_chart[current_month_col].sum()
                total_actual = agg_chart["당월출하"].sum()
                avg_rate     = total_actual / total_plan if total_plan > 0 else 0
                cnt_done     = (agg_chart["소진율_pct"] >= 100).sum()
                mc1.metric("이번 달 소진계획 합계",  f"{total_plan:,.0f}")
                mc2.metric("이번 달 실제 출하 합계", f"{total_actual:,.0f}")
                mc3.metric("전체 평균 소진율",        f"{avg_rate:.1%}")
                mc4.metric("계획 달성 자재수",        f"{cnt_done} / {len(agg_chart)} 종")

                st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

                # ── 카드형 소진율 바 렌더링 ──────────────────────────────
                # 소진율 낮은 순(부진 우선)으로 정렬
                agg_sorted = agg_chart.sort_values("소진율_pct", ascending=True).reset_index(drop=True)

                import textwrap

                def _make_no_plan_card(name, actual):
                    return (
                        f'<div style="background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:12px;'
                        f'padding:14px 18px;margin-bottom:0;opacity:0.75;">'
                        f'<div style="font-size:0.85rem;font-weight:700;color:#94A3B8;margin-bottom:6px;'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>'
                        f'<div style="background:#E2E8F0;border-radius:999px;height:18px;"></div>'
                        f'<div style="display:flex;justify-content:space-between;margin-top:5px;">'
                        f'<span style="font-size:0.72rem;color:#94A3B8;">당월 출하: <strong>{actual:,.0f}</strong></span>'
                        f'<span style="font-size:0.72rem;color:#94A3B8;font-weight:600;">계획 미입력</span>'
                        f'</div></div>'
                    )

                def _make_card(name, actual, plan, fill, bar_color, status_lbl, status_clr, rate_pct):
                    return (
                        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;'
                        f'padding:14px 18px;margin-bottom:0;box-shadow:0 1px 4px rgba(15,23,42,0.05);">'
                        f'<div style="font-size:0.85rem;font-weight:700;color:#1E293B;margin-bottom:8px;'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>'
                        f'<div style="position:relative;background:#F1F5F9;border-radius:999px;height:20px;overflow:hidden;">'
                        f'<div style="position:absolute;left:0;top:0;height:100%;width:{fill:.2f}%;'
                        f'background:{bar_color};border-radius:999px;"></div></div>'
                        f'<div style="display:flex;justify-content:space-between;margin-top:5px;">'
                        f'<span style="font-size:0.72rem;color:#64748B;">'
                        f'당월: <strong style="color:#1E293B;">{actual:,.0f}</strong>'
                        f'&nbsp;/&nbsp;계획: <strong style="color:#1E293B;">{plan:,.0f}</strong></span>'
                        f'<span style="font-size:0.76rem;font-weight:700;color:{status_clr};">'
                        f'{status_lbl} {rate_pct:.1f}%</span></div></div>'
                    )

                normal_cards = []
                no_plan_cards = []
                for _, r in agg_sorted.iterrows():
                    mat_name   = r["자재내역"]
                    plan_val   = r[current_month_col]
                    actual_val = r["당월출하"]
                    rate_pct   = r["소진율_pct"]

                    if plan_val == 0:
                        no_plan_cards.append(_make_no_plan_card(mat_name, actual_val))
                        continue

                    is_over    = rate_pct >= 100
                    bar_color  = "#22C55E" if is_over else "#EF4444"
                    status_lbl = "초과" if is_over else "부진"
                    status_clr = "#059669" if is_over else "#DC2626"
                    fill_pct   = min(rate_pct, 100)   # 끝 = 100%

                    normal_cards.append(_make_card(mat_name, actual_val, plan_val,
                                                   fill_pct, bar_color, status_lbl, status_clr, rate_pct))

                # 2열 CSS grid로 렌더링
                grid_items = "".join(c for c in normal_cards)
                html_out = (
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">'
                    f'{grid_items}</div>'
                )
                if no_plan_cards:
                    np_items = "".join(c for c in no_plan_cards)
                    html_out += (
                        f'<details><summary style="cursor:pointer;font-size:0.82rem;color:#94A3B8;'
                        f'margin-bottom:8px;">계획 미입력 자재 ({len(no_plan_cards)}종) 보기</summary>'
                        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px;">'
                        f'{np_items}</div></details>'
                    )

                st.markdown(html_out, unsafe_allow_html=True)





            else:
                st.info("소진율을 계산할 데이터가 없습니다. 소진계획 파일에 이번 달 계획 수량을 입력해주세요.")
        else:
            st.info("소진계획.csv와 품절예상조회 파일이 모두 있어야 소진율을 계산할 수 있습니다.")
    except Exception as e:
        st.error(f"소진율 계산 중 오류가 발생했습니다: {e}")
        import traceback
        st.expander("에러 상세 (소진율)").code(traceback.format_exc())

st.markdown("<hr>", unsafe_allow_html=True)


###############################################################################
# 🧪 5. 데이터 시뮬레이션 및 종합 분석 결과
###############################################################################

if not st.session_state.get("sim_result"):
    st.info("위의 '데이터 전처리 및 시뮬레이션 실행'을 진행하거나 저장된 데이터를 불러오세요.")
else:
    # 결과 표시
    detail_df = st.session_state["sim_result"]["detail"]
    updated_df = st.session_state["sim_result"]["updated"]

    st.markdown('<div class="section-label">FEFO 시뮬레이션 결과</div>', unsafe_allow_html=True)
    st.markdown("### 시뮬레이션 후 잔량 (updated)")
    st.info("FEFO 소진 후 잔량이 반영된 재고 (금액 높은 순 정렬)")

    # ─── 그룹화 및 컬럼 정리 ───────────────────────────────────────────
    agg_rules = {
        "기말수량": "sum", "기말금액": "sum",
        "3평판": "first", "예측부진재고": "first", "예측부진재고금액": "first",
        "판매개선율": "first", "권장판매량": "first",
        "유효기한": "first", "유효 기한": "first", "남은일": "first", "유효기한구간": "first",
        "대분류": "first", "소분류": "first", "단가": "first", "자재내역": "first"
    }
    valid_agg = {k: v for k, v in agg_rules.items() if k in updated_df.columns}
    
    grouped_upd = updated_df.groupby(["자재코드", "배치"], dropna=False).agg(valid_agg).reset_index()
    
    # 지정된 순서로 컬럼 재배치
    ordered_cols = [
        "자재코드", "자재내역", "배치", "기말수량", "기말금액", 
        "3평판", "예측부진재고", "예측부진재고금액", "판매개선율", "권장판매량", 
        "유효기한", "유효 기한", "남은일", "유효기한구간", "대분류", "소분류", "단가"
    ]
    final_cols = [c for c in ordered_cols if c in grouped_upd.columns]
    
    # 없는 나머지 컬럼들도 뒤에 붙여줌
    remain_cols = [c for c in grouped_upd.columns if c not in final_cols]
    grouped_upd = grouped_upd[final_cols + remain_cols]

    if "예측부진재고금액" in grouped_upd.columns:
        grouped_upd = grouped_upd.sort_values("예측부진재고금액", ascending=False)
    # ────────────────────────────────────────────────────────────
    
    # 요약
    u1, u2, u3 = st.columns(3)
    u1.metric("전체 행 수", f"{len(grouped_upd):,}")
    u2.metric("잔량 > 0 배치", f"{(grouped_upd['예측부진재고'] > 0).sum():,}")
    u3.metric("완전 소진 배치", f"{(grouped_upd['예측부진재고'] <= 0).sum():,}")
    
    # 잔량 필터
    show_nonzero = st.checkbox("잔량 > 0 만 보기", value=False, key="updated_nonzero")
    view_upd = grouped_upd[grouped_upd["예측부진재고"] > 0] if show_nonzero else grouped_upd
    
    # 색상 강조 로직
    def highlight_cols(s):
        styles = pd.DataFrame('', index=s.index, columns=s.columns)
        for col in ["예측부진재고", "예측부진재고금액"]:
            if col in styles.columns: styles[col] = "background-color: #ffebee; color: #b71c1c; font-weight: bold;"
        for col in ["판매개선율", "권장판매량"]:
            if col in styles.columns: styles[col] = "background-color: #e8f5e9; color: #1b5e20; font-weight: bold;"
        return styles

    styled_upd = view_upd.reset_index(drop=True).style.apply(highlight_cols, axis=None)
    
    st.dataframe(styled_upd, use_container_width=True, height=450)
    
    # 다운로드
    col1, col2 = st.columns(2)
    with col1:
        csv_detail = detail_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("detail 다운로드 (CSV)", csv_detail, "detail_df.csv", "text/csv")
    with col2:
        csv_updated = updated_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("updated 다운로드 (CSV)", csv_updated, "updated_df.csv", "text/csv")

st.markdown("<hr>", unsafe_allow_html=True)

###############################################################################
# 🔍 5. 자재코드별 시뮬레이션 흐름 시각화 (개별 상세 조회)
###############################################################################

if not st.session_state.get("sim_result"):
    st.info("위의 '데이터 전처리 및 시뮬레이션 실행'을 진행하거나 저장된 데이터를 불러오세요.")
else:
    import plotly.graph_objects as go
    from datetime import date as _date

    _detail = st.session_state["sim_result"]["detail"]
    _upd = st.session_state["sim_result"]["updated"]
    today_date = _date.today()

    # --- [추가] 고가치 리스크 자재 (중복 제거) Top 10 버튼 ---
    if "예측부진재고금액" in _upd.columns:
        # 금액순 정렬 후 자재코드 중복 제거 (표 상단의 단일 배치 금액과 동일하게 표시)
        top_mats = (
            _upd[_upd["예측부진재고"] > 0]
            .sort_values("예측부진재고금액", ascending=False)
            .drop_duplicates(subset=["자재코드"])
            .head(10).reset_index(drop=True)
        )
        if not top_mats.empty:
            st.write(" ") # 약간의 간격
            btn_cols = st.columns(5)
            for idx, row in top_mats.iterrows():
                m_code = str(row["자재코드"])
                full_amt = f"{row['예측부진재고금액']:,.0f}"
                if btn_cols[idx % 5].button(f"{m_code}\n({full_amt})", key=f"btn_v3_{m_code}_{idx}", use_container_width=True):
                    st.session_state["viz_mat_code"] = m_code
                    st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True) # 버튼 섹션과 입력창 구분선
    # ------------------------------------------------------

    mat_input = st.text_input("자재코드 입력", value="9308335", key="viz_mat_code")
    sub = _detail[_detail["자재코드"].astype(str) == str(mat_input).strip()]

    if sub.empty:
        st.warning(f"**{mat_input}** 에 해당하는 시뮬레이션 결과가 없습니다.")
    else:
        mat_name = sub["자재내역"].iloc[0] if "자재내역" in sub.columns else ""
        st.caption(f"자재코드: **{mat_input}** | {mat_name} | 배치 **{len(sub)}개**")

        import plotly.express as px

        sub_v = sub.copy()
        today_ts = pd.Timestamp.today().normalize()

        for c in ["sell_start_date", "sell_end_date", "risk_entry_date"]:
            if c in sub_v.columns:
                sub_v[c] = pd.to_datetime(sub_v[c], errors="coerce")

        sub_v["expiry_date"]  = today_ts + pd.to_timedelta(sub_v["init_days"], unit="D")
        sub_v["batch_label"]  = sub_v["배치"].astype(str)
        sub_v["_no_sell"]     = sub_v["stop_reason"].isin({"risk_reached_before_start", "no_sales"})
        sub_v["_sell_end_ts"] = pd.to_datetime(sub_v["sell_end_date"], errors="coerce")

        # 판매기간 바
        sales_bar = sub_v.dropna(subset=["sell_start_date", "sell_end_date"]).copy()
        sales_bar = sales_bar[sales_bar["sell_start_date"] != sales_bar["sell_end_date"]]
        sales_bar["phase"] = "판매기간"
        sales_bar["bar_text"] = ""
        sales_bar = sales_bar.rename(columns={"sell_start_date": "x_start", "sell_end_date": "x_end"})

        # 부진재고 구간 바 (risk_entry_date -> expiry_date)
        slug_bar = sub_v[sub_v["remaining_qty"].fillna(0) > 0].copy()
        slug_bar = slug_bar.rename(columns={"remaining_qty": "예측부진재고"})
        slug_bar = slug_bar.dropna(subset=["risk_entry_date", "expiry_date"])
        slug_bar["phase"] = "부진재고 구간"
        slug_bar["bar_text"] = slug_bar["예측부진재고"].apply(lambda v: f"{v:,.0f}" if pd.notna(v) and v > 0 else "")
        slug_bar = slug_bar.rename(columns={"risk_entry_date": "x_start", "expiry_date": "x_end"})

        plot_df = pd.concat([sales_bar, slug_bar], ignore_index=True)

        # y축 순서: sell_start 오름차순 -> slug-only 배치 아래
        order_base = (
            sales_bar[["batch_label", "x_start"]].drop_duplicates("batch_label")
            .sort_values(["x_start", "batch_label"])
        )
        y_order = order_base["batch_label"].tolist()
        for lbl in slug_bar["batch_label"].unique():
            if lbl not in y_order:
                y_order.append(lbl)

        if plot_df.empty:
            st.info("표시할 판매 구간이 없습니다.")
        else:
            fig = px.timeline(
                plot_df,
                x_start="x_start", x_end="x_end", y="batch_label", color="phase", text="bar_text",
                color_discrete_map={"판매기간": "#4C78A8", "부진재고 구간": "#E45756"},
                hover_data={
                    "bar_text": False,
                    "자재코드": True, "자재내역": True, "배치": True,
                    "예측부진재고": True, "risk_entry_date": True, "expiry_date": True,
                },
            )
            fig.update_traces(
                textposition="inside",
                textfont=dict(color="white", size=11, family="Arial Black"),
                marker_line_color="white", marker_line_width=1, opacity=0.9
            )
            fig.update_yaxes(categoryorder="array", categoryarray=y_order, autorange="reversed")
            dynamic_height = max(180, len(y_order) * 35 + 130)
            fig.update_layout(
                height=dynamic_height,
                margin=dict(t=50, b=50, l=10, r=10),
                xaxis_title="Simulation Timeline",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9", dtick="M1", tickformat="%Y-%m")
            fig.update_traces(marker_line_color="white", marker_line_width=1, opacity=0.9)
            st.plotly_chart(fig, use_container_width=True)

        # ── 수량 바차트 ────────────────────────────────────────────────
        sub_v_ren = sub_v.rename(columns={"remaining_qty": "예측부진재고"})

        # ── 상세 테이블 ─────────────────────────────────────────────────
        cols_show = ["배치", "init_qty", "init_days", "risk_entry_date",
                     "sell_start_date", "sell_end_date", "qty_sold",
                     "예측부진재고", "days_left_at_stop", "stop_reason"]
        
        # 테이블: sell_end_date 오름차순, 판매 없는 배치 맨 아래 (init_qty > 0 필터링)
        disp = sub_v_ren.copy()
        if "init_qty" in disp.columns:
            disp = disp[disp["init_qty"] > 0]
            
        disp = pd.concat([
            disp[~disp["_no_sell"]].sort_values("_sell_end_ts", ascending=True),
            disp[disp["_no_sell"]].sort_values("init_days", ascending=True),
        ], ignore_index=True)
        
        # 컬럼 존재 확인 후 선택
        cols_final = [c for c in cols_show if c in disp.columns]
        disp_final = disp[cols_final].copy()

        for dc in ["risk_entry_date", "sell_start_date", "sell_end_date"]:
            if dc in disp_final.columns:
                disp_final[dc] = pd.to_datetime(disp_final[dc], errors="coerce").dt.strftime("%Y-%m-%d")

        def _hl(x):
            df = x.copy(); df.loc[:, :] = ""
            for col in ["risk_entry_date", "예측부진재고"]:
                if col in df.columns: df.loc[:, col] = "background-color: #fff3e0"
            for col in ["qty_sold"]:
                if col in df.columns: df.loc[:, col] = "background-color: #e0f2f1"
            return df

        styled = disp_final.reset_index(drop=True).style.set_properties(**{"font-weight": "bold"}).apply(_hl, axis=None)
        st.dataframe(styled, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

###############################################################################
# 📦 6. 데이터 현황 (Footer)
###############################################################################
with st.expander("데이터 현황"):
    current_files = st.session_state["dfs"].get(target_year, {}).get(target_month, {})
    st.markdown(f"**{target_year} {target_month}** 세션 로드: {len(current_files)}개")
    for item in INPUT_DATA_ITEMS:
        fpath = get_latest_file(os.path.join(INPUT_DATA_BASE, item["folder"]))
        status = f"`{os.path.basename(fpath)}`" if fpath else "없음"
        st.markdown(f"- **{item['label']}**: {status}")
