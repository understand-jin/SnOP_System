import io
import re
from wsgiref import headers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import os
from pathlib import Path

# -----------------------------
# 공통 전처리(값/컬럼명 정리)
# -----------------------------
def preprocess_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]

    obj_cols = df.select_dtypes(include=["object"]).columns
    for c in obj_cols:
        df[c] = df[c].astype(str).str.strip()

    for c in df.columns:
        if df[c].dtype == "object":
            s = df[c].str.replace(",", "", regex=False)
            numeric = pd.to_numeric(s, errors="coerce")
            if numeric.notna().mean() >= 0.7:
                df[c] = numeric

    df = df.dropna(how="all").dropna(axis=1, how="all")
    return df


# -----------------------------
# 헤더 자동 보정
# -----------------------------
def clean_header_row(header_list):
    s = pd.Series(header_list, dtype="object")

    def norm(x):
        if pd.isna(x):
            return None
        x = re.sub(r"\s+", " ", str(x)).strip()
        if x in ("", "nan", "None"):
            return None
        return x

    s = s.map(norm).ffill()

    cols = []
    for i, v in enumerate(s.tolist()):
        cols.append(v if v else f"col_{i}")

    out, seen = [], {}
    for c in cols:
        if c in seen:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            out.append(c)
    return out


def combine_two_header_rows(h1, h2):
    h1 = pd.Series(h1, dtype="object")
    h2 = pd.Series(h2, dtype="object")

    def norm(x):
        if pd.isna(x):
            return None
        x = re.sub(r"\s+", " ", str(x)).strip()
        if x in ("", "nan", "None"):
            return None
        return x

    h1 = h1.map(norm).ffill()
    h2 = h2.map(norm)

    merged = []
    for i in range(len(h1)):
        a = h1.iloc[i]
        b = h2.iloc[i]
        if a and b:
            merged.append(f"{a}_{b}")
        elif b:
            merged.append(b)
        elif a:
            merged.append(a)
        else:
            merged.append(f"col_{i}")

    return clean_header_row(merged)


def should_use_two_header(raw: pd.DataFrame, header_r: int) -> bool:
    if header_r + 1 >= len(raw):
        return False
    r2 = raw.iloc[header_r + 1].astype(str)
    r2_num = pd.to_numeric(r2.str.replace(",", "", regex=False), errors="coerce").notna().mean()
    r2_text = (~r2.str.match(r"^\s*$")).mean()
    r2_blank = (r2.str.strip().isin(["", "nan", "None"])).mean()
    return (r2_num < 0.6) and (r2_text > 0.3) and (r2_blank > 0.05)


# -----------------------------
# 표 블록 자동 추출
# -----------------------------
def score_header_row(raw: pd.DataFrame, r: int) -> float:
    row = raw.iloc[r]
    non_na = row.notna().mean()
    as_str = row.astype(str)
    textish = (~as_str.str.match(r"^\s*$")).mean()
    numericish = pd.to_numeric(as_str.str.replace(",", "", regex=False), errors="coerce").notna().mean()

    score = non_na * 2.5 + textish * 2.0 - numericish * 1.5
    if row.notna().sum() <= 2:
        score -= 2.0
    return score


def extract_block(raw: pd.DataFrame, header_r: int, auto_header_fix: bool = True):
    if auto_header_fix and should_use_two_header(raw, header_r):
        cols = combine_two_header_rows(raw.iloc[header_r].tolist(), raw.iloc[header_r + 1].tolist())
        body = raw.iloc[header_r + 2:].copy()
    else:
        cols = clean_header_row(raw.iloc[header_r].tolist())
        body = raw.iloc[header_r + 1:].copy()

    body.columns = cols
    body = body.dropna(axis=1, how="all")

    fill_ratio = body.notna().mean(axis=1)
    is_data = fill_ratio >= 0.2
    if not is_data.any():
        return None

    start = int(np.argmax(is_data.values))
    end = start
    blank_streak = 0
    for i in range(start, len(body)):
        if is_data.iloc[i]:
            end = i
            blank_streak = 0
        else:
            blank_streak += 1
            if blank_streak >= 3:
                break

    df = body.iloc[start:end + 1].copy().dropna(how="all")
    if df.shape[0] < 2 or df.shape[1] < 2:
        return None
    return df


