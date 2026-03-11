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
SMTP_PASS = "haxh wnik ycoh amaw"   # ✅ Gmail 앱 비밀번호 (공백 포함 그대로)

TO_EMAILS = [
    "2600144@daewoong.co.kr",
    #"2240410@daewoong.co.kr",
]

# ---------------------------
# 📄 데이터 경로 몇년도, 월 여기서 선택해주면 됨
# ---------------------------
STOCK_PATH = os.path.join("Datas", "2025년", "12월", "Stock.csv")

# ---------------------------
# ✅ Stock.csv 고정 컬럼명
# ---------------------------
MAT_COL   = "자재"
DESC_COL  = "자재 내역"
EXP_COL   = "유효 기한"   # 만료일(날짜)
BATCH_COL = "배치"        # 없으면 자동 생성
QTY_COL   = "Stock Quantity on Period End"
VAL_COL   = "Stock Value on Period End"

# ---- (계산 컬럼) ----
DAYS_COL   = "days_to_expiry"
BUCKET_COL = "bucket"

# ---- 이번 메일 기준: 1~9개월 미만까지 ----
MAX_MONTH = 9
MAX_DAYS = 30 * MAX_MONTH  # 270일


# ---------------------------
# Utils
# ---------------------------
def fmt_won_int(x: float) -> str:
    try:
        return f"₩{int(round(float(x))):,}"
    except Exception:
        return "₩0"


def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
              .str.replace(",", "", regex=False)
              .str.replace("원", "", regex=False)
              .str.strip(),
        errors="coerce"
    )


def to_bucket(days: float) -> str:
    """오늘 기준 days_to_expiry를 1~12개월 미만/이상으로 라벨링"""
    if pd.isna(days):
        return "유효기한 없음"
    if days < 0:
        return "폐기확정(유효기한 지남)"
    if days < 30:
        return "1개월 미만"
    if days < 60:
        return "2개월 미만"
    if days < 90:
        return "3개월 미만"
    if days < 120:
        return "4개월 미만"
    if days < 150:
        return "5개월 미만"
    if days < 180:
        return "6개월 미만"
    if days < 210:
        return "7개월 미만"
    if days < 240:
        return "8개월 미만"
    if days < 270:
        return "9개월 미만"
    if days < 300:
        return "10개월 미만"
    if days < 330:
        return "11개월 미만"
    if days < 365:
        return "12개월 미만"
    return "12개월 이상"


def load_prepare(stock_path: str) -> pd.DataFrame:
    df = pd.read_csv(stock_path, encoding="utf-8-sig")

    # 배치 컬럼 없으면 생성
    if BATCH_COL not in df.columns:
        df[BATCH_COL] = None

    # 만료일/남은일 계산
    today = pd.Timestamp.today().normalize()
    df["_expiry"] = pd.to_datetime(df[EXP_COL], errors="coerce")
    df[DAYS_COL] = (df["_expiry"] - today).dt.days

    # 수량/금액 숫자화
    df["_qty"] = safe_num(df[QTY_COL]).fillna(0)
    df["_val"] = safe_num(df[VAL_COL]).fillna(0)

    # 버킷 재계산
    df[BUCKET_COL] = df[DAYS_COL].apply(to_bucket)

    return df


def build_batch_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    (자재+배치) 단위로 집계:
    - 부진재고 수량/금액 (합)
    - 남은일(최소), 유효기간(최소), 3평판(first), 버킷(first)
    """
    out = (
        df.groupby([MAT_COL, DESC_COL, BATCH_COL], as_index=False)
          .agg(
              **{
                  "_qty": ("_qty", "sum"),
                  "_val": ("_val", "sum"),
                  DAYS_COL: (DAYS_COL, "min"),
                  "_expiry": ("_expiry", "min"),
                  "3평판": ("3평판", "first") if "3평판" in df.columns else (MAT_COL, "size"),
                  BUCKET_COL: (BUCKET_COL, "first"),
              }
          )
    )
    # 정렬: 남은일 오름차순(급한 순) -> 금액 내림차순
    out = out.sort_values(by=[DAYS_COL, "_val"], ascending=[True, False], na_position="last").reset_index(drop=True)
    return out


# ---------------------------
# ✅ 조건부 색상(버킷별 행 배경)
# ---------------------------
def row_bg_color(bucket: str) -> str:
    # 메일 호환 위해 너무 진한 색 대신 "옅은 배경" 추천
    if bucket == "폐기확정(유효기한 지남)":
        return "#f3f4f6"  # 회색 톤 (폐기확정)
    if bucket == "1개월 미만":
        return "#ffe4e6"  # 연빨강
    if bucket == "2개월 미만":
        return "#ffedd5"  # 연주황
    if bucket == "3개월 미만":
        return "#fef9c3"  # 연노랑
    if bucket in ["4개월 미만", "5개월 미만", "6개월 미만"]:
        return "#ecfccb"  # 연연두
    if bucket in ["7개월 미만", "8개월 미만", "9개월 미만"]:
        return "#dbeafe"  # 연파랑
    if bucket == "유효기한 없음":
        return "#ffffff"  # 흰색
    return "#ffffff"


def df_to_html_table(df: pd.DataFrame, title: str) -> str:
    """메일에서 잘 보이도록 인라인 스타일 테이블 생성 + 조건부 색상"""
    if df.empty:
        return f"""
        <div style="margin-top:14px;">
          <div style="font-weight:700; margin-bottom:8px;">{title}</div>
          <div style="color:#666;">해당 없음</div>
        </div>
        """

    #view = df.copy().head(max_rows)
    view = df.copy()

    # 표 표시용 컬럼 구성
    view["유효기간"] = pd.to_datetime(view["_expiry"], errors="coerce").dt.strftime("%Y-%m-%d")

    if "3평판" in view.columns:
        view["3평판"] = pd.to_numeric(view["3평판"], errors="coerce")

    view = view.rename(columns={
        MAT_COL: "자재",
        DESC_COL: "자재 내역",
        BATCH_COL: "배치",
        BUCKET_COL: "버킷",
        DAYS_COL: "남은 일(Day)",
        "_qty": "부진재고 수량",
        "_val": "부진재고 금액",
    })

    # 포맷
    view["부진재고 수량"] = pd.to_numeric(view["부진재고 수량"], errors="coerce").fillna(0).round(0).astype(int).map(lambda x: f"{x:,}")
    view["부진재고 금액"] = pd.to_numeric(view["부진재고 금액"], errors="coerce").fillna(0).map(fmt_won_int)
    view["남은 일(Day)"] = pd.to_numeric(view["남은 일(Day)"], errors="coerce").fillna(0).astype(int)

    if "3평판" in view.columns:
        view["3평판"] = view["3평판"].fillna(0).round(0).astype(int).map(lambda x: f"{x:,}")

    cols = ["자재", "자재 내역", "배치", "버킷", "유효기간", "남은 일(Day)", "3평판", "부진재고 수량", "부진재고 금액"]
    cols = [c for c in cols if c in view.columns]
    view = view[cols]

    # 헤더
    header_html = "".join([
        f'<th style="border-bottom:1px solid #e5e7eb; padding:10px; text-align:left; font-size:13px; color:#111;">{col}</th>'
        for col in (["No"] + list(view.columns))
    ])

    # 바디
    rows_html = ""
    for i, (_, row) in enumerate(view.iterrows(), start=1):
        bg = row_bg_color(str(row["버킷"]))
        cells = [str(i)] + [str(row[c]) for c in view.columns]

        row_html = "".join([
            f'<td style="border-bottom:1px solid #f0f0f0; padding:10px; font-size:13px; color:#111; vertical-align:top;">{cell}</td>'
            for cell in cells
        ])
        rows_html += f'<tr style="background:{bg};">{row_html}</tr>'

    return f"""
    <div style="margin-top:18px;">
      <div style="font-weight:700; margin-bottom:10px; font-size:14px;">{title}</div>

      <div style="margin-bottom:8px; font-size:12px; color:#6b7280;">
        <span style="background:#ffe4e6; padding:2px 8px; border-radius:999px; margin-right:6px;">1개월</span>
        <span style="background:#ffedd5; padding:2px 8px; border-radius:999px; margin-right:6px;">2개월</span>
        <span style="background:#fef9c3; padding:2px 8px; border-radius:999px; margin-right:6px;">3개월</span>
        <span style="background:#ecfccb; padding:2px 8px; border-radius:999px; margin-right:6px;">4~6개월</span>
        <span style="background:#dbeafe; padding:2px 8px; border-radius:999px; margin-right:6px;">7~9개월</span>
        <span style="background:#f3f4f6; padding:2px 8px; border-radius:999px;">폐기확정</span>
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

