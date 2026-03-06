# ==========================================
# 1. 라이브러리 임포트 및 페이지 설정
# ==========================================
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os
import plotly.express as px
import matplotlib.ticker as ticker
import plotly.graph_objects as go
import math
import numpy as np
from pathlib import Path
import re
from utils import get_stock_csv_path, save_stock_csv, load_stock_csv
from inventory_utils import (
    normalize_mat_code, to_numeric_safe, build_final_df, 
    simulate_batches_by_product, calculate_min_multiplier
)

st.set_page_config(page_title="Aging Stock Analysis", layout="wide")

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
/* 섹션 라벨 */
.section-label { font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.6rem; padding-left: 2px; }
.panel-title-bar { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px 10px 0 0; border-bottom: 2px solid #2563EB; padding: 0.75rem 1.2rem; display: flex; align-items: center; gap: 8px; font-size: 0.9rem; font-weight: 700; color: #1E293B; margin-bottom: 0; }
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #E2E8F0; }
hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.2rem 0; }
h1, h2, h3 { color: #1E293B !important; }
</style>
""", unsafe_allow_html=True)

# 헤더 배너
st.markdown("""
<div class="dash-header">
    <div class="dash-header-left">
        <div class="dash-header-icon">📦</div>
        <div>
            <div class="dash-header-title">Aging Stock Analysis</div>
            <div class="dash-header-sub">유효기한 기반 부진재고 리스크 분석 · 소진 시뮬레이션</div>
        </div>
    </div>
    <div><span class="dash-badge">FEFO Simulation</span></div>
</div>
""", unsafe_allow_html=True)

# ✅ 상수 설정 (기본 유지)
PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"
SALES_DF_KEY = "5. 3개월 매출(자재별).xls"
CLASSIFICATION_DF_KEY = "대분류_소분류_Sheet1.xlsx"

BATCH_COL, MAT_COL, MAT_NAME_COL = "배치", "자재", "자재 내역"
EXPIRY_COL, QTY_SRC_COL, UNIT_COST_COL = "유효 기한", "Stock Quantity on Period End", "단위원가"
VALUE_COL, BUCKET_COL, DAYS_COL = "Stock Value on Period End", "expiry_bucket", "days_to_expiry"

# ✅ 환경 설정 (폰트 등)
def set_korean_font():
    # 경로 설정은 사용자 환경에 맞춰 조정 필요
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NanumGothic-Regular.ttf"))
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = fm.FontProperties(fname=font_path).get_name()
    else:
        plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()
sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"])


# ==========================================
# 3. 데이터 로드 및 전처리 (캐시 활용)
# ==========================================
all_dfs_store = st.session_state.get("dfs", {})
if not all_dfs_store:
    st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
    st.stop()

# 분석 대상 연도/월 선택
st.sidebar.header("📂 분석 대상 선택")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("📅 연도 선택", options=[f"{y}년" for y in range(2023, 2041)], index=range(2023, 2041).index(current_year) if current_year in range(2023, 2041) else 0)
selected_month = st.sidebar.selectbox("📆 월 선택", options=[f"{m}월" for m in range(1, 13)], index=datetime.now().month - 1)

year_data = all_dfs_store.get(selected_year, {})
target_dfs = year_data.get(selected_month)

# 로컬 캐시 확인
stock_csv_path = get_stock_csv_path(selected_year, selected_month)
use_cache = stock_csv_path.exists()
st.caption(f"📌 로컬 캐시 상태: {'✅ 있음' if use_cache else '❌ 없음'}")

if use_cache:
    with st.spinner("캐시 불러오는 중..."):
        final_df = load_stock_csv(selected_year, selected_month)
elif target_dfs is not None:
    with st.expander("📁 분석 파일 정보 확인"):
        file_info = [{"파일명": k, "행": len(v), "열": v.shape[1]} for k, v in target_dfs.items()]
        st.table(pd.DataFrame(file_info))

    with st.spinner("데이터 통합 분석 중..."):
        config_cols = {
            "PRICE_DF_KEY": PRICE_DF_KEY, "STOCK_DF_KEY": STOCK_DF_KEY, "EXPIRY_DF_KEY": EXPIRY_DF_KEY,
            "SALES_DF_KEY": SALES_DF_KEY, "CLASSIFICATION_DF_KEY": CLASSIFICATION_DF_KEY,
            "BATCH_COL": BATCH_COL, "MAT_COL": MAT_COL, "UNIT_COST_COL": UNIT_COST_COL,
            "QTY_SRC_COL": QTY_SRC_COL, "EXPIRY_COL": EXPIRY_COL, "DAYS_COL": DAYS_COL,
            "BUCKET_COL": BUCKET_COL, "VALUE_COL": VALUE_COL
        }
        final_df = build_final_df(target_dfs, selected_year, selected_month, config_cols)
        save_stock_csv(final_df, selected_year, selected_month)
else:
    st.warning("분석할 데이터가 없습니다.")
    st.stop()


# ==========================================
# 4. 기간별 위험 재고 요약
# ==========================================
with st.container():
    st.markdown('<div class="section-label">부진재고 리스크 현황</div>', unsafe_allow_html=True)
    st.markdown("### 📊 부진재고 리스크")
    
    total_value = final_df[VALUE_COL].sum()
    total_count = final_df[MAT_COL].nunique()
    
    risk_buckets_9m = ["폐기확정(유효기한 지남)", "1개월 미만", "2개월 미만", "3개월 미만", "4개월 미만", "5개월 미만", "6개월 미만", "7개월 미만", "8개월 미만", "9개월 미만"]
    risk_df_9m = final_df[final_df[BUCKET_COL].isin(risk_buckets_9m)]
    risk_value_9m = risk_df_9m[VALUE_COL].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("총 재고 가치", f"₩{total_value:,.0f}")
    m2.metric("9개월 미만 재고 금액", f"₩{risk_value_9m:,.0f}")
    m3.metric("분석 대상 자재 수", f"{total_count:,}종")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-label">기간별 상세 리스크 테이블 · {selected_year} {selected_month}</div>', unsafe_allow_html=True)
    with st.container(border=True):
        tab6, tab7, tab9, tab12 = st.tabs(["⚠️ 6개월 미만", "🔔 7개월 미만", "ℹ️ 9개월 미만", "📅 12개월 미만"])

def display_risk_summary(target_buckets, tab_obj, title):
    """기간별 리스크 요약 테이블 표시 함수"""
    with tab_obj:
        risk_df = final_df.copy()

        if risk_df.empty:
            st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
            return

        # ✅ 컬럼명
        EXPIRY_COL = "유효 기한"     # 만료일(날짜)
        SALES_COL  = "3평판"
        DAYS_COL   = "days_to_expiry"

        # 1) 오늘 기준 재계산
        today = pd.Timestamp.today().normalize()  # 오늘 00:00 기준 (시간 영향 제거)

        risk_df[EXPIRY_COL] = pd.to_datetime(risk_df[EXPIRY_COL], errors="coerce")
        risk_df[DAYS_COL] = (risk_df[EXPIRY_COL] - today).dt.days

        def to_bucket(days):
            if pd.isna(days):
                return "유효기한 없음"
            if days < 0:
                return "폐기확정(유효기한 지남)"
            if days < 30:
                return "1개월 미만"
            if days < 60:
                return "2개월 미만"
            if days < 90:
                return "3개월 미만"
            if days < 120:
                return "4개월 미만"
            if days < 150:
                return "5개월 미만"
            if days < 180:
                return "6개월 미만"
            if days < 210:
                return "7개월 미만"
            if days < 240:
                return "8개월 미만"
            if days < 270:
                return "9개월 미만"
            if days < 300:
                return "10개월 미만"
            if days < 330:
                return "11개월 미만"
            if days < 365:
                return "12개월 미만"
            return "12개월 이상"

        risk_df[BUCKET_COL] = risk_df[DAYS_COL].apply(to_bucket)

        # ✅ 여기서 이제 target_buckets로 필터링
        risk_df = risk_df[risk_df[BUCKET_COL].isin(target_buckets)].copy()

        if risk_df.empty:
            st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
            return
        
        # 3) (자재+배치) 단위 표
        summary = (
            risk_df.groupby([MAT_COL, MAT_NAME_COL, "배치"], as_index=False)
            .agg(
                **{
                    QTY_SRC_COL: (QTY_SRC_COL, "sum"),
                    VALUE_COL: (VALUE_COL, "sum"),
                    DAYS_COL: (DAYS_COL, "min"),
                    EXPIRY_COL: (EXPIRY_COL, "min"),
                    SALES_COL: (SALES_COL, "first"),
                    BUCKET_COL: (BUCKET_COL, "first"),
                }
            )
            # ✅ 추천: 급한 순으로 보고 싶으면 아래로 바꿔도 됨
            .sort_values([DAYS_COL, VALUE_COL], ascending=[True, False])
            #.sort_values(VALUE_COL, ascending=False)
            .reset_index(drop=True)
        )

        # 4) 메트릭
        c1, c2 = st.columns(2)
        c1.metric(f"{title} 배치 수", f"{summary['배치'].nunique()}개")
        c2.metric("총 위험 금액", f"₩{summary[VALUE_COL].sum():,.0f}")

        # 5) 포맷 & 표시
        disp = summary.copy()
        disp[EXPIRY_COL] = pd.to_datetime(disp[EXPIRY_COL], errors="coerce").dt.strftime("%Y-%m-%d")

        disp[VALUE_COL] = disp[VALUE_COL].map(lambda x: f"{x:,.0f}")
        disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map(lambda x: f"{x:,.0f}")
        disp[SALES_COL] = disp[SALES_COL].map(lambda x: f"{x:,.0f}" if pd.notna(x) else x)

        disp = disp.rename(columns={
            QTY_SRC_COL: "부진재고 수량",
            VALUE_COL: "부진재고 금액",
            DAYS_COL: "남은 일(Day)",
            EXPIRY_COL: "유효기간",
            SALES_COL: "3평판",
            BUCKET_COL: "버킷",
        })

        show_cols = [
            MAT_COL, MAT_NAME_COL, "배치",
            "버킷", "유효기간", "남은 일(Day)", "3평판",
            "부진재고 수량", "부진재고 금액",
        ]
        
        # ✅ 데이터 테이블 스타일링: Bold 처리 및 특정 컬럼 강조
        styled_disp = disp[show_cols].style.set_properties(**{'font-weight': 'bold'})
        
        def highlight_columns(x):
            df = x.copy()
            df.loc[:, :] = ''
            # 강조할 컬럼 리스트
            target_cols = ['버킷', '유효기간', '부진재고 금액']
            for col in target_cols:
                if col in df.columns:
                    df.loc[:, col] = 'background-color: #fff3e0' # 부드러운 오렌지/옐로우 계열 강조색
            return df
            
        styled_disp = styled_disp.apply(highlight_columns, axis=None)
        
        st.dataframe(styled_disp, use_container_width=True, height=600)


# 리스크 요약 실행
risk_base = ["폐기확정(유효기한 지남)", "1개월 미만", "2개월 미만", "3개월 미만", "4개월 미만", "5개월 미만"]
display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
display_risk_summary(["7개월 미만"], tab7, "7개월 미만")
display_risk_summary(["8개월 미만", "9개월 미만"], tab9, "9개월 미만")
display_risk_summary(["10개월 미만", "11개월 미만", "12개월 미만"], tab12, "12개월 미만")

# ==========================================
# 5. 재고 소진 시뮬레이션 및 시각화
# ==========================================
base_today = datetime.now().date()

# 시뮬레이션 실행 (FEFO 방식)
detail_df, df_after = simulate_batches_by_product(
    df=final_df,
    product_cols=(MAT_COL, MAT_NAME_COL),
    batch_col=BATCH_COL,
    days_col=DAYS_COL,
    qty_col=QTY_SRC_COL,
    monthly_sales_col="3평판",
    risk_days=180,
    step_days=30,
    today=base_today,
)

# 시뮬레이션 결과 가공 (리스크가 있는 배치만 필터링)
gantt_df = detail_df[detail_df["remaining_qty"].fillna(0) > 0].copy()

# 소분류/대분류 데이터 다시 붙이기 (필터링 UI용)
if not gantt_df.empty:
    mat_to_cls = final_df[[MAT_COL, "대분류", "소분류"]].drop_duplicates(subset=[MAT_COL])
    gantt_df = gantt_df.merge(mat_to_cls, on=MAT_COL, how="left")
    gantt_df["소분류"] = gantt_df["소분류"].fillna("미분류")

# no_sales 제외 및 날짜 변환
if not gantt_df.empty:
    if "stop_reason" in gantt_df.columns:
        gantt_df = gantt_df[gantt_df["stop_reason"] != "no_sales"].copy()
    
    for c in ["sell_start_date", "sell_end_date", "risk_entry_date"]:
        if c in gantt_df.columns:
            gantt_df[c] = pd.to_datetime(gantt_df[c], errors="coerce")
    
    gantt_df = gantt_df.dropna(subset=["sell_start_date", "sell_end_date"]).copy()

# =========================================================
# 1) 소분류 선택 UI
# =========================================================

st.divider()

with st.container(border=True):
    st.markdown('<div class="section-label" style="margin-bottom:0.5rem;">소진 시뮬레이션 (FEFO)</div>', unsafe_allow_html=True)
    st.markdown("### 🗓️ 소분류별 배치 판매 시뮬레이션")
    
    # gantt_df는 이미 remaining_qty > 0인 배치만 포함하고 있음
    risk_subcats = gantt_df["소분류"].unique().tolist()

    subcat_meta = (
        gantt_df[gantt_df["소분류"].isin(risk_subcats)]
        .fillna("미분류")
        .drop_duplicates(subset=["소분류"])
        .copy()
    )

    if subcat_meta.empty:
        st.info("현재 분석 데이터 중 '부진재고'가 발생하는 품목이 없습니다.")
        st.stop()

    subcat_meta["ui_label"] = (
        subcat_meta["대분류"].astype(str) + "(" + subcat_meta["소분류"].astype(str) + ") | " + subcat_meta["소분류"].astype(str)
    )

    label_to_subcat = dict(zip(subcat_meta["ui_label"], subcat_meta["소분류"]))
    ui_options = ["(전체)"] + sorted(subcat_meta["ui_label"].unique().tolist())
    selected_ui = st.selectbox("소분류 선택 (부진재고 발생 소분류만 표시)", options=ui_options)

    selected_subcat = None if selected_ui == "(전체)" else label_to_subcat[selected_ui]
    view_df = gantt_df if selected_subcat is None else gantt_df[gantt_df["소분류"] == selected_subcat]

    if selected_subcat is not None:
        st.caption(
            f"선택 소분류: {selected_ui}  |  제품 수: {view_df[MAT_COL].nunique()}개 / 배치 수: {view_df[BATCH_COL].nunique()}개"
        )

    # 부진재고 요약 지표 (KPI)
    risk_view_df = view_df[view_df["remaining_qty"].fillna(0) > 0].copy()
    if not risk_view_df.empty:
        if "단위원가" not in risk_view_df.columns:
            unit_cost_map = (
                final_df[[MAT_COL, "단위원가"]]
                .dropna(subset=[MAT_COL, "단위원가"])
                .drop_duplicates(subset=[MAT_COL])
            )
            risk_view_df = risk_view_df.merge(unit_cost_map, on=MAT_COL, how="left")

        risk_view_df["단위원가"] = pd.to_numeric(risk_view_df["단위원가"], errors="coerce").fillna(0)
        risk_view_df["remaining_amount"] = risk_view_df["remaining_qty"].fillna(0) * risk_view_df["단위원가"]

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("부진재고 배치 수", f"{risk_view_df[BATCH_COL].nunique()}개")
        with kpi2:
            st.metric("예상 부진재고 금액 합계", f"₩{risk_view_df['remaining_amount'].sum():,.0f}")
        with kpi3:
            first_date = risk_view_df["risk_entry_date"].min()
            st.metric("가장 빠른 부진재고 진입일", first_date.strftime("%Y-%m-%d") if pd.notna(first_date) else "-")
    else:
        st.success("✅ 선택한 범위 내에는 부진재고가 발생할 것으로 예상되는 배치가 없습니다.")

    # 최소 매출 배수 계산 (부진재고 0 달성 시뮬레이션)
    if selected_ui != "(전체)" and (not view_df.empty):
        base_risk_df = view_df[view_df["remaining_qty"].fillna(0) > 0].copy()

        if base_risk_df.empty:
            st.success("현재 소분류는 기준 평판(1.0x) 시나리오에서 부진재고가 없습니다.")
        else:
            risk_mats = base_risk_df[MAT_COL].dropna().unique().tolist()
            sub_df_base = final_df[final_df[MAT_COL].isin(risk_mats)].copy()

            if "3평판" not in sub_df_base.columns:
                st.warning("final_df에 '3평판' 컬럼이 없어 최소 배수를 계산할 수 없습니다.")
                minmult_df = pd.DataFrame(columns=["자재코드", "자재내역", "3평판", "부진재고 0을 위한 최소 배수(추정)", "비고"])
            else:
                sales_series = pd.to_numeric(sub_df_base["3평판"], errors="coerce").fillna(0)
                if sales_series.sum() <= 0:
                    st.warning("이 소분류는 3평판 값이 0(또는 없음)이라 최소 배수를 계산할 수 없습니다.")
                    minmult_df = pd.DataFrame(columns=["자재코드", "자재내역", "3평판", "부진재고 0을 위한 최소 배수(추정)", "비고"])
                else:
                    minmult_rows = []
                    for mat in sorted(sub_df_base[MAT_COL].dropna().unique().tolist()):
                        df_mat = sub_df_base[sub_df_base[MAT_COL] == mat].copy()
                        mat_name = str(df_mat[MAT_NAME_COL].dropna().iloc[0]) if MAT_NAME_COL in df_mat.columns and df_mat[MAT_NAME_COL].notna().any() else ""
                        base_sales = float(pd.to_numeric(df_mat["3평판"], errors="coerce").fillna(0).iloc[0])

                        if base_sales <= 0:
                            minmult_rows.append({
                                "자재코드": mat, "자재내역": mat_name, "3평판": base_sales,
                                "부진재고 0을 위한 최소 배수(추정)": "- (3평판=0)", "비고": "판매량 0 → 배수로 개선 불가",
                            })
                            continue

                        min_m = calculate_min_multiplier(
                            df_mat=df_mat, product_cols=(MAT_COL, MAT_NAME_COL), batch_col=BATCH_COL,
                            days_col=DAYS_COL, qty_col=QTY_SRC_COL, monthly_sales_col="3평판",
                            today=base_today, lo=1.0, hi=6.0
                        )

                        minmult_rows.append({
                            "자재코드": mat, "자재내역": mat_name, "3평판": base_sales,
                            "부진재고 0을 위한 최소 배수(추정)": "-" if min_m is None else f"{min_m:.2f}x",
                            "비고": "6.0x까지도 0이 안 됨" if min_m is None else "D-180 기준 잔존 0 달성",
                        })

                    minmult_df = pd.DataFrame(minmult_rows).sort_values(["자재코드"]).reset_index(drop=True)

            # 권장 판매량 및 요약 표 구성
            st.write(f"### 🧾 부진재고 요약 (소분류: {selected_subcat})")
            summary_df = risk_view_df.copy()
            summary_df = summary_df.sort_values(["risk_entry_date", "init_days"], ascending=[True, True])

            table_df = summary_df.copy().rename(columns={
                MAT_COL: "자재코드", MAT_NAME_COL: "자재내역", BATCH_COL: "배치",
                "risk_entry_date": "부진재고 진입일", "remaining_qty": "예상부진재고량", "remaining_amount": "예상부진금액",
            })

            mult_map = minmult_df[["자재코드", "3평판", "부진재고 0을 위한 최소 배수(추정)", "비고"]].drop_duplicates(subset=["자재코드"])
            table_df = table_df.merge(mult_map, on="자재코드", how="left")

            def parse_multiplier(v):
                if pd.isna(v): return np.nan
                s = str(v).strip()
                if s == "-" or s.startswith("-"): return np.nan
                m = re.search(r"([0-9]*\.?[0-9]+)\s*x", s.lower())
                return float(m.group(1)) if m else np.nan

            sales_num = pd.to_numeric(table_df["3평판"], errors="coerce")
            mult_num = table_df["부진재고 0을 위한 최소 배수(추정)"].apply(parse_multiplier)
            table_df["권장 판매량"] = (sales_num * mult_num).round(0).apply(lambda x: f"{int(x):,}" if pd.notna(x) else "-")
            table_df["판매 개선율(%)"] = ((mult_num - 1.0) * 100).round(0).apply(lambda x: f"{int(x)}% 증가" if pd.notna(x) else "-")

            show_cols = ["자재코드", "자재내역", "배치", "3평판", "부진재고 진입일", "예상부진재고량", "예상부진금액", "권장 판매량", "판매 개선율(%)"]
            table_df = table_df[[c for c in show_cols if c in table_df.columns]].copy()
            table_df = table_df.sort_values(["부진재고 진입일", "예상부진금액"], ascending=[True, False])

            table_df["부진재고 진입일"] = pd.to_datetime(table_df["부진재고 진입일"], errors="coerce").dt.strftime("%Y-%m-%d")
            table_df["예상부진재고량"] = pd.to_numeric(table_df["예상부진재고량"], errors="coerce").fillna(0).astype(int).map(lambda x: f"{x:,}")
            table_df["예상부진금액"] = pd.to_numeric(table_df["예상부진금액"], errors="coerce").fillna(0).map(lambda x: f"₩{x:,.0f}")
            table_df["3평판"] = pd.to_numeric(table_df["3평판"], errors="coerce").fillna(0).astype(int).map(lambda x: f"{x:,}")

            def highlight_sim_columns(x):
                df = x.copy(); df.loc[:, :] = ''
                orange_cols = ['부진재고 진입일', '예상부진금액']
                mint_cols = ['권장 판매량', '판매 개선율(%)']
                for col in orange_cols: 
                    if col in df.columns: df.loc[:, col] = 'background-color: #fff3e0'
                for col in mint_cols:
                    if col in df.columns: df.loc[:, col] = 'background-color: #e0f2f1'
                return df

            styled_table = table_df.style.set_properties(**{'font-weight': 'bold'}).apply(highlight_sim_columns, axis=None)
            st.dataframe(styled_table, use_container_width=True, height=320)

    # 간트 차트 시각화
    if view_df.empty:
        st.info("시뮬레이션 결과 표시할 데이터가 없습니다.")
    else:
        # 시각화용 데이터 준비
        view_df = view_df.copy()
        view_df["mat_label"] = view_df[MAT_COL].astype(str) + " | " + view_df[MAT_NAME_COL].astype(str)
        view_df["expiry_date"] = pd.to_datetime(base_today) + pd.to_timedelta(view_df["init_days"], unit="D")

        # 판매기간 바
        sales_bar = view_df.copy()
        sales_bar["phase"] = "판매기간"
        sales_bar = sales_bar.rename(columns={"sell_start_date": "x_start", "sell_end_date": "x_end"})

        # 부진재고 구간 바
        sluggish_bar = view_df[view_df["remaining_qty"].fillna(0) > 0].copy()
        sluggish_bar = sluggish_bar.dropna(subset=["risk_entry_date", "expiry_date"]).copy()
        sluggish_bar["phase"] = "부진재고 구간"
        sluggish_bar = sluggish_bar.rename(columns={"risk_entry_date": "x_start", "expiry_date": "x_end"})

        plot_df = pd.concat([sales_bar, sluggish_bar], ignore_index=True)
        plot_df["batch_label"] = plot_df["mat_label"].astype(str) + " | " + plot_df[BATCH_COL].astype(str)
        
        # 정렬 로직 (자재 -> 배치별 판매시작일 순)
        order_base = plot_df[plot_df["phase"] == "판매기간"].copy()
        if order_base.empty: order_base = plot_df.copy()
        
        order_meta = order_base[["batch_label", "mat_label", "x_start"]].drop_duplicates(subset=["batch_label"]).rename(columns={"x_start": "sell_start"})
        order_meta = order_meta.sort_values(["mat_label", "sell_start", "batch_label"], ascending=[True, True, True])
        y_order = order_meta["batch_label"].tolist()

        fig = px.timeline(
            plot_df, x_start="x_start", x_end="x_end", y="batch_label", color="phase", 
            color_discrete_map={"판매기간": "#4C78A8", "부진재고 구간": "#E45756"},
            hover_data={MAT_COL: True, MAT_NAME_COL: True, "remaining_qty": True, "risk_entry_date": True, "expiry_date": True},
        )
        
        fig.update_yaxes(categoryorder="array", categoryarray=y_order, autorange="reversed")
        
        dynamic_height = max(400, len(y_order) * 30 + 120)
        fig.update_layout(
            height=dynamic_height, margin=dict(t=50, b=50, l=10, r=10),
            xaxis_title="Simulation Timeline", plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9", dtick="M1", tickformat="%Y-%m")
        fig.update_traces(marker_line_color='white', marker_line_width=1, opacity=0.9)

        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. 결과 저장 및 다운로드
# ==========================================
if "stock_data" not in st.session_state:
    st.session_state["stock_data"] = {}

# 세션 상태에 최종 결과 저장
if selected_year not in st.session_state["stock_data"]:
    st.session_state["stock_data"][selected_year] = {}
if selected_month not in st.session_state["stock_data"][selected_year]:
    st.session_state["stock_data"][selected_year][selected_month] = {}

st.session_state["stock_data"][selected_year][selected_month]["유효기한"] = {
    "df": final_df,
    "processed_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

st.sidebar.success(f"✅ {selected_year} {selected_month} 분석 완료")

with st.container():
    st.markdown("<hr>", unsafe_allow_html=True)
    d1, d2, _ = st.columns([1, 1, 2])
    with d1:
        csv_bytes = final_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ CSV 다운로드", 
            data=csv_bytes, 
            file_name=f"{selected_year}_{selected_month}_유효기한.csv", 
            mime="text/csv",
            use_container_width=True
        )

