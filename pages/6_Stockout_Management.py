import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils import load_stock_csv, save_stockout_csv, load_stockout_csv
import numpy as np

# ✅ 페이지 설정
st.set_page_config(page_title="Stockout Management", layout="wide")

# --- 커스텀 CSS (프리미엄 UI) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .main {
        background-color: #f8f9fa;
    }
    
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<h1 style="color: #1e293b;">🚨 Stockout Management</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #64748b; font-size: 1.1rem;">자재별 총 재고량을 기반으로 품절 리스크를 분석합니다.</p>', unsafe_allow_html=True)

# -----------------------------------------------------
# 1) 사이드바 설정 (연도/월 선택)
# -----------------------------------------------------
st.sidebar.header("📅 분석 대상 선택")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox(
    "연도 선택",
    options=[f"{y}년" for y in range(2023, 2041)],
    index=range(2023, 2041).index(current_year) if current_year in range(2023, 2041) else 0
)

selected_month = st.sidebar.selectbox(
    "월 선택",
    options=[f"{m}월" for m in range(1, 13)],
    index=datetime.now().month - 1
)

# -----------------------------------------------------
# 2) 데이터 생성/로드 (Stockout.csv)
# -----------------------------------------------------
MAT_COL, MAT_NAME_COL, QTY_COL, SALES_COL = "자재", "자재 내역", "Stock Quantity on Period End", "3평판"

@st.cache_data(show_spinner="품절 분석 데이터를 생성 중입니다...")
def create_stockout_data(year, month):
    try:
        source_df = load_stock_csv(year, month)
        if source_df is None or source_df.empty:
            return None
            
        # 자재별 집계
        # QTY_COL은 합산, 나머지는 첫 번째 값 유지
        agg_dict = {
            MAT_NAME_COL: "first",
            QTY_COL: "sum",
            SALES_COL: "first"
        }
        # 대분류, 소분류가 있으면 추가
        if "대분류" in source_df.columns: agg_dict["대분류"] = "first"
        if "소분류" in source_df.columns: agg_dict["소분류"] = "first"
        
        agg_df = source_df.groupby(MAT_COL, as_index=False).agg(agg_dict)
        
        # 재고일수 재계산: 집계된 QTY / (3평판 / 30)
        agg_df[QTY_COL] = pd.to_numeric(agg_df[QTY_COL], errors="coerce").fillna(0)
        agg_df[SALES_COL] = pd.to_numeric(agg_df[SALES_COL], errors="coerce").fillna(0)
        
        agg_df["재고일수"] = agg_df.apply(
            lambda r: r[QTY_COL] / (r[SALES_COL] / 30.0) if r[SALES_COL] > 0 else 999.0,
            axis=1
        )
        
        # Stockout.csv 저장
        save_stockout_csv(agg_df, year, month)
        return agg_df
    except Exception as e:
        st.error(f"데이터 생성 오류: {e}")
        return None

# 분석 실행
final_df = load_stockout_csv(selected_year, selected_month)

if final_df is None:
    final_df = create_stockout_data(selected_year, selected_month)

if final_df is None or final_df.empty:
    st.warning(f"⚠️ {selected_year} {selected_month}에 해당하는 분석 원본 데이터(Stock.csv)가 없습니다.")
    st.info("먼저 'Stock Data Analysis' 페이지에서 통합 분석을 완료해 주세요.")
    st.stop()

# -----------------------------------------------------
# 3) 상단 KPI 메트릭
# -----------------------------------------------------
risk_red = final_df[final_df["재고일수"] < 30].copy()
risk_orange = final_df[(final_df["재고일수"] >= 30) & (final_df["재고일수"] < 60)].copy()

st.write("### 📊 리스크 요약 (자재 합산 기준)")
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("위험 (30일 미만)", f"{len(risk_red)}종", delta_color="inverse")
with k2:
    st.metric("주의 (60일 미만)", f"{len(risk_orange)}종", delta_color="off")
