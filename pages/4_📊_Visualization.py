# pages/4_Visualization.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="S&OP - Visualization", layout="wide")
st.title("📊 Visualization")

# -----------------------------
# seaborn 스타일
# -----------------------------
sns.set_theme(
    style="whitegrid",
    font="Malgun Gothic",
    rc={"axes.unicode_minus": False}
)

# -----------------------------
# 공통 컬럼명
# -----------------------------
BATCH_COL = "배치"
MAT_COL = "자재 내역"        # ✅ 자재 내역 컬럼
EXPIRY_COL = "유효 기한"
QTY_COL = "재고수량"
VAL_COL = "재고금액"
BUCKET_COL = "expiry_bucket"
DAYS_COL = "days_to_expiry"

bucket_order_no_na = [
    "폐기확정(유효기한 지남)",
    "3개월 미만",
    "6개월 미만",
    "9개월 미만",
    "12개월 미만",
    "18개월 미만",
    "24개월 미만",
    "24개월 이상",
]
NA_BUCKET = "유효기한 없음"

# ✅ "위험 재고" 기준(폐기 + 9개월 미만까지)
RISK_BUCKETS = ["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만", "9개월 미만"]

# -----------------------------
# 데이터 로드: registry 우선, 없으면 stock_data
# -----------------------------
df = None

if "data_registry" in st.session_state and st.session_state["data_registry"].get("selected_id"):
    reg = st.session_state["data_registry"]
    did = reg["selected_id"]
    meta = reg["datasets"].get(did)
    if meta:
        df = meta.get("df")
        st.caption(f"선택된 데이터셋: {did} | {meta.get('title','')} | {meta.get('created_at','')}")
else:
    sd = st.session_state.get("stock_data")
    if sd:
        df = sd.get("stock_df")
        st.caption(f"선택된 데이터셋: stock_data | run_id: {sd.get('run_id','-')}")

if df is None or not isinstance(df, pd.DataFrame):
    st.warning("먼저 3번(Data Analysis)에서 재고 유효기한 데이터를 생성해 주세요.")
    st.stop()

df = df.copy()

# -----------------------------
# 안전 처리
# -----------------------------
required = [BUCKET_COL, QTY_COL]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"필수 컬럼이 없습니다: {missing}. Data Analysis에서 expiry_bucket/재고수량 생성 여부를 확인하세요.")
    st.stop()

df[QTY_COL] = pd.to_numeric(df[QTY_COL], errors="coerce").fillna(0)

if VAL_COL not in df.columns:
    df[VAL_COL] = 0
df[VAL_COL] = pd.to_numeric(df[VAL_COL], errors="coerce").fillna(0)

# 버킷 카테고리 고정
all_bucket_order = bucket_order_no_na + [NA_BUCKET]
df[BUCKET_COL] = pd.Categorical(df[BUCKET_COL], categories=all_bucket_order, ordered=True)

# -----------------------------
# KPI
# -----------------------------
st.subheader("핵심 지표")

total_qty = float(df[QTY_COL].sum())
risk_9m_qty = float(df.loc[df[BUCKET_COL].isin(RISK_BUCKETS), QTY_COL].sum())
na_qty = float(df.loc[df[BUCKET_COL] == NA_BUCKET, QTY_COL].sum())

c1, c2, c3 = st.columns(3)
c1.metric("총 재고수량", f"{total_qty:,.0f}")
c2.metric("폐기+9개월미만 수량", f"{risk_9m_qty:,.0f}", f"{(risk_9m_qty/total_qty*100 if total_qty else 0):.1f}%")
c3.metric("유효기한 없음 수량", f"{na_qty:,.0f}", f"{(na_qty/total_qty*100 if total_qty else 0):.1f}%")

st.divider()

# -----------------------------
# 필터
# -----------------------------
st.subheader("필터")

colA, colB, colC, colD, colE = st.columns([1.4, 1.2, 2.0, 1.8, 1.8])

with colA:
    show_only_risky = st.checkbox("폐기 + 9개월 미만만 보기", value=False)
with colB:
    top_n = st.slider("TOP N", 5, 30, 15, 5)
with colC:
    search_batch = st.text_input("배치 검색(부분일치)", "")
