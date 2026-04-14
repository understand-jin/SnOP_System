import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from po_utils import for_PO_check, load_PO_data
from card_html_utils import generate_inventory_html
from datetime import datetime

st.set_page_config(page_title="데일리 수요 모니터링", layout="wide")

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

hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.4rem 0; }
.upload-section { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px; margin-bottom: 8px; }
.upload-label { font-size: 0.72rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="dash-header">
  <div class="dash-header-left">
    <div class="dash-header-bar"></div>
    <div>
      <div class="dash-header-title">데일리 수요 모니터링</div>
      <div class="dash-header-sub">발주 의사결정 지원 데이터</div>
    </div>
  </div>
  <span class="dash-tag">데일리 수요 모니터링</span>
</div>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────────────────────────────
col_btn, col_time, col_gap = st.columns([1, 3, 3])
with col_btn:
    refresh = st.button("🔄 데이터 새로고침")
with col_time:
    if "po_last_refreshed" in st.session_state:
        st.markdown(
            f'<div style="padding-top:8px;font-size:0.78rem;color:#64748B;">'
            f'마지막 새로고침: <b>{st.session_state["po_last_refreshed"]}</b></div>',
            unsafe_allow_html=True
        )

if refresh:
    with st.spinner("SAP에서 최신 데이터 다운로드 중..."):
        try:
            st.session_state["po_df"], st.session_state["po_file_info"] = for_PO_check()
            st.session_state["po_last_refreshed"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 데이터 로드 실패: {e}")
            st.stop()
elif "po_df" not in st.session_state:
    with st.spinner("데이터 불러오는 중..."):
        try:
            st.session_state["po_df"], st.session_state["po_file_info"] = load_PO_data()
        except Exception as e:
            st.error(f"❌ 데이터 로드 실패: {e}")
            st.stop()

df = st.session_state["po_df"]

# ── 입력 데이터 현황 ──────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="section-label">입력 데이터 현황 (psi_input)</div>', unsafe_allow_html=True)
file_info = st.session_state.get("po_file_info", {})
fi_cols = st.columns(3)
for col, label in zip(fi_cols, ["품절예상조회", "재고개요", "SF"]):
    info = file_info.get(label)
    with col:
        if info:
            st.markdown(
                f'<div class="upload-section">'
                f'<div class="upload-label">{label}</div>'
                f'<div style="font-size:0.75rem;color:#16A34A;font-weight:600;">확인</div>'
                f'<div style="font-size:0.7rem;color:#64748B;margin-top:2px;word-break:break-all;">{info["name"]}</div>'
                f'<div style="font-size:0.68rem;color:#94A3B8;">{info["mtime"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="upload-section" style="border-color:#FCA5A5;">'
                f'<div class="upload-label">{label}</div>'
                f'<div style="font-size:0.75rem;color:#DC2626;font-weight:600;">파일 없음</div>'
                f'</div>',
                unsafe_allow_html=True
            )
st.markdown("<hr>", unsafe_allow_html=True)

# ── 검색 ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">데이터 검색</div>', unsafe_allow_html=True)
search = st.text_input("검색어 입력 (컬럼 전체 대상)", placeholder="자재코드, 자재내역 등...", label_visibility="collapsed")

if search:
    mask = df.apply(lambda col: col.astype(str).str.contains(search, case=False, na=False)).any(axis=1)
    view_df = df[mask].reset_index(drop=True)
else:
    view_df = df.copy()

# ── 결과 요약 ─────────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-label">총 {len(view_df):,}건</div>', unsafe_allow_html=True)

def progress_bar_html(value, color="#3B82F6"):
    """판매율 값(0.0~∞)을 프로그레스바 HTML로 변환. 100% 기준으로 클램프."""
    if value is None or (isinstance(value, float) and (value != value)):  # NaN 체크
        return '<span style="color:#CBD5E1;font-size:0.75rem;">-</span>'
    actual_pct = value * 100
    bar_pct = min(actual_pct, 100)
    if actual_pct >= 70:
        bar_color = "#EF4444"     # 빨강 (과다 판매)
    elif actual_pct >= 30:
        bar_color = "#10B981"     # 초록 (적정)
    else:
        bar_color = "#F59E0B"     # 주황 (저조)
    label = f"{actual_pct:.1f}%"
    return (
        f'<div style="display:flex;align-items:center;gap:6px;min-width:100px;">'
        f'  <div style="flex:1;background:#E2E8F0;border-radius:4px;height:8px;overflow:hidden;">'
        f'    <div style="width:{bar_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>'
        f'  </div>'
        f'  <span style="font-size:0.75rem;font-weight:700;color:{bar_color};white-space:nowrap;">{label}</span>'
        f'</div>'
    )

# ── 컬럼 분류 ─────────────────────────────────────────────────────────────────
FIXED_COLS = ["자재코드", "자재내역", "3평판", "SF", "당월출하", "판매율(평판)", "판매율(SF)"]
RATE_COLS  = ["판매율(평판)", "판매율(SF)"]

# 판매율(SF) 내림차순 정렬 (NaN은 맨 뒤)
display_df = view_df.copy()
if "판매율(SF)" in display_df.columns:
    display_df = display_df.sort_values("판매율(SF)", ascending=False, na_position="last").reset_index(drop=True)

# 창고(저장위치) 컬럼 = 데이터에 있으나 FIXED_COLS에 없는 나머지
WAREHOUSE_COLS = [c for c in display_df.columns if c not in FIXED_COLS]


# ── HTML 테이블 생성 ──────────────────────────────────────────────────────────
def render_table(df):
    TH = (
        'style="padding:8px 12px;font-size:0.72rem;font-weight:700;color:#64748B;'
        'white-space:nowrap;border-bottom:2px solid #E2E8F0;text-align:{align};"'
    )

    # 헤더: 고정 컬럼
    header_cells = ""
    for c in FIXED_COLS:
        if c not in df.columns:
            continue
        align = "right" if c in RATE_COLS else "left"
        header_cells += f'<th {TH.format(align=align)}>{c}</th>'

    # 헤더: 창고 컬럼 각각 1열
    for wh in WAREHOUSE_COLS:
        header_cells += f'<th {TH.format(align="right")}>{wh}</th>'

    # 창고별 최대값 (열 기준 히트맵용)
    wh_max = {}
    for wh in WAREHOUSE_COLS:
        try:
            wh_max[wh] = pd.to_numeric(df[wh], errors="coerce").max()
        except Exception:
            wh_max[wh] = 0

    rows = ""
    for i, row in df.iterrows():
        cells = ""

        # 고정 컬럼 셀
        for c in FIXED_COLS:
            if c not in df.columns:
                continue
            val = row[c]
            if c in RATE_COLS:
                cell_html = progress_bar_html(val)
                align = "left"
            elif isinstance(val, float):
                cell_html = f"{val:,.2f}" if val == val else "-"
                align = "right"
            elif isinstance(val, int):
                cell_html = f"{val:,}"
                align = "right"
            else:
                cell_html = str(val) if val == val else "-"
                align = "left"
            fw = "800" if c in ["3평판", "당월출하", "SF"] else "500"
            bg_extra = "background-color:#E0F2FE;" if c == "당월출하" else ""
            cells += (
                f'<td style="padding:7px 12px;text-align:{align};font-size:0.82rem;'
                f'font-weight:{fw};color:#1E293B;{bg_extra}border-bottom:1px solid #F1F5F9;">'
                f'{cell_html}</td>'
            )

        # 창고 컬럼 셀 (열 기준 히트맵)
        for wh in WAREHOUSE_COLS:
            v = row.get(wh, 0)
            try:
                num = int(v) if pd.notna(v) else 0
            except (TypeError, ValueError):
                num = 0

            mx = wh_max.get(wh, 0) or 0
            if num > 0 and mx > 0:
                intensity = 0.12 + (num / mx) * 0.55   # 0.12 ~ 0.67
                r = int(133 * intensity + 255 * (1 - intensity))
                g = int(183 * intensity + 255 * (1 - intensity))
                b = int(235 * intensity + 255 * (1 - intensity))
                cell_bg = f"background-color:rgb({r},{g},{b});"
                txt_color = "#1E3A5F"
            else:
                cell_bg = ""
                txt_color = "#CBD5E1"

            cell_val = f"{num:,}" if num > 0 else "-"
            cells += (
                f'<td style="padding:7px 12px;text-align:right;font-size:0.8rem;'
                f'font-weight:700;color:{txt_color};{cell_bg}border-bottom:1px solid #F1F5F9;">'
                f'{cell_val}</td>'
            )

        row_bg = "#FAFAFA" if i % 2 == 0 else "#FFFFFF"
        rows += f'<tr style="background:{row_bg};">{cells}</tr>'

    return (
        f'<div style="overflow-x:auto;border-radius:10px;border:1px solid #E2E8F0;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="background:#F8FAFC;">{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table></div>'
    )

tab_table, tab_card = st.tabs(["📋 테이블 뷰", "🃏 카드 뷰"])

with tab_table:
    st.dataframe(display_df, use_container_width=True, height=700)

with tab_card:
    if "판매율(SF)" in display_df.columns:
        rate = display_df["판매율(SF)"]
        df_급등 = display_df[rate > 1.0].reset_index(drop=True)
        df_주의 = display_df[(rate >= 0.8) & (rate <= 1.0)].reset_index(drop=True)
        df_안정 = display_df[(rate < 0.8) | rate.isna()].reset_index(drop=True)
    else:
        df_급등, df_주의, df_안정 = pd.DataFrame(), pd.DataFrame(), display_df

    sub_급등, sub_주의, sub_안정 = st.tabs([
        f"🔴 판매율 급등 ({len(df_급등)})",
        f"🟡 주의 ({len(df_주의)})",
        f"🔵 안정 ({len(df_안정)})",
    ])

    def _render_card_tab(sub_df, tab_obj):
        with tab_obj:
            if sub_df.empty:
                st.info("해당 항목이 없습니다.")
            else:
                card_html = generate_inventory_html(sub_df)
                card_height = max(400, len(sub_df) * 230)
                components.html(card_html, height=card_height, scrolling=True)

    _render_card_tab(df_급등, sub_급등)
    _render_card_tab(df_주의, sub_주의)
    _render_card_tab(df_안정, sub_안정)

# ── 다운로드 ─────────────────────────────────────────────────────────────────
csv_bytes = view_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button("⬇️ CSV 다운로드", csv_bytes, "po_check.csv", "text/csv")
