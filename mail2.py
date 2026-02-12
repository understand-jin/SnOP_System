import os
import time
import smtplib
import schedule
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# ---------------------------
# 1) Gmail SMTP 정보
# ---------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SMTP_USER = "sotorl0005@gmail.com"
SMTP_PASS = "haxh wnik ycoh amaw"   # ✅ Gmail 앱 비밀번호 (공백 포함 그대로)

TO_EMAILS = [
    "2600144@daewoong.co.kr",
    # "2240410@daewoong.co.kr",
]


# ---------------------------
# 2) 분석 대상 설정 (년도/월만 바꾸면 됨)
# ---------------------------
TARGET_YEAR = "2025년"
TARGET_MONTH = "12월"

# 위 설정값을 바탕으로 자동으로 경로가 생성됩니다. (Stockout.csv 사용)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOCK_PATH = os.path.join(BASE_DIR, "Datas", TARGET_YEAR, TARGET_MONTH, "Stockout.csv")

MAT_COL = "자재"
MAT_NAME_COL = "자재 내역"
SALES_COL = "3평판"  # 월 판매량(3개월 평균 월판매량)
QTY_COL = "Stock Quantity on Period End"

# 기준
DAYS_WARN = 60
DAYS_RISK = 30


# ---------------------------
# Utils
# ---------------------------
def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce"
    ).fillna(0)


def fmt_int(x) -> str:
    try:
        return f"{int(round(float(x))):,}"
    except Exception:
        return "0"


def row_bg_color(grade: str) -> str:
    if grade == "위험":
        return "#ffe4e6"  # 연빨강
    if grade == "주의":
        return "#ffedd5"  # 연주황
    return "#ffffff"