with colD:
    exclude_na_bucket = st.checkbox("비중/구간 그래프에서 '유효기한 없음' 제외", value=True)
with colE:
    pie_group_small = st.checkbox("작은 비중 묶기(기타)", value=True)

fdf = df.copy()

if show_only_risky:
    fdf = fdf[fdf[BUCKET_COL].isin(RISK_BUCKETS)]

if search_batch and BATCH_COL in fdf.columns:
    fdf = fdf[fdf[BATCH_COL].astype(str).str.contains(search_batch, case=False, na=False)]

st.divider()

# -----------------------------
# 1) 구간별 재고수량 (선 그래프)
# -----------------------------
st.subheader("유효기한 구간별 재고수량 (선 그래프)")

bucket_sum = (
    fdf.groupby(BUCKET_COL, as_index=False)[QTY_COL]
       .sum()
)

plot_buckets = bucket_order_no_na.copy()
if not exclude_na_bucket:
    plot_buckets = plot_buckets + [NA_BUCKET]

bucket_full = (
    pd.DataFrame({BUCKET_COL: plot_buckets})
      .merge(bucket_sum, on=BUCKET_COL, how="left")
      .fillna({QTY_COL: 0})
)

bucket_full[BUCKET_COL] = pd.Categorical(bucket_full[BUCKET_COL], categories=plot_buckets, ordered=True)
bucket_full = bucket_full.sort_values(BUCKET_COL)

fig, ax = plt.subplots(figsize=(11, 4))
sns.lineplot(data=bucket_full, x=BUCKET_COL, y=QTY_COL, marker="o", linewidth=2.5, ax=ax)

ax.set_title("유효기한 구간별 재고수량" + (" (유효기한 없음 제외)" if exclude_na_bucket else ""))
ax.set_xlabel("")
ax.set_ylabel("재고수량")
plt.xticks(rotation=25, ha="right")

for x, y in zip(bucket_full[BUCKET_COL].astype(str), bucket_full[QTY_COL].tolist()):
    ax.text(x, y, f"{int(y):,}", ha="center", va="bottom", fontsize=9)

plt.tight_layout()
st.pyplot(fig)

# ✅ 구간별 집계 테이블 + (자재 내역, 몇개월 미만인지) 표시
with st.expander("구간별 집계 테이블 보기"):
    st.write("#### 구간별 재고수량 합계")
    st.dataframe(bucket_full, use_container_width=True)

    st.divider()
    st.write("#### 폐기 + 9개월 미만 자재 내역 (중복 제거) + 구간 표시")

    if MAT_COL not in df.columns:
        st.info(f"'{MAT_COL}' 컬럼이 없어 자재 내역을 표시할 수 없습니다. (Data Analysis에서 컬럼 포함 여부 확인)")
    else:
        risk_rows = df[df[BUCKET_COL].isin(RISK_BUCKETS)].copy()

        # 자재 내역 + expiry_bucket을 자재 기준으로 중복 제거
        # 규칙: 같은 자재가 여러 구간에 있으면 "가장 위험한 구간(먼저 나오는 구간)"으로 1개만 남김
        risk_rank = {b: i for i, b in enumerate(RISK_BUCKETS)}  # 폐기확정이 0, 3개월미만이 1 ...
        risk_rows["_risk_rank"] = risk_rows[BUCKET_COL].map(risk_rank).fillna(9999)

        risk_rows[MAT_COL] = risk_rows[MAT_COL].astype(str).str.strip()
        risk_rows = risk_rows[(risk_rows[MAT_COL].notna()) & (risk_rows[MAT_COL] != "")]

        # 자재별로 가장 위험한 구간 1개 선택
        mat_bucket_df = (
            risk_rows.sort_values(["_risk_rank", MAT_COL])
                    .drop_duplicates(subset=[MAT_COL], keep="first")
                    [[MAT_COL, BUCKET_COL]]
                    .rename(columns={BUCKET_COL: "유효기한 구간"})
                    .sort_values(["유효기한 구간", MAT_COL])
                    .reset_index(drop=True)
        )

        st.write(f"- 포함 구간: {', '.join(RISK_BUCKETS)}")
        st.write(f"- 자재 종류(중복 제거): **{len(mat_bucket_df):,}개**")

        if len(mat_bucket_df) == 0:
            st.info("폐기 + 9개월 미만 구간에 해당하는 자재 내역이 없습니다.")
        else:
            st.dataframe(mat_bucket_df, use_container_width=True)

st.divider()

# -----------------------------
# 2) 유효기한 구간별 재고 비중(%) - 원 그래프(legend로 겹침 방지)
# -----------------------------
st.subheader("유효기한 구간별 재고 비중(%) (원 그래프)")

ratio_df = bucket_full.copy()
if exclude_na_bucket:
    ratio_df = ratio_df[ratio_df[BUCKET_COL] != NA_BUCKET]

denom_total = float(ratio_df[QTY_COL].sum())
if denom_total == 0:
    st.info("비중 계산을 위한 총 재고수량이 0입니다. (필터 조건을 완화해보세요.)")
else:
    ratio_df["ratio_pct"] = (ratio_df[QTY_COL] / denom_total) * 100
    pie_df = ratio_df[ratio_df[QTY_COL] > 0].copy()

    threshold = 1.0
    if pie_group_small and len(pie_df) > 0:
        small = pie_df[pie_df["ratio_pct"] < threshold]
        big = pie_df[pie_df["ratio_pct"] >= threshold]
        if len(small) > 0:
            etc_qty = float(small[QTY_COL].sum())
            etc_pct = float(small["ratio_pct"].sum())
            big = pd.concat(
                [big, pd.DataFrame({BUCKET_COL: ["기타(<1%)"], QTY_COL: [etc_qty], "ratio_pct": [etc_pct]})],
                ignore_index=True
            )
        pie_df = big

    fig, ax = plt.subplots(figsize=(8, 8))

    wedges, _, _ = ax.pie(
        pie_df[QTY_COL],
        labels=None,
        autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
        startangle=90,
        pctdistance=0.70
    )

    ax.set_title("유효기한 구간별 재고 비중(%)" + (" (유효기한 없음 제외)" if exclude_na_bucket else ""))
    ax.axis("equal")

    legend_labels = [f"{lbl} ({pct:.1f}%)" for lbl, pct in zip(pie_df[BUCKET_COL].astype(str), pie_df["ratio_pct"])]
    ax.legend(
        wedges,
        legend_labels,
        title="구간",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        borderaxespad=0.0
    )

    plt.tight_layout()
    st.pyplot(fig)

st.divider()

# -----------------------------
# 3) 위험(폐기+9개월) Top 배치
# -----------------------------
st.subheader("위험 재고 TOP 배치 (폐기/9개월 미만)")

risk_df = df[df[BUCKET_COL].isin(RISK_BUCKETS)].copy()

top_batch = (
    risk_df.groupby(BATCH_COL, as_index=False)[QTY_COL]
           .sum()
           .sort_values(QTY_COL, ascending=False)
           .head(top_n)
)

if len(top_batch) == 0:
    st.info("폐기/9개월 미만 구간 데이터가 없습니다.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_batch, y=BATCH_COL, x=QTY_COL, ax=ax)
    ax.set_title(f"폐기/9개월 미만 TOP {top_n} 배치")
    ax.set_xlabel("재고수량")
    ax.set_ylabel("")
    plt.tight_layout()
    st.pyplot(fig)

st.divider()

# -----------------------------
# 상세 테이블 + 다운로드
# -----------------------------
st.subheader("상세 데이터")

show_cols = [c for c in [BATCH_COL, MAT_COL, EXPIRY_COL, DAYS_COL, BUCKET_COL, QTY_COL, VAL_COL] if c in fdf.columns]
if not show_cols:
    show_cols = fdf.columns.tolist()

sort_cols = []
if BUCKET_COL in fdf.columns:
    sort_cols.append(BUCKET_COL)
if DAYS_COL in fdf.columns:
    sort_cols.append(DAYS_COL)

out_df = fdf.copy()
if sort_cols:
    out_df = out_df.sort_values(by=sort_cols)

st.dataframe(out_df[show_cols].head(500), use_container_width=True)

st.write("### CSV 다운로드 (현재 필터 결과)")
csv_bytes = out_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "CSV 다운로드",
    data=csv_bytes,
    file_name="stock_visual_filtered.csv",
    mime="text/csv"
)
