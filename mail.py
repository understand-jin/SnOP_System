# import os
# import time
# import smtplib
# import schedule
# import pandas as pd
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart

# # ---------------------------
# # Gmail SMTP 정보
# # ---------------------------
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = 587

# SMTP_USER = "sotorl0005@gmail.com"
# SMTP_PASS = "haxh wnik ycoh amaw"

# # 여러 명에게 보낼 경우 리스트로 관리
# TO_EMAILS = [
#     "2600144@daewoong.co.kr",
#     "2240410@daewoong.co.kr",
# ]

# # ---------------------------
# # 📄 데이터 경로
# # ---------------------------
# STOCK_PATH = os.path.join("Datas", "2025년", "12월", "Stock.csv")

# # ---------------------------
# # ✅ Stock.csv 고정 컬럼명
# # ---------------------------
# MAT_COL   = "자재"
# DESC_COL  = "자재 내역"
# EXP_COL   = "유효 기한"
# QTY_COL   = "Stock Quantity on Period End"
# VAL_COL   = "Stock Value on Period End"

# DAYS_6M = 180
# DAYS_9M = 270


# def fmt_won_int(x: float) -> str:
#     return f"₩{int(round(x)):,}"


# def safe_num(series: pd.Series) -> pd.Series:
#     return pd.to_numeric(
#         series.astype(str)
#               .str.replace(",", "", regex=False)
#               .str.replace("원", "", regex=False)
#               .str.strip(),
#         errors="coerce"
#     )


# def load_and_summarize_by_expiry(stock_path: str):
#     df = pd.read_csv(stock_path, encoding="utf-8-sig")

#     today = pd.Timestamp.today().normalize()
#     df["_expiry"] = pd.to_datetime(df[EXP_COL], errors="coerce")
#     df["_days_to_expiry"] = (df["_expiry"] - today).dt.days

#     df["_qty"] = safe_num(df[QTY_COL]).fillna(0)
#     df["_val"] = safe_num(df[VAL_COL]).fillna(0)

#     valid = df.dropna(subset=["_expiry"]).copy()
#     valid = valid[valid["_days_to_expiry"] >= 0]  # 만료(음수) 제외

#     df_6 = valid[valid["_days_to_expiry"] < DAYS_6M]
#     df_9 = valid[valid["_days_to_expiry"] < DAYS_9M]

#     cnt_6 = int(df_6[MAT_COL].nunique())
#     sum_6 = float(df_6["_val"].sum())

#     cnt_9 = int(df_9[MAT_COL].nunique())
#     sum_9 = float(df_9["_val"].sum())

#     top6 = (
#         df_6.groupby([MAT_COL, DESC_COL], as_index=False)
#             .agg({"_qty": "sum", "_val": "sum"})
#             .sort_values("_val", ascending=False)
#             .head(10)
#             .reset_index(drop=True)
#     )

#     top9 = (
#         df_9.groupby([MAT_COL, DESC_COL], as_index=False)
#             .agg({"_qty": "sum", "_val": "sum"})
#             .sort_values("_val", ascending=False)
#             .head(10)
#             .reset_index(drop=True)
#     )

#     return {
#         "today": today,
#         "cnt_6": cnt_6,
#         "sum_6": sum_6,
#         "cnt_9": cnt_9,
#         "sum_9": sum_9,
#         "top6": top6,
#         "top9": top9,
#         "file_path": stock_path,
#     }


# def df_to_html_table(df: pd.DataFrame, title: str) -> str:
#     """이메일에서 잘 보이도록 인라인 스타일로 테이블 생성"""
#     if df.empty:
#         return f"""
#         <div style="margin-top:14px;">
#           <div style="font-weight:700; margin-bottom:8px;">{title}</div>
#           <div style="color:#666;">해당 없음</div>
#         </div>
#         """