def build_html_email(today: pd.Timestamp, file_path: str, kpis: dict, risk_table: pd.DataFrame) -> str:
    card_style = (
        "border:1px solid #e5e7eb; border-radius:12px; padding:14px; "
        "display:inline-block; margin-right:12px; min-width:220px; background:#fff;"
    )
    kpi_label = "color:#6b7280; font-size:12px; margin-bottom:6px;"
    kpi_value = "font-size:22px; font-weight:800; color:#111;"

    # ✅ 4개 카드 (6M 2개 + 9M 2개)
    kpi_cards = f"""
    <div style="margin-top:16px;">
      <div style="{card_style}">
        <div style="{kpi_label}">6개월 미만 배치 수</div>
        <div style="{kpi_value}">{kpis['batch_cnt_6']:,}개</div>
      </div>
      <div style="{card_style}">
        <div style="{kpi_label}">6개월 미만 총 위험 금액</div>
        <div style="{kpi_value}">{fmt_won_int(kpis['total_val_6'])}</div>
      </div>
    </div>

    <div style="margin-top:12px;">
      <div style="{card_style}">
        <div style="{kpi_label}">9개월 미만 배치 수</div>
        <div style="{kpi_value}">{kpis['batch_cnt_9']:,}개</div>
      </div>
      <div style="{card_style}">
        <div style="{kpi_label}">9개월 미만 총 위험 금액</div>
        <div style="{kpi_value}">{fmt_won_int(kpis['total_val_9'])}</div>
      </div>
    </div>
    """

    table_html = df_to_html_table(
        risk_table,
        title="📋 유효기한 임박 배치 목록 (남은 일 기준 오름차순)"
    )

    return f"""
    <div style="font-family:Arial, sans-serif; color:#111; line-height:1.5;">
      <div style="font-size:15px; margin-bottom:6px;">안녕하세요.</div>
      <div style="font-size:14px; color:#374151;">
        금일(<b>{today.strftime('%Y-%m-%d')}</b>) 기준, 유효기한과 오늘 일자를 비교하여
        <b>1~9개월 미만</b> 유효기한 임박 배치 현황을 공유드립니다.
      </div>

      <div style="margin-top:10px; font-size:12px; color:#6b7280;">
        기준 파일: {file_path}
      </div>

      {kpi_cards}

      <div style="margin-top:12px; font-size:12px; color:#6b7280;">
        ※ 표는 (자재+배치) 단위로 집계되며, 남은 일(Day) 오름차순(급한 순)으로 정렬되었습니다.
      </div>

      {table_html}

      <div style="margin-top:18px; font-size:12px; color:#6b7280;">
        ※ 상세 내용은 S&OP 시스템 참고 부탁드립니다.
      </div>
      <div style="margin-top:10px; font-size:14px;">감사합니다.</div>
    </div>
    """

def send_mail():
    if not SMTP_PASS:
        raise RuntimeError("SMTP_PASS가 비어있습니다. Gmail 앱 비밀번호를 확인해주세요.")

    today = pd.Timestamp.today().normalize()

    # 1) 로드 + 오늘 기준 재계산
    df = load_prepare(STOCK_PATH)

    # 2) 메일 본문 테이블(1~9개월 미만) 범위
    in_scope_9 = df[
        df[DAYS_COL].notna() &
        (df[DAYS_COL] >= 0) &
        (df[DAYS_COL] < 270)
    ].copy()

    # ✅ 6개월 미만 범위
    in_scope_6 = df[
        df[DAYS_COL].notna() &
        (df[DAYS_COL] >= 0) &
        (df[DAYS_COL] < 180)
    ].copy()

    # 3) (자재+배치) 테이블 생성
    batch_table_9 = build_batch_table(in_scope_9)  # 테이블도 여기 기준으로 출력(1~9개월)
    batch_table_6 = build_batch_table(in_scope_6)

    # ✅ 메일 테이블은 1~9개월 전체를 쭉 보여주기
    risk_table = batch_table_9.copy()

    # 4) KPI (6개월/9개월)
    kpis = {
        "batch_cnt_6": int(batch_table_6[BATCH_COL].nunique()),
        "total_val_6": float(batch_table_6["_val"].sum()),
        "batch_cnt_9": int(batch_table_9[BATCH_COL].nunique()),
        "total_val_9": float(batch_table_9["_val"].sum()),
    }

    # 5) 메일 생성
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Subject"] = "[보고] 유효기한 임박(6M/9M) 배치 현황"

    text_body = f"""안녕하세요.

금일({today.strftime('%Y-%m-%d')}) 기준 유효기한 임박 배치 현황입니다.
- 6개월 미만: {kpis['batch_cnt_6']}개 / {int(round(kpis['total_val_6'])):,}원
- 9개월 미만: {kpis['batch_cnt_9']}개 / {int(round(kpis['total_val_9'])):,}원

(상세는 HTML 본문 및 S&OP 시스템 참고)
"""

    html_body = build_html_email(
        today=today,
        file_path=STOCK_PATH,
        kpis=kpis,
        risk_table=risk_table
    )

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
schedule.every().day.at("15:21").do(send_mail)

print("🕘 메일 스케줄러 실행 중... (종료하려면 Ctrl+C)")

while True:
    schedule.run_pending()
    time.sleep(30)
