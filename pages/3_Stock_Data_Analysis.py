import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os
import plotly.express as px

# ✅ 페이지 설정
st.set_page_config(page_title="Stock Data Analysis", layout="wide")
st.title("📈 Stock Data Analysis")

# ✅ 상수 설정 (기본 유지)
PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

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
    # 필수 파일 존재 확인
    for key in [PRICE_DF_KEY, STOCK_DF_KEY, EXPIRY_DF_KEY]:
        if key not in dfs_dict:
            st.error(f"❌ '{year_str} {month_str}' 폴더에 필수 파일이 없습니다: {key}")
            st.stop()
            
    df_price = dfs_dict[PRICE_DF_KEY]
    tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
    tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
    tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
    unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
    unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1)
    
    df_stock = dfs_dict[STOCK_DF_KEY]
    df_expiry = dfs_dict[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
    merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
    merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
    merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
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
    merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL]], on=MAT_COL, how="left")
    merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
    merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
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
            m1, m2, m3 = st.columns([1, 1, 2])
            m1.metric(f"{title} 자재 수", f"{len(summary)}종")
            m2.metric(f"총 위험 금액", f"₩{summary[VALUE_COL].sum():,.0f}")
            with m3:
                disp = summary.copy()
                disp[VALUE_COL] = disp[VALUE_COL].map('{:,.0f}'.format)
                disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map('{:,.0f}'.format)
                st.dataframe(disp, use_container_width=True, height=200)

risk_base = ["폐기확정(유효기한 지남)", "3개월 미만"]
display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만"], tab7, "7개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만", "9개월 미만"], tab9, "9개월 미만")

st.divider()

# -----------------------------------------------------
# 2️⃣ 자재-배치 단위 상세 분석 및 시각화
# -----------------------------------------------------
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
            fig, ax = plt.subplots(figsize=(12, 5)) 
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

            import matplotlib.ticker as ticker
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

# -----------------------------------------------------
# 1. [함수] 국가 분류 로직 (저장 위치 코드 기준)
# -----------------------------------------------------
def classify_country(location_code):
    # 빈 값 처리
    if pd.isna(location_code) or str(location_code).strip() == "":
        return "국내"
    
    # 데이터를 문자열로 변환 후 소수점 제거 및 공백 제거 (예: '6030.0' -> '6030')
    loc = str(location_code).split('.')[0].strip()
    
    # 매핑 규칙 적용
    if loc in ["6030", "7030", "7040"]:
        return "China"
    elif loc == "6080":
        return "United States"
    elif loc == "7090":
        return "Japan"
    else:
        return "국내"

# -----------------------------------------------------
# 2. [데이터 전처리] 국가 할당 및 합계 계산
# -----------------------------------------------------
st.subheader("🌍 국가별 전체 재고 가치 분포")

# final_df 복사본 생성
geo_df = final_df.copy()

# '저장 위치' 컬럼을 안전하게 숫자 형식으로 인지하도록 처리 (숫자가 아닌 것은 NaN)
geo_df['저장 위치'] = pd.to_numeric(geo_df['저장 위치'], errors='coerce')

# 분류 함수 적용하여 'Country' 컬럼 생성
geo_df['Country'] = geo_df['저장 위치'].apply(classify_country)

# 국가별 재고 가치(VALUE_COL: "Stock Value on Period End") 합계 계산
country_summary = geo_df.groupby('Country')[VALUE_COL].sum().reset_index()

# 글로벌 전체 재고 대비 비중(%) 계산
total_global_val = country_summary[VALUE_COL].sum()
if total_global_val > 0:
    country_summary['비중(%)'] = (country_summary[VALUE_COL] / total_global_val * 100).round(3)
else:
    country_summary['비중(%)'] = 0

# Plotly 지도가 인식하는 국가명으로 매핑 (국내 -> South Korea)
country_summary['Country_Map'] = country_summary['Country'].replace({'국내': 'South Korea'})

# -----------------------------------------------------
# 3. [시각화] 상단 요약 지표 (Metric Widgets)
# -----------------------------------------------------
st.write("#### 📊 주요 지역별 재고 자산 요약")
m1, m2, m3, m4 = st.columns(4)

def render_region_metric(label, col_obj):
    row = country_summary[country_summary['Country'] == label]
    if not row.empty:
        val = row[VALUE_COL].values[0]
        pct = row['비중(%)'].values[0]
        col_obj.metric(label, f"₩{val:,.0f}", f"{pct}%")
    else:
        col_obj.metric(label, "₩0", "0%")

render_region_metric("국내", m1)
render_region_metric("China", m2)
render_region_metric("United States", m3)
render_region_metric("Japan", m4)

# -----------------------------------------------------
# 4. [시각화] Plotly 글로벌 지도 (Choropleth Map)
# -----------------------------------------------------
# 가치가 높을수록 짙은 빨간색으로 표현하여 집중도 확인
fig_map = px.choropleth(
    country_summary,
    locations="Country_Map",
    locationmode="country names",
    color=VALUE_COL,
    hover_name="Country",
    hover_data={VALUE_COL: ':,.0f', '비중(%)': ':.1f%', 'Country_Map': False},
    color_continuous_scale="Blues",
    title=f"🌐 {selected_year} {selected_month} 글로벌 거점별 재고 가치 합계",
    labels={VALUE_COL: "재고 가치(₩)", "비중(%)": "글로벌 비중"}
)

fig_map.update_layout(
    margin={"r":0,"t":50,"l":0,"b":0},
    geo=dict(
        showframe=False, 
        showcoastlines=True, 
        projection_type='equirectangular',
        landcolor="lightgray"
    )
)

st.plotly_chart(fig_map, use_container_width=True)


# -----------------------------------------------------
# 5. [데이터 테이블] 지역별/위험구간별 상세 수치 분석
# -----------------------------------------------------
with st.expander("📝 지역별 & 위험구간별 상세 분석 테이블"):
    # 1. 분석할 위험 구간 정의
    target_buckets = ["6개월 미만", "7개월 미만", "9개월 미만", "폐기확정(유효기한 지남)", "3개월 미만"]
    
    # 2. 분석용 데이터 필터링 (geo_df 사용)
    # 전체 재고 중 위험 구간에 해당하는 데이터만 추출
    risk_detail_df = geo_df.copy()
    
    # 3. 피벗 테이블 생성: 행(Country), 열(expiry_bucket), 값(Stock Value)
    pivot_risk = risk_detail_df.pivot_table(
        index='Country',
        columns=BUCKET_COL,
        values=VALUE_COL,
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # 4. 사용자가 요청한 주요 위험 구간 열만 필터링 (데이터에 해당 열이 있을 경우만)
    existing_cols = [col for col in target_buckets if col in pivot_risk.columns]
    final_cols = ['Country'] + existing_cols
    
    table_display = pivot_risk[final_cols].copy()
    
    # 5. 합계 열 추가 (위험 재고 총액)
    table_display['위험재고 합계'] = table_display[existing_cols].sum(axis=1)
    
    # 6. 테이블 출력 (금액 형식 포맷팅)
    st.write("##### 📍 국가별 유효기한 리스크 현황 (단위: 원)")
    st.dataframe(
        table_display.sort_values('위험재고 합계', ascending=False).style.format({
            col: '{:,.0f}' for col in table_display.columns if col != 'Country'
        }),
        use_container_width=True
    )
    
    st.caption("※ 위 테이블은 전체 재고 중 유효기한 리스크가 있는 항목만 추려서 국가별로 합산한 결과입니다.")


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

