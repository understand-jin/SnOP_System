import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="재고 소진계획", layout="wide")

###############################################################################
# CSS
###############################################################################
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
    padding: 1.3rem 2.8rem;
    display: flex; align-items: center; justify-content: space-between;
}
.dash-header-left { display: flex; align-items: center; gap: 16px; }
.dash-header-bar {
    width: 4px; height: 38px; background: #60A5FA;
    border-radius: 2px; flex-shrink: 0;
}
.dash-header-title { color: #FFFFFF; font-size: 1.3rem; font-weight: 700; letter-spacing: -0.3px; }
.dash-header-sub { color: #93C5FD; font-size: 0.78rem; margin-top: 3px; font-weight: 400; }
.dash-tag {
    background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
    color: #BFDBFE; font-size: 0.72rem; font-weight: 600;
    padding: 0.3rem 0.9rem; border-radius: 4px; letter-spacing: 0.5px;
}

/* ── 메트릭 ── */
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: 0.9rem 1.2rem; box-shadow: 0 1px 4px rgba(15,23,42,0.05);
    border-top: 3px solid #2563EB;
}
[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 800 !important; color: #0F172A !important; }
[data-testid="stMetricLabel"] { font-size: 0.72rem !important; font-weight: 600 !important; color: #64748B !important; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── 섹션 라벨 ── */
.section-label {
    font-size: 0.68rem; font-weight: 700; color: #94A3B8;
    text-transform: uppercase; letter-spacing: 1.2px;
    margin-bottom: 0.6rem; padding-left: 2px;
}

/* ── 정보 바 ── */
.info-bar {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 0.65rem 1.4rem; display: flex; align-items: center; gap: 20px;
    margin-bottom: 1.4rem; flex-wrap: wrap;
}
.info-item { font-size: 0.78rem; color: #64748B; }
.info-item strong { color: #1E293B; font-weight: 700; }
.info-divider { width: 1px; height: 14px; background: #E2E8F0; }

/* ── 유효기한 색상 ── */
.exp-danger { font-size: 0.78rem; font-weight: 700; color: #DC2626; }
.exp-warn   { font-size: 0.78rem; font-weight: 700; color: #D97706; }
.exp-ok     { font-size: 0.78rem; font-weight: 600; color: #374151; }

/* ── 6개월 진입 배지 ── */
.rb-now  { display:inline-block; background:#FEE2E2; color:#B91C1C; border:1px solid #FECACA; border-radius:4px; padding:2px 9px; font-size:0.75rem; font-weight:700; }
.rb-soon { display:inline-block; background:#FEF3C7; color:#92400E; border:1px solid #FDE68A; border-radius:4px; padding:2px 9px; font-size:0.75rem; font-weight:700; }
.rb-ok   { display:inline-block; background:#DBEAFE; color:#1E40AF; border:1px solid #BFDBFE; border-radius:4px; padding:2px 9px; font-size:0.75rem; font-weight:700; }
.rb-none { font-size:0.72rem; color:#94A3B8; }

/* ── 버킷 구분 ── */
.bucket-bar {
    display: flex; align-items: center; gap: 10px;
    margin: 20px 0 8px 0;
    color: #94A3B8;
}
.bucket-bar::before, .bucket-bar::after {
    content: ''; flex: 1;
    height: 1px; background: #E2E8F0;
}
.bucket-bar span {
    font-size: 0.68rem; font-weight: 600;
    color: #94A3B8; white-space: nowrap;
    letter-spacing: 0.5px;
}

/* ── Timeline 카드 메타 헤더 ── */
.tl-meta {
    background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%);
    border: 1.5px solid #E2E8F0;
    border-left: 4px solid #3B82F6;
    border-radius: 8px 8px 0 0;
    padding: 9px 16px;
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 4px;
}
.tl-code  { font-size: 0.82rem; font-weight: 800; color: #1E293B; font-family: 'Courier New', monospace; background:#EFF6FF; padding:1px 6px; border-radius:4px; }
.tl-name  { font-size: 0.85rem; font-weight: 700; color: #1E293B; }
.tl-batch { font-size: 0.74rem; color: #64748B; font-weight: 500; background:#F1F5F9; padding:1px 6px; border-radius:4px; }
.tl-sep   { color: #CBD5E1; font-size: 0.8rem; }
.tl-lbl   { font-size: 0.67rem; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.3px; margin-right: 2px; }
.tl-val   { font-size: 0.78rem; font-weight: 700; color: #1E293B; }
.tl-info  { font-size: 0.78rem; color: #374151; }
.tl-tag-risk   { display:inline-block; background:#FEF3C7; color:#92400E; border:1px solid #FDE68A; border-radius:4px; padding:1px 7px; font-size:0.7rem; font-weight:700; }
.tl-tag-expire { display:inline-block; background:#FEE2E2; color:#B91C1C; border:1px solid #FECACA; border-radius:4px; padding:1px 7px; font-size:0.7rem; font-weight:700; }

/* ── Timeline strip 월 레이블 ── */
.tl-month-label {
    text-align: center;
    padding: 4px 2px 3px 2px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.3px;
    line-height: 1.3;
    border-radius: 4px 4px 0 0;
}
.tl-lbl-normal { color: #1D4ED8; background: #EFF6FF; border: 2px solid #93C5FD; border-bottom: none; }
.tl-lbl-risk   { color: #9A3412; background: #FFF7ED; border: 2px solid #FB923C; border-bottom: none; }
.tl-lbl-expire { color: #B91C1C; background: #FEF2F2; border: 2px solid #FCA5A5; border-bottom: none; }
.tl-lbl-dead   { color: #9CA3AF; background: #F3F4F6; border: 2px solid #E5E7EB; border-bottom: none; }
.tl-lbl-note   { color: #64748B; background: #F8FAFC; border: 2px solid #E2E8F0; border-bottom: none; }

/* ── 폐기후 셀 ── */
.tl-dead-cell {
    font-size: 0.72rem; font-weight: 600;
    color: #9CA3AF; background: #F3F4F6;
    border: 2px solid #E5E7EB;
    border-radius: 0 0 5px 5px;
    text-align: center; padding: 7px 0;
}

/* ── 행 구분선 ── */
.row-sep { border: none; border-top: 1px solid #E2E8F0; margin: 10px 0 4px 0; }

/* ── 입력 칸 (기본 — 정상 구간) ── */
div[data-testid="stNumberInput"] {
    margin-top: -4px !important;
}
div[data-testid="stNumberInput"] > div {
    background-color: #EFF6FF !important;
    border: 2px solid #93C5FD !important;
    border-radius: 0 0 6px 6px !important;
    border-top: none !important;
}
div[data-testid="stNumberInput"] > div:focus-within {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
    background-color: #FFFFFF !important;
}
div[data-testid="stNumberInput"] input {
    background: transparent !important;
    color: #1E3A8A !important;
    font-weight: 800 !important;
    font-size: 0.88rem !important;
    text-align: center !important;
    padding: 4px !important;
}
div[data-testid="stNumberInput"] button { display: none !important; }

/* ── 비고 입력 ── */
div[data-testid="stTextInput"] {
    margin-top: -4px !important;
}
div[data-testid="stTextInput"] > div {
    border-radius: 0 0 6px 6px !important;
    border-top: none !important;
    border-color: #E2E8F0 !important;
    background: #F8FAFC !important;
}
div[data-testid="stTextInput"] input { font-size: 0.78rem !important; color: #374151 !important; }

/* ── 버튼 ── */
.stButton > button {
    background: #1E40AF; color: #FFFFFF; border: none;
    border-radius: 7px; font-weight: 600; font-size: 0.875rem;
    padding: 0.5rem 1.2rem; transition: background 0.15s;
}
.stButton > button:hover { background: #1D4ED8; }

hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

###############################################################################
# 세션 데이터 — 없으면 연도/월 선택 후 CSV에서 자동 로드
###############################################################################
from datetime import datetime as _dt

target_year  = st.session_state.get("plan_target_year", "")
target_month = st.session_state.get("plan_target_month", "")

if not target_year or not target_month:
    _cy = _dt.now().year
    _cm = _dt.now().month
    _yc, _mc = st.columns([2, 2])
    with _yc:
        target_year  = st.selectbox("연도", [f"{y}년" for y in range(2023, 2041)],
                                    index=range(2023, 2041).index(_cy) if _cy in range(2023, 2041) else 0,
                                    key="_dp_year")
    with _mc:
        target_month = st.selectbox("월", [f"{m}월" for m in range(1, 13)],
                                    index=_cm - 1, key="_dp_month")

target_dir = st.session_state.get("plan_target_dir") or os.path.join("data", target_year, target_month)
ref_label  = f"{target_year} {target_month}"

major_df = st.session_state.get("major_management_df")
if major_df is None or major_df.empty:
    _csv_path = os.path.join(target_dir, "major_management_inventory.csv")
    if os.path.exists(_csv_path):
        try:
            major_df = pd.read_csv(_csv_path, encoding="utf-8-sig")
            st.info(f"저장된 중점관리 데이터를 불러왔습니다.  ({_csv_path})")
        except Exception as _e:
            st.error(f"CSV 로드 오류: {_e}")
            major_df = None

# 헤더 배너
st.markdown(f"""
<div class="dash-header">
  <div class="dash-header-left">
    <div class="dash-header-bar"></div>
    <div>
      <div class="dash-header-title">재고 소진계획 입력</div>
      <div class="dash-header-sub">중점관리 대상 품목 · 월별 소진 목표 수량 입력</div>
    </div>
  </div>
  <div style="display:flex;gap:8px;align-items:center;">
    <span class="dash-tag">기준 {ref_label}</span>
    <span class="dash-tag">DEPLETION PLAN</span>
  </div>
</div>
""", unsafe_allow_html=True)

if major_df is None or major_df.empty:
    st.error("중점관리 대상 품목 데이터가 없습니다. Aging Stock 페이지에서 분석을 먼저 실행하세요.")
    if st.button("Aging Stock 으로 돌아가기"):
        st.switch_page("pages/7_Aging_Stock.py")
    st.stop()

###############################################################################
# 월 목록 — 기준월 다음 달부터 시작
###############################################################################
today = pd.Timestamp.today().normalize()

try:
    year_int  = int(str(target_year).replace("년", "").strip())
    month_int = int(str(target_month).replace("월", "").strip())
except Exception:
    year_int, month_int = today.year, today.month

nm = month_int + 1
ny = year_int
if nm > 12:
    nm, ny = 1, ny + 1
plan_start = pd.Timestamp(year=ny, month=nm, day=1)

if "남은일" in major_df.columns:
    max_days = pd.to_numeric(major_df["남은일"], errors="coerce").max()
    last_ts  = today + pd.Timedelta(days=max(int(max_days) - 180, 0))
else:
    last_ts = today + pd.Timedelta(days=180)

all_months, cur = [], plan_start
end = last_ts.replace(day=1)
while cur <= end:
    all_months.append(cur)
    cur = cur.replace(month=cur.month + 1) if cur.month < 12 else cur.replace(year=cur.year + 1, month=1)
month_labels = [f"{int(m.strftime('%m'))}월" for m in all_months]

###############################################################################
# KPI
###############################################################################
total_items = major_df["자재코드"].nunique() if "자재코드" in major_df.columns else len(major_df)
total_batch = major_df["배치"].nunique()     if "배치"    in major_df.columns else len(major_df)
total_amt   = pd.to_numeric(major_df.get("기말금액", pd.Series(dtype=float)), errors="coerce").sum()

st.markdown('<div class="section-label">소진계획 개요</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("중점관리 자재",  f"{total_items} 종")
c2.metric("대상 배치",      f"{total_batch} 건")
c3.metric("총 위험 재고",   f"₩{total_amt/1e8:,.1f}억")
c4.metric("계획 기간",
          f"{month_labels[0] if month_labels else '-'} ~ {month_labels[-1] if month_labels else '-'} "
          f"({len(all_months)}개월)")

st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

st.markdown(f"""
<div class="info-bar">
  <div class="info-item">데이터 기준&nbsp; <strong>{ref_label}</strong></div>
  <div class="info-divider"></div>
  <div class="info-item">소진계획 시작&nbsp; <strong style="color:#2563EB;">{month_labels[0] if month_labels else '-'}</strong>&nbsp; (기준월 다음달)</div>
  <div class="info-divider"></div>
  <div class="info-item">
    <span style="display:inline-block;width:11px;height:11px;background:#EFF6FF;border:2px solid #93C5FD;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>정상&nbsp;&nbsp;
    <span style="display:inline-block;width:11px;height:11px;background:#FFF7ED;border:2px solid #FB923C;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>⚠ 6개월 위험&nbsp;&nbsp;
    <span style="display:inline-block;width:11px;height:11px;background:#FEF2F2;border:2px solid #FCA5A5;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>💀 폐기월
  </div>
</div>
""", unsafe_allow_html=True)

col_back_top, _ = st.columns([1, 8])
with col_back_top:
    if st.button("Aging Stock", key="back_top"):
        st.switch_page("pages/7_Aging_Stock.py")

st.markdown("<hr>", unsafe_allow_html=True)

###############################################################################
# 기존 소진계획 불러오기
###############################################################################
plan_csv_path = os.path.join(target_dir, "소진계획.csv")
existing_plan = {}
if os.path.exists(plan_csv_path):
    try:
        existing_df = pd.read_csv(plan_csv_path, encoding="utf-8-sig")
        for _, erow in existing_df.iterrows():
            batch_key = str(erow["배치"]) if "배치" in existing_df.columns else ""
            existing_plan[(str(erow["자재코드"]), batch_key)] = erow
    except Exception:
        pass

###############################################################################
# 세팅
###############################################################################
bucket_col = "유효기한구간" if "유효기한구간" in major_df.columns else None
sort_cols  = ["남은일"] if "남은일" in major_df.columns else []
rows_df    = major_df.sort_values(sort_cols) if sort_cols else major_df

MONTH_STRIP_WIDTHS = [1.0] * len(all_months) + [1.5]  # 마지막 = 비고

###############################################################################
# 섹션 라벨
###############################################################################
st.markdown('<div class="section-label">월별 소진계획 Timeline</div>', unsafe_allow_html=True)

###############################################################################
# Timeline 렌더링
###############################################################################
plan_inputs        = {}
last_bucket        = None
risk_zone_labels   = []
expire_zone_labels = []

for row_idx, (_, row) in enumerate(rows_df.iterrows()):
    bucket     = str(row.get(bucket_col, "")) if bucket_col else ""
    mat_code   = str(row.get("자재코드", ""))
    mat_name   = str(row.get("자재내역", ""))
    batch      = str(row.get("배치", ""))
    expiry_raw = row.get("유효기한", "")
    days_left  = pd.to_numeric(row.get("남은일", None), errors="coerce")
    qty        = row.get("기말수량", 0)
    amt        = row.get("기말금액", 0)

    expiry_dt  = pd.to_datetime(expiry_raw, errors="coerce")
    expiry_str = expiry_dt.strftime("%Y-%m-%d") if pd.notna(expiry_dt) else "-"

    # 위험 날짜 계산
    if pd.notna(days_left):
        risk6_ts       = today + pd.Timedelta(days=int(days_left) - 180)
        expiry_ts      = today + pd.Timedelta(days=int(days_left))
        risk6_month_ts = pd.Timestamp(year=risk6_ts.year,  month=risk6_ts.month,  day=1)
        expire_month_ts= pd.Timestamp(year=expiry_ts.year, month=expiry_ts.month, day=1)
        days_to_risk6  = (risk6_ts - today).days

        if days_to_risk6 <= 0:
            risk6_badge = f'<span class="rb-now">{risk6_ts.strftime("%Y.%m.%d")}</span>'
        elif days_to_risk6 <= 90:
            risk6_badge = f'<span class="rb-soon">{risk6_ts.strftime("%Y.%m.%d")}</span>'
        else:
            risk6_badge = f'<span class="rb-ok">{risk6_ts.strftime("%Y.%m.%d")}</span>'
    else:
        risk6_ts = expiry_ts = None
        risk6_month_ts = expire_month_ts = None
        risk6_badge = '<span class="rb-none">-</span>'

    # 버킷 구분선
    if bucket != last_bucket:
        last_bucket = bucket
        st.markdown(f'<div class="bucket-bar"><span>{bucket}</span></div>', unsafe_allow_html=True)

    # 표시 형식
    qty_str = f"{float(qty):,.0f}" if qty not in ("", None) else "-"
    try:
        amt_val = float(amt)
        amt_str = f"₩{amt_val/1e8:,.2f}억" if amt_val >= 1e7 else f"₩{amt_val:,.0f}"
    except Exception:
        amt_str = "-"

    if pd.notna(days_left):
        exp_cls = "exp-danger" if days_left < 180 else ("exp-warn" if days_left < 270 else "exp-ok")
    else:
        exp_cls = "exp-ok"

    # 구간 태그
    risk_cnt = sum(
        1 for m in all_months
        if risk6_month_ts is not None and expire_month_ts is not None
        and m >= risk6_month_ts and m < expire_month_ts
    )
    has_expire = expire_month_ts is not None and expire_month_ts >= plan_start and expire_month_ts <= end

    risk_tag   = f'<span class="tl-tag-risk">⚠ 위험 {risk_cnt}개월</span>' if risk_cnt > 0 else ""
    expire_tag = f'<span class="tl-tag-expire">💀 {int(expire_month_ts.month)}월 폐기</span>' if has_expire else ""

    # ── 카드 메타 헤더 ────────────────────────────────────────────
    st.markdown(f"""
    <div class="tl-meta">
      <span class="tl-code">{mat_code}</span>
      <span class="tl-sep">│</span>
      <span class="tl-name">{mat_name}</span>
      <span class="tl-sep">│</span>
      <span class="tl-batch">배치 {batch}</span>
      <span class="tl-sep">│</span>
      <span class="tl-info"><span class="tl-lbl">유효기한</span><span class="{exp_cls}">{expiry_str}</span></span>
      <span class="tl-sep">│</span>
      <span class="tl-info"><span class="tl-lbl">기말수량</span><span class="tl-val">{qty_str}</span></span>
      <span class="tl-sep">│</span>
      <span class="tl-info"><span class="tl-lbl">금액</span><span class="tl-val">{amt_str}</span></span>
      <span class="tl-sep">│</span>
      <span class="tl-info"><span class="tl-lbl">6개월진입</span>{risk6_badge}</span>
      {risk_tag}{expire_tag}
    </div>
    """, unsafe_allow_html=True)

    # ── Timeline strip + 입력 ────────────────────────────────────
    plan_inputs[(mat_code, batch)] = {}
    mcols = st.columns(MONTH_STRIP_WIDTHS)

    for mi, (mcol_ts, mlabel) in enumerate(zip(all_months, month_labels)):
        is_after_expiry = (expire_month_ts is not None and mcol_ts > expire_month_ts)
        is_expire_month = (expire_month_ts is not None and mcol_ts == expire_month_ts)
        is_risk_zone    = (risk6_month_ts  is not None and expire_month_ts is not None
                           and mcol_ts >= risk6_month_ts and mcol_ts < expire_month_ts)

        with mcols[mi]:
            if is_after_expiry:
                st.markdown(f'<div class="tl-month-label tl-lbl-dead">{mlabel}</div>',
                            unsafe_allow_html=True)
                st.markdown('<div class="tl-dead-cell">—</div>', unsafe_allow_html=True)
                plan_inputs[(mat_code, batch)][mlabel] = 0
                continue

            # 레이블 색상
            if is_expire_month:
                lbl_cls  = "tl-lbl-expire"
                lbl_text = f"💀 {mlabel}"
            elif is_risk_zone:
                lbl_cls  = "tl-lbl-risk"
                lbl_text = f"⚠ {mlabel}"
            else:
                lbl_cls  = "tl-lbl-normal"
                lbl_text = mlabel

            st.markdown(f'<div class="tl-month-label {lbl_cls}">{lbl_text}</div>',
                        unsafe_allow_html=True)

            input_label = f"_{mat_code}_{batch}_{mlabel}"
            if is_risk_zone:
                risk_zone_labels.append(input_label)
            elif is_expire_month:
                expire_zone_labels.append(input_label)

            # 기존 저장값
            saved_val = 0.0
            saved_row = existing_plan.get((mat_code, batch))
            if saved_row is not None and mlabel in saved_row:
                try:
                    saved_val = float(saved_row[mlabel])
                except Exception:
                    saved_val = 0.0

            val = st.number_input(
                label=input_label,
                min_value=0.0,
                value=saved_val,
                step=1.0,
                label_visibility="collapsed",
                key=f"dp_{row_idx}_{mat_code}_{batch}_{mlabel}"
            )
            plan_inputs[(mat_code, batch)][mlabel] = val

    # ── 비고 ─────────────────────────────────────────────────────
    with mcols[-1]:
        st.markdown('<div class="tl-month-label tl-lbl-note">비고</div>',
                    unsafe_allow_html=True)
        saved_row = existing_plan.get((mat_code, batch))
        saved_note = ""
        if saved_row is not None and "비고" in saved_row:
            raw_note = str(saved_row["비고"])
            saved_note = "" if raw_note == "nan" else raw_note

        note_val = st.text_input(
            label=f"note_{mat_code}_{batch}",
            value=saved_note,
            placeholder="소진 전략 메모",
            label_visibility="collapsed",
            key=f"note_{row_idx}_{mat_code}_{batch}"
        )
    plan_inputs[(mat_code, batch)]["__note__"] = note_val

    st.markdown('<hr class="row-sep">', unsafe_allow_html=True)

###############################################################################
# 리스크 구간 CSS 주입 (그리드 렌더링 완료 후)
###############################################################################
def _css_sel(labels, extra=""):
    return ", ".join(
        f'div[data-testid="stNumberInput"]:has(input[aria-label="{l}"]){extra}'
        for l in labels
    )

css_parts = []

if risk_zone_labels:
    css_parts.append(f"""
    {_css_sel(risk_zone_labels, " > div")} {{
        background-color: #FFF7ED !important;
        border-color: #FB923C !important;
    }}
    {_css_sel(risk_zone_labels, " input")} {{
        color: #9A3412 !important;
    }}
    """)

if expire_zone_labels:
    css_parts.append(f"""
    {_css_sel(expire_zone_labels, " > div")} {{
        background-color: #FEF2F2 !important;
        border-color: #FCA5A5 !important;
    }}
    {_css_sel(expire_zone_labels, " input")} {{
        color: #B91C1C !important;
    }}
    """)

if css_parts:
    st.markdown(f"<style>{''.join(css_parts)}</style>", unsafe_allow_html=True)

###############################################################################
# 저장
###############################################################################
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="section-label">저장</div>', unsafe_allow_html=True)

col_save, col_back2, _ = st.columns([1.4, 1.2, 5])

with col_save:
    if st.button("소진계획 전체 저장", type="primary", use_container_width=True):
        save_rows = []
        for (mat_code, batch), month_vals in plan_inputs.items():
            mask = major_df["자재코드"].astype(str) == mat_code
            if "배치" in major_df.columns and batch:
                mask &= major_df["배치"].astype(str) == batch
            row_data = major_df[mask]
            if row_data.empty:
                continue
            row_info = row_data.iloc[0]
            entry = {
                "자재코드": mat_code,
                "자재내역": str(row_info.get("자재내역", "")),
                "배치": batch,
                "유효기한": str(row_info.get("유효기한", "")),
                "기말수량": row_info.get("기말수량", ""),
                "기말금액": row_info.get("기말금액", ""),
                "비고": month_vals.pop("__note__", ""),
            }
            for mlabel in month_labels:
                entry[mlabel] = month_vals.get(mlabel, 0)
            save_rows.append(entry)

        plan_df = pd.DataFrame(save_rows)
        os.makedirs(target_dir, exist_ok=True)
        plan_df.to_csv(plan_csv_path, index=False, encoding="utf-8-sig")
        st.success(f"저장 완료  →  {plan_csv_path}")

        csv_bytes = plan_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv_bytes, "소진계획.csv", "text/csv",
                           use_container_width=True)

with col_back2:
    if st.button("Aging Stock 으로", use_container_width=True):
        st.switch_page("pages/7_Aging_Stock.py")
