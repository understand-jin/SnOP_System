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

    # 원가율/평판류는 미매핑이면 빈칸(원하면 0으로 바꿔도 됨)
    for col in ["원가율", "평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = out[col].fillna("")

    # 8) 결측 처리
    if "대분류" in out.columns:
        out["대분류"] = out["대분류"].fillna("미분류")
    if "소분류" in out.columns:
        out["소분류"] = out["소분류"].fillna("미분류")

    # if "대분류" in out.columns:
    #     out = out[out["대분류"] != "원료"].copy()

    # -----------------------------
    # ✅ 8) 평판 / 평판*1.38배 누락이면 '기말 재고 수량'으로 채우기
    # -----------------------------
    # (1) 평판 관련 결측 → 0
    for col in ["평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    # (2) 평판이 0인 행 → 유효기간 2099년으로
    #     (유효기간 컬럼명이 케이스별로 다를 수 있으니 후보에서 탐색)
    expiry_candidates = ["유효 기한", "유효기간", "유통기한"]
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)

    if expiry_col is not None and "평판" in out.columns:
        mask_rating_zero = pd.to_numeric(out["평판"], errors="coerce").fillna(0).eq(0)
        out.loc[mask_rating_zero, expiry_col] = pd.Timestamp("2099-12-31")

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

    out["who"] = "자사"
        
    return out

def build_mapped_inventory_df2(
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
    rating_take_cols=("평판 * 1.38배",),   # ✅ 이것만 사용
    drop_major_raw: bool = False,          # 필요하면 원료 제거 옵션
    major_col: str = "대분류",
) -> pd.DataFrame:
    """
    기말재고(inv_df)에 대해
    - 기준정보(cls_df)에서 대분류/소분류/원가율 매핑
    - 평판기준(rating_df)에서 '평판 * 1.38배'만 매핑
    - 출하원가 계산도 '평판 * 1.38배'만 사용
    """

    inv = inv_df.copy()
    cls = cls_df.copy()
    rating = rating_df.copy()

    # 1) 즉시 정리: 용역비/배송비 포함 행 제거 (자재 내역 기반)
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

    # 6) 평판기준: '평판 * 1.38배'만 존재 체크 + 매핑 테이블 생성
    if isinstance(rating_take_cols, str):
        # 실수 방지
        rating_take_cols = (rating_take_cols,)

    for col in rating_take_cols:
        if col not in rating.columns:
            raise ValueError(f"평판 기준 파일에 '{col}' 컬럼이 없습니다.")

    rating_small = (
        rating[["_mat_key"] + list(rating_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    # 7) Merge
    out = inv.merge(cls_small, on="_mat_key", how="left")
    out = out.merge(rating_small, on="_mat_key", how="left")

    # 8) 결측 처리
    if "대분류" in out.columns:
        out["대분류"] = out["대분류"].fillna("미분류")
    else:
        out["대분류"] = "미분류"

    if "소분류" in out.columns:
        out["소분류"] = out["소분류"].fillna("미분류")
    else:
        out["소분류"] = "미분류"

    # 필요하면 대분류=원료 제거
    if drop_major_raw and major_col in out.columns:
        out = out[out[major_col] != "원료"].copy()

    # ✅ 원가율은 숫자형으로
    if "원가율" in out.columns:
        out["원가율"] = pd.to_numeric(out["원가율"], errors="coerce")

    # ✅ 평판*1.38배 결측 → 0
    rating_col = "평판 * 1.38배"
    if rating_col in out.columns:
        out[rating_col] = pd.to_numeric(out[rating_col], errors="coerce").fillna(0.0)
    else:
        out[rating_col] = 0.0

    # (옵션) 평판*1.38배가 0인 행 → 유효기간 2099-12-31
    expiry_candidates = ["유효 기한", "유효기간", "유통기한"]
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)
    if expiry_col is not None:
        mask_rating_zero = out[rating_col].fillna(0).eq(0)
        out.loc[mask_rating_zero, expiry_col] = pd.Timestamp("2099-12-31")

    # ==================================================
    # 9) 파생 컬럼 계산
    # ==================================================
    qty_candidates = ["기말 재고 수량", "기말수량", "재고수량", "Stock Quantity on Period End"]
    amt_candidates = ["기말 재고 금액", "기말금액", "재고금액", "Stock Amount on Period End"]

    qty_col = next((c for c in qty_candidates if c in out.columns), None)
    amt_col = next((c for c in amt_candidates if c in out.columns), None)

    if qty_col is None or amt_col is None:
        raise ValueError(f"수량/금액 컬럼을 찾지 못했습니다. qty_col={qty_col}, amt_col={amt_col}")

    qty_num = pd.to_numeric(out[qty_col], errors="coerce")
    amt_num = pd.to_numeric(out[amt_col], errors="coerce")

    # (1) 단가 = 금액 / 수량
    out["단가"] = amt_num / qty_num.replace({0: pd.NA})

    # (2) 출하원가 = 단가 * (평판*1.38배)
    out["출하원가"] = pd.to_numeric(out["단가"], errors="coerce") * out[rating_col]

    # (3) 출하판가 = 출하원가 / 원가율
    out["출하판가"] = out["출하원가"] / pd.to_numeric(out["원가율"], errors="coerce").replace({0: pd.NA})

    # (4) 판가 = 금액 / 원가율
    out["판가"] = amt_num / pd.to_numeric(out["원가율"], errors="coerce").replace({0: pd.NA})

    out["who"] = "자사"

    return out

def build_mapped_inventory_df3(
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

    # 원가율/평판류는 미매핑이면 빈칸(원하면 0으로 바꿔도 됨)
    for col in ["원가율", "평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = out[col].fillna("")

        # --------------------------------------------------
    # ✅ 7.5) 자재 중복 행 처리: 수량/금액만 합계하고 1행으로 만들기
    #      (파생컬럼 계산 전에 수행)
    # --------------------------------------------------
    qty_candidates = ["기말 재고 수량", "기말수량", "재고수량", "Stock Quantity on Period End"]
    amt_candidates = ["기말 재고 금액", "기말금액", "재고금액", "Stock Amount on Period End"]

    qty_col = next((c for c in qty_candidates if c in out.columns), None)
    amt_col = next((c for c in amt_candidates if c in out.columns), None)

    if qty_col is None or amt_col is None:
        raise ValueError(f"수량/금액 컬럼을 찾지 못했습니다. qty_col={qty_col}, amt_col={amt_col}")

    # 숫자 변환(집계용)
    out[qty_col] = pd.to_numeric(out[qty_col], errors="coerce").fillna(0.0)
    out[amt_col] = pd.to_numeric(out[amt_col], errors="coerce").fillna(0.0)

    # 그룹키: 자재(원본) 기준으로 묶기
    group_key = inv_code_col if inv_code_col in out.columns else "_mat_key"

    # 집계 규칙 만들기
    agg_map = {qty_col: "sum", amt_col: "sum"}

    # 나머지 컬럼은 대표값 1개만 유지 (first)
    for c in out.columns:
        if c not in agg_map and c != group_key:
            agg_map[c] = "first"

    out = out.groupby(group_key, as_index=False).agg(agg_map)


    # 8) 결측 처리
    if "대분류" in out.columns:
        out["대분류"] = out["대분류"].fillna("미분류")
    if "소분류" in out.columns:
        out["소분류"] = out["소분류"].fillna("미분류")

    # if "대분류" in out.columns:
    #     out = out[out["대분류"] != "원료"].copy()

    # -----------------------------
    # ✅ 8) 평판 / 평판*1.38배 누락이면 '기말 재고 수량'으로 채우기
    # -----------------------------
    # (1) 평판 관련 결측 → 0
    for col in ["평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    # (2) 평판이 0인 행 → 유효기간 2099년으로
    #     (유효기간 컬럼명이 케이스별로 다를 수 있으니 후보에서 탐색)
    expiry_candidates = ["유효 기한", "유효기간", "유통기한"]
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)

    if expiry_col is not None and "평판" in out.columns:
        mask_rating_zero = pd.to_numeric(out["평판"], errors="coerce").fillna(0).eq(0)
        out.loc[mask_rating_zero, expiry_col] = pd.Timestamp("2099-12-31")

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

    out["who"] = "자사"
        
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

try:
    mapped_df2 = build_mapped_inventory_df2(inv_df, cls_df, rating_df)
except Exception as e:
    st.error(f"❌ 매핑 중 오류가 발생했습니다: {e}")
    st.stop()

try:
    mapped_df3 = build_mapped_inventory_df3(inv_df, cls_df, rating_df)
except Exception as e:
    st.error(f"❌ 매핑 중 오류가 발생했습니다: {e}")
    st.stop()

st.dataframe(mapped_df3, use_container_width=True)
# ======================================================
# 6) 제조사 재고 처리
# ======================================================
def build_mapped_cancel_po_df(
    cancel_df: pd.DataFrame,
    cls_df: pd.DataFrame,
    rating_df: pd.DataFrame,
    *,
    # --- 취소현황 컬럼 후보들 ---
    prod_code_candidates=("제품코드", "제품 코드", "자재", "자재코드"),
    prod_name_candidates=("제품명", "품명", "자재 내역", "자재명"),
    unit_price_candidates=("단가", "단가(원)", "단가(￦)"),
    qty_candidates=("잔여 PO", "잔여PO", "잔여_PO", "수량", "잔여수량"),
    amt_candidates=("금액", "재고금액", "취소금액", "잔여금액"),

    # --- 기준정보 / 평판 기준 키 컬럼 ---
    cls_code_col: str = "자재코드",
    rating_code_col: str = "자재",

    # --- 매핑해서 가져올 컬럼 ---
    cls_take_cols=("대분류", "소분류", "원가율"),
    rating_take_cols=("평판", "평판 * 1.38배"),

    # --- 기타 ---
    remove_keywords_regex: str = "용역비|배송비",
    expiry_candidates=("유효 기한", "유효기간", "유통기한"),   # 취소현황에 있으면 사용
    set_expiry_2099_when_rating_zero: bool = True
) -> pd.DataFrame:
    """
    [제조사 수주 취소 현황]을 베이스로:
    - 제품코드/제품명/단가/잔여PO/금액 추출 & 표준화
    - 기준정보(cls_df)에서 대분류/소분류/원가율 매핑
    - 평판기준(rating_df)에서 평판/평판*1.38배 매핑
    - 단가/출하원가/출하판가/판가 파생 컬럼 계산
    """

    base = cancel_df.copy()
    cls = cls_df.copy()
    rating = rating_df.copy()

    # --------------------------------------------------
    # 0) 취소현황에서 필요한 컬럼 찾기
    # --------------------------------------------------
    def _pick_col(df, candidates):
        return next((c for c in candidates if c in df.columns), None)

    code_col = _pick_col(base, prod_code_candidates)
    name_col = _pick_col(base, prod_name_candidates)
    unit_col = _pick_col(base, unit_price_candidates)
    qty_col  = _pick_col(base, qty_candidates)
    amt_col  = _pick_col(base, amt_candidates)

    missing = [("제품코드", code_col), ("제품명", name_col), ("단가", unit_col), ("잔여 PO(수량)", qty_col), ("금액", amt_col)]
    missing = [label for label, col in missing if col is None]
    if missing:
        raise ValueError(f"[취소현황] 필수 컬럼을 찾지 못했습니다: {missing}\n현재 컬럼: {list(base.columns)}")

    # --------------------------------------------------
    # 1) 용역비/배송비 제거 (제품명 기반)
    # --------------------------------------------------
    if name_col is not None:
        base = base[~base[name_col].astype(str).str.contains(remove_keywords_regex, na=False)].copy()

    # --------------------------------------------------
    # 2) 표준 컬럼으로 정리 (후속 로직 호환)
    #    자재=제품코드, 자재 내역=제품명, 기말재고수량=잔여PO, 기말재고금액=금액
    # --------------------------------------------------
    out = pd.DataFrame({
        "자재": base[code_col],
        "자재 내역": base[name_col],
        "단가(원본)": base[unit_col],
        "기말 재고 수량": base[qty_col],
        "기말 재고 금액": base[amt_col],
    })

    # 원본 컬럼도 필요하면 같이 붙이고 싶을 때:
    # out = pd.concat([out, base.drop(columns=[code_col, name_col, unit_col, qty_col, amt_col], errors="ignore")], axis=1)

    # 숫자형 캐스팅
    out["기말 재고 수량"] = pd.to_numeric(out["기말 재고 수량"], errors="coerce").fillna(0)
    out["기말 재고 금액"] = pd.to_numeric(out["기말 재고 금액"], errors="coerce").fillna(0)
    out["단가(원본)"] = pd.to_numeric(out["단가(원본)"], errors="coerce")

    # --------------------------------------------------
    # 3) 키 정규화 (제품코드 기준)
    # --------------------------------------------------
    out["_mat_key"] = normalize_code_to_int_string(out["자재"])
    cls["_mat_key"] = normalize_code_to_int_string(cls[cls_code_col])
    rating["_mat_key"] = normalize_code_to_int_string(rating[rating_code_col])

    # --------------------------------------------------
    # 4) 기준정보 매핑 (대분류/소분류/원가율)
    # --------------------------------------------------
    for col in cls_take_cols:
        if col not in cls.columns:
            raise ValueError(f"기준정보 파일에 '{col}' 컬럼이 없습니다.")
    cls_small = (
        cls[["_mat_key"] + list(cls_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    # --------------------------------------------------
    # 5) 평판 매핑 (평판/평판*1.38배)
    # --------------------------------------------------
    for col in rating_take_cols:
        if col not in rating.columns:
            raise ValueError(f"평판 기준 파일에 '{col}' 컬럼이 없습니다.")
    rating_small = (
        rating[["_mat_key"] + list(rating_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    out = out.merge(cls_small, on="_mat_key", how="left")
    out = out.merge(rating_small, on="_mat_key", how="left")

    # --------------------------------------------------
    # 6) 결측 처리
    # --------------------------------------------------
    out["대분류"] = out["대분류"].fillna("미분류") if "대분류" in out.columns else "미분류"
    out["소분류"] = out["소분류"].fillna("미분류") if "소분류" in out.columns else "미분류"

    for col in ["원가율", "평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    # --------------------------------------------------
    # 7) (옵션) 평판=0이면 유효기간 2099년 세팅 (취소현황에 유효기간 컬럼이 있을 때만)
    # --------------------------------------------------
    expiry_col = next((c for c in expiry_candidates if c in cancel_df.columns), None)
    if set_expiry_2099_when_rating_zero and expiry_col is not None:
        # out에 유효기간 컬럼 추가(원본에서 가져오기)
        out[expiry_col] = cancel_df.loc[base.index, expiry_col].values
        mask_rating_zero = out["평판"].fillna(0).eq(0)
        out.loc[mask_rating_zero, expiry_col] = pd.Timestamp("2099-12-31")

    # --------------------------------------------------
    # 8) 파생 컬럼 계산 (너가 쓰던 동일 로직)
    # --------------------------------------------------
    # (1) 단가 = 금액 / 수량 (단, 수량 0이면 NaN)
    out["단가"] = out["기말 재고 금액"] / out["기말 재고 수량"].replace({0: pd.NA})

    # (2) 출하원가 = 단가 * 평판
    out["출하원가"] = pd.to_numeric(out["단가"], errors="coerce") * out["평판"]

    # (3) 출하판가 = 출하원가 / 원가율
    out["출하판가"] = out["출하원가"] / out["원가율"].replace({0: pd.NA})

    # (4) 판가 = 금액 / 원가율
    out["판가"] = out["기말 재고 금액"] / out["원가율"].replace({0: pd.NA})

    out = out.iloc[:-1].copy()

    out["유효기간"] = pd.Timestamp("2028-12-31")

    out["who"] = "제조사"

    return out

def build_mapped_cancel_po_df2(
    cancel_df: pd.DataFrame,
    cls_df: pd.DataFrame,
    rating_df: pd.DataFrame,
    *,
    # --- 취소현황 컬럼 후보들 ---
    prod_code_candidates=("제품코드", "제품 코드", "자재", "자재코드"),
    prod_name_candidates=("제품명", "품명", "자재 내역", "자재명"),
    unit_price_candidates=("단가", "단가(원)", "단가(￦)"),
    qty_candidates=("잔여 PO", "잔여PO", "잔여_PO", "수량", "잔여수량"),
    amt_candidates=("금액", "재고금액", "취소금액", "잔여금액"),

    # --- 기준정보 / 평판 기준 키 컬럼 ---
    cls_code_col: str = "자재코드",
    rating_code_col: str = "자재",

    # --- 매핑해서 가져올 컬럼 ---
    cls_take_cols=("대분류", "소분류", "원가율"),
    rating_take_cols=("평판 * 1.38배",),   # ✅ 이것만 사용

    # --- 기타 ---
    remove_keywords_regex: str = "용역비|배송비",
    expiry_candidates=("유효 기한", "유효기간", "유통기한"),
    set_expiry_2099_when_rating_zero: bool = True
) -> pd.DataFrame:
    """
    [제조사 수주 취소 현황] 기반 DF 생성
    - 평판은 사용하지 않고 '평판 * 1.38배'만 사용
    """

    base = cancel_df.copy()
    cls = cls_df.copy()
    rating = rating_df.copy()

    # --------------------------------------------------
    # 0) 취소현황에서 필요한 컬럼 찾기
    # --------------------------------------------------
    def _pick_col(df, candidates):
        return next((c for c in candidates if c in df.columns), None)

    code_col = _pick_col(base, prod_code_candidates)
    name_col = _pick_col(base, prod_name_candidates)
    unit_col = _pick_col(base, unit_price_candidates)
    qty_col  = _pick_col(base, qty_candidates)
    amt_col  = _pick_col(base, amt_candidates)

    missing = [("제품코드", code_col), ("제품명", name_col),
               ("단가", unit_col), ("잔여 PO", qty_col), ("금액", amt_col)]
    missing = [label for label, col in missing if col is None]
    if missing:
        raise ValueError(f"[취소현황] 필수 컬럼 누락: {missing}")

    # --------------------------------------------------
    # 1) 용역비/배송비 제거
    # --------------------------------------------------
    base = base[~base[name_col].astype(str).str.contains(remove_keywords_regex, na=False)].copy()

    # --------------------------------------------------
    # 2) 표준 컬럼 구성
    # --------------------------------------------------
    out = pd.DataFrame({
        "자재": base[code_col],
        "자재 내역": base[name_col],
        "기말 재고 수량": pd.to_numeric(base[qty_col], errors="coerce").fillna(0),
        "기말 재고 금액": pd.to_numeric(base[amt_col], errors="coerce").fillna(0),
    })

    # --------------------------------------------------
    # 3) 키 정규화
    # --------------------------------------------------
    out["_mat_key"] = normalize_code_to_int_string(out["자재"])
    cls["_mat_key"] = normalize_code_to_int_string(cls[cls_code_col])
    rating["_mat_key"] = normalize_code_to_int_string(rating[rating_code_col])

    # --------------------------------------------------
    # 4) 기준정보 매핑
    # --------------------------------------------------
    cls_small = (
        cls[["_mat_key"] + list(cls_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates("_mat_key")
    )

    # --------------------------------------------------
    # 5) 평판 * 1.38배 매핑
    # --------------------------------------------------
    rating_small = (
        rating[["_mat_key"] + list(rating_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates("_mat_key")
    )

    out = out.merge(cls_small, on="_mat_key", how="left")
    out = out.merge(rating_small, on="_mat_key", how="left")

    # --------------------------------------------------
    # 6) 결측 처리
    # --------------------------------------------------
    out["대분류"] = out.get("대분류", "미분류").fillna("미분류")
    out["소분류"] = out.get("소분류", "미분류").fillna("미분류")

    out["원가율"] = pd.to_numeric(out["원가율"], errors="coerce")
    out["평판 * 1.38배"] = pd.to_numeric(out["평판 * 1.38배"], errors="coerce").fillna(0)

    # --------------------------------------------------
    # 7) 평판*1.38배 = 0 → 유효기간 2099
    # --------------------------------------------------
    expiry_col = next((c for c in expiry_candidates if c in cancel_df.columns), None)
    if set_expiry_2099_when_rating_zero:
        out["유효기간"] = pd.Timestamp("2028-12-31")
        if expiry_col is not None:
            mask_zero = out["평판 * 1.38배"].eq(0)
            out.loc[mask_zero, "유효기간"] = pd.Timestamp("2099-12-31")

    # --------------------------------------------------
    # 8) 파생 컬럼 계산
    # --------------------------------------------------
    out["단가"] = out["기말 재고 금액"] / out["기말 재고 수량"].replace({0: pd.NA})
    out["출하원가"] = out["단가"] * out["평판 * 1.38배"]
    out["출하판가"] = out["출하원가"] / out["원가율"].replace({0: pd.NA})
    out["판가"] = out["기말 재고 금액"] / out["원가율"].replace({0: pd.NA})

    out["who"] = "제조사"

    return out

def build_mapped_cancel_po_df3(
    cancel_df: pd.DataFrame,
    cls_df: pd.DataFrame,
    rating_df: pd.DataFrame,
    *,
    # --- 취소현황 컬럼 후보들 ---
    prod_code_candidates=("제품코드", "제품 코드", "자재", "자재코드"),
    prod_name_candidates=("제품명", "품명", "자재 내역", "자재명"),
    unit_price_candidates=("단가", "단가(원)", "단가(￦)"),
    qty_candidates=("잔여 PO", "잔여PO", "잔여_PO", "수량", "잔여수량"),
    amt_candidates=("금액", "재고금액", "취소금액", "잔여금액"),

    # --- 기준정보 / 평판 기준 키 컬럼 ---
    cls_code_col: str = "자재코드",
    rating_code_col: str = "자재",

    # --- 매핑해서 가져올 컬럼 ---
    cls_take_cols=("대분류", "소분류", "원가율"),
    rating_take_cols=("평판", "평판 * 1.38배"),

    # --- 기타 ---
    remove_keywords_regex: str = "용역비|배송비",
    expiry_candidates=("유효 기한", "유효기간", "유통기한"),   # 취소현황에 있으면 사용
    set_expiry_2099_when_rating_zero: bool = True
) -> pd.DataFrame:
    """
    [제조사 수주 취소 현황]을 베이스로:
    - 제품코드/제품명/단가/잔여PO/금액 추출 & 표준화
    - 기준정보(cls_df)에서 대분류/소분류/원가율 매핑
    - 평판기준(rating_df)에서 평판/평판*1.38배 매핑
    - ✅ 자재 중복이면 수량/금액만 합계하여 자재당 1행 유지
    - 단가/출하원가/출하판가/판가 파생 컬럼 계산
    """

    base = cancel_df.copy()
    cls = cls_df.copy()
    rating = rating_df.copy()

    # --------------------------------------------------
    # 0) 취소현황에서 필요한 컬럼 찾기
    # --------------------------------------------------
    def _pick_col(df, candidates):
        return next((c for c in candidates if c in df.columns), None)

    code_col = _pick_col(base, prod_code_candidates)
    name_col = _pick_col(base, prod_name_candidates)
    unit_col = _pick_col(base, unit_price_candidates)
    qty_col  = _pick_col(base, qty_candidates)
    amt_col  = _pick_col(base, amt_candidates)

    missing = [("제품코드", code_col), ("제품명", name_col), ("단가", unit_col), ("잔여 PO(수량)", qty_col), ("금액", amt_col)]
    missing = [label for label, col in missing if col is None]
    if missing:
        raise ValueError(f"[취소현황] 필수 컬럼을 찾지 못했습니다: {missing}\n현재 컬럼: {list(base.columns)}")

    # --------------------------------------------------
    # 1) 용역비/배송비 제거 (제품명 기반)
    # --------------------------------------------------
    if name_col is not None:
        base = base[~base[name_col].astype(str).str.contains(remove_keywords_regex, na=False)].copy()

    # --------------------------------------------------
    # 2) 표준 컬럼으로 정리
    # --------------------------------------------------
    out = pd.DataFrame({
        "자재": base[code_col],
        "자재 내역": base[name_col],
        "단가(원본)": base[unit_col],
        "기말 재고 수량": base[qty_col],
        "기말 재고 금액": base[amt_col],
    })

    # 숫자형 캐스팅
    out["기말 재고 수량"] = pd.to_numeric(out["기말 재고 수량"], errors="coerce").fillna(0)
    out["기말 재고 금액"] = pd.to_numeric(out["기말 재고 금액"], errors="coerce").fillna(0)
    out["단가(원본)"] = pd.to_numeric(out["단가(원본)"], errors="coerce")

    # --------------------------------------------------
    # 3) 키 정규화 (제품코드 기준)
    # --------------------------------------------------
    out["_mat_key"] = normalize_code_to_int_string(out["자재"])
    cls["_mat_key"] = normalize_code_to_int_string(cls[cls_code_col])
    rating["_mat_key"] = normalize_code_to_int_string(rating[rating_code_col])

    # --------------------------------------------------
    # 4) 기준정보 매핑 (대분류/소분류/원가율)
    # --------------------------------------------------
    for col in cls_take_cols:
        if col not in cls.columns:
            raise ValueError(f"기준정보 파일에 '{col}' 컬럼이 없습니다.")
    cls_small = (
        cls[["_mat_key"] + list(cls_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    # --------------------------------------------------
    # 5) 평판 매핑 (평판/평판*1.38배)
    # --------------------------------------------------
    for col in rating_take_cols:
        if col not in rating.columns:
            raise ValueError(f"평판 기준 파일에 '{col}' 컬럼이 없습니다.")
    rating_small = (
        rating[["_mat_key"] + list(rating_take_cols)]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )

    out = out.merge(cls_small, on="_mat_key", how="left")
    out = out.merge(rating_small, on="_mat_key", how="left")

    # --------------------------------------------------
    # 6) 결측 처리
    # --------------------------------------------------
    out["대분류"] = out["대분류"].fillna("미분류") if "대분류" in out.columns else "미분류"
    out["소분류"] = out["소분류"].fillna("미분류") if "소분류" in out.columns else "미분류"

    for col in ["원가율", "평판", "평판 * 1.38배"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    # --------------------------------------------------
    # 7) (옵션) 평판=0이면 유효기간 2099년 세팅 (취소현황에 유효기간 컬럼이 있을 때만)
    # --------------------------------------------------
    expiry_col = next((c for c in expiry_candidates if c in cancel_df.columns), None)
    if set_expiry_2099_when_rating_zero and expiry_col is not None:
        out[expiry_col] = cancel_df.loc[base.index, expiry_col].values
        mask_rating_zero = out["평판"].fillna(0).eq(0)
        out.loc[mask_rating_zero, expiry_col] = pd.Timestamp("2099-12-31")

    # --------------------------------------------------
    # ✅ 7.5) 자재 중복이면 수량/금액만 합계해서 자재당 1행 유지
    # --------------------------------------------------
    qty_sum_col = "기말 재고 수량"
    amt_sum_col = "기말 재고 금액"

    # 집계 규칙: 수량/금액만 sum, 나머지는 first
    agg_map = {qty_sum_col: "sum", amt_sum_col: "sum"}
    for c in out.columns:
        if c not in agg_map and c not in ["자재", "_mat_key"]:
            agg_map[c] = "first"

    # 그룹키는 "자재"로 (표준화된 코드 기준으로 묶는 게 직관적)
    out = out.groupby("자재", as_index=False).agg(agg_map)

    # --------------------------------------------------
    # 8) 파생 컬럼 계산
    # --------------------------------------------------
    out["단가"] = out["기말 재고 금액"] / out["기말 재고 수량"].replace({0: pd.NA})

    out["출하원가"] = pd.to_numeric(out["단가"], errors="coerce") * out["평판"]

    out["출하판가"] = out["출하원가"] / out["원가율"].replace({0: pd.NA})

    out["판가"] = out["기말 재고 금액"] / out["원가율"].replace({0: pd.NA})

    # (주의) out.iloc[:-1] 이건 "마지막 행이 합계"일 때만 의미 있음
    #        지금은 groupby로 재구성했으니, 필요 없으면 제거하는 게 안전함.
    # out = out.iloc[:-1].copy()

    out["유효기간"] = pd.Timestamp("2028-12-31")
    out["who"] = "제조사"

    return out


cancel_df = pick_df(files_dict["12월 말 제조사 수주 취소 현황_코스맥스 취소.xlsx"]).copy()
cls_df    = pick_df(files_dict["기준정보_분류 및 원가율.xlsx"]).copy()
rating_df = pick_df(files_dict["기준정보_평판 기준.xlsx"]).copy()

mapped_cancel_df = build_mapped_cancel_po_df(cancel_df, cls_df, rating_df)

mapped_cancel_df2 = build_mapped_cancel_po_df2(cancel_df, cls_df, rating_df)

mapped_cancel_df3 = build_mapped_cancel_po_df3(cancel_df, cls_df, rating_df)

#st.dataframe(mapped_cancel_df, use_container_width=True)

# ======================================================
# 원하는 형식의 표 만들기
# ======================================================
# def build_major_only_report_table(
#     df_self: pd.DataFrame,
#     df_manu: pd.DataFrame,
#     *,
#     major_col="대분류",
#     sub_col="소분류",
#     cost_col_candidates=("기말 재고 금액", "금액"),
#     price_col_candidates=("판가",),
#     ship_cost_candidates=("출하원가",),
#     ship_price_candidates=("출하판가",),
#     self_name="자사",
#     manu_name="제조사",
#     include_total=True,
#     include_major_subtotal=True,
# ):
#     """
#     [요구사항 반영]
#     - 제품명/번호 레벨 제거
#     - 소분류 소계 없음
#     - 대분류 단위 소계만 존재
#     - 상세는 (대분류, 소분류) 레벨 집계
#     - 컬럼:
#       (자사 원가/판가) (제조사 원가/판가) (합계 원가/판가)
#       + (출하원가/출하판가 = 월 출하) + 회전월
#     """

#     def pick_col(df, candidates):
#         return next((c for c in candidates if c in df.columns), None)

#     # --- 자사/제조사에서 필요한 컬럼 찾기 ---
#     cost_col_self = pick_col(df_self, cost_col_candidates)
#     cost_col_manu = pick_col(df_manu, cost_col_candidates)
#     price_col_self = pick_col(df_self, price_col_candidates)
#     price_col_manu = pick_col(df_manu, price_col_candidates)

#     ship_cost_self = pick_col(df_self, ship_cost_candidates)
#     ship_cost_manu = pick_col(df_manu, ship_cost_candidates)
#     ship_price_self = pick_col(df_self, ship_price_candidates)
#     ship_price_manu = pick_col(df_manu, ship_price_candidates)

#     if cost_col_self is None or price_col_self is None:
#         raise ValueError(f"[df_self] 원가/판가 컬럼을 찾지 못함. columns={list(df_self.columns)}")
#     if cost_col_manu is None or price_col_manu is None:
#         raise ValueError(f"[df_manu] 원가/판가 컬럼을 찾지 못함. columns={list(df_manu.columns)}")

#     # 출하원가/출하판가는 없을 수도 있으니(취소PO에 없거나) 없으면 0으로 처리
#     # (단, 자사 DF(mapped_df)는 보통 있음)
#     def standardize(df, who, cost_col, price_col, ship_cost_col, ship_price_col):
#         tmp = df.copy()
#         if major_col not in tmp.columns:
#             tmp[major_col] = "미분류"
#         if sub_col not in tmp.columns:
#             tmp[sub_col] = "미분류"

#         tmp["_who"] = who
#         tmp["_cost"] = pd.to_numeric(tmp[cost_col], errors="coerce").fillna(0.0)
#         tmp["_price"] = pd.to_numeric(tmp[price_col], errors="coerce").fillna(0.0)

#         if ship_cost_col is None:
#             tmp["_ship_cost"] = 0.0
#         else:
#             tmp["_ship_cost"] = pd.to_numeric(tmp[ship_cost_col], errors="coerce").fillna(0.0)

#         if ship_price_col is None:
#             tmp["_ship_price"] = 0.0
#         else:
#             tmp["_ship_price"] = pd.to_numeric(tmp[ship_price_col], errors="coerce").fillna(0.0)

#         return tmp[[major_col, sub_col, "_who", "_cost", "_price", "_ship_cost", "_ship_price"]]

#     s = standardize(df_self, self_name, cost_col_self, price_col_self, ship_cost_self, ship_price_self)
#     m = standardize(df_manu, manu_name, cost_col_manu, price_col_manu, ship_cost_manu, ship_price_manu)
#     base = pd.concat([s, m], ignore_index=True)

#     # ✅ (대분류, 소분류) 레벨 집계
#     piv = base.pivot_table(
#         index=[major_col, sub_col],
#         columns="_who",
#         values=["_cost", "_price", "_ship_cost", "_ship_price"],
#         aggfunc="sum",
#         fill_value=0.0
#     )

#     # 컬럼명 펼치기
#     def col_name(measure, who):
#         if measure == "_cost":
#             return f"{who} 원가"
#         if measure == "_price":
#             return f"{who} 판가"
#         if measure == "_ship_cost":
#             return f"{who} 출하원가"
#         return f"{who} 출하판가"

#     piv.columns = [col_name(measure, who) for (measure, who) in piv.columns]
#     piv = piv.reset_index()

#     # 없는 컬럼 보정
#     needed_cols = [
#         f"{self_name} 원가", f"{self_name} 판가", f"{self_name} 출하원가", f"{self_name} 출하판가",
#         f"{manu_name} 원가", f"{manu_name} 판가", f"{manu_name} 출하원가", f"{manu_name} 출하판가",
#     ]
#     for c in needed_cols:
#         if c not in piv.columns:
#             piv[c] = 0.0

#     # 합계(원가/판가)
#     piv["합계 원가"] = piv[f"{self_name} 원가"] + piv[f"{manu_name} 원가"]
#     piv["합계 판가"] = piv[f"{self_name} 판가"] + piv[f"{manu_name} 판가"]

#     # ✅ 출하/월(원가/판가) = 자사 출하 + 제조사 출하
#     piv["출하/월 원가"] = piv[f"{self_name} 출하원가"] + piv[f"{manu_name} 출하원가"]
#     piv["출하/월 판가"] = piv[f"{self_name} 출하판가"] + piv[f"{manu_name} 출하판가"]

#     # ✅ 회전월 = 합계 원가 / 출하/월 원가
#     denom = piv["출하/월 원가"].replace({0: np.nan})
#     piv["회전월"] = (piv["합계 원가"] / denom).fillna(0)

#     # ---- 대분류 소계 / 총계 추가 ----
#     rows = []

#     if include_total:
#         total = pd.DataFrame([{
#             major_col: "총계",
#             sub_col: "",
#             f"{self_name} 원가": piv[f"{self_name} 원가"].sum(),
#             f"{self_name} 판가": piv[f"{self_name} 판가"].sum(),
#             f"{manu_name} 원가": piv[f"{manu_name} 원가"].sum(),
#             f"{manu_name} 판가": piv[f"{manu_name} 판가"].sum(),
#             "합계 원가": piv["합계 원가"].sum(),
#             "합계 판가": piv["합계 판가"].sum(),
#             "출하/월 원가": piv["출하/월 원가"].sum(),
#             "출하/월 판가": piv["출하/월 판가"].sum(),
#             # 총계 회전월도 동일 정의로
#             "회전월": (piv["합계 원가"].sum() / (piv["출하/월 원가"].sum() if piv["출하/월 원가"].sum() != 0 else np.nan)) or 0,
#         }])
#         rows.append(total)

#     for maj, maj_df in piv.groupby(major_col, sort=False):
#         if include_major_subtotal:
#             maj_ship = maj_df["출하/월 원가"].sum()
#             maj_total = pd.DataFrame([{
#                 major_col: maj,
#                 sub_col: "소계",
#                 f"{self_name} 원가": maj_df[f"{self_name} 원가"].sum(),
#                 f"{self_name} 판가": maj_df[f"{self_name} 판가"].sum(),
#                 f"{manu_name} 원가": maj_df[f"{manu_name} 원가"].sum(),
#                 f"{manu_name} 판가": maj_df[f"{manu_name} 판가"].sum(),
#                 "합계 원가": maj_df["합계 원가"].sum(),
#                 "합계 판가": maj_df["합계 판가"].sum(),
#                 "출하/월 원가": maj_ship,
#                 "출하/월 판가": maj_df["출하/월 판가"].sum(),
#                 "회전월": (maj_df["합계 원가"].sum() / maj_ship) if maj_ship != 0 else 0,
#             }])
#             rows.append(maj_total)

#         rows.append(maj_df)

#     final = pd.concat(rows, ignore_index=True)

#     # 보기 좋게: 소계/총계가 아닌 상세행에서는 대분류 공백 처리
#     mask_detail = (final[major_col] != "총계") & (final[sub_col] != "소계")
#     final.loc[mask_detail, major_col] = ""

#     # 컬럼 순서 (네 표처럼)
#     final = final[
#         [major_col, sub_col,
#          f"{self_name} 원가", f"{self_name} 판가",
#          f"{manu_name} 원가", f"{manu_name} 판가",
#          "합계 원가", "합계 판가",
#          "출하/월 원가", "출하/월 판가",
#          "회전월"]
#     ]

#     # EOK = 100_000_000

#     # money_cols = [
#     #     f"{self_name} 원가", f"{self_name} 판가",
#     #     f"{manu_name} 원가", f"{manu_name} 판가",
#     #     "합계 원가", "합계 판가",
#     #     "출하/월 원가", "출하/월 판가",
#     # ]

#     # for c in money_cols:
#     #     if c in final.columns:
#     #         final[c] = final[c] / EOK
    

#     return final


def build_major_only_report_table(
    df_self: pd.DataFrame,
    df_manu: pd.DataFrame,
    *,
    major_col="대분류",
    sub_col="소분류",
    cost_col_candidates=("기말 재고 금액", "금액"),
    price_col_candidates=("판가",),
    ship_cost_candidates=("출하원가",),
    ship_price_candidates=("출하판가",),
    self_name="자사",
    manu_name="제조사",
    include_total=True,
    include_major_subtotal=True,
):
    """
    [요구사항 반영]
    - 제품명/번호 레벨 제거
    - 소분류 소계 없음
    - 대분류 단위 소계만 존재
    - 상세는 (대분류, 소분류) 레벨 집계
    - 컬럼:
      (자사 원가/판가) (제조사 원가/판가) (합계 원가/판가)
    - ✅ 출하원가/출하판가/회전월은 계산/표시하지 않음
    """

    def pick_col(df, candidates):
        return next((c for c in candidates if c in df.columns), None)

    # --- 자사/제조사에서 필요한 컬럼 찾기 ---
    cost_col_self = pick_col(df_self, cost_col_candidates)
    cost_col_manu = pick_col(df_manu, cost_col_candidates)
    price_col_self = pick_col(df_self, price_col_candidates)
    price_col_manu = pick_col(df_manu, price_col_candidates)

    # (표시 안 하더라도, 있으면 읽어는 둘 수 있음 / 없으면 무시)
    ship_cost_self = pick_col(df_self, ship_cost_candidates)
    ship_cost_manu = pick_col(df_manu, ship_cost_candidates)
    ship_price_self = pick_col(df_self, ship_price_candidates)
    ship_price_manu = pick_col(df_manu, ship_price_candidates)

    if cost_col_self is None or price_col_self is None:
        raise ValueError(f"[df_self] 원가/판가 컬럼을 찾지 못함. columns={list(df_self.columns)}")
    if cost_col_manu is None or price_col_manu is None:
        raise ValueError(f"[df_manu] 원가/판가 컬럼을 찾지 못함. columns={list(df_manu.columns)}")

    def standardize(df, who, cost_col, price_col, ship_cost_col, ship_price_col):
        tmp = df.copy()
        if major_col not in tmp.columns:
            tmp[major_col] = "미분류"
        if sub_col not in tmp.columns:
            tmp[sub_col] = "미분류"

        tmp["_who"] = who
        tmp["_cost"] = pd.to_numeric(tmp[cost_col], errors="coerce").fillna(0.0)
        tmp["_price"] = pd.to_numeric(tmp[price_col], errors="coerce").fillna(0.0)

        # 아래 두 값은 이번 버전에서는 표에 쓰지 않지만, 표준화 컬럼 유지(호환용)
        if ship_cost_col is None:
            tmp["_ship_cost"] = 0.0
        else:
            tmp["_ship_cost"] = pd.to_numeric(tmp[ship_cost_col], errors="coerce").fillna(0.0)

        if ship_price_col is None:
            tmp["_ship_price"] = 0.0
        else:
            tmp["_ship_price"] = pd.to_numeric(tmp[ship_price_col], errors="coerce").fillna(0.0)

        return tmp[[major_col, sub_col, "_who", "_cost", "_price", "_ship_cost", "_ship_price"]]

    s = standardize(df_self, self_name, cost_col_self, price_col_self, ship_cost_self, ship_price_self)
    m = standardize(df_manu, manu_name, cost_col_manu, price_col_manu, ship_cost_manu, ship_price_manu)
    base = pd.concat([s, m], ignore_index=True)

    # ✅ (대분류, 소분류) 레벨 집계
    piv = base.pivot_table(
        index=[major_col, sub_col],
        columns="_who",
        values=["_cost", "_price"],   # ✅ 출하 관련 measure 제외
        aggfunc="sum",
        fill_value=0.0
    )

    # 컬럼명 펼치기
    def col_name(measure, who):
        if measure == "_cost":
            return f"{who} 원가"
        return f"{who} 판가"

    piv.columns = [col_name(measure, who) for (measure, who) in piv.columns]
    piv = piv.reset_index()
    

    
    # 없는 컬럼 보정
    needed_cols = [
        f"{self_name} 원가", f"{self_name} 판가",
        f"{manu_name} 원가", f"{manu_name} 판가",
    ]
    for c in needed_cols:
        if c not in piv.columns:
            piv[c] = 0.0

    # 합계(원가/판가)
    piv["합계 원가"] = piv[f"{self_name} 원가"] + piv[f"{manu_name} 원가"]
    piv["합계 판가"] = piv[f"{self_name} 판가"] + piv[f"{manu_name} 판가"]

    # ---- 대분류 소계 / 총계 추가 ----
    rows = []

    if include_total:
        total = pd.DataFrame([{
            major_col: "총계",
            sub_col: "",
            f"{self_name} 원가": piv[f"{self_name} 원가"].sum(),
            f"{self_name} 판가": piv[f"{self_name} 판가"].sum(),
            f"{manu_name} 원가": piv[f"{manu_name} 원가"].sum(),
            f"{manu_name} 판가": piv[f"{manu_name} 판가"].sum(),
            "합계 원가": piv["합계 원가"].sum(),
            "합계 판가": piv["합계 판가"].sum(),
        }])
        rows.append(total)

    for maj, maj_df in piv.groupby(major_col, sort=False):
        if include_major_subtotal:
            maj_total = pd.DataFrame([{
                major_col: maj,
                sub_col: "소계",
                f"{self_name} 원가": maj_df[f"{self_name} 원가"].sum(),
                f"{self_name} 판가": maj_df[f"{self_name} 판가"].sum(),
                f"{manu_name} 원가": maj_df[f"{manu_name} 원가"].sum(),
                f"{manu_name} 판가": maj_df[f"{manu_name} 판가"].sum(),
                "합계 원가": maj_df["합계 원가"].sum(),
                "합계 판가": maj_df["합계 판가"].sum(),
            }])
            rows.append(maj_total)

        rows.append(maj_df)

    final = pd.concat(rows, ignore_index=True)

    # 보기 좋게: 소계/총계가 아닌 상세행에서는 대분류 공백 처리
    mask_detail = (final[major_col] != "총계") & (final[sub_col] != "소계")
    final.loc[mask_detail, major_col] = ""

    # 컬럼 순서 (출하/회전월 제외)
    final = final[
        [major_col, sub_col,
         f"{self_name} 원가", f"{self_name} 판가",
         f"{manu_name} 원가", f"{manu_name} 판가",
         "합계 원가", "합계 판가"]
    ]

    return final

major_report_df = build_major_only_report_table(
    df_self=mapped_df3,
    df_manu=mapped_cancel_df3,   # 제조사 DF 변수명 맞춰서
    major_col="대분류",
    sub_col="소분류",
    self_name="자사",
    manu_name="제조사",
    include_total=True,
    include_major_subtotal=True,
)

st.subheader("📌 대분류 소계 포함 통합 리포트 ")
st.dataframe(major_report_df, use_container_width=True)

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
    season_mat_codes=None,              # 시즌 판매 자재코드 리스트
    season_months=(5, 6, 7, 8),         # 5~8월만 판매
    col_fmt=lambda y, m: f"{str(y)[-2:]}_{m}"
):
    """
    [월별 재고금액 소진 시뮬레이션 - 최종]
    - 판매는 '유효기간 - 6개월'이 속한 월까지만 허용
    - 시즌 자재는 지정된 월(season_months)에만 판매
    - 유효기간 컬럼이 없으면 월 컬럼만 생성하고 전부 0
    """

    out = df.copy()

    # --------------------------------------------------
    # 0) 자재코드 컬럼 찾기 (시즌 규칙용)
    # --------------------------------------------------
    mat_col = next((c for c in mat_col_candidates if c in out.columns), None)

    if season_mat_codes is None:
        season_mat_codes = []

    season_set = set(str(x).strip() for x in season_mat_codes)

    if mat_col is not None:
        mat_key = out[mat_col].astype(str).str.strip()
        is_season_item = mat_key.isin(season_set)
    else:
        is_season_item = pd.Series(False, index=out.index)

    # --------------------------------------------------
    # 1) 유효기간 컬럼 찾기
    # --------------------------------------------------
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)

    # 유효기간 컬럼이 없으면 → 월 컬럼만 생성하고 종료
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

    # --------------------------------------------------
    # 2) 유효기간 파싱 + 컷오프(유효기간 - 6개월)
    # --------------------------------------------------
    raw_exp = out[expiry_col].astype(str).str.strip()
    exp_dt = pd.to_datetime(raw_exp, errors="coerce")
    has_expiry = exp_dt.notna()

    # ✅ 유효기간 - 6개월
    cutoff_dt = exp_dt - pd.DateOffset(months=6)
    cut_y = cutoff_dt.dt.year
    cut_m = cutoff_dt.dt.month

    # --------------------------------------------------
    # 3) 금액 / 출하원가 숫자 준비
    # --------------------------------------------------
    remaining = pd.to_numeric(out.get(amount_col), errors="coerce").fillna(0.0)
    burn = pd.to_numeric(out.get(burn_col), errors="coerce").fillna(0.0)

    # --------------------------------------------------
    # 4) 시뮬레이션 월 리스트 생성
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 5) 월별 소진 시뮬레이션
    # --------------------------------------------------
    for (y, m) in months:
        col_name = col_fmt(y, m)
        out[col_name] = 0.0

        # (A) 유효기간-6개월 컷오프 기준 판매 가능 여부
        can_sell_by_cutoff = (
            has_expiry &
            ((y < cut_y) | ((y == cut_y) & (m <= cut_m)))
        )

        # (B) 시즌 판매 필터
        if m in season_months:
            season_allowed = pd.Series(True, index=out.index)
        else:
            season_allowed = pd.Series(False, index=out.index)

        season_filter = (~is_season_item) | (is_season_item & season_allowed)

        # (C) 최종 판매 가능 여부
        can_sell = can_sell_by_cutoff & season_filter

        # (D) 소진 적용
        remaining = remaining.where(
            ~can_sell,
            (remaining - burn).clip(lower=0)
        )

        # (E) 결과 반영 (유효기간 있는 행만)
        out.loc[has_expiry, col_name] = remaining.loc[has_expiry]

    return out


# ======================================================
# 8) 유효기간 기준으로 부진재고량, 부진재고진입시점, 부진재고진입분기, 회전월 컬럼 추가 함수
# ======================================================
def add_obsolete_cols_at_cutoff_6m(
    df: pd.DataFrame,
    *,
    expiry_candidates=("유효기간", "유효 기한", "유통기한"),
    col_fmt=lambda y, m: f"{str(y)[-2:]}_{m}",
    amt_zero=0.0,
    amount_col="기말 재고 금액",
    burn_col="출하원가"
) -> pd.DataFrame:
    out = df.copy()

    # 0) 기본 컬럼 초기화
    out["부진재고량"] = amt_zero
    out["부진재고진입시점"] = 0
    out["부진재고진입분기"] = 0
    out["회전월"] = 0.0

    # 1) 회전월 = 기말 재고 금액 / 출하원가
    amt = pd.to_numeric(out.get(amount_col), errors="coerce")
    burn = pd.to_numeric(out.get(burn_col), errors="coerce")
    mask_turn = burn.notna() & (burn != 0) & amt.notna()
    out.loc[mask_turn, "회전월"] = amt.loc[mask_turn] / burn.loc[mask_turn]

    # 2) 유효기간 컬럼 찾기
    expiry_col = next((c for c in expiry_candidates if c in out.columns), None)
    if expiry_col is None:
        return out

    # 3) 유효기간 파싱
    exp_dt = pd.to_datetime(out[expiry_col], errors="coerce")
    has_expiry = exp_dt.notna()
    if not has_expiry.any():
        return out

    # ✅ 4) 컷오프(유효기간-6개월) 계산
    cutoff_dt = exp_dt - pd.DateOffset(months=6)
    cut_y = cutoff_dt.dt.year
    cut_m = cutoff_dt.dt.month

    # 5) 컷오프 월 컬럼값 → 부진재고량
    for idx in out.index:
        if not has_expiry.loc[idx]:
            continue

        y = int(cut_y.loc[idx])
        m = int(cut_m.loc[idx])
        cut_col = col_fmt(y, m)

        if cut_col not in out.columns:
            continue

        val = pd.to_numeric(out.at[idx, cut_col], errors="coerce")
        if pd.isna(val):
            continue

        out.at[idx, "부진재고량"] = float(val)

        # ✅ 부진재고 진입 시점/분기: 컷오프 날짜 기준
        if float(val) > 0:
            entry_dt = cutoff_dt.loc[idx]  # 유효기간-6개월 날짜
            out.at[idx, "부진재고진입시점"] = entry_dt

            q = (entry_dt.month - 1) // 3 + 1
            yy = str(entry_dt.year)[-2:]
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
# 자사 + 제조사 통합 시뮬레이션용 DF 준비
######################################################

# 1) 두 DF에서 공통 컬럼만 맞추지 말고,
#    "둘 중 하나라도 갖고 있는 컬럼"을 모두 포함시키되, 없는 컬럼은 NaN으로 생성되게 concat
combined_df = pd.concat(
    [mapped_df, mapped_cancel_df],
    ignore_index=True,
    sort=False
).copy()

combined_df2 = pd.concat(
    [mapped_df2, mapped_cancel_df2],
    ignore_index=True,
    sort=False
).copy()

sim_df = simulate_monthly_remaining_amount(
    combined_df,
    start_ym=(2026, 1),
    end_ym=(2028, 12),
    amount_col="기말 재고 금액",
    burn_col="출하원가",
    season_mat_codes=season_codes,  
    season_months=(5,6,7,8)
)


sim_df = add_obsolete_cols_at_cutoff_6m(sim_df)

sim_df2 = simulate_monthly_remaining_amount(
    combined_df2,
    start_ym=(2026, 1),
    end_ym=(2028, 12),
    amount_col="기말 재고 금액",
    burn_col="출하원가",
    season_mat_codes=season_codes,  
    season_months=(5,6,7,8)
)


sim_df2 = add_obsolete_cols_at_cutoff_6m(sim_df2)

sim_df3 = simulate_monthly_remaining_amount(
    mapped_df,
    start_ym=(2026, 1),
    end_ym=(2028, 12),
    amount_col="기말 재고 금액",
    burn_col="출하원가",
    season_mat_codes=season_codes,  
    season_months=(5,6,7,8)
)


sim_df3 = add_obsolete_cols_at_cutoff_6m(sim_df3)

sim_df4 = simulate_monthly_remaining_amount(
    mapped_df2,
    start_ym=(2026, 1),
    end_ym=(2028, 12),
    amount_col="기말 재고 금액",
    burn_col="출하원가",
    season_mat_codes=season_codes,  
    season_months=(5,6,7,8)
)


sim_df4 = add_obsolete_cols_at_cutoff_6m(sim_df4)
st.subheader("📌 자사 + 제조사 통합 재고 소진 시뮬레이션 결과")
st.dataframe(sim_df, use_container_width=True)
st.dataframe(sim_df2, use_container_width=True)
st.dataframe(sim_df3, use_container_width=True)
st.dataframe(sim_df4, use_container_width=True)



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
    # 재고
    cost_col="기말 재고 금액",
    qty_col="기말 재고 수량",
    # 판매량 컬럼(둘 중 하나를 함수 입력으로 선택)
    sales_col="평판",                 
    # ✅ 추가: sales_col이 없을 때 자동 fallback 후보
    sales_fallback_cols=("평판 * 1.38배", "평판"),
    allow_sales_fallback=True,
    # 원가율
    cost_rate_col="원가율",            
    # KPI 컬럼명(출력용)
    ship_cost_col="출하원가",
    ship_price_col="출하판가",
    # 자재 키
    mat_col="자재",
):
    base = df.copy()
    quarter_cols = make_quarter_cols(start_year, end_year)

    # --------------------------------
    # 1) 분기 컬럼 정리 (Pivot용 base)
    # --------------------------------
    if quarter_col not in base.columns:
        raise KeyError(f"Column '{quarter_col}' not found. columns={list(base.columns)}")

    base["_분기"] = base[quarter_col].where(
        base[quarter_col].isin(quarter_cols), pd.NA
    )

    # --------------------------------
    # 2) 분기 Pivot (부진재고량은 base 기준)
    # --------------------------------
    for c in [*cat_cols, value_col]:
        if c not in base.columns:
            raise KeyError(f"Column '{c}' not found. columns={list(base.columns)}")

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

    # =====================================================
    # 3) KPI 계산용: 자재 단위로 재집계 (합산 기반)
    # =====================================================

    # ✅ sales_col 유효성 체크 + fallback
    if sales_col not in base.columns:
        if allow_sales_fallback:
            found = None
            for cand in sales_fallback_cols:
                if cand in base.columns:
                    found = cand
                    break
            if found is None:
                # 평판 관련 후보 컬럼을 같이 보여주기
                hint = [c for c in base.columns if "평판" in str(c)]
                raise KeyError(
                    f"sales_col='{sales_col}' not found and no fallback found. "
                    f"fallbacks={sales_fallback_cols}. "
                    f"Available '평판' candidates={hint}. "
                    f"All columns={list(base.columns)}"
                )
            sales_col = found  # ✅ 자동 대체
        else:
            hint = [c for c in base.columns if "평판" in str(c)]
            raise KeyError(
                f"sales_col='{sales_col}' not found. "
                f"Available '평판' candidates={hint}. "
                f"All columns={list(base.columns)}"
            )

    # 필수 컬럼 체크 (sales_col은 위에서 확정)
    for c in [mat_col, *cat_cols, cost_col, qty_col, sales_col, cost_rate_col]:
        if c not in base.columns:
            raise KeyError(f"Column '{c}' not found. columns={list(base.columns)}")

    tmp = base.copy()

    # 숫자화
    tmp[cost_col] = pd.to_numeric(tmp[cost_col], errors="coerce").fillna(0.0)
    tmp[qty_col] = pd.to_numeric(tmp[qty_col], errors="coerce").fillna(0.0)
    tmp[sales_col] = pd.to_numeric(tmp[sales_col], errors="coerce").fillna(0.0)
    tmp[cost_rate_col] = pd.to_numeric(tmp[cost_rate_col], errors="coerce").fillna(0.0)

    # 자재별 집계
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

    # 원가단가 = 재고금액합 / 재고수량합
    mat_agg["_원가단가"] = 0.0
    m_qty = mat_agg[qty_col] != 0
    mat_agg.loc[m_qty, "_원가단가"] = mat_agg.loc[m_qty, cost_col] / mat_agg.loc[m_qty, qty_col]

    # 자재별 출하원가 = 원가단가 * 판매량
    mat_agg[ship_cost_col] = mat_agg["_원가단가"] * mat_agg[sales_col]

    # 자재별 출하판가 = 출하원가 / 원가율 (원가율이 0이면 0)
    mat_agg[ship_price_col] = 0.0
    m_rate = mat_agg[cost_rate_col] != 0
    mat_agg.loc[m_rate, ship_price_col] = (
        mat_agg.loc[m_rate, ship_cost_col] / mat_agg.loc[m_rate, cost_rate_col]
    )

    # --------------------------------
    # 4) 카테고리(대/소분류) KPI 집계
    # --------------------------------
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

    # (기존 컬럼 호환)
    kpi["회전율"] = kpi["회전월"]

    detail = (
        kpi.merge(pivot_detail, on=list(cat_cols), how="left")
        .fillna(0.0)
    )

    # --------------------------------
    # 5) 대분류 소계
    # --------------------------------
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
    major_kpi["회전율"] = major_kpi["회전월"]

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
    # 6) 총계 (자재 집계 기반)
    # --------------------------------
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

    # --------------------------------
    # 7) 순서 정렬 (총계 → 대분류 소계 → 상세)
    # --------------------------------
    rows = [total]
    for d in major_tbl[cat_cols[0]].unique():
        rows.append(major_tbl[major_tbl[cat_cols[0]] == d])
        rows.append(detail[detail[cat_cols[0]] == d])

    final = pd.concat(rows, ignore_index=True)

    # 컬럼 순서
    kpi_cols = ["원가", "출하원가", "출하판가", "회전월"]
    final = final[[*cat_cols, *kpi_cols, "합계", *quarter_cols]]

    # --------------------------------
    # 8) 같은 대분류 반복 표시 제거
    # --------------------------------
    major_name, sub_name = cat_cols[0], cat_cols[1]
    mask_detail = (final[major_name] != "총계") & (final[sub_name] != "소계")
    final.loc[mask_detail, major_name] = ""

    return final


#st.subheader("📊 대분류/소분류 기준 분기 집계표 (컬럼형)")

cat_table = build_category_quarter_table_column_style(
    df=sim_df, 
    sales_col="평판"              
)

cat_table2 = build_category_quarter_table_column_style(
    df=sim_df2,
    sales_col="평판 * 1.38배" 
)

cat_table3 = build_category_quarter_table_column_style(
    df=sim_df3,
    sales_col="평판" 
)

cat_table4 = build_category_quarter_table_column_style(
    df=sim_df4,
    sales_col="평판 * 1.38배" 
)


# =========================
# 0) 공용: merge key 만들기
# =========================
def add_merge_keys(df: pd.DataFrame, major="대분류", sub="소분류") -> pd.DataFrame:
    out = df.copy()

    # 컬럼명 통일
    if "소분" in out.columns and sub not in out.columns:
        out = out.rename(columns={"소분": sub})

    # major/sub 없으면 에러 (원하면 여기서 생성 로직으로 바꿔도 됨)
    if major not in out.columns or sub not in out.columns:
        raise ValueError(f"'{major}', '{sub}' 컬럼이 필요합니다. 현재 columns={list(out.columns)}")

    # major는 빈칸이 있는 경우 ffill로 채워서 키 안정화
    out["merge_major"] = out[major].replace("", np.nan).ffill()
    out["merge_sub"] = out[sub].fillna("")
    return out


# ======================================================
# 1) 공용: cat_table을 base_df 오른쪽에 붙이는 함수
#    - drop_mode:
#      "cost_price_only"  : 원가/판가만 제거 (출하는 유지)
#      "cost_price_ship_turn" : 원가/판가/출하/회전 모두 제거 (잔액만)
# ======================================================
def attach_cat_table(
    base_df: pd.DataFrame,
    cat_df: pd.DataFrame,
    *,
    prefix: str,
    drop_mode: str = "cost_price_only",  # "cost_price_only" or "cost_price_ship_turn"
    include_ship_cols: bool = True,      # drop_mode="cost_price_only"일 때만 의미 있음
    major="대분류",
    sub="소분류",
) -> pd.DataFrame:
    ct = cat_df.copy()

    # 1) drop 컬럼 결정
    if drop_mode == "cost_price_ship_turn":
        drop_keywords = ["원가", "판가", "출하", "회전"]
        drop_cols = [c for c in ct.columns if any(k in c for k in drop_keywords)]
    elif drop_mode == "cost_price_only":
        # 원가/판가 포함하는데, 출하원가/출하판가는 유지 옵션
        def is_drop_col(c: str) -> bool:
            has_cost_price = ("원가" in c) or ("판가" in c)
            if not has_cost_price:
                return False

            if include_ship_cols:
                # 출하원가/출하판가는 남기기
                is_ship = ("출하" in c)
                return has_cost_price and (not is_ship)
            else:
                # 출하도 제거하고 싶으면 True
                return True

        drop_cols = [c for c in ct.columns if is_drop_col(c)]
    else:
        raise ValueError("drop_mode는 'cost_price_only' 또는 'cost_price_ship_turn'만 가능합니다.")

    ct = ct.drop(columns=drop_cols, errors="ignore")

    # 2) cat_table에 merge key 생성
    ct = add_merge_keys(ct, major=major, sub=sub)

    # 3) 붙일 값 컬럼들 (키 제외)
    value_cols = [c for c in ct.columns if c not in [major, sub, "merge_major", "merge_sub"]]
    ct_small = ct[["merge_major", "merge_sub"] + value_cols].copy()

    # 4) prefix 붙여 컬럼 중복 방지
    rename_map = {c: f"{prefix}_{c}" for c in value_cols}
    ct_small = ct_small.rename(columns=rename_map)
    renamed_cols = [rename_map[c] for c in value_cols]

    # 5) base_df는 merge_major/merge_sub가 반드시 있어야 함
    if ("merge_major" not in base_df.columns) or ("merge_sub" not in base_df.columns):
        raise ValueError("base_df에 merge_major/merge_sub가 없습니다. (drop하기 전에 붙여야 합니다)")

    # 6) base_df의 행 순서대로 매칭
    tmp = base_df[["merge_major", "merge_sub"]].merge(
        ct_small,
        on=["merge_major", "merge_sub"],
        how="left"
    )
    tmp[renamed_cols] = tmp[renamed_cols].fillna(0)

    # 7) 오른쪽에 concat
    out = pd.concat([base_df, tmp[renamed_cols]], axis=1)
    return out


# =========================
# 2) 엑셀 다운로드 함수
# =========================
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



st.dataframe(cat_table, use_container_width=True)
st.dataframe(cat_table2, use_container_width=True)
st.dataframe(cat_table3, use_container_width=True)
st.dataframe(cat_table4, use_container_width=True)


# ------------------------------------------------------
# A) major_report_df에 merge key 만들기
# ------------------------------------------------------
mr = add_merge_keys(major_report_df, major="대분류", sub="소분류")  # merge_major/merge_sub 생성


# ------------------------------------------------------
# B) cat_table(기본) 붙이기
#    - 원가/판가/출하/회전 제거 → “잔액(분기)”만 붙임
#    - prefix는 원하는 이름으로
# ------------------------------------------------------
merged = attach_cat_table(
    base_df=mr,
    cat_df=cat_table,
    prefix="자사+제조사",                 # ✅ 여기 이름 바꾸면 컬럼명이 바뀜
    drop_mode="cost_price_only",    # 잔액만
    include_ship_cols=True
)


# ------------------------------------------------------
# C) cat_table2 붙이기 (1.38배)
#    - 원가/판가만 제거, 출하원가/출하판가 + 잔액(분기) 유지
#    - prefix: "자사_1.38배"
# ------------------------------------------------------
merged = attach_cat_table(
    base_df=merged,
    cat_df=cat_table2,
    prefix="자사+제조사1.38배",
    drop_mode="cost_price_only",
    include_ship_cols=True
)


# ------------------------------------------------------
# D) cat_table3 붙이기 (자사)
# ------------------------------------------------------
merged = attach_cat_table(
    base_df=merged,
    cat_df=cat_table3,
    prefix="자사",
    drop_mode="cost_price_only",
    include_ship_cols=True
)


# ------------------------------------------------------
# E) cat_table4 붙이기 (제조사)
# ------------------------------------------------------
merged = attach_cat_table(
    base_df=merged,
    cat_df=cat_table4,
    prefix="자사1.38배",
    drop_mode="cost_price_only",
    include_ship_cols=True
)


# ------------------------------------------------------
# F) merge 키 제거 (최종 표시/다운로드용)
# ------------------------------------------------------
merged2 = merged.drop(columns=["merge_major", "merge_sub"], errors="ignore")


# ------------------------------------------------------
# G) 1억 단위 변환 (숫자 컬럼만 / 회전 포함 컬럼 제외)
# ------------------------------------------------------
EOK = 100_000_000  # 1억원
merged2 = merged2.copy()

num_cols = merged2.select_dtypes(include="number").columns.tolist()
num_cols = [c for c in num_cols if "회전" not in c]  # 회전월/회전율 제외
merged2[num_cols] = merged2[num_cols] / EOK

# ======================================================
# (추가) merged2 대분류 사용자 지정 순서 정렬
# ======================================================
desired_order = [
    "멜라(앰플쿠션)", "멜라(앰플쿠션 外)", "매트커버팩트", "글로우커버팩트",
    "부스터샷", "원데이앰플", "시카알로에", "미국", "로즈", "포스트레이저",
    "이펙트코어", "두피앰플", "베리어", "신제품", "원료", "임가공",
    "클리어", "판촉물", "세트포장재", "기타"
]
order_map = {name: i for i, name in enumerate(desired_order)}

tmp = merged2.copy()
tmp["__major_key"] = tmp["대분류"].replace("", np.nan).ffill()

# 총계 최상단
tmp["__is_total_top"] = (tmp["__major_key"] == "총계").astype(int) * -1

# 대분류 사용자 순서
tmp["__major_sort"] = tmp["__major_key"].map(order_map).fillna(len(desired_order))

# 소분류 기타는 그룹 맨 아래
tmp["__sub_etc_last"] = (tmp["소분류"].fillna("").str.strip() == "기타").astype(int)

tmp["__row_idx"] = np.arange(len(tmp))

tmp = tmp.sort_values(
    ["__is_total_top", "__major_sort", "__major_key", "__sub_etc_last", "__row_idx"],
    ascending=[True, True, True, True, True]
)

merged2 = tmp.drop(
    columns=["__major_key", "__is_total_top", "__major_sort", "__sub_etc_last", "__row_idx"],
    errors="ignore"
)
import pandas as pd

def postprocess_mela_order_and_subtotals(
    merged2: pd.DataFrame,
    *,
    major_col="대분류",
    sub_col="소분류",
    target_major="멜라(앰플쿠션)",
    # 합계를 낼 숫자 컬럼들 (자동 탐색)
):
    df = merged2.copy()

    # 숫자 컬럼 자동 탐색 (대분류/소분류 제외)
    num_cols = df.select_dtypes("number").columns.tolist()

    # 원하는 그룹 정의 (소계 이름 + 포함 소분류)
    groups = [
        ("본품 소계(15G)", ["본품19호(15G)", "본품21호(15G)", "본품22호(15G)", "본품23호(15G)"]),
        ("본품 소계(13G)", ["본품19호(13G)", "본품21호(13G)", "본품22호(13G)", "본품23호(13G)"]),
        ("리필 소계(15G)", ["리필19호(15G)", "리필21호(15G)", "리필22호(15G)", "리필23호(15G)"]),
        ("리필 소계(13G)", ["리필19호(13G)", "리필21호(13G)", "리필22호(13G)", "리필23호(13G)"]),
        ("미니 소계", ["19호(미니)", "21호(미니)", "22호(미니)", "23호(미니)"]),
    ]

    # 멜라만 분리
    mel = df[df[major_col].astype(str).str.strip() == target_major].copy()
    other = df[df[major_col].astype(str).str.strip() != target_major].copy()

    # 공백/타입 정리
    mel[major_col] = mel[major_col].astype(str).str.strip()
    mel[sub_col] = mel[sub_col].astype(str).str.strip()

    # 소계/정렬용 결과를 쌓을 리스트
    out_parts = []

    # 그룹별로 "상세 + 소계행" 순서대로 쌓기
    for subtotal_name, items in groups:
        block = mel[mel[sub_col].isin(items)].copy()

        # 상세가 하나도 없으면 스킵
        if block.empty:
            continue

        out_parts.append(block)

        # 소계 행 만들기
        subtotal_row = {major_col: target_major, sub_col: subtotal_name}
        for c in num_cols:
            subtotal_row[c] = float(block[c].sum())

        out_parts.append(pd.DataFrame([subtotal_row]))

    # (선택) 그룹에 포함되지 않은 나머지 소분류도 뒤에 붙이기
    grouped_items = set(x for _, items in groups for x in items)
    rest = mel[~mel[sub_col].isin(grouped_items)].copy()
    if not rest.empty:
        out_parts.append(rest)

    mel_new = pd.concat(out_parts, ignore_index=True)

    # 최종 합치기 (기존 순서를 유지하려면 other를 그대로 앞/뒤에 붙이면 됨)
    # 여기서는 "총계" 같은 특수행이 있으면 맨 위 유지하는게 보통이라 분리 처리
    if (df[major_col] == "총계").any():
        top = df[df[major_col] == "총계"].copy()
        middle = pd.concat([other[other[major_col] != "총계"], mel_new], ignore_index=True)
        result = pd.concat([top, middle], ignore_index=True)
    else:
        result = pd.concat([other, mel_new], ignore_index=True)

    return result

final = postprocess_mela_order_and_subtotals(merged2, major_col="대분류", sub_col="소분류")

# ------------------------------------------------------
# H) 화면 표시 + 엑셀 다운로드
# ------------------------------------------------------
st.subheader("📌 디엔코스메틱스 보유재고 운영 시뮬레이션 보고")
st.dataframe(merged2, use_container_width=True,height = 1000)

download_excel_openpyxl(
    merged2,
    filename="디엔코스메틱스 보유재고 운영 시뮬레이션 보고.xlsx",
    sheet_name="MergedReport"
)

