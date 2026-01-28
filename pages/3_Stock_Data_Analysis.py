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
# 💾 재고소진시뮬레이션 (FEFO + D-180 도달 즉시 판매중단)
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


# =====================================================
# 아래는 Streamlit에서 그려주는 전체 흐름
# (final_df, MAT_COL 등은 네 기존 코드에서 만들어진 걸 그대로 사용)
# =====================================================

# 예시: 네 코드에서 이미 정의돼있을 변수들
# MAT_COL = "자재"
# MAT_NAME_COL = "자재 내역"
# BATCH_COL = "배치"
# DAYS_COL = "유효 기한"
# QTY_SRC_COL = "Stock Quantity on Period End"

base_today = datetime.now().date()

# ✅ 시뮬레이션 실행
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

# no_sales 제외
if "stop_reason" in gantt_df.columns:
    gantt_df = gantt_df[gantt_df["stop_reason"] != "no_sales"].copy()

# 날짜 컬럼 datetime으로 변환 (Plotly timeline용)
for c in ["sell_start_date", "sell_end_date", "risk_entry_date"]:
    if c in gantt_df.columns:
        gantt_df[c] = pd.to_datetime(gantt_df[c], errors="coerce")

# 판매 시작/끝 없는 행 제외
gantt_df = gantt_df.dropna(subset=["sell_start_date", "sell_end_date"]).copy()

st.write("### 🗓️ 제품별 배치 판매 간트 차트 (no_sales 제외)")

# -----------------------------
# 2) 제품 선택 UI
# -----------------------------
gantt_df["mat_label"] = gantt_df[MAT_COL].astype(str) + " | " + gantt_df[MAT_NAME_COL].astype(str)

prod_list = sorted(gantt_df["mat_label"].unique())
selected_prod = st.selectbox("제품 선택", options=["(전체)"] + prod_list)

view_df = gantt_df if selected_prod == "(전체)" else gantt_df[gantt_df["mat_label"] == selected_prod].copy()

# -----------------------------
# 3) 간트 차트 (판매기간 + 부진재고 구간)
# -----------------------------
if view_df.empty:
    st.info("표시할 데이터가 없습니다. (no_sales 제외 후 남은 배치가 없거나, sell_start/end가 비어있을 수 있어요.)")
else:
    # ✅ 만료일(expiry_date) 계산
    view_df["expiry_date"] = pd.to_datetime(base_today) + pd.to_timedelta(view_df["init_days"], unit="D")

    # ✅ 판매 구간
    sales_bar = view_df.copy()
    sales_bar["phase"] = "판매기간"
    sales_bar = sales_bar.rename(columns={"sell_start_date": "x_start", "sell_end_date": "x_end"})

    # ✅ 부진재고(잔존재고) 구간: remaining_qty > 0 인 배치만
    sluggish_bar = view_df.copy()
    sluggish_bar = sluggish_bar[sluggish_bar["remaining_qty"].fillna(0) > 0].copy()
    sluggish_bar = sluggish_bar.dropna(subset=["risk_entry_date", "expiry_date"]).copy()
    sluggish_bar["phase"] = "부진재고 구간"
    sluggish_bar = sluggish_bar.rename(columns={"risk_entry_date": "x_start", "expiry_date": "x_end"})

    # 합치기
    plot_df = pd.concat([sales_bar, sluggish_bar], ignore_index=True)

    # 배치 정렬 (유효기한 짧은 순 위로)
    plot_df = plot_df.sort_values(["mat_label", "init_days"], ascending=[True, True])

    # ✅ 색상 고정: 부진재고는 빨강
    color_map = {
        "판매기간": "#4C78A8",
        "부진재고 구간": "#E45756"
    }

    fig = px.timeline(
        plot_df,
        x_start="x_start",
        x_end="x_end",
        y=BATCH_COL,
        color="phase",
        color_discrete_map=color_map,
        hover_data={
            MAT_COL: True,
            MAT_NAME_COL: True,
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

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=550 if selected_prod == "(전체)" else 420,
        margin=dict(t=30, b=10, l=10, r=10),
        xaxis_title="기간",
        yaxis_title="배치",
        xaxis_title_font=dict(size=18, family="Arial Black"),
        yaxis_title_font=dict(size=18, family="Arial Black"),
        legend_title_text=""
    )

    fig.update_xaxes(
    tickfont=dict(size=14, family="Arial Black")
    )

    fig.update_yaxes(
        tickfont=dict(size=14, family="Arial Black")
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 4) ✅ 간트 아래 요약 문장 출력 (제품 선택 시 배치별)
# -----------------------------
if selected_prod != "(전체)" and (not view_df.empty):
    st.write("### 🧾 부진재고 요약 (배치별)")

    summary_df = view_df[view_df["remaining_qty"].fillna(0) > 0].copy()
    summary_df = summary_df.sort_values(["risk_entry_date", "init_days"], ascending=[True, True])

    if summary_df.empty:
        st.success("이 제품은 시뮬레이션 기준으로 D-180 시점에 부진재고로 남는 배치가 없습니다.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("부진재고 배치 수", f"{len(summary_df)}개")
        with c2:
            st.metric("부진재고 수량 합계", f"{summary_df['remaining_qty'].sum():,.0f}개")
        with c3:
            first_date = summary_df["risk_entry_date"].min()
            st.metric("가장 빠른 부진재고 진입일", first_date.strftime("%Y-%m-%d") if pd.notna(first_date) else "-")

        st.write("#### 📌 배치별 문장 요약")
        lines = []
        for _, r in summary_df.iterrows():
            b = r[BATCH_COL]
            dt = r["risk_entry_date"]
            qty = r["remaining_qty"]

            dt_str = dt.strftime("%Y-%m-%d") if pd.notna(dt) else "-"
            qty_str = f"{qty:,.0f}"

            # (원하면 sold_days_total도 같이 보여줄 수 있음)
            if "sold_days_total" in r and pd.notna(r["sold_days_total"]):
                sd = int(r["sold_days_total"])
                lines.append(
                    f"- 배치 **{b}**는 **{dt_str}**부터 부진재고(D-180) 구간에 진입하며, "
                    f"예상 잔량은 **{qty_str}개**입니다. (위험진입 전 판매일수: **{sd}일**)"
                )
            else:
                lines.append(
                    f"- 배치 **{b}**는 **{dt_str}**부터 부진재고(D-180) 구간에 진입하며, "
                    f"예상 잔량은 **{qty_str}개**입니다."
                )

        st.markdown("\n".join(lines))

        with st.expander("📋 부진재고 배치 리스트 보기"):
            show_cols = [
                BATCH_COL, "risk_entry_date", "expiry_date",
                "init_days", "init_qty", "qty_sold", "remaining_qty",
                "sold_days_total", "stop_reason"
            ]
            show_cols = [c for c in show_cols if c in summary_df.columns]
            st.dataframe(summary_df[show_cols], use_container_width=True, height=260)

# -----------------------------
# 5) (선택) 데이터 일부 표로 보기
# -----------------------------
with st.expander("📋 간트 데이터(일부) 보기"):
    show_cols = [
        MAT_COL, MAT_NAME_COL, BATCH_COL,
        "sell_start_date", "sell_end_date", "stop_reason",
        "init_days", "init_qty", "qty_sold", "remaining_qty",
        "sold_days_total", "days_left_at_stop", "risk_entry_date"
    ]
    show_cols = [c for c in show_cols if c in gantt_df.columns]
    st.dataframe(view_df[show_cols].head(200), use_container_width=True)


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

