import io
import streamlit as st
import pandas as pd

st.set_page_config(page_title="S&OP System - Table Manager", layout="wide")
st.title("🗂️ 테이블 관리 (DF 확인)")

# -----------------------------
# 1. 연도별/월별 데이터 선택 로직
# -----------------------------
all_data = st.session_state.get("dfs", {})

if not all_data:
    st.warning("아직 업로드된 데이터가 없습니다. 먼저 '데이터 업로드' 페이지에서 파일을 올려주세요.")
    st.stop()

# 레이아웃을 3컬럼으로 나누어 연도, 월, 파일을 각각 선택
sel_col1, sel_col2, sel_col3 = st.columns(3)

with sel_col1:
    # 1단계: 저장된 '연도' 목록 가져오기
    available_years = sorted(list(all_data.keys()))
    selected_year = st.selectbox("📅 연도(Year) 선택", available_years)

with sel_col2:
    # 2단계: 선택된 연도 내부의 '월' 목록 가져오기
    year_data = all_data.get(selected_year, {})
    available_months = sorted(list(year_data.keys()))
    
    if not available_months:
        st.error(f"{selected_year}에 데이터가 없습니다.")
        st.stop()
        
    selected_month = st.selectbox("📆 월(Month) 선택", available_months)

with sel_col3:
    # 3단계: 선택된 월 내부의 '파일' 목록 가져오기
    month_dfs = year_data.get(selected_month, {})
    
    if len(month_dfs) == 0:
        st.error(f"{selected_year} {selected_month}에 파일이 없습니다.")
        st.stop()
    
    file_list = list(month_dfs.keys())
    selected_file = st.selectbox("📄 파일(DataFrame) 선택", file_list)

# 최종적으로 선택된 데이터프레임 가져오기
df = month_dfs[selected_file]

# -----------------------------
# 2. 데이터 요약 (Metric)
# -----------------------------
st.divider()
st.subheader(f"📊 {selected_year} {selected_month} - {selected_file} 요약")
c1, c2, c3 = st.columns(3)
c1.metric("Rows", f"{len(df):,}")
c2.metric("Cols", f"{df.shape[1]:,}")
c3.metric("Missing(%)", f"{(df.isna().mean().mean() * 100):.1f}%")

# -----------------------------
# 3. 검색 및 테이블 표시
# -----------------------------
search = st.text_input(f"🔍 [{selected_year} {selected_month}] 빠른 검색 (행 필터링)")
view = df
if search:
    # 모든 컬럼을 문자열로 바꿔서 검색어가 포함된 행만 추출
    mask = df.astype(str).apply(lambda row: row.str.contains(search, case=False, na=False)).any(axis=1)
    view = df[mask]

st.dataframe(view, use_container_width=True, height=500)

with st.expander("🧾 전체 컬럼명 확인", expanded=False):
    st.write(list(df.columns))

# -----------------------------
# 4. 다운로드
# -----------------------------
st.write("---")
d1, d2, _ = st.columns([1, 1, 2])
with d1:
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ CSV 다운로드", 
        data=csv_bytes, 
        file_name=f"{selected_year}_{selected_month}_{selected_file}.csv", 
        mime="text/csv"
    )

with d2:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="processed")
    st.download_button(
        label="⬇️ Excel 다운로드",
        data=buf.getvalue(),
        file_name=f"{selected_year}_{selected_month}_{selected_file}_processed.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# import io
# import streamlit as st
# import pandas as pd

# st.set_page_config(page_title="S&OP System - Table Manager", layout="wide")
# st.title("🗂️ 테이블 관리 (DF 확인)")

# dfs = st.session_state.get("dfs", {})

# if not dfs:
#     st.warning("아직 업로드된 데이터가 없습니다. 먼저 '데이터 업로드' 페이지에서 파일을 올려주세요.")
#     st.stop()

# selected = st.selectbox("확인할 파일(DataFrame) 선택", list(dfs.keys()))
# df = dfs[selected]

# c1, c2, c3 = st.columns(3) #화면을 3개로 나눠서 표시
# c1.metric("Rows", f"{len(df):,}")
# c2.metric("Cols", f"{df.shape[1]:,}")
# c3.metric("Missing(%)", f"{(df.isna().mean().mean() * 100):.1f}%")

# search = st.text_input("빠른 검색(문자열 포함 행 필터)")
# view = df
# if search:
#     mask = df.astype(str).apply(lambda row: row.str.contains(search, case=False, na=False)).any(axis=1)
#     view = df[mask]

# st.dataframe(view, use_container_width=True, height=560)

# with st.expander("🧾 컬럼명", expanded=False):
#     st.write(list(df.columns))

# d1, d2 = st.columns(2)
# with d1:
#     csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
#     st.download_button("⬇️ CSV 다운로드", data=csv_bytes, file_name=f"{selected}.csv", mime="text/csv")

# with d2:
#     buf = io.BytesIO()
#     with pd.ExcelWriter(buf, engine="openpyxl") as writer:
#         df.to_excel(writer, index=False, sheet_name="processed")
#     st.download_button(
#         "⬇️ Excel 다운로드",
#         data=buf.getvalue(),
#         file_name=f"{selected}_processed.xlsx",
#         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )
