import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="S&OP System - 재고 시뮬레이션", layout="wide")
st.title("🧪 재고 시뮬레이션 - 분류 매핑(자재코드 기준)")

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

if INV_FILE not in files_dict:
    st.error(f"❌ {INV_FILE} 파일이 {sel_year} {sel_month}에 없습니다.")
    st.write("현재 파일 목록:", list(files_dict.keys()))
    st.stop()

if CLS_FILE not in files_dict:
    st.error(f"❌ {CLS_FILE} 파일이 {sel_year} {sel_month}에 없습니다.")
    st.write("현재 파일 목록:", list(files_dict.keys()))
    st.stop()

# ======================================================
# 3) 멀티시트 대응 (첫 시트 사용)
# ======================================================
def pick_df(obj):
    if isinstance(obj, dict):
        return obj[list(obj.keys())[0]]
    return obj

inv_df = pick_df(files_dict[INV_FILE]).copy()
cls_df = pick_df(files_dict[CLS_FILE]).copy()

# --------------------------------------------------
# 🔥 [즉시 정리] 자재내역에 '용역비' 또는 '배송비' 포함된 행 제거
# --------------------------------------------------
INV_ITEM_CANDS = ["자재 내역", "자재내역", "자재명", "자재 명"]

inv_item_col = next((c for c in INV_ITEM_CANDS if c in inv_df.columns), None)

if inv_item_col is not None:
    inv_df = inv_df[
        ~inv_df[inv_item_col].astype(str).str.contains("용역비|배송비", na=False)
    ].copy()

# ======================================================
# 3-1) 12월 기말 재고: 불필요 컬럼 제거
# ======================================================
DROP_COLS = ["평가 유형", "플랜트", "저장위치", "특별재고"]
inv_df = inv_df.drop(columns=[c for c in DROP_COLS if c in inv_df.columns], errors="ignore")

# ======================================================
# 4) ✅ 매핑 키 컬럼 찾기 + 숫자 코드로 통일
#    - 기말 재고 '자재' ↔ 기준정보 '자재코드'
# ======================================================
INV_CODE_COL = "자재"
CLS_CODE_COL = "자재코드"

if INV_CODE_COL not in inv_df.columns:
    st.error(f"❌ 기말 재고 파일에 '{INV_CODE_COL}' 컬럼이 없습니다.")
    st.write("inv_df 컬럼:", list(inv_df.columns))
    st.stop()

if CLS_CODE_COL not in cls_df.columns:
    st.error(f"❌ 기준정보 파일에 '{CLS_CODE_COL}' 컬럼이 없습니다.")
    st.write("cls_df 컬럼:", list(cls_df.columns))
    st.stop()

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

inv_df["_mat_key"] = normalize_code_to_int_string(inv_df[INV_CODE_COL])
cls_df["_mat_key"] = normalize_code_to_int_string(cls_df[CLS_CODE_COL])

# ======================================================
# 5) ✅ 기준정보 + 추가_분류에서 가져올 컬럼 준비 (대분류/소분류)
#    우선순위: 기준정보 → (없을 때만) 추가_분류 → 미분류
# ======================================================
ADD_FILE = "추가_분류_Sheet1.xlsx"

# --- (1) 기준정보: 자재코드 기준으로 매핑 테이블 만들기
for col in ["대분류", "소분류"]:
    if col not in cls_df.columns:
        st.error(f"❌ 기준정보 파일에 '{col}' 컬럼이 없습니다.")
        st.write("기준정보 컬럼:", list(cls_df.columns))
        st.stop()

cls_small = (
    cls_df[["_mat_key", "대분류", "소분류"]]
    .dropna(subset=["_mat_key"])
    .drop_duplicates(subset=["_mat_key"])
)

# --- (2) 추가_분류: (있으면) 자재 기준으로 매핑 테이블 만들기
add_small = None
if ADD_FILE in files_dict:
    add_df = pick_df(files_dict[ADD_FILE]).copy()

    if "자재" not in add_df.columns:
        st.error("❌ 추가_분류.xlsx에 '자재' 컬럼이 없습니다.")
        st.write("추가_분류 컬럼:", list(add_df.columns))
        st.stop()

    for col in ["대분류", "소분류"]:
        if col not in add_df.columns:
            st.error(f"❌ 추가_분류.xlsx에 '{col}' 컬럼이 없습니다.")
            st.write("추가_분류 컬럼:", list(add_df.columns))
            st.stop()

    # 추가_분류도 동일하게 정규화 키 생성
    add_df["_mat_key"] = normalize_code_to_int_string(add_df["자재"])

    add_small = (
        add_df[["_mat_key", "대분류", "소분류"]]
        .dropna(subset=["_mat_key"])
        .drop_duplicates(subset=["_mat_key"])
    )
