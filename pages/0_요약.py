import streamlit as st
from pathlib import Path

st.set_page_config(page_title="요약", layout="wide")

###############################################################################
# 🎨 UI 스타일링 (Dashboard CSS)
###############################################################################
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #EEF2F7; }
.main .block-container { padding-top: 0 !important; padding-bottom: 2rem; padding-left: 2rem; padding-right: 2rem; max-width: 100%; }
/* 사이드바 */
[data-testid="stSidebar"] { background: #0B1E3F !important; border-right: none; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebarNav"] { padding: 0.5rem; }
[data-testid="stSidebarNav"] a { border-radius: 8px; padding: 0.55rem 0.9rem !important; margin-bottom: 2px; font-size: 0.875rem; font-weight: 500; color: #94A3B8 !important; display: block; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.08) !important; color: #E2E8F0 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(37,99,235,0.3) !important; color: #FFFFFF !important; font-weight: 600; border-left: 3px solid #3B82F6; }
[data-testid="stSidebarNav"] span { color: inherit !important; }
/* 헤더 배너 */
.dash-header { background: linear-gradient(135deg, #0B1E3F 0%, #1565C0 100%); margin: -1px -2rem 2rem -2rem; padding: 1.2rem 2.5rem; display: flex; align-items: center; justify-content: space-between; }
.dash-header-title { color: #FFFFFF; font-size: 1.25rem; font-weight: 700; }
.dash-header-sub { color: #93C5FD; font-size: 0.75rem; margin-top: 2px; }
.dash-badge { background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2); color: #E0F2FE; font-size: 0.72rem; font-weight: 500; padding: 0.3rem 0.75rem; border-radius: 20px; }
/* 이미지 컨테이너 */
.image-container { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 4px rgba(15,23,42,0.06); }
hr { border: none; border-top: 1px solid #E9EEF5; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# 헤더 배너
st.markdown("""
<div class="dash-header">
    <div>
        <div class="dash-header-title">요약</div>
        <div class="dash-header-sub">S&OP 전체 현황 요약 보고</div>
    </div>
    <div style="display:flex;gap:8px;">
        <span class="dash-badge">Summary</span>
    </div>
</div>
""", unsafe_allow_html=True)

###############################################################################
# 이미지 표시
###############################################################################
image_path = Path(__file__).parent.parent / "요약.png"

if image_path.exists():
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.image(str(image_path), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.error(f"이미지 파일을 찾을 수 없습니다: {image_path}")