#     view = df.copy()
#     view.index = view.index + 1  # 1부터
#     view = view.rename(columns={
#         MAT_COL: "자재",
#         DESC_COL: "자재 내역",
#         "_qty": "부진재고 수량",
#         "_val": "부진재고 금액",
#     })
#     view["부진재고 수량"] = view["부진재고 수량"].round(0).astype(int).map(lambda x: f"{x:,}")
#     view["부진재고 금액"] = view["부진재고 금액"].map(fmt_won_int)

#     header_html = "".join([
#         f'<th style="border-bottom:1px solid #e5e7eb; padding:10px; text-align:left; font-size:13px; color:#111;">{col}</th>'
#         for col in (["No"] + list(view.columns))
#     ])

#     rows_html = ""
#     for idx, row in view.iterrows():
#         bg = "#fafafa" if idx % 2 == 0 else "#ffffff"
#         cells = [str(idx)] + [str(row[c]) for c in view.columns]
#         row_html = "".join([
#             f'<td style="border-bottom:1px solid #f0f0f0; padding:10px; font-size:13px; color:#111; vertical-align:top;">{cell}</td>'
#             for cell in cells
#         ])
#         rows_html += f'<tr style="background:{bg};">{row_html}</tr>'

#     return f"""
#     <div style="margin-top:18px;">
#       <div style="font-weight:700; margin-bottom:10px; font-size:14px;">{title}</div>
#       <div style="border:1px solid #e5e7eb; border-radius:10px; overflow:hidden;">
#         <table style="border-collapse:collapse; width:100%; font-family:Arial, sans-serif;">
#           <thead style="background:#f3f4f6;">
#             <tr>{header_html}</tr>
#           </thead>
#           <tbody>
#             {rows_html}
#           </tbody>
#         </table>
#       </div>
#     </div>
#     """


# def build_html_email(summary: dict) -> str:
#     card_style = (
#         "border:1px solid #e5e7eb; border-radius:12px; padding:14px; "
#         "display:inline-block; margin-right:12px; min-width:220px; background:#fff;"
#     )
#     kpi_label = "color:#6b7280; font-size:12px; margin-bottom:6px;"
#     kpi_value = "font-size:26px; font-weight:800; color:#111;"

#     return f"""
#     <div style="font-family:Arial, sans-serif; color:#111; line-height:1.5;">
#       <div style="font-size:15px; margin-bottom:8px;">안녕하세요.</div>
#       <div style="font-size:14px; color:#374151;">
#         금일(<b>{summary['today'].strftime('%Y-%m-%d')}</b>) 기준, Stock.csv의 유효기한과 오늘 일자를 비교하여
#         부진재고/부진위험재고 현황을 공유드립니다.
#       </div>

#       <div style="margin-top:12px; font-size:12px; color:#6b7280;">
#         기준 파일: {summary['file_path']}
#       </div>

#       <div style="margin-top:16px;">
#         <div style="{card_style}">
#           <div style="{kpi_label}">6개월 미만 자재 수</div>
#           <div style="{kpi_value}">{summary['cnt_6']:,}종</div>
#         </div>
#         <div style="{card_style}">
#           <div style="{kpi_label}">6개월 미만 총 위험 금액</div>
#           <div style="{kpi_value}">{fmt_won_int(summary['sum_6'])}</div>
#         </div>
#       </div>

#       <div style="margin-top:12px;">
#         <div style="{card_style}">
#           <div style="{kpi_label}">9개월 미만 자재 수</div>
#           <div style="{kpi_value}">{summary['cnt_9']:,}종</div>
#         </div>
#         <div style="{card_style}">
#           <div style="{kpi_label}">9개월 미만 총 위험 금액</div>
#           <div style="{kpi_value}">{fmt_won_int(summary['sum_9'])}</div>
#         </div>
#       </div>

#       {df_to_html_table(summary['top6'], "6개월 미만 TOP10 (금액 기준)")}
#       {df_to_html_table(summary['top9'], "9개월 미만 TOP10 (금액 기준)")}

#       <div style="margin-top:18px; font-size:12px; color:#6b7280;">
#         ※ 상세 내용은 S&OP 시스템 참고 부탁드립니다.
#       </div>
#       <div style="margin-top:10px; font-size:14px;">감사합니다.</div>
#     </div>
#     """


# def send_mail():
#     summary = load_and_summarize_by_expiry(STOCK_PATH)

#     msg = MIMEMultipart("alternative")
#     msg["From"] = SMTP_USER
#     msg["To"] = ", ".join(TO_EMAILS)
#     msg["Subject"] = "[보고] S&OP 부진재고 / 부진위험재고 자동알림"

#     text_body = f"""안녕하세요.

# 금일({summary['today'].strftime('%Y-%m-%d')}) 기준 부진재고/부진위험재고 현황입니다.

# - 6개월 미만: {summary['cnt_6']}종 / {int(round(summary['sum_6'])):,}원
# - 9개월 미만: {summary['cnt_9']}종 / {int(round(summary['sum_9'])):,}원

# (상세는 S&OP 시스템 참고)
# """
#     html_body = build_html_email(summary)

#     msg.attach(MIMEText(text_body, "plain", "utf-8"))
#     msg.attach(MIMEText(html_body, "html", "utf-8"))

#     with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#         server.starttls()
#         server.login(SMTP_USER, SMTP_PASS)

#         # ✅ 여러 수신자 안정 발송: sendmail 사용
#         server.sendmail(SMTP_USER, TO_EMAILS, msg.as_string())

#     print("✅ HTML 메일 발송 완료")


# # ---------------------------
# # ⏰ 매일 원하는 시간 스케줄링
# # ---------------------------
# schedule.every().day.at("09:30").do(send_mail)

# print("🕘 메일 스케줄러 실행 중... (종료하려면 Ctrl+C)")

# while True:
#     schedule.run_pending()
#     time.sleep(30)

import os
import time
import smtplib
import schedule
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------
# Gmail SMTP 정보
# ---------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SMTP_USER = "sotorl0005@gmail.com"
SMTP_PASS = "haxh wnik ycoh amaw"

TO_EMAILS = [
    "2600144@daewoong.co.kr",
    #"2240410@daewoong.co.kr",
]

# ---------------------------
# 📄 데이터 경로
# ---------------------------
STOCK_PATH = os.path.join("Datas", "2025년", "12월", "Stock.csv")

# ---------------------------
# ✅ Stock.csv 고정 컬럼명
# ---------------------------
MAT_COL   = "자재"
DESC_COL  = "자재 내역"
EXP_COL   = "유효 기한"
BATCH_COL = "배치"  # ✅ 추가 (Stock.csv에 없으면 자동 '-' 처리)
QTY_COL   = "Stock Quantity on Period End"
VAL_COL   = "Stock Value on Period End"

DAYS_6M = 180
DAYS_9M = 270


def fmt_won_int(x: float) -> str:
    return f"₩{int(round(x)):,}"


def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
              .str.replace(",", "", regex=False)
              .str.replace("원", "", regex=False)
              .str.strip(),
        errors="coerce"
    )


