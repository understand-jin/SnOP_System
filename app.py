import streamlit as st

st.set_page_config(page_title="S&OP System", layout="wide")
st.title("📊S&OP System")

st.markdown(
    """
왼쪽 사이드바에서 페이지를 선택하세요.

1) **데이터 업로드**: 파일 업로드 & 표 자동 추출  
2) **테이블 관리**: 업로드된 DF 확인/검색/다운로드  
3) **시각화**: 선택한 DF로 차트 생성
"""
)

st.info("먼저 **데이터 업로드** 페이지에서 파일을 올려주세요.")


