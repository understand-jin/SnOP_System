"""
upload_to_firestore.py
======================
S&OP 데이터를 Firestore에 업로드하는 Python 스크립트.

현재 로컬에 저장된 CSV 파일들을 읽어 Firestore에 연도/월 구조로 저장합니다.

Firestore 구조:
  reports/
    {YYYY_MM}/                     (e.g. "2025_12")
      year, month, processedAt
      [sub-collections]
        aging_inventory/   <- aging_inventory_preprocess 결과
        simulation_detail/ <- simulate_batches_by_product detail_df
        forecasted/        <- binary_search 결과 (updated_df)
        stockout/          <- Stockout.csv (품절 리스크)

사용법:
  # 서비스 계정 키 파일 준비 (Firebase Console > 프로젝트 설정 > 서비스 계정)
  # 'serviceAccountKey.json' 이름으로 저장

  # 로컬 CSV 파일에서 업로드:
  python upload_to_firestore.py --year 2025 --month 12

  # 특정 데이터 디렉토리 지정:
  python upload_to_firestore.py --year 2025 --month 12 --base-dir "C:/path/to/SnOPWeb"

  # 서비스 계정 파일 경로 지정:
  python upload_to_firestore.py --year 2025 --month 12 --sa "path/to/serviceAccountKey.json"
"""

import argparse
import sys
import os
import io
from pathlib import Path

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("ERROR: firebase-admin 패키지가 설치되지 않았습니다.")
    print("실행: pip install firebase-admin")
    sys.exit(1)

# ── Configuration ────────────────────────────────────────────
BATCH_SIZE = 400  # Firestore batch limit is 500


# ── Firebase Init ────────────────────────────────────────────
def init_firebase(service_account_path: str):
    if not firebase_admin._apps:
        sa_path = Path(service_account_path)
        if not sa_path.exists():
            print(f"ERROR: 서비스 계정 파일을 찾을 수 없습니다: {sa_path}")
            print("Firebase Console > 프로젝트 설정 > 서비스 계정 > 새 비공개 키 생성")
            sys.exit(1)
        cred = credentials.Certificate(str(sa_path))
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Data Cleaning ────────────────────────────────────────────
def clean_for_firestore(record: dict) -> dict:
    """Firestore에 저장 가능한 형태로 데이터 정제 (NaN, Inf, Timestamp 등 처리)"""
    clean = {}
    for k, v in record.items():
        key = str(k)
        if v is None:
            clean[key] = None
        elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            clean[key] = None
        elif isinstance(v, (np.integer,)):
            clean[key] = int(v)
        elif isinstance(v, (np.floating,)):
            clean[key] = float(v)
        elif isinstance(v, pd.Timestamp):
            clean[key] = v.isoformat() if not pd.isna(v) else None
        elif hasattr(v, 'isoformat'):
            clean[key] = v.isoformat()
        elif isinstance(v, str) and v in ('nan', 'NaT', 'None', 'null', 'NaN'):
            clean[key] = None
        else:
            clean[key] = v
    return clean


# ── Core Upload Function ──────────────────────────────────────
def upload_dataframe(
    db,
    year: str,
    month: str,
    subcollection: str,
    df: pd.DataFrame,
    id_cols: list = None,
    overwrite: bool = True
):
    """DataFrame을 Firestore 하위 컬렉션에 업로드"""
    doc_id  = f"{year}_{month.zfill(2)}"
    col_ref = db.collection('reports').document(doc_id).collection(subcollection)

    records = df.to_dict(orient='records')
    total   = len(records)

    if total == 0:
        print(f"  ⚠ {subcollection}: 업로드할 데이터가 없습니다.")
        return 0

    # 기존 문서 삭제 (overwrite 모드)
    if overwrite:
        existing = col_ref.limit(500).get()
        if existing:
            delete_batch = db.batch()
            for doc in existing:
                delete_batch.delete(doc.reference)
            delete_batch.commit()

    batch   = db.batch()
    count   = 0
    written = 0

    for i, record in enumerate(records):
        clean_record = clean_for_firestore(record)

        # 문서 ID 생성
        if id_cols:
            parts   = [str(clean_record.get(c, '')) for c in id_cols if c in clean_record]
            doc_key = '_'.join(parts) + f'_{i}'
        else:
            doc_key = str(i)

        # Firestore 허용 문자로 변환 (슬래시, 마침표 등 제거)
        doc_key = doc_key.replace('/', '_').replace('.', '').replace(' ', '_')[:150]
        if not doc_key or doc_key.startswith('_'):
            doc_key = f'doc_{i}'

        batch.set(col_ref.document(doc_key), clean_record)
        count   += 1
        written += 1

        if count >= BATCH_SIZE:
            batch.commit()
            batch = db.batch()
            count = 0
            print(f"    {written}/{total} 업로드 중...")

    if count > 0:
        batch.commit()

    print(f"  ✅ {subcollection}: {total}건 업로드 완료")
    return total


