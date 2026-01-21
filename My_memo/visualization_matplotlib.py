# # pages/4_Visualization_Stock.py
# import streamlit as st
# import matplotlib.pyplot as plt
# import pandas as pd

# st.title("4) Visualization - 재고")

# sd = st.session_state.get("stock_data", None)
# if sd is None:
#     st.warning("Data Analysis에서 stock_data를 먼저 생성/저장해 주세요.")
#     st.stop()

# df = sd["stock_df"].copy()
# summary = sd["expiry_summary"].copy()
# kpi = sd["kpi"]

# # ---- KPI 카드 ----
# c1, c2, c3, c4 = st.columns(4)
# c1.metric("총 재고수량", f"{kpi['total_qty']:,.0f}")
# c2.metric("총 재고금액", f"{kpi['total_value']:,.0f}")
# c3.metric("9개월 미만 재고수량", f"{kpi['under_9m_qty']:,.0f}", f"{kpi['under_9m_ratio_qty']*100:.1f}%")
# c4.metric("9개월 미만 재고금액", f"{kpi['under_9m_value']:,.0f}", f"{kpi['under_9m_ratio_value']*100:.1f}%")

# st.divider()

# # ---- 필터(선택) ----
# st.subheader("필터")
# col1, col2 = st.columns(2)

# # 예시: 창고 컬럼이 있다고 가정할 때만 표시
# warehouse_col = "창고"
# material_col = "자재"

# with col1:
#     if warehouse_col in df.columns:
#         wh_opts = ["(전체)"] + sorted(df[warehouse_col].dropna().astype(str).unique().tolist())
#         wh = st.selectbox("창고", wh_opts)
#     else:
#         wh = "(전체)"

# with col2:
#     if material_col in df.columns:
#         mat_query = st.text_input("자재 검색(부분일치)", "")
#     else:
#         mat_query = ""

# only_risky = st.checkbox("9개월 미만만 보기", value=False)

# fdf = df.copy()
# if wh != "(전체)" and warehouse_col in fdf.columns:
#     fdf = fdf[fdf[warehouse_col].astype(str) == wh]

# if mat_query and material_col in fdf.columns:
#     fdf = fdf[fdf[material_col].astype(str).str.contains(mat_query, case=False, na=False)]

# if only_risky:
#     fdf = fdf[fdf["expiry_bucket"].isin(["만료/만료임박", "3개월 미만", "6개월 미만", "9개월 미만"])]

# st.divider()

# # ---- 그래프 1: 유효기한 구간별 재고 ----
# st.subheader("유효기한 구간별 재고 (수량/금액)")

# qty_col = "재고수량"
# value_col = "재고금액"

# plot_summary = (
#     fdf.groupby("expiry_bucket", as_index=False)[[qty_col, value_col]]
#        .sum()
# )

# fig1 = plt.figure()
# plt.bar(plot_summary["expiry_bucket"], plot_summary[qty_col])
# plt.xticks(rotation=30, ha="right")
# plt.ylabel("재고수량")
# plt.tight_layout()
# st.pyplot(fig1)

# fig2 = plt.figure()
# plt.bar(plot_summary["expiry_bucket"], plot_summary[value_col])
# plt.xticks(rotation=30, ha="right")
# plt.ylabel("재고금액")
# plt.tight_layout()
# st.pyplot(fig2)

# # ---- 그래프 2: 3개월 미만 TOP 자재 ----
# st.subheader("3개월 미만 재고 TOP 10 (자재 기준)")

# if material_col in fdf.columns:
#     top = (
#         fdf[fdf["expiry_bucket"].isin(["만료/만료임박","3개월 미만"])]
#           .groupby(material_col, as_index=False)[[qty_col, value_col]]
#           .sum()
#           .sort_values(by=qty_col, ascending=False)
#           .head(10)
#     )

#     fig3 = plt.figure()
#     plt.bar(top[material_col].astype(str), top[qty_col])
#     plt.xticks(rotation=45, ha="right")
#     plt.ylabel("재고수량")
#     plt.tight_layout()
#     st.pyplot(fig3)
# else:
#     st.info("자재 컬럼이 없어 TOP 분석을 생략합니다.")

# # ---- 상세 테이블 ----
# st.subheader("상세 목록")
# st.dataframe(fdf, use_container_width=True)
