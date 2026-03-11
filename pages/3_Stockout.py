import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from inventory_utils2 import stock_out

st.set_page_config(page_title="Stockout Analysis", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #F0F4F8; }
.main .block-container {
    padding-top: 0 !important; padding-bottom: 2.5rem;
    padding-left: 2.5rem; padding-right: 2.5rem; max-width: 100%;
}

/* ── 사이드바 ── */
[data-testid="stSidebar"] { background: #0B1E3F !important; border-right: none; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebarNav"] { padding: 0.5rem; }
[data-testid="stSidebarNav"] a {
    border-radius: 8px; padding: 0.55rem 0.9rem !important;
    margin-bottom: 2px; font-size: 0.875rem; font-weight: 500;
    color: #94A3B8 !important; display: block;
}
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.08) !important; color: #E2E8F0 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(37,99,235,0.3) !important; color: #FFFFFF !important;
    font-weight: 600; border-left: 3px solid #3B82F6;
}
[data-testid="stSidebarNav"] span { color: inherit !important; }

/* ── 헤더 배너 ── */
.dash-header {
    background: linear-gradient(135deg, #0B1E3F 0%, #1565C0 100%);
    margin: -1px -2.5rem 2rem -2.5rem;
    padding: 1.4rem 2.8rem;
    display: flex; align-items: center; justify-content: space-between;
}
.dash-header-left { display: flex; align-items: center; gap: 16px; }
.dash-header-bar  { width: 4px; height: 40px; background: #60A5FA; border-radius: 2px; flex-shrink: 0; }
.dash-header-title { color: #FFFFFF; font-size: 1.35rem; font-weight: 700; letter-spacing: -0.4px; }
.dash-header-sub   { color: #93C5FD; font-size: 0.78rem; margin-top: 4px; font-weight: 400; }
.dash-tag {
    background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
    color: #BFDBFE; font-size: 0.7rem; font-weight: 700;
    padding: 0.3rem 1rem; border-radius: 20px; letter-spacing: 1px;
}

/* ── 섹션 라벨 ── */
.section-label {
    font-size: 0.67rem; font-weight: 700; color: #94A3B8;
    text-transform: uppercase; letter-spacing: 1.3px;
    margin-bottom: 0.65rem; padding-left: 2px;
}

/* ── KPI 카드 (커스텀 HTML) ── */
.kpi-card {
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E8F0;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 2px 8px rgba(15,23,42,0.06);
    height: 100%;
}
.kpi-card-danger  { border-top: 4px solid #EF4444; }
.kpi-card-warning { border-top: 4px solid #F59E0B; }
.kpi-label { font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0.5rem; }
.kpi-value { font-size: 2.2rem; font-weight: 800; line-height: 1; }
.kpi-value-danger  { color: #DC2626; }
.kpi-value-warning { color: #D97706; }
.kpi-sub { font-size: 0.72rem; color: #94A3B8; margin-top: 0.35rem; }

/* ── 기간 선택 ── */
[data-testid="stSelectbox"] > div > div {
    border-radius: 8px; border-color: #CBD5E1;
    font-size: 0.875rem; background: #FFFFFF;
}

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: transparent; border-bottom: 2px solid #E2E8F0;
}
.stTabs [data-baseweb="tab"] {
    height: 38px; background: #F8FAFC; border-radius: 8px 8px 0 0;
    color: #64748B; font-weight: 600; font-size: 0.83rem;
    padding: 8px 18px; border: 1px solid #E2E8F0; border-bottom: none;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important; color: #2563EB !important;
    border-bottom: 2px solid #2563EB !important;
}

/* ── 필터 라디오 ── */
[data-testid="stRadio"] > div { gap: 8px; }
[data-testid="stRadio"] label {
    background: #F8FAFC; border: 1px solid #E2E8F0;
    border-radius: 20px; padding: 4px 14px;
    font-size: 0.8rem; font-weight: 600; color: #475569;
    cursor: pointer; transition: all 0.15s;
}
[data-testid="stRadio"] label:has(input:checked) {
    background: #EFF6FF; border-color: #93C5FD; color: #1D4ED8;
}

/* ── 버튼 ── */
.stButton > button {
    background: #1E40AF; color: #FFFFFF; border: none;
    border-radius: 8px; font-weight: 600; font-size: 0.85rem;
    padding: 0.5rem 1.2rem; transition: background 0.15s;
}
.stButton > button:hover { background: #1D4ED8; }
.stDownloadButton > button {
    background: #F8FAFC; color: #374151; border: 1px solid #E2E8F0;
    border-radius: 8px; font-weight: 600; font-size: 0.82rem;
    padding: 0.45rem 1rem; transition: all 0.15s;
}
.stDownloadButton > button:hover { background: #EFF6FF; border-color: #93C5FD; color: #1D4ED8; }

/* ── 검색 입력 ── */
[data-testid="stTextInput"] > div {
    border-radius: 8px; border-color: #CBD5E1; background: #FFFFFF;
}



hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.4rem 0; }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="dash-header">
  <div class="dash-header-left">
    <div class="dash-header-bar"></div>
    <div>
      <div class="dash-header-title">Stockout Risk Analysis</div>
      <div class="dash-header-sub">재고일수 기반 품절 리스크 모니터링</div>
    </div>
  </div>
  <span class="dash-tag">STOCKOUT</span>
</div>
""", unsafe_allow_html=True)

# ── 기간 선택 ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">분석 기간 설정</div>', unsafe_allow_html=True)

_cy = datetime.now().year
_cm = datetime.now().month
c1, c2, c3 = st.columns([2, 2, 4])
with c1:
    selected_year = st.selectbox("연도",
        options=[f"{y}년" for y in range(2023, 2041)],
        index=range(2023, 2041).index(_cy) if _cy in range(2023, 2041) else 0)
with c2:
    selected_month = st.selectbox("월",
        options=[f"{m}월" for m in range(1, 13)],
        index=_cm - 1)

# ── 데이터 로드 & 분석 ────────────────────────────────────────────────────────
inv_path = os.path.join("data", selected_year, selected_month, "inventory.csv")

if not os.path.exists(inv_path):
    st.warning(f"`{inv_path}` 파일이 없습니다. Data Upload 페이지에서 먼저 업로드해 주세요.")
    st.stop()

try:
    inv_df = pd.read_csv(inv_path, encoding="utf-8-sig")
except Exception as e:
    st.error(f"inventory.csv 로드 오류: {e}"); st.stop()

required_cols = {"자재코드", "자재내역", "3평판", "기말수량"}
missing = required_cols - set(inv_df.columns)
if missing:
    st.error(f"필요한 컬럼 없음: {missing}"); st.stop()

try:
    stockout_df = stock_out(inv_df)
except Exception as e:
    st.error(f"stock_out 오류: {e}"); st.stop()

stockout_df["기말수량"] = pd.to_numeric(stockout_df["기말수량"], errors="coerce").fillna(0)
stockout_df["3평판"]   = pd.to_numeric(stockout_df["3평판"],   errors="coerce").fillna(0)

agg_df = (
    stockout_df.groupby("자재코드", as_index=False)
    .agg(자재내역=("자재내역", "first"),
         기말수량=("기말수량", "sum"),
         판매평균=("3평판",   "first"))
)
agg_df["재고일수"] = agg_df.apply(
    lambda r: r["기말수량"] / (r["판매평균"] / 30.0) if r["판매평균"] > 0 else 999.0, axis=1)
agg_df["현황"] = agg_df["재고일수"].apply(
    lambda x: "위험" if x < 30 else ("주의" if x < 60 else "정상"))

n_danger  = int((agg_df["현황"] == "위험").sum())
n_warning = int((agg_df["현황"] == "주의").sum())
n_ok      = int((agg_df["현황"] == "정상").sum())
n_total   = len(agg_df)

# ── 리스크 요약 ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">리스크 요약</div>', unsafe_allow_html=True)

pct_d = round(n_danger  / n_total * 100, 1) if n_total else 0
pct_w = round(n_warning / n_total * 100, 1) if n_total else 0
pct_o = round(n_ok      / n_total * 100, 1) if n_total else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""
    <div class="kpi-card" style="border-top:4px solid #3B82F6;">
        <div class="kpi-label">전체 자재</div>
        <div class="kpi-value" style="color:#1E40AF;">{n_total}<span style="font-size:1rem;font-weight:600;color:#94A3B8;margin-left:4px;">종</span></div>
        <div class="kpi-sub">분석 대상 전체</div>
    </div>
    """, unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="kpi-card kpi-card-danger">
        <div class="kpi-label">위험 · 30일 미만</div>
        <div class="kpi-value kpi-value-danger">{n_danger}<span style="font-size:1rem;font-weight:600;color:#94A3B8;margin-left:4px;">종</span></div>
        <div class="kpi-sub">{pct_d}% · 즉시 조치 필요</div>
    </div>
    """, unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class="kpi-card kpi-card-warning">
        <div class="kpi-label">주의 · 30~60일</div>
        <div class="kpi-value kpi-value-warning">{n_warning}<span style="font-size:1rem;font-weight:600;color:#94A3B8;margin-left:4px;">종</span></div>
        <div class="kpi-sub">{pct_w}% · 모니터링 필요</div>
    </div>
    """, unsafe_allow_html=True)
with k4:
    st.markdown(f"""
    <div class="kpi-card" style="border-top:4px solid #10B981;">
        <div class="kpi-label">정상 · 60일 이상</div>
        <div class="kpi-value" style="color:#059669;">{n_ok}<span style="font-size:1rem;font-weight:600;color:#94A3B8;margin-left:4px;">종</span></div>
        <div class="kpi-sub">{pct_o}% · 안전 수준</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── 탭 ───────────────────────────────────────────────────────────────────────
tab_risk, tab_all = st.tabs(["리스크 자재 (60일 미만)", "전체 자재 목록"])

# ── 탭 1: 리스크 자재 ────────────────────────────────────────────────────────
with tab_risk:
    risk_df = agg_df[agg_df["재고일수"] < 60].copy().sort_values("재고일수")

    if risk_df.empty:
        st.success("재고일수 60일 미만인 자재가 없습니다. 품절 리스크가 낮습니다.")
    else:
        risk_options = ["전체", "위험 (30일 미만)", "주의 (30~60일)"]
        sel_risk = st.radio("등급 필터", options=risk_options, horizontal=True, key="risk_filter",
                            label_visibility="collapsed")

        filtered = risk_df.copy()
        if "위험" in sel_risk:
            filtered = filtered[filtered["현황"] == "위험"]
        elif "주의" in sel_risk:
            filtered = filtered[filtered["현황"] == "주의"]

        if filtered.empty:
            st.info("해당 필터에 해당하는 자재가 없습니다.")
        else:
            table_col, chart_col = st.columns([1.2, 1])

            # 테이블
            with table_col:
                st.markdown('<div class="section-label">상세 리스트</div>', unsafe_allow_html=True)

                disp = filtered[["현황", "자재코드", "자재내역", "재고일수", "판매평균", "기말수량"]].copy()
                disp = disp.rename(columns={
                    "현황": "등급", "판매평균": "3평판", "기말수량": "총재고량"})
                fmt = disp.copy()
                fmt["3평판"]   = fmt["3평판"].apply(lambda x: f"{x:,.0f}")
                fmt["총재고량"] = fmt["총재고량"].apply(lambda x: f"{x:,.0f}")
                fmt["재고일수"] = fmt["재고일수"].apply(
                    lambda x: f"{x:.1f}일" if x < 999 else "999일+")

                def _style_grade(val):
                    if val == "위험": return "background-color:#EF4444;color:white;font-weight:700;"
                    if val == "주의": return "background-color:#F59E0B;color:white;font-weight:700;"
                    return ""

                def _highlight_days(x):
                    df_ = x.copy(); df_.loc[:, :] = ""
                    if "재고일수" in df_.columns:
                        df_.loc[:, "재고일수"] = "background-color:#FFF3E0;font-weight:700;"
                    return df_

                styled = (
                    fmt.style
                    .map(_style_grade, subset=["등급"])
                    .set_properties(subset=[c for c in fmt.columns if c != "등급"],
                                    **{"font-weight": "600"})
                    .apply(_highlight_days, axis=None)
                )
                st.dataframe(styled, use_container_width=True,
                             height=max(400, len(filtered) * 35 + 40),
                             hide_index=True)

                csv_bytes = disp.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("CSV 다운로드", csv_bytes,
                    f"stockout_risk_{selected_year}_{selected_month}.csv", "text/csv")

            # 차트
            with chart_col:
                st.markdown('<div class="section-label">재고 리스크 시각화</div>', unsafe_allow_html=True)

                plot_df = filtered.copy()
                fig = px.bar(
                    plot_df, x="재고일수", y="자재코드", color="현황",
                    orientation="h",
                    color_discrete_map={"위험": "#ef4444", "주의": "#f59e0b"},
                    labels={"재고일수": "재고일수 (일)", "자재코드": "자재코드"},
                    custom_data=["자재내역"]
                )
                fig.update_layout(
                    height=max(500, len(plot_df) * 35),
                    showlegend=False,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=True, gridcolor="#e2e8f0",
                               tickfont=dict(size=11, color="#64748B")),
                    yaxis=dict(autorange="reversed", type="category",
                               tickfont=dict(size=11, color="#374151")),
                    margin=dict(l=0, r=10, t=10, b=0),
                )
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{y}</b><br>%{customdata[0]}<br>"
                        "재고일수: %{x:.1f}일<extra></extra>"))
                fig.add_vline(x=30, line_dash="dash", line_color="#ef4444",
                              line_width=1.5, annotation_text="위험(30일)",
                              annotation_font=dict(size=11, color="#ef4444"))
                fig.add_vline(x=60, line_dash="dash", line_color="#f59e0b",
                              line_width=1.5, annotation_text="주의(60일)",
                              annotation_font=dict(size=11, color="#f59e0b"))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── 탭 2: 전체 자재 ──────────────────────────────────────────────────────────
with tab_all:
    st.markdown('<div class="section-label">전체 자재 목록</div>', unsafe_allow_html=True)

    search = st.text_input("자재코드 / 자재내역 검색", placeholder="검색어 입력", key="search_all")

    view_df = agg_df.copy().sort_values("재고일수")
    if search:
        mask = (
            view_df["자재코드"].astype(str).str.contains(search, case=False, na=False) |
            view_df["자재내역"].astype(str).str.contains(search, case=False, na=False)
        )
        view_df = view_df[mask]

    if view_df.empty:
        st.info("검색 결과가 없습니다.")
    else:
        disp_all = view_df[["현황", "자재코드", "자재내역", "재고일수", "판매평균", "기말수량"]].copy()
        disp_all = disp_all.rename(columns={
            "현황": "등급", "판매평균": "3평판", "기말수량": "총재고량"})
        fmt_all = disp_all.copy()
        fmt_all["3평판"]   = fmt_all["3평판"].apply(lambda x: f"{x:,.0f}")
        fmt_all["총재고량"] = fmt_all["총재고량"].apply(lambda x: f"{x:,.0f}")
        fmt_all["재고일수"] = fmt_all["재고일수"].apply(
            lambda x: f"{x:.1f}일" if x < 999 else "999일+")

        def _style_all(val):
            if val == "위험": return "background-color:#EF4444;color:white;font-weight:700;"
            if val == "주의": return "background-color:#F59E0B;color:white;font-weight:700;"
            if val == "정상": return "background-color:#D1FAE5;color:#065F46;font-weight:700;"
            return ""

        styled_all = fmt_all.style.map(_style_all, subset=["등급"])
        st.dataframe(styled_all, use_container_width=True,
                     height=min(600, len(view_df) * 35 + 40),
                     hide_index=True)

        csv_all = disp_all.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv_all,
            f"stockout_all_{selected_year}_{selected_month}.csv", "text/csv")