with k3:
    st.metric("분석 대상 총 자재 수", f"{len(final_df)}종")

st.markdown("---")

# -----------------------------------------------------
# 4) 시각화 (Plotly Scatter)
# -----------------------------------------------------
# -----------------------------------------------------
# 4) 데이터 전략적 분류 및 필터링
# -----------------------------------------------------
st.write("### 📋 전략적 리스크 관리 리스트")

total_risk_df = final_df[final_df["재고일수"] < 60].copy()

if total_risk_df.empty:
    st.success("✅ 현재 재고일수 60일 미만인 자재가 없습니다. 품절 리스크가 낮습니다.")
else:
    # 3평판 평균값 (전략 분류 기준)
    avg_sales = final_df[SALES_COL].mean()
    
    # 전략 등급 부여 함수
    def get_strategic_grade(row):
        is_high_sales = row[SALES_COL] > avg_sales
        is_risk = row["재고일수"] < 30
        
        if is_high_sales and is_risk: return "🚨 최우선 대응"
        if is_high_sales and not is_risk: return "⚠️ 모니터링"
        if not is_high_sales and is_risk: return "📉 저매출 리스크"
        return "✅ 안정권"

    total_risk_df["전략 등급"] = total_risk_df.apply(get_strategic_grade, axis=1)
    
    # 리스크 등급 (기존 로직 유지)
    total_risk_df["리스크 등급"] = total_risk_df["재고일수"].apply(
        lambda x: "위험" if x < 30 else "주의"
    )
    
    # 상단 필터 UI
    grade_options = ["전체", "⭐ 집중 관리 (최우선+모니터링)", "🚨 최우선 대응", "⚠️ 모니터링", "📉 저매출 리스크"]
    selected_grade = st.radio("전략 분류 필터:", options=grade_options, horizontal=True)
    
    view_table_df = total_risk_df.copy()
    if "최우선 대응" in selected_grade and "집중" not in selected_grade:
        view_table_df = view_table_df[view_table_df["전략 등급"] == "🚨 최우선 대응"]
    elif "모니터링" in selected_grade and "집중" not in selected_grade:
        view_table_df = view_table_df[view_table_df["전략 등급"] == "⚠️ 모니터링"]
    elif "저매출" in selected_grade:
        view_table_df = view_table_df[view_table_df["전략 등급"] == "📉 저매출 리스크"]
    elif "집중 관리" in selected_grade:
        view_table_df = view_table_df[view_table_df["전략 등급"].isin(["🚨 최우선 대응", "⚠️ 모니터링"])]

    if view_table_df.empty:
        st.info("해당 필터에 부합하는 데이터가 없습니다.")
    else:
        # 가독성을 위한 정렬
        view_table_df = view_table_df.sort_values(["전략 등급", "재고일수"], ascending=[True, True])
        
        table_disp = view_table_df.copy()
        table_disp = table_disp.rename(columns={
            MAT_COL: "자재코드",
            MAT_NAME_COL: "자재내역",
            SALES_COL: "3평판(월평균)",
            QTY_COL: "총재고량",
            "재고일수": "남은 재고일수"
        })
        
        # 컬럼 순서 및 포맷팅
        cols = ["전략 등급", "자재코드", "자재내역", "남은 재고일수", "3평판(월평균)", "총재고량"]
        if "대분류" in table_disp.columns: cols.append("대분류")
        if "소분류" in table_disp.columns: cols.append("소분류")
        table_disp = table_disp[cols]
        
        format_disp = table_disp.copy()
        format_disp["3평판(월평균)"] = format_disp["3평판(월평균)"].apply(lambda x: f"{x:,.0f}")
        format_disp["총재고량"] = format_disp["총재고량"].apply(lambda x: f"{x:,.0f}")
        format_disp["남은 재고일수"] = format_disp["남은 재고일수"].apply(lambda x: f"{x:.1f}일")
        
        st.dataframe(format_disp, use_container_width=True, height=400)

        # CSV 다운로드
        csv = table_disp.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="⬇️ Stockout.csv 다운로드",
            data=csv,
            file_name=f"Stockout_{selected_grade}_{selected_year}_{selected_month}.csv",
            mime='text/csv',
        )

