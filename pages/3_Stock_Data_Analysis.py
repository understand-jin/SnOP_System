import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os

# ✅ 페이지 설정
st.set_page_config(page_title="Stock Data Analysis", layout="wide")
st.title("📈 Stock Data Analysis")

# ✅ 상수 설정 (기본 유지)
PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

BATCH_COL, MAT_COL, MAT_NAME_COL = "배치", "자재", "자재 내역"
EXPIRY_COL, QTY_SRC_COL, UNIT_COST_COL = "유효 기한", "Stock Quantity on Period End", "단위원가"
VALUE_COL, BUCKET_COL, DAYS_COL = "Stock Value on Period End", "expiry_bucket", "days_to_expiry"

# ✅ 환경 설정 (폰트 등)
def set_korean_font():
    # 경로 설정은 사용자 환경에 맞춰 조정 필요
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NanumGothic-Regular.ttf"))
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = fm.FontProperties(fname=font_path).get_name()
    else:
        plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()
sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"])

# ✅ 데이터 처리 함수 (기존 로직 유지)
def to_numeric_safe(s): return pd.to_numeric(s, errors="coerce").fillna(0)

def build_final_df(dfs_dict, year_str, month_str):
    # 필수 파일 존재 확인
    for key in [PRICE_DF_KEY, STOCK_DF_KEY, EXPIRY_DF_KEY]:
        if key not in dfs_dict:
            st.error(f"❌ '{year_str} {month_str}' 폴더에 필수 파일이 없습니다: {key}")
            st.stop()
            
    df_price = dfs_dict[PRICE_DF_KEY]
    tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
    tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
    tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
    unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
    unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1)
    
    df_stock = dfs_dict[STOCK_DF_KEY]
    df_expiry = dfs_dict[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
    merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
    merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
    merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
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
    merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL]], on=MAT_COL, how="left")
    merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
    merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
    return merged

# =====================================================
# 🚀 메인 로직 시작
# =====================================================
all_dfs_store = st.session_state.get("dfs", {})

if not all_dfs_store:
    st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
    st.stop()

# --- 📅 [수정] 분석 대상 연도 및 월 선택 ---
st.sidebar.header("📂 분석 대상 선택")
available_years = sorted(list(all_dfs_store.keys()))
selected_year = st.sidebar.selectbox("📅 연도 선택", options=available_years)

year_data = all_dfs_store.get(selected_year, {})
available_months = sorted(list(year_data.keys()))

if not available_months:
    st.error(f"{selected_year}에 저장된 월 데이터가 없습니다.")
    st.stop()

selected_month = st.sidebar.selectbox("📆 월 선택", options=available_months)

# 선택된 연도/월의 데이터 뭉치 가져오기
target_dfs = year_data[selected_month]

# -----------------------------------------------------
# ✅ 현재 분석에 사용되는 파일 정보 표시
# -----------------------------------------------------
with st.expander(f"📁 {selected_year} {selected_month} 분석 대상 파일 확인", expanded=False):
    file_info = []
    for f_name, f_df in target_dfs.items():
        file_info.append({"파일명": f_name, "행 수": len(f_df), "컬럼 수": f_df.shape[1]})
    st.table(pd.DataFrame(file_info))

# 최종 가공 데이터 생성
with st.spinner(f"{selected_year} {selected_month} 데이터를 통합 분석 중입니다..."):
    final_df = build_final_df(target_dfs, selected_year, selected_month)

# -----------------------------------------------------
# 1️⃣ 기간별 위험 자재 요약 (탭)
# -----------------------------------------------------
st.subheader(f"🚨 {selected_year} {selected_month} 기간별 위험 자재 요약")
tab6, tab7, tab9 = st.tabs(["⚠️ 6개월 미만", "🔔 7개월 미만", "ℹ️ 9개월 미만"])

def display_risk_summary(target_buckets, tab_obj, title):
    with tab_obj:
        risk_df = final_df[final_df[BUCKET_COL].isin(target_buckets)].copy()
        if risk_df.empty:
            st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
        else:
            summary = (
                risk_df.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[[QTY_SRC_COL, VALUE_COL]]
                .sum()
                .sort_values(VALUE_COL, ascending=False)
                .reset_index(drop=True)
            )
            m1, m2, m3 = st.columns([1, 1, 2])
            m1.metric(f"{title} 자재 수", f"{len(summary)}종")
            m2.metric(f"총 위험 금액", f"₩{summary[VALUE_COL].sum():,.0f}")
            with m3:
                disp = summary.copy()
                disp[VALUE_COL] = disp[VALUE_COL].map('{:,.0f}'.format)
                disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map('{:,.0f}'.format)
                st.dataframe(disp, use_container_width=True, height=200)

risk_base = ["폐기확정(유효기한 지남)", "3개월 미만"]
display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만"], tab7, "7개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만", "9개월 미만"], tab9, "9개월 미만")

st.divider()

# -----------------------------------------------------
# 2️⃣ 자재-배치 단위 상세 분석 및 시각화
# -----------------------------------------------------
st.subheader("🔍 자재-배치별 상세 분석 (6/7/9개월 집중)")

target_risks_all = ["3개월 미만", "6개월 미만", "7개월 미만", "9개월 미만", "폐기확정(유효기한 지남)"]
df_risk_all = final_df[final_df[BUCKET_COL].isin(target_risks_all)].copy()

if not df_risk_all.empty:
    top_mats = (
        df_risk_all.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[VALUE_COL].sum()
        .sort_values(VALUE_COL, ascending=False)
    )
    top_mats["label"] = top_mats[MAT_COL].astype(str) + " | " + top_mats[MAT_NAME_COL].astype(str)
    
    col_sel, col_chk = st.columns([2, 1])
    with col_sel:
        selected_label = st.selectbox("상세 조사가 필요한 자재를 선택하세요", options=top_mats["label"].tolist())
        selected_mat = selected_label.split(" | ")[0]
    with col_chk:
        show_all_batches = st.checkbox("모든 위험 배치 보기 (금액순)", value=False)

    if show_all_batches:
        view_df = df_risk_all.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
    else:
        view_df = df_risk_all[df_risk_all[MAT_COL].astype(str) == selected_mat].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)

    st.write(f"### 📍 상세 리스트 (분석 대상: {selected_label if not show_all_batches else '전체 위험 배치'})")
    
    v_disp = view_df[[MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]].copy()
    v_disp[VALUE_COL] = v_disp[VALUE_COL].map('{:,.0f}'.format)
    v_disp[QTY_SRC_COL] = v_disp[QTY_SRC_COL].map('{:,.0f}'.format)
    st.dataframe(v_disp, use_container_width=True)

    if not show_all_batches:
        chart_targets = ["6개월 미만", "7개월 미만", "9개월 미만"]
        chart_df = view_df[view_df[BUCKET_COL].isin(chart_targets)].copy()

        if not chart_df.empty:
            fig, ax = plt.subplots(figsize=(12, 5)) 
            sns.barplot(
                data=chart_df, 
                x=BATCH_COL, 
                y=VALUE_COL, 
                hue=BUCKET_COL, 
                palette="viridis",
                ax=ax,
                errorbar=None,
                width=0.7 
            )
            
            ax.set_title(f"📍 [{selected_label}] 배치별 상세 가치 분석 (6/7/9개월 미만)", fontsize=15, pad=20)
            ax.set_xlabel("배치 번호", fontsize=12)
            ax.set_ylabel("재고 가치 (Stock Value)", fontsize=12)

            import matplotlib.ticker as ticker
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            ax.legend(title="위험 구간", bbox_to_anchor=(1.05, 1), loc='upper left')
            
            sns.despine()
            plt.xticks(rotation=0, ha="right")
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
        else:
            st.info("💡 선택한 자재에는 6/7/9개월 미만에 해당하는 배치가 없습니다.")
else:
    st.info("관리 대상 위험 재고가 없습니다.")

# -----------------------------------------------------
# 💾 가공된 데이터 최종 등록
# -----------------------------------------------------
if "stock_data" not in st.session_state:
    st.session_state["stock_data"] = {}

# 저장 시에도 연도-월 구조를 유지하면 나중에 비교하기 좋습니다.
if selected_year not in st.session_state["stock_data"]:
    st.session_state["stock_data"][selected_year] = {}

st.session_state["stock_data"][selected_year][selected_month] = {
    "df": final_df,
    "processed_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

st.sidebar.success(f"✅ {selected_year} {selected_month} 가공 완료")


# import streamlit as st
# import pandas as pd
# from datetime import datetime
# import matplotlib.pyplot as plt
# import seaborn as sns
# import matplotlib.font_manager as fm
# import os

# # ✅ 페이지 설정
# st.set_page_config(page_title="Stock Data Analysis", layout="wide")
# st.title("📈 Stock Data Analysis")

# # ✅ 상수 설정 (기존과 동일)
# PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
# STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
# EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

# BATCH_COL, MAT_COL, MAT_NAME_COL = "배치", "자재", "자재 내역"
# EXPIRY_COL, QTY_SRC_COL, UNIT_COST_COL = "유효 기한", "Stock Quantity on Period End", "단위원가"
# VALUE_COL, BUCKET_COL, DAYS_COL = "Stock Value on Period End", "expiry_bucket", "days_to_expiry"

# # ✅ 환경 설정 (폰트 등)
# def set_korean_font():
#     font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NanumGothic-Regular.ttf"))
#     if os.path.exists(font_path):
#         fm.fontManager.addfont(font_path)
#         plt.rcParams["font.family"] = fm.FontProperties(fname=font_path).get_name()
#     else:
#         plt.rcParams["font.family"] = "Malgun Gothic"
#     plt.rcParams["axes.unicode_minus"] = False

# set_korean_font()
# sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"])

# # ✅ 데이터 처리 함수 (기존 로직 유지)
# def to_numeric_safe(s): return pd.to_numeric(s, errors="coerce").fillna(0)

# def build_final_df(dfs_dict):
#     # 필수 파일 존재 확인
#     for key in [PRICE_DF_KEY, STOCK_DF_KEY, EXPIRY_DF_KEY]:
#         if key not in dfs_dict:
#             st.error(f"❌ 필수 파일이 없습니다: {key}")
#             st.stop()
            
#     df_price = dfs_dict[PRICE_DF_KEY]
#     tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
#     tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
#     tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
#     unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
#     unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1)
    
#     df_stock = dfs_dict[STOCK_DF_KEY]
#     df_expiry = dfs_dict[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
#     merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
#     merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
#     merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
#     today = pd.Timestamp(datetime.now().date())
#     merged[EXPIRY_COL] = pd.to_datetime(merged[EXPIRY_COL], errors="coerce")
#     merged[DAYS_COL] = (merged[EXPIRY_COL] - today).dt.days
    
#     def bucketize(days):
#         if pd.isna(days): return "유효기한 없음"
#         if days <= 0: return "폐기확정(유효기한 지남)"
#         if days <= 90: return "3개월 미만"
#         if days <= 180: return "6개월 미만"
#         if days <= 210: return "7개월 미만"  
#         if days <= 270: return "9개월 미만"
#         if days <= 365: return "12개월 미만"
#         return "12개월 이상"
    
#     merged[BUCKET_COL] = merged[DAYS_COL].apply(bucketize)
#     merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL]], on=MAT_COL, how="left")
#     merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
#     merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
#     return merged

# # # =====================================================
# # # 🚀 메인 로직 시작
# # # =====================================================
# # all_dfs_store = st.session_state.get("dfs", {})

# # if not all_dfs_store:
# #     st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
# #     st.stop()

# # # --- 📅 분석 대상 월 선택 ---
# # available_months = list(all_dfs_store.keys())
# # selected_month = st.selectbox("🔍 분석할 데이터 기준 월을 선택하세요", options=available_months)

# # # 선택된 월의 데이터 뭉치(3개 파일) 가져오기
# # target_dfs = all_dfs_store[selected_month]

# # # 최종 가공 데이터 생성
# # final_df = build_final_df(target_dfs)

# # =====================================================
# # 🚀 메인 로직 시작
# # =====================================================
# all_dfs_store = st.session_state.get("dfs", {})

# if not all_dfs_store:
#     st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
#     st.stop()

# # --- 📅 [수정] 분석 대상 연도 및 월 선택 ---
# st.sidebar.header("📂 분석 대상 선택")
# available_years = sorted(list(all_dfs_store.keys()))
# selected_year = st.sidebar.selectbox("📅 연도 선택", options=available_years)

# year_data = all_dfs_store.get(selected_year, {})
# available_months = sorted(list(year_data.keys()))

# if not available_months:
#     st.error(f"{selected_year}에 저장된 월 데이터가 없습니다.")
#     st.stop()

# selected_month = st.sidebar.selectbox("📆 월 선택", options=available_months)

# # 선택된 연도/월의 데이터 뭉치 가져오기
# target_dfs = year_data[selected_month]

# # -----------------------------------------------------
# # ✅ [추가] 현재 분석에 사용되는 파일 정보 표시
# # -----------------------------------------------------
# with st.expander(f"📁 {selected_year} {selected_month} 분석 대상 파일 확인", expanded=False):
#     file_info = []
#     for f_name, f_df in target_dfs.items():
#         file_info.append({"파일명": f_name, "행 수": len(f_df), "컬럼 수": f_df.shape[1]})
#     st.table(pd.DataFrame(file_info))

# # 최종 가공 데이터 생성
# with st.spinner(f"{selected_year} {selected_month} 데이터를 통합 분석 중입니다..."):
#     final_df = build_final_df(target_dfs, selected_year, selected_month)

# # -----------------------------------------------------
# # 1️⃣ 기간별 위험 자재 요약 (탭)
# # -----------------------------------------------------
# st.subheader(f"🚨 {selected_year} {selected_month} 기간별 위험 자재 요약")
# tab6, tab7, tab9 = st.tabs(["⚠️ 6개월 미만", "🔔 7개월 미만", "ℹ️ 9개월 미만"])

# def display_risk_summary(target_buckets, tab_obj, title):
#     with tab_obj:
#         risk_df = final_df[final_df[BUCKET_COL].isin(target_buckets)].copy()
#         if risk_df.empty:
#             st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
#         else:
#             summary = (
#                 risk_df.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[[QTY_SRC_COL, VALUE_COL]]
#                 .sum()
#                 .sort_values(VALUE_COL, ascending=False)
#                 .reset_index(drop=True)
#             )
#             m1, m2, m3 = st.columns([1, 1, 2])
#             m1.metric(f"{title} 자재 수", f"{len(summary)}종")
#             m2.metric(f"총 위험 금액", f"₩{summary[VALUE_COL].sum():,.0f}")
#             with m3:
#                 disp = summary.copy()
#                 disp[VALUE_COL] = disp[VALUE_COL].map('{:,.0f}'.format)
#                 disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map('{:,.0f}'.format)
#                 st.dataframe(disp, use_container_width=True, height=200)

# risk_base = ["폐기확정(유효기한 지남)", "3개월 미만"]
# display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
# display_risk_summary(risk_base + ["6개월 미만", "7개월 미만"], tab7, "7개월 미만")
# display_risk_summary(risk_base + ["6개월 미만", "7개월 미만", "9개월 미만"], tab9, "9개월 미만")

# st.divider()

# # -----------------------------------------------------
# # 2️⃣ 자재-배치 단위 상세 분석 및 시각화
# # -----------------------------------------------------
# st.subheader("🔍 자재-배치별 상세 분석 (6/7/9개월 집중)")

# target_risks_all = ["3개월 미만", "6개월 미만", "7개월 미만", "9개월 미만", "폐기확정(유효기한 지남)"]
# df_risk_all = final_df[final_df[BUCKET_COL].isin(target_risks_all)].copy()

# if not df_risk_all.empty:
#     top_mats = (
#         df_risk_all.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[VALUE_COL].sum()
#         .sort_values(VALUE_COL, ascending=False)
#     )
#     top_mats["label"] = top_mats[MAT_COL].astype(str) + " | " + top_mats[MAT_NAME_COL].astype(str)
    
#     col_sel, col_chk = st.columns([2, 1])
#     with col_sel:
#         selected_label = st.selectbox("상세 조사가 필요한 자재를 선택하세요", options=top_mats["label"].tolist())
#         selected_mat = selected_label.split(" | ")[0]
#     with col_chk:
#         show_all_batches = st.checkbox("모든 위험 배치 보기 (금액순)", value=False)

#     if show_all_batches:
#         view_df = df_risk_all.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
#     else:
#         view_df = df_risk_all[df_risk_all[MAT_COL].astype(str) == selected_mat].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)

#     st.write(f"### 📍 상세 리스트 (분석 대상: {selected_label if not show_all_batches else '전체 위험 배치'})")
    
#     v_disp = view_df[[MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]].copy()
#     v_disp[VALUE_COL] = v_disp[VALUE_COL].map('{:,.0f}'.format)
#     v_disp[QTY_SRC_COL] = v_disp[QTY_SRC_COL].map('{:,.0f}'.format)
#     st.dataframe(v_disp, use_container_width=True)

#     if not show_all_batches:
#         chart_targets = ["6개월 미만", "7개월 미만", "9개월 미만"]
#         chart_df = view_df[view_df[BUCKET_COL].isin(chart_targets)].copy()

#         if not chart_df.empty:
#             fig, ax = plt.subplots(figsize=(12, 5)) 
#             sns.barplot(
#                 data=chart_df, 
#                 x=BATCH_COL, 
#                 y=VALUE_COL, 
#                 hue=BUCKET_COL, 
#                 palette="viridis",
#                 ax=ax,
#                 errorbar=None,
#                 width=0.7 
#             )
            
#             ax.set_title(f"📍 [{selected_label}] 배치별 상세 가치 분석 (6/7/9개월 미만)", fontsize=15, pad=20)
#             ax.set_xlabel("배치 번호", fontsize=12)
#             ax.set_ylabel("재고 가치 (Stock Value)", fontsize=12)

#             import matplotlib.ticker as ticker
#             ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
#             ax.legend(title="위험 구간", bbox_to_anchor=(1.05, 1), loc='upper left')
            
#             sns.despine()
#             plt.xticks(rotation=0, ha="right")
#             plt.tight_layout()
#             st.pyplot(fig, use_container_width=True)
#         else:
#             st.info("💡 선택한 자재에는 6/7/9개월 미만에 해당하는 배치가 없습니다.")
# else:
#     st.info("관리 대상 위험 재고가 없습니다.")

# # -----------------------------------------------------
# # 💾 가공된 데이터 최종 등록
# # -----------------------------------------------------
# if "stock_data" not in st.session_state:
#     st.session_state["stock_data"] = {}

# # 저장 시에도 연도-월 구조를 유지하면 나중에 비교하기 좋습니다.
# if selected_year not in st.session_state["stock_data"]:
#     st.session_state["stock_data"][selected_year] = {}

# st.session_state["stock_data"][selected_year][selected_month] = {
#     "df": final_df,
#     "processed_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# }

# st.sidebar.success(f"✅ {selected_year} {selected_month} 가공 완료")


# # import streamlit as st
# # import pandas as pd
# # from datetime import datetime
# # import matplotlib.pyplot as plt
# # import seaborn as sns
# # import matplotlib.font_manager as fm
# # import os

# # # ✅ 페이지 브라우저 탭 이름과 레이아웃 설정
# # st.set_page_config(page_title="Stock Data Analysis", layout="wide")

# # # ✅ 화면 메인 제목 설정
# # st.title("📈 Stock Data Analysis")

# # # =====================================================
# # # ✅ dfs key (파일명 그대로)
# # # =====================================================
# # PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
# # STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
# # EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

# # # =====================================================
# # # ✅ 표준 컬럼명
# # # =====================================================
# # BATCH_COL = "배치"
# # MAT_COL = "자재"
# # MAT_NAME_COL = "자재 내역"
# # EXPIRY_COL = "유효 기한"
# # QTY_SRC_COL = "Stock Quantity on Period End"
# # UNIT_COST_COL = "단위원가"
# # VALUE_COL = "Stock Value on Period End"
# # BUCKET_COL = "expiry_bucket"
# # DAYS_COL = "days_to_expiry"