def load_and_summarize_by_expiry(stock_path: str):
    df = pd.read_csv(stock_path, encoding="utf-8-sig")

    # 배치 컬럼이 없으면 만들어두기 (메일 표 형식 유지용)
    if BATCH_COL not in df.columns:
        df[BATCH_COL] = None

    today = pd.Timestamp.today().normalize()
    df["_expiry"] = pd.to_datetime(df[EXP_COL], errors="coerce")
    df["_days_to_expiry"] = (df["_expiry"] - today).dt.days

    df["_qty"] = safe_num(df[QTY_COL]).fillna(0)
    df["_val"] = safe_num(df[VAL_COL]).fillna(0)

    valid = df.dropna(subset=["_expiry"]).copy()
    valid = valid[valid["_days_to_expiry"] >= 0]  # 만료(음수) 제외

    df_6 = valid[valid["_days_to_expiry"] < DAYS_6M]
    df_9 = valid[valid["_days_to_expiry"] < DAYS_9M]

    cnt_6 = int(df_6[MAT_COL].nunique())
    sum_6 = float(df_6["_val"].sum())

    cnt_9 = int(df_9[MAT_COL].nunique())
    sum_9 = float(df_9["_val"].sum())

    # ✅ Streamlit 표처럼 "배치수/배치목록" 포함 집계
    def build_top(df_filtered: pd.DataFrame) -> pd.DataFrame:
        out = (
            df_filtered.groupby([MAT_COL, DESC_COL], as_index=False)
            .agg(
                배치수=(BATCH_COL, "nunique"),
                배치목록=(BATCH_COL, lambda s: ", ".join(map(str, pd.Series(s).dropna().astype(str).unique()[:10]))),
                _qty=("_qty", "sum"),
                _val=("_val", "sum"),
            )
            .sort_values("_val", ascending=False)
            .head(15)  # 필요하면 10으로 줄여도 됨
            .reset_index(drop=True)
        )

        # 배치목록이 비어있으면 '-'로
        out["배치목록"] = out["배치목록"].replace("", "-").fillna("-")
        return out

    top6 = build_top(df_6)
    top9 = build_top(df_9)

    return {
        "today": today,
        "cnt_6": cnt_6,
        "sum_6": sum_6,
        "cnt_9": cnt_9,
        "sum_9": sum_9,
        "top6": top6,
        "top9": top9,
        "file_path": stock_path,
    }


def df_to_html_table(df: pd.DataFrame, title: str) -> str:
    """이메일에서 잘 보이도록 인라인 스타일로 테이블 생성"""
    if df.empty:
        return f"""
        <div style="margin-top:14px;">
          <div style="font-weight:700; margin-bottom:8px;">{title}</div>
          <div style="color:#666;">해당 없음</div>
        </div>
        """

    view = df.copy()
    view.index = view.index + 1  # 1부터

    # ✅ 표시 컬럼명 (Streamlit 표와 동일 컨셉)
    view = view.rename(columns={
        MAT_COL: "자재",
        DESC_COL: "자재 내역",
        "_qty": "부진재고 수량",
        "_val": "부진재고 금액",
    })

    # 숫자 포맷
    if "부진재고 수량" in view.columns:
        view["부진재고 수량"] = pd.to_numeric(view["부진재고 수량"], errors="coerce").fillna(0).round(0).astype(int).map(lambda x: f"{x:,}")
    if "부진재고 금액" in view.columns:
        view["부진재고 금액"] = pd.to_numeric(view["부진재고 금액"], errors="coerce").fillna(0).map(fmt_won_int)
    if "배치수" in view.columns:
        view["배치수"] = pd.to_numeric(view["배치수"], errors="coerce").fillna(0).astype(int)

    # ✅ 컬럼 순서 지정
    cols = ["자재", "자재 내역", "배치수", "배치목록", "부진재고 수량", "부진재고 금액"]
    cols = [c for c in cols if c in view.columns]
    view = view[cols]

    header_html = "".join([
        f'<th style="border-bottom:1px solid #e5e7eb; padding:10px; text-align:left; font-size:13px; color:#111;">{col}</th>'
        for col in (["No"] + list(view.columns))
    ])

    rows_html = ""
    for idx, row in view.iterrows():
        bg = "#fafafa" if idx % 2 == 0 else "#ffffff"
        cells = [str(idx)] + [str(row[c]) for c in view.columns]
        row_html = "".join([
            f'<td style="border-bottom:1px solid #f0f0f0; padding:10px; font-size:13px; color:#111; vertical-align:top;">{cell}</td>'
            for cell in cells
        ])
        rows_html += f'<tr style="background:{bg};">{row_html}</tr>'

    return f"""
    <div style="margin-top:18px;">
      <div style="font-weight:700; margin-bottom:10px; font-size:14px;">{title}</div>
      <div style="border:1px solid #e5e7eb; border-radius:10px; overflow:hidden;">
        <table style="border-collapse:collapse; width:100%; font-family:Arial, sans-serif;">
          <thead style="background:#f3f4f6;">
            <tr>{header_html}</tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </div>
    """


