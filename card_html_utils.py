"""
generate_inventory_html(df)
────────────────────────────
df를 받아 자재별 카드형 인터랙티브 HTML을 반환합니다.

Streamlit:
    import streamlit.components.v1 as components
    components.html(generate_inventory_html(df), height=...)

Jupyter:
    from IPython.display import HTML, display
    display(HTML(generate_inventory_html(df)))
"""

import math
import pandas as pd

FIXED_COLS = ["자재코드", "자재내역", "3평판", "SF", "당월출하", "판매율(평판)", "판매율(SF)"]

# 색상 팔레트
COLOR_RED    = "#E24B4A"
COLOR_ORANGE = "#EF9F27"
COLOR_BLUE   = "#85B7EB"
COLOR_GRAY   = "#9CA3AF"


def _rate_meta(rate_val):
    """(badge_text, color, is_nan) 반환"""
    try:
        v = float(rate_val)
        if math.isnan(v):
            return "산출불가", COLOR_GRAY, True
    except (TypeError, ValueError):
        return "산출불가", COLOR_GRAY, True
    if v > 1.0:
        return "판매율 급등", COLOR_RED, False
    elif v >= 0.8:
        return "주의", COLOR_ORANGE, False
    else:
        return "안정", COLOR_BLUE, False


def _heatmap_bg(value, max_value, hex_color):
    """재고량 → 배경색 (0이면 연한 회색, 있으면 hex_color 계열 그라데이션)"""
    if value == 0 or max_value == 0:
        return "#F1F5F9"
    palette = {
        COLOR_RED:    (226, 75,  74),
        COLOR_ORANGE: (239, 159, 39),
        COLOR_BLUE:   (133, 183, 235),
        COLOR_GRAY:   (156, 163, 175),
    }
    r, g, b = palette.get(hex_color, (133, 183, 235))
    alpha = 0.18 + (value / max_value) * 0.62   # 0.18 ~ 0.80
    br = int(r * alpha + 255 * (1 - alpha))
    bg = int(g * alpha + 255 * (1 - alpha))
    bb = int(b * alpha + 255 * (1 - alpha))
    return f"rgb({br},{bg},{bb})"


def _fmt(v):
    try:
        return f"{int(v):,}"
    except Exception:
        return str(v)


def _card(row, warehouse_cols):
    mat_code = str(row.get("자재코드", ""))
    mat_name = str(row.get("자재내역", ""))
    평판_3   = row.get("3평판",   0)
    sf       = row.get("SF",      0)
    출하     = row.get("당월출하", 0)
    rate_sf  = row.get("판매율(SF)", None)

    badge_text, color, is_nan = _rate_meta(rate_sf)

    badge_bg_map = {
        COLOR_RED:    "rgba(226,75,74,0.10)",
        COLOR_ORANGE: "rgba(239,159,39,0.10)",
        COLOR_BLUE:   "rgba(133,183,235,0.15)",
        COLOR_GRAY:   "rgba(156,163,175,0.12)",
    }
    badge_bg = badge_bg_map[color]

    # ── 1. 헤더
    header = f"""
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:8px;">
      <div>
        <span style="font-size:0.93rem;font-weight:700;color:#1E293B;">{mat_name}</span>
        <span style="font-size:0.72rem;color:#94A3B8;margin-left:8px;">{mat_code}</span>
      </div>
      <span style="flex-shrink:0;background:{badge_bg};color:{color};border:1px solid {color};
                   border-radius:12px;padding:2px 10px;font-size:0.68rem;font-weight:700;margin-left:12px;">
        {badge_text}
      </span>
    </div>"""

    # ── 2. 서브 정보
    sub = f"""
    <div style="font-size:0.74rem;color:#64748B;margin-bottom:10px;">
      <span style="margin-right:14px;">3평판&nbsp;<b style="color:#334155;">{_fmt(평판_3)}</b></span>
      <span style="margin-right:14px;">SF&nbsp;<b style="color:#334155;">{_fmt(sf)}</b></span>
      <span>당월출하&nbsp;<b style="color:#334155;">{_fmt(출하)}</b></span>
    </div>"""

    # ── 3. 프로그레스 바
    if is_nan:
        bar = '<div style="font-size:0.82rem;color:#94A3B8;margin-bottom:12px;font-weight:600;">N/A</div>'
    else:
        pct = float(rate_sf) * 100
        bar_w = min((pct / 150) * 100, 100)   # 150% 기준 → 100% 너비
        bar = f"""
        <div style="margin-bottom:14px;">
          <div style="font-size:0.78rem;font-weight:700;color:{color};margin-bottom:4px;">{pct:.1f}%</div>
          <div style="background:#E2E8F0;border-radius:6px;height:10px;overflow:hidden;">
            <div style="width:{bar_w:.2f}%;background:{color};height:100%;border-radius:6px;
                        transition:width 0.4s ease;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:0.62rem;color:#CBD5E1;margin-top:2px;">
            <span>0%</span><span>50%</span><span>100%</span><span>150%</span>
          </div>
        </div>"""

    # ── 4. 창고 히트맵
    wh_vals = {}
    for wh in warehouse_cols:
        v = row.get(wh, 0)
        try:
            wh_vals[wh] = int(v) if pd.notna(v) else 0
        except Exception:
            wh_vals[wh] = 0

    max_val = max(wh_vals.values()) if wh_vals else 0

    cells = ""
    for wh, val in wh_vals.items():
        bg  = _heatmap_bg(val, max_val, color)
        txt = "#1E293B" if val > 0 else "#94A3B8"
        cells += f"""
        <div style="width:52px;height:36px;background:{bg};border-radius:6px;
                    display:flex;flex-direction:column;align-items:center;justify-content:center;
                    border:1px solid rgba(0,0,0,0.06);margin:2px;">
          <div style="font-size:0.58rem;font-weight:700;color:{txt};line-height:1.3;">{wh}</div>
          <div style="font-size:0.7rem;font-weight:600;color:{txt};line-height:1.3;">{val:,}</div>
        </div>"""

    wh_section = f"""
    <div>
      <div style="font-size:0.63rem;font-weight:700;color:#94A3B8;text-transform:uppercase;
                  letter-spacing:1.1px;margin-bottom:6px;">창고별 보유 재고</div>
      <div style="display:flex;flex-wrap:wrap;">{cells}</div>
    </div>"""

    return f"""
    <div style="background:#FFFFFF;border:0.5px solid #E2E8F0;border-radius:12px;
                padding:16px 20px;margin-bottom:12px;
                box-shadow:0 1px 4px rgba(0,0,0,0.05);">
      {header}
      {sub}
      {bar}
      {wh_section}
    </div>"""