else:
    st.info("ℹ️ 추가_분류.xlsx가 없어 기준정보 매핑만 수행합니다.")

# ======================================================
# 6) ✅ Merge: 기준정보 먼저 붙이고, 부족한 값만 추가_분류로 채움
# ======================================================

# (1) 기준정보 merge → mapped_df에 대분류/소분류가 생김(없으면 NaN)
mapped_df = inv_df.merge(cls_small, on="_mat_key", how="left")

# (2) 기준정보에서 비어있는(=NaN) 행만 추가_분류로 채우기
if add_small is not None:
    # 추가_분류를 임시 컬럼명으로 merge해서 가져오기
    mapped_df = mapped_df.merge(
        add_small.rename(columns={"대분류": "_대분류_add", "소분류": "_소분류_add"}),
        on="_mat_key",
        how="left"
    )

    # ✅ 기준정보 값이 없을 때만(add)로 채움
    mapped_df["대분류"] = mapped_df["대분류"].combine_first(mapped_df["_대분류_add"])
    mapped_df["소분류"] = mapped_df["소분류"].combine_first(mapped_df["_소분류_add"])

    # 임시 컬럼 제거
    mapped_df = mapped_df.drop(columns=["_대분류_add", "_소분류_add"], errors="ignore")

# (3) 둘 다 없으면 미분류 처리
mapped_df["대분류"] = mapped_df["대분류"].fillna("미분류")
mapped_df["소분류"] = mapped_df["소분류"].fillna("미분류")



# ======================================================
# 7) ✅ 보기 좋게 컬럼 순서 정렬 (자재 옆에 대분류/소분류)
# ======================================================
base_cols = []
if "자재" in mapped_df.columns:
    base_cols.append("자재")
if "자재 내역" in mapped_df.columns:
    base_cols.append("자재 내역")
if "자재내역" in mapped_df.columns:
    base_cols.append("자재내역")

front_cols = [c for c in base_cols if c in mapped_df.columns] + ["대분류", "소분류"]
rest_cols = [c for c in mapped_df.columns if c not in (front_cols + ["_mat_key"])]

view_df = mapped_df[front_cols + rest_cols]

# ======================================================
# 8) ✅ 결과 DF 보여주기
# ======================================================
st.subheader("✅ 자재(기말재고) ↔ 자재코드(기준정보) 매핑 결과")
st.dataframe(view_df, use_container_width=True)

with st.expander("⚠️ 미분류 항목만 보기"):
    st.dataframe(
        view_df[(view_df["대분류"] == "미분류") | (view_df["소분류"] == "미분류")],
        use_container_width=True
    )

# ======================================================
# 9) ✅ 미분류 품목 엑셀 다운로드 (자재 내역 중복 제거)
# ======================================================
st.divider()
st.subheader("⬇️ 미분류 품목 엑셀 다운로드 (중복 제거)")

miss_base = mapped_df[
    (mapped_df["대분류"] == "미분류") | (mapped_df["소분류"] == "미분류")
].copy()

if miss_base.empty:
    st.info("미분류 품목이 없습니다.")
else:
    # 자재 내역 컬럼 찾기 (없으면 자재코드 기준으로라도 가능)
    name_candidates = ["자재내역", "자재 내역", "자재명", "자재 명"]
    name_col = next((c for c in name_candidates if c in miss_base.columns), None)

    if name_col is None:
        st.warning("⚠️ '자재 내역' 컬럼이 없어 자재코드 기준으로 중복 제거합니다.")
        miss_base["_dedup_key"] = miss_base["_mat_key"]
        out_cols = ["자재", "_mat_key", "대분류", "소분류"]
    else:
        miss_base["_dedup_key"] = miss_base[name_col].astype(str).str.strip()
        out_cols = ["자재", name_col, "대분류", "소분류"]

    # 중복 제거
    download_df = miss_base.drop_duplicates(subset=["_dedup_key"]).copy()

    # 기말 수량/금액 있으면 같이 포함
    extra_cols = []
    for c in ["기말 재고 수량", "기말 재고 금액", "재고수량", "재고금액", "기말수량", "기말금액"]:
        if c in download_df.columns and c not in out_cols:
            extra_cols.append(c)
    download_df = download_df[out_cols + extra_cols]

    # 컬럼명 정리
    rename_map = {"_mat_key": "자재코드(정규화)"}
    if name_col:
        rename_map[name_col] = "자재 내역"
    download_df = download_df.rename(columns=rename_map)

    st.dataframe(download_df, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        download_df.to_excel(writer, index=False, sheet_name="미분류")
    buffer.seek(0)

    filename = f"미분류_품목_중복제거_{sel_year}_{sel_month}.xlsx"
    st.download_button(
        label="📥 미분류 품목 엑셀 다운로드 (중복 제거)",
        data=buffer,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