# ── Main Upload Logic ─────────────────────────────────────────
def upload_from_local_csvs(db, year: str, month: str, base_dir: Path):
    """
    로컬에 저장된 CSV 파일들을 읽어 Firestore에 업로드.

    7_Aging_Stock.py 저장 경로:
      data/{year}년/{month}월/inventory.csv         -> aging_inventory
      data/{year}년/{month}월/simulation.csv        -> simulation_detail
      data/{year}년/{month}월/forecasted_inventory.csv -> forecasted

    utils.py (load_stockout_csv) 저장 경로:
      Datas/{year}년/{month}월/Stockout.csv         -> stockout
      Datas/{year}년/{month}월/Stock.csv            -> (참고용)
    """
    doc_id   = f"{year}_{month.zfill(2)}"
    year_str  = f"{year}년"
    month_str = f"{month}월"

    print(f"\n📦 {year_str} {month_str} 데이터 Firestore 업로드 시작...")
    print(f"  Document ID: reports/{doc_id}")

    # 메타데이터 저장
    db.collection('reports').document(doc_id).set({
        'year':         year_str,
        'month':        month_str,
        'yearNum':      int(year),
        'monthNum':     int(month),
        'processedAt':  firestore.SERVER_TIMESTAMP,
        'uploadedBy':   'upload_to_firestore.py'
    })
    print(f"  ✅ 메타데이터 저장 완료")

    uploaded_any = False

    # 1. aging_inventory (inventory.csv)
    for candidates in [
        base_dir / 'data' / year_str / month_str / 'inventory.csv',
        base_dir / 'data' / year_str / month_str / 'aging_inventory.csv',
    ]:
        if candidates.exists():
            print(f"\n  📂 aging_inventory 로드: {candidates}")
            df = pd.read_csv(candidates, encoding='utf-8-sig')
            upload_dataframe(db, year, month, 'aging_inventory', df, id_cols=['자재코드', '배치'])
            uploaded_any = True
            break
    else:
        print(f"  ⚠ aging_inventory CSV 없음 (data/{year_str}/{month_str}/inventory.csv)")

    # 2. simulation_detail (simulation.csv)
    for candidates in [
        base_dir / 'data' / year_str / month_str / 'simulation.csv',
        base_dir / 'data' / year_str / month_str / 'detail_df.csv',
    ]:
        if candidates.exists():
            print(f"\n  📂 simulation_detail 로드: {candidates}")
            df = pd.read_csv(candidates, encoding='utf-8-sig')
            upload_dataframe(db, year, month, 'simulation_detail', df, id_cols=['자재코드', '배치'])
            uploaded_any = True
            break
    else:
        print(f"  ⚠ simulation CSV 없음 (data/{year_str}/{month_str}/simulation.csv)")

    # 3. forecasted (forecasted_inventory.csv)
    for candidates in [
        base_dir / 'data' / year_str / month_str / 'forecasted_inventory.csv',
        base_dir / 'data' / year_str / month_str / 'forecasted.csv',
    ]:
        if candidates.exists():
            print(f"\n  📂 forecasted 로드: {candidates}")
            df = pd.read_csv(candidates, encoding='utf-8-sig')
            upload_dataframe(db, year, month, 'forecasted', df, id_cols=['자재코드', '배치'])
            uploaded_any = True
            break
    else:
        print(f"  ⚠ forecasted CSV 없음 (data/{year_str}/{month_str}/forecasted_inventory.csv)")

    # 4. stockout (Stockout.csv from Datas/)
    for candidates in [
        base_dir / 'Datas' / year_str / month_str / 'Stockout.csv',
        base_dir / 'data'  / year_str / month_str / 'Stockout.csv',
    ]:
        if candidates.exists():
            print(f"\n  📂 stockout 로드: {candidates}")
            df = pd.read_csv(candidates, encoding='utf-8-sig')
            upload_dataframe(db, year, month, 'stockout', df, id_cols=['자재'])
            uploaded_any = True
            break
    else:
        print(f"  ⚠ Stockout CSV 없음 (Datas/{year_str}/{month_str}/Stockout.csv)")

    if not uploaded_any:
        print(f"\n⚠ 업로드된 파일이 없습니다. 경로를 확인하세요.")
        print(f"  현재 base_dir: {base_dir.resolve()}")
    else:
        print(f"\n🎉 {year_str} {month_str} 업로드 완료! (Firestore: reports/{doc_id})")


