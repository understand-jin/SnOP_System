import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import re

def normalize_mat_code(x):
    """자재코드 정규화: 123.0 -> '123'"""
    s = str(x).strip()
    try:
        return str(int(float(s)))
    except:
        return s

def to_numeric_safe(s):
    """안전한 숫자 변환"""
    return pd.to_numeric(s, errors="coerce").fillna(0)

def find_col(df, target, candidates):
    """대상 컬럼이 없으면 후보 중에서 찾아주는 헬퍼"""
    if target in df.columns:
        return target
    for c in candidates:
        if c in df.columns:
            return c
    return target # 오류 발생하도록 원본 반환

def bucketize(days):
    if pd.isna(days): 
        return "유효기한 없음"
    if days <= 0: 
        return "폐기확정"
    if days <= 90: 
        return "3개월 미만"
    if days <= 180: 
        return "6개월 미만"
    if days <= 210: 
        return "7개월 미만"
    if days <= 270: 
        return "9개월 미만"
    if days <= 365: 
        return "12개월 미만"
    if days <= 548: 
        return "18개월 미만"
    if days <= 730: 
        return "24개월 미만"
    return "24개월 이상"

def aging_inventory_preprocess(cost_df, standard_df, expiration_df, sales_df, cls_df, year_str, month_str):

    # 1. 데이터 불러오기 + 컬럼명 변경
    # 자재수불부 (cost_df) [자재코드, 기말수량_cosst, 기말금액]
    cost_df = cost_df[["자재","기말(수량)", "기말(금액)합계"]].copy()
    cost_df.rename(columns = {"자재" : "자재코드", "기말(수량)" : "기말수량_cost", "기말(금액)합계" : "기말금액"}, inplace = True)
    cost_df["자재코드"] = (cost_df["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))

    # 재고개요 (standard_df) [자재코드, 플랜트, 특별재고, 저장위치, 배치, 기말수량]
    standard_df = standard_df[["자재", "자재 내역", "플랜트", "특별 재고", "저장 위치", "배치", "기말 재고 수량"]].copy()
    standard_df.rename(columns = {"자재" : "자재코드", "자재 내역" : "자재내역", "특별 재고" : "특별재고", "저장 위치" : "저장위치", "기말 재고 수량" : "기말수량"}, inplace = True)
    standard_df["자재코드"] = (standard_df["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    standard_df["배치"] = (standard_df["배치"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))

    # 배치별유효기한 (expiration_df) [자재코드, 배치, 유효기한]
    expiration_df = expiration_df[["자재", "배치", "배치만료일"]].copy()
    expiration_df.rename(columns = {"자재" : "자재코드", "배치만료일" : "유효기한"}, inplace = True)
    expiration_df["자재코드"] = (expiration_df["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    expiration_df["배치"] = (expiration_df["배치"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    

    # 3개월매출 (sales_df) [년월, 자재코드, 순매출금액, 순매출수량]
    sales_df = sales_df[["년월", "자재코드", "순매출", "순매출수량"]].copy()
    sales_df.rename(columns = {"순매출" : "순매출금액"}, inplace = True)
    sales_df["자재코드"] = (sales_df["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    

    # 대분류_소분류 (cls_df) [자재코드, 대분류, 소분류]
    cls_df = cls_df[["자재", "대분류", "소분류"]].copy()
    cls_df.rename(columns= {"자재" : "자재코드"}, inplace = True)
    cls_df["자재코드"] = (cls_df["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
    

    #2. 단가 계산 후 standard에 mapping
    cost_df["기말수량_cost"] = pd.to_numeric(cost_df["기말수량_cost"], errors="coerce")
    cost_df["기말금액"] = pd.to_numeric(cost_df["기말금액"], errors="coerce")
    cost_df["단가"] = cost_df["기말금액"] / cost_df["기말수량_cost"].replace(0, pd.NA)
    
    cost_map = cost_df.drop_duplicates(subset=["자재코드"]).set_index("자재코드")["단가"]
    standard_df["단가"] = standard_df["자재코드"].map(cost_map).fillna(0)
    standard_df = standard_df[["자재코드", "자재내역", "플랜트", "특별재고", "저장위치", "배치", "기말수량", "단가"]]

    #3. 소분류, 대분류 standard에 mapping
    big_map = cls_df.drop_duplicates(subset=["자재코드"]).set_index("자재코드")["대분류"]
    small_map = cls_df.drop_duplicates(subset=["자재코드"]).set_index("자재코드")["소분류"]
    standard_df["대분류"] = standard_df["자재코드"].map(big_map).fillna("미분류")
    standard_df["소분류"] = standard_df["자재코드"].map(small_map).fillna("미분류")

    # 4. 유효기한 standard에 mapping
    exp_map = (expiration_df.drop_duplicates(subset=["자재코드", "배치"]).set_index(["자재코드", "배치"])["유효기한"])
    standard_df = standard_df.join(exp_map, on=["자재코드", "배치"])
    standard_df["유효기한"] = standard_df["유효기한"].fillna("nan")
    
    # 5. 남은일 & 유효기한구간 계산
    standard_df["유효기한"] = pd.to_datetime(standard_df["유효기한"], errors="coerce").dt.normalize()
    today = pd.Timestamp.today().normalize()
    standard_df["남은일"] = (standard_df["유효기한"] - today).dt.days
    standard_df["유효기한구간"] = standard_df["남은일"].apply(bucketize)

    # 6.재고금액계산
    standard_df["기말금액"] = standard_df["기말수량"] * standard_df["단가"]

    # 7. 3평판 계산
    tmp = sales_df.copy()
    tmp["순매출수량"] = pd.to_numeric(tmp["순매출수량"], errors="coerce").fillna(0)
    tmp["년월"] = tmp["년월"].astype(str).str.strip()
    tmp["자재코드"] = tmp["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    month_count = tmp.groupby("자재코드")["년월"].nunique()
    month_qty = tmp.groupby("자재코드")["순매출수량"].sum()
    sales_avg = (month_qty / month_count.replace(0, pd.NA)).fillna(0)

    standard_df["3평판"] = standard_df["자재코드"].map(sales_avg).fillna(0)
    print("STEP7 standard:", standard_df["자재코드"].nunique())

   
    standard_df = standard_df[["자재코드", "자재내역", "플랜트", "특별재고", "저장위치", "배치", "기말수량", "기말금액", "단가", "대분류", "소분류", "유효기한", "남은일", "유효기한구간", "3평판"]]

    return standard_df

def simulate_batches_by_product(df: pd.DataFrame, risk_days: int = 180, step_days: int = 30, today=None):

    if today is None:
        today = datetime.now().date()
    elif isinstance(today, datetime):
        today = today.date()

    df0 = df.copy()
<<<<<<< HEAD
    df0["남은일"]  = pd.to_numeric(df0["남은일"],  errors="coerce").fillna(0).astype(int)
    df0["기말수량"] = pd.to_numeric(df0["기말수량"], errors="coerce").fillna(0.0)
    df0["3평판"]   = pd.to_numeric(df0["3평판"],   errors="coerce").fillna(0.0)

    detail_rows = []
    updated = df0.copy()
    updated["예측부진재고"] = 0.0  # 시뮬레이션 결과 저장용 컬럼 초기화
=======
    df0["남은일"] = pd.to_numeric(df0["남은일"], errors="coerce").fillna(0).astype(int)
    df0["기말수량"] = pd.to_numeric(df0["기말수량"], errors="coerce").fillna(0.0)
    df0["3평판"] = pd.to_numeric(df0["3평판"], errors="coerce").fillna(0.0)

    detail_rows = []
    updated = df0.copy()
>>>>>>> 97023ce (refactoring...)

    for (mat, mat_name), g in df0.groupby(["자재코드", "자재내역"], dropna=False):
        g = g.sort_values("남은일", ascending=True).reset_index(drop=True)  # FEFO
        monthly_sales = float(g["3평판"].iloc[0]) if len(g) else 0.0
<<<<<<< HEAD
        daily_sales   = monthly_sales / step_days if step_days > 0 else 0.0

        # 배치별 상태 배열
        n               = len(g)
        batches_id      = g["배치"].tolist()
        batches_init_days = g["남은일"].tolist()
        batches_init_qty  = g["기말수량"].tolist()
        qty             = list(batches_init_qty)
        qty_sold        = [0.0] * n
        sell_start_date = [None] * n
        sell_end_date   = [None] * n
        stop_reason     = [None] * n

        # 배치별 risk 진입 날짜
=======
        daily_sales = monthly_sales / step_days if step_days > 0 else 0.0

        n = len(g)
        batches_id = g["배치"].tolist()
        batches_init_days = g["남은일"].tolist()
        batches_init_qty = g["기말수량"].tolist()
        qty = list(batches_init_qty)
        qty_sold = [0.0] * n
        sell_start_date = [None] * n
        sell_end_date = [None] * n
        stop_reason = [None] * n

>>>>>>> 97023ce (refactoring...)
        risk_entry = [
            today if d <= risk_days else today + timedelta(days=(d - risk_days))
            for d in batches_init_days
        ]

<<<<<<< HEAD
        # ── no_sales: 월평판 = 0 ──────────────────────────────────────────
        if monthly_sales <= 0:
            for k in range(n):
                detail_rows.append({
                    "자재코드":        mat,
                    "자재내역":        mat_name,
                    "배치":            batches_id[k],
                    "init_qty":        batches_init_qty[k],
                    "init_days":       batches_init_days[k],
                    "risk_entry_date": risk_entry[k],
                    "sell_start_date": None,
                    "sell_end_date":   today,
                    "qty_sold":        0.0,
                    "remaining_qty":   qty[k],
                    "days_left_at_stop": batches_init_days[k],
                    "stop_reason":     "no_sales",
                })
            continue

        # ── carry-over 시뮬레이션 ────────────────────────────────────────
        current_date = today
        idx = 0

        # 시작 시점에 이미 risk인 배치 먼저 처리
        while idx < n and (batches_init_days[idx] - (current_date - today).days) <= risk_days:
            stop_reason[idx]   = "risk_reached_before_start"
            sell_end_date[idx] = current_date
            idx += 1

        # 무한루프 방지 상한
        max_elapsed = max((d - risk_days for d in batches_init_days if d > risk_days), default=0)
        max_months  = min(int(max_elapsed / step_days) + 2, 120)
=======
        if monthly_sales <= 0:
            for k in range(n):
                detail_rows.append({
                    "자재코드": mat,
                    "자재내역": mat_name,
                    "배치": batches_id[k],
                    "init_qty": batches_init_qty[k],
                    "init_days": batches_init_days[k],
                    "risk_entry_date": risk_entry[k],
                    "sell_start_date": None,
                    "sell_end_date": today,
                    "qty_sold": 0.0,
                    "remaining_qty": qty[k],
                    "days_left_at_stop": batches_init_days[k],
                    "stop_reason": "no_sales",
                })
            continue

        current_date = today
        idx = 0

        while idx < n and (batches_init_days[idx] - (current_date - today).days) <= risk_days:
            stop_reason[idx] = "risk_reached_before_start"
            sell_end_date[idx] = current_date
            idx += 1

        max_elapsed = max((d - risk_days for d in batches_init_days if d > risk_days), default=0)
        max_months = min(int(max_elapsed / step_days) + 2, 120)
>>>>>>> 97023ce (refactoring...)

        for _ in range(max_months):
            if idx >= n:
                break

<<<<<<< HEAD
            month_demand    = monthly_sales
=======
            month_demand = monthly_sales
>>>>>>> 97023ce (refactoring...)
            month_days_left = float(step_days)

            while month_demand > 1e-9 and month_days_left > 1e-9 and idx < n:
                days_now = batches_init_days[idx] - (current_date - today).days

<<<<<<< HEAD
                # risk 구간 → 다음 배치
                if days_now <= risk_days:
                    if stop_reason[idx] is None:
                        stop_reason[idx]   = "risk_reached_before_start" if qty_sold[idx] <= 0 else "risk_reached"
=======
                if days_now <= risk_days:
                    if stop_reason[idx] is None:
                        stop_reason[idx] = "risk_reached_before_start" if qty_sold[idx] <= 0 else "risk_reached"
>>>>>>> 97023ce (refactoring...)
                        sell_end_date[idx] = current_date
                    idx += 1
                    continue

                days_until_risk = (risk_entry[idx] - current_date).days
<<<<<<< HEAD
                sellable_days   = min(month_days_left, float(days_until_risk))
                sellable_qty    = daily_sales * sellable_days
                sell_qty        = min(qty[idx], month_demand, sellable_qty)

                if sell_qty <= 1e-12:
                    if stop_reason[idx] is None:
                        stop_reason[idx]   = "risk_reached"
=======
                sellable_days = min(month_days_left, float(days_until_risk))
                sellable_qty = daily_sales * sellable_days
                sell_qty = min(qty[idx], month_demand, sellable_qty)

                if sell_qty <= 1e-12:
                    if stop_reason[idx] is None:
                        stop_reason[idx] = "risk_reached"
>>>>>>> 97023ce (refactoring...)
                        sell_end_date[idx] = current_date
                    idx += 1
                    continue

                days_used = sell_qty / daily_sales

                if sell_start_date[idx] is None:
                    sell_start_date[idx] = current_date

<<<<<<< HEAD
                qty[idx]        -= sell_qty
                qty_sold[idx]   += sell_qty
                month_demand    -= sell_qty          # ← carry-over 핵심
                month_days_left -= days_used
                current_date     = current_date + timedelta(days=days_used)
                sell_end_date[idx] = current_date

                # 완판 → 다음 배치로 (남은 month_demand 이월)
                if qty[idx] <= 1e-9:
                    qty[idx]        = 0.0
=======
                qty[idx] -= sell_qty
                qty_sold[idx] += sell_qty
                month_demand -= sell_qty
                month_days_left -= days_used
                current_date = current_date + timedelta(days=days_used)
                sell_end_date[idx] = current_date

                if qty[idx] <= 1e-9:
                    qty[idx] = 0.0
>>>>>>> 97023ce (refactoring...)
                    stop_reason[idx] = "sold_out"
                    idx += 1
                    continue

<<<<<<< HEAD
                # risk 진입 → 다음 배치로
=======
>>>>>>> 97023ce (refactoring...)
                if current_date >= risk_entry[idx]:
                    stop_reason[idx] = "risk_reached"
                    idx += 1
                    continue

            if month_days_left > 1e-9:
                current_date = current_date + timedelta(days=month_days_left)

<<<<<<< HEAD
        # 보정: 루프 종료 후 처리 안 된 배치
        for k in range(n):
            if stop_reason[k] is None:
                stop_reason[k]   = "stopped_with_sales" if qty_sold[k] > 0 else "stopped"
                sell_end_date[k] = sell_end_date[k] or current_date

        # ── detail_rows 적재 ─────────────────────────────────────────────
        for k in range(n):
            days_at_stop = batches_init_days[k] - (sell_end_date[k] - today).days if sell_end_date[k] else None
            detail_rows.append({
                "자재코드":        mat,
                "자재내역":        mat_name,
                "배치":            batches_id[k],
                "init_qty":        batches_init_qty[k],
                "init_days":       batches_init_days[k],
                "risk_entry_date": risk_entry[k],
                "sell_start_date": sell_start_date[k],
                "sell_end_date":   sell_end_date[k],
                "qty_sold":        qty_sold[k],
                "remaining_qty":   qty[k],
                "days_left_at_stop": days_at_stop,
                "stop_reason":     stop_reason[k],
            })

        for k in range(n):
            updated.loc[
                (updated["자재코드"] == mat) & (updated["배치"] == batches_id[k]),
                "예측부진재고"
            ] = qty[k]
        updated["예측부진재고금액"] = updated["예측부진재고"] * updated["단가"]

        forecasted_aging_inventory_df = updated.copy()

    return pd.DataFrame(detail_rows), forecasted_aging_inventory_df
=======
        for k in range(n):
            if stop_reason[k] is None:
                stop_reason[k] = "stopped_with_sales" if qty_sold[k] > 0 else "stopped"
                sell_end_date[k] = sell_end_date[k] or current_date

        for k in range(n):
            days_at_stop = batches_init_days[k] - (sell_end_date[k] - today).days if sell_end_date[k] else None
            detail_rows.append({
                "자재코드": mat,
                "자재내역": mat_name,
                "배치": batches_id[k],
                "init_qty": batches_init_qty[k],
                "init_days": batches_init_days[k],
                "risk_entry_date": risk_entry[k],
                "sell_start_date": sell_start_date[k],
                "sell_end_date": sell_end_date[k],
                "qty_sold": qty_sold[k],
                "remaining_qty": qty[k],
                "days_left_at_stop": days_at_stop,
                "stop_reason": stop_reason[k],
            })

    detail_df = pd.DataFrame(detail_rows)

    remaining_gty_df = detail_df[["자재코드", "배치", "remaining_qty"]].copy()
    remaining_gty_df = (
        remaining_gty_df
        .groupby(["자재코드", "배치"], as_index=False)["remaining_qty"]
        .sum()
    )

    updated = updated.drop(columns=["플랜트", "특별재고", "저장위치"], errors="ignore")

    sum_cols = ["기말수량", "기말금액"]
    agg_dict = {col: "first" for col in updated.columns}
    for col in sum_cols:
        agg_dict[col] = "sum"

    result = (
        updated.groupby(["자재코드", "배치"], as_index=False)
        .agg(agg_dict)
    )

    result = result.merge(remaining_gty_df, on=["자재코드", "배치"], how="left")
    result.rename(columns={"remaining_qty": "예측부진재고"}, inplace=True)
    result["예측부진재고"] = result["예측부진재고"].fillna(0)
    result["예측부진재고금액"] = result["예측부진재고"] * result["단가"]

    forecasted_aging_inventory_df = result.copy()

    return detail_df, forecasted_aging_inventory_df
>>>>>>> 97023ce (refactoring...)

def binary_search(standard_df: pd.DataFrame, forecasted_df: pd.DataFrame, today=None, lo=1.0, hi=10.0, tol=1e-3, max_iter=100):
    
    res_df = forecasted_df.copy()
    res_df["판매개선율"] = ""
    res_df["권장판매량"] = ""
    
    slug_mats = res_df[res_df["예측부진재고"] > 0]["자재코드"].unique()
    
    for mat in slug_mats:
        mat_df = standard_df[standard_df["자재코드"] == mat].copy()
        if mat_df.empty:
            continue
            
        def _get_metric(m):
            df_in = mat_df.copy()
            df_in["3평판"] = pd.to_numeric(df_in["3평판"], errors="coerce").fillna(0) * m
            detail_df, _ = simulate_batches_by_product(df_in, today=today)
            return detail_df["remaining_qty"].sum()

        best_m = None
        if _get_metric(lo) <= 0:
            best_m = lo
        elif _get_metric(hi) > 0:
            best_m = hi
        else:
            a, b = lo, hi
            for _ in range(max_iter):
                mid = (a + b) / 2
                if _get_metric(mid) > 0:
                    a = mid
                else:
                    b = mid
                if (b - a) < tol:
                    break
            best_m = b
            
        if best_m is not None:
            # 상한선(hi)에 도달한 경우 "OOO% 이상"으로 표기
            if best_m >= hi:
                disp_rate = f"{(hi - 1) * 100:.0f}% 이상"
            else:
                disp_rate = f"{(best_m - 1) * 100:.0f}%"
                
            res_df.loc[res_df["자재코드"] == mat, "판매개선율"] = disp_rate
            
            # 권장판매량은 원래 수치 기반으로 계산
            base_sales = pd.to_numeric(res_df.loc[res_df["자재코드"] == mat, "3평판"], errors="coerce").fillna(0).astype(float)
            res_df.loc[res_df["자재코드"] == mat, "권장판매량"] = base_sales * best_m
                
<<<<<<< HEAD
    return res_df
=======
    return res_df


def picking_major_management_inventory(df):

    major_management_df = df[(180 <= df["남은일"]) & (df["남은일"] < 360)]

    detail_df,major_management_df= simulate_batches_by_product(major_management_df)

    major_management_df = major_management_df[major_management_df["예측부진재고"] > 0]

    detail_df = detail_df[detail_df["remaining_qty"] > 0]

    return major_management_df


def depletion_rate(df1, df2):
    """
    소진계획 대비 실제 출하 소진율 계산
    df1: 소진계획.csv DataFrame (자재코드, 배치, 각 월 컬럼 포함)
    df2: 품절예상조회 DataFrame (자재, 당월출하 컬럼 포함)
    """
    current_month = datetime.today().month
    month_col = f"{current_month}월"

    # df1에 해당 월 컬럼이 없으면 빈 결과 반환
    if month_col not in df1.columns:
        return pd.DataFrame(columns=["자재코드", "자재내역", "배치", month_col, "당월출하", "소진율"])

    df1 = df1[["자재코드", "자재내역", "배치", month_col]].copy()

    df2 = df2.copy()
    # 자재 컬럼명 정규화
    if "자재" in df2.columns and "자재코드" not in df2.columns:
        df2.rename(columns={"자재": "자재코드"}, inplace=True)
    df2["자재코드"] = df2["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df2 = df2[["자재코드", "당월출하"]].copy()
    df2["당월출하"] = pd.to_numeric(df2["당월출하"], errors="coerce").fillna(0)
    # 자재코드 단위로 합산 (배치 구분 없음)
    df2 = df2.groupby("자재코드", as_index=False)["당월출하"].sum()

    df1["자재코드"] = df1["자재코드"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df1[month_col] = pd.to_numeric(df1[month_col], errors="coerce").fillna(0)

    result = df1.merge(df2, on="자재코드", how="left")
    result["당월출하"] = result["당월출하"].fillna(0)
    result["소진율"] = result.apply(
        lambda r: r["당월출하"] / r[month_col] if r[month_col] > 0 else 0.0, axis=1
    )
    result["소진율"] = result["소진율"].clip(upper=1.0)  # 최대 100%로 제한

    return result

>>>>>>> 97023ce (refactoring...)