st.markdown("---")

# -----------------------------------------------------
# 5) 시각화 (Plotly Scatter - 프리미엄 고도화)
# -----------------------------------------------------
st.write("### 📉 품절 리스크 입체 분석 (4사분면)")
st.caption("※ **상단 왼쪽(1사분면)**은 판매 영향도가 크고 재고가 부족한 **'최우선 대응'** 자재입니다.")

if not total_risk_df.empty:
    # 필터링된 데이터만 차트에 표시
    plot_df = view_table_df.copy() if not view_table_df.empty else total_risk_df.copy()
    plot_df["Label"] = plot_df[MAT_COL].astype(str) + " | " + plot_df[MAT_NAME_COL].astype(str)
    
    # 3평판 평균값 (전체 데이터 기준)
    total_avg_sales = final_df[SALES_COL].mean()
    
    fig = px.scatter(
        plot_df,
        x="재고일수",
        y=SALES_COL,
        size=QTY_COL,
        color="재고일수",
        color_continuous_scale='RdYlGn_r',
        range_color=[0, 60],
        hover_name="Label",
        labels={
            "재고일수": "남은 재고일수 (Days)",
            SALES_COL: "월평균 판매량 (3평판)",
            QTY_COL: "총 재고량"
        }
    )
    
    fig.update_traces(
        marker=dict(line=dict(width=1, color='DarkSlateGrey'), opacity=0.8),
        hovertemplate="<br>".join([
            "<b>%{hovertext}</b>",
            "전략 등급: %{customdata[0]}",
            "남은 재고일수: %{x:.1f}일",
            "월평균 판매량: ₩%{y:,.0f}",
            "현재 총 재고: %{marker.size:,.0f}",
            "<extra></extra>"
        ]),
        customdata=np.stack((plot_df["전략 등급"],), axis=-1) if not plot_df.empty else []
    )
    
    # 기준선 및 사분면 라벨
    max_sales = max(plot_df[SALES_COL].max() * 1.1 if not plot_df.empty else 100, total_avg_sales * 1.2)
    
    fig.add_vline(x=30, line_dash="dash", line_color="#ef4444", annotation_text=" 긴급(30일)")
    fig.add_vline(x=60, line_dash="dash", line_color="#f59e0b", annotation_text=" 주의(60일)")
    fig.add_hline(y=total_avg_sales, line_dash="dot", line_color="#94a3b8", opacity=0.5)
    
    fig.add_annotation(x=15, y=max_sales*0.95, text="🚨 최우선 대응", showarrow=False, font=dict(color="#ef4444", size=14))
    fig.add_annotation(x=45, y=max_sales*0.95, text="⚠️ 모니터링", showarrow=False, font=dict(color="#f59e0b", size=14))
    fig.add_annotation(x=15, y=0, text="📉 저매출 리스크", showarrow=False, font=dict(color="#64748b", size=14))
    fig.add_annotation(x=45, y=0, text="✅ 안정권", showarrow=False, font=dict(color="#10b981", size=14))

    fig.update_layout(
        height=700, plot_bgcolor="rgba(248, 249, 250, 0.5)",
        margin=dict(l=40, r=40, t=80, b=40),
        xaxis=dict(showgrid=True, gridcolor="white", gridwidth=2, range=[0, 65]),
        yaxis=dict(showgrid=True, gridcolor="white", gridwidth=2, range=[0, max_sales]),
        title=dict(text=f"전략적 등급별 품절 분석 ({selected_year} {selected_month})", x=0.5, font=dict(size=20))
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("시각화할 리스크 자재가 없습니다.")
