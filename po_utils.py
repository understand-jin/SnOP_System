import pandas as pd
import glob
import os
from sap_download import download_stockout_prediction, download_inventory_overview
from datetime import datetime
from inventory_utils2 import filter_special_stock


BASE = os.path.dirname(os.path.abspath(__file__))

def latest_file(folder):
    """폴더 안에서 가장 최근 수정된 xlsx 파일 경로 반환"""
    files = [f for f in glob.glob(os.path.join(BASE, folder, "*.xlsx"))
             if not os.path.basename(f).startswith("~$")]
    if not files:
        raise FileNotFoundError(f"{folder} 폴더에 xlsx 파일이 없습니다.")
    return max(files, key=os.path.getmtime)


def _build_po_dataframe():
    stockout_path = latest_file("psi_input\품절예상조회")
    overview_path = latest_file("psi_input\재고개요")
    sf_path       = latest_file("psi_input\SF")
    def _finfo(path):
        return {
            "name": os.path.basename(path),
            "mtime": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%m/%d %H:%M"),
        }
    file_info = {
        "품절예상조회": _finfo(stockout_path),
        "재고개요":     _finfo(overview_path),
        "SF":           _finfo(sf_path),
    }
    ###################################여기서 부터 시작###############################
    df_stockout = pd.read_excel(stockout_path)
    df_overview = pd.read_excel(overview_path)
    df_sf = pd.read_excel(sf_path)
    df_sf.columns = df_sf.columns.astype(str)

    # 품절예상조회 전처리 
    df_stockout = df_stockout[["자재", "자재명", "3개월 평균출하", "당월출하"]].copy()
    df_stockout.rename(columns = {"자재":"자재코드", "자재명":"자재내역", "3개월 평균출하":"3평판"}, inplace=True)
    df_stockout["자재코드"] = df_stockout["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df_stockout["당월출하"] = pd.to_numeric(df_stockout["당월출하"], errors="coerce").fillna(0)
    df_stockout["3평판"] = pd.to_numeric(df_stockout["3평판"], errors="coerce").fillna(0)

    # SF 전처리 
    today = datetime.today() 
    year_month = today.strftime('%Y.%m')
    df_sf = df_sf[["자재코드", "자재내역", "관리 채널", year_month]].copy()
    df_sf.rename(columns = {"관리 채널":"관리채널", year_month:"SF"}, inplace=True)
    df_sf["자재코드"] = df_sf["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df_sf["SF"] = pd.to_numeric(df_sf["SF"], errors="coerce").fillna(0)
    df_sf = df_sf.groupby("자재코드").agg(자재내역=("자재내역", "first"), SF=("SF", "sum")).reset_index()
    #df_sf["SF"] = df_sf["SF"].round().astype(int)

    # 품절예상조회 + SF 병합
    # df_standard의 자재내역 기본, 비어있는 경우만 df_sf 자재내역으로 채움
    df_standard = pd.merge(df_stockout, df_sf, on="자재코드", how="outer", suffixes=("", "_sf"))
    df_standard["자재내역"] = df_standard["자재내역"].fillna(df_standard["자재내역_sf"])
    df_standard.drop(columns=["자재내역_sf"], inplace=True)

    df_standard["3평판"]   = df_standard["3평판"].fillna(0)
    df_standard["당월출하"] = df_standard["당월출하"].fillna(0)
    df_standard["SF"]     = df_standard["SF"].fillna(0)

    # 판매율 계산 (분모 0이면 NaN 처리)
    df_standard["판매율(평판)"] = (df_standard["당월출하"] / df_standard["3평판"]).where(df_standard["3평판"] != 0)
    df_standard["판매율(SF)"]  = (df_standard["당월출하"] / df_standard["SF"]).where(df_standard["SF"] != 0)

    df_standard["3평판"] = df_standard["3평판"].astype(float)
    df_standard["당월출하"] = df_standard["당월출하"].astype(float)
    df_standard["SF"] = df_standard["SF"].astype(float)

    # 판매율(SF) 높은 순 정렬
    df_standard = df_standard.sort_values("판매율(SF)", ascending=False, na_position="last").reset_index(drop=True)
    df_standard = df_standard[["자재코드", "자재내역", "3평판", "SF", "당월출하", "판매율(평판)", "판매율(SF)"]]

    #재고개요 전처리 
    df_overview = df_overview[["자재", "저장 위치", "배치", "특별 재고", "기말 재고 수량"]].copy()
    df_overview.rename(columns = {"자재":"자재코드", "저장 위치":"저장위치", "배치":"배치", "특별 재고":"특별재고", "기말 재고 수량":"기말재고"}, inplace=True)
    df_overview["자재코드"] = df_overview["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df_overview["기말재고"] = pd.to_numeric(df_overview["기말재고"], errors="coerce").fillna(0)

    # 특별재고 제거
    df_overview = filter_special_stock(df_overview)

    # 자재코드- 저장위치로 grouping 
    df_overview["자재코드"] = df_overview["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df_overview["저장위치"] = df_overview["저장위치"].fillna("알수없음")
    df_overview["저장위치"] = df_overview["저장위치"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    df_overview = df_overview.groupby(["자재코드", "저장위치"], as_index = False).agg({
    "기말재고" : "sum"
    })

    # 각 자재코드별 저장위치의 기말재고 피벗 테이블
    df_overview = df_overview.pivot_table(
    index="자재코드",
    columns="저장위치",
    values="기말재고",
    aggfunc="sum",   # 중복 시 합계
    fill_value=0     # 없는 값은 0
    )

    #판매율 데이터를 기준으로 저장위치별 창고 재고현황 붙여주기
    df_standard = pd.merge(df_standard, df_overview, on = "자재코드", how = "left")


    return df_standard, file_info


def load_PO_data():
    """기존 파일로만 데이터 로드 (SAP 다운로드 없음). (df, file_info) 튜플 반환"""
    return _build_po_dataframe()


def for_PO_check():
    """SAP에서 최신 파일 다운로드 후 데이터 로드. (df, file_info) 튜플 반환"""
    stockout_dir = os.path.join(BASE, "psi_input", "품절예상조회")
    overview_dir = os.path.join(BASE, "psi_input", "재고개요")
    os.makedirs(stockout_dir, exist_ok=True)
    os.makedirs(overview_dir, exist_ok=True)
    download_stockout_prediction(stockout_dir)
    download_inventory_overview(overview_dir)
    return _build_po_dataframe()


