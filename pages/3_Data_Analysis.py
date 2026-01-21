import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os

st.set_page_config(page_title="S&OP - Data Analysis", layout="wide")
st.title("📈 Data Analysis (Stock)")

# =====================================================
# ✅ dfs key (파일명 그대로)
# =====================================================
PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

# =====================================================
# ✅ 표준 컬럼명
# =====================================================
BATCH_COL = "배치"
MAT_COL = "자재"
MAT_NAME_COL = "자재 내역"
EXPIRY_COL = "유효 기한"
QTY_SRC_COL = "Stock Quantity on Period End"
UNIT_COST_COL = "단위원가"
VALUE_COL = "Stock Value on Period End"
BUCKET_COL = "expiry_bucket"
DAYS_COL = "days_to_expiry"

# =====================================================
# ✅ 환경 설정 (폰트 등)
# =====================================================
def set_korean_font():
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NanumGothic-Regular.ttf"))
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = fm.FontProperties(fname=font_path).get_name()
    else:
        plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()
sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"])

# =====================================================
# 🛠️ 데이터 처리 함수
# =====================================================
def to_numeric_safe(s): return pd.to_numeric(s, errors="coerce").fillna(0)

def build_final_df(dfs):
    # 1. 단위원가 계산 (1번 파일)
    df_price = dfs[PRICE_DF_KEY]
    tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
    tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
    tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
    unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
    unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1)
    
    # 2. 재고 + 유효기한 병합 (2번 + 3번)
    df_stock = dfs[STOCK_DF_KEY]
    df_expiry = dfs[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
    merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
    # 3. 수량 0인 데이터 제외
    merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
    merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
    # 4. 유효기한 버킷 생성
    today = pd.Timestamp(datetime.now().date())
    merged[EXPIRY_COL] = pd.to_datetime(merged[EXPIRY_COL], errors="coerce")
    merged[DAYS_COL] = (merged[EXPIRY_COL] - today).dt.days
    
    def bucketize(days):
        if pd.isna(days): return "유효기한 없음"
        if days <= 0: return "폐기확정(유효기한 지남)"
        if days <= 90: return "3개월 미만"
        if days <= 180: return "6개월 미만"
        if days <= 270: return "9개월 미만"
        if days <= 365: return "12개월 미만"
        return "12개월 이상"
    
    merged[BUCKET_COL] = merged[DAYS_COL].apply(bucketize)
    
    # 5. 금액 계산 결합
    merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL]], on=MAT_COL, how="left")
    merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
    merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
    return merged

# =====================================================
# 🚀 메인 실행
# =====================================================
dfs = st.session_state.get("dfs")
if not dfs:
    st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
    st.stop()

final_df = build_final_df(dfs)

# -----------------------------------------------------
# 1️⃣ [우선 확인] 위험 기간별 요약 (탭 메뉴)
# -----------------------------------------------------
st.subheader("🚨 기간별 위험 자재 요약")
st.write("의사결정이 필요한 위험 구간을 선택하세요.")

# 탭 생성
tab3, tab6, tab9 = st.tabs(["🔥 3개월 미만", "⚠️ 6개월 미만", "ℹ️ 9개월 미만"])

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

# 각 탭에 데이터 매핑
display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만"], tab3, "3개월 미만")
display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만"], tab6, "6개월 미만")
display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만", "9개월 미만"], tab9, "9개월 미만")

st.divider()

# -----------------------------------------------------
# 2️⃣ 자재-배치 단위 상세 분석 (Drill-down)
# -----------------------------------------------------
st.subheader("🔍 자재-배치별 상세 분석")

# 분석 대상 버킷 (3/6/9개월 모두 포함하여 선택 가능하게 함)
target_risks = ["3개월 미만", "6개월 미만", "9개월 미만", "폐기확정(유효기한 지남)"]
df_risk_all = final_df[final_df[BUCKET_COL].isin(target_risks)].copy()

if not df_risk_all.empty:
    # 1. 자재 선택 필터
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

    # 2. 필터링된 데이터 준비
    if show_all_batches:
        view_df = df_risk_all.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
    else:
        view_df = df_risk_all[df_risk_all[MAT_COL].astype(str) == selected_mat].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)

    # 3. 테이블 및 차트
    st.write(f"### 📍 상세 리스트 (분석 대상: {selected_label if not show_all_batches else '전체 위험 배치'})")
    
    v_disp = view_df[[MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]].copy()
    v_disp[VALUE_COL] = v_disp[VALUE_COL].map('{:,.0f}'.format)
    v_disp[QTY_SRC_COL] = v_disp[QTY_SRC_COL].map('{:,.0f}'.format)
    st.dataframe(v_disp, use_container_width=True)

    # 시각화
    if not show_all_batches:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=view_df.head(15), x=BATCH_COL, y=VALUE_COL, hue=BUCKET_COL, 
                    palette="magma", ax=ax)
        ax.set_title(f"[{selected_label}] 배치별 자산 가치 현황")
        plt.xticks(rotation=45)
        st.pyplot(fig)
else:
    st.info("관리 대상 위험 재고가 없습니다.")

# =====================================================
# ✅ 데이터 저장
# =====================================================
if "stock_data_registry" not in st.session_state:
    st.session_state["stock_data_registry"] = {"datasets": {}, "selected_id": None}

did = f"stock_final_{datetime.now().strftime('%Y%m%d')}"
st.session_state["stock_data_registry"]["datasets"][did] = {"df": final_df}
st.session_state["stock_data_registry"]["selected_id"] = did

# # import streamlit as st
# # import pandas as pd
# # from datetime import datetime
# # import matplotlib.pyplot as plt
# # import seaborn as sns
# # import matplotlib.font_manager as fm
# # import os

# # st.set_page_config(page_title="S&OP - Data Analysis", layout="wide")
# # st.title("📈 Data Analysis (Stock)")

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

# # # =====================================================
# # # ✅ 환경 설정 (폰트 등)
# # # =====================================================
# # def set_korean_font():
# #     font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NanumGothic-Regular.ttf"))
# #     if os.path.exists(font_path):
# #         fm.fontManager.addfont(font_path)
# #         plt.rcParams["font.family"] = fm.FontProperties(fname=font_path).get_name()
# #     else:
# #         plt.rcParams["font.family"] = "Malgun Gothic"
# #     plt.rcParams["axes.unicode_minus"] = False

# # set_korean_font()
# # sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"])

# # # =====================================================
# # # 🛠️ 데이터 처리 함수
# # # =====================================================
# # def to_numeric_safe(s): return pd.to_numeric(s, errors="coerce").fillna(0)

# # def build_final_df(dfs):
# #     # 1. 단위원가 계산 (1번 파일)
# #     df_price = dfs[PRICE_DF_KEY]
# #     tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
# #     tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
# #     tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
# #     unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
# #     unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1)
    
# #     # 2. 재고 + 유효기한 병합 (2번 + 3번)
# #     df_stock = dfs[STOCK_DF_KEY]
# #     df_expiry = dfs[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
# #     merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
# #     # 3. 수량 0인 데이터 제외
# #     merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
# #     merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
# #     # 4. 유효기한 버킷 생성
# #     today = pd.Timestamp(datetime.now().date())
# #     merged[EXPIRY_COL] = pd.to_datetime(merged[EXPIRY_COL], errors="coerce")
# #     merged[DAYS_COL] = (merged[EXPIRY_COL] - today).dt.days
    
# #     def bucketize(days):
# #         if pd.isna(days): return "유효기한 없음"
# #         if days <= 0: return "폐기확정(유효기한 지남)"
# #         if days <= 90: return "3개월 미만"
# #         if days <= 180: return "6개월 미만"
# #         if days <= 270: return "9개월 미만"
# #         if days <= 365: return "12개월 미만"
# #         return "12개월 이상"
    
# #     merged[BUCKET_COL] = merged[DAYS_COL].apply(bucketize)
    
# #     # 5. 금액 계산 결합
# #     merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL]], on=MAT_COL, how="left")
# #     merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
# #     merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
# #     return merged

# # # =====================================================
# # # 🚀 메인 실행
# # # =====================================================
# # dfs = st.session_state.get("dfs")
# # if not dfs:
# #     st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
# #     st.stop()

# # final_df = build_final_df(dfs)

# # # -----------------------------------------------------
# # # 1️⃣ [우선 확인] 위험 기간별 요약 (탭 메뉴)
# # # -----------------------------------------------------
# # st.subheader("🚨 기간별 위험 자재 요약")
# # st.write("의사결정이 필요한 위험 구간을 선택하세요.")

# # # 탭 생성
# # tab3, tab6, tab9 = st.tabs(["🔥 3개월 미만", "⚠️ 6개월 미만", "ℹ️ 9개월 미만"])

# # def display_risk_summary(target_buckets, tab_obj, title):
# #     with tab_obj:
# #         risk_df = final_df[final_df[BUCKET_COL].isin(target_buckets)].copy()
# #         if risk_df.empty:
# #             st.success(f"✅ {title} 내에 해당하는 자재가 없습니다.")
# #         else:
# #             summary = (
# #                 risk_df.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[[QTY_SRC_COL, VALUE_COL]]
# #                 .sum()
# #                 .sort_values(VALUE_COL, ascending=False)
# #                 .reset_index(drop=True)
# #             )
            
# #             m1, m2, m3 = st.columns([1, 1, 2])
# #             m1.metric(f"{title} 자재 수", f"{len(summary)}종")
# #             m2.metric(f"총 위험 금액", f"₩{summary[VALUE_COL].sum():,.0f}")
            
# #             with m3:
# #                 disp = summary.copy()
# #                 disp[VALUE_COL] = disp[VALUE_COL].map('{:,.0f}'.format)
# #                 disp[QTY_SRC_COL] = disp[QTY_SRC_COL].map('{:,.0f}'.format)
# #                 st.dataframe(disp, use_container_width=True, height=200)

# # # 각 탭에 데이터 매핑
# # display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만"], tab3, "3개월 미만")
# # display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만"], tab6, "6개월 미만")
# # display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만", "9개월 미만"], tab9, "9개월 미만")

# # st.divider()

# # # -----------------------------------------------------
# # # 2️⃣ 자재-배치 단위 상세 분석 (Drill-down)
# # # -----------------------------------------------------
# # st.subheader("🔍 자재-배치별 상세 분석")

# # # 분석 대상 버킷 (3/6/9개월 모두 포함하여 선택 가능하게 함)
# # target_risks = ["3개월 미만", "6개월 미만", "9개월 미만", "폐기확정(유효기한 지남)"]
# # df_risk_all = final_df[final_df[BUCKET_COL].isin(target_risks)].copy()

# # if not df_risk_all.empty:
# #     # 1. 자재 선택 필터
# #     top_mats = (
# #         df_risk_all.groupby([MAT_COL, MAT_NAME_COL], as_index=False)[VALUE_COL].sum()
# #         .sort_values(VALUE_COL, ascending=False)
# #     )
# #     top_mats["label"] = top_mats[MAT_COL].astype(str) + " | " + top_mats[MAT_NAME_COL].astype(str)
    
# #     col_sel, col_chk = st.columns([2, 1])
# #     with col_sel:
# #         selected_label = st.selectbox("상세 조사가 필요한 자재를 선택하세요", options=top_mats["label"].tolist())
# #         selected_mat = selected_label.split(" | ")[0]
# #     with col_chk:
# #         show_all_batches = st.checkbox("모든 위험 배치 보기 (금액순)", value=False)

# #     # 2. 필터링된 데이터 준비
# #     if show_all_batches:
# #         view_df = df_risk_all.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
# #     else:
# #         view_df = df_risk_all[df_risk_all[MAT_COL].astype(str) == selected_mat].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)

# #     # 3. 테이블 및 차트
# #     st.write(f"### 📍 상세 리스트 (분석 대상: {selected_label if not show_all_batches else '전체 위험 배치'})")
    
# #     v_disp = view_df[[MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]].copy()
# #     v_disp[VALUE_COL] = v_disp[VALUE_COL].map('{:,.0f}'.format)
# #     v_disp[QTY_SRC_COL] = v_disp[QTY_SRC_COL].map('{:,.0f}'.format)
# #     st.dataframe(v_disp, use_container_width=True)

# #     # 시각화
# #     if not show_all_batches:
# #         fig, ax = plt.subplots(figsize=(10, 4))
# #         sns.barplot(data=view_df.head(15), x=BATCH_COL, y=VALUE_COL, hue=BUCKET_COL, 
# #                     palette="magma", ax=ax)
# #         ax.set_title(f"[{selected_label}] 배치별 자산 가치 현황")
# #         plt.xticks(rotation=45)
# #         st.pyplot(fig)
# # else:
# #     st.info("관리 대상 위험 재고가 없습니다.")

# # # =====================================================
# # # ✅ 데이터 저장
# # # =====================================================
# # if "stock_data_registry" not in st.session_state:
# #     st.session_state["stock_data_registry"] = {"datasets": {}, "selected_id": None}

# # did = f"stock_final_{datetime.now().strftime('%Y%m%d')}"
# # st.session_state["stock_data_registry"]["datasets"][did] = {"df": final_df}
# # st.session_state["stock_data_registry"]["selected_id"] = did

# import streamlit as st
# import pandas as pd
# from datetime import datetime
# import matplotlib.pyplot as plt
# import seaborn as sns
# import matplotlib.font_manager as fm
# import os

# st.set_page_config(page_title="S&OP - Data Analysis", layout="wide")
# st.title("📈 Data Analysis (Stock)")

# # =====================================================
# # ✅ [추가] Streamlit 표/텍스트 한글 깨짐 방지용 웹폰트 CSS
# #    - st.dataframe(표)도 브라우저 폰트 영향이라 이게 중요!
# # =====================================================
# st.markdown(
#     """
#     <style>
#     @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600&display=swap');
#     html, body, [class*="css"]  {
#         font-family: 'Noto Sans KR', sans-serif !important;
#     }
#     /* dataframe/table에도 적용 */
#     .stDataFrame, .stDataFrame * {
#         font-family: 'Noto Sans KR', sans-serif !important;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# # =====================================================
# # ✅ dfs key (파일명 그대로)
# # =====================================================
# PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
# STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
# EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

# # =====================================================
# # ✅ 표준 컬럼명(고정)
# # =====================================================
# BATCH_COL = "배치"
# MAT_COL = "자재"
# MAT_DESC_COL = "자재 내역"   # ✅ [추가] 자재 내역 컬럼
# EXPIRY_COL = "유효 기한"

# PRICE_QTY_COL = "기말(수량)"
# PRICE_AMT_COL = "기말(금액)합계"

# QTY_SRC_COL = "Stock Quantity on Period End"
# UNIT_COST_COL = "단위원가"
# VALUE_COL = "Stock Value on Period End"

# BUCKET_COL = "expiry_bucket"
# DAYS_COL = "days_to_expiry"

# # 위험 자재 요약 기준 (3/6/9)
# RISK_BUCKETS_369 = ["3개월 미만", "6개월 미만", "9개월 미만"]

# # =====================================================
# # ✅ 폰트 + seaborn (그래프용)
# # =====================================================
# def set_korean_font():
#     font_path = os.path.abspath(
#         os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NanumGothic-Regular.ttf")
#     )
#     if os.path.exists(font_path):
#         fm.fontManager.addfont(font_path)
#         font_name = fm.FontProperties(fname=font_path).get_name()
#         plt.rcParams["font.family"] = font_name
#         return font_name
#     else:
#         plt.rcParams["font.family"] = "DejaVu Sans"
#         return "DejaVu Sans"

# plt.rcParams["axes.unicode_minus"] = False
# font_name = set_korean_font()

# # seaborn에도 그래프 폰트 반영 (중요)
# sns.set_theme(style="whitegrid", rc={"font.family": font_name, "axes.unicode_minus": False})

# # =====================================================
# # 유틸
# # =====================================================
# def to_datetime_safe(s):
#     return pd.to_datetime(s, errors="coerce")

# def to_numeric_safe(s):
#     return pd.to_numeric(s, errors="coerce")

# def require_columns(df, cols, df_name):
#     missing = [c for c in cols if c not in df.columns]
#     if missing:
#         raise ValueError(f"[{df_name}] 필수 컬럼 누락: {missing}")

# # =====================================================
# # 1) 단위원가 테이블 생성 (1번 자료)
# # =====================================================
# def build_unit_cost_df(df_price: pd.DataFrame) -> pd.DataFrame:
#     require_columns(df_price, [MAT_COL, PRICE_QTY_COL, PRICE_AMT_COL], "1번(원가 자료)")

#     tmp = df_price[[MAT_COL, PRICE_QTY_COL, PRICE_AMT_COL]].copy()
#     tmp[PRICE_QTY_COL] = to_numeric_safe(tmp[PRICE_QTY_COL]).fillna(0)
#     tmp[PRICE_AMT_COL] = to_numeric_safe(tmp[PRICE_AMT_COL]).fillna(0)

#     grp = tmp.groupby(MAT_COL, as_index=False).sum()
#     grp[UNIT_COST_COL] = grp.apply(
#         lambda r: r[PRICE_AMT_COL] / r[PRICE_QTY_COL] if r[PRICE_QTY_COL] else 0,
#         axis=1
#     )
#     return grp[[MAT_COL, UNIT_COST_COL]]

# # =====================================================
# # 2) 재고 + 유효기한 병합 (2번 + 3번)
# # =====================================================
# def build_stock_expiry_df(df_stock: pd.DataFrame, df_expiry: pd.DataFrame) -> pd.DataFrame:
#     # ✅ 자재 내역이 있으면 가져오고, 없어도 돌아가게(옵션)
#     need_stock_cols = [BATCH_COL, MAT_COL, QTY_SRC_COL]
#     require_columns(df_stock, need_stock_cols, "2번(배치 재고수불부)")

#     require_columns(df_expiry, [BATCH_COL, EXPIRY_COL], "3번(유효기한)")

#     e = df_expiry[[BATCH_COL, EXPIRY_COL]].copy()
#     e[EXPIRY_COL] = to_datetime_safe(e[EXPIRY_COL])

#     merged = df_stock.merge(e, on=BATCH_COL, how="left")
#     merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL]).fillna(0)

#     return merged

# # =====================================================
# # 3) 유효기한 bucket 생성
# # =====================================================
# def add_expiry_bucket(df: pd.DataFrame) -> pd.DataFrame:
#     df = df.copy()
#     today = pd.Timestamp(datetime.now().date())

#     df[EXPIRY_COL] = to_datetime_safe(df[EXPIRY_COL])
#     df[DAYS_COL] = (df[EXPIRY_COL] - today).dt.days

#     def bucketize(days):
#         if pd.isna(days):
#             return "유효기한 없음"
#         if days <= 0:
#             return "폐기확정(유효기한 지남)"
#         if days <= 90:
#             return "3개월 미만"
#         if days <= 180:
#             return "6개월 미만"
#         if days <= 270:
#             return "9개월 미만"
#         if days <= 365:
#             return "12개월 미만"
#         if days <= 540:
#             return "18개월 미만"
#         if days <= 730:
#             return "24개월 미만"
#         return "24개월 이상"

#     df[BUCKET_COL] = df[DAYS_COL].apply(bucketize)
#     return df

# # =====================================================
# # 4) 단위원가 붙이고 Stock Value 계산
# # =====================================================
# def add_unit_cost_and_value(df: pd.DataFrame, unit_cost_df: pd.DataFrame) -> pd.DataFrame:
#     require_columns(df, [MAT_COL, QTY_SRC_COL], "재고DF")
#     require_columns(unit_cost_df, [MAT_COL, UNIT_COST_COL], "단위원가DF")

#     out = df.merge(unit_cost_df, on=MAT_COL, how="left")
#     out[UNIT_COST_COL] = to_numeric_safe(out[UNIT_COST_COL]).fillna(0)
#     out[VALUE_COL] = to_numeric_safe(out[QTY_SRC_COL]).fillna(0) * out[UNIT_COST_COL]
#     return out

# # =====================================================
# # ✅ dfs 로드
# # =====================================================
# dfs = st.session_state.get("dfs")
# if dfs is None:
#     st.warning("먼저 업로드 페이지에서 Raw 데이터를 업로드해 주세요.")
#     st.stop()

# need_keys = [PRICE_DF_KEY, STOCK_DF_KEY, EXPIRY_DF_KEY]
# missing = [k for k in need_keys if k not in dfs]
# if missing:
#     st.error(f"dfs에 필요한 파일이 없습니다: {missing} (업로드 파일명을 확인하세요)")
#     st.stop()

# df_price = dfs[PRICE_DF_KEY]
# df_stock = dfs[STOCK_DF_KEY]
# df_expiry = dfs[EXPIRY_DF_KEY]

# # =====================================================
# # ✅ 최종 재고 데이터(final_df) 생성
# # =====================================================
# st.subheader("✅ 최종 재고 데이터 자동 생성 (단위원가/유효기한/재고금액 포함)")

# with st.spinner("1) 단위원가 계산 → 2) 재고+유효기한 병합 → 3) 버킷 생성 → 4) 재고금액 계산..."):
#     unit_cost_df = build_unit_cost_df(df_price)
#     stock_expiry = build_stock_expiry_df(df_stock, df_expiry)
#     stock_bucket = add_expiry_bucket(stock_expiry)
#     final_df = add_unit_cost_and_value(stock_bucket, unit_cost_df)

# st.success("✅ final_df 생성 완료!")

# # =====================================================
# # ✅ stock_data_registry 저장
# # =====================================================
# if "stock_data_registry" not in st.session_state:
#     st.session_state["stock_data_registry"] = {"datasets": {}, "selected_id": None}

# final_id = f"stock_final_{datetime.now().strftime('%Y%m%d')}"
# st.session_state["stock_data_registry"]["datasets"][final_id] = {
#     "domain": "stock",
#     "type": "final_stock",
#     "title": "최종 재고 데이터(유효기한/단위원가/재고금액 포함)",
#     "df": final_df,
#     "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
# }
# st.session_state["stock_data_registry"]["selected_id"] = final_id

# # =====================================================
# # ✅ 최종 재고 데이터(final_df) 생성 완료 이후:
# #    ❌ final_df 미리보기 표는 보여주지 않음
# #    ✅ 기간별 위험 자재 요약만 보여줌
# # =====================================================

# st.divider()
# st.subheader("🚨 기간별 위험 자재 요약")
# st.write("의사결정이 필요한 위험 구간을 선택하세요.")

# # ---------------------------
# # 필수 컬럼 체크
# # ---------------------------
# need_cols = [MAT_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]
# missing = [c for c in need_cols if c not in final_df.columns]
# if missing:
#     st.error(f"final_df에 필수 컬럼이 없습니다: {missing}")
#     st.stop()

# # 자재 내역 컬럼이 없다면 빈칸으로 생성(오류 방지)
# if MAT_DESC_COL not in final_df.columns:
#     final_df[MAT_DESC_COL] = ""

# # 숫자형 안전 처리
# final_df[QTY_SRC_COL] = pd.to_numeric(final_df[QTY_SRC_COL], errors="coerce").fillna(0)
# final_df[VALUE_COL]   = pd.to_numeric(final_df[VALUE_COL], errors="coerce").fillna(0)

# # ---------------------------
# # 탭 구성 (요청 UI)
# # ---------------------------
# tab3, tab6, tab9 = st.tabs(["🔥 3개월 미만", "⚠️ 6개월 미만", "ℹ️ 9개월 미만"])


# def show_risk_tab(tab_obj, bucket_list, title):
#     with tab_obj:
#         risk_df = final_df[final_df[BUCKET_COL].isin(bucket_list)].copy()

#         risk_df = risk_df[(risk_df[QTY_SRC_COL] != 0) | (risk_df[VALUE_COL] != 0)]

#         if risk_df.empty:
#             st.success(f"✅ {title} 구간에 해당하는 자재가 없습니다.")
#             return

#         # ✅ 자재 + 배치 기준 집계
#         summary = (
#             risk_df
#             .groupby([MAT_COL, MAT_DESC_COL, BATCH_COL], as_index=False)[[QTY_SRC_COL, VALUE_COL]]
#             .sum()
#             .sort_values(VALUE_COL, ascending=False)
#             .reset_index(drop=True)
#         )

#         # KPI (자재 수 / 총 금액은 자재 기준으로 계산)
#         mat_cnt = summary[MAT_COL].nunique()
#         total_risk_value = float(summary[VALUE_COL].sum())

#         c1, c2 = st.columns(2)
#         c1.metric(f"{title} 자재 수", f"{mat_cnt:,}종")
#         c2.metric("총 위험 금액", f"₩{total_risk_value:,.0f}")

#         # ✅ 테이블 표시 (배치 포함)
#         show_df = summary.rename(columns={
#             MAT_COL: "자재",
#             MAT_DESC_COL: "자재 내역",
#             BATCH_COL: "배치",
#             QTY_SRC_COL: "수량",
#             VALUE_COL: "금액(원)"
#         }).copy()

#         show_df["수량"] = show_df["수량"].map(lambda x: f"{x:,.0f}")
#         show_df["금액(원)"] = show_df["금액(원)"].map(lambda x: f"{x:,.0f}")

#         st.dataframe(show_df, use_container_width=True, height=350)



# # ✅ 탭별 기준
# # - 3개월 탭: 폐기 + 3개월
# # - 6개월 탭: 폐기 + 3 + 6개월
# # - 9개월 탭: 폐기 + 3 + 6 + 9개월
# show_risk_tab(
#     tab3,
#     ["폐기확정(유효기한 지남)", "3개월 미만"],
#     "3개월 미만"
# )

# show_risk_tab(
#     tab6,
#     ["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만"],
#     "6개월 미만"
# )

# show_risk_tab(
#     tab9,
#     ["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만", "9개월 미만"],
#     "9개월 미만"
# )


# # # =====================================================
# # # ✅ final_df 미리보기
# # # =====================================================
# # st.write("### 📌 최종 재고 데이터 미리보기")
# # preview_cols = [c for c in [BATCH_COL, MAT_COL, MAT_DESC_COL, EXPIRY_COL, DAYS_COL, BUCKET_COL, QTY_SRC_COL, UNIT_COST_COL, VALUE_COL] if c in final_df.columns]
# # st.dataframe(final_df[preview_cols].head(80), use_container_width=True)

# # st.download_button(
# #     "📥 최종 재고 데이터(final_df) CSV 다운로드",
# #     data=final_df.to_csv(index=False).encode("utf-8-sig"),
# #     file_name=f"{final_id}.csv",
# #     mime="text/csv"
# # )

# # =====================================================
# # ✅ [추가] 자재-배치 단위 위험재고(3/6/9개월 미만) 상세 테이블 + 시각화
# # =====================================================
# st.divider()
# st.subheader("✅ 자재-배치 단위 위험재고 상세 (3/6/9개월 미만)")

# need = [MAT_COL, BATCH_COL, EXPIRY_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]
# missing = [c for c in need if c not in final_df.columns]
# if missing:
#     st.error(f"final_df에 필수 컬럼이 없습니다: {missing}")
#     st.stop()

# df_detail = final_df.copy()
# df_detail[QTY_SRC_COL] = pd.to_numeric(df_detail[QTY_SRC_COL], errors="coerce").fillna(0)
# df_detail[VALUE_COL] = pd.to_numeric(df_detail[VALUE_COL], errors="coerce").fillna(0)

# # 3/6/9개월 미만만
# df_detail = df_detail[df_detail[BUCKET_COL].isin(RISK_BUCKETS_369)].copy()

# # ✅ [핵심] 자재코드 → 자재 내역 매핑(대표값 1개)
# if MAT_DESC_COL in df_detail.columns:
#     mat_master = (
#         df_detail[[MAT_COL, MAT_DESC_COL]]
#         .dropna()
#         .astype({MAT_COL: str, MAT_DESC_COL: str})
#         .drop_duplicates()
#         .groupby(MAT_COL, as_index=False)[MAT_DESC_COL]
#         .first()
#     )
# else:
#     mat_master = pd.DataFrame({MAT_COL: df_detail[MAT_COL].astype(str).unique(), MAT_DESC_COL: ""})

# # 배치 단위로 합치기 (자재/배치/구간)
# batch_table = (
#     df_detail.groupby([MAT_COL, BATCH_COL, BUCKET_COL], as_index=False)[[QTY_SRC_COL, VALUE_COL]]
#              .sum()
# )

# # ✅ 자재 내역 붙이기
# batch_table[MAT_COL] = batch_table[MAT_COL].astype(str)
# mat_master[MAT_COL] = mat_master[MAT_COL].astype(str)
# batch_table = batch_table.merge(mat_master, on=MAT_COL, how="left")

# # 보기 좋게 정렬
# bucket_order = ["3개월 미만", "6개월 미만", "9개월 미만"]
# batch_table[BUCKET_COL] = pd.Categorical(batch_table[BUCKET_COL], categories=bucket_order, ordered=True)
# batch_table = batch_table.sort_values([MAT_COL, BUCKET_COL, VALUE_COL], ascending=[True, True, False]).reset_index(drop=True)

# # UI: 자재 선택
# top_mat = (
#     batch_table.groupby(MAT_COL, as_index=False)[VALUE_COL].sum()
#               .sort_values(VALUE_COL, ascending=False)
#               .head(30)
# )

# mat_options = top_mat[MAT_COL].tolist()
# if len(mat_options) == 0:
#     st.info("3/6/9개월 미만 데이터가 없습니다.")
#     st.stop()

# col1, col2 = st.columns([2, 1])
# with col1:
#     selected_mat = st.selectbox("자재 선택 (위험금액 TOP 기준)", options=mat_options)
# with col2:
#     show_all_mats = st.checkbox("전체 자재 보기", value=False)

# if show_all_mats:
#     view_df = batch_table.copy()
# else:
#     view_df = batch_table[batch_table[MAT_COL] == str(selected_mat)].copy()

# st.write("### 📌 자재-배치별 3/6/9개월 미만 상세 테이블 (자재 + 자재 내역 포함)")
# show_cols = [MAT_COL, MAT_DESC_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]
# st.dataframe(view_df[show_cols], use_container_width=True)

# # 저장 + 다운로드
# detail_id = f"stock_mat_batch_risk_369_{datetime.now().strftime('%Y%m%d')}"
# st.session_state["stock_data_registry"]["datasets"][detail_id] = {
#     "domain": "stock",
#     "type": "material_batch_risk_369",
#     "title": "자재-배치별 위험재고(3/6/9개월 미만) 상세",
#     "df": batch_table,
#     "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
# }

# st.download_button(
#     "📥 (자재-배치 위험재고 상세) CSV 다운로드",
#     data=batch_table.to_csv(index=False).encode("utf-8-sig"),
#     file_name=f"{detail_id}.csv",
#     mime="text/csv"
# )

# # -----------------------------
# # 시각화 1) 선택 자재의 배치별 금액 Bar
# # -----------------------------
# st.divider()
# st.subheader("📊 시각화: 선택 자재의 배치별 위험 금액")

# if not show_all_mats:
#     top_n_batch = st.slider("TOP N 배치 (선택 자재)", 5, 40, 15, 5)

#     plot_top = (
#         view_df.groupby([BATCH_COL, BUCKET_COL], as_index=False)[VALUE_COL]
#                .sum()
#                .sort_values(VALUE_COL, ascending=False)
#                .head(top_n_batch)
#     )

#     fig, ax = plt.subplots(figsize=(12, 6))
#     sns.barplot(data=plot_top, x=BATCH_COL, y=VALUE_COL, hue=BUCKET_COL, ax=ax)
#     ax.set_title(f"[{selected_mat}] 배치별 위험 재고금액 (3/6/9개월 미만)")
#     ax.set_xlabel("배치")
#     ax.set_ylabel("금액")
#     plt.xticks(rotation=25, ha="right")
#     plt.tight_layout()
#     st.pyplot(fig)

# # -----------------------------
# # 시각화 2) 선택 자재의 구간별 수량/금액 Pie
# # -----------------------------
# st.divider()
# st.subheader("📊 시각화: 선택 자재의 구간별 비중")

# if not show_all_mats:
#     agg_mat = (
#         view_df.groupby(BUCKET_COL, as_index=False)[[QTY_SRC_COL, VALUE_COL]]
#                .sum()
#                .sort_values(BUCKET_COL)
#     )

#     c1, c2 = st.columns(2)

#     with c1:
#         fig, ax = plt.subplots(figsize=(6, 6))
#         ax.pie(
#             agg_mat[VALUE_COL].values,
#             labels=agg_mat[BUCKET_COL].astype(str).tolist(),
#             autopct=lambda p: f"{p:.1f}%" if p > 0 else ""
#         )
#         ax.set_title("구간별 금액 비중(%)")
#         plt.tight_layout()
#         st.pyplot(fig)

#     with c2:
#         fig, ax = plt.subplots(figsize=(6, 6))
#         ax.pie(
#             agg_mat[QTY_SRC_COL].values,
#             labels=agg_mat[BUCKET_COL].astype(str).tolist(),
#             autopct=lambda p: f"{p:.1f}%" if p > 0 else ""
#         )
#         ax.set_title("구간별 수량 비중(%)")
#         plt.tight_layout()
#         st.pyplot(fig)
