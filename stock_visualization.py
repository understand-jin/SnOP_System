import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as ticker

# 1. 기간별 위험 자재 요약 (탭)
def render_risk_tabs(final_df, mat_col, mat_name_col, qty_col, value_col, bucket_col):
    st.subheader("🚨 기간별 위험 자재 요약")
    tab6, tab7, tab9 = st.tabs(["⚠️ 6개월 미만", "🔔 7개월 미만", "ℹ️ 9개월 미만"])
    
    risk_base = ["폐기확정(유효기한 지남)", "3개월 미만"]

    def _display_risk_summary(target_buckets, tab_obj, title):
        with tab_obj:
            risk_df = final_df[final_df[bucket_col].isin(target_buckets)].copy()
            if risk_df.empty:
                st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
            else:
                summary = (
                    risk_df.groupby([mat_col, mat_name_col], as_index=False)[[qty_col, value_col]]
                    .sum()
                    .sort_values(value_col, ascending=False)
                    .reset_index(drop=True)
                )
                m1, m2, m3 = st.columns([1, 1, 3])
                m1.metric(f"{title} 자재 수", f"{len(summary)}종")
                m2.metric(f"총 위험 금액", f"₩{summary[value_col].sum():,.0f}")
                with m3:
                    disp = summary.copy()
                    disp[value_col] = disp[value_col].map('{:,.0f}'.format)
                    disp[qty_col] = disp[qty_col].map('{:,.0f}'.format)
                    st.dataframe(disp, use_container_width=True, height=200)

    _display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
    _display_risk_summary(risk_base + ["6개월 미만", "7개월 미만"], tab7, "7개월 미만")
    _display_risk_summary(risk_base + ["6개월 미만", "7개월 미만", "9개월 미만"], tab9, "9개월 미만")

# 2. 자재-배치 단위 상세 분석 및 차트
def render_batch_analysis(final_df, mat_col, mat_name_col, batch_col, qty_col, value_col, bucket_col):
    st.subheader("🔍 자재-배치별 상세 분석 (6/7/9개월 집중)")
    
    target_risks_all = ["3개월 미만", "6개월 미만", "7개월 미만", "9개월 미만", "폐기확정(유효기한 지남)"]
    df_risk_all = final_df[final_df[bucket_col].isin(target_risks_all)].copy()

    if not df_risk_all.empty:
        top_mats = (
            df_risk_all.groupby([mat_col, mat_name_col], as_index=False)[value_col].sum()
            .sort_values(value_col, ascending=False)
        )
        top_mats["label"] = top_mats[mat_col].astype(str) + " | " + top_mats[mat_name_col].astype(str)
        
        col_sel, col_chk = st.columns([2, 1])
        with col_sel:
            selected_label = st.selectbox("상세 조사가 필요한 자재를 선택하세요", options=top_mats["label"].tolist())
            selected_mat = selected_label.split(" | ")[0]
        with col_chk:
            show_all_batches = st.checkbox("모든 위험 배치 보기 (금액순)", value=False)

        view_df = df_risk_all if show_all_batches else df_risk_all[df_risk_all[mat_col].astype(str) == selected_mat]
        view_df = view_df.sort_values(value_col, ascending=False).reset_index(drop=True)

        v_disp = view_df[[mat_col, mat_name_col, batch_col, bucket_col, qty_col, value_col]].copy()
        v_disp[value_col] = v_disp[value_col].map('{:,.0f}'.format)
        v_disp[qty_col] = v_disp[qty_col].map('{:,.0f}'.format)
        st.dataframe(v_disp, use_container_width=True)

        if not show_all_batches:
            chart_targets = ["6개월 미만", "7개월 미만", "9개월 미만"]
            chart_df = view_df[view_df[bucket_col].isin(chart_targets)].copy()
            if not chart_df.empty:
                fig, ax = plt.subplots(figsize=(12, 5)) 
                sns.barplot(data=chart_df, x=batch_col, y=value_col, hue=bucket_col, palette="viridis", ax=ax)
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
                plt.xticks(rotation=45)
                st.pyplot(fig)

# 3. 국가별 재고 현황 시각화 (지도 및 피벗 테이블)
def render_country_analysis(final_df, selected_year, selected_month, value_col, bucket_col):
    st.subheader("🌍 국가별 전체 재고 가치 분포")
    
    def _classify_country(loc_code):
        if pd.isna(loc_code) or str(loc_code).strip() == "": return "South Korea"
        loc = str(loc_code).split('.')[0].strip()
        mapping = {"6030": "China", "7030": "China", "7040": "China", "6080": "United States", "7090": "Japan"}
        return mapping.get(loc, "South Korea")

    geo_df = final_df.copy()
    geo_df['저장 위치'] = pd.to_numeric(geo_df['저장 위치'], errors='coerce')
    geo_df['Country'] = geo_df['저장 위치'].apply(_classify_country)

    summary = geo_df.groupby('Country')[value_col].sum().reset_index()
    total = summary[value_col].sum()
    summary['비중(%)'] = (summary[value_col] / total * 100).round(3) if total > 0 else 0

    # Metric Widgets
    m_cols = st.columns(4)
    for idx, c in enumerate(["South Korea", "China", "United States", "Japan"]):
        row = summary[summary['Country'] == c]
        val = row[value_col].values[0] if not row.empty else 0
        pct = row['비중(%)'].values[0] if not row.empty else 0
        m_cols[idx].metric(c, f"₩{val:,.0f}", f"{pct:.3f}%")

    # Map
    fig = px.choropleth(summary, locations="Country", locationmode="country names", color=value_col,
                        color_continuous_scale="Blues", title="글로벌 재고 현황")
    st.plotly_chart(fig, use_container_width=True)

    # Pivot Table
    with st.expander("📝 국가별 & 위험구간별 상세 분석 테이블"):
        pivot = geo_df.pivot_table(index='Country', columns=bucket_col, values=value_col, aggfunc='sum', fill_value=0).reset_index()
        st.dataframe(pivot.style.format({col: '{:,.0f}' for col in pivot.columns if col != 'Country'}))