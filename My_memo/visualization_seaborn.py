# # pages/4_Visualization.py  (재고 시각화 - seaborn 버전)
# import streamlit as st
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# from datetime import datetime

# # -----------------------------
# # 기본 UI/스타일
# # -----------------------------
# st.set_page_config(page_title="S&OP - Visualization", layout="wide")

# sns.set_theme(
#     style="whitegrid",
#     font="Malgun Gothic",          # Windows 한글 폰트 (한글 깨지면 바꿔줘)
#     rc={"axes.unicode_minus": False}
# )

# st.title("4) Visualization - 재고 데이터")

# # -----------------------------
# # 세션 데이터 로드
# # -----------------------------
# sd = st.session_state.get("stock_data", None)
# if sd is None:
#     st.warning("먼저 3번(Data Analysis)에서 재고 데이터(stock_data)를 생성/저장해 주세요.")
#     st.stop()

# df = sd["stock_df"].copy()
# summary = sd["expiry_summary"].copy()
# kpi = sd.get("kpi", {})

# # 컬럼명 (너희 실제 컬럼명에 맞춰 필요 시 수정)
# MATERIAL_COL = "자재"
# WAREHOUSE_COL = "창고"
# BATCH_COL = "배치"
# EXPIRY_COL = "유효 기한"
# BUCKET_COL = "expiry_bucket"
# QTY_COL = "재고수량"
# VAL_COL = "재고금액"

# # -----------------------------
# # 상단 KPI
# # -----------------------------
# st.caption(f"run_id: {sd.get('run_id','-')}  |  생성일: {kpi.get('today','-')}")
# c1, c2, c3, c4 = st.columns(4)
# c1.metric("총 재고수량", f"{kpi.get('total_qty', 0):,.0f}")
# c2.metric("총 재고금액", f"{kpi.get('total_value', 0):,.0f}")
# c3.metric("9개월 미만 재고수량", f"{kpi.get('under_9m_qty', 0):,.0f}", f"{kpi.get('under_9m_ratio_qty', 0)*100:.1f}%")
# c4.metric("9개월 미만 재고금액", f"{kpi.get('under_9m_value', 0):,.0f}", f"{kpi.get('under_9m_ratio_value', 0)*100:.1f}%")

# st.divider()

# # -----------------------------
# # 필터 영역
# # -----------------------------
# st.subheader("필터")

# colA, colB, colC, colD = st.columns([1.2, 1.2, 1.2, 2.0])

# with colA:
#     only_under_9m = st.checkbox("9개월 미만만 보기", value=False)

# with colB:
#     only_high_risk = st.checkbox("만료/3개월 미만만 보기", value=False)

# with colC:
#     top_n = st.slider("TOP N", min_value=5, max_value=30, value=10, step=5)

# with colD:
#     mat_query = st.text_input("자재 검색(부분일치)", "")

# # 선택 필터(창고)
# if WAREHOUSE_COL in df.columns:
#     wh_opts = ["(전체)"] + sorted(df[WAREHOUSE_COL].dropna().astype(str).unique().tolist())
#     wh = st.selectbox("창고 선택", wh_opts, index=0)
# else:
#     wh = "(전체)"

# # 필터 적용
# fdf = df.copy()

# if wh != "(전체)" and WAREHOUSE_COL in fdf.columns:
#     fdf = fdf[fdf[WAREHOUSE_COL].astype(str) == wh]

# if mat_query and MATERIAL_COL in fdf.columns:
#     fdf = fdf[fdf[MATERIAL_COL].astype(str).str.contains(mat_query, case=False, na=False)]

# if only_under_9m:
#     fdf = fdf[fdf[BUCKET_COL].isin(["만료/만료임박", "3개월 미만", "6개월 미만", "9개월 미만"])]

# if only_high_risk:
#     fdf = fdf[fdf[BUCKET_COL].isin(["만료/만료임박", "3개월 미만"])]

# # 필터된 요약 테이블 생성(차트들이 fdf 기준으로 움직이게)
# plot_summary = (
#     fdf.groupby(BUCKET_COL, as_index=False)[[QTY_COL, VAL_COL]]
#        .sum()
# )

# # 구간 순서 고정(보기 좋게)
# bucket_order = ["만료/만료임박", "3개월 미만", "6개월 미만", "9개월 미만", "9개월 이상", "유효기한 없음"]
# plot_summary[BUCKET_COL] = pd.Categorical(plot_summary[BUCKET_COL], categories=bucket_order, ordered=True)
# plot_summary = plot_summary.sort_values(BUCKET_COL)

# st.divider()

# # -----------------------------
# # 차트 1: 유효기한 구간별 분포(수량/금액)
# # -----------------------------
# st.subheader("유효기한 구간별 재고 분포")

# left, right = st.columns(2)

