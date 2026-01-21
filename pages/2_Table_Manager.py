import io
import streamlit as st
import pandas as pd

st.set_page_config(page_title="S&OP System - Table Manager", layout="wide")
st.title("🗂️ 테이블 관리 (DF 확인)")

dfs = st.session_state.get("dfs", {})

if not dfs:
    st.warning("아직 업로드된 데이터가 없습니다. 먼저 '데이터 업로드' 페이지에서 파일을 올려주세요.")
    st.stop()

selected = st.selectbox("확인할 파일(DataFrame) 선택", list(dfs.keys()))
df = dfs[selected]

c1, c2, c3 = st.columns(3) #화면을 3개로 나눠서 표시
c1.metric("Rows", f"{len(df):,}")
c2.metric("Cols", f"{df.shape[1]:,}")
c3.metric("Missing(%)", f"{(df.isna().mean().mean() * 100):.1f}%")

search = st.text_input("빠른 검색(문자열 포함 행 필터)")
view = df
if search:
    mask = df.astype(str).apply(lambda row: row.str.contains(search, case=False, na=False)).any(axis=1)
    view = df[mask]

st.dataframe(view, use_container_width=True, height=560)

with st.expander("🧾 컬럼명", expanded=False):
    st.write(list(df.columns))

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
