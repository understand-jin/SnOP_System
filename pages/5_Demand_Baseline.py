import streamlit as st
import pandas as pd
import numpy as np

from utils import preprocess_df, read_excel_with_smart_header
from prophet import Prophet
import plotly.graph_objects as go

st.set_page_config(page_title="S&OP System - Demand Baseline", layout="wide")

st.title("📊 Demand Baseline")
st.markdown("""
이 페이지는 **25년 매출실적_Data.xlsx** 파일을 분석하여 채널별 실매출액 및 순매출수량을 집계하고,  
선택한 채널의 월별 수요 데이터를 기반으로 **Prophet 수요 예측**을 수행합니다.
(※ `for_forecast.csv`는 저장하지 않고 화면에서 바로 생성/확인합니다.)
""")

REQUIRED_COLS = ["년월", "자재", "자재명", "실매출액", "순매출수량", "채널.1"]

st.divider()
st.subheader("1️⃣ 데이터 로드")

uploaded_file = st.file_uploader("25년 매출실적_Data.xlsx 파일을 업로드하세요.", type=["xlsx"])


def convert_to_ds_val(ym):
    if pd.isna(ym):
        return None
    ym_str = str(ym).strip()

    if len(ym_str) == 6 and ym_str.isdigit():  # 202501
        return pd.to_datetime(ym_str, format="%Y%m")

    try:
        dt = pd.to_datetime(ym_str)
        return pd.Timestamp(dt.year, dt.month, 1)  # 월 시작일로 정규화
    except Exception:
        return None


if not uploaded_file:
    st.info("시작하려면 엑셀 파일을 업로드해 주세요.")
    st.stop()

try:
    # -----------------------------
    # 1) Load & Preprocess
    # -----------------------------
    with st.spinner("파일을 읽는 중..."):
        df_raw = read_excel_with_smart_header(uploaded_file.getvalue())
        df = preprocess_df(df_raw)

    st.success("파일 로드 완료!")

    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        st.warning(f"⚠️ 필수 컬럼 중 일부가 없습니다: {missing_cols}")
        st.write("현재 컬럼 리스트:", df.columns.tolist())
        st.stop()

    df_selected = df[REQUIRED_COLS].copy()

    with st.expander("원본 데이터 미리보기", expanded=False):
        st.dataframe(df_selected.head(50), use_container_width=True)

    # -----------------------------
    # 2) Aggregation
    # -----------------------------
    st.divider()
    st.subheader("2️⃣ 채널별 집계 (년월 + 채널.1)")

    agg_cols = ["실매출액", "순매출수량"]
    for col in agg_cols:
        df_selected[col] = pd.to_numeric(df_selected[col], errors="coerce")

    df_selected[agg_cols] = df_selected[agg_cols].fillna(0)

    df_agg = (
        df_selected
        .groupby(["년월", "채널.1"], as_index=False)[agg_cols]
        .sum()
        .sort_values(["채널.1", "년월"])
    )

    st.write("### 📈 집계 결과")
    st.dataframe(df_agg, use_container_width=True)

    # -----------------------------
    # 3) Build Prophet Input (No saving)
    # -----------------------------
    st.divider()
    st.subheader("3️⃣ Prophet 입력 데이터 생성 (저장 없이 화면에서 바로 확인)")

    channels = sorted(df_agg["채널.1"].dropna().unique().tolist())
    default_idx = channels.index("홈쇼핑") if "홈쇼핑" in channels else 0
    selected_channel = st.selectbox("예측할 채널 선택", channels, index=default_idx)

    y_choice = st.radio("예측 대상 선택", ["순매출수량", "실매출액"], horizontal=True)

    df_prophet_base = df_agg[df_agg["채널.1"] == selected_channel].copy()
    if df_prophet_base.empty:
        st.error(f"'{selected_channel}' 채널 데이터가 없습니다.")
        st.stop()

    df_prophet_base["ds"] = df_prophet_base["년월"].apply(convert_to_ds_val)
    df_prophet_base = df_prophet_base.dropna(subset=["ds"]).copy()
    df_prophet_base[y_choice] = pd.to_numeric(df_prophet_base[y_choice], errors="coerce").fillna(0)

    df_for_forecast = (
        df_prophet_base.groupby("ds", as_index=False)[y_choice]
        .sum()
        .rename(columns={y_choice: "y"})
        .sort_values("ds")
    )

    # ✅ 핵심 1: 월 누락 자동 보정 (연속 월 인덱스로 강제)
    min_ds = df_for_forecast["ds"].min()
    max_ds = df_for_forecast["ds"].max()
    full_months = pd.date_range(min_ds, max_ds, freq="MS")

    df_for_forecast = (
        df_for_forecast.set_index("ds")
        .reindex(full_months)
        .rename_axis("ds")
        .reset_index()
    )

    # 누락 월은 0으로 둘지(매출/수량 누락=0) / NaN으로 둘지 선택
    # 대부분 매출실적 집계 누락은 "데이터 누락"일 수 있으니,
    # Baseline 용이면 0보다 NaN이 낫기도 함. 여기선 안전하게 0 처리.
    df_for_forecast["y"] = pd.to_numeric(df_for_forecast["y"], errors="coerce").fillna(0)

    st.write("### ✅ Prophet 입력 데이터 (ds, y) - 월 누락 보정 후")
    st.dataframe(df_for_forecast, use_container_width=True)

    # -----------------------------
    # 4) Prophet Forecast
    # -----------------------------
    st.divider()
    st.subheader("4️⃣ Prophet 예측")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        train_start = st.text_input("학습 시작(ds)", "2025-01-01")
    with col2:
        train_end = st.text_input("학습 종료(ds)", "2025-10-01")
    with col3:
        test_start = st.text_input("테스트 시작(ds)", "2025-11-01")
    with col4:
        test_end = st.text_input("테스트 종료(ds)", "2025-12-01")

    train_start_dt = pd.to_datetime(train_start)
    train_end_dt = pd.to_datetime(train_end)
    test_start_dt = pd.to_datetime(test_start)
    test_end_dt = pd.to_datetime(test_end)

    df_train = df_for_forecast[(df_for_forecast["ds"] >= train_start_dt) & (df_for_forecast["ds"] <= train_end_dt)].copy()
    df_test = df_for_forecast[(df_for_forecast["ds"] >= test_start_dt) & (df_for_forecast["ds"] <= test_end_dt)].copy()

    # ✅ 디버깅용(짧게): 학습 데이터 마지막 달 확인
    st.caption(f"📌 df_train 마지막 ds = {df_train['ds'].max().date() if not df_train.empty else 'None'}")

    if len(df_train) < 6:
        st.warning("학습 데이터가 너무 적습니다. (Prophet은 최소 6포인트 이상 권장)")
        st.stop()

    st.markdown("**모델 옵션**")
    opt1, opt2, opt3 = st.columns(3)
    with opt1:
        cps = st.slider("changepoint_prior_scale (추세변화 민감도)", 0.01, 0.5, 0.2, 0.01)
    with opt2:
        yearly = st.checkbox("yearly_seasonality", value=True)
    with opt3:
        mode = st.selectbox("seasonality_mode", ["additive", "multiplicative"], index=0)

    extra_periods = st.number_input("추가 예측 개월 수 (테스트 이후)", min_value=0, max_value=24, value=0, step=1)

    with st.spinner("Prophet 모델 학습 및 예측 중..."):
        model = Prophet(
            yearly_seasonality=yearly,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=cps,
            seasonality_mode=mode
        )
        model.fit(df_train)

        # ✅ 핵심 2: UI train_end가 아니라 "실제 학습 데이터 마지막 달" 기준으로 horizon 계산
        last_train_ds = df_train["ds"].max()
        horizon = (test_end_dt.to_period("M") - last_train_ds.to_period("M")).n
        periods = int(horizon + int(extra_periods))
        periods = max(periods, 1)

        future = model.make_future_dataframe(periods=periods, freq="MS")
        forecast = model.predict(future)

    # -----------------------------
    # Plot
    # -----------------------------
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_for_forecast["ds"], y=df_for_forecast["y"],
        mode="lines+markers", name="Actual"
    ))

    fig.add_trace(go.Scatter(
        x=forecast["ds"], y=forecast["yhat"],
        mode="lines", name="Predicted (yhat)"
    ))

    fig.add_trace(go.Scatter(
        x=pd.concat([forecast["ds"], forecast["ds"][::-1]]),
        y=pd.concat([forecast["yhat_upper"], forecast["yhat_lower"][::-1]]),
        fill="toself",
        line=dict(width=0),
        hoverinfo="skip",
        name="Confidence Interval"
    ))

    fig.add_vline(x=test_start_dt, line_dash="dash")
    fig.add_annotation(x=test_start_dt, y=1, yref="paper", text="Train/Test Split", showarrow=False)

    fig.update_layout(
        title=f"📌 {selected_channel} 채널 수요 예측 (Prophet) | y={y_choice}",
        xaxis_title="ds (월)",
        yaxis_title="y",
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="whitesmoke")
    fig.update_yaxes(showgrid=True, gridcolor="whitesmoke")
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # 5) Test Evaluation (MAPE)
    # -----------------------------
    st.divider()
    st.subheader("5️⃣ 테스트 기간 성능(11~12월 등)")

    # 테스트 월(11~12)을 강제로 만들고 forecast에서 뽑기
    test_months = pd.date_range(start=test_start_dt, end=test_end_dt, freq="MS")
    pred_test = forecast[forecast["ds"].isin(test_months)][["ds", "yhat"]].copy()

    # ✅ 예측값 자체를 먼저 보여주기 (11,12월 yhat 확인용)
    st.write("### ✅ 테스트 기간 예측값(yhat) (forecast에서 추출)")
    st.dataframe(pred_test, use_container_width=True)

    # 실제값이 있으면 오차 계산
    if df_test.empty:
        st.info("테스트 '실제값'이 없어 오차 계산은 생략합니다.")
    else:
        result_compare = df_test.merge(pred_test, on="ds", how="left")
        result_compare["abs_error"] = (result_compare["y"] - result_compare["yhat"]).abs()

        safe = result_compare["y"] != 0
        result_compare["ape(%)"] = np.where(
            safe,
            (result_compare["abs_error"] / result_compare["y"]) * 100,
            np.nan
        )
        mape = result_compare["ape(%)"].mean()

        st.dataframe(
            result_compare.style.format({
                "y": "{:,.0f}",
                "yhat": "{:,.1f}",
                "abs_error": "{:,.1f}",
                "ape(%)": "{:.1f}%"
            }),
            use_container_width=True
        )
        st.metric("MAPE(%)", f"{mape:.1f}" if pd.notna(mape) else "N/A")

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.exception(e)
