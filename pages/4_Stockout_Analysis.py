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
total_risk_df = final_df[final_df["재고일수"] < 60].copy()

with st.container(border=True):
    st.write("### 📋 전략적 리스크 관리 리스트")

    if total_risk_df.empty:
        st.success("✅ 현재 재고일수 60일 미만인 자재가 없습니다. 품절 리스크가 낮습니다.")
    else:
        # 리스크 등급 (기존 로직 유지)
        total_risk_df["리스크 등급"] = total_risk_df["재고일수"].apply(
            lambda x: "위험" if x < 30 else "주의"
        )
        
        # 상단 필터 UI
        risk_options = ["전체", "🚨 위험 (30일 미만)", "⚠️ 주의 (60일 미만)"]
        selected_risk = st.radio("리스크 등급 필터:", options=risk_options, horizontal=True)

        view_table_df = total_risk_df.copy()
        
        # 리스크 등급 필터링
        if "위험" in selected_risk:
            view_table_df = view_table_df[view_table_df["리스크 등급"] == "위험"]
        elif "주의" in selected_risk:
            view_table_df = view_table_df[view_table_df["리스크 등급"] == "주의"]

        if view_table_df.empty:
            st.info("해당 필터에 부합하는 데이터가 없습니다.")
        else:
            # 가독성을 위한 정렬
            view_table_df = view_table_df.sort_values("재고일수", ascending=True)
            
            # -----------------------------------------------------
            # 5) 사이드바이사이드 레이아웃 (Chart & Table)
            # -----------------------------------------------------
            table_col, chart_col = st.columns([1.2, 1])
            
            with table_col:
                st.write("##### 📋 상세 리스트")
                table_disp = view_table_df.copy()
                table_disp = table_disp.rename(columns={
                    MAT_COL: "자재코드",
                    MAT_NAME_COL: "자재내역",
                    SALES_COL: "3평판(월평균)",
                    QTY_COL: "총재고량",
                    "재고일수": "남은 재고일수",
                    "리스크 등급": "등급"
                })
                
                # 컬럼 순서 및 포맷팅 (전략 등급 제거, 대/소분류 제거)
                cols = ["등급", "자재코드", "자재내역", "남은 재고일수", "3평판(월평균)", "총재고량"]
                table_disp = table_disp[cols]
                
                format_disp = table_disp.copy()
                format_disp["3평판(월평균)"] = format_disp["3평판(월평균)"].apply(lambda x: f"{x:,.0f}")
                format_disp["총재고량"] = format_disp["총재고량"].apply(lambda x: f"{x:,.0f}")
                format_disp["남은 재고일수"] = format_disp["남은 재고일수"].apply(lambda x: f"{x:.1f}일")
                
                # 등급별 색상 지정 함수
                def style_grade(val):
                    if val == "위험":
                        return "background-color: #ef4444; color: white; font-weight: bold;"
                    elif val == "주의":
                        return "background-color: #f59e0b; color: white; font-weight: bold;"
                    return ""
                
                # ✅ 테이블 스타일링: 등급 제외 모든 값 bold + 남은 재고일수 강조
                bold_cols = [c for c in format_disp.columns if c != "등급"]
                
                def highlight_days_col(x):
                    df = x.copy()
                    df.loc[:, :] = ''
                    if "남은 재고일수" in df.columns:
                        df.loc[:, "남은 재고일수"] = 'background-color: #fff3e0' # 연한 주황색 강조
                    return df

                styled_df = (
                    format_disp.style
                    .map(style_grade, subset=["등급"])
                    .set_properties(subset=bold_cols, **{'font-weight': 'bold'})
                    .apply(highlight_days_col, axis=None)
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True, 
                    height=max(500, len(view_table_df) * 35)
                )

                # CSV 다운로드
                csv = table_disp.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="⬇️ Stockout.csv 다운로드",
                    data=csv,
                    file_name=f"Stockout_{selected_risk}_{selected_year}_{selected_month}.csv",
                    mime='text/csv',
                )

            with chart_col:
                st.write("##### 📊 재고 리스크 시각화")
                plot_df = view_table_df.copy()
                
                # 색상 맵핑
                color_map = {"위험": "#ef4444", "주의": "#f59e0b"}
                
                fig = px.bar(
                    plot_df,
                    x="재고일수",
                    y=MAT_COL, # 자재 코드로 변경
                    color="리스크 등급",
                    orientation='h',
                    color_discrete_map=color_map,
                    labels={
                        "재고일수": "남은 재고일수 (일)",
                        MAT_COL: "자재코드",
                        "리스크 등급": "구분"
                    },
                    custom_data=[MAT_NAME_COL] # 호버용 자재내역
                )
                
                fig.update_layout(
                    height=max(500, len(plot_df) * 35),
                    showlegend=True,
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
                    yaxis=dict(autorange="reversed", type='category'), # 자재코드를 범주형으로 처리
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                
                fig.update_traces(
                    hovertemplate="<b>자재코드: %{y}</b><br>자재내역: %{customdata[0]}<br>남은 재고일수: %{x:.1f}일<extra></extra>"
                )
                
                fig.add_vline(x=30, line_dash="dash", line_color="#ef4444", annotation_text="위험(30일)")
                fig.add_vline(x=60, line_dash="dash", line_color="#f59e0b", annotation_text="주의(60일)")
                
                st.plotly_chart(fig, use_container_width=True)