import io
import pandas as pd

def extract_table_any_excel(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    - 엑셀의 첫 번째 시트만 읽는다
    - 첫 번째 행(1행)을 무조건 헤더로 사용한다
    - 완전 빈 행/열 제거
    """
    bio = io.BytesIO(file_bytes)
    engine = "xlrd" if filename.lower().endswith(".xls") else "openpyxl"

    df = pd.read_excel(
        bio,
        sheet_name=0,   # 첫 번째 시트
        header=0,       # 첫 번째 행 = 헤더
        engine=engine
    )

    # 완전히 빈 행/열 제거
    df = df.dropna(how="all").dropna(axis=1, how="all")

    if df.empty or df.shape[1] < 2:
        raise ValueError("첫 번째 시트에서 유효한 테이블을 찾지 못했습니다.")

    return df

# -----------------------------
# CSV 인코딩 안전 로더
# -----------------------------
def load_csv_any_encoding(file_bytes: bytes) -> pd.DataFrame:
    bio = io.BytesIO(file_bytes)
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            bio.seek(0)
            return pd.read_csv(bio, encoding=enc)
        except Exception:
            pass
    bio.seek(0)
    return pd.read_csv(bio, encoding_errors="ignore")


# -----------------------------
# MIME/HTML 기반 "가짜 .xls" HTML 테이블 fallback
# -----------------------------
def parse_html_tables(file_bytes: bytes) -> pd.DataFrame:
    text = None
    # 1. 인코딩 시도
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            text = file_bytes.decode(enc, errors="ignore")
            if text and text.strip():
                break
        except Exception:
            pass

    if not text:
        raise ValueError("텍스트로 디코딩이 불가합니다.")

    soup = BeautifulSoup(text, 'html.parser')
    table = soup.find('table')
    if not table:
        raise ValueError("HTML 테이블을 찾지 못했습니다.")

    rows = table.find_all('tr')
    
    def safe_int(val, default=1):
        try:
            if val is None: return default
            s_val = str(val).strip().replace('"', '').replace("'", "")
            return int(s_val) if s_val else default
        except (ValueError, TypeError):
            return default

    # [수정] 2. 실제 필요한 최대 열 개수를 더 정확하게 파악
    num_rows = len(rows)
    num_cols = 0
    for row in rows:
        cells = row.find_all(['td', 'th'])
        current_row_width = 0
        for c in cells:
            current_row_width += safe_int(c.get('colspan'))
        if current_row_width > num_cols:
            num_cols = current_row_width

    # 3. 빈 격자 생성
    grid = [[None for _ in range(num_cols)] for _ in range(num_rows)]

    # 4. 데이터 채우기
    for r_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        curr_col = 0
        for cell in cells:
            # 이미 채워진 칸(rowspan 영향) 건너뛰기
            while curr_col < num_cols and grid[r_idx][curr_col] is not None:
                curr_col += 1
            
            if curr_col >= num_cols:
                break

            val = cell.get_text(strip=True)
            row_span = safe_int(cell.get('rowspan'))
            col_span = safe_int(cell.get('colspan'))
            
            # 격자 범위를 벗어나지 않도록 안전하게 채우기
            for r in range(r_idx, min(r_idx + row_span, num_rows)):
                for c in range(curr_col, min(curr_col + col_span, num_cols)):
                    grid[r][c] = val
            
            curr_col += col_span

    df = pd.DataFrame(grid)

    # [추가] 5. 이미지처럼 상단에 불필요한 정보가 있는 경우 처리
    # 유효한 데이터가 시작되는 지점(예: '관리회계 영역' 이 포함된 행)을 찾습니다.
    # 만약 clean_header_row 함수를 쓰신다면, 그 함수가 이 "진짜 헤더"를 찾도록 설계되어야 합니다.
    
    # 임시 해결책: 첫 번째 행에 'None'이 너무 많으면 진짜 헤더가 나올 때까지 행을 버림
    while len(df) > 0 and df.iloc[0].isna().sum() > (len(df.columns) * 0.5):
        df = df.iloc[1:].reset_index(drop=True)

    if not df.empty:
        # 기존에 사용하시던 헤더 정리 로직 적용
        df.columns = clean_header_row(df.iloc[0].tolist())
        df = df.drop(df.index[0]).reset_index(drop=True)

    return df



# -----------------------------
# 컬럼 작동 인식
# -----------------------------
def read_excel_with_smart_header(file_bytes: bytes, sheet_name=None, scan_rows: int = 60) -> pd.DataFrame:
    """
    엑셀의 헤더 행(컬럼 행)을 범용적으로 자동 탐지하여 DataFrame 생성
    - 키워드 기반 + 통계 기반(숫자비율/빈칸/중복/텍스트비율) 혼합
    - SAP/보고서형 엑셀(상단 공백/제목/병합셀)에도 비교적 강함
    """
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=None)
    raw = raw.iloc[:scan_rows].copy()

    def _cell_str(x):
        if pd.isna(x):
            return ""
        return str(x).strip()

    def _is_number_like(s: str) -> bool:
        if s == "":
            return False
        try:
            float(s.replace(",", ""))
            return True
        except:
            return False

    # (선택) 자주 나오는 컬럼명 키워드(있으면 가점)
    header_keywords = [
        "자재", "자재코드", "자재 내역", "자재내역", "자재명",
        "대분류", "소분류", "유효", "기말", "재고", "수량", "금액",
        "판매", "평판", "단가", "원가율", "코드"
    ]

    best_idx = None
    best_score = -1e18

    for i in range(len(raw)):
        row = raw.iloc[i].tolist()
        cells = [_cell_str(x) for x in row]

        non_empty = [c for c in cells if c != ""]
        if len(non_empty) < 2:
            continue

        # 통계 지표들
        n = len(cells)
        non_empty_ratio = len(non_empty) / max(n, 1)

        num_like = sum(_is_number_like(c) for c in non_empty)
        num_ratio = num_like / max(len(non_empty), 1)

        uniq_ratio = len(set(non_empty)) / max(len(non_empty), 1)

        # 텍스트 길이(헤더는 보통 짧음)
        avg_len = np.mean([len(c) for c in non_empty]) if non_empty else 0

        # 키워드 포함 가점
        kw_hits = sum(any(k in c for k in header_keywords) for c in non_empty)

        # 점수 설계(헤더일수록: 적당히 채워짐, 숫자 적음, 중복 적음, 텍스트 짧음, 키워드 많음)
        score = 0
        score += non_empty_ratio * 3.0
        score += (1 - num_ratio) * 4.0
        score += uniq_ratio * 2.0
        score += max(0, (20 - avg_len) / 20) * 1.0
        score += kw_hits * 2.5

        # “자재/코드/명” 같은 강력 신호 있으면 추가 가점
        strong = any(("자재" in c or "코드" in c) for c in non_empty)
        if strong:
            score += 1.5

        if score > best_score:
            best_score = score
            best_idx = i

    if best_idx is None:
        raise ValueError("❌ 헤더 행을 자동으로 찾지 못했습니다. (scan_rows를 늘려보세요)")

    # best_idx를 header로 재로딩
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=best_idx)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]  # 컬럼명 정리

    # 이름 없는 컬럼 제거(전부 NaN인 열 등)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]

    return df


BASE_DATA_DIR = Path("Datas")   # 로컬에 Datas 폴더 기준

def get_stock_csv_path(year: str, month: str) -> Path:
    # month가 "1월" 이런 형태면 폴더명 그대로 쓰고, 숫자만 쓰고 싶으면 여기서 가공 가능
    return BASE_DATA_DIR / str(year) / str(month) / "Stock.csv"

def save_stock_csv(df: pd.DataFrame, year: str, month: str) -> Path:
    p = get_stock_csv_path(year, month)
    p.parent.mkdir(parents=True, exist_ok=True)  # ✅ 연도/월 폴더 자동 생성
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p

def load_stock_csv(year: str, month: str) -> pd.DataFrame:
    p = get_stock_csv_path(year, month)
    return pd.read_csv(p, encoding="utf-8-sig")