# ---------------------------
# 3) 데이터 로드 및 계산 (Stockout.csv 기반)
# ---------------------------
def load_and_process() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not os.path.exists(STOCK_PATH):
        raise FileNotFoundError(f"Stockout.csv 파일을 찾을 수 없습니다: {STOCK_PATH}\n(먼저 웹에서 분석을 실행하여 파일을 생성해 주세요)")

    df = pd.read_csv(STOCK_PATH, encoding="utf-8-sig")

    # 필수 컬럼 체크 (Stockout.csv 기준)
    required = [MAT_COL, MAT_NAME_COL, SALES_COL, QTY_COL, "재고일수"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Stockout.csv에 필요한 컬럼이 없습니다: {missing}")

    # 숫자화
    df[SALES_COL] = safe_num(df[SALES_COL])
    df[QTY_COL] = safe_num(df[QTY_COL])
    df["재고일수"] = safe_num(df["재고일수"])

    # 60일 미만만 리스크
    risk_df = df[df["재고일수"] < DAYS_WARN].copy()
    if not risk_df.empty:
        risk_df["리스크 등급"] = risk_df["재고일수"].apply(lambda x: "위험" if x < DAYS_RISK else "주의")
        risk_df = risk_df.sort_values(["재고일수"], ascending=True).reset_index(drop=True)

    return df, risk_df


# ---------------------------
# 4) HTML 메일 본문 (부진재고 메일 스타일로)
# ---------------------------
def build_html_email(today_str: str, file_path: str, df_all: pd.DataFrame, df_risk: pd.DataFrame) -> str:
    risk_count = int((df_risk.get("리스크 등급") == "위험").sum()) if not df_risk.empty else 0
    caution_count = int((df_risk.get("리스크 등급") == "주의").sum()) if not df_risk.empty else 0
    total_count = int(len(df_all))

    card_style = (
        "border:1px solid #e5e7eb; border-radius:12px; padding:14px; "
        "display:inline-block; margin-right:12px; min-width:220px; background:#fff;"
    )
    kpi_label = "color:#6b7280; font-size:12px; margin-bottom:6px;"
    kpi_value = "font-size:22px; font-weight:800; color:#111;"

    # KPI 카드
    kpi_cards = f"""
    <div style="margin-top:16px;">
      <div style="{card_style} border-left:6px solid #ef4444;">
        <div style="{kpi_label}">위험 ({DAYS_RISK}일 미만)</div>
        <div style="{kpi_value}">{risk_count:,}종</div>
      </div>
      <div style="{card_style} border-left:6px solid #f59e0b;">
        <div style="{kpi_label}">주의 ({DAYS_WARN}일 미만)</div>
        <div style="{kpi_value}">{caution_count:,}종</div>
      </div>
      <div style="{card_style}">
        <div style="{kpi_label}">총 분석 대상</div>
        <div style="{kpi_value}">{total_count:,}종</div>
      </div>
    </div>
    """

    # 테이블
    if df_risk.empty:
        table_html = """
        <div style="margin-top:18px; padding:14px; border:1px solid #e5e7eb; border-radius:10px; color:#6b7280;">
          관리 대상 리스크가 없습니다.
        </div>
        """
    else:
        view = df_risk.copy()
        view["남은 재고일수"] = view["재고일수"].round(1).astype(float).map(lambda x: f"{x:.1f}일")
        view["3평판"] = pd.to_numeric(view[SALES_COL], errors="coerce").fillna(0).round(0).astype(int).map(lambda x: f"{x:,}")
        view["총재고량"] = pd.to_numeric(view[QTY_COL], errors="coerce").fillna(0).round(0).astype(int).map(lambda x: f"{x:,}")

        view = view.rename(columns={
            MAT_COL: "자재코드",
            MAT_NAME_COL: "자재내역",
        })[["리스크 등급", "자재코드", "자재내역", "남은 재고일수", "3평판", "총재고량"]]

        header_html = "".join([
            f'<th style="border-bottom:1px solid #e5e7eb; padding:10px; text-align:left; font-size:13px; color:#111;">{col}</th>'
            for col in (["No"] + list(view.columns))
        ])

        rows_html = ""
        for i, (_, row) in enumerate(view.iterrows(), start=1):
            bg = row_bg_color(str(row["리스크 등급"]))
            cells = [str(i)] + [str(row[c]) for c in view.columns]
            row_html = "".join([
                f'<td style="border-bottom:1px solid #f0f0f0; padding:10px; font-size:13px; color:#111; vertical-align:top;">{cell}</td>'
                for cell in cells
            ])
            rows_html += f'<tr style="background:{bg};">{row_html}</tr>'

        table_html = f"""
        <div style="margin-top:18px;">
          <div style="font-weight:700; margin-bottom:10px; font-size:14px;">📋 품절 리스크 상세 리스트 (재고일수 {DAYS_WARN}일 미만)</div>

          <div style="margin-bottom:8px; font-size:12px; color:#6b7280;">
            <span style="background:#ffe4e6; padding:2px 8px; border-radius:999px; margin-right:6px;">위험</span>
            <span style="background:#ffedd5; padding:2px 8px; border-radius:999px;">주의</span>
          </div>

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

    return f"""
    <div style="font-family:Arial, sans-serif; color:#111; line-height:1.5;">
      <div style="font-size:15px; margin-bottom:6px;">안녕하세요.</div>
      <div style="font-size:14px; color:#374151;">
        금일(<b>{today_str}</b>) 기준, <b>재고일수 30일 미만(위험) 및 60일 미만(주의)</b> 품목을 분류하여 공유드립니다.
      </div>

      <div style="margin-top:10px; font-size:12px; color:#6b7280;">
        기준 파일: {file_path}
      </div>

      {kpi_cards}

      <div style="margin-top:12px; font-size:12px; color:#6b7280;">
        ※ 재고일수 계산: 재고수량 / (3평판/30) (단, 3평판이 0이면 999일로 처리)
      </div>

      {table_html}

      <div style="margin-top:18px; font-size:12px; color:#6b7280;">
        ※ 본 메일은 S&OP 자동화 시스템에 의해 발송되었습니다.
      </div>
      <div style="margin-top:10px; font-size:14px;">감사합니다.</div>
    </div>
    """


# ---------------------------
# 5) 메일 발송
# ---------------------------
def send_stockout_mail():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 메일 발송 시작")

    df_all, df_risk = load_and_process()

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Subject"] = f"[보고] 품절 리스크 현황 ({today_str})"

    # text(간단) + html(예쁜 본문)
    text_body = (
        f"금일({today_str}) 기준 품절 리스크(재고일수 {DAYS_WARN}일 미만) 현황입니다.\n"
        f"- 위험({DAYS_RISK}일 미만): {int((df_risk.get('리스크 등급')=='위험').sum()) if not df_risk.empty else 0}종\n"
        f"- 주의({DAYS_WARN}일 미만): {int((df_risk.get('리스크 등급')=='주의').sum()) if not df_risk.empty else 0}종\n"
        f"(상세는 HTML 본문 참고)\n"
    )
    html_body = build_html_email(today_str, STOCK_PATH, df_all, df_risk)

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, TO_EMAILS, msg.as_string())

    print("✅ 메일 발송 완료")


# ---------------------------
# 6) 스케줄링
# ---------------------------
if __name__ == "__main__":
    # ✅ 즉시 테스트 발송 원하면 True로
    SEND_NOW_FOR_TEST = False
    if SEND_NOW_FOR_TEST:
        send_stockout_mail()

    SEND_TIME = "15:56"   # 여기를 원하는 시간으로
    schedule.every().day.at(SEND_TIME).do(send_stockout_mail)

    print(f"🕘 메일 스케줄러 실행 중... (매일 {SEND_TIME} 발송, 종료 Ctrl+C)")
    while True:
        schedule.run_pending()
        time.sleep(30)
