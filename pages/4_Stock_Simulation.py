import streamlit as st
import pandas as pd
import io
import numpy as np

st.set_page_config(page_title="S&OP System - 재고 시뮬레이션", layout="wide")
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

required_files = [INV_FILE, CLS_FILE, RATING_FILE]
missing = [f for f in required_files if f not in files_dict]
if missing:
    st.error(f"❌ 필수 파일이 없습니다: {missing}")
    st.write("현재 파일 목록:", list(files_dict.keys()))
    st.stop()

# ======================================================
# 3) 유틸
# ======================================================
def pick_df(obj):
    if isinstance(obj, dict):
        return obj[list(obj.keys())[0]]
    return obj

def normalize_code_to_int_string(s: pd.Series) -> pd.Series:
    """
    숫자/문자/9310288.0/공백/쉼표 섞여 있어도
    '정수 문자열'로 통일하여 매핑 안정화
    """
    x = s.astype(str).str.strip()
    x = x.str.replace(",", "", regex=False)

    num = pd.to_numeric(x, errors="coerce")

    out = x.copy()
    mask = num.notna()
    out.loc[mask] = num.loc[mask].round(0).astype("Int64").astype(str)

    out = out.replace({"nan": "", "<NA>": ""})
    return out

# ======================================================
# ✅ 파일에서 필요한 컬럼 다 합치기 (매핑)
# ======================================================
def build_mapped_inventory_df(
    inv_df: pd.DataFrame,
    cls_df: pd.DataFrame,
    rating_df: pd.DataFrame,
    *,
    inv_code_col: str = "자재",        # 기말재고
    cls_code_col: str = "자재코드",    # 기준정보_분류/원가율
    rating_code_col: str = "자재",     # 기준정보_평판기준
    remove_keywords_regex: str = "용역비|배송비",
    inv_item_candidates=("자재 내역", "자재내역", "자재명", "자재 명"),
    drop_inv_cols=("평가 유형", "플랜트", "저장위치", "특별재고"),
    cls_take_cols=("대분류", "소분류", "원가율"),
    rating_take_cols=("평판", "평판 * 1.38배"),
) -> pd.DataFrame:
    """
    기말재고(inv_df)에 대해
    - 기준정보(cls_df)에서 대분류/소분류/원가율 매핑
    - 평판기준(rating_df)에서 평판/평판*1.38배 매핑
    을 수행해 최종 DF 반환
    """

    inv = inv_df.copy()
    cls = cls_df.copy()
    rating = rating_df.copy()

    # 1) 즉시 정리: 용역비/배송비 포함 행 제거
    inv_item_col = next((c for c in inv_item_candidates if c in inv.columns), None)
    if inv_item_col is not None:
        inv = inv[~inv[inv_item_col].astype(str).str.contains(remove_keywords_regex, na=False)].copy()

    # 2) 기말재고 불필요 컬럼 제거
    inv = inv.drop(columns=[c for c in drop_inv_cols if c in inv.columns], errors="ignore")

    # 3) 필수 키 컬럼 체크
    for need_col, df_name in [(inv_code_col, "기말재고"), (cls_code_col, "기준정보"), (rating_code_col, "평판기준")]:
        if (df_name == "기말재고" and need_col not in inv.columns) \
           or (df_name == "기준정보" and need_col not in cls.columns) \
           or (df_name == "평판기준" and need_col not in rating.columns):
            raise ValueError(f"필수 컬럼 누락: [{df_name}]에 '{need_col}' 컬럼이 없습니다.")

    # 4) 키 정규화
    inv["_mat_key"] = normalize_code_to_int_string(inv[inv_code_col])
    cls["_mat_key"] = normalize_code_to_int_string(cls[cls_code_col])
    rating["_mat_key"] = normalize_code_to_int_string(rating[rating_code_col])

    # 5) 기준정보: 가져올 컬럼 존재 체크 + 매핑 테이블 생성
    for col in cls_take_cols:
        if col not in cls.columns:
            raise ValueError(f"기준정보 파일에 '{col}' 컬럼이 없습니다.")
    cls_small = (
        cls[["_mat_key"] + list(cls_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    # 6) 평판기준: 가져올 컬럼 존재 체크 + 매핑 테이블 생성
    for col in rating_take_cols:
        if col not in rating.columns:
            raise ValueError(f"평판 기준 파일에 '{col}' 컬럼이 없습니다.")
    rating_small = (
        rating[["_mat_key"] + list(rating_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    # 7) Merge (기준정보 + 평판기준)
    out = inv.merge(cls_small, on="_mat_key", how="left")
    out = out.merge(rating_small, on="_mat_key", how="left")

    # # 8) 결측 처리
    # if "대분류" in out.columns:
    #     out["대분류"] = out["대분류"].fillna("미분류")
    # if "소분류" in out.columns:
    #     out["소분류"] = out["소분류"].fillna("미분류")

    # 원가율/평판류는 미매핑이면 빈칸(원하면 0으로 바꿔도 됨)
    for col in ["원가율", "평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = out[col].fillna("")

    # 8) 결측 처리
    if "대분류" in out.columns:
        out["대분류"] = out["대분류"].fillna("미분류")
    if "소분류" in out.columns:
        out["소분류"] = out["소분류"].fillna("미분류")

    # -----------------------------
    # ✅ (1) 평판 / 평판*1.38배 누락이면 '기말 재고 수량'으로 채우기
    # -----------------------------
    qty_col = "기말 재고 수량"

    if qty_col is not None:
        qty_num = pd.to_numeric(out[qty_col], errors="coerce")

        for col in ["평판", "평판 * 1.38배"]:
            if col in out.columns:
                col_num = pd.to_numeric(out[col], errors="coerce")
                out[col] = col_num.fillna(qty_num)  # 누락이면 기말재고수량으로 대체
    
    # ==================================================
    # 9) 파생 컬럼 계산 (지시된 계산식만 사용)
    # ==================================================
    qty_candidates = ["기말 재고 수량", "기말수량", "재고수량", "Stock Quantity on Period End"]
    amt_candidates = ["기말 재고 금액", "기말금액", "재고금액", "Stock Amount on Period End"]

    qty_col = next((c for c in qty_candidates if c in out.columns), None)
    amt_col = next((c for c in amt_candidates if c in out.columns), None)

    qty_num = pd.to_numeric(out[qty_col], errors="coerce") if qty_col else None
    amt_num = pd.to_numeric(out[amt_col], errors="coerce") if amt_col else None

    # (1) 단가 = 기말 재고 금액 / 기말 재고 수량
    if qty_col and amt_col:
        out["단가"] = amt_num / qty_num.replace({0: pd.NA})

    # (2) 출하원가 = 단가 * 평판
    if "단가" in out.columns and "평판" in out.columns:
        out["출하원가"] = (
            pd.to_numeric(out["단가"], errors="coerce") *
            pd.to_numeric(out["평판"], errors="coerce")
        )

    # (3) 출하판가 = 출하원가 / 원가율
    if "출하원가" in out.columns and "원가율" in out.columns:
        out["출하판가"] = (
            pd.to_numeric(out["출하원가"], errors="coerce") /
            pd.to_numeric(out["원가율"], errors="coerce").replace({0: pd.NA})
        )

    if "기말 재고 금액" in out.columns and "원가율" in out.columns:
        out["판가"] = (
            pd.to_numeric(out["기말 재고 금액"], errors="coerce") /
            pd.to_numeric(out["원가율"], errors="coerce").replace({0: pd.NA})
        )
        
    return out

# ======================================================
# 4) 데이터 로드
# ======================================================
inv_df = pick_df(files_dict[INV_FILE]).copy()
cls_df = pick_df(files_dict[CLS_FILE]).copy()
rating_df = pick_df(files_dict[RATING_FILE]).copy()

# ======================================================
# 5) 함수 실행 (최종 DF 생성)
# ======================================================
try:
    mapped_df = build_mapped_inventory_df(inv_df, cls_df, rating_df)
except Exception as e:
    st.error(f"❌ 매핑 중 오류가 발생했습니다: {e}")
    st.stop()

# ======================================================
# 6) 보기 좋게 컬럼 순서 정리
# ======================================================
base_cols = []
if "자재" in mapped_df.columns:
    base_cols.append("자재")
if "자재 내역" in mapped_df.columns:
    base_cols.append("자재 내역")
if "자재내역" in mapped_df.columns:
    base_cols.append("자재내역")

front_cols = [c for c in base_cols if c in mapped_df.columns] + ["대분류", "소분류", "원가율", "평판", "평판 * 1.38배"]
front_cols = [c for c in front_cols if c in mapped_df.columns]

rest_cols = [c for c in mapped_df.columns if c not in (front_cols + ["_mat_key"])]

view_df = mapped_df[front_cols + rest_cols]

# ======================================================
# 7) 결과 표시
# ======================================================
st.subheader("✅ 자재 매핑 결과 (대/소분류 + 원가율 + 평판)")
st.dataframe(view_df, use_container_width=True)

# with st.expander("⚠️ 미분류 항목만 보기"):
#     st.dataframe(
#         view_df[(view_df.get("대분류") == "미분류") | (view_df.get("소분류") == "미분류")],
#         use_container_width=True
#     )

# ======================================================
# 7) 재고 소진 시뮬레이션 (특정 자재 코드는 매년 5~8월에만 판매)
# ======================================================
def simulate_monthly_remaining_amount(
    df: pd.DataFrame,
    start_ym=(2026, 1),
    end_ym=(2028, 12),
    amount_col="기말 재고 금액",
    burn_col="출하원가",
    expiry_candidates=("유효기간", "유효 기한", "유통기한"),
    mat_col_candidates=("자재", "자재코드", "자재 코드"),
    season_mat_codes=None,              # ✅ 시즌 판매 자재코드 리스트
    season_months=(5, 6, 7, 8),         # ✅ 5~8월만 판매
    col_fmt=lambda y, m: f"{str(y)[-2:]}_{m}"
):
    """
    월별 재고금액 소진 시뮬레이션
    - 기본: 유효기간 있는 경우 출하원가만큼 월별 차감 (유효기간 월까지)
    - 유효기간 없는 경우: 시뮬레이션 미수행 → 모든 월 컬럼 0
    - ✅ 특정 자재코드(season_mat_codes): 매년 5~8월에만 차감(판매)하도록 강제
    """
    out = df.copy()

    # ---------------------------
    # 0) 자재코드 컬럼 찾기 (시즌 규칙용)
    # ---------------------------
    mat_col = next((c for c in mat_col_candidates if c in out.columns), None)
    if season_mat_codes is None:
        season_mat_codes = []

    season_set = set(str(x).strip() for x in season_mat_codes)

    if mat_col is not None:
        mat_key = out[mat_col].astype(str).str.strip()
        is_season_item = mat_key.isin(season_set)
    else:
        # 자재 컬럼이 없다면 시즌 규칙 적용 불가 → 전부 False
        is_season_item = pd.Series(False, index=out.index)

    # ---------------------------
    # 1) 유효기간 컬럼 찾기
    # ---------------------------
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)

    # 유효기간 컬럼 자체가 없으면 → 전부 0으로만 컬럼 생성
    if expiry_col is None:
        sy, sm = start_ym
        ey, em = end_ym
        y, m = sy, sm
        while (y < ey) or (y == ey and m <= em):
            out[col_fmt(y, m)] = 0.0
            m += 1
            if m == 13:
                y += 1
                m = 1
        return out

    # ---------------------------
    # 2) 유효기간 파싱
    # ---------------------------
    raw_exp = out[expiry_col].astype(str).str.strip()
    exp_dt = pd.to_datetime(raw_exp, errors="coerce")

    # 유효기간 존재 여부 마스크
    has_expiry = exp_dt.notna()

    # ---------------------------
    # 3) 숫자 컬럼 준비
    # ---------------------------
    amt0 = pd.to_numeric(out.get(amount_col), errors="coerce").fillna(0.0)
    burn = pd.to_numeric(out.get(burn_col), errors="coerce").fillna(0.0)

    # ---------------------------
    # 4) 시뮬레이션 월 리스트
    # ---------------------------
    sy, sm = start_ym
    ey, em = end_ym
    months = []
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        months.append((y, m))
        m += 1
        if m == 13:
            y += 1
            m = 1

    exp_y = exp_dt.dt.year
    exp_m = exp_dt.dt.month

    # ---------------------------
    # 5) 월별 시뮬레이션
    # ---------------------------
    remaining = amt0.copy()

    for (y, m) in months:
        col_name = col_fmt(y, m)

        # 기본값: 전부 0 (유효기간 없는 행은 계속 0 유지)
        out[col_name] = 0.0

        # (A) 유효기간 기준 판매 가능 여부 (유효기간 월까지)
        can_sell_by_expiry = has_expiry & ((y < exp_y) | ((y == exp_y) & (m <= exp_m)))

        # (B) ✅ 시즌 품목은 5~8월에만 판매 가능
        if m in season_months:
            season_allowed = pd.Series(True, index=out.index)
        else:
            season_allowed = pd.Series(False, index=out.index)

        # 시즌품목이면 season_allowed를 따라가고, 시즌품목이 아니면 항상 True(제약 없음)
        season_filter = (~is_season_item) | (is_season_item & season_allowed)

        # 최종 판매 가능 여부
        can_sell = can_sell_by_expiry & season_filter

        # 소진 적용
        remaining = remaining.where(~can_sell, (remaining - burn).clip(lower=0))

        # 결과 반영 (유효기간 있는 행만)
        out.loc[has_expiry, col_name] = remaining.loc[has_expiry]

    return out

# ======================================================
# 8) 유효기간 기준으로 부진재고량, 부진재고진입시점, 부진재고진입분기, 회전월 컬럼 추가 함수~
# ======================================================
def add_obsolete_cols_prev_month(
    df: pd.DataFrame,
    *,
    expiry_candidates=("유효기간", "유효 기한", "유통기한"),
    col_fmt=lambda y, m: f"{str(y)[-2:]}_{m}",   # 2027,6 -> "27_6"
    amt_zero=0.0,
    amount_col="기말 재고 금액",
    burn_col="출하원가"
) -> pd.DataFrame:
    out = df.copy()

    # =====================================================
    # 0) 기본 컬럼 초기화
    # =====================================================
    out["부진재고량"] = amt_zero
    out["부진재고진입시점"] = 0
    out["부진재고진입분기"] = 0
    out["회전월"] = 0.0

    # =====================================================
    # 1) 회전월 계산: 기말 재고 금액 / 출하원가
    # =====================================================
    amt = pd.to_numeric(out.get(amount_col), errors="coerce")
    burn = pd.to_numeric(out.get(burn_col), errors="coerce")

    mask_turn = burn.notna() & (burn != 0) & amt.notna()
    out.loc[mask_turn, "회전월"] = amt.loc[mask_turn] / burn.loc[mask_turn]

    # =====================================================
    # 2) 유효기간 컬럼 찾기
    # =====================================================
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)
    if expiry_col is None:
        return out

    # =====================================================
    # 3) 유효기간 파싱
    # =====================================================
    exp_dt = pd.to_datetime(out[expiry_col], errors="coerce")
    has_expiry = exp_dt.notna()

    # =====================================================
    # 4) 유효기간 기준 "전월" 계산
    # =====================================================
    exp_y = exp_dt.dt.year
    exp_m = exp_dt.dt.month

    prev_y = exp_y.where(exp_m > 1, exp_y - 1)
    prev_m = (exp_m - 1).where(exp_m > 1, 12)

    # =====================================================
    # 5) 전월 컬럼 값 → 부진재고량
    # =====================================================
    for idx in out.index:
        if not has_expiry.loc[idx]:
            continue

        y = int(prev_y.loc[idx])
        m = int(prev_m.loc[idx])
        prev_col = col_fmt(y, m)

        if prev_col not in out.columns:
            continue

        val = pd.to_numeric(out.at[idx, prev_col], errors="coerce")
        if pd.isna(val):
            continue

        out.at[idx, "부진재고량"] = float(val)

        # 부진재고 발생 시 진입 시점/분기 기록
        if float(val) > 0:
            entry_dt = out.at[idx, expiry_col]
            out.at[idx, "부진재고진입시점"] = entry_dt

            entry_parsed = pd.to_datetime(entry_dt, errors="coerce")
            if pd.notna(entry_parsed):
                yy = str(entry_parsed.year)[-2:]
                q = (entry_parsed.month - 1) // 3 + 1
                out.at[idx, "부진재고진입분기"] = f"{yy}년 {q}Q"

    return out

######################################################
# ✅ 시즌 판매 자재코드 리스트 (여기만 바꾸면 된당)
######################################################
season_codes = [
    "9305997","9307728","9307905","9307906","9308000","9308231",
    "9308427","9310455","9310878","9311190","9311191","9311719"
]
######################################################
######################################################


sim_df = simulate_monthly_remaining_amount(
    mapped_df,
    start_ym=(2026, 1),
    end_ym=(2028, 12),
    amount_col="기말 재고 금액",
    burn_col="출하원가",
    season_mat_codes=season_codes,   # ✅ 여기!
    season_months=(5,6,7,8)
)


sim_df = add_obsolete_cols_prev_month(sim_df)

def make_quarter_cols(start_year: int, end_year: int):
    """
    예: start_year=2026, end_year=2028
    → ['26년 1Q', '26년 2Q', ..., '28년 4Q']
    """
    q_cols = []
    for y in range(start_year, end_year + 1):
        yy = str(y)[-2:]
        for q in [1, 2, 3, 4]:
            q_cols.append(f"{yy}년 {q}Q")
    return q_cols


# def build_category_quarter_table_fixed_years(
#     df: pd.DataFrame,
#     *,
#     cat_cols=("대분류", "소분류"),
#     value_col="부진재고량",
#     quarter_col="부진재고진입분기",
#     start_year=2026,
#     end_year=2028,
#     amount_col="기말 재고 금액",
#     burn_col="출하원가",
# ):
#     base = df.copy()

#     # -------------------------
#     # 1) 고정 분기 컬럼 생성
#     # -------------------------
#     quarter_cols = make_quarter_cols(start_year, end_year)

#     # -------------------------
#     # 2) 분기 Pivot (허용 분기만)
#     # -------------------------
#     base["_분기"] = base[quarter_col].where(
#         base[quarter_col].isin(quarter_cols),
#         None
#     )

#     pivot_q = (
#         base.dropna(subset=["_분기"])
#             .pivot_table(
#                 index=list(cat_cols),
#                 columns="_분기",
#                 values=value_col,
#                 aggfunc="sum",
#                 fill_value=0.0
#             )
#             .reindex(columns=quarter_cols, fill_value=0.0)
#     )

#     # -------------------------
#     # 3) KPI (좌측 컬럼)
#     # -------------------------
#     g = base.groupby(list(cat_cols), dropna=False)

#     kpi = pd.DataFrame(index=g.size().index)
#     kpi["합계_기말재고금액"] = g[amount_col].sum()
#     kpi["합계_출하원가"] = g[burn_col].sum()

#     kpi["회전월"] = 0.0
#     mask = kpi["합계_출하원가"] != 0
#     kpi.loc[mask, "회전월"] = (
#         kpi.loc[mask, "합계_기말재고금액"]
#         / kpi.loc[mask, "합계_출하원가"]
#     )

#     # -------------------------
#     # 4) 합치기
#     # -------------------------
#     final = kpi.join(pivot_q, how="left").fillna(0.0)

#     return final

import pandas as pd
import numpy as np

def make_quarter_cols(start_year: int, end_year: int):
    q_cols = []
    for y in range(start_year, end_year + 1):
        yy = str(y)[-2:]
        for q in [1, 2, 3, 4]:
            q_cols.append(f"{yy}년 {q}Q")
    return q_cols


def build_category_quarter_table_column_style(
    df: pd.DataFrame,
    *,
    cat_cols=("대분류", "소분류"),
    value_col="부진재고량",
    quarter_col="부진재고진입분기",
    start_year=2026,
    end_year=2028,
    cost_col="기말 재고 금액",
    price_col="판가",
    ship_cost_col="출하원가",
    ship_price_col="출하판가",
):
    base = df.copy()
    quarter_cols = make_quarter_cols(start_year, end_year)

    # --------------------------------
    # 1) 분기 컬럼 정리
    # --------------------------------
    base["_분기"] = base[quarter_col].where(
        base[quarter_col].isin(quarter_cols), pd.NA
    )

    # --------------------------------
    # 2) 상세 (대분류-소분류) 분기 Pivot
    # --------------------------------
    pivot_detail = (
        base.dropna(subset=["_분기"])
        .pivot_table(
            index=list(cat_cols),
            columns="_분기",
            values=value_col,
            aggfunc="sum",
            fill_value=0.0
        )
        .reindex(columns=quarter_cols, fill_value=0.0)
    )
    pivot_detail["합계"] = pivot_detail.sum(axis=1)
    pivot_detail = pivot_detail.reset_index()

    # --------------------------------
    # 3) 상세 KPI
    # --------------------------------
    g = base.groupby(list(cat_cols), dropna=False)

    kpi = g.agg(
        원가=(cost_col, "sum"),
        판가=(price_col, "sum"),
        출하원가=(ship_cost_col, "sum"),
        출하판가=(ship_price_col, "sum"),
    ).reset_index()

    kpi["회전율"] = 0.0
    mask = kpi["출하원가"] != 0
    kpi.loc[mask, "회전율"] = kpi.loc[mask, "원가"] / kpi.loc[mask, "출하원가"]

    detail = kpi.merge(
        pivot_detail,
        on=list(cat_cols),
        how="left"
    ).fillna(0.0)

    # --------------------------------
    # 4) 대분류 소계
    # --------------------------------
    major = base.groupby(cat_cols[0], dropna=False)

    major_kpi = major.agg(
        원가=(cost_col, "sum"),
        판가=(price_col, "sum"),
        출하원가=(ship_cost_col, "sum"),
        출하판가=(ship_price_col, "sum"),
    ).reset_index()

    major_kpi["회전율"] = 0.0
    mask = major_kpi["출하원가"] != 0
    major_kpi.loc[mask, "회전율"] = (
        major_kpi.loc[mask, "원가"] / major_kpi.loc[mask, "출하원가"]
    )

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

    # --------------------------------
    # 5) 총계
    # --------------------------------
    total = pd.DataFrame([{
        cat_cols[0]: "총계",
        cat_cols[1]: "",
        "원가": base[cost_col].sum(),
        "판가": base[price_col].sum(),
        "출하원가": base[ship_cost_col].sum(),
        "출하판가": base[ship_price_col].sum(),
        "회전율": (
            base[cost_col].sum() / base[ship_cost_col].sum()
            if base[ship_cost_col].sum() != 0 else 0
        ),
        **{q: base.loc[base["_분기"] == q, value_col].sum() for q in quarter_cols},
        "합계": base[value_col].sum()
    }])

    # --------------------------------
    # 6) 순서 정렬 (총계 → 대분류 소계 → 상세)
    # --------------------------------
    rows = [total]

    for d in major_tbl[cat_cols[0]].unique():
        rows.append(major_tbl[major_tbl[cat_cols[0]] == d])
        rows.append(detail[detail[cat_cols[0]] == d])

    final = pd.concat(rows, ignore_index=True)

    # 컬럼 순서
    kpi_cols = ["원가", "판가", "출하원가", "출하판가", "회전율"]
    final = final[[*cat_cols, *kpi_cols, "합계", *quarter_cols]]

    # --------------------------------
    # 7) 같은 대분류 반복 표시 제거: "소계" 행에만 대분류 표시
    # --------------------------------
    major_col, sub_col = cat_cols[0], cat_cols[1]

    mask_detail = (final[major_col] != "총계") & (final[sub_col] != "소계")
    final.loc[mask_detail, major_col] = ""   # 상세행은 대분류 공백 처리

    return final


st.subheader("📊 대분류/소분류 기준 분기 집계표 (컬럼형)")

cat_table = build_category_quarter_table_column_style(
    sim_df,
    start_year=2026,
    end_year=2028
)


st.dataframe(cat_table, use_container_width=True)

buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    cat_table.to_excel(
        writer,
        index=False,              # 컬럼형이니까 index 제거
        sheet_name="분기집계표"
    )

buffer.seek(0)

st.download_button(
    label="📥 대분류/소분류 분기 집계표 엑셀 다운로드",
    data=buffer,
    file_name=f"대분류_소분류_분기집계표_{sel_year}_{sel_month}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)




# st.subheader("📊 대분류/소분류 기준 분기 집계표 (다운로드 포함)")

# cat_table = build_category_quarter_table_fixed_years(
#     sim_df,
#     start_year=2026,
#     end_year=2028
# )


# # 화면 표시
# st.dataframe(cat_table, use_container_width=True)

# # ✅ 엑셀 다운로드 (MultiIndex를 컬럼으로 풀어서 저장)
# download_df = cat_table.reset_index()

# buffer = io.BytesIO()
# with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
#     download_df.to_excel(writer, index=False, sheet_name="분기집계표")
# buffer.seek(0)

# st.download_button(
#     label="📥 대분류/소분류 분기 집계표 엑셀 다운로드",
#     data=buffer,
#     file_name=f"대분류_소분류_분기집계표_{sel_year}_{sel_month}.xlsx",
#     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# )



st.divider()
st.subheader("📌 월별 재고금액 소진 시뮬레이션 (26_1 ~ 28_12)")


# 보기 좋게: 자재/내역/유효기간/주요지표 + 월컬럼만 앞쪽으로
month_cols = [c for c in sim_df.columns if "_" in c and c.split("_")[0].isdigit()]
base_show = [c for c in ["자재", "자재 내역", "대분류", "소분류", "원가율", "평판", "단가", "출하원가", "기말 재고 금액", "유효기간", "유효 기한"] if c in sim_df.columns]
show_cols = base_show + month_cols

# st.dataframe(sim_df[show_cols], use_container_width=True)
st.dataframe(sim_df, use_container_width=True)

# 다운로드
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    sim_df[show_cols].to_excel(writer, index=False, sheet_name="monthly_sim")
buffer.seek(0)

st.download_button(
    "📥 월별 시뮬레이션 엑셀 다운로드",
    data=buffer,
    file_name=f"월별_재고금액_시뮬레이션_{sel_year}_{sel_month}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)














# # ======================================================
# # 8) 원가율, 평판 없는 애들 확인 코드(필요시 사용)
# # ======================================================
# def is_missing_series(s: pd.Series) -> pd.Series:
#     # NaN 또는 공백 문자열까지 "누락" 처리
#     return s.isna() | (s.astype(str).str.strip() == "") | (s.astype(str).str.lower().isin(["nan", "<na>"]))


# st.divider()
# st.subheader("⬇️ 원가율/평판 누락 품목 엑셀 다운로드 (중복 제거)")

# # ✅ 누락 마스크 생성 (원가율/평판/평판*1.38배 중 하나라도 누락이면 포함)
# miss_mask = (
#     is_missing_series(mapped_df["원가율"]) |
#     is_missing_series(mapped_df["평판"]) |
#     is_missing_series(mapped_df["평판 * 1.38배"])
# )

# miss_base = mapped_df[miss_mask].copy()

# if miss_base.empty:
#     st.info("원가율/평판 누락 품목이 없습니다.")
# else:
#     # 자재 내역 컬럼 찾기 (없으면 자재코드 기준으로라도 가능)
#     name_candidates = ["자재내역", "자재 내역", "자재명", "자재 명"]
#     name_col = next((c for c in name_candidates if c in miss_base.columns), None)

#     if name_col is None:
#         st.warning("⚠️ '자재 내역' 컬럼이 없어 자재코드 기준으로 중복 제거합니다.")
#         miss_base["_dedup_key"] = miss_base["_mat_key"]
#         out_cols = ["자재", "_mat_key", "대분류", "소분류", "원가율", "평판", "평판 * 1.38배"]
#     else:
#         miss_base["_dedup_key"] = miss_base[name_col].astype(str).str.strip()
#         out_cols = ["자재", name_col, "대분류", "소분류", "원가율", "평판", "평판 * 1.38배"]

#     # ✅ 중복 제거
#     download_df = miss_base.drop_duplicates(subset=["_dedup_key"]).copy()

#     # 기말 수량/금액 있으면 같이 포함
#     extra_cols = []
#     for c in ["기말 재고 수량", "기말 재고 금액", "재고수량", "재고금액", "기말수량", "기말금액", "유효기간"]:
#         if c in download_df.columns and c not in out_cols:
#             extra_cols.append(c)

#     download_df = download_df[out_cols + extra_cols]

#     # 컬럼명 정리
#     rename_map = {"_mat_key": "자재코드(정규화)"}
#     if name_col:
#         rename_map[name_col] = "자재 내역"
#     download_df = download_df.rename(columns=rename_map)

#     st.dataframe(download_df, use_container_width=True)

#     buffer = io.BytesIO()
#     with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
#         download_df.to_excel(writer, index=False, sheet_name="누락목록")
#     buffer.seek(0)

#     filename = f"원가율_평판_누락_품목_{sel_year}_{sel_month}.xlsx"
#     st.download_button(
#         label="📥 원가율/평판 누락 품목 엑셀 다운로드 (중복 제거)",
#         data=buffer,
#         file_name=filename,
#         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )



# # ======================================================
# # 8) 미분류 품목 엑셀 다운로드 (중복 제거)
# # ======================================================
# st.divider()
# st.subheader("⬇️ 미분류 품목 엑셀 다운로드 (중복 제거)")

# miss_base = mapped_df[
#     (mapped_df["대분류"] == "미분류") | (mapped_df["소분류"] == "미분류")
# ].copy()

# if miss_base.empty:
#     st.info("미분류 품목이 없습니다.")
# else:
#     name_candidates = ["자재내역", "자재 내역", "자재명", "자재 명"]
#     name_col = next((c for c in name_candidates if c in miss_base.columns), None)

#     if name_col is None:
#         miss_base["_dedup_key"] = miss_base["_mat_key"]
#         out_cols = ["자재", "_mat_key", "대분류", "소분류", "원가율", "평판", "평판 * 1.38배"]
#     else:
#         miss_base["_dedup_key"] = miss_base[name_col].astype(str).str.strip()
#         out_cols = ["자재", name_col, "대분류", "소분류", "원가율", "평판", "평판 * 1.38배"]

#     download_df = miss_base.drop_duplicates(subset=["_dedup_key"]).copy()

#     extra_cols = []
#     for c in ["기말 재고 수량", "기말 재고 금액", "재고수량", "재고금액", "기말수량", "기말금액"]:
#         if c in download_df.columns and c not in out_cols:
#             extra_cols.append(c)

#     download_df = download_df[out_cols + extra_cols]
#     download_df = download_df.rename(columns={"_mat_key": "자재코드(정규화)"})
#     if name_col:
#         download_df = download_df.rename(columns={name_col: "자재 내역"})

#     st.dataframe(download_df, use_container_width=True)

#     buffer = io.BytesIO()
#     with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
#         download_df.to_excel(writer, index=False, sheet_name="미분류")
#     buffer.seek(0)

#     st.download_button(
#         label="📥 미분류 품목 엑셀 다운로드 (중복 제거)",
#         data=buffer,
#         file_name=f"미분류_품목_중복제거_{sel_year}_{sel_month}.xlsx",
#         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )
