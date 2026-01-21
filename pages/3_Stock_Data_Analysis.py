import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os

# st.set_page_config(page_title="S&OP - Data Analysis", layout="wide")
# st.title("📈 Data Analysis (Stock)")
# ✅ 페이지 브라우저 탭 이름과 레이아웃 설정
st.set_page_config(page_title="Stock Data Analysis", layout="wide")

# ✅ 화면 메인 제목 설정
st.title("📈 Stock Data Analysis")

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
    df_price = dfs[PRICE_DF_KEY]
    tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
    tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
    tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
    unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
    unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1)
    
    df_stock = dfs[STOCK_DF_KEY]
    df_expiry = dfs[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
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
        if days <= 210: return "7개월 미만"  # ✅ 7개월 추가
        if days <= 270: return "9개월 미만"
        if days <= 365: return "12개월 미만"
        return "12개월 이상"
    
    merged[BUCKET_COL] = merged[DAYS_COL].apply(bucketize)
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
# 1️⃣ [우선 확인] 위험 기간별 요약 (6/7/9개월 탭)
# -----------------------------------------------------
st.subheader("🚨 기간별 위험 자재 요약")
st.write("의사결정이 필요한 위험 구간을 선택하세요. (기본 3개월 데이터 포함)")

# 탭 구성 변경
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

# 데이터 매핑 (상위 구간은 하위 구간을 포함함)
risk_base = ["폐기확정(유효기한 지남)", "3개월 미만"]
display_risk_summary(risk_base + ["6개월 미만"], tab6, "6개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만"], tab7, "7개월 미만")
display_risk_summary(risk_base + ["6개월 미만", "7개월 미만", "9개월 미만"], tab9, "9개월 미만")

st.divider()

# -----------------------------------------------------
# 2️⃣ 자재-배치 단위 상세 분석 (시각화: 3개월 제외)
# -----------------------------------------------------
st.subheader("🔍 자재-배치별 상세 분석 (6/7/9개월 집중)")

# 분석 및 테이블용 전체 위험 데이터 (3개월 포함)
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

    # 필터링
    if show_all_batches:
        view_df = df_risk_all.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
    else:
        view_df = df_risk_all[df_risk_all[MAT_COL].astype(str) == selected_mat].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)

    st.write(f"### 📍 상세 리스트 (분석 대상: {selected_label if not show_all_batches else '전체 위험 배치'})")
    
    v_disp = view_df[[MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]].copy()
    v_disp[VALUE_COL] = v_disp[VALUE_COL].map('{:,.0f}'.format)
    v_disp[QTY_SRC_COL] = v_disp[QTY_SRC_COL].map('{:,.0f}'.format)
    st.dataframe(v_disp, use_container_width=True)

    # 📊 시각화: 3개월 미만 및 폐기확정 제외 (6, 7, 9개월만 표시)
    if not show_all_batches:
        # ✅ 시각화 전용 필터링 로직 추가
        chart_targets = ["6개월 미만", "7개월 미만", "9개월 미만"]
        chart_df = view_df[view_df[BUCKET_COL].isin(chart_targets)].copy()

        if not chart_df.empty:
            fig, ax = plt.subplots(figsize=(12, 5)) 
            sns.barplot(
                data=chart_df.head(15), 
                x=BATCH_COL, 
                y=VALUE_COL, 
                hue=BUCKET_COL, 
                palette="viridis",  # 색상 변경
                ax=ax,
                errorbar=None,
                ci=None,
                width=0.7 
            )
            
            ax.set_title(f"📍 [{selected_label}] 배치별 상세 가치 분석 (6/7/9개월 미만)", fontsize=15, pad=20)
            ax.set_xlabel("배치 번호 (Batch No.)", fontsize=12)
            ax.set_ylabel("재고 가치 (Stock Value)", fontsize=12)

            import matplotlib.ticker as ticker
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            
            # 범례 다시 활성화 (구간 확인용)
            ax.legend(title="위험 구간", bbox_to_anchor=(1.05, 1), loc='upper left')
            
            sns.despine()
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            
            st.pyplot(fig, use_container_width=True)
        else:
            st.info("💡 선택한 자재에는 6/7/9개월 미만에 해당하는 배치가 없습니다. (3개월 미만 또는 폐기 대상만 존재)")
else:
    st.info("관리 대상 위험 재고가 없습니다.")

# 데이터 등록
if "stock_data_registry" not in st.session_state:
    st.session_state["stock_data_registry"] = {"datasets": {}, "selected_id": None}

did = f"stock_final_{datetime.now().strftime('%Y%m%d')}"
st.session_state["stock_data_registry"]["datasets"][did] = {"df": final_df}
st.session_state["stock_data_registry"]["selected_id"] = did




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
# # ✅ dfs key (파일명 그대로)
# # =====================================================
# PRICE_DF_KEY = "1. 결산 재고수불부(원가).xls"
# STOCK_DF_KEY = "2. 배치 재고수불부(배치).xls"
# EXPIRY_DF_KEY = "3. 창고별 재고현황(유효기한)_1.19.xls"

# # =====================================================
# # ✅ 표준 컬럼명
# # =====================================================
# BATCH_COL = "배치"
# MAT_COL = "자재"
# MAT_NAME_COL = "자재 내역"
# EXPIRY_COL = "유효 기한"
# QTY_SRC_COL = "Stock Quantity on Period End"
# UNIT_COST_COL = "단위원가"
# VALUE_COL = "Stock Value on Period End"
# BUCKET_COL = "expiry_bucket"
# DAYS_COL = "days_to_expiry"

# # =====================================================
# # ✅ 환경 설정 (폰트 등)
# # =====================================================
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

# # =====================================================
# # 🛠️ 데이터 처리 함수
# # =====================================================
# def to_numeric_safe(s): return pd.to_numeric(s, errors="coerce").fillna(0)

# def build_final_df(dfs):
#     # 1. 단위원가 계산 (1번 파일)
#     df_price = dfs[PRICE_DF_KEY]
#     tmp = df_price[[MAT_COL, "기말(수량)", "기말(금액)합계"]].copy()
#     tmp["기말(수량)"] = to_numeric_safe(tmp["기말(수량)"])
#     tmp["기말(금액)합계"] = to_numeric_safe(tmp["기말(금액)합계"])
#     unit_cost_df = tmp.groupby(MAT_COL, as_index=False).sum()
#     unit_cost_df[UNIT_COST_COL] = unit_cost_df.apply(lambda r: r["기말(금액)합계"] / r["기말(수량)"] if r["기말(수량)"] > 0 else 0, axis=1)
    
#     # 2. 재고 + 유효기한 병합 (2번 + 3번)
#     df_stock = dfs[STOCK_DF_KEY]
#     df_expiry = dfs[EXPIRY_DF_KEY][[BATCH_COL, EXPIRY_COL]].drop_duplicates(subset=[BATCH_COL])
#     merged = df_stock.merge(df_expiry, on=BATCH_COL, how="left")
    
#     # 3. 수량 0인 데이터 제외
#     merged[QTY_SRC_COL] = to_numeric_safe(merged[QTY_SRC_COL])
#     merged = merged[merged[QTY_SRC_COL] > 0].copy()
    
#     # 4. 유효기한 버킷 생성
#     today = pd.Timestamp(datetime.now().date())
#     merged[EXPIRY_COL] = pd.to_datetime(merged[EXPIRY_COL], errors="coerce")
#     merged[DAYS_COL] = (merged[EXPIRY_COL] - today).dt.days
    
#     def bucketize(days):
#         if pd.isna(days): return "유효기한 없음"
#         if days <= 0: return "폐기확정(유효기한 지남)"
#         if days <= 90: return "3개월 미만"
#         if days <= 180: return "6개월 미만"
#         if days <= 270: return "9개월 미만"
#         if days <= 365: return "12개월 미만"
#         return "12개월 이상"
    
#     merged[BUCKET_COL] = merged[DAYS_COL].apply(bucketize)
    
#     # 5. 금액 계산 결합
#     merged = merged.merge(unit_cost_df[[MAT_COL, UNIT_COST_COL]], on=MAT_COL, how="left")
#     merged[UNIT_COST_COL] = merged[UNIT_COST_COL].fillna(0)
#     merged[VALUE_COL] = merged[QTY_SRC_COL] * merged[UNIT_COST_COL]
    
#     return merged

# # =====================================================
# # 🚀 메인 실행
# # =====================================================
# dfs = st.session_state.get("dfs")
# if not dfs:
#     st.warning("먼저 업로드 페이지에서 데이터를 업로드해 주세요.")
#     st.stop()

# final_df = build_final_df(dfs)

# # -----------------------------------------------------
# # 1️⃣ [우선 확인] 위험 기간별 요약 (탭 메뉴)
# # -----------------------------------------------------
# st.subheader("🚨 기간별 위험 자재 요약")
# st.write("의사결정이 필요한 위험 구간을 선택하세요.")