# ── Process & Upload (Excel 파일에서 직접 처리) ──────────────
def process_and_upload(db, year: str, month: str, excel_files: dict):
    """
    5개 Excel 파일을 직접 처리하여 Firestore에 업로드.
    excel_files: { 'cost': path, 'standard': path, 'expiration': path, 'sales': path, 'cls': path }
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from inventory_utils2 import (
        aging_inventory_preprocess,
        simulate_batches_by_product,
        binary_search
    )
    from utils import read_excel_with_smart_header, preprocess_df

    print(f"\n🔧 {year}년 {month}월 데이터 전처리 시작...")

    def load_excel(path):
        with open(path, 'rb') as f:
            raw = f.read()
        try:
            return preprocess_df(read_excel_with_smart_header(raw, scan_rows=80))
        except Exception as e:
            print(f"  경고: 스마트 헤더 탐지 실패 ({e}), 기본 로드 시도...")
            import io
            return pd.read_excel(io.BytesIO(raw))

    cost_df       = load_excel(excel_files['cost'])
    standard_df   = load_excel(excel_files['standard'])
    expiration_df = load_excel(excel_files['expiration'])
    sales_df      = load_excel(excel_files['sales'])
    cls_df        = load_excel(excel_files['cls'])

    year_str  = f"{year}년"
    month_str = f"{month}월"

    print("  ▶ aging_inventory_preprocess 실행 중...")
    aging_df = aging_inventory_preprocess(
        cost_df=cost_df,
        standard_df=standard_df,
        expiration_df=expiration_df,
        sales_df=sales_df,
        cls_df=cls_df,
        year_str=year_str,
        month_str=month_str
    )
    print(f"  ✅ 전처리 완료: {len(aging_df):,}행")

    print("  ▶ FEFO 시뮬레이션 실행 중...")
    detail_df, updated_df = simulate_batches_by_product(aging_df)
    print(f"  ✅ 시뮬레이션 완료: detail {len(detail_df):,}건")

    print("  ▶ 판매개선율 탐색 중 (시간 소요)...")
    forecasted_df = binary_search(aging_df, updated_df)
    print(f"  ✅ 이진탐색 완료")

    # Firestore 업로드
    doc_id = f"{year}_{month.zfill(2)}"
    db.collection('reports').document(doc_id).set({
        'year':        year_str,
        'month':       month_str,
        'yearNum':     int(year),
        'monthNum':    int(month),
        'processedAt': firestore.SERVER_TIMESTAMP,
        'uploadedBy':  'upload_to_firestore.py (process_mode)'
    })

    upload_dataframe(db, year, month, 'aging_inventory',   aging_df,      id_cols=['자재코드', '배치'])
    upload_dataframe(db, year, month, 'simulation_detail', detail_df,     id_cols=['자재코드', '배치'])
    upload_dataframe(db, year, month, 'forecasted',        forecasted_df, id_cols=['자재코드', '배치'])

    print(f"\n🎉 처리 및 업로드 완료! (reports/{doc_id})")


# ── CLI ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='S&OP 데이터를 Firestore에 업로드합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 로컬 CSV에서 업로드 (가장 일반적인 사용법)
  python upload_to_firestore.py --year 2025 --month 12

  # 서비스 계정 파일 직접 지정
  python upload_to_firestore.py --year 2025 --month 12 --sa path/to/key.json

  # 다른 디렉토리의 CSV 파일 업로드
  python upload_to_firestore.py --year 2025 --month 12 --base-dir "D:/SnOPWeb"
        """
    )
    parser.add_argument('--year',     required=True, help='연도 (예: 2025)')
    parser.add_argument('--month',    required=True, help='월 (예: 12)')
    parser.add_argument('--sa',       default='serviceAccountKey.json',
                        help='Firebase 서비스 계정 JSON 파일 경로 (기본: serviceAccountKey.json)')
    parser.add_argument('--base-dir', default=None,
                        help='데이터 루트 디렉토리 (기본: 스크립트 상위 폴더)')
    parser.add_argument('--mode',     choices=['csv', 'process'], default='csv',
                        help='csv: 기존 CSV 파일 업로드 / process: Excel 직접 처리 후 업로드')

    args = parser.parse_args()

    # Base dir 결정
    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        # 스크립트 위치 기준으로 상위 폴더 (프로젝트 루트)
        script_dir = Path(__file__).parent
        base_dir   = script_dir.parent
        if not (base_dir / 'data').exists() and not (base_dir / 'Datas').exists():
            base_dir = Path('.')
            print(f"  경고: data/ 또는 Datas/ 폴더를 찾지 못했습니다. 현재 디렉토리를 기준으로 합니다: {base_dir.resolve()}")

    print("=" * 60)
    print("  S&OP Firestore Uploader")
    print("=" * 60)
    print(f"  대상:     {args.year}년 {args.month}월")
    print(f"  서비스 계정: {args.sa}")
    print(f"  기준 경로: {base_dir.resolve()}")
    print(f"  모드:     {args.mode}")
    print("=" * 60)

    db = init_firebase(args.sa)

    if args.mode == 'csv':
        upload_from_local_csvs(db, args.year, args.month, base_dir)
    elif args.mode == 'process':
        print("\n⚠ process 모드: Excel 파일 경로를 코드에 직접 지정하거나 대화형으로 입력하세요.")
        excel_files = {}
        file_labels = {
            'cost':       '자재수불부 (Cost)',
            'standard':   '재고개요 (Standard)',
            'expiration': '배치별유효기한 (Expiry)',
            'sales':      '3개월매출 (Sales)',
            'cls':        '대분류_소분류 (Classification)'
        }
        for key, label in file_labels.items():
            path = input(f"  {label} 파일 경로: ").strip().strip('"')
            if not Path(path).exists():
                print(f"ERROR: 파일 없음 - {path}")
                sys.exit(1)
            excel_files[key] = path
        process_and_upload(db, args.year, args.month, excel_files)


if __name__ == '__main__':
    main()
