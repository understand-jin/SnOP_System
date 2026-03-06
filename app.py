import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from utils import load_stock_csv, load_stockout_csv

st.set_page_config(page_title="S&OP Dashboard", layout="wide", initial_sidebar_state="expanded")

# ── 대시보드 CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── 전체 배경 ── */
.stApp { background-color: #EEF2F7; }
.main .block-container {
    padding-top: 0 !important;
    padding-bottom: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100%;
}

/* ── 사이드바 ── */
[data-testid="stSidebar"] {
    background: #0B1E3F !important;
    border-right: none;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebarNav"] { padding: 0.5rem; }
[data-testid="stSidebarNav"] a {
    border-radius: 8px;
    padding: 0.55rem 0.9rem !important;
    margin-bottom: 2px;
    font-size: 0.875rem;
    font-weight: 500;
    color: #94A3B8 !important;
    transition: all 0.15s;
    display: block;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(255,255,255,0.08) !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(37,99,235,0.3) !important;
    color: #FFFFFF !important;
    font-weight: 600;
    border-left: 3px solid #3B82F6;
}
[data-testid="stSidebarNav"] span { color: inherit !important; }

/* ── 헤더 배너 ── */
.dash-header {
    background: linear-gradient(135deg, #0B1E3F 0%, #1565C0 100%);
    margin: -1px -2rem 2rem -2rem;
    padding: 1.4rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.dash-header-left { display: flex; align-items: center; gap: 14px; }
.dash-header-icon {
    width: 42px; height: 42px;
    background: rgba(255,255,255,0.15);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
}
.dash-header-title { color: #FFFFFF; font-size: 1.35rem; font-weight: 700; line-height: 1.2; }
.dash-header-sub { color: #93C5FD; font-size: 0.78rem; font-weight: 400; margin-top: 2px; }
.dash-header-right { display: flex; align-items: center; gap: 12px; }
.dash-badge {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    color: #E0F2FE;
    font-size: 0.75rem;
    font-weight: 500;
    padding: 0.35rem 0.85rem;
    border-radius: 20px;
}
.dash-badge-live {
    background: rgba(16,185,129,0.25);
    border: 1px solid rgba(16,185,129,0.4);
    color: #6EE7B7;
    display: flex; align-items: center; gap: 5px;
}
.live-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #10B981;
    animation: pulse 1.8s ease-in-out infinite;
    display: inline-block;
}
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* ── 패널 공통 ── */
.panel {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 4px rgba(15,23,42,0.06);
    overflow: hidden;
    margin-bottom: 1.2rem;
}
.panel-header {
    padding: 0.85rem 1.3rem;
    border-bottom: 1px solid #F1F5F9;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #FAFBFC;
}
.panel-title {
    font-size: 0.875rem;
    font-weight: 700;
    color: #1E293B;
    display: flex;
    align-items: center;
    gap: 8px;
}
.panel-body { padding: 1.2rem 1.3rem; }

/* ── KPI 카드 ── */
.kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05);
    border-top: 3px solid #E2E8F0;
    height: 100%;
}
.kpi-card.danger  { border-top-color: #EF4444; }
.kpi-card.warning { border-top-color: #F59E0B; }
.kpi-card.info    { border-top-color: #3B82F6; }
.kpi-card.success { border-top-color: #10B981; }

.kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 0.55rem;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.kpi-value.danger  { color: #DC2626; }
.kpi-value.warning { color: #D97706; }
.kpi-value.info    { color: #2563EB; }
.kpi-value.success { color: #059669; }
.kpi-unit { font-size: 0.9rem; font-weight: 600; color: #94A3B8; margin-left: 3px; }
.kpi-sub {
    font-size: 0.72rem;
    color: #94A3B8;
    margin-top: 0.3rem;
}

/* ── 상태 배지 ── */
.badge {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 0.7rem; font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
}
.badge-danger  { background: #FEE2E2; color: #DC2626; }
.badge-warning { background: #FEF3C7; color: #D97706; }
.badge-info    { background: #DBEAFE; color: #2563EB; }
.badge-success { background: #D1FAE5; color: #059669; }

/* ── 모듈 카드 ── */
.module-card {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
    padding: 1.2rem;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05);
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    text-decoration: none !important;
    display: flex;
    flex-direction: column;
    height: 100%;
    cursor: pointer;
}
.module-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(37,99,235,0.1);
    border-color: #3B82F6;
}
.module-icon-wrap {
    width: 40px; height: 40px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem;
    margin-bottom: 0.75rem;
}
.module-title {
    font-size: 0.875rem;
    font-weight: 700;
    color: #1E293B;
    margin-bottom: 0.3rem;
}
.module-desc {
    font-size: 0.75rem;
    color: #64748B;
    line-height: 1.5;
    flex-grow: 1;
    margin-bottom: 0.85rem;
}
.module-arrow {
    font-size: 0.72rem;
    font-weight: 600;
    color: #3B82F6;
    display: flex; align-items: center; gap: 3px;
    margin-top: auto;
}

/* ── 필터 바 ── */
.filter-bar {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.75rem 1.2rem;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1.2rem;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
}
.filter-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #475569;
    white-space: nowrap;
}

/* ── Streamlit 위젯 보정 ── */
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 10px; padding: 0.9rem 1.1rem;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
}
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 800 !important; color: #0F172A !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; font-weight: 600 !important; color: #64748B !important; }

.stButton > button {
    background-color: #2563EB; color: #FFFFFF; border: none;
    border-radius: 8px; font-weight: 600; font-size: 0.875rem;
    padding: 0.5rem 1.1rem; transition: background 0.15s;
}
.stButton > button:hover { background-color: #1D4ED8; }

[data-testid="stSelectbox"] > div > div {
    border-radius: 8px; border-color: #CBD5E1;
    font-size: 0.875rem;
}
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #E2E8F0; }

/* 섹션 라벨 */
.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.75rem;
    padding-left: 2px;
}

hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── 헤더 배너 ────────────────────────────────────────────────────
now_str = datetime.now().strftime("%Y.%m.%d %H:%M")
st.markdown(f"""
<div class="dash-header">
    <div class="dash-header-left">
        <div class="dash-header-icon">📊</div>
        <div>
            <div class="dash-header-title">S&amp;OP Intelligence Dashboard</div>
            <div class="dash-header-sub">SCM Innovation TFT · Supply Chain Analytics Platform</div>
        </div>
    </div>
    <div class="dash-header-right">
        <div class="dash-badge">{now_str} 기준</div>
        <div class="dash-badge dash-badge-live"><span class="live-dot"></span> LIVE</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 조회 기간 필터 ────────────────────────────────────────────────
c_filter1, c_filter2, c_spacer = st.columns([0.9, 0.9, 5])
with c_filter1:
    selected_year = st.selectbox(
        "연도",
        options=[f"{y}년" for y in range(2023, 2041)],
        index=range(2023, 2041).index(2025),
        label_visibility="collapsed"
    )
with c_filter2:
    selected_month = st.selectbox(
        "월",
        options=[f"{m}월" for m in range(1, 13)],
        index=11,
        label_visibility="collapsed"
    )
with c_spacer:
    st.markdown(f"""
    <div style="display:flex; align-items:center; height:38px; gap:8px; color:#64748B; font-size:0.8rem;">
        <span style="color:#94A3B8;">📅</span>
        <b style="color:#1E293B;">{selected_year} {selected_month}</b> 데이터 기준 리스크 현황
    </div>
    """, unsafe_allow_html=True)

# ── 데이터 로드 ──────────────────────────────────────────────────
stock_df    = None
stockout_df = None
try:
    stock_df    = load_stock_csv(selected_year, selected_month)
    stockout_df = load_stockout_csv(selected_year, selected_month)
except Exception:
    pass

# ── Stockout 계산 ─────────────────────────────────────────────────
if stockout_df is not None:
    risk_red    = stockout_df[stockout_df["재고일수"] < 30]
    risk_orange = stockout_df[(stockout_df["재고일수"] >= 30) & (stockout_df["재고일수"] < 60)]
    total_mat   = len(stockout_df)
    n_danger    = len(risk_red)
    n_warning   = len(risk_orange)
else:
    total_mat = n_danger = n_warning = "-"

# ── Aging Stock 계산 ─────────────────────────────────────────────
if stock_df is not None:
    BUCKET_COL = "expiry_bucket"
    VALUE_COL  = "Stock Value on Period End"
    def get_aging_metrics(buckets):
        sub = stock_df[stock_df[BUCKET_COL].isin(buckets)]
        return sub["배치"].nunique(), sub[VALUE_COL].sum()

    risk_6  = ["폐기확정(유효기한 지남)", "1개월 미만", "2개월 미만", "3개월 미만", "4개월 미만", "5개월 미만", "6개월 미만"]
    risk_7  = ["7개월 미만"]
    risk_9  = ["8개월 미만", "9개월 미만"]
    risk_12 = ["10개월 미만", "11개월 미만", "12개월 미만"]

    m6_c,  m6_v  = get_aging_metrics(risk_6)
    m7_c,  m7_v  = get_aging_metrics(risk_7)
    m9_c,  m9_v  = get_aging_metrics(risk_9)
    m12_c, m12_v = get_aging_metrics(risk_12)
    aging_v6_fmt  = f"₩{m6_v/1e8:,.1f}억"  if isinstance(m6_v,  (int,float)) else "-"
    aging_v7_fmt  = f"₩{m7_v/1e8:,.1f}억"  if isinstance(m7_v,  (int,float)) else "-"
    aging_v9_fmt  = f"₩{m9_v/1e8:,.1f}억"  if isinstance(m9_v,  (int,float)) else "-"
    aging_v12_fmt = f"₩{m12_v/1e8:,.1f}억" if isinstance(m12_v, (int,float)) else "-"
else:
    m6_c = m7_c = m9_c = m12_c = "-"
    aging_v6_fmt = aging_v7_fmt = aging_v9_fmt = aging_v12_fmt = "-"

# ── KPI 요약 카드 (상단 4개) ──────────────────────────────────────
st.markdown('<div class="section-label">핵심 리스크 현황</div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""
    <div class="kpi-card info">
        <div class="kpi-label">분석 대상 자재</div>
        <div class="kpi-value info">{total_mat}<span class="kpi-unit">종</span></div>
        <div class="kpi-sub">Stockout 분석 대상 전체</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="kpi-card danger">
        <div class="kpi-label">위험 자재 (30일 미만)</div>
        <div class="kpi-value danger">{n_danger}<span class="kpi-unit">종</span></div>
        <div class="kpi-sub"><span class="badge badge-danger">CRITICAL</span>&nbsp; 즉시 대응 필요</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class="kpi-card warning">
        <div class="kpi-label">주의 자재 (30~60일)</div>
        <div class="kpi-value warning">{n_warning}<span class="kpi-unit">종</span></div>
        <div class="kpi-sub"><span class="badge badge-warning">WARNING</span>&nbsp; 모니터링 필요</div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""
    <div class="kpi-card danger">
        <div class="kpi-label">부진재고 위험 금액 (6개월↓)</div>
        <div class="kpi-value" style="font-size:1.5rem; color:#DC2626;">{aging_v6_fmt}</div>
        <div class="kpi-sub"><span class="badge badge-danger">HIGH RISK</span>&nbsp; 배치 {m6_c}건</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── 상세 KPI 패널 (두 열) ─────────────────────────────────────────
left_col, right_col = st.columns([1, 1], gap="medium")

with left_col:
    # Stockout 패널
    st.markdown("""
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">🚨 Stockout Risk · 재고일수 분석</div>
            <span class="badge badge-info">Stockout</span>
        </div>
    </div>""", unsafe_allow_html=True)

    if stockout_df is not None:
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(f"""
            <div class="kpi-card danger" style="border-top-width:2px;">
                <div class="kpi-label" style="color:#EF4444;">위험</div>
                <div class="kpi-value danger" style="font-size:1.6rem;">{n_danger}</div>
                <div class="kpi-sub">30일 미만</div>
            </div>""", unsafe_allow_html=True)
        with s2:
            st.markdown(f"""
            <div class="kpi-card warning" style="border-top-width:2px;">
                <div class="kpi-label" style="color:#F59E0B;">주의</div>
                <div class="kpi-value warning" style="font-size:1.6rem;">{n_warning}</div>
                <div class="kpi-sub">30~60일</div>
            </div>""", unsafe_allow_html=True)
        with s3:
            st.markdown(f"""
            <div class="kpi-card info" style="border-top-width:2px;">
                <div class="kpi-label" style="color:#3B82F6;">전체</div>
                <div class="kpi-value info" style="font-size:1.6rem;">{total_mat}</div>
                <div class="kpi-sub">분석 자재 수</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info(f"{selected_year} {selected_month} Stockout 데이터 없음")

with right_col:
    # Aging Stock 패널
    st.markdown("""
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">📦 Aging Stock · 유효기한 리스크</div>
            <span class="badge badge-warning">Aging</span>
        </div>
    </div>""", unsafe_allow_html=True)

    if stock_df is not None:
        a1, a2 = st.columns(2)
        a3, a4 = st.columns(2)
        aging_rows = [
            (a1, "danger",  "⚠️ 6개월 미만", aging_v6_fmt,  f"배치 {m6_c}건"),
            (a2, "warning", "🔔 7개월 미만", aging_v7_fmt,  f"배치 {m7_c}건"),
            (a3, "info",    "ℹ️ 9개월 미만", aging_v9_fmt,  f"배치 {m9_c}건"),
            (a4, "success", "📅 12개월 미만", aging_v12_fmt, f"배치 {m12_c}건"),
        ]
        for col, cls, label, val, sub in aging_rows:
            with col:
                st.markdown(f"""
                <div class="kpi-card {cls}" style="border-top-width:2px; margin-bottom:0.6rem;">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value" style="font-size:1.2rem; color:#0F172A;">{val}</div>
                    <div class="kpi-sub">{sub}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info(f"{selected_year} {selected_month} Aging 데이터 없음")

st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ── 모듈 네비게이션 ───────────────────────────────────────────────
st.markdown('<div class="section-label">분석 모듈 바로가기</div>', unsafe_allow_html=True)

modules = [
    {"name": "Data Upload",         "icon": "📥", "color": "#DBEAFE", "path": "/Data_Upload",         "desc": "Excel/SAP 리포트 업로드 및 표준화"},
    {"name": "Table Manager",       "icon": "📋", "color": "#F3E8FF", "path": "/Table_Manager",       "desc": "마스터 데이터 조회 및 관리"},
    {"name": "Aging Stock Analysis","icon": "📦", "color": "#FEF3C7", "path": "/Aging_Stock_Analysis","desc": "유효기한 기반 부진재고 리스크 분석"},
    {"name": "Stockout Analysis",   "icon": "🚨", "color": "#FEE2E2", "path": "/Stockout_Analysis",   "desc": "재고일수 기반 수급 리스크 모니터링"},
    {"name": "Demand Baseline",     "icon": "📈", "color": "#D1FAE5", "path": "/Demand_Baseline",     "desc": "수요 예측 및 통계 분석"},
]

m_cols = st.columns(5)
for i, m in enumerate(modules):
    with m_cols[i]:
        st.markdown(f"""
        <a href="{m['path']}" target="_self" style="text-decoration:none;">
            <div class="module-card">
                <div class="module-icon-wrap" style="background:{m['color']};">{m['icon']}</div>
                <div class="module-title">{m['name']}</div>
                <div class="module-desc">{m['desc']}</div>
                <div class="module-arrow">바로가기 →</div>
            </div>
        </a>""", unsafe_allow_html=True)

# ── 푸터 ──────────────────────────────────────────────────────────
st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:center;
            padding: 0.8rem 0.2rem; border-top: 1px solid #E2E8F0;">
    <div style="color:#94A3B8; font-size:0.72rem;">
        © 2026 S&amp;OP Intelligence Platform &nbsp;|&nbsp; SCM Innovation TFT
    </div>
    <div style="color:#94A3B8; font-size:0.72rem;">
        Developed by <b style="color:#64748B;">LEE HYE JIN</b>
    </div>
</div>
""", unsafe_allow_html=True)