# # 탭 생성
# tab3, tab6, tab9 = st.tabs(["🔥 3개월 미만", "⚠️ 6개월 미만", "ℹ️ 9개월 미만"])

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

# # 각 탭에 데이터 매핑
# display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만"], tab3, "3개월 미만")
# display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만"], tab6, "6개월 미만")
# display_risk_summary(["폐기확정(유효기한 지남)", "3개월 미만", "6개월 미만", "9개월 미만"], tab9, "9개월 미만")

# st.divider()

# # -----------------------------------------------------
# # 2️⃣ 자재-배치 단위 상세 분석 (Drill-down)
# # -----------------------------------------------------
# st.subheader("🔍 자재-배치별 상세 분석")

# # 분석 대상 버킷 (3/6/9개월 모두 포함하여 선택 가능하게 함)
# target_risks = ["3개월 미만", "6개월 미만", "9개월 미만", "폐기확정(유효기한 지남)"]
# df_risk_all = final_df[final_df[BUCKET_COL].isin(target_risks)].copy()

# if not df_risk_all.empty:
#     # 1. 자재 선택 필터
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

#     # 2. 필터링된 데이터 준비
#     if show_all_batches:
#         view_df = df_risk_all.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
#     else:
#         view_df = df_risk_all[df_risk_all[MAT_COL].astype(str) == selected_mat].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)

#     # 3. 테이블 및 차트
#     st.write(f"### 📍 상세 리스트 (분석 대상: {selected_label if not show_all_batches else '전체 위험 배치'})")
    
#     v_disp = view_df[[MAT_COL, MAT_NAME_COL, BATCH_COL, BUCKET_COL, QTY_SRC_COL, VALUE_COL]].copy()
#     v_disp[VALUE_COL] = v_disp[VALUE_COL].map('{:,.0f}'.format)
#     v_disp[QTY_SRC_COL] = v_disp[QTY_SRC_COL].map('{:,.0f}'.format)
#     st.dataframe(v_disp, use_container_width=True)

#     # 시각화 (화면 맞춤 및 디자인 개선)
#     if not show_all_batches:
#         # 1. 그래프 크기를 화면 너비에 맞춰 유동적으로 조절하기 위해 가로를 길게 설정 (12, 5)
#         fig, ax = plt.subplots(figsize=(12, 5)) 
        
#         # 2. 막대 그래프 그리기 (width 조절로 더 깔끔하게)
#         sns.barplot(
#             data=view_df.head(15), 
#             x=BATCH_COL, 
#             y=VALUE_COL, 
#             hue=BUCKET_COL, 
#             palette="magma", 
#             ax=ax,
#             errorbar=None,
#             ci=None,
#             # 막대 너비를 살짝 줄여서 여백의 미를 줍니다 (0.8이 기본)
#             width=0.7 
#         )
        
#         # 3. 타이틀 및 라벨 폰트 크기 조정
#         ax.set_title(f"📍 [{selected_label}] 배치별 상세 가치 분석", fontsize=15, pad=20)
#         ax.set_xlabel("배치 번호 (Batch No.)", fontsize=12)
#         ax.set_ylabel("재고 가치 (Stock Value)", fontsize=12)

#         # 4. 천 단위 콤마 포맷 (Y축 금액 가독성)
#         import matplotlib.ticker as ticker
#         ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        
#         # 5. 불필요한 범례 제거
#         if ax.get_legend():
#             ax.get_legend().remove()
            
#         # 6. 테두리 깔끔하게 정리 (위쪽, 오른쪽 선 제거)
#         sns.despine()
        
#         plt.xticks(rotation=30, ha="right") # 각도를 30도로 줄여서 더 깔끔하게
#         plt.tight_layout()
        
#         # 🔥 핵심: use_container_width=True를 사용하여 브라우저 너비에 꽉 채움
#         st.pyplot(fig, use_container_width=True)
# else:
#     st.info("관리 대상 위험 재고가 없습니다.")

# # =====================================================
# # ✅ 데이터 저장
# # =====================================================
# if "stock_data_registry" not in st.session_state:
#     st.session_state["stock_data_registry"] = {"datasets": {}, "selected_id": None}

# did = f"stock_final_{datetime.now().strftime('%Y%m%d')}"
# st.session_state["stock_data_registry"]["datasets"][did] = {"df": final_df}
# st.session_state["stock_data_registry"]["selected_id"] = did