def build_html_email(summary: dict) -> str:
    card_style = (
        "border:1px solid #e5e7eb; border-radius:12px; padding:14px; "
        "display:inline-block; margin-right:12px; min-width:220px; background:#fff;"
    )
    kpi_label = "color:#6b7280; font-size:12px; margin-bottom:6px;"
    kpi_value = "font-size:26px; font-weight:800; color:#111;"

    return f"""
    <div style="font-family:Arial, sans-serif; color:#111; line-height:1.5;">
      <div style="font-size:15px; margin-bottom:8px;">안녕하세요.</div>
      <div style="font-size:14px; color:#374151;">
        금일(<b>{summary['today'].strftime('%Y-%m-%d')}</b>) 기준, Stock.csv의 유효기한과 오늘 일자를 비교하여
        부진재고/부진위험재고 현황을 공유드립니다.
      </div>

      <div style="margin-top:12px; font-size:12px; color:#6b7280;">
        기준 파일: {summary['file_path']}
      </div>

      <div style="margin-top:16px;">
        <div style="{card_style}">
          <div style="{kpi_label}">6개월 미만 자재 수</div>
          <div style="{kpi_value}">{summary['cnt_6']:,}종</div>
        </div>
        <div style="{card_style}">
          <div style="{kpi_label}">6개월 미만 총 위험 금액</div>
          <div style="{kpi_value}">{fmt_won_int(summary['sum_6'])}</div>
        </div>
      </div>

      <div style="margin-top:12px;">
        <div style="{card_style}">
          <div style="{kpi_label}">9개월 미만 자재 수</div>
          <div style="{kpi_value}">{summary['cnt_9']:,}종</div>
        </div>
        <div style="{card_style}">
          <div style="{kpi_label}">9개월 미만 총 위험 금액</div>
          <div style="{kpi_value}">{fmt_won_int(summary['sum_9'])}</div>
        </div>
      </div>

      {df_to_html_table(summary['top6'], "6개월 미만 TOP (금액 기준)")}
      {df_to_html_table(summary['top9'], "9개월 미만 TOP (금액 기준)")}

      <div style="margin-top:18px; font-size:12px; color:#6b7280;">
        ※ 상세 내용은 S&OP 시스템 참고 부탁드립니다.
      </div>
      <div style="margin-top:10px; font-size:14px;">감사합니다.</div>
    </div>
    """


def send_mail():
    summary = load_and_summarize_by_expiry(STOCK_PATH)

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Subject"] = "[보고] S&OP 부진재고 / 부진위험재고 자동알림"

    text_body = f"""안녕하세요.

금일({summary['today'].strftime('%Y-%m-%d')}) 기준 부진재고/부진위험재고 현황입니다.

- 6개월 미만: {summary['cnt_6']}종 / {int(round(summary['sum_6'])):,}원
- 9개월 미만: {summary['cnt_9']}종 / {int(round(summary['sum_9'])):,}원

(상세는 S&OP 시스템 참고)
"""
    html_body = build_html_email(summary)

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, TO_EMAILS, msg.as_string())

    print("✅ HTML 메일 발송 완료")


# ---------------------------
# ⏰ 매일 원하는 시간 스케줄링
# ---------------------------
schedule.every().day.at("10:05").do(send_mail)

print("🕘 메일 스케줄러 실행 중... (종료하려면 Ctrl+C)")

while True:
    schedule.run_pending()
    time.sleep(30)
