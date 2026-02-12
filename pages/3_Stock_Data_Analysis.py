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

# ✅ 페이지 설정
st.set_page_config(page_title="Stock Data Analysis", layout="wide")

# --- [추가] 커스텀 CSS (프리미엄 UI 스타일링) ---
st.markdown("""
<style>
    /* 전체 배경 및 폰트 설정 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .main {
        background-color: #f8f9fa;
    }
    
    /* 카드형 컨테이너 스타일 */
    .stContainer {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
        border: 1px solid #e9ecef;
    }
    
    /* 제목 스타일 */
    .main-title {
        font-family: 'Inter', sans-serif;
        color: #1e293b;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* 메트릭 박스 스타일 */
    [data-testid="stMetric"] {
        border: 1px solid #e9ecef;
        padding: 15px 20px;
        border-radius: 12px;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 600;
    }

    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        color: #475569;
        font-weight: 600;
        padding: 10px 20px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #2563eb !important;
        border-bottom: 2px solid #2563eb !important;
    }
</style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<h1 class="main-title">📈 Stock Data Analysis</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">재고 현황 및 유효기한 리스크 심층 분석 대시보드</p>', unsafe_allow_html=True)

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

def normalize_mat_code(x):
    # 숫자처럼 생긴 건 정수로 바꿨다가 문자열화 (123.0 -> "123")
    # 문자 섞인 건 그대로 문자열
    s = str(x).strip()
    try:
        # 123.0, 123 같은 케이스 통일
        return str(int(float(s)))
    except:
        return s

# ✅ 데이터 처리 함수 (기존 로직 유지)
def to_numeric_safe(s): return pd.to_numeric(s, errors="coerce").fillna(0)


def build_final_df(dfs_dict, year_str, month_str):
    # 1. 필수 파일 존재 확인 (매출 파일 포함 4개)
    required_keys = [PRICE_DF_KEY, STOCK_DF_KEY, EXPIRY_DF_KEY, SALES_DF_KEY]
    for key in required_keys:
        if key not in dfs_dict:
            st.error(f"❌ '{year_str} {month_str}' 폴더에 필수 파일이 없습니다: {key}")
            st.stop()
            
    # --- [Step 1] 단위원가 계산 (1번 파일 활용) ---
    df_price = dfs_dict[PRICE_DF_KEY]
    tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
    tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
    tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
    unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
    unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(
        lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1
    )

    # --- [Step 1-추가] 대분류/소분류 매핑 붙이기 (분류 파일 활용) ---
    # 1️⃣ 타입 통일 (중요)
    df_cls = dfs_dict[CLASSIFICATION_DF_KEY].copy()
    unit_cost_df[MAT_COL] = unit_cost_df[MAT_COL].astype(str).str.strip()
    df_cls[MAT_COL] = df_cls[MAT_COL].astype(str).str.strip()

    # 2️⃣ 자재 → 대분류 / 소분류 매핑 dict 생성
    major_map = df_cls.drop_duplicates(subset=[MAT_COL]) \
                    .set_index(MAT_COL)["대분류"]

    minor_map = df_cls.drop_duplicates(subset=[MAT_COL]) \
                    .set_index(MAT_COL)["소분류"]

    # 3️⃣ unit_cost_df에 매핑해서 컬럼 생성
    unit_cost_df["대분류"] = unit_cost_df[MAT_COL].map(major_map)
    unit_cost_df["소분류"] = unit_cost_df[MAT_COL].map(minor_map)

    # 4️⃣ 매핑 실패한 경우 처리
    unit_cost_df["대분류"] = unit_cost_df["대분류"].fillna("미분류")
    unit_cost_df["소분류"] = unit_cost_df["소분류"].fillna("미분류")

    unit_cost_df[MAT_COL] = pd.to_numeric(unit_cost_df[MAT_COL], errors="coerce")

    # --- [Step 2] 재고 정보와 유효기한 병합 (2, 3번 파일 활용) ---
    df_stock = dfs_dict[STOCK_DF_KEY]
    df_expiry = dfs_dict[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
    merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
    merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
    merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
    # --- [Step 3] 유효기한 버킷팅 (D-Day 계산) ---
    today = pd.Timestamp(datetime.now().date())
    merged[EXPIRY_COL] = pd.to_datetime(merged[EXPIRY_COL], errors="coerce")
    merged[DAYS_COL] = (merged[EXPIRY_COL] - today).dt.days
    
    def bucketize(days):
        if pd.isna(days): return "유효기한 없음"
        if days <= 0: return "폐기확정(유효기한 지남)"
        if days <= 90: return "3개월 미만"
        if days <= 180: return "6개월 미만"
        if days <= 210: return "7개월 미만"  
        if days <= 270: return "9개월 미만"
        if days <= 365: return "12개월 미만"
        return "12개월 이상"
    
    merged[BUCKET_COL] = merged[DAYS_COL].apply(bucketize)
    
    # --- [Step 4] 재고 가치 산출 (수량 * 단위원가) ---
    merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL, "대분류", "소분류"]], on=MAT_COL, how="left")
    merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
    merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
    # --- [Step 5] 자재별 월평균 매출(3평판) 자동 계산 (5번 파일 활용) ---
    df_sales = dfs_dict[SALES_DF_KEY].copy()
    df_sales['순매출수량'] = to_numeric_safe(df_sales['순매출수량'])
    
    # 1. 자재별 실제 데이터가 존재하는 개월 수 카운트 (nunique 사용)
    # 한 자재가 202510, 202511 두 달치 데이터만 있다면 개월수는 2가 됨
    month_counts = df_sales.groupby('자재코드')['년월'].nunique().reset_index()
    month_counts.columns = ['자재코드', '개월수']
    
    # 2. 자재별 전체 순매출수량 합계 계산
    total_sales = df_sales.groupby('자재코드', as_index=False)['순매출수량'].sum()
    
    # 3. 평균(3평판) 계산: (전체 합계 / 실제 데이터 개월수)
    sales_avg = total_sales.merge(month_counts, on='자재코드')
    sales_avg['3평판'] = sales_avg.apply(
        lambda r: r['순매출수량'] / r['개월수'] if r['개월수'] > 0 else 0, axis=1
    )
    

    # --- [수정] 최종 데이터프레임에 '3평판'과 '개월수' 함께 추가 ---
    merged = merged.merge(
        sales_avg[['자재코드', '3평판', '개월수']], # 개월수 컬럼 추가
        left_on=MAT_COL, 
        right_on='자재코드', 
        how="left"
    )
    
    # --- [Step 6] 데이터 정리 및 반환 ---
    if '자재코드' in merged.columns:
        merged.drop(columns=['자재코드'], inplace=True)
    merged['3평판'] = merged['3평판'].fillna(0)
    
    # ✅ "재고일수" 컬럼 추가: Stock Quantity / (3평판 / 30)
    # 3평판이 0인 경우 매우 큰 값(999)으로 채움
    merged['재고일수'] = merged.apply(
        lambda r: r[QTY_SRC_COL] / (r['3평판'] / 30.0) if r['3평판'] > 0 else 999.0, 
        axis=1
    )
    
    return merged

# =====================================================
# 🚀 메인 로직 시작
# =====================================================
all_dfs_store = st.session_state.get("dfs", {})

if not all_dfs_store:
    st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
    st.stop()

# --- 📅 [수정] 분석 대상 연도 및 월 선택 ---
st.sidebar.header("📂 분석 대상 선택")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox(
    "📅 연도 선택",
    options=[f"{y}년" for y in range(2023, 2041)],
    index=range(2023, 2041).index(current_year) if current_year in range(2023, 2041) else 0
)

selected_month = st.sidebar.selectbox(
    "📆 월 선택",
    options=[f"{m}월" for m in range(1, 13)],
    index=datetime.now().month - 1
)

# 선택된 연도/월의 데이터 뭉치 가져오기 (세션 상태)
year_data = all_dfs_store.get(selected_year, {})
target_dfs = year_data.get(selected_month)

BASE_DATA_DIR = Path("Datas")

# 로컬 캐시 우선 로드 로직
stock_csv_path = get_stock_csv_path(selected_year, selected_month)
use_cache = stock_csv_path.exists()

# (선택) 사이드/화면에 상태 표시
st.caption(f"📌 로컬 캐시 상태: {'✅ 있음 (Stock.csv 로드)' if use_cache else '❌ 없음 (업로드 데이터로 생성)'}")

# 2) final_df 생성: 캐시 있으면 로드, 없으면 생성 후 저장
if use_cache:
    with st.spinner(f"{selected_year} {selected_month} Stock.csv 캐시 불러오는 중..."):
        final_df = load_stock_csv(selected_year, selected_month)
    st.success(f"✅ 캐시 로드 완료: {stock_csv_path}")

elif target_dfs is not None:
    # 캐시가 없을 때만 기존 UI/빌드 로직 실행
    with st.expander(f"📁 {selected_year} {selected_month} 분석 대상 파일 확인", expanded=False):
        file_info = []
        for f_name, f_df in target_dfs.items():
            file_info.append({"파일명": f_name, "행 수": len(f_df), "컬럼 수": f_df.shape[1]})
        st.table(pd.DataFrame(file_info))

    # 최종 가공 데이터 생성
    with st.spinner(f"{selected_year} {selected_month} 데이터를 통합 분석 중입니다..."):
        final_df = build_final_df(target_dfs, selected_year, selected_month)

    # ✅ 생성 후 로컬에 저장
    saved_path = save_stock_csv(final_df, selected_year, selected_month)
    st.success(f"✅ Stock.csv 저장 완료: {saved_path}")

else:
    st.warning(f"⚠️ {selected_year} {selected_month}에 해당하는 데이터가 없습니다.")
    st.info("먼저 업로드 페이지에서 데이터를 업로드하거나, 기존 분석 결과(Stock.csv)가 있는지 확인해 주세요.")
    st.stop()


# -----------------------------------------------------
# 1️⃣ 기간별 위험 자재 요약 (ON)
# -----------------------------------------------------
with st.container():
    st.markdown("### 📊 한눈에 보는 재고 리스크")
    
    # 상단 요약 지표 (KPI)
    total_value = final_df[VALUE_COL].sum()
    total_count = final_df[MAT_COL].nunique()
    
    # 위험 구간(9개월 미만) 필터
    risk_buckets_9m = ["폐기확정(유효기한 지남)", "1개월 미만", "2개월 미만", "3개월 미만", "4개월 미만", "5개월 미만", "6개월 미만", "7개월 미만", "8개월 미만", "9개월 미만"]
    risk_df_9m = final_df[final_df[BUCKET_COL].isin(risk_buckets_9m)]
    risk_value_9m = risk_df_9m[VALUE_COL].sum()
    risk_percent_9m = (risk_value_9m / total_value * 100) if total_value > 0 else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("총 재고 가치", f"₩{total_value:,.0f}")
    m2.metric("9개월 미만 재고 금액", f"₩{risk_value_9m:,.0f}")
    m3.metric("분석 대상 자재 수", f"{total_count:,}종")

    st.markdown("---")
    st.markdown(f"#### 🚨 {selected_year} {selected_month} 기간별 상세 요약")
    tab6, tab7, tab9, tab12 = st.tabs(
        ["⚠️ 6개월 미만", "🔔 7개월 미만", "ℹ️ 9개월 미만", "📅 12개월 미만"]
    )

# def display_risk_summary(target_buckets, tab_obj, title):
#     with tab_obj:
#         risk_df = final_df[final_df[BUCKET_COL].isin(target_buckets)].copy()
#         if risk_df.empty:
#             st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
#             return

#         # ✅ 자재 단위 요약 + 배치 정보 포함
#         summary = (
#             risk_df.groupby([MAT_COL, MAT_NAME_COL], as_index=False)
#             .agg(
#                 배치수=("배치", "nunique"),
#                 배치목록=("배치", lambda s: ", ".join(map(str, pd.Series(s).dropna().unique()[:10]))),
#                 **{QTY_SRC_COL: (QTY_SRC_COL, "sum"),
#                    VALUE_COL: (VALUE_COL, "sum")}
#             )
#             .sort_values(VALUE_COL, ascending=False)
#             .reset_index(drop=True)
#         )

#         # (1) ✅ 메트릭은 1:1로만
#         c1, c2 = st.columns(2)
#         c1.metric(f"{title} 자재 수", f"{len(summary)}종")
#         c2.metric("총 위험 금액", f"₩{summary[VALUE_COL].sum():,.0f}")

#         # (2) ✅ 표는 바로 아래 + 배치 정보 컬럼 포함
#         disp = summary.copy()
#         disp[VALUE_COL] = disp[VALUE_COL].map(lambda x: f"{x:,.0f}")
#         disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map(lambda x: f"{x:,.0f}")

#         disp = disp.rename(columns={QTY_SRC_COL: "부진재고 수량", VALUE_COL: "부진재고 금액"})
#         # 컬럼 순서 보기 좋게 정리 (원하면 더 수정 가능)
#         show_cols = [MAT_COL, MAT_NAME_COL, "배치수", "배치목록", "부진재고 수량", "부진재고 금액"]
#         st.dataframe(disp[show_cols], use_container_width=True, height=600)

def display_risk_summary(target_buckets, tab_obj, title):
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
        st.dataframe(disp[show_cols], use_container_width=True, height=600)


risk_base = ["폐기확정(유효기한 지남)", "1개월 미만", "2개월 미만", "3개월 미만", "4개월 미만", "5개월 미만"]
display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
display_risk_summary(["7개월 미만"], tab7, "7개월 미만")
display_risk_summary(["8개월 미만", "9개월 미만"], tab9, "9개월 미만")
display_risk_summary(["10개월 미만", "11개월 미만", "12개월 미만"], tab12,"12개월 미만")


# -----------------------------------------------------
# 2️⃣ 자재-배치 단위 상세 분석 및 시각화 (OFF)
# -----------------------------------------------------
def render_batch_analysis_section(final_df, MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL):
    """
    자재-배치별 상세 분석 섹션을 렌더링하는 함수입니다.
    기존 로직을 그대로 유지하며 매개변수로 필요한 상수들을 받습니다.
    """
    with st.container():
        st.subheader("🔍 자재-배치별 상세 분석 (6/7/9개월 집중)")

        target_risks_all = ["3개월 미만", "6개월 미만", "7개월 미만", "9개월 미만", "폐기확정(유효기한 지남)"]
        df_risk_all = final_df[final_df[BUCKET_COL].isin(target_risks_all)].copy()

        if not df_risk_all.empty:
            top_mats = (
                df_risk_all.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[VALUE_COL].sum()
                .sort_values(VALUE_COL, ascending=False)
            )
            top_mats["label"] = top_mats[MAT_COL].astype(str) + " | " + top_mats[MAT_NAME_COL].astype(str)
            
            col_sel, col_chk = st.columns([2, 1])
            with col_sel:
                selected_label = st.selectbox("상세 조사가 필요한 자재를 선택하세요", options=top_mats["label"].tolist())
                selected_mat = selected_label.split(" | ")[0]
            with col_chk:
                show_all_batches = st.checkbox("모든 위험 배치 보기 (금액순)", value=False)

            if show_all_batches:
                view_df = df_risk_all.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
            else:
                view_df = df_risk_all[df_risk_all[MAT_COL].astype(str) == selected_mat].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)

            st.write(f"### 📍 상세 리스트 (분석 대상: {selected_label if not show_all_batches else '전체 위험 배치'})")
            
            v_disp = view_df[[MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]].copy()
            v_disp[VALUE_COL] = v_disp[VALUE_COL].map('{:,.0f}'.format)
            v_disp[QTY_SRC_COL] = v_disp[QTY_SRC_COL].map('{:,.0f}'.format)
            st.dataframe(v_disp, use_container_width=True)

            if not show_all_batches:
                chart_targets = ["6개월 미만", "7개월 미만", "9개월 미만"]
                chart_df = view_df[view_df[BUCKET_COL].isin(chart_targets)].copy()

                if not chart_df.empty:
                    fig, ax = plt.subplots(figsize=(10, 4)) 
                    sns.barplot(
                        data=chart_df, 
                        x=BATCH_COL, 
                        y=VALUE_COL, 
                        hue=BUCKET_COL, 
                        palette="viridis",
                        ax=ax,
                        errorbar=None,
                        width=0.7 
                    )
                    
                    ax.set_title(f"📍 [{selected_label}] 배치별 상세 가치 분석 (6/7/9개월 미만)", fontsize=15, pad=20)
                    ax.set_xlabel("배치 번호", fontsize=12)
                    ax.set_ylabel("재고 가치 (Stock Value)", fontsize=12)

                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
                    ax.legend(title="위험 구간", bbox_to_anchor=(1.05, 1), loc='upper left')
                    
                    sns.despine()
                    plt.xticks(rotation=0, ha="right")
                    plt.tight_layout()
                    st.pyplot(fig, use_container_width=True)
                else:
                    st.info("💡 선택한 자재에는 6/7/9개월 미만에 해당하는 배치가 없습니다.")
        else:
            st.info("관리 대상 위험 재고가 없습니다.")
#render_batch_analysis_section(final_df, MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL)

# -----------------------------------------------------
# 3️⃣ 국가별 재고 가치 분포(지도), 요약 지표(Metric), 상세 리스크 테이블 시각화 (OFF)
# -----------------------------------------------------
def render_country_stock_analysis(final_df, VALUE_COL, BUCKET_COL, selected_year, selected_month):
    """
    국가별 재고 가치 분포(지도), 요약 지표(Metric), 상세 리스크 테이블을 렌더링합니다.
    """
    # 내부 함수: 국가 분류 로직
    def classify_country(location_code):
        if pd.isna(location_code) or str(location_code).strip() == "":
            return "국내"
        loc = str(location_code).split('.')[0].strip()
        if loc in ["6030", "7030", "7040"]:
            return "China"
        elif loc == "6080":
            return "United States"
        elif loc == "7090":
            return "Japan"
        else:
            return "국내"

    st.subheader("🌍 국가별 전체 재고 가치 분포")

    # 1. 데이터 전처리
    geo_df = final_df.copy()
    geo_df['저장 위치'] = pd.to_numeric(geo_df['저장 위치'], errors='coerce')
    geo_df['Country'] = geo_df['저장 위치'].apply(classify_country)

    # 국가별 합계 계산
    country_summary = geo_df.groupby('Country')[VALUE_COL].sum().reset_index()
    total_global_val = country_summary[VALUE_COL].sum()

    if total_global_val > 0:
        country_summary['비중(%)'] = (country_summary[VALUE_COL] / total_global_val * 100).round(3)
    else:
        country_summary['비중(%)'] = 0

    country_summary['Country_Map'] = country_summary['Country'].replace({'국내': 'South Korea'})

    # 2. 상단 요약 지표 (Metric Widgets)
    st.write("#### 📊 주요 지역별 재고 자산 요약")
    m1, m2, m3, m4 = st.columns(4)

    def render_region_metric(label, col_obj):
        row = country_summary[country_summary['Country'] == label]
        if not row.empty:
            val = row[VALUE_COL].values[0]
            pct = row['비중(%)'].values[0]
            col_obj.metric(label, f"₩{val:,.0f}", f"{pct:.3f}%")
        else:
            col_obj.metric(label, "₩0", "0.000%")

    render_region_metric("국내", m1)
    render_region_metric("China", m2)
    render_region_metric("United States", m3)
    render_region_metric("Japan", m4)

    # 3. Plotly 글로벌 지도 (Blues 스케일 적용)
    fig_map = px.choropleth(
        country_summary,
        locations="Country_Map",
        locationmode="country names",
        color=VALUE_COL,
        hover_name="Country",
        hover_data={VALUE_COL: ':,.0f', '비중(%)': ':.3f%', 'Country_Map': False},
        color_continuous_scale="Reds", 
        title=f"🌐 {selected_year} {selected_month} 글로벌 거점별 재고 가치 합계",
        labels={VALUE_COL: "재고 가치(₩)", "비중(%)": "글로벌 비중"}
    )

    fig_map.update_layout(
        margin={"r":0,"t":50,"l":0,"b":0},
        geo=dict(showframe=False, showcoastlines=True, landcolor="lightgray")
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # 4. 상세 분석 테이블 (Expander)
    with st.expander("📝 지역별 & 위험구간별 상세 분석 테이블"):
        target_buckets = ["6개월 미만", "7개월 미만", "9개월 미만", "폐기확정(유효기한 지남)", "3개월 미만"]
        pivot_risk = geo_df.pivot_table(
            index='Country',
            columns=BUCKET_COL,
            values=VALUE_COL,
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        existing_cols = [col for col in target_buckets if col in pivot_risk.columns]
        table_display = pivot_risk[['Country'] + existing_cols].copy()
        table_display['위험재고 합계'] = table_display[existing_cols].sum(axis=1)
        
        st.write("##### 📍 국가별 유효기한 리스크 현황 (단위: 원)")
        st.dataframe(
            table_display.sort_values('위험재고 합계', ascending=False).style.format({
                col: '{:,.0f}' for col in table_display.columns if col != 'Country'
            }),
            use_container_width=True
        )
        st.caption("※ 위 테이블은 전체 재고 중 유효기한 리스크가 있는 항목만 추려서 국가별로 합산한 결과입니다.")
#render_country_stock_analysis(final_df, VALUE_COL, BUCKET_COL, selected_year, selected_month)


# -----------------------------------------------------
# 4️⃣ 재고소진시뮬레이션 (FEFO + D-180 도달 즉시 판매중단) (ON)
# -----------------------------------------------------
def simulate_batches_by_product(
    df: pd.DataFrame,
    product_cols=("자재", "자재 내역"),            # (MAT_COL, MAT_NAME_COL)
    batch_col="배치",                          # BATCH_COL
    days_col="유효 기한",                      # DAYS_COL  (남은 일수 컬럼)
    qty_col="Stock Quantity on Period End",     # QTY_SRC_COL
    monthly_sales_col="3평판",                  # 월 판매량
    risk_days=180,                              # D-180
    step_days=30,                               # 30일 단위
    today=None
):
    """
    제품별로 배치를 유효기한(남은일수) 짧은 순으로 정렬한 뒤,
    가장 먼저 만료되는 배치부터 월평균 판매량(3평판) 기준으로 판매(차감) 시뮬레이션.

    ✅ 변경점(요구사항 반영):
      - 유효기한이 6개월 미만(D-180 이하)이 되는 시점(risk_entry_date)부터는 판매 불가
      - 만약 30일 판매 구간 중간에 risk_entry_date가 끼면, risk_entry_date 직전까지만 "부분판매(일할)" 후 즉시 중단하고 다음 배치로 넘어감

    판매 중단 조건:
      - 재고가 0이 됨 (sold_out)
      - 유효기한이 risk_days 이하가 됨 (risk_reached)  ← risk_entry_date 도달 즉시 판매 중단

    반환:
      - detail_df: 배치별 판매 시작/종료/중단사유/잔량/위험진입일 등 이력
      - updated_df: 시뮬레이션 후 배치별 잔량(qty_col 업데이트)
    """

    if today is None:
        today = datetime.now().date()
    elif isinstance(today, datetime):
        today = today.date()

    df0 = df.copy()

    # 숫자형 정리 (NaN 방어)
    df0[days_col] = pd.to_numeric(df0[days_col], errors="coerce").fillna(0).astype(int)
    df0[qty_col] = pd.to_numeric(df0[qty_col], errors="coerce").fillna(0.0)
    df0[monthly_sales_col] = pd.to_numeric(df0[monthly_sales_col], errors="coerce").fillna(0.0)

    detail_rows = []
    updated = df0.copy()

    grp_cols = list(product_cols)

    for prod_key, g in df0.groupby(grp_cols, dropna=False):
        g = g.copy()

        # (1) 배치: 유효기한 짧은 순 정렬 (FEFO)
        g = g.sort_values(days_col, ascending=True)

        # 제품 판매량: 배치마다 동일하다고 가정(대표값 사용)
        monthly_sales = float(g[monthly_sales_col].iloc[0]) if len(g) else 0.0

        # 이 제품의 시간은 "오늘"부터 시작
        current_date = today

        # 배치 상태 저장
        batches = []
        for _, row in g.iterrows():
            init_days = int(row[days_col])
            init_qty = float(row[qty_col])
            batches.append({
                "prod_key": prod_key,
                "batch": row[batch_col],
                "init_days": init_days,
                "qty": init_qty
            })

        # helper: 특정 날짜에서 남은 일수 계산(시간 경과 반영)
        def remaining_days(init_days, date_):
            return init_days - (date_ - today).days

        # 배치들을 순서대로 처리
        for b in batches:
            batch_id = b["batch"]
            init_days = b["init_days"]
            init_qty = b["qty"]

            # 위험진입일(언제 D-180 되는지)
            if init_days <= risk_days:
                risk_entry_date = today
            else:
                risk_entry_date = today + timedelta(days=(init_days - risk_days))

            # 배치에 도착한 시점(현재시간)에서 남은 일수
            days_now = remaining_days(init_days, current_date)

            # 기록용 변수
            sell_start_date = None
            sell_end_date = None
            stop_reason = None
            qty_sold_total = 0.0
            months_sold = 0
            sold_days_total = 0  # ✅ 부분판매를 위해 실제 판매일수 누적

            # 판매량 0이면 판매 불가
            if monthly_sales <= 0:
                sell_start_date = None
                sell_end_date = current_date
                stop_reason = "no_sales"
                days_left_at_stop = remaining_days(init_days, current_date)

                detail_rows.append({
                    product_cols[0]: prod_key[0] if isinstance(prod_key, tuple) else prod_key,
                    product_cols[1]: prod_key[1] if isinstance(prod_key, tuple) and len(prod_key) > 1 else None,
                    batch_col: batch_id,
                    "init_qty": init_qty,
                    "init_days": init_days,
                    "risk_entry_date": risk_entry_date,
                    "sell_start_date": sell_start_date,
                    "sell_end_date": sell_end_date,
                    "months_sold": months_sold,
                    "sold_days_total": sold_days_total,
                    "qty_sold": qty_sold_total,
                    "remaining_qty": max(0.0, b["qty"]),
                    "days_left_at_stop": days_left_at_stop,
                    "stop_reason": stop_reason
                })
                continue

            # 이미 위험 구간이면 시작도 못함
            if days_now <= risk_days:
                sell_start_date = None
                sell_end_date = current_date
                stop_reason = "risk_reached_before_start"
                days_left_at_stop = days_now

                detail_rows.append({
                    product_cols[0]: prod_key[0] if isinstance(prod_key, tuple) else prod_key,
                    product_cols[1]: prod_key[1] if isinstance(prod_key, tuple) and len(prod_key) > 1 else None,
                    batch_col: batch_id,
                    "init_qty": init_qty,
                    "init_days": init_days,
                    "risk_entry_date": risk_entry_date,
                    "sell_start_date": sell_start_date,
                    "sell_end_date": sell_end_date,
                    "months_sold": months_sold,
                    "sold_days_total": sold_days_total,
                    "qty_sold": qty_sold_total,
                    "remaining_qty": max(0.0, b["qty"]),
                    "days_left_at_stop": days_left_at_stop,
                    "stop_reason": stop_reason
                })
                continue

            # (2)(3)(4) 판매 시뮬레이션
            sell_start_date = current_date
            daily_sales = monthly_sales / step_days if step_days > 0 else 0.0

            while True:
                days_now = remaining_days(init_days, current_date)

                # ✅ 위험 도달(=D-180 이하) 즉시 판매 중단
                if days_now <= risk_days:
                    sell_end_date = current_date
                    stop_reason = "risk_reached"
                    break

                # 재고 0이면 종료
                if b["qty"] <= 0:
                    sell_end_date = current_date
                    stop_reason = "sold_out"
                    break

                next_date = current_date + timedelta(days=step_days)
                days_until_risk = (risk_entry_date - current_date).days  # 위험진입까지 남은 일수

                # ✅ 이번 30일 구간 중간에 risk_entry_date가 들어오면:
                # risk_entry_date 직전까지만 "부분판매(일할)" 후 즉시 중단
                if 0 < days_until_risk < step_days:
                    sellable_days = days_until_risk
                    sellable_qty = daily_sales * sellable_days

                    sell_qty = min(b["qty"], sellable_qty)
                    b["qty"] -= sell_qty
                    qty_sold_total += sell_qty
                    sold_days_total += sellable_days

                    # 시간은 위험진입일로 정확히 이동
                    current_date = risk_entry_date

                    sell_end_date = current_date
                    stop_reason = "risk_reached"
                    break

                # ✅ 이번 구간에는 위험진입 없음 => 30일치 정상 판매
                sell_qty = min(b["qty"], monthly_sales)
                b["qty"] -= sell_qty
                qty_sold_total += sell_qty
                months_sold += 1
                sold_days_total += step_days

                current_date = next_date

            days_left_at_stop = remaining_days(init_days, sell_end_date)

            detail_rows.append({
                product_cols[0]: prod_key[0] if isinstance(prod_key, tuple) else prod_key,
                product_cols[1]: prod_key[1] if isinstance(prod_key, tuple) and len(prod_key) > 1 else None,
                batch_col: batch_id,
                "init_qty": init_qty,
                "init_days": init_days,
                "risk_entry_date": risk_entry_date,
                "sell_start_date": sell_start_date,
                "sell_end_date": sell_end_date,
                "months_sold": months_sold,
                "sold_days_total": sold_days_total,
                "qty_sold": qty_sold_total,
                "remaining_qty": max(0.0, b["qty"]),
                "days_left_at_stop": days_left_at_stop,
                "stop_reason": stop_reason
            })

        # updated_df에 반영: 제품/배치 기준으로 qty 업데이트
        for b in batches:
            updated.loc[
                (updated[product_cols[0]] == (prod_key[0] if isinstance(prod_key, tuple) else prod_key)) &
                (updated[batch_col] == b["batch"]),
                qty_col
            ] = max(0.0, b["qty"])

    detail_df = pd.DataFrame(detail_rows)
    return detail_df, updated

# -----------------------------------------------------
# 5️⃣ 재고소진시뮬레이션 + 소분류 간트 차트 (ON)
# -----------------------------------------------------
# =========================================================
# 0) 준비: 시뮬레이션 실행 → gantt_df 생성
# =========================================================
base_today = datetime.now().date()

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

gantt_df = detail_df.copy()

# 소분류 붙이기
if "소분류" not in gantt_df.columns:
    mat_to_cls = final_df[[MAT_COL, "대분류", "소분류"]].drop_duplicates(subset=[MAT_COL])
    gantt_df = gantt_df.merge(mat_to_cls, on=MAT_COL, how="left")
    gantt_df["소분류"] = gantt_df["소분류"].fillna("미분류")

# no_sales 제외
if "stop_reason" in gantt_df.columns:
    gantt_df = gantt_df[gantt_df["stop_reason"] != "no_sales"].copy()

# 날짜 컬럼 datetime 변환
for c in ["sell_start_date", "sell_end_date", "risk_entry_date"]:
    if c in gantt_df.columns:
        gantt_df[c] = pd.to_datetime(gantt_df[c], errors="coerce")

# 판매 시작/끝 없는 행 제외
gantt_df = gantt_df.dropna(subset=["sell_start_date", "sell_end_date"]).copy()

# =========================================================
# 1) 소분류 선택 UI
# =========================================================
with st.container():
    st.markdown("### 🗓️ 소분류별 배치 판매 시뮬레이션")
    
    gantt_df["mat_label"] = gantt_df[MAT_COL].astype(str) + " | " + gantt_df[MAT_NAME_COL].astype(str)

# ✅ 부진재고(remaining_qty > 0)가 있는 소분류만 필터링
risk_subcats = gantt_df[gantt_df["remaining_qty"].fillna(0) > 0]["소분류"].unique().tolist()

subcat_meta = (
    gantt_df[gantt_df["소분류"].isin(risk_subcats)]
    .fillna("미분류")
    .drop_duplicates(subset=["소분류"], keep="first")
    .copy()
)

if subcat_meta.empty:
    st.info("현재 분석 데이터 중 '부진재고'가 발생하는 품목이 없습니다.")
    st.stop()

subcat_meta["ui_label"] = (
    subcat_meta["대분류"].astype(str)
    + "("
    + subcat_meta["소분류"].astype(str)
    + ") | "
    + subcat_meta["소분류"].astype(str)
)

label_to_subcat = dict(zip(subcat_meta["ui_label"], subcat_meta["소분류"]))
ui_options = ["(전체)"] + sorted(subcat_meta["ui_label"].unique().tolist())
selected_ui = st.selectbox("소분류 선택 (부진재고 발생 소분류만 표시)", options=ui_options)

selected_subcat = None if selected_ui == "(전체)" else label_to_subcat[selected_ui]

# (전체) 선택 시에도 '부진재고'가 있는 데이터만 보여주고 싶다면 아래 필터 추가 가능
# 여기서는 사용자가 "해당 애들만 선택해서... 보여주도록" 했으므로, 
# view_df 자체도 부진재고가 있는 subcat들로 제한합니다.
if selected_subcat is None:
    view_df = gantt_df[gantt_df["소분류"].isin(risk_subcats)].copy()
else:
    view_df = gantt_df[gantt_df["소분류"].fillna("미분류") == selected_subcat].copy()

if selected_subcat is not None:
    st.caption(
        f"선택 소분류: {selected_ui}  |  제품 수: {view_df[MAT_COL].nunique()}개 / 배치 수: {view_df[BATCH_COL].nunique()}개"
    )

# =========================================================
# 1.5) 부진재고 요약 지표 (KPI) - (전체) 및 소분류 공통
# =========================================================
risk_view_df = view_df[view_df["remaining_qty"].fillna(0) > 0].copy()
if not risk_view_df.empty:
    # 단위원가 정보가 없으면 final_df에서 가져옴
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

# =========================================================
# 2) [방법 A] 최소 배수(minmult_df) 먼저 계산
#    → 그 다음 요약 표(table_df)에 merge해서 "한 표"로 출력
# =========================================================
if selected_ui != "(전체)" and (not view_df.empty):

    # ✅ 기준(1.0x)에서 부진재고가 남는 row만
    base_risk_df = view_df[view_df["remaining_qty"].fillna(0) > 0].copy()

    if base_risk_df.empty:
        st.success("현재 소분류는 기준 평판(1.0x) 시나리오에서 부진재고가 없습니다.")
    else:
        # ---------------------------------------------------------
        # (A-1) 최소 배수 계산 대상 자재 목록
        # ---------------------------------------------------------
        risk_mats = base_risk_df[MAT_COL].dropna().unique().tolist()
        sub_df_base = final_df[final_df[MAT_COL].isin(risk_mats)].copy()

        # st.write("### 🎯 (부진재고 발생 자재만) 부진재고 0을 위한 최소 평판 배수 (소분류 기준)")
        # st.caption("※ 기준(1.0x)에서 부진재고가 발생한 자재만 대상으로 최소 배수를 계산합니다.")

        if "3평판" not in sub_df_base.columns:
            st.warning("final_df에 '3평판' 컬럼이 없어 최소 배수를 계산할 수 없습니다.")
            minmult_df = pd.DataFrame(columns=["자재코드", "자재내역", "3평판", "부진재고 0을 위한 최소 배수(추정)", "비고"])
        else:
            sales_series = pd.to_numeric(sub_df_base["3평판"], errors="coerce").fillna(0)
            if sales_series.sum() <= 0:
                st.warning("이 소분류는 3평판 값이 0(또는 없음)이라 최소 배수를 계산할 수 없습니다.")
                minmult_df = pd.DataFrame(columns=["자재코드", "자재내역", "3평판", "부진재고 0을 위한 최소 배수(추정)", "비고"])
            else:
                # ---------- 유틸 ----------
                def _risk_summary(detail_k: pd.DataFrame):
                    risk_k = detail_k[detail_k["remaining_qty"].fillna(0) > 0].copy()

                    risk_qty = float(
                        pd.to_numeric(risk_k["remaining_qty"], errors="coerce").fillna(0).sum()
                    ) if not risk_k.empty else 0.0

                    if (not risk_k.empty) and ("remaining_amount" in risk_k.columns):
                        risk_amt = float(pd.to_numeric(risk_k["remaining_amount"], errors="coerce").fillna(0).sum())
                    else:
                        if (not risk_k.empty) and ("단위원가" in risk_k.columns):
                            uc = pd.to_numeric(risk_k["단위원가"], errors="coerce").fillna(0)
                            rq = pd.to_numeric(risk_k["remaining_qty"], errors="coerce").fillna(0)
                            risk_amt = float((rq * uc).sum())
                        else:
                            risk_amt = np.nan
                    return {"risk_qty": risk_qty, "risk_amt": risk_amt}

                def _run_sim_mat(df_mat: pd.DataFrame, mult: float):
                    df_in = df_mat.copy()
                    df_in["_sales_k"] = pd.to_numeric(df_in["3평판"], errors="coerce").fillna(0) * mult

                    detail_k, _ = simulate_batches_by_product(
                        df=df_in,
                        product_cols=(MAT_COL, MAT_NAME_COL),
                        batch_col=BATCH_COL,
                        days_col=DAYS_COL,
                        qty_col=QTY_SRC_COL,
                        monthly_sales_col="_sales_k",
                        risk_days=180,
                        step_days=30,
                        today=base_today,
                    )
                    return detail_k

                def _risk_metric_mat(df_mat: pd.DataFrame, mult: float) -> float:
                    detail_k = _run_sim_mat(df_mat, mult)
                    s = _risk_summary(detail_k)
                    if not np.isnan(s["risk_amt"]):
                        return s["risk_amt"]
                    return s["risk_qty"]

                def _find_min_multiplier_mat(df_mat: pd.DataFrame, lo=1.0, hi=6.0, tol=1e-3, max_iter=50):
                    if _risk_metric_mat(df_mat, lo) <= 0:
                        return lo
                    if _risk_metric_mat(df_mat, hi) > 0:
                        return None

                    a, b = lo, hi
                    for _ in range(max_iter):
                        mid = (a + b) / 2
                        v = _risk_metric_mat(df_mat, mid)
                        if v > 0:
                            a = mid
                        else:
                            b = mid
                        if (b - a) < tol:
                            break
                    return b

                # ---------- 계산 ----------
                minmult_rows = []
                for mat in sorted(sub_df_base[MAT_COL].dropna().unique().tolist()):
                    df_mat = sub_df_base[sub_df_base[MAT_COL] == mat].copy()

                    mat_name = ""
                    if MAT_NAME_COL in df_mat.columns and df_mat[MAT_NAME_COL].notna().any():
                        mat_name = str(df_mat[MAT_NAME_COL].dropna().iloc[0])

                    base_sales = float(pd.to_numeric(df_mat["3평판"], errors="coerce").fillna(0).iloc[0])

                    if base_sales <= 0:
                        minmult_rows.append({
                            "자재코드": mat,
                            "자재내역": mat_name,
                            "3평판": base_sales,
                            "부진재고 0을 위한 최소 배수(추정)": "- (3평판=0)",
                            "비고": "판매량 0 → 배수로 개선 불가",
                        })
                        continue

                    min_m = _find_min_multiplier_mat(df_mat, lo=1.0, hi=6.0)

                    minmult_rows.append({
                        "자재코드": mat,
                        "자재내역": mat_name,
                        "3평판": base_sales,
                        "부진재고 0을 위한 최소 배수(추정)": "-" if min_m is None else f"{min_m:.2f}x",
                        "비고": "20.0x까지도 0이 안 됨" if min_m is None else "D-180 기준 잔존 0 달성",
                    })

                minmult_df = pd.DataFrame(minmult_rows).sort_values(["자재코드"]).reset_index(drop=True)

        # ---------------------------------------------------------
        # (A-2) 요약표(table_df) 생성 + minmult_df를 "한 표"로 merge
        # ---------------------------------------------------------
        st.write(f"### 🧾 부진재고 요약 (소분류: {selected_subcat})")

        summary_df = view_df[view_df["remaining_qty"].fillna(0) > 0].copy()
        summary_df = summary_df.sort_values(["risk_entry_date", "init_days"], ascending=[True, True])

        UNIT_COST_COL = "단위원가"
        if UNIT_COST_COL not in summary_df.columns:
            unit_cost_map = (
                final_df[[MAT_COL, UNIT_COST_COL]]
                .dropna(subset=[MAT_COL, UNIT_COST_COL])
                .drop_duplicates(subset=[MAT_COL])
            )
            summary_df = summary_df.merge(unit_cost_map, on=MAT_COL, how="left")

        summary_df[UNIT_COST_COL] = pd.to_numeric(summary_df[UNIT_COST_COL], errors="coerce").fillna(0)
        summary_df["remaining_amount"] = summary_df["remaining_qty"].fillna(0) * summary_df[UNIT_COST_COL]

        # KPI (위에서 공통으로 표시하므로 여기서는 상세 표 제목만 유지하거나 생략 가능)
        # 여기서는 이미 위에서 요약 지표를 보여주었으므로, 표 바로 위에는 제목만 남깁니다.
        # st.write(f"### 🧾 부진재고 상세 (소분류: {selected_subcat})")
        # 대신 risk_view_df를 활용하여 아래 표(summary_df)를 구성합니다.
        summary_df = risk_view_df.copy()
        summary_df = summary_df.sort_values(["risk_entry_date", "init_days"], ascending=[True, True])

        # table_df
        table_df = summary_df.copy()
        table_df = table_df.rename(columns={
            MAT_COL: "자재코드",
            MAT_NAME_COL: "자재내역",
            BATCH_COL: "배치",
            "risk_entry_date": "부진재고 진입일",
            "remaining_qty": "예상부진재고량",
            "remaining_amount": "예상부진금액",
        })

        # ✅ minmult_df(자재 단위) 붙이기
        mult_map = minmult_df[["자재코드", "3평판", "부진재고 0을 위한 최소 배수(추정)", "비고"]].drop_duplicates(subset=["자재코드"])
        table_df = table_df.merge(mult_map, on="자재코드", how="left")

        # ✅ 최소배수 문자열("1.20x") -> float(1.20)로 파싱
        def parse_multiplier(v):
            if pd.isna(v):
                return np.nan
            s = str(v).strip()
            # "-", "- (3평판=0)" 같은 케이스
            if s == "-" or s.startswith("-"):
                return np.nan
            m = re.search(r"([0-9]*\.?[0-9]+)\s*x", s.lower())
            return float(m.group(1)) if m else np.nan

        # 1) 숫자형 3평판 확보 (계산용 원본)
        sales_num = pd.to_numeric(table_df["3평판"], errors="coerce")

        # 2) 최소배수 float
        mult_num = table_df["부진재고 0을 위한 최소 배수(추정)"].apply(parse_multiplier)

        # 3) 권장 판매량 / 판매 개선율(%)
        table_df["권장 판매량"] = (sales_num * mult_num).round(0)
        table_df["판매 개선율(%)"] = ((mult_num - 1.0) * 100).round(0)

        # 4) 표시 포맷 (최소배수 없는 애들은 빈칸)
        table_df["권장 판매량"] = pd.to_numeric(table_df["권장 판매량"], errors="coerce").apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "-"
        )
        table_df["판매 개선율(%)"] = pd.to_numeric(table_df["판매 개선율(%)"], errors="coerce").apply(
            lambda x: f"{int(x)}% 증가" if pd.notna(x) else "-"
        )

        # 표시 컬럼
        show_cols = [
                    "자재코드",
                    "자재내역",
                    "배치",
                    "3평판",
                    "부진재고 진입일",
                    "예상부진재고량",
                    "예상부진금액",
                    "권장 판매량",
                    "판매 개선율(%)",
                ]
        show_cols = [c for c in show_cols if c in table_df.columns]
        table_df = table_df[show_cols].copy()

        # 정렬
        if "부진재고 진입일" in table_df.columns:
            table_df = table_df.sort_values(["부진재고 진입일", "예상부진금액"], ascending=[True, False])

        # 포맷
        if "부진재고 진입일" in table_df.columns:
            table_df["부진재고 진입일"] = pd.to_datetime(table_df["부진재고 진입일"], errors="coerce").dt.strftime("%Y-%m-%d")

        if "예상부진재고량" in table_df.columns:
            table_df["예상부진재고량"] = (
                pd.to_numeric(table_df["예상부진재고량"], errors="coerce")
                .fillna(0).astype(int).map(lambda x: f"{x:,}")
            )

        if "예상부진금액" in table_df.columns:
            table_df["예상부진금액"] = (
                pd.to_numeric(table_df["예상부진금액"], errors="coerce")
                .fillna(0).map(lambda x: f"₩{x:,.0f}")
            )

        if "3평판" in table_df.columns:
            # minmult_df에서 들어온 3평판은 숫자일 수도/문자일 수도 있어서 안전 변환
            _sales = pd.to_numeric(table_df["3평판"], errors="coerce").fillna(0).astype(int)
            table_df["3평판"] = _sales.map(lambda x: f"{x:,}")

        # ✅ 한 표 출력
        st.dataframe(table_df, use_container_width=True, height=320)

# =========================================================
# 3) 간트 차트 생성/표시
# =========================================================
if view_df.empty:
    st.info("표시할 데이터가 없습니다. (no_sales 제외 후 남은 배치가 없거나, sell_start/end가 비어있을 수 있어요.)")
else:
    view_df = view_df.copy()
    view_df["expiry_date"] = pd.to_datetime(base_today) + pd.to_timedelta(view_df["init_days"], unit="D")

    sales_bar = view_df.copy()
    sales_bar["phase"] = "판매기간"
    sales_bar = sales_bar.rename(columns={"sell_start_date": "x_start", "sell_end_date": "x_end"})

    sluggish_bar = view_df.copy()
    sluggish_bar = sluggish_bar[sluggish_bar["remaining_qty"].fillna(0) > 0].copy()
    sluggish_bar = sluggish_bar.dropna(subset=["risk_entry_date", "expiry_date"]).copy()
    sluggish_bar["phase"] = "부진재고 구간"
    sluggish_bar = sluggish_bar.rename(columns={"risk_entry_date": "x_start", "expiry_date": "x_end"})

    plot_df = pd.concat([sales_bar, sluggish_bar], ignore_index=True)
    plot_df["batch_label"] = plot_df["mat_label"].astype(str) + " | " + plot_df[BATCH_COL].astype(str)

    plot_df = plot_df.sort_values(["mat_label", "init_days", "phase"], ascending=[True, True, True])

    color_map = {"판매기간": "#4C78A8", "부진재고 구간": "#E45756"}

    order_base = plot_df[plot_df["phase"] == "판매기간"].copy()
    if order_base.empty:
        order_base = plot_df.copy()

    order_meta = (
        order_base[["batch_label", "mat_label", "x_start"]]
        .drop_duplicates(subset=["batch_label"])
        .rename(columns={"x_start": "sell_start"})
    )

    order_meta = order_meta.sort_values(["mat_label", "sell_start", "batch_label"], ascending=[True, True, True])
    y_order = order_meta["batch_label"].tolist()

    plot_df = plot_df.merge(order_meta[["batch_label", "sell_start"]], on="batch_label", how="left")
    plot_df = plot_df.sort_values(["mat_label", "sell_start", "phase"], ascending=[True, True, True])

    fig = px.timeline(
        plot_df,
        x_start="x_start",
        x_end="x_end",
        y="batch_label",
        color="phase",
        color_discrete_map=color_map,
        hover_data={
            MAT_COL: True,
            MAT_NAME_COL: True,
            "소분류": True if "소분류" in plot_df.columns else False,
            "stop_reason": True if "stop_reason" in plot_df.columns else False,
            "init_days": True if "init_days" in plot_df.columns else False,
            "init_qty": True if "init_qty" in plot_df.columns else False,
            "qty_sold": True if "qty_sold" in plot_df.columns else False,
            "remaining_qty": True if "remaining_qty" in plot_df.columns else False,
            "sold_days_total": True if "sold_days_total" in plot_df.columns else False,
            "risk_entry_date": True if "risk_entry_date" in plot_df.columns else False,
            "expiry_date": True if "expiry_date" in plot_df.columns else False,
        },
    )

    fig.update_yaxes(categoryorder="array", categoryarray=y_order)
    fig.update_yaxes(autorange="reversed")

    # ✅ 배치 수에 따른 동적 높이 계산 (최소 400px, 배치당 30px + 여백)
    dynamic_height = max(400, len(y_order) * 30 + 120)

    fig.update_layout(
        height=dynamic_height,
        margin=dict(t=50, b=50, l=10, r=10),
        xaxis_title="Simulation Timeline",
        yaxis_title="Material | Batch",
        xaxis_title_font=dict(size=14),
        yaxis_title_font=dict(size=14),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    fig.update_xaxes(
        showgrid=True, 
        gridcolor="#f1f5f9", 
        gridwidth=1,
        dtick="M1", # 매달 그리드
        tickformat="%Y-%m",
        tickfont=dict(size=12)
    )
    fig.update_yaxes(
        showgrid=True, 
        gridcolor="#f1f5f9", 
        gridwidth=1,
        tickfont=dict(size=11)
    )
    
    # 바 테두리 및 투명도 조절
    fig.update_traces(marker_line_color='white', marker_line_width=1, opacity=0.9)

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------
# 7️⃣ 가공된 데이터 최종 등록 (계층: 연도 -> 월 -> 분석타입) (ON)
# -----------------------------------------------------
if "stock_data" not in st.session_state:
    st.session_state["stock_data"] = {}

# 1. 연도 폴더 생성
if selected_year not in st.session_state["stock_data"]:
    st.session_state["stock_data"][selected_year] = {}

# 2. 월 폴더 생성
if selected_month not in st.session_state["stock_data"][selected_year]:
    st.session_state["stock_data"][selected_year][selected_month] = {}

# 3. "유효기한 데이터"라는 이름으로 최종 저장
st.session_state["stock_data"][selected_year][selected_month]["유효기한"] = {
    "df": final_df,
    "processed_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

st.sidebar.success(f"✅ {selected_year} {selected_month} 유효기한 분석 완료")
with st.container():
    st.write("---")
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