def _legend():
    return """
    <div style="background:#F8FAFC;border:0.5px solid #E2E8F0;border-radius:10px;
                padding:12px 16px;margin-top:4px;">
      <div style="font-size:0.63rem;font-weight:700;color:#94A3B8;text-transform:uppercase;
                  letter-spacing:1.1px;margin-bottom:8px;">범례</div>
      <div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;">
        <div style="display:flex;align-items:center;gap:5px;">
          <div style="width:9px;height:9px;border-radius:2px;background:#E24B4A;flex-shrink:0;"></div>
          <span style="font-size:0.71rem;color:#64748B;">판매율 &gt; 100% (급등)</span>
        </div>
        <div style="display:flex;align-items:center;gap:5px;">
          <div style="width:9px;height:9px;border-radius:2px;background:#EF9F27;flex-shrink:0;"></div>
          <span style="font-size:0.71rem;color:#64748B;">판매율 80~100% (주의)</span>
        </div>
        <div style="display:flex;align-items:center;gap:5px;">
          <div style="width:9px;height:9px;border-radius:2px;background:#85B7EB;flex-shrink:0;"></div>
          <span style="font-size:0.71rem;color:#64748B;">판매율 &lt; 80% (안정)</span>
        </div>
        <div style="display:flex;align-items:center;gap:5px;">
          <div style="width:9px;height:9px;border-radius:2px;background:#9CA3AF;flex-shrink:0;"></div>
          <span style="font-size:0.71rem;color:#64748B;">산출불가 (분모=0)</span>
        </div>
        <div style="margin-left:auto;font-size:0.68rem;color:#94A3B8;white-space:nowrap;">
          판매율(SF) = 당월출하 ÷ SF &nbsp;|&nbsp; 프로그레스바: 150% 기준
        </div>
      </div>
      <div style="margin-top:6px;font-size:0.66rem;color:#CBD5E1;">
        히트맵: 자재별 최대 재고 창고가 가장 진한 색. 재고 0 = 연한 회색.
      </div>
    </div>"""


def generate_inventory_html(df: pd.DataFrame) -> str:
    """
    df를 받아 자재별 카드형 인터랙티브 HTML 문자열을 반환.

    Parameters
    ----------
    df : DataFrame
        po_utils._build_po_dataframe() 이 반환하는 형태.
        필수 컬럼: 자재코드, 자재내역, 3평판, SF, 당월출하, 판매율(SF)
        창고 컬럼: 숫자 4자리 컬럼명 (예: 5000, 5010, ...)

    Returns
    -------
    str : 완성된 HTML 문자열
    """
    # 창고 컬럼 자동 감지 (숫자 4자리)
    warehouse_cols = [
        c for c in df.columns
        if str(c).strip().isdigit() and len(str(c).strip()) == 4
    ]

    # 판매율(SF) 내림차순 정렬 (NaN 맨 뒤)
    if "판매율(SF)" in df.columns:
        sorted_df = df.sort_values("판매율(SF)", ascending=False, na_position="last").reset_index(drop=True)
    else:
        sorted_df = df.copy()

    cards = "".join(_card(row, warehouse_cols) for _, row in sorted_df.iterrows())

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
    background: transparent;
    color: #1E293B;
  }}
</style>
</head>
<body>
<div style="padding:4px 0;">
  {cards}
  {_legend()}
</div>
</body>
</html>"""
