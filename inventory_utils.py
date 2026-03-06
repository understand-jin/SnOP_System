import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import re

def normalize_mat_code(x):
    """
    숫자처럼 생긴 건 정수로 바꿨다가 문자열화 (123.0 -> "123")
    문자 섞인 건 그대로 문자열
    """
    s = str(x).strip()
    try:
        # 123.0, 123 같은 케이스 통일
        return str(int(float(s)))
    except:
        return s

def to_numeric_safe(s): 
    return pd.to_numeric(s, errors="coerce").fillna(0)

def build_final_df(dfs_dict, year_str, month_str, config_cols):
    """
    데이터 전처리 및 병합 로직
    """
    # config_cols에서 상수 가져오기
    PRICE_DF_KEY = config_cols.get("PRICE_DF_KEY")
    STOCK_DF_KEY = config_cols.get("STOCK_DF_KEY")
    EXPIRY_DF_KEY = config_cols.get("EXPIRY_DF_KEY")
    SALES_DF_KEY = config_cols.get("SALES_DF_KEY")
    CLASSIFICATION_DF_KEY = config_cols.get("CLASSIFICATION_DF_KEY")
    
    BATCH_COL = config_cols.get("BATCH_COL")
    MAT_COL = config_cols.get("MAT_COL")
    UNIT_COST_COL = config_cols.get("UNIT_COST_COL")
    QTY_SRC_COL = config_cols.get("QTY_SRC_COL")
    EXPIRY_COL = config_cols.get("EXPIRY_COL")
    DAYS_COL = config_cols.get("DAYS_COL")
    BUCKET_COL = config_cols.get("BUCKET_COL")
    VALUE_COL = config_cols.get("VALUE_COL")

    # 1. 필수 파일 존재 확인
    required_keys = [PRICE_DF_KEY, STOCK_DF_KEY, EXPIRY_DF_KEY, SALES_DF_KEY]
    for key in required_keys:
        if key not in dfs_dict:
            st.error(f"❌ '{year_str} {month_str}' 폴더에 필수 파일이 없습니다: {key}")
            st.stop()
            
    # --- [Step 1] 단위원가 계산 ---
    df_price = dfs_dict[PRICE_DF_KEY]
    tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
    tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
    tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
    unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
    unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(
        lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1
    )

    # --- [Step 1-추가] 대분류/소분류 매핑 ---
    df_cls = dfs_dict[CLASSIFICATION_DF_KEY].copy()
    unit_cost_df[MAT_COL] = unit_cost_df[MAT_COL].astype(str).str.strip()
    df_cls[MAT_COL] = df_cls[MAT_COL].astype(str).str.strip()

    major_map = df_cls.drop_duplicates(subset=[MAT_COL]).set_index(MAT_COL)["대분류"]
    minor_map = df_cls.drop_duplicates(subset=[MAT_COL]).set_index(MAT_COL)["소분류"]

    unit_cost_df["대분류"] = unit_cost_df[MAT_COL].map(major_map)
    unit_cost_df["소분류"] = unit_cost_df[MAT_COL].map(minor_map)
    unit_cost_df["대분류"] = unit_cost_df["대분류"].fillna("미분류")
    unit_cost_df["소분류"] = unit_cost_df["소분류"].fillna("미분류")

    unit_cost_df[MAT_COL] = pd.to_numeric(unit_cost_df[MAT_COL], errors="coerce")

    # --- [Step 2] 재고 정보와 유효기한 병합 ---
    df_stock = dfs_dict[STOCK_DF_KEY]
    df_expiry = dfs_dict[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
    merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
    merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
    merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
    # --- [Step 3] 유효기한 버킷팅 ---
    today = pd.Timestamp(datetime.now().date())
    merged[EXPIRY_COL] = pd.to_datetime(merged[EXPIRY_COL], errors="coerce")
    merged[DAYS_COL] = (merged[EXPIRY_COL] - today).dt.days
    
    def bucketize(days):
        if pd.isna(days): return "유효기한 없음"
        if days <= 0: return "폐기확정(유효기한 지남)"
        if days <= 90: return "3개월 미만"
        if days <= 180: return "6개월 미만"
        if days <= 210: return "7개월 미만"  
        if days <= 270: return "9개월 미만"
        if days <= 365: return "12개월 미만"
        return "12개월 이상"
    
    merged[BUCKET_COL] = merged[DAYS_COL].apply(bucketize)
    
    # --- [Step 4] 재고 가치 산출 ---
    merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL, "대분류", "소분류"]], on=MAT_COL, how="left")
    merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
    merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
    # --- [Step 5] 자재별 월평균 매출(3평판) 계산 ---
    df_sales = dfs_dict[SALES_DF_KEY].copy()
    df_sales['순매출수량'] = to_numeric_safe(df_sales['순매출수량'])
    
    month_counts = df_sales.groupby('자재코드')['년월'].nunique().reset_index()
    month_counts.columns = ['자재코드', '개월수']
    
    total_sales = df_sales.groupby('자재코드', as_index=False)['순매출수량'].sum()
    
    sales_avg = total_sales.merge(month_counts, on='자재코드')
    sales_avg['3평판'] = sales_avg.apply(
        lambda r: r['순매출수량'] / r['개월수'] if r['개월수'] > 0 else 0, axis=1
    )
    
    merged = merged.merge(
        sales_avg[['자재코드', '3평판', '개월수']], 
        left_on=MAT_COL, 
        right_on='자재코드', 
        how="left"
    )
    
    # --- [Step 6] 데이터 정리 및 반환 ---
    if '자재코드' in merged.columns:
        merged.drop(columns=['자재코드'], inplace=True)
    merged['3평판'] = merged['3평판'].fillna(0)
    
    merged['재고일수'] = merged.apply(
        lambda r: r[QTY_SRC_COL] / (r['3평판'] / 30.0) if r['3평판'] > 0 else 999.0, 
        axis=1
    )
    
    return merged

def simulate_batches_by_product(
    df: pd.DataFrame,
    product_cols=("자재", "자재 내역"),
    batch_col="배치",
    days_col="유효 기한",
    qty_col="Stock Quantity on Period End",
    monthly_sales_col="3평판",
    risk_days=180,
    step_days=30,
    today=None
):
    """
    제품별 배치 판매 시뮬레이션 (FEFO)
    """
    if today is None:
        today = datetime.now().date()
    elif isinstance(today, datetime):
        today = today.date()

    df0 = df.copy()

    df0[days_col] = pd.to_numeric(df0[days_col], errors="coerce").fillna(0).astype(int)
    df0[qty_col] = pd.to_numeric(df0[qty_col], errors="coerce").fillna(0.0)
    df0[monthly_sales_col] = pd.to_numeric(df0[monthly_sales_col], errors="coerce").fillna(0.0)

    detail_rows = []
    updated = df0.copy()

    grp_cols = list(product_cols)

    for prod_key, g in df0.groupby(grp_cols, dropna=False):
        g = g.copy()
        g = g.sort_values(days_col, ascending=True)
        monthly_sales = float(g[monthly_sales_col].iloc[0]) if len(g) else 0.0
        current_date = today

        batches = []
        for _, row in g.iterrows():
            batches.append({
                "prod_key": prod_key,
                "batch": row[batch_col],
                "init_days": int(row[days_col]),
                "qty": float(row[qty_col])
            })

        def remaining_days(init_days, date_):
            return init_days - (date_ - today).days

        for b in batches:
            batch_id = b["batch"]
            init_days = b["init_days"]
            init_qty = b["qty"]

            if init_days <= risk_days:
                risk_entry_date = today
            else:
                risk_entry_date = today + timedelta(days=(init_days - risk_days))

            days_now = remaining_days(init_days, current_date)

            sell_start_date = None
            sell_end_date = None
            stop_reason = None
            qty_sold_total = 0.0
            months_sold = 0
            sold_days_total = 0

            if monthly_sales <= 0:
                sell_end_date = current_date
                stop_reason = "no_sales"
                detail_rows.append({
                    product_cols[0]: prod_key[0] if isinstance(prod_key, tuple) else prod_key,
                    product_cols[1]: prod_key[1] if isinstance(prod_key, tuple) and len(prod_key) > 1 else None,
                    batch_col: batch_id,
                    "init_qty": init_qty,
                    "init_days": init_days,
                    "risk_entry_date": risk_entry_date,
                    "sell_start_date": sell_start_date,
                    "sell_end_date": sell_end_date,
                    "months_sold": months_sold,
                    "sold_days_total": sold_days_total,
                    "qty_sold": qty_sold_total,
                    "remaining_qty": max(0.0, b["qty"]),
                    "days_left_at_stop": remaining_days(init_days, current_date),
                    "stop_reason": stop_reason
                })
                continue

            if days_now <= risk_days:
                sell_end_date = current_date
                stop_reason = "risk_reached_before_start"
                detail_rows.append({
                    product_cols[0]: prod_key[0] if isinstance(prod_key, tuple) else prod_key,
                    product_cols[1]: prod_key[1] if isinstance(prod_key, tuple) and len(prod_key) > 1 else None,
                    batch_col: batch_id,
                    "init_qty": init_qty,
                    "init_days": init_days,
                    "risk_entry_date": risk_entry_date,
                    "sell_start_date": sell_start_date,
                    "sell_end_date": sell_end_date,
                    "months_sold": months_sold,
                    "sold_days_total": sold_days_total,
                    "qty_sold": qty_sold_total,
                    "remaining_qty": max(0.0, b["qty"]),
                    "days_left_at_stop": days_now,
                    "stop_reason": stop_reason
                })
                continue

            sell_start_date = current_date
            daily_sales = monthly_sales / step_days if step_days > 0 else 0.0

            while True:
                days_now = remaining_days(init_days, current_date)
                if days_now <= risk_days:
                    sell_end_date = current_date
                    stop_reason = "risk_reached"
                    break
                if b["qty"] <= 0:
                    sell_end_date = current_date
                    stop_reason = "sold_out"
                    break

                next_date = current_date + timedelta(days=step_days)
                days_until_risk = (risk_entry_date - current_date).days

                if 0 < days_until_risk < step_days:
                    sellable_days = days_until_risk
                    sellable_qty = daily_sales * sellable_days
                    sell_qty = min(b["qty"], sellable_qty)
                    b["qty"] -= sell_qty
                    qty_sold_total += sell_qty
                    sold_days_total += sellable_days
                    current_date = risk_entry_date
                    sell_end_date = current_date
                    stop_reason = "risk_reached"
                    break

                sell_qty = min(b["qty"], monthly_sales)
                b["qty"] -= sell_qty
                qty_sold_total += sell_qty
                months_sold += 1
                sold_days_total += step_days
                current_date = next_date

            detail_rows.append({
                product_cols[0]: prod_key[0] if isinstance(prod_key, tuple) else prod_key,
                product_cols[1]: prod_key[1] if isinstance(prod_key, tuple) and len(prod_key) > 1 else None,
                batch_col: batch_id,
                "init_qty": init_qty,
                "init_days": init_days,
                "risk_entry_date": risk_entry_date,
                "sell_start_date": sell_start_date,
                "sell_end_date": sell_end_date,
                "months_sold": months_sold,
                "sold_days_total": sold_days_total,
                "qty_sold": qty_sold_total,
                "remaining_qty": max(0.0, b["qty"]),
                "days_left_at_stop": remaining_days(init_days, sell_end_date),
                "stop_reason": stop_reason
            })

        for b in batches:
            updated.loc[
                (updated[product_cols[0]] == (prod_key[0] if isinstance(prod_key, tuple) else prod_key)) &
                (updated[batch_col] == b["batch"]),
                qty_col
            ] = max(0.0, b["qty"])

    return pd.DataFrame(detail_rows), updated

def _get_risk_summary(detail_df: pd.DataFrame):
    """
    시뮬레이션 결과에서 부진재고 수량 및 금액 요약 (내부용)
    """
    risk_k = detail_df[detail_df["remaining_qty"].fillna(0) > 0].copy()

    risk_qty = float(
        pd.to_numeric(risk_k["remaining_qty"], errors="coerce").fillna(0).sum()
    ) if not risk_k.empty else 0.0

    if (not risk_k.empty) and ("remaining_amount" in risk_k.columns):
        risk_amt = float(pd.to_numeric(risk_k["remaining_amount"], errors="coerce").fillna(0).sum())
    else:
        if (not risk_k.empty) and ("단위원가" in risk_k.columns):
            uc = pd.to_numeric(risk_k["단위원가"], errors="coerce").fillna(0)
            rq = pd.to_numeric(risk_k["remaining_qty"], errors="coerce").fillna(0)
            risk_amt = float((rq * uc).sum())
        else:
            risk_amt = np.nan
    return {"risk_qty": risk_qty, "risk_amt": risk_amt}

def calculate_min_multiplier(
    df_mat: pd.DataFrame,
    product_cols,
    batch_col,
    days_col,
    qty_col,
    monthly_sales_col,
    today,
    lo=1.0,
    hi=6.0,
    tol=1e-3,
    max_iter=50
):
    """
    부진재고 0을 달성하기 위한 최소 매출 배수를 이진 탐색으로 찾음
    """
    def _get_metric(m):
        df_in = df_mat.copy()
        df_in["_temp_sales"] = pd.to_numeric(df_in[monthly_sales_col], errors="coerce").fillna(0) * m
        
        detail_k, _ = simulate_batches_by_product(
            df=df_in,
            product_cols=product_cols,
            batch_col=batch_col,
            days_col=days_col,
            qty_col=qty_col,
            monthly_sales_col="_temp_sales",
            risk_days=180,
            step_days=30,
            today=today,
        )
        res = _get_risk_summary(detail_k)
        return res["risk_amt"] if not np.isnan(res["risk_amt"]) else res["risk_qty"]

    if _get_metric(lo) <= 0:
        return lo
    if _get_metric(hi) > 0:
        return None

    a, b = lo, hi
    for _ in range(max_iter):
        mid = (a + b) / 2
        if _get_metric(mid) > 0:
            a = mid
        else:
            b = mid
        if (b - a) < tol:
            break
    return b
