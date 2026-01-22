import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os
import plotly.express as px
import matplotlib.ticker as ticker
import plotly.graph_objects as go

# ✅ 페이지 설정
st.set_page_config(page_title="Stock Data Analysis", layout="wide")
st.title("📈 Stock Data Analysis")

# ✅ 상수 설정 (기본 유지)
PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"
SALES_DF_KEY = "5. 3개월 매출(자재별).xls"

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
    merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL]], on=MAT_COL, how="left")
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
    
    # # 4. 최종 데이터프레임에 '3평판' 열 추가 (자재코드 기준 매핑)
    # merged = merged.merge(
    #     sales_avg[['자재코드', '3평판']], 
    #     left_on=MAT_COL, 
    #     right_on='자재코드', 
    #     how="left"
    # )
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
    
    # (선택사항) '재고 보유 월수(MOI)' 지표 추가 가능
    # merged['재고월수'] = merged.apply(lambda r: r[QTY_SRC_COL] / r['3평판'] if r['3평판'] > 0 else 999, axis=1)
    
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
available_years = sorted(list(all_dfs_store.keys()))
selected_year = st.sidebar.selectbox("📅 연도 선택", options=available_years)

year_data = all_dfs_store.get(selected_year, {})
available_months = sorted(list(year_data.keys()))

if not available_months:
    st.error(f"{selected_year}에 저장된 월 데이터가 없습니다.")
    st.stop()

selected_month = st.sidebar.selectbox("📆 월 선택", options=available_months)

# 선택된 연도/월의 데이터 뭉치 가져오기
target_dfs = year_data[selected_month]

# -----------------------------------------------------
# ✅ 현재 분석에 사용되는 파일 정보 표시
# -----------------------------------------------------
with st.expander(f"📁 {selected_year} {selected_month} 분석 대상 파일 확인", expanded=False):
    file_info = []
    for f_name, f_df in target_dfs.items():
        file_info.append({"파일명": f_name, "행 수": len(f_df), "컬럼 수": f_df.shape[1]})
    st.table(pd.DataFrame(file_info))

# 최종 가공 데이터 생성
with st.spinner(f"{selected_year} {selected_month} 데이터를 통합 분석 중입니다..."):
    final_df = build_final_df(target_dfs, selected_year, selected_month)

# -----------------------------------------------------
# 1️⃣ 기간별 위험 자재 요약 (탭)
# -----------------------------------------------------
st.subheader(f"🚨 {selected_year} {selected_month} 기간별 위험 자재 요약")
tab6, tab7, tab9 = st.tabs(["⚠️ 6개월 미만", "🔔 7개월 미만", "ℹ️ 9개월 미만"])

def display_risk_summary(target_buckets, tab_obj, title):
    with tab_obj:
        risk_df = final_df[final_df[BUCKET_COL].isin(target_buckets)].copy()
        if risk_df.empty:
            st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
        else:
            summary = (
                risk_df.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[[QTY_SRC_COL, VALUE_COL]]
                .sum()
                .sort_values(VALUE_COL, ascending=False)
                .reset_index(drop=True)
            )
            m1, m2, m3 = st.columns([1, 1, 3])
            m1.metric(f"{title} 자재 수", f"{len(summary)}종")
            m2.metric(f"총 위험 금액", f"₩{summary[VALUE_COL].sum():,.0f}")
            with m3:
                disp = summary.copy()
                disp[VALUE_COL] = disp[VALUE_COL].map('{:,.0f}'.format)
                disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map('{:,.0f}'.format)
                st.dataframe(disp, use_container_width=True, height=400)

risk_base = ["폐기확정(유효기한 지남)", "3개월 미만"]
display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만"], tab7, "7개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만", "9개월 미만"], tab9, "9개월 미만")

st.divider()

# -----------------------------------------------------
# 2️⃣ 자재-배치 단위 상세 분석 및 시각화
# -----------------------------------------------------
def render_batch_analysis_section(final_df, MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL):
    """
    자재-배치별 상세 분석 섹션을 렌더링하는 함수입니다.
    기존 로직을 그대로 유지하며 매개변수로 필요한 상수들을 받습니다.
    """
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
                fig, ax = plt.subplots(figsize=(8, 2.5)) 
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
render_batch_analysis_section(final_df, MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL)


# -----------------------------------------------------
# 💾 국가별 재고 가치 분포(지도), 요약 지표(Metric), 상세 리스크 테이블 시각화 
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
render_country_stock_analysis(final_df, VALUE_COL, BUCKET_COL, selected_year, selected_month)


# -----------------------------------------------------
# 💾 재고소진시뮬레이션
# -----------------------------------------------------

def render_future_risk_simulation(final_df):
    st.divider()
    st.subheader("🔮 향후 유효기한 리스크 시뮬레이션 (판매 속도 반영)")
    st.info("실제 판매 속도(3평판)를 기반으로 유효기한이 180일(6개월) 남은 시점의 예상 잔고를 산출합니다.")

    # 1. 데이터 필터링: 12개월 전후이면서 판매 실적(3평판)이 있는 데이터
    sim_targets = ["12개월 미만", "12개월 이상"]
    df_sim = final_df[
        (final_df[BUCKET_COL].isin(sim_targets)) & 
        (final_df['3평판'] >= 1)
    ].copy()

    if df_sim.empty:
        st.warning("시뮬레이션 대상 자재(12개월 전후 & 판매실적 존재)가 없습니다.")
        return

    # 2. 시뮬레이션 로직 함수 (배치별 적용)
    def run_simulation(row):
        days_left = row[DAYS_COL]
        qty_left = row[QTY_SRC_COL]
        monthly_sales = row['3평판']
        # 유효기한이 180일 남을 때까지 30일 단위로 판매량 차감
        while days_left > 180 and qty_left > 0:
            days_left -= 30
            qty_left -= monthly_sales
        return max(0, qty_left)

    df_sim['예비위험재고수량'] = df_sim.apply(run_simulation, axis=1)
    df_sim['예비위험금액'] = df_sim['예비위험재고수량'] * df_sim[UNIT_COST_COL]
    
    # 예비위험재고가 1개라도 남을 것으로 예측되는 데이터만 추출
    risk_summary = df_sim[df_sim['예비위험재고수량'] > 0].copy()
    
    # --- [섹션 1] 상단 요약 지표 ---
    m1, m2, m3 = st.columns(3)
    m1.metric("탐지된 위험 배치 수", f"{len(risk_summary)}개")
    m2.metric("예상 위험 금액 (합계)", f"₩{risk_summary['예비위험금액'].sum():,.0f}")
    m3.info("💡 180일(6개월) 시점에 재고가 남는 배치만 리스트업됩니다.")

    # --- [섹션 2] 상세 리스트 ---
    st.write("#### 📋 예비 위험 탐지 상세 리스트 (배치 단위)")
    display_cols = [MAT_COL, MAT_NAME_COL, BATCH_COL, DAYS_COL, '3평판', '예비위험재고수량', '예비위험금액']
    st.dataframe(
        risk_summary[display_cols].sort_values('예비위험금액', ascending=False), 
        use_container_width=True,
        height=300
    )

    st.write("---")

    # --- [섹션 3] 자재 및 배치별 심층 분석 시각화 ---
    st.write("#### 📈 배치별 소진 시뮬레이션 상세 확인")
    
    # 1단계: 자재 선택
    risk_summary['mat_label'] = risk_summary[MAT_COL].astype(str) + " | " + risk_summary[MAT_NAME_COL].astype(str)
    selected_mat = st.selectbox("1. 분석할 자재를 선택하세요", options=sorted(risk_summary['mat_label'].unique()))

    if selected_mat:
        # 2단계: 선택한 자재 내의 배치 선택
        mat_only_df = risk_summary[risk_summary['mat_label'] == selected_mat]
        selected_batch = st.selectbox(
            "2. 상세 확인 배치(Batch)를 선택하세요", 
            options=mat_only_df[BATCH_COL].unique(),
            help="동일 자재라도 배치별 유효기한이 다르므로 개별 확인이 필요합니다."
        )

        if selected_batch:
            # 최종 타겟 행 추출
            target_row = mat_only_df[mat_only_df[BATCH_COL] == selected_batch].iloc[0]
            
            # 날짜 계산
            today = datetime.now()
            target_date_180 = today + pd.Timedelta(days=int(target_row[DAYS_COL]) - 180)
            expiry_date = today + pd.Timedelta(days=int(target_row[DAYS_COL]))

            # 정보 박스 시각화
            st.write(f"##### 🔍 [{selected_batch}] 배치 분석 정보")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.write("**현재 재고**"); st.write(f"{target_row[QTY_SRC_COL]:,.0f}")
            with c2: st.write("**월평균 판매(3평판)**"); st.write(f"{target_row['3평판']:,.2f}")
            with c3: st.write("**위험 도달일 (D-180)**"); st.write(f":red[{target_date_180.strftime('%Y-%m-%d')}]")
            with c4: st.write("**유효기한 만료일**"); st.write(f"{expiry_date.strftime('%Y-%m-%d')}")

            # 시뮬레이션 그래프 데이터 생성 (30일 간격 틱)
            history_days = []
            history_qty = []
            curr_days = target_row[DAYS_COL]
            curr_qty = target_row[QTY_SRC_COL]
            sales_per_tick = target_row['3평판']

            while curr_days > -30 and curr_qty > -sales_per_tick:
                history_days.append(curr_days)
                history_qty.append(max(0, curr_qty))
                curr_days -= 30
                curr_qty -= sales_per_tick

            # 그래프 시각화
            fig, ax = plt.subplots(figsize=(8, 2.5))
            ax.plot(history_days, history_qty, marker='o', color='#e74c3c', linewidth=2, label='예상 재고 흐름')
            ax.axvline(x=180, color='blue', linestyle='--', alpha=0.6, label='위험 경계 (D-180)')
            ax.fill_between(history_days, history_qty, color='#e74c3c', alpha=0.1)

            ax.set_title(f"자재: {selected_mat} / 배치: {selected_batch}", fontsize=12, pad=15)
            ax.set_xlabel("남은 유효기한 (Days)")
            ax.set_ylabel("재고 수량")
            ax.invert_xaxis()  # 날짜가 줄어드는 흐름 표현
            ax.legend()
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            
            st.pyplot(fig)
            
            # 최종 코멘트
            st.warning(f"⚠️ **시뮬레이션 요약**: 이 배치는 **{target_date_180.strftime('%Y년 %m월 %d일')}**에 위험 구간(D-180)에 진입합니다. "
                       f"평균 판매 속도 유지 시 해당 시점에 약 **{target_row['예비위험재고수량']:,.0f}**개의 재고가 소진되지 못하고 남을 것으로 예측됩니다.")


render_future_risk_simulation(final_df)

# -----------------------------------------------------
# 💾 가공된 데이터 최종 등록 (계층: 연도 -> 월 -> 분석타입)
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
st.write("---")
d1, d2, _ = st.columns([1, 1, 2])
with d1:
    csv_bytes = final_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ CSV 다운로드", 
        data=csv_bytes, 
        file_name=f"{selected_year}_{selected_month}_유효기한.csv", 
        mime="text/csv"
    )

