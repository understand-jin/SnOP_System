import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from utils import load_stock_csv, load_stockout_csv

# ✅ 페이지 설정
st.set_page_config(page_title="S&OP System", layout="wide")

# --- 🎨 커스텀 CSS (프리미엄 UI) ---
st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .main {
        background-color: #fcfcfc;
    }
    
    /* 헤더 스타일 */
    .header-container {
        text-align: center;
        padding: 2rem 0;
    }
    .main-title {
        font-family: 'Inter', sans-serif;
        color: #3b82f6; /* Blue-600 */
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* 섹션 제목 스타일 */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.4rem;
        font-weight: 700;
        color: #1e293b;
        margin: 2rem 0 1rem 0;
        padding-left: 10px;
        border-left: 5px solid #3b82f6;
    }

    /* 카드 그리드 스타일 */
    .nav-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }

    /* 카드 스타일 */
    .card {
        background-color: #ffffff;
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
        text-decoration: none !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #3b82f6;
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .card-desc {
        color: #64748b;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        line-height: 1.4;
    }
    .card-link {
        color: #3b82f6;
        font-weight: 600;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        gap: 5px;
        margin-top: auto;
    }

    /* 메트릭 박스 스타일 */
    .metric-container {
        background-color: #ffffff;
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        text-align: left;
        margin-bottom: 10px; /* 여유 공간 추가 */
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 0.6rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
    }
    .metric-unit {
        font-size: 1.1rem;
        font-weight: 600;
        margin-left: 4px;
        color: #334155;
    }
    
    /* 하이라이트 박스 */
    .info-box {
        background-color: #eff6ff;
        border: 1px solid #dbeafe;
        padding: 0.8rem 1.2rem;
        border-radius: 8px;
        color: #1d4ed8;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- 🏠 헤더 섹션 ---
st.markdown("""
<div class="header-container">
    <div class="main-title">📊 S&OP System</div>
    <div class="sub-title">데이터 기반의 효율적인 관리 및 수급 리스크 분석을 위한 자동화 시스템</div>
</div>
""", unsafe_allow_html=True)

# --- 💡 주요 기능 안내 섹션 ---
st.markdown('<div class="section-header">💡 주요 기능 안내</div>', unsafe_allow_html=True)

# 5개 페이지에 대한 카드 생성 (실제 파일명 및 경로 반영)
pages_info = [
    {"name": "Data Upload", "icon": "📥", "desc": "Excel/SAP 리포트 업로드 및 표준화", "path": "/Data_Upload"},
    {"name": "Table Manager", "icon": "📋", "desc": "마스터 데이터 조회 및 관리", "path": "/Table_Manager"},
    {"name": "Aging Stock Analysis", "icon": "📦", "desc": "유효기한 기반 부진재고 리스크 분석", "path": "/Aging_Stock_Analysis"},
    {"name": "Stockout Analysis", "icon": "🚨", "desc": "재고일수 기반 수급 리스크 모니터링", "path": "/Stockout_Analysis"},
    {"name": "Demand Baseline", "icon": "📈", "desc": "수요 예측 및 통계 분석", "path": "/Demand_Baseline"}
]

# 카드 레이아웃 (한 줄에 3개, 다음 줄에 2개)
cols = st.columns(3)
for i, info in enumerate(pages_info[:3]):
    with cols[i]:
        st.markdown(f"""
        <a href="{info['path']}" target="_self" style="text-decoration: none;">
            <div class="card">
                <div class="card-title">{info['icon']} {info['name']}</div>
                <div class="card-desc">{info['desc']}</div>
                <div class="card-link">{info['name']}로 이동 →</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

cols2 = st.columns(3)
for i, info in enumerate(pages_info[3:]):
    with cols2[i]:
        st.markdown(f"""
        <a href="{info['path']}" target="_self" style="text-decoration: none;">
            <div class="card">
                <div class="card-title">{info['icon']} {info['name']}</div>
                <div class="card-desc">{info['desc']}</div>
                <div class="card-link">{info['name']}로 이동 →</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

st.markdown("<br><hr>", unsafe_allow_html=True)

# --- 🎯 핵심 KPI 조회 섹션 ---
st.markdown('<div class="section-header">🎯 핵심 KPI 조회</div>', unsafe_allow_html=True)

with st.container(border=True):
    # 1) 조회 기간 필터
    st.markdown("#### 📅 조회 기간 선택")
    c_filter1, c_filter2, c_info = st.columns([1, 1, 3])

    with c_filter1:
        current_year = datetime.now().year
        selected_year = st.selectbox(
            "조회 연도",
            options=[f"{y}년" for y in range(2023, 2041)],
            ####################################
            # 이 부분 나중에 인덱스 수정하면 기본값은 가장 최신으로 설정 가능한 (연도) 즉 걍 주석처리 풀면 됌#############################################
            ######################################
            #index=range(2023, 2041).index(current_year) if current_year in range(2023, 2041) else 2,
            index=range(2023, 2041).index(2025),
            label_visibility="collapsed"
        )

    with c_filter2:
        selected_month = st.selectbox(
            "조회 월",
            options=[f"{m}월" for m in range(1, 13)],
            ####################################
            # 이 부분 나중에 인덱스 수정하면!! 기본값은 가장 최신으로 설정 가능한 (월) 즉 걍 주석처리 풀면 됌###################################################
            ######################################
            #index=datetime.now().month - 1,
            index=11,
            label_visibility="collapsed"
        )

    with c_info:
        st.markdown(f"""
        <div class="info-box">
            📍 현재 기준: <b>{selected_year} {selected_month}</b> 데이터를 기반으로 리스크 현황을 요약합니다.
        </div>
        """, unsafe_allow_html=True)

    # 데이터 로드
    stock_df = None
    stockout_df = None

    try:
        stock_df = load_stock_csv(selected_year, selected_month)
        stockout_df = load_stockout_csv(selected_year, selected_month)
    except Exception:
        pass

    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # 2) Stockout Analysis 현황
    st.markdown("#### 🚨 Stockout Analysis 현황")
    with st.container(border=True):
        if stockout_df is not None:
            # 재고일수 기준 분류
            risk_red = stockout_df[stockout_df["재고일수"] < 30]
            risk_orange = stockout_df[(stockout_df["재고일수"] >= 30) & (stockout_df["재고일수"] < 60)]
            
            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown(f'<div class="metric-container"><div class="metric-label" style="color: #ef4444;">🔴 위험 (30일 미만)</div><div class="metric-value">{len(risk_red)}<span class="metric-unit">종</span></div></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="metric-container"><div class="metric-label" style="color: #f59e0b;">🟠 주의 (60일 미만)</div><div class="metric-value">{len(risk_orange)}<span class="metric-unit">종</span></div></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="metric-container"><div class="metric-label">📊 분석 대상 총 자재 수</div><div class="metric-value">{len(stockout_df)}<span class="metric-unit">종</span></div></div>', unsafe_allow_html=True)
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True) # 하단 여백 추가
        else:
            st.info(f"{selected_year} {selected_month}의 Stockout 분석 데이터가 없습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3) Aging Stock Analysis 현황
    st.markdown("#### 📦 Aging Stock Analysis 현황")
    with st.container(border=True):
        if stock_df is not None:
            # Aging Stock 계산 로직
            BUCKET_COL = "expiry_bucket"
            VALUE_COL = "Stock Value on Period End"
            
            def get_aging_metrics(target_buckets):
                sub_df = stock_df[stock_df[BUCKET_COL].isin(target_buckets)]
                batch_count = sub_df["배치"].nunique()
                risk_value = sub_df[VALUE_COL].sum()
                return batch_count, risk_value

            risk_6 = ["폐기확정(유효기한 지남)", "1개월 미만", "2개월 미만", "3개월 미만", "4개월 미만", "5개월 미만", "6개월 미만"]
            risk_7 = ["7개월 미만"]
            risk_9 = ["8개월 미만", "9개월 미만"]
            risk_12 = ["10개월 미만", "11개월 미만", "12개월 미만"]

            m6_c, m6_v = get_aging_metrics(risk_6)
            m7_c, m7_v = get_aging_metrics(risk_7)
            m9_c, m9_v = get_aging_metrics(risk_9)
            m12_c, m12_v = get_aging_metrics(risk_12)

            a1, a2, a3, a4 = st.columns(4)
            with a1:
                st.markdown(f'<div class="metric-container"><div class="metric-label">⚠️ 6개월 미만</div><div class="metric-value">₩{m6_v:,.0f}</div></div>', unsafe_allow_html=True)
            with a2:
                st.markdown(f'<div class="metric-container"><div class="metric-label">🔔 7개월 미만</div><div class="metric-value">₩{m7_v:,.0f}</div></div>', unsafe_allow_html=True)
            with a3:
                st.markdown(f'<div class="metric-container"><div class="metric-label">ℹ️ 9개월 미만</div><div class="metric-value">₩{m9_v:,.0f}</div></div>', unsafe_allow_html=True)
            with a4:
                st.markdown(f'<div class="metric-container"><div class="metric-label">📅 12개월 미만</div><div class="metric-value">₩{m12_v:,.0f}</div></div>', unsafe_allow_html=True)
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True) # 하단 여백 추가
        else:
            st.info(f"{selected_year} {selected_month}의 Aging 분석 데이터가 없습니다.")

# Footer
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(
    '''
    <div style="text-align: center; color: #94a3b8; font-size: 0.8rem;">
        © 2026 S&OP Intelligence Platform | SCM Innovation TFT<br>
        Developed by <b>LEE HYE JIN</b>
    </div>
    ''',
    unsafe_allow_html=True
)
#st.markdown('<div style="text-align: center; color: #94a3b8; font-size: 0.8rem;">© 2026 S&OP System. All rights reserved.</div>', unsafe_allow_html=True)
