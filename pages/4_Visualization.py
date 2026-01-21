# pages/4_Visualization.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os

st.set_page_config(page_title="S&OP - Visualization", layout="wide")
st.title("📊 Visualization")


# =====================================================
# ✅ 한글 폰트 설정 (Cloud/Local 완벽 대응)
# =====================================================
def set_korean_font():
    # 현재 파일 위치를 기준으로 프로젝트 루트 경로 확보
    # pages/4_Visualization.py -> 부모(pages) -> 부모(root)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # ✅ 중요: 실제 파일명인 'NanumGothic-Regular.ttf'로 수정했습니다.
    font_path = os.path.join(root_dir, "assets", "fonts", "NanumGothic-Regular.ttf")

    if os.path.exists(font_path):
        try:
            # 폰트 등록
            fm.fontManager.addfont(font_path)
            font_name = fm.FontProperties(fname=font_path).get_name()
            
            # Matplotlib 전역 설정
            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            return font_name
        except Exception as e:
            st.error(f"폰트 로드 실패: {e}")
            return "DejaVu Sans"
    else:
        # 파일이 없을 경우 대비 (로컬 윈도우용 fallback)
        return "Malgun Gothic" if os.name == 'nt' else "DejaVu Sans"


FONT_NAME = set_korean_font()

# =====================================================
# ✅ seaborn 스타일 설정
# =====================================================
sns.set_theme(
    style="whitegrid",
    font=FONT_NAME,
    rc={"axes.unicode_minus": False}
)

# =====================================================
# 공통 컬럼명 및 버킷 정의
# =====================================================
BATCH_COL = "배치"
MAT_COL = "자재 내역"
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
RISK_BUCKETS = ["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만", "9개월 미만"]

# =====================================================
# 데이터 로드 로직
# =====================================================
df = None
if "stock_data_registry" in st.session_state and st.session_state["stock_data_registry"].get("selected_id"):
    reg = st.session_state["stock_data_registry"]
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

# 데이터 전처리
required = [BUCKET_COL, QTY_COL]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"필수 컬럼이 없습니다: {missing}.")
    st.stop()

df[QTY_COL] = pd.to_numeric(df[QTY_COL], errors="coerce").fillna(0)
if VAL_COL not in df.columns:
    df[VAL_COL] = 0
df[VAL_COL] = pd.to_numeric(df[VAL_COL], errors="coerce").fillna(0)

all_bucket_order = bucket_order_no_na + [NA_BUCKET]
df[BUCKET_COL] = pd.Categorical(df[BUCKET_COL], categories=all_bucket_order, ordered=True)

# =====================================================
# KPI 섹션
# =====================================================
st.subheader("핵심 지표")
total_qty = float(df[QTY_COL].sum())
risk_9m_qty = float(df.loc[df[BUCKET_COL].isin(RISK_BUCKETS), QTY_COL].sum())
na_qty = float(df.loc[df[BUCKET_COL] == NA_BUCKET, QTY_COL].sum())

c1, c2, c3 = st.columns(3)
c1.metric("총 재고수량", f"{total_qty:,.0f}")
c2.metric("폐기+9개월미만 수량", f"{risk_9m_qty:,.0f}", f"{(risk_9m_qty/total_qty*100 if total_qty else 0):.1f}%")
c3.metric("유효기한 없음 수량", f"{na_qty:,.0f}", f"{(na_qty/total_qty*100 if total_qty else 0):.1f}%")

st.divider()

# =====================================================
# 필터 섹션
# =====================================================
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

# =====================================================
# 1) 구간별 재고수량 시각화
# =====================================================
st.subheader("유효기한 구간별 재고수량 (선 그래프)")
bucket_sum = fdf.groupby(BUCKET_COL, as_index=False)[QTY_COL].sum()
plot_buckets = bucket_order_no_na.copy()
if not exclude_na_bucket:
    plot_buckets += [NA_BUCKET]

bucket_full = pd.DataFrame({BUCKET_COL: plot_buckets}).merge(bucket_sum, on=BUCKET_COL, how="left")
bucket_full[QTY_COL] = bucket_full[QTY_COL].fillna(0)
bucket_full[BUCKET_COL] = pd.Categorical(bucket_full[BUCKET_COL], categories=plot_buckets, ordered=True)
bucket_full = bucket_full.sort_values(BUCKET_COL)

fig, ax = plt.subplots(figsize=(11, 4))
sns.lineplot(data=bucket_full, x=BUCKET_COL, y=QTY_COL, marker="o", linewidth=2.5, ax=ax)
ax.set_title("유효기한 구간별 재고수량")
plt.xticks(rotation=25, ha="right")

for x, y in zip(bucket_full[BUCKET_COL].astype(str), bucket_full[QTY_COL].tolist()):
    ax.text(x, y, f"{int(y):,}", ha="center", va="bottom", fontsize=9)

st.pyplot(fig)

with st.expander("상세 집계 정보 보기"):
    st.write("#### 폐기 + 9개월 미만 자재 리스트")
    if MAT_COL in df.columns:
        risk_mats = df[df[BUCKET_COL].isin(RISK_BUCKETS)][[MAT_COL, BUCKET_COL]].drop_duplicates().sort_values(BUCKET_COL)
        st.dataframe(risk_mats, use_container_width=True)

st.divider()

# =====================================================
# 2) 재고 비중 시각화 (Pie Chart)
# =====================================================
st.subheader("유효기한 구간별 재고 비중(%)")
ratio_df = bucket_full.copy()
if exclude_na_bucket:
    ratio_df = ratio_df[ratio_df[BUCKET_COL] != NA_BUCKET]

total = ratio_df[QTY_COL].sum()
if total > 0:
    ratio_df["ratio_pct"] = (ratio_df[QTY_COL] / total) * 100
    pie_df = ratio_df[ratio_df[QTY_COL] > 0].copy()
    
    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(pie_df[QTY_COL], autopct='%1.1f%%', startangle=90, pctdistance=0.8)
    ax.legend(wedges, pie_df[BUCKET_COL], title="구간", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    st.pyplot(fig)
else:
    st.info("데이터가 없습니다.")

st.divider()

# =====================================================
# 3) 위험 재고 TOP 배치
# =====================================================
st.subheader(f"위험 재고 TOP {top_n} 배치")
risk_df = df[df[BUCKET_COL].isin(RISK_BUCKETS)].copy()
if not risk_df.empty and BATCH_COL in risk_df.columns:
    top_batch = risk_df.groupby(BATCH_COL)[QTY_COL].sum().sort_values(ascending=False).head(top_n).reset_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_batch, x=QTY_COL, y=BATCH_COL, ax=ax)
    st.pyplot(fig)

# =====================================================
# 상세 데이터 다운로드
# =====================================================
st.subheader("상세 데이터 및 다운로드")
st.dataframe(fdf.head(500), use_container_width=True)
st.download_button("CSV 다운로드", fdf.to_csv(index=False).encode("utf-8-sig"), "stock_data.csv", "text/csv")