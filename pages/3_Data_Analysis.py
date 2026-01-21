# pages/3_Data_Analysis.py
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="S&OP - Data Analysis", layout="wide")
st.title("📈 Data Analysis")

# =====================================================
# 🔧 dfs key 이름 (실제 파일명 그대로) (재고 데이터)
# =====================================================
STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

BATCH_COL = "배치"
EXPIRY_COL = "유효 기한"

# ✅ 재고수량은 이 컬럼을 사용!
STOCK_QTY_SOURCE_COL = "Stock Quantity on Period End"
QTY_COL = "재고수량"     # 최종 통합 DF에서 쓸 표준 컬럼명

# 금액 컬럼은 아직 확정 없으니(없어도 동작하게) optional 처리
VAL_COL = "재고금액"

# =====================================================
# 재고유틸
# =====================================================
def to_datetime_safe(s):
    return pd.to_datetime(s, errors="coerce")

def build_stock_df(df_stock: pd.DataFrame, df_expiry: pd.DataFrame):
    # 필요한 컬럼 체크
    if BATCH_COL not in df_stock.columns:
        raise ValueError(f"재고 데이터에 '{BATCH_COL}' 컬럼이 없습니다.")

    if STOCK_QTY_SOURCE_COL not in df_stock.columns:
        raise ValueError(
            f"재고 데이터에 재고수량 원천 컬럼 '{STOCK_QTY_SOURCE_COL}' 이(가) 없습니다."
        )

    if BATCH_COL not in df_expiry.columns or EXPIRY_COL not in df_expiry.columns:
        raise ValueError(f"유효기한 데이터에 '{BATCH_COL}', '{EXPIRY_COL}' 컬럼이 없습니다.")

    # 유효기한 DF 정리
    df_expiry2 = df_expiry[[BATCH_COL, EXPIRY_COL]].copy()
    df_expiry2[EXPIRY_COL] = to_datetime_safe(df_expiry2[EXPIRY_COL])

    # ✅ 배치 기준 병합
    merged = df_stock.merge(df_expiry2, on=BATCH_COL, how="left")

    # ✅ 최종 표준 컬럼으로 재고수량 만들기
    merged[QTY_COL] = pd.to_numeric(merged[STOCK_QTY_SOURCE_COL], errors="coerce").fillna(0)

    # 금액 컬럼은 없으면 0으로 (나중에 원가/단가 붙이면 확장 가능)
    if VAL_COL not in merged.columns:
        merged[VAL_COL] = 0
    merged[VAL_COL] = pd.to_numeric(merged[VAL_COL], errors="coerce").fillna(0)

    # 품질
    quality = {
        "rows": len(merged),
        "mapped_expiry_rate": float(merged[EXPIRY_COL].notna().mean()),
        "missing_expiry_rows": int(merged[EXPIRY_COL].isna().sum())
    }
    return merged, quality

def add_expiry_bucket(df: pd.DataFrame):
    df = df.copy()
    today = pd.Timestamp(datetime.now().date())

    # 날짜 변환(문자열 섞여 있어도 안전)
    df[EXPIRY_COL] = to_datetime_safe(df[EXPIRY_COL])

    # 남은 일수
    df["days_to_expiry"] = (df[EXPIRY_COL] - today).dt.days

    # ✅ 요청한 버킷 구간
    # 버컷 : 연속적인 값을 의미 있는 구간(범주)로 묶는 것
    def bucketize(days):
        if pd.isna(days):
            return "유효기한 없음"
        if days <= 0:
            return "폐기확정(유효기한 지남)"
        if days <= 90:
            return "3개월 미만"
        if days <= 180:
            return "6개월 미만"
        if days <= 270:
            return "9개월 미만"
        if days <= 365:
            return "12개월 미만"
        if days <= 540:
            return "18개월 미만"
        if days <= 730:
            return "24개월 미만"
        return "24개월 이상"

    df["expiry_bucket"] = df["days_to_expiry"].apply(bucketize)

    # 보기 좋은 순서
    bucket_order = [
        "폐기확정(유효기한 지남)",
        "3개월 미만",
        "6개월 미만",
        "9개월 미만",
        "12개월 미만",
        "18개월 미만",
        "24개월 미만",
        "24개월 이상",
        "유효기한 없음",
    ]
    df["expiry_bucket"] = pd.Categorical(df["expiry_bucket"], categories=bucket_order, ordered=True)

    # ✅ 요약
    summary = (
        df.groupby("expiry_bucket", as_index=False)[[QTY_COL, VAL_COL]]
          .sum()
          .sort_values("expiry_bucket")
    )

    # KPI
    expired_mask = df["expiry_bucket"] == "폐기확정(유효기한 지남)"
    kpi = {
        "today": str(today.date()),
        "total_qty": float(df[QTY_COL].sum()),
        "expired_qty": float(df.loc[expired_mask, QTY_COL].sum()),
        "expired_ratio": float(df.loc[expired_mask, QTY_COL].sum() / df[QTY_COL].sum()) if df[QTY_COL].sum() else 0.0,
    }

    return df, summary, kpi

# =====================================================
# dfs 로드
# =====================================================
dfs = st.session_state.get("dfs")
if dfs is None:
    st.warning("먼저 업로드 페이지에서 Raw 데이터를 업로드해 주세요.")
    st.stop()

if STOCK_DF_KEY not in dfs or EXPIRY_DF_KEY not in dfs:
    st.error("필요한 재고/유효기한 파일이 dfs에 없습니다. 업로드 파일명을 확인하세요.")
    st.stop()

df_stock = dfs[STOCK_DF_KEY]
df_expiry = dfs[EXPIRY_DF_KEY]

# =====================================================
# 🚀 자동 병합 & 생성
# =====================================================
st.subheader("✅ 재고 유효기한 데이터 자동 생성")

with st.spinner("배치 기준으로 유효기한을 병합하고, 유효기한 구간을 계산 중입니다..."):
    merged_df, quality = build_stock_df(df_stock, df_expiry)
    stock_df2, expiry_summary, kpi = add_expiry_bucket(merged_df)

# =====================================================
# 📦 data_registry에 등록 (여러 데이터 관리용)
# =====================================================
if "data_registry" not in st.session_state:
    st.session_state["data_registry"] = {"datasets": {}, "selected_id": None}

dataset_id = f"stock_expiry_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
st.session_state["data_registry"]["datasets"][dataset_id] = {
    "domain": "stock",
    "title": "재고 유효기한(폐기~24개월+) 분류",
    "df": stock_df2,
    "summary": expiry_summary,
    "kpi": kpi,
    "quality": quality,
    "source": [STOCK_DF_KEY, EXPIRY_DF_KEY],
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}
st.session_state["data_registry"]["selected_id"] = dataset_id

# =====================================================
# 📊 화면 출력
# =====================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("유효기한 매핑률", f"{quality['mapped_expiry_rate']*100:.1f}%")
c2.metric("총 행 수", f"{quality['rows']:,}")
c3.metric("폐기확정 수량", f"{kpi['expired_qty']:,.0f}")
c4.metric("폐기확정 비중", f"{kpi['expired_ratio']*100:.1f}%")

st.write("### ✅ 유효기한 구간 요약")
st.dataframe(expiry_summary, use_container_width=True)

st.write("### ✅ 새 재고 유효기한 데이터(미리보기)")
# 핵심 컬럼 위주로 먼저 보여주기
preview_cols = [c for c in [BATCH_COL, EXPIRY_COL, "days_to_expiry", "expiry_bucket", STOCK_QTY_SOURCE_COL, QTY_COL] if c in stock_df2.columns]
st.dataframe(stock_df2[preview_cols].head(80), use_container_width=True)

# =====================================================
# ⬇️ 다운로드
# =====================================================
st.divider()
csv_bytes = stock_df2.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "📥 재고 유효기한 데이터 CSV 다운로드",
    data=csv_bytes,
    file_name=f"{dataset_id}.csv",
    mime="text/csv"
)