# with left:
#     fig, ax = plt.subplots(figsize=(7, 4))
#     sns.barplot(
#         data=plot_summary,
#         x=BUCKET_COL,
#         y=QTY_COL,
#         ax=ax
#     )
#     ax.set_title("구간별 재고 수량")
#     ax.set_xlabel("")
#     ax.set_ylabel("재고수량")
#     plt.xticks(rotation=25, ha="right")
#     plt.tight_layout()
#     st.pyplot(fig)

# with right:
#     fig, ax = plt.subplots(figsize=(7, 4))
#     sns.barplot(
#         data=plot_summary,
#         x=BUCKET_COL,
#         y=VAL_COL,
#         ax=ax
#     )
#     ax.set_title("구간별 재고 금액")
#     ax.set_xlabel("")
#     ax.set_ylabel("재고금액")
#     plt.xticks(rotation=25, ha="right")
#     plt.tight_layout()
#     st.pyplot(fig)

# st.divider()

# # -----------------------------
# # 차트 2: 3개월 미만(및 만료) TOP 자재
# # -----------------------------
# st.subheader("리스크 재고 TOP 자재")

# if MATERIAL_COL in fdf.columns:
#     risk_df = fdf[fdf[BUCKET_COL].isin(["만료/만료임박", "3개월 미만"])].copy()

#     top_qty = (
#         risk_df.groupby(MATERIAL_COL, as_index=False)[QTY_COL]
#                .sum()
#                .sort_values(QTY_COL, ascending=False)
#                .head(top_n)
#     )

#     top_val = (
#         risk_df.groupby(MATERIAL_COL, as_index=False)[VAL_COL]
#                .sum()
#                .sort_values(VAL_COL, ascending=False)
#                .head(top_n)
#     )

#     col1, col2 = st.columns(2)

#     with col1:
#         fig, ax = plt.subplots(figsize=(7, 4))
#         sns.barplot(data=top_qty, y=MATERIAL_COL, x=QTY_COL, ax=ax)
#         ax.set_title(f"만료/3개월 미만 TOP {top_n} (수량)")
#         ax.set_xlabel("재고수량")
#         ax.set_ylabel("")
#         plt.tight_layout()
#         st.pyplot(fig)

#     with col2:
#         fig, ax = plt.subplots(figsize=(7, 4))
#         sns.barplot(data=top_val, y=MATERIAL_COL, x=VAL_COL, ax=ax)
#         ax.set_title(f"만료/3개월 미만 TOP {top_n} (금액)")
#         ax.set_xlabel("재고금액")
#         ax.set_ylabel("")
#         plt.tight_layout()
#         st.pyplot(fig)
# else:
#     st.info("자재 컬럼이 없어 TOP 자재 차트를 생략합니다.")

# st.divider()

# # -----------------------------
# # 차트 3: (옵션) 창고 x 유효기한 히트맵
# # -----------------------------
# st.subheader("창고별 유효기한 분포 (Heatmap)")

# if WAREHOUSE_COL in fdf.columns:
#     pivot_qty = (
#         fdf.pivot_table(
#             index=WAREHOUSE_COL,
#             columns=BUCKET_COL,
#             values=QTY_COL,
#             aggfunc="sum",
#             fill_value=0
#         )
#     )

#     # 컬럼 순서 고정
#     for b in bucket_order:
#         if b not in pivot_qty.columns:
#             pivot_qty[b] = 0
#     pivot_qty = pivot_qty[bucket_order]

#     fig, ax = plt.subplots(figsize=(12, 6))
#     sns.heatmap(
#         pivot_qty,
#         annot=False,        # 숫자 너무 많으면 지저분 -> 필요 시 True로
#         linewidths=0.3,
#         ax=ax
#     )
#     ax.set_title("창고별 유효기한 구간 재고수량 히트맵")
#     ax.set_xlabel("")
#     ax.set_ylabel("")
#     plt.tight_layout()
#     st.pyplot(fig)

#     with st.expander("히트맵 테이블 보기"):
#         st.dataframe(pivot_qty, use_container_width=True)
# else:
#     st.info("창고 컬럼이 없어 히트맵을 생략합니다.")

# st.divider()

# # -----------------------------
# # 상세 테이블 (의사결정용 리스트)
# # -----------------------------
# st.subheader("상세 목록 (필터 적용 결과)")
# show_cols = [c for c in [MATERIAL_COL, BATCH_COL, WAREHOUSE_COL, EXPIRY_COL, BUCKET_COL, "days_to_expiry", QTY_COL, VAL_COL] if c in fdf.columns]
# if show_cols:
#     st.dataframe(fdf[show_cols].sort_values(by=["days_to_expiry"], ascending=True, na_position="last"), use_container_width=True)
# else:
#     st.dataframe(fdf.head(200), use_container_width=True)

# # 다운로드(선택)
# with st.expander("다운로드"):
#     csv = fdf.to_csv(index=False).encode("utf-8-sig")
#     st.download_button("필터된 재고 데이터 CSV 다운로드", data=csv, file_name="stock_filtered.csv", mime="text/csv")
