import streamlit as st
import pandas as pd
import numpy as np
import io

# ======================================================
# Page
# ======================================================
st.set_page_config(page_title="S&OP System - 재고 시뮬레이션", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #EEF2F7; }
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; padding-left: 2rem; padding-right: 2rem; max-width: 100%; }
[data-testid="stSidebar"] { background: #0B1E3F !important; border-right: none; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebarNav"] { padding: 0.5rem; }
[data-testid="stSidebarNav"] a { border-radius: 8px; padding: 0.55rem 0.9rem !important; margin-bottom: 2px; font-size: 0.875rem; font-weight: 500; color: #94A3B8 !important; display: block; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.08) !important; color: #E2E8F0 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(37,99,235,0.3) !important; color: #FFFFFF !important; font-weight: 600; border-left: 3px solid #3B82F6; }
[data-testid="stSidebarNav"] span { color: inherit !important; }
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.9rem 1.1rem; box-shadow: 0 1px 3px rgba(15,23,42,0.04); }
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 800 !important; color: #0F172A !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; font-weight: 600 !important; color: #64748B !important; }
.stButton > button { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 600; font-size: 0.875rem; padding: 0.5rem 1.1rem; transition: background 0.15s; }
.stButton > button:hover { background-color: #1D4ED8; }
[data-testid="stSelectbox"] > div > div { border-radius: 8px; border-color: #CBD5E1; font-size: 0.875rem; }
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: transparent; border-bottom: 2px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] { height: 40px; background: #F8FAFC; border-radius: 8px 8px 0 0; color: #64748B; font-weight: 600; font-size: 0.85rem; padding: 8px 16px; border: 1px solid #E2E8F0; border-bottom: none; }
.stTabs [aria-selected="true"] { background: #FFFFFF !important; color: #2563EB !important; border-bottom: 2px solid #2563EB !important; }
hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.2rem 0; }
h1 { font-size: 1.5rem !important; font-weight: 700 !important; color: #1E293B !important; margin-bottom: 0.3rem !important; }
h2 { font-size: 1.2rem !important; font-weight: 700 !important; color: #1E293B !important; }
h3 { font-size: 1rem !important; font-weight: 700 !important; color: #374151 !important; }
</style>""", unsafe_allow_html=True)

st.title("🧪 재고 시뮬레이션 - 분류/원가율/평판 매핑(자재코드 기준)")

# ======================================================
# 0) 세션 데이터 확인
# ======================================================
dfs_all = st.session_state.get("dfs", {})
if not dfs_all:
    st.warning("먼저 [📥 데이터 업로드] 페이지에서 파일을 업로드하고 로드해주세요.")
    st.stop()

# ======================================================
# 1) 연도 / 월 선택
# ======================================================
years = sorted(dfs_all.keys())
sel_year = st.selectbox("📅 연도 선택", years, index=len(years) - 1)

months = sorted(
    dfs_all[sel_year].keys(),
    key=lambda x: int(str(x).replace("월", "")) if "월" in str(x) else 0
)
sel_month = st.selectbox("📆 월 선택", months, index=len(months) - 1)

files_dict = dfs_all[sel_year][sel_month]
st.info(f"📍 선택 기준: **{sel_year} {sel_month}**")

# ======================================================
# 2) 파일명 고정
# ======================================================
INV_FILE = "12월 기말 재고_Data.xlsx"
CLS_FILE = "기준정보_분류 및 원가율.xlsx"
RATING_FILE = "기준정보_평판 기준.xlsx"
CANCEL_FILE = "12월 말 제조사 수주 취소 현황_코스맥스 취소.xlsx"

required_files = [INV_FILE, CLS_FILE, RATING_FILE, CANCEL_FILE]
missing = [f for f in required_files if f not in files_dict]
if missing:
    st.error(f"❌ 필수 파일이 없습니다: {missing}")
    st.write("현재 파일 목록:", list(files_dict.keys()))
    st.stop()

# ======================================================
# Utils
# ======================================================
def pick_df(obj):
    """session_state에서 sheet dict로 들어온 경우 첫 df 뽑기"""
    if isinstance(obj, dict):
        return obj[list(obj.keys())[0]]
    return obj

def normalize_code_to_int_string(s: pd.Series) -> pd.Series:
    """
    숫자/문자/9310288.0/공백/쉼표 섞여 있어도
    '정수 문자열'로 통일하여 매핑 안정화
    """
    x = s.astype(str).str.strip().str.replace(",", "", regex=False)
    num = pd.to_numeric(x, errors="coerce")

    out = x.copy()
    mask = num.notna()
    out.loc[mask] = num.loc[mask].round(0).astype("Int64").astype(str)
    out = out.replace({"nan": "", "<NA>": ""})
    return out

def pick_col(df: pd.DataFrame, candidates):
    return next((c for c in candidates if c in df.columns), None)

def download_excel_openpyxl(df: pd.DataFrame, filename: str, sheet_name: str = "Report"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    st.download_button(
        label="📥 엑셀 다운로드",
        data=buffer,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================================================
# 3) Mapping (자사 기말재고) - 통합 버전
# ======================================================
def build_mapped_inventory_df(
    inv_df: pd.DataFrame,
    cls_df: pd.DataFrame,
    rating_df: pd.DataFrame,
    *,
    inv_code_col="자재",
    cls_code_col="자재코드",
    rating_code_col="자재",
    remove_keywords_regex="용역비|배송비",
    inv_item_candidates=("자재 내역", "자재내역", "자재명", "자재 명"),
    drop_inv_cols=("평가 유형", "플랜트", "저장위치", "특별재고"),
    cls_take_cols=("대분류", "소분류", "원가율"),
    # ✅ 어떤 평판을 사용할지: "평판" or "평판 * 1.38배"
    rating_mode: str = "both",   # "both" / "plain" / "x138"
    dedup_by_material: bool = False,  # 자재 중복 시 수량/금액 합쳐 1행
    set_expiry_2099_when_rating_zero: bool = True,
) -> pd.DataFrame:
    inv = inv_df.copy()
    cls = cls_df.copy()
    rating = rating_df.copy()

    # 1) 용역비/배송비 제거
    inv_item_col = next((c for c in inv_item_candidates if c in inv.columns), None)
    if inv_item_col is not None:
        inv = inv[~inv[inv_item_col].astype(str).str.contains(remove_keywords_regex, na=False)].copy()

    # 2) 불필요 컬럼 drop
    inv = inv.drop(columns=[c for c in drop_inv_cols if c in inv.columns], errors="ignore")

    # 3) 필수 컬럼 체크
    for need_col, df_name, df_obj in [
        (inv_code_col, "기말재고", inv),
        (cls_code_col, "기준정보", cls),
        (rating_code_col, "평판기준", rating),
    ]:
        if need_col not in df_obj.columns:
            raise ValueError(f"필수 컬럼 누락: [{df_name}]에 '{need_col}' 컬럼이 없습니다.")

    # 4) 키 정규화
    inv["_mat_key"] = normalize_code_to_int_string(inv[inv_code_col])
    cls["_mat_key"] = normalize_code_to_int_string(cls[cls_code_col])
    rating["_mat_key"] = normalize_code_to_int_string(rating[rating_code_col])

    # 5) 기준정보 매핑 테이블
    for col in cls_take_cols:
        if col not in cls.columns:
            raise ValueError(f"기준정보 파일에 '{col}' 컬럼이 없습니다.")
    cls_small = (
        cls[["_mat_key"] + list(cls_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    # 6) 평판 매핑 테이블 (mode별)
    if rating_mode == "both":
        rating_take_cols = ("평판", "평판 * 1.38배")
    elif rating_mode == "plain":
        rating_take_cols = ("평판",)
    elif rating_mode == "x138":
        rating_take_cols = ("평판 * 1.38배",)
    else:
        raise ValueError("rating_mode는 'both'/'plain'/'x138' 중 하나여야 합니다.")

    for col in rating_take_cols:
        if col not in rating.columns:
            raise ValueError(f"평판 기준 파일에 '{col}' 컬럼이 없습니다.")
    rating_small = (
        rating[["_mat_key"] + list(rating_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    # 7) merge
    out = inv.merge(cls_small, on="_mat_key", how="left")
    out = out.merge(rating_small, on="_mat_key", how="left")

    # 8) 결측 처리
    out["대분류"] = out.get("대분류", "미분류").fillna("미분류")
    out["소분류"] = out.get("소분류", "미분류").fillna("미분류")

    # 9) 자재 중복 처리(옵션)
    qty_candidates = ["기말 재고 수량", "기말수량", "재고수량", "Stock Quantity on Period End"]
    amt_candidates = ["기말 재고 금액", "기말금액", "재고금액", "Stock Amount on Period End"]
    qty_col = pick_col(out, qty_candidates)
    amt_col = pick_col(out, amt_candidates)
    if qty_col is None or amt_col is None:
        raise ValueError(f"수량/금액 컬럼을 찾지 못했습니다. qty={qty_col}, amt={amt_col}")

    out[qty_col] = pd.to_numeric(out[qty_col], errors="coerce").fillna(0.0)
    out[amt_col] = pd.to_numeric(out[amt_col], errors="coerce").fillna(0.0)

    if dedup_by_material:
        group_key = inv_code_col if inv_code_col in out.columns else "_mat_key"
        agg_map = {qty_col: "sum", amt_col: "sum"}
        for c in out.columns:
            if c not in agg_map and c != group_key:
                agg_map[c] = "first"
        out = out.groupby(group_key, as_index=False).agg(agg_map)

    # 10) 평판 숫자화 + (평판0이면 유효기한 2099 세팅 옵션)
    expiry_candidates = ["유효 기한", "유효기간", "유통기한"]
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)

    for col in ["평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    if set_expiry_2099_when_rating_zero and expiry_col is not None:
        # 기준: plain일 때는 평판, x138일 때는 평판*1.38배
        if rating_mode == "x138":
            base_rating_col = "평판 * 1.38배"
        else:
            base_rating_col = "평판" if "평판" in out.columns else None

        if base_rating_col:
            mask_zero = out[base_rating_col].fillna(0).eq(0)
            out.loc[mask_zero, expiry_col] = pd.Timestamp("2099-12-31")

    # 11) 파생 컬럼 계산
    qty_num = out[qty_col]
    amt_num = out[amt_col]

    out["단가"] = amt_num / qty_num.replace({0: pd.NA})

    # 출하원가 기준: plain이면 평판, x138이면 평판*1.38배, both면 평판(기존 로직 유지)
    if rating_mode == "x138":
        sales_col = "평판 * 1.38배"
    else:
        sales_col = "평판" if "평판" in out.columns else None

    out["출하원가"] = pd.to_numeric(out["단가"], errors="coerce") * pd.to_numeric(out.get(sales_col, 0), errors="coerce")

    out["원가율"] = pd.to_numeric(out.get("원가율"), errors="coerce")
    out["출하판가"] = out["출하원가"] / out["원가율"].replace({0: pd.NA})
    out["판가"] = amt_num / out["원가율"].replace({0: pd.NA})

    out["who"] = "자사"
    return out

# ======================================================
# 4) Mapping (제조사 취소PO) - 통합 버전
# ======================================================
def build_mapped_cancel_po_df(
    cancel_df: pd.DataFrame,
    cls_df: pd.DataFrame,
    rating_df: pd.DataFrame,
    *,
    prod_code_candidates=("제품코드", "제품 코드", "자재", "자재코드"),
    prod_name_candidates=("제품명", "품명", "자재 내역", "자재명"),
    qty_candidates=("잔여 PO", "잔여PO", "잔여_PO", "수량", "잔여수량"),
    amt_candidates=("금액", "재고금액", "취소금액", "잔여금액"),
    cls_code_col="자재코드",
    rating_code_col="자재",
    cls_take_cols=("대분류", "소분류", "원가율"),
    rating_mode="plain",    # "plain" / "x138" / "both"
    remove_keywords_regex="용역비|배송비",
    dedup_by_material=True, # 제조사는 보통 자재당 1행 유지하고 싶어서 default True
    expiry_default=pd.Timestamp("2028-12-31"),
) -> pd.DataFrame:
    base = cancel_df.copy()
    cls = cls_df.copy()
    rating = rating_df.copy()

    code_col = pick_col(base, prod_code_candidates)
    name_col = pick_col(base, prod_name_candidates)
    qty_col  = pick_col(base, qty_candidates)
    amt_col  = pick_col(base, amt_candidates)

    missing = [("제품코드", code_col), ("제품명", name_col), ("잔여PO", qty_col), ("금액", amt_col)]
    missing = [label for label, col in missing if col is None]
    if missing:
        raise ValueError(f"[취소현황] 필수 컬럼을 찾지 못했습니다: {missing}\n현재 컬럼: {list(base.columns)}")

    # 용역비/배송비 제거
    base = base[~base[name_col].astype(str).str.contains(remove_keywords_regex, na=False)].copy()

    out = pd.DataFrame({
        "자재": base[code_col],
        "자재 내역": base[name_col],
        "기말 재고 수량": pd.to_numeric(base[qty_col], errors="coerce").fillna(0.0),
        "기말 재고 금액": pd.to_numeric(base[amt_col], errors="coerce").fillna(0.0),
    })

    # 키 정규화
    out["_mat_key"] = normalize_code_to_int_string(out["자재"])
    cls["_mat_key"] = normalize_code_to_int_string(cls[cls_code_col])
    rating["_mat_key"] = normalize_code_to_int_string(rating[rating_code_col])

    # 기준정보
    cls_small = (
        cls[["_mat_key"] + list(cls_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates("_mat_key")
    )

    # 평판 mode
    if rating_mode == "both":
        rating_take_cols = ("평판", "평판 * 1.38배")
    elif rating_mode == "plain":
        rating_take_cols = ("평판",)
    elif rating_mode == "x138":
        rating_take_cols = ("평판 * 1.38배",)
    else:
        raise ValueError("rating_mode는 'both'/'plain'/'x138' 중 하나여야 합니다.")

    rating_small = (
        rating[["_mat_key"] + list(rating_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates("_mat_key")
    )

    out = out.merge(cls_small, on="_mat_key", how="left")
    out = out.merge(rating_small, on="_mat_key", how="left")

    out["대분류"] = out.get("대분류", "미분류").fillna("미분류")
    out["소분류"] = out.get("소분류", "미분류").fillna("미분류")
    out["원가율"] = pd.to_numeric(out.get("원가율"), errors="coerce").fillna(0.0)

    for col in ["평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    # 자재 중복이면 수량/금액 sum, 나머지 first
    if dedup_by_material:
        agg_map = {"기말 재고 수량": "sum", "기말 재고 금액": "sum"}
        for c in out.columns:
            if c not in agg_map and c not in ["자재", "_mat_key"]:
                agg_map[c] = "first"
        out = out.groupby("자재", as_index=False).agg(agg_map)

    # 파생
    out["단가"] = out["기말 재고 금액"] / out["기말 재고 수량"].replace({0: pd.NA})

    sales_col = "평판 * 1.38배" if rating_mode == "x138" else ("평판" if "평판" in out.columns else None)
    out["출하원가"] = pd.to_numeric(out["단가"], errors="coerce") * pd.to_numeric(out.get(sales_col, 0), errors="coerce")
    out["출하판가"] = out["출하원가"] / out["원가율"].replace({0: pd.NA})
    out["판가"] = out["기말 재고 금액"] / out["원가율"].replace({0: pd.NA})

    out["유효기간"] = expiry_default
    out["who"] = "제조사"
    return out

# ======================================================
# 5) 대분류 소계 포함 리포트 (원가/판가만)
# ======================================================
def build_major_only_report_table(
    df_self: pd.DataFrame,
    df_manu: pd.DataFrame,
    *,
    major_col="대분류",
    sub_col="소분류",
    cost_col="기말 재고 금액",
    price_col="판가",
    self_name="자사",
    manu_name="제조사",
    include_total=True,
    include_major_subtotal=True,
):
    s = df_self.copy()
    m = df_manu.copy()

    for d in [s, m]:
        if major_col not in d.columns: d[major_col] = "미분류"
        if sub_col not in d.columns:   d[sub_col] = "미분류"

    s["_who"] = self_name
    m["_who"] = manu_name

    s["_cost"] = pd.to_numeric(s.get(cost_col), errors="coerce").fillna(0.0)
    m["_cost"] = pd.to_numeric(m.get(cost_col), errors="coerce").fillna(0.0)
    s["_price"] = pd.to_numeric(s.get(price_col), errors="coerce").fillna(0.0)
    m["_price"] = pd.to_numeric(m.get(price_col), errors="coerce").fillna(0.0)

    base = pd.concat([s[[major_col, sub_col, "_who", "_cost", "_price"]],
                      m[[major_col, sub_col, "_who", "_cost", "_price"]]], ignore_index=True)

    piv = base.pivot_table(
        index=[major_col, sub_col],
        columns="_who",
        values=["_cost", "_price"],
        aggfunc="sum",
        fill_value=0.0
    )

    def col_name(measure, who):
        return f"{who} 원가" if measure == "_cost" else f"{who} 판가"

    piv.columns = [col_name(measure, who) for (measure, who) in piv.columns]
    piv = piv.reset_index()

    # 보정
    for c in [f"{self_name} 원가", f"{self_name} 판가", f"{manu_name} 원가", f"{manu_name} 판가"]:
        if c not in piv.columns:
            piv[c] = 0.0

    piv["합계 원가"] = piv[f"{self_name} 원가"] + piv[f"{manu_name} 원가"]
    piv["합계 판가"] = piv[f"{self_name} 판가"] + piv[f"{manu_name} 판가"]

    rows = []
    if include_total:
        rows.append(pd.DataFrame([{
            major_col: "총계", sub_col: "",
            f"{self_name} 원가": piv[f"{self_name} 원가"].sum(),
            f"{self_name} 판가": piv[f"{self_name} 판가"].sum(),
            f"{manu_name} 원가": piv[f"{manu_name} 원가"].sum(),
            f"{manu_name} 판가": piv[f"{manu_name} 판가"].sum(),
            "합계 원가": piv["합계 원가"].sum(),
            "합계 판가": piv["합계 판가"].sum(),
        }]))

    for maj, maj_df in piv.groupby(major_col, sort=False):
        if include_major_subtotal:
            rows.append(pd.DataFrame([{
                major_col: maj, sub_col: "소계",
                f"{self_name} 원가": maj_df[f"{self_name} 원가"].sum(),
                f"{self_name} 판가": maj_df[f"{self_name} 판가"].sum(),
                f"{manu_name} 원가": maj_df[f"{manu_name} 원가"].sum(),
                f"{manu_name} 판가": maj_df[f"{manu_name} 판가"].sum(),
                "합계 원가": maj_df["합계 원가"].sum(),
                "합계 판가": maj_df["합계 판가"].sum(),
            }]))
        rows.append(maj_df)

    final = pd.concat(rows, ignore_index=True)

    # 상세행에서 대분류 공백 처리
    mask_detail = (final[major_col] != "총계") & (final[sub_col] != "소계")
    final.loc[mask_detail, major_col] = ""

    return final[[major_col, sub_col,
                  f"{self_name} 원가", f"{self_name} 판가",
                  f"{manu_name} 원가", f"{manu_name} 판가",
                  "합계 원가", "합계 판가"]]

# ======================================================
# 6) 재고 소진 시뮬레이션 (시즌코드 5~8월만 판매)
# ======================================================
# def simulate_monthly_remaining_amount(
#     df: pd.DataFrame,
#     start_ym=(2026, 1),
#     end_ym=(2028, 12),
#     amount_col="기말 재고 금액",
#     burn_col="출하원가",
#     expiry_candidates=("유효기간", "유효 기한", "유통기한"),
#     mat_col_candidates=("자재", "자재코드", "자재 코드"),
#     season_mat_codes=None,
#     season_months=(5, 6, 7, 8),
#     col_fmt=lambda y, m: f"{str(y)[-2:]}_{m}"
# ):
#     out = df.copy()

#     mat_col = next((c for c in mat_col_candidates if c in out.columns), None)
#     season_set = set(str(x).strip() for x in (season_mat_codes or []))
#     is_season_item = out[mat_col].astype(str).str.strip().isin(season_set) if mat_col else pd.Series(False, index=out.index)

#     expiry_col = next((c for c in expiry_candidates if c in out.columns), None)
#     if expiry_col is None:
#         # 유효기간 없으면 월 컬럼만 생성
#         y, m = start_ym
#         ey, em = end_ym
#         while (y < ey) or (y == ey and m <= em):
#             out[col_fmt(y, m)] = 0.0
#             m += 1
#             if m == 13: y, m = y + 1, 1
#         return out

#     exp_dt = pd.to_datetime(out[expiry_col].astype(str).str.strip(), errors="coerce")
#     has_expiry = exp_dt.notna()

#     cutoff_dt = exp_dt - pd.DateOffset(months=6)
#     cut_y = cutoff_dt.dt.year
#     cut_m = cutoff_dt.dt.month

#     remaining = pd.to_numeric(out.get(amount_col), errors="coerce").fillna(0.0)
#     burn = pd.to_numeric(out.get(burn_col), errors="coerce").fillna(0.0)

#     # 월 리스트
#     months = []
#     y, m = start_ym
#     ey, em = end_ym
#     while (y < ey) or (y == ey and m <= em):
#         months.append((y, m))
#         m += 1
#         if m == 13: y, m = y + 1, 1

#     for (y, m) in months:
#         col_name = col_fmt(y, m)
#         out[col_name] = 0.0

#         can_sell_by_cutoff = has_expiry & ((y < cut_y) | ((y == cut_y) & (m <= cut_m)))

#         season_allowed = pd.Series(True, index=out.index) if (m in season_months) else pd.Series(False, index=out.index)
#         season_filter = (~is_season_item) | (is_season_item & season_allowed)

#         can_sell = can_sell_by_cutoff & season_filter

#         remaining = remaining.where(~can_sell, (remaining - burn).clip(lower=0))
#         out.loc[has_expiry, col_name] = remaining.loc[has_expiry]

#     return out

def add_obsolete_cols_at_cutoff_6m(
    df: pd.DataFrame,
    *,
    expiry_candidates=("유효기간", "유효 기한", "유통기한"),
    col_fmt=lambda y, m: f"{str(y)[-2:]}_{m}",
    amount_col="기말 재고 금액",
    burn_col="출하원가",
) -> pd.DataFrame:
    out = df.copy()
    out["부진재고량"] = 0.0
    out["부진재고진입시점"] = 0
    out["부진재고진입분기"] = 0
    out["회전월"] = 0.0

    amt = pd.to_numeric(out.get(amount_col), errors="coerce")
    burn = pd.to_numeric(out.get(burn_col), errors="coerce")
    mask_turn = burn.notna() & (burn != 0) & amt.notna()
    out.loc[mask_turn, "회전월"] = amt.loc[mask_turn] / burn.loc[mask_turn]

    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)
    if expiry_col is None:
        return out

    exp_dt = pd.to_datetime(out[expiry_col], errors="coerce")
    has_expiry = exp_dt.notna()
    if not has_expiry.any():
        return out

    cutoff_dt = exp_dt - pd.DateOffset(months=6)
    cut_y = cutoff_dt.dt.year
    cut_m = cutoff_dt.dt.month

    for idx in out.index:
        if not has_expiry.loc[idx]:
            continue
        y = int(cut_y.loc[idx]); m = int(cut_m.loc[idx])
        cut_col = col_fmt(y, m)
        if cut_col not in out.columns:
            continue

        val = pd.to_numeric(out.at[idx, cut_col], errors="coerce")
        if pd.isna(val):
            continue

        out.at[idx, "부진재고량"] = float(val)

        if float(val) > 0:
            entry_dt = cutoff_dt.loc[idx]
            out.at[idx, "부진재고진입시점"] = entry_dt
            q = (entry_dt.month - 1) // 3 + 1
            yy = str(entry_dt.year)[-2:]
            out.at[idx, "부진재고진입분기"] = f"{yy}년 {q}Q"

    return out

def simulate_monthly_remaining_amount_fefo(
    df: pd.DataFrame,
    start_ym=(2026, 1),
    end_ym=(2028, 12),
    *,
    mat_col="자재",
    batch_col="배치",
    expiry_candidates=("유효기간", "유효 기한", "유통기한"),
    amount_col="기말 재고 금액",
    burn_col="출하원가",   # "월에 소진되는 금액" (단가*평판)
    season_mat_codes=None,
    season_months=(5, 6, 7, 8),
    col_fmt=lambda y, m: f"{str(y)[-2:]}_{m}",
):
    out = df.copy()

    # ---- 컬럼 확인 ----
    if mat_col not in out.columns:
        raise KeyError(f"'{mat_col}' 컬럼이 필요합니다.")
    if batch_col not in out.columns:
        raise KeyError(f"FEFO를 하려면 '{batch_col}'(배치) 컬럼이 필요합니다.")
    exp_col = next((c for c in expiry_candidates if c in out.columns), None)
    if exp_col is None:
        raise KeyError(f"유효기간 컬럼이 없습니다. 후보={expiry_candidates}")

    # ---- 타입 정리 ----
    out[amount_col] = pd.to_numeric(out.get(amount_col), errors="coerce").fillna(0.0)
    out[burn_col]   = pd.to_numeric(out.get(burn_col), errors="coerce").fillna(0.0)
    out["_exp_dt"]  = pd.to_datetime(out[exp_col].astype(str).str.strip(), errors="coerce")
    out["_has_exp"] = out["_exp_dt"].notna()

    # cutoff (D-6개월) : 이 시점(월)까지는 판매 가능, 이후는 판매 불가로 간주
    out["_cutoff_dt"] = out["_exp_dt"] - pd.DateOffset(months=6)
    out["_cut_y"] = out["_cutoff_dt"].dt.year
    out["_cut_m"] = out["_cutoff_dt"].dt.month

    # 시즌 아이템 플래그
    season_set = set(str(x).strip() for x in (season_mat_codes or []))
    out["_is_season"] = out[mat_col].astype(str).str.strip().isin(season_set)

    # 월 리스트
    months = []
    y, m = start_ym
    ey, em = end_ym
    while (y < ey) or (y == ey and m <= em):
        months.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1

    # 월 컬럼 생성 (배치별 잔액)
    for (yy, mm) in months:
        out[col_fmt(yy, mm)] = 0.0

    # ---- FEFO: 자재별로 배치를 유효기간 오름차순 정렬해서, 월 burn를 앞 배치부터 소진 ----
    # 상태: 각 행(배치)의 remaining_amount를 들고 감
    remaining = out[amount_col].to_numpy().copy()

    # 자재별 인덱스 묶기
    # FEFO 순서: exp_dt 오름차순 (NaT는 뒤로)
    grouped = (
        out.reset_index()
           .sort_values(by=[mat_col, "_has_exp", "_exp_dt"], ascending=[True, False, True])
           .groupby(mat_col)["index"]
           .apply(list)
           .to_dict()
    )

    for (yy, mm) in months:
        col = col_fmt(yy, mm)

        # 월별로 "판매 가능한 배치"만 대상으로 burn를 적용
        # 판매 가능 조건:
        # 1) 유효기간 있음
        # 2) (현재 월) <= cutoff 월  (D-6개월까지 판매로 간주)
        # 3) 시즌코드면 5~8월만 판매
        season_allowed = (mm in season_months)

        for mat, idx_list in grouped.items():
            # 이 자재의 월 burn (평판 기반): 자재 단위로 1번만 적용해야 함
            # - 그런데 df가 배치단위라 burn_col 값이 배치별로 중복될 수 있음
            #   → "첫 배치의 burn"을 자재 burn로 사용 (너 로직상 평판은 자재 고유값이니까)
            #   → 더 안전하게 하려면 자재별 burn을 별도로 만든 뒤 merge하는 게 베스트
            mat_burn = float(out.loc[idx_list[0], burn_col]) if len(idx_list) else 0.0
            if mat_burn <= 0:
                continue

            # 시즌이면 시즌월 아니면 판매 불가
            # (이 자재가 시즌인지 여부는 아무 배치나 동일하다고 가정)
            is_season_item = bool(out.loc[idx_list[0], "_is_season"])
            if is_season_item and (not season_allowed):
                continue

            # 자재별 burn를 FEFO로 분배
            burn_left = mat_burn

            for i in idx_list:
                # 유효기간 없는 배치는 판매 불가로 치고 스킵
                if not bool(out.at[i, "_has_exp"]):
                    continue

                # cutoff 이후면 판매 불가
                cy = out.at[i, "_cut_y"]; cm = out.at[i, "_cut_m"]
                if pd.isna(cy) or pd.isna(cm):
                    continue
                cy = int(cy); cm = int(cm)
                if (yy > cy) or (yy == cy and mm > cm):
                    continue

                if burn_left <= 0:
                    break

                # 이 배치에서 소진
                use = min(remaining[i], burn_left)
                remaining[i] -= use
                burn_left -= use

                if burn_left <= 0:
                    break

        # 월말 잔액 기록(유효기간 있는 배치에만 기록)
        out.loc[out["_has_exp"], col] = remaining[out["_has_exp"].to_numpy()]

    # 정리 컬럼 제거는 선택 (필요하면 삭제)
    out = out.drop(columns=["_exp_dt","_has_exp","_cutoff_dt","_cut_y","_cut_m","_is_season"], errors="ignore")
    return out


# ======================================================
# 7) 분기 집계표 (카테고리별 + KPI + 분기 잔액)
#    - "자재 단위 재집계"로 출하원가/출하판가 중복 문제 방지
# ======================================================
def make_quarter_cols(start_year: int, end_year: int):
    cols = []
    for y in range(start_year, end_year + 1):
        yy = str(y)[-2:]
        for q in [1,2,3,4]:
            cols.append(f"{yy}년 {q}Q")
    return cols

def build_category_quarter_table(
    df: pd.DataFrame,
    *,
    cat_cols=("대분류", "소분류"),
    value_col="부진재고량",
    quarter_col="부진재고진입분기",
    start_year=2026,
    end_year=2028,
    cost_col="기말 재고 금액",
    qty_col="기말 재고 수량",
    sales_col="평판",
    sales_fallback_cols=("평판 * 1.38배", "평판"),
    cost_rate_col="원가율",
    ship_cost_col="출하원가",
    ship_price_col="출하판가",
    mat_col="자재",
):
    base = df.copy()
    quarter_cols = make_quarter_cols(start_year, end_year)

    if quarter_col not in base.columns:
        raise KeyError(f"'{quarter_col}' 컬럼 없음. columns={list(base.columns)}")

    base["_분기"] = base[quarter_col].where(base[quarter_col].isin(quarter_cols), pd.NA)

    # Pivot: 분기별 부진재고량
    for c in [*cat_cols, value_col]:
        if c not in base.columns:
            raise KeyError(f"'{c}' 컬럼 없음. columns={list(base.columns)}")

    pivot_detail = (
        base.dropna(subset=["_분기"])
        .pivot_table(index=list(cat_cols), columns="_분기", values=value_col, aggfunc="sum", fill_value=0.0)
        .reindex(columns=quarter_cols, fill_value=0.0)
    )
    pivot_detail["합계"] = pivot_detail.sum(axis=1)
    pivot_detail = pivot_detail.reset_index()

    # sales_col fallback
    if sales_col not in base.columns:
        found = next((c for c in sales_fallback_cols if c in base.columns), None)
        if found is None:
            hint = [c for c in base.columns if "평판" in str(c)]
            raise KeyError(f"sales_col='{sales_col}'도 없고 fallback도 없음. 후보={hint}")
        sales_col = found

    # 자재 단위 재집계
    for c in [mat_col, *cat_cols, cost_col, qty_col, sales_col, cost_rate_col]:
        if c not in base.columns:
            raise KeyError(f"'{c}' 컬럼 없음. columns={list(base.columns)}")

    tmp = base.copy()
    tmp[cost_col] = pd.to_numeric(tmp[cost_col], errors="coerce").fillna(0.0)
    tmp[qty_col] = pd.to_numeric(tmp[qty_col], errors="coerce").fillna(0.0)
    tmp[sales_col] = pd.to_numeric(tmp[sales_col], errors="coerce").fillna(0.0)
    tmp[cost_rate_col] = pd.to_numeric(tmp[cost_rate_col], errors="coerce").fillna(0.0)

    mat_agg = (
        tmp.groupby(mat_col, dropna=False)
        .agg(
            **{
                cat_cols[0]: (cat_cols[0], "first"),
                cat_cols[1]: (cat_cols[1], "first"),
                cost_col: (cost_col, "sum"),
                qty_col: (qty_col, "sum"),
                sales_col: (sales_col, "first"),
                cost_rate_col: (cost_rate_col, "first"),
            }
        )
        .reset_index()
    )

    mat_agg["_원가단가"] = 0.0
    m_qty = mat_agg[qty_col] != 0
    mat_agg.loc[m_qty, "_원가단가"] = mat_agg.loc[m_qty, cost_col] / mat_agg.loc[m_qty, qty_col]

    mat_agg[ship_cost_col] = mat_agg["_원가단가"] * mat_agg[sales_col]

    mat_agg[ship_price_col] = 0.0
    m_rate = mat_agg[cost_rate_col] != 0
    mat_agg.loc[m_rate, ship_price_col] = mat_agg.loc[m_rate, ship_cost_col] / mat_agg.loc[m_rate, cost_rate_col]

    # 카테고리 KPI
    kpi = (
        mat_agg.groupby(list(cat_cols), dropna=False)
        .agg(
            원가=(cost_col, "sum"),
            출하원가=(ship_cost_col, "sum"),
            출하판가=(ship_price_col, "sum"),
        )
        .reset_index()
    )

    kpi["회전월"] = 0.0
    m_ship = kpi["출하원가"] != 0
    kpi.loc[m_ship, "회전월"] = kpi.loc[m_ship, "원가"] / kpi.loc[m_ship, "출하원가"]

    detail = kpi.merge(pivot_detail, on=list(cat_cols), how="left").fillna(0.0)

    # 대분류 소계
    major_kpi = (
        mat_agg.groupby(cat_cols[0], dropna=False)
        .agg(
            원가=(cost_col, "sum"),
            출하원가=(ship_cost_col, "sum"),
            출하판가=(ship_price_col, "sum"),
        )
        .reset_index()
    )
    major_kpi["회전월"] = 0.0
    m2 = major_kpi["출하원가"] != 0
    major_kpi.loc[m2, "회전월"] = major_kpi.loc[m2, "원가"] / major_kpi.loc[m2, "출하원가"]

    major_q = (
        base.dropna(subset=["_분기"])
        .groupby([cat_cols[0], "_분기"])[value_col]
        .sum()
        .unstack("_분기")
        .reindex(columns=quarter_cols, fill_value=0.0)
        .reset_index()
    )
    major_q["합계"] = major_q[quarter_cols].sum(axis=1)

    major_tbl = major_kpi.merge(major_q, on=cat_cols[0], how="left").fillna(0.0)
    major_tbl[cat_cols[1]] = "소계"

    # 총계
    total_cost = mat_agg[cost_col].sum()
    total_ship_cost = mat_agg[ship_cost_col].sum()
    total = pd.DataFrame([{
        cat_cols[0]: "총계",
        cat_cols[1]: "",
        "원가": total_cost,
        "출하원가": total_ship_cost,
        "출하판가": mat_agg[ship_price_col].sum(),
        "회전월": (total_cost / total_ship_cost if total_ship_cost != 0 else 0),
        **{q: base.loc[base["_분기"] == q, value_col].sum() for q in quarter_cols},
        "합계": base[value_col].sum()
    }])

    rows = [total]
    for d in major_tbl[cat_cols[0]].unique():
        rows.append(major_tbl[major_tbl[cat_cols[0]] == d])
        rows.append(detail[detail[cat_cols[0]] == d])

    final = pd.concat(rows, ignore_index=True)
    final = final[[*cat_cols, "원가", "출하원가", "출하판가", "회전월", "합계", *quarter_cols]]

    # 상세행에서 대분류 공백 처리
    major_name, sub_name = cat_cols[0], cat_cols[1]
    mask_detail = (final[major_name] != "총계") & (final[sub_name] != "소계")
    final.loc[mask_detail, major_name] = ""

    return final

# ======================================================
# 8) cat_table 붙이기(최종 보고서 merged)
# ======================================================
def add_merge_keys(df: pd.DataFrame, major="대분류", sub="소분류") -> pd.DataFrame:
    out = df.copy()
    if "소분" in out.columns and sub not in out.columns:
        out = out.rename(columns={"소분": sub})
    if major not in out.columns or sub not in out.columns:
        raise ValueError(f"'{major}', '{sub}' 컬럼이 필요합니다. 현재 columns={list(out.columns)}")
    out["merge_major"] = out[major].replace("", np.nan).ffill()
    out["merge_sub"] = out[sub].fillna("")
    return out

def attach_cat_table(
    base_df: pd.DataFrame,
    cat_df: pd.DataFrame,
    *,
    prefix: str,
    drop_mode: str = "cost_price_only",   # "cost_price_only" / "cost_price_ship_turn"
    include_ship_cols: bool = True,
    major="대분류",
    sub="소분류",
) -> pd.DataFrame:
    ct = cat_df.copy()

    if drop_mode == "cost_price_ship_turn":
        drop_keywords = ["원가", "판가", "출하", "회전"]
        drop_cols = [c for c in ct.columns if any(k in c for k in drop_keywords)]
    elif drop_mode == "cost_price_only":
        def is_drop_col(c: str) -> bool:
            has_cost_price = ("원가" in c) or ("판가" in c)
            if not has_cost_price:
                return False
            if include_ship_cols:
                is_ship = ("출하" in c)
                return has_cost_price and (not is_ship)
            return True
        drop_cols = [c for c in ct.columns if is_drop_col(c)]
    else:
        raise ValueError("drop_mode는 'cost_price_only' 또는 'cost_price_ship_turn'만 가능합니다.")

    ct = ct.drop(columns=drop_cols, errors="ignore")

    ct = add_merge_keys(ct, major=major, sub=sub)
    value_cols = [c for c in ct.columns if c not in [major, sub, "merge_major", "merge_sub"]]
    ct_small = ct[["merge_major", "merge_sub"] + value_cols].copy()

    rename_map = {c: f"{prefix}_{c}" for c in value_cols}
    ct_small = ct_small.rename(columns=rename_map)
    renamed_cols = [rename_map[c] for c in value_cols]

    if ("merge_major" not in base_df.columns) or ("merge_sub" not in base_df.columns):
        raise ValueError("base_df에 merge_major/merge_sub가 없습니다. (drop하기 전에 붙여야 합니다)")

    tmp = base_df[["merge_major", "merge_sub"]].merge(
        ct_small, on=["merge_major", "merge_sub"], how="left"
    )
    tmp[renamed_cols] = tmp[renamed_cols].fillna(0)

    return pd.concat([base_df, tmp[renamed_cols]], axis=1)

# ======================================================
# 9) Data Load
# ======================================================
inv_df = pick_df(files_dict[INV_FILE]).copy()
cls_df = pick_df(files_dict[CLS_FILE]).copy()
rating_df = pick_df(files_dict[RATING_FILE]).copy()
cancel_df = pick_df(files_dict[CANCEL_FILE]).copy()

# ======================================================
# 10) Run: 자사 매핑 2종(plain / x138) + (옵션) dedup버전
# ======================================================
mapped_self_plain = build_mapped_inventory_df(inv_df, cls_df, rating_df, rating_mode="plain", dedup_by_material=True)
mapped_self_x138  = build_mapped_inventory_df(inv_df, cls_df, rating_df, rating_mode="x138",  dedup_by_material=True)

# 제조사 매핑 2종(plain / x138)
mapped_manu_plain = build_mapped_cancel_po_df(cancel_df, cls_df, rating_df, rating_mode="plain", dedup_by_material=True)
mapped_manu_x138  = build_mapped_cancel_po_df(cancel_df, cls_df, rating_df, rating_mode="x138",  dedup_by_material=True)

st.subheader("✅ 매핑 결과(샘플)")
st.dataframe(mapped_self_plain.head(50), use_container_width=True)
st.dataframe(mapped_manu_plain.head(50), use_container_width=True)

# ======================================================
# 11) 대분류 소계 리포트
# ======================================================
major_report_df = build_major_only_report_table(
    df_self=mapped_self_plain,
    df_manu=mapped_manu_plain,
    major_col="대분류",
    sub_col="소분류",
    self_name="자사",
    manu_name="제조사",
)
st.subheader("📌 대분류 소계 포함 통합 리포트")
st.dataframe(major_report_df, use_container_width=True)

# ======================================================
# 12) 시뮬레이션 준비 (자사+제조사 / plain & x138 / 자사만 / 자사x138만)
# ======================================================
season_codes = [
    "9305997","9307728","9307905","9307906","9308000","9308231",
    "9308427","9310455","9310878","9311190","9311191","9311719"
]

combined_plain = pd.concat([mapped_self_plain, mapped_manu_plain], ignore_index=True, sort=False)
combined_x138  = pd.concat([mapped_self_x138,  mapped_manu_x138],  ignore_index=True, sort=False)

# sim_plain = simulate_monthly_remaining_amount(
#     combined_plain, amount_col="기말 재고 금액", burn_col="출하원가",
#     season_mat_codes=season_codes, season_months=(5,6,7,8),
# )
# sim_plain = add_obsolete_cols_at_cutoff_6m(sim_plain)

# sim_x138 = simulate_monthly_remaining_amount(
#     combined_x138, amount_col="기말 재고 금액", burn_col="출하원가",
#     season_mat_codes=season_codes, season_months=(5,6,7,8),
# )
# sim_x138 = add_obsolete_cols_at_cutoff_6m(sim_x138)

# sim_self_plain = add_obsolete_cols_at_cutoff_6m(
#     simulate_monthly_remaining_amount(mapped_self_plain, season_mat_codes=season_codes, season_months=(5,6,7,8))
# )
# sim_self_x138 = add_obsolete_cols_at_cutoff_6m(
#     simulate_monthly_remaining_amount(mapped_self_x138, season_mat_codes=season_codes, season_months=(5,6,7,8))
# )

sim_plain = simulate_monthly_remaining_amount_fefo(
    combined_plain, amount_col="기말 재고 금액", burn_col="출하원가",
    season_mat_codes=season_codes, season_months=(5,6,7,8),
)

sim_x138 = simulate_monthly_remaining_amount_fefo(
    combined_x138, amount_col="기말 재고 금액", burn_col="출하원가",
    season_mat_codes=season_codes, season_months=(5,6,7,8),
)

sim_self_plain = simulate_monthly_remaining_amount_fefo(
    mapped_self_plain, amount_col="기말 재고 금액", burn_col="출하원가",
    season_mat_codes=season_codes, season_months=(5,6,7,8),
)

sim_self_x138 = simulate_monthly_remaining_amount_fefo(
    mapped_self_x138, amount_col="기말 재고 금액", burn_col="출하원가",
    season_mat_codes=season_codes, season_months=(5,6,7,8),
)
sim_plain = add_obsolete_cols_at_cutoff_6m(sim_plain)
sim_x138  = add_obsolete_cols_at_cutoff_6m(sim_x138)
sim_self_plain = add_obsolete_cols_at_cutoff_6m(sim_self_plain)
sim_self_x138  = add_obsolete_cols_at_cutoff_6m(sim_self_x138)


st.subheader("📌 시뮬레이션 결과(요약)")
st.dataframe(sim_plain.head(30), use_container_width=True)
st.dataframe(sim_x138.head(30), use_container_width=True)

# ======================================================
# 13) 분기 집계표 4종
# ======================================================
cat_table_plain = build_category_quarter_table(sim_plain, sales_col="평판")
cat_table_x138  = build_category_quarter_table(sim_x138,  sales_col="평판 * 1.38배")
cat_table_self_plain = build_category_quarter_table(sim_self_plain, sales_col="평판")
cat_table_self_x138  = build_category_quarter_table(sim_self_x138,  sales_col="평판 * 1.38배")

st.subheader("📊 분기 집계표")
st.dataframe(cat_table_plain, use_container_width=True)
st.dataframe(cat_table_x138, use_container_width=True)

# ======================================================
# 14) major_report_df + cat_table들을 오른쪽에 붙여 최종 보고서 만들기
# ======================================================
mr = add_merge_keys(major_report_df, major="대분류", sub="소분류")

merged = attach_cat_table(
    base_df=mr, cat_df=cat_table_plain,
    prefix="자사+제조사",
    drop_mode="cost_price_only",
    include_ship_cols=True
)

merged = attach_cat_table(
    base_df=merged, cat_df=cat_table_x138,
    prefix="자사+제조사1.38배",
    drop_mode="cost_price_only",
    include_ship_cols=True
)

merged = attach_cat_table(
    base_df=merged, cat_df=cat_table_self_plain,
    prefix="자사",
    drop_mode="cost_price_only",
    include_ship_cols=True
)

merged = attach_cat_table(
    base_df=merged, cat_df=cat_table_self_x138,
    prefix="자사1.38배",
    drop_mode="cost_price_only",
    include_ship_cols=True
)

merged2 = merged.drop(columns=["merge_major", "merge_sub"], errors="ignore")

# 1억 단위 변환(숫자 컬럼만 / 회전 포함 제외)
EOK = 100_000_000
num_cols = merged2.select_dtypes(include="number").columns.tolist()
num_cols = [c for c in num_cols if "회전" not in c]
merged2[num_cols] = merged2[num_cols] / EOK

st.subheader("📌 디엔코스메틱스 보유재고 운영 시뮬레이션 보고")
st.dataframe(merged2, use_container_width=True, height=900)

download_excel_openpyxl(
    merged2,
    filename="디엔코스메틱스 보유재고 운영 시뮬레이션 보고.xlsx",
    sheet_name="MergedReport"
)
