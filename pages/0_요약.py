import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="요약", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #EEF2F7; }
.main .block-container { padding-top: 0 !important; padding-bottom: 0; padding-left: 1rem; padding-right: 1rem; max-width: 100%; }
[data-testid="stSidebar"] { background: #0B1E3F !important; border-right: none; }
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebarNav"] { padding: 0.5rem; }
[data-testid="stSidebarNav"] a { border-radius: 8px; padding: 0.55rem 0.9rem !important; margin-bottom: 2px; font-size: 0.875rem; font-weight: 500; color: #94A3B8 !important; display: block; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.08) !important; color: #E2E8F0 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(37,99,235,0.3) !important; color: #FFFFFF !important; font-weight: 600; border-left: 3px solid #3B82F6; }
[data-testid="stSidebarNav"] span { color: inherit !important; }
</style>
""", unsafe_allow_html=True)

components.html("""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>S&OP 통합 운영 시스템 — 한눈에 보기</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }

  :root {
    --or: #60A5FA;
    --or2: #3B82F6;
    --orl: #F0F7FF;
    --nv: #2C3E50;
    --nv2: #4A5568;
    --gr: #718096;
    --bg: #F5F8FC;
    --wh: #FFFFFF;
    --bd: #DBEAFE;
  }

  html, body {
    font-family: 'Noto Sans KR', sans-serif;
    background: var(--bg);
    color: var(--nv);
    height: 100%;
  }

  .page {
    width: 100%;
    margin: 0 auto;
    padding: 16px 20px 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* ── HEADER ── */
  .header {
    background: var(--nv);
    border-radius: 12px;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .header-left h1 {
    font-size: 16px;
    font-weight: 900;
    color: var(--wh);
    line-height: 1.25;
  }
  .header-left h1 span { color: var(--or); }
  .header-left p { font-size: 10px; color: rgba(255,255,255,0.4); margin-top: 3px; }
  .header-right { display: flex; gap: 8px; align-items: center; }
  .hbadge {
    background: rgba(96,165,250,0.15);
    border: 1px solid var(--or);
    color: var(--or);
    font-size: 10px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
  }

  /* ── MAIN GRID ── */
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
  }

  .col {
    background: var(--wh);
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    border: 1.5px solid var(--bd);
  }

  .col-head {
    background: var(--nv);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .col-num {
    width: 24px; height: 24px;
    background: var(--or);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 900; color: var(--nv);
    flex-shrink: 0;
  }
  .col-head-text h2 { font-size: 13px; font-weight: 800; color: var(--wh); }
  .col-head-text p  { font-size: 9.5px; color: rgba(255,255,255,0.4); margin-top: 1px; }

  .col-body { padding: 12px 14px; flex: 1; display: flex; flex-direction: column; gap: 9px; }

  .intro-box {
    background: var(--orl);
    border-left: 3px solid var(--or);
    border-radius: 0 8px 8px 0;
    padding: 9px 11px;
    font-size: 11px;
    color: var(--nv2);
    line-height: 1.6;
    font-weight: 500;
  }

  .prob-item {
    border: 1.5px solid var(--bd);
    border-radius: 9px;
    padding: 10px 12px;
    position: relative;
    overflow: hidden;
  }
  .prob-item::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2.5px;
    background: var(--or);
  }
  .prob-item h3 {
    font-size: 11.5px; font-weight: 800; color: var(--nv);
    margin-bottom: 5px; display: flex; align-items: center; gap: 6px;
  }
  .prob-item h3 .ico { font-size: 13px; }
  .prob-item ul { list-style: none; }
  .prob-item ul li {
    font-size: 10.5px; color: var(--gr);
    padding: 2px 0 2px 12px;
    position: relative; line-height: 1.5;
  }
  .prob-item ul li::before { content:'—'; position:absolute; left:0; color:var(--or); font-size:9px; top:4px; }

  .kpi-row { display: flex; gap: 7px; }
  .kpi {
    flex: 1; background: var(--nv); border-radius: 8px;
    padding: 9px 7px; text-align: center;
  }
  .kpi .kl { font-size: 9px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 3px; }
  .kpi .kv { font-size: 13px; font-weight: 900; color: var(--or); line-height: 1.1; }
  .kpi .ks { font-size: 8.5px; color: rgba(255,255,255,0.35); margin-top: 2px; }

  .strat-item {
    border: 1.5px solid var(--bd);
    border-radius: 9px;
    overflow: hidden;
    flex: 1;
  }
  .strat-top {
    background: var(--nv2);
    padding: 8px 11px;
    display: flex; align-items: center; gap: 8px;
  }
  .strat-top .snum {
    font-size: 9px; font-weight: 700; color: var(--or);
    letter-spacing: 1.5px; text-transform: uppercase;
  }
  .strat-top h3 { font-size: 12px; font-weight: 800; color: var(--wh); }
  .strat-body { padding: 9px 11px; }
  .strat-body .slead {
    font-size: 10.5px; color: var(--nv2); font-weight: 600;
    margin-bottom: 5px; line-height: 1.45;
  }
  .strat-body ul { list-style: none; }
  .strat-body ul li {
    font-size: 10.5px; color: var(--gr);
    padding: 2px 0 2px 12px;
    position: relative; line-height: 1.5;
  }
  .strat-body ul li::before { content:'▶'; position:absolute; left:0; color:var(--or); font-size:7px; top:4px; }
  .strat-body ul li strong { color: var(--or2); }

  .flow { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; margin-top: 7px; }
  .fc {
    background: var(--orl); color: var(--or2);
    border: 1px solid var(--or); border-radius: 12px;
    padding: 2px 8px; font-size: 9.5px; font-weight: 700;
  }
  .fc.dark { background: var(--nv); color: var(--wh); border-color: var(--nv); }
  .fa { color: var(--gr); font-size: 10px; }

  .result-banner {
    background: var(--or);
    border-radius: 9px;
    padding: 10px 13px;
    display: flex; align-items: center; gap: 10px;
  }
  .result-banner .rb-icon { font-size: 20px; }
  .result-banner h3 { font-size: 12px; font-weight: 900; color: var(--nv); }
  .result-banner p  { font-size: 10px; color: rgba(26,30,46,0.65); margin-top: 2px; line-height: 1.4; }

  .metric-bar {
    background: var(--nv);
    border-radius: 9px;
    padding: 11px 14px;
    display: flex;
    align-items: center;
    justify-content: space-around;
  }
  .mb-item { text-align: center; }
  .mb-item .ml { font-size: 8.5px; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px; }
  .mb-item .mv { font-size: 16px; font-weight: 900; }
  .mb-item .mv.bad  { color: #F87171; }
  .mb-item .mv.good { color: #34D399; }
  .mb-item .mv.mid  { color: var(--or); font-size: 13px; }
  .mb-item .ms { font-size: 9px; color: rgba(255,255,255,0.35); margin-top: 2px; }
  .mb-div { width: 1px; height: 38px; background: rgba(255,255,255,0.1); }

  table.rtable {
    width: 100%;
    border-collapse: collapse;
    font-size: 10.5px;
    flex: 1;
  }
  table.rtable thead tr { background: #f0ece5; }
  table.rtable thead th {
    padding: 7px 9px; font-size: 9.5px; font-weight: 700;
    color: var(--gr); text-align: left; letter-spacing: 0.4px;
    border-bottom: 1.5px solid var(--bd);
  }
  table.rtable tbody tr { border-bottom: 1px solid var(--bd); }
  table.rtable tbody tr:last-child { border-bottom: none; }
  table.rtable tbody tr:hover { background: #fdf9f3; }
  table.rtable tbody td { padding: 7px 9px; vertical-align: middle; line-height: 1.4; }
  table.rtable tbody td:first-child { font-weight: 700; font-size: 10.5px; }

  .bc { display:inline-block; padding: 2px 7px; border-radius: 12px; font-size: 10px; font-weight: 700; }
  .bc.red  { background: #FEE2E2; color: #B91C1C; }
  .bc.grn  { background: #D1FAE5; color: #065F46; }
  .bc.org  { background: var(--orl); color: var(--or2); }

  .foot {
    background: var(--nv);
    border-radius: 10px;
    padding: 9px 18px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .foot span { font-size: 10.5px; color: rgba(255,255,255,0.4); }
  .foot strong { color: var(--or); }
  .foot a { font-size: 10.5px; color: rgba(255,255,255,0.5); text-decoration: none; border-bottom: 1px solid rgba(96,165,250,0.35); }
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="header">
    <div class="header-left">
      <h1>B2C SCM 관리 고도화를 위한 <span>S&amp;OP 통합 운영 시스템</span> 구축</h1>
      <p>Development of an Integrated S&amp;OP System to Enhance SCM Management in B2C Business</p>
    </div>
    <div class="header-right">
      <span class="hbadge">이혜진 · CMO팀 인턴</span>
      <span class="hbadge">2026.03.18</span>
      <span class="hbadge">대웅제약</span>
    </div>
  </div>

  <!-- 3 COLUMNS -->
  <div class="grid">

    <!-- ① 배경 및 문제 정의 -->
    <div class="col">
      <div class="col-head">
        <div class="col-num">1</div>
        <div class="col-head-text">
          <h2>배경 및 문제 정의</h2>
          <p>Background &amp; Problem Definition</p>
        </div>
      </div>
      <div class="col-body">

        <div class="intro-box">
          B2C는 프로모션·시장 변동으로 <strong>수요 예측이 어렵고</strong>, 갑작스러운 급등 시 품절, 부진 시 과잉재고가 발생합니다. 통합 S&OP 없이는 <strong>선제적 대응이 불가능</strong>합니다.
        </div>

        <div class="prob-item">
          <h3><span class="ico">🗄️</span> 멀티 소스 데이터 통합 구조 부재</h3>
          <ul>
            <li>다중 소스 데이터 수동 병합·전처리 의존</li>
            <li>S&OP 회의 준비에 <strong>월 평균 20시간</strong> 소요</li>
            <li>사람 주도 데이터 통합 → 오류·지연 위험</li>
          </ul>
        </div>

        <div class="prob-item">
          <h3><span class="ico">🛡️</span> 구조적 재고 관리 프로세스 부재</h3>
          <ul>
            <li>월 1회 S&OP 회의 시에만 재고 현황 검토</li>
            <li>실시간 재고 리스크 가시성 매우 부족</li>
            <li>9개월 미만 리스크 재고 <strong>약 2.5억 원</strong></li>
          </ul>
        </div>

        <div class="prob-item">
          <h3><span class="ico">🔄</span> 구조적 PSI 관리 프로세스 부재</h3>
          <ul>
            <li>SCM·구매팀 간 수동 협의로 발주 결정</li>
            <li>발주 타이밍 놓침 → 직접적 품절 리스크</li>
            <li><strong>월 평균 품절 1회</strong> 지속 발생</li>
          </ul>
        </div>

        <div class="kpi-row">
          <div class="kpi">
            <div class="kl">준비 시간</div>
            <div class="kv">월 20h</div>
            <div class="ks">수동 취합 기준</div>
          </div>
          <div class="kpi">
            <div class="kl">리스크 재고</div>
            <div class="kv">2.5억 원</div>
            <div class="ks">9개월 미만</div>
          </div>
          <div class="kpi">
            <div class="kl">예측 부진재고</div>
            <div class="kv">35.5억 원</div>
            <div class="ks">2026 추정치</div>
          </div>
        </div>

      </div>
    </div>

    <!-- ② 3대 핵심 실행 전략 -->
    <div class="col">
      <div class="col-head">
        <div class="col-num">2</div>
        <div class="col-head-text">
          <h2>3대 핵심 실행 전략</h2>
          <p>Execution Strategy</p>
        </div>
      </div>
      <div class="col-body">

        <div class="strat-item">
          <div class="strat-top">
            <div>
              <div class="snum">Strategy 01</div>
              <h3>🗄️ 데이터 통합 기반 구축</h3>
            </div>
          </div>
          <div class="strat-body">
            <p class="slead">재고·매출·공급 데이터를 표준화 DB로 통합</p>
            <ul>
              <li>SAP 데이터 <strong>일/주/월 자동 추출</strong> 스케줄링</li>
              <li>자동 전처리 → 분석 가능 DB 저장</li>
              <li>다운로드~분석 <strong>수동 개입 Zero</strong></li>
            </ul>
            <div class="flow">
              <span class="fc">재고</span><span class="fa">→</span>
              <span class="fc">매출</span><span class="fa">→</span>
              <span class="fc">공급</span><span class="fa">→</span>
              <span class="fc dark">표준화 DB</span>
            </div>
          </div>
        </div>

        <div class="strat-item">
          <div class="strat-top">
            <div>
              <div class="snum">Strategy 02</div>
              <h3>🛡️ 선제적 재고 리스크 관리</h3>
            </div>
          </div>
          <div class="strat-body">
            <p class="slead">시뮬레이션·모니터링·자동 알림으로 선제 대응</p>
            <ul>
              <li><strong>부진재고(6~12M)</strong>: 소진계획 수립 + 일별 달성률 모니터링</li>
              <li><strong>예측 부진재고</strong>: 미래 재고 시뮬레이션 + 권고 판매량</li>
              <li><strong>품절재고</strong>: 재고일수 대시보드 + 자동 이메일 알림</li>
            </ul>
            <div class="flow">
              <span class="fc">표준화 DB</span><span class="fa">→</span>
              <span class="fc">Web 대시보드</span><span class="fa">→</span>
              <span class="fc dark">자동 알림</span>
            </div>
          </div>
        </div>

        <div class="strat-item">
          <div class="strat-top">
            <div>
              <div class="snum">Strategy 03</div>
              <h3>🔄 PSI 시뮬레이션 자동화</h3>
            </div>
          </div>
          <div class="strat-body">
            <p class="slead">수요·공급 반영 미래 재고 예측 및 발주 최적화</p>
            <ul>
              <li>PSI 시뮬레이션으로 <strong>미래 재고 자동 예측</strong></li>
              <li>안전재고·리드타임 고려한 <strong>발주 타이밍 결정</strong></li>
              <li>MOQ 반영 <strong>권고 발주 수량</strong> 자동 제안</li>
            </ul>
            <div class="flow">
              <span class="fc">PSI 시뮬</span><span class="fa">→</span>
              <span class="fc dark">최적 발주 수량</span>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- ③ 기대 결과 및 목표 -->
    <div class="col">
      <div class="col-head">
        <div class="col-num">3</div>
        <div class="col-head-text">
          <h2>기대 결과 및 목표</h2>
          <p>Expected Results &amp; Goal</p>
        </div>
      </div>
      <div class="col-body">

        <div class="result-banner">
          <div class="rb-icon">🎯</div>
          <div>
            <h3>"Company-wide S&OP System-Based Process"</h3>
            <p>시스템 기반 S&OP로 가시성 향상 + 선제적 리스크 관리 + 데이터 기반 의사결정</p>
          </div>
        </div>

        <div class="metric-bar">
          <div class="mb-item">
            <div class="ml">현재 AS-IS</div>
            <div class="mv bad">월 20시간</div>
            <div class="ms">S&OP 준비 시간</div>
          </div>
          <div class="mb-div"></div>
          <div class="mb-item">
            <div class="ml">개선 효과</div>
            <div class="mv mid">99.5% ↓</div>
            <div class="ms">시간 단축률</div>
          </div>
          <div class="mb-div"></div>
          <div class="mb-item">
            <div class="ml">목표 TO-BE</div>
            <div class="mv good">월 6분</div>
            <div class="ms">완전 자동화</div>
          </div>
        </div>

        <table class="rtable">
          <thead>
            <tr>
              <th>지표</th>
              <th>AS-IS</th>
              <th>TO-BE</th>
              <th>목표 시점</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>부진재고 금액</td>
              <td><span class="bc red">2.5억 원</span></td>
              <td><span class="bc grn">6,000만 원</span></td>
              <td><span class="bc org">2026.12</span></td>
            </tr>
            <tr>
              <td>예측 부진재고</td>
              <td><span class="bc red">35.5억 원</span></td>
              <td><span class="bc grn">10억 원</span></td>
              <td><span class="bc org">2026.12</span></td>
            </tr>
            <tr>
              <td>품절 횟수</td>
              <td><span class="bc red">월 1회</span></td>
              <td><span class="bc grn">0회 (Zero)</span></td>
              <td><span class="bc org">2026.06</span></td>
            </tr>
            <tr>
              <td>발주 방식</td>
              <td><span class="bc red">수동 발주</span></td>
              <td><span class="bc grn">PSI 최적화</span></td>
              <td><span class="bc org">2026.06</span></td>
            </tr>
            <tr>
              <td>S&OP 준비</td>
              <td><span class="bc red">월 20시간</span></td>
              <td><span class="bc grn">월 6분</span></td>
              <td><span class="bc org">2026.04</span></td>
            </tr>
          </tbody>
        </table>

      </div>
    </div>

  </div><!-- /grid -->

  <!-- FOOTER -->
  <div class="foot">
    <span>발표자: <strong>이혜진</strong> · INTERN CMO Team · 대웅제약 &nbsp;|&nbsp; 2600144@daewoong.co.kr</span>
    <a href="https://snopsystem.streamlit.app/" target="_blank">🔗 snopsystem.streamlit.app</a>
  </div>

</div>
</body>
</html>
""", height=900, scrolling=False)

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

components.html("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>S&OP Integrated Operations System — At a Glance</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }

  :root {
    --or: #60A5FA;
    --or2: #3B82F6;
    --orl: #F0F7FF;
    --nv: #2C3E50;
    --nv2: #4A5568;
    --gr: #718096;
    --bg: #F5F8FC;
    --wh: #FFFFFF;
    --bd: #DBEAFE;
  }

  html, body {
    font-family: 'Noto Sans', sans-serif;
    background: var(--bg);
    color: var(--nv);
    height: 100%;
  }

  .page {
    width: 100%;
    margin: 0 auto;
    padding: 16px 20px 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .header {
    background: var(--nv);
    border-radius: 12px;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .header-left h1 { font-size: 16px; font-weight: 900; color: var(--wh); line-height: 1.25; }
  .header-left h1 span { color: var(--or); }
  .header-left p { font-size: 10px; color: rgba(255,255,255,0.4); margin-top: 3px; }
  .header-right { display: flex; gap: 8px; align-items: center; }
  .hbadge {
    background: rgba(96,165,250,0.15);
    border: 1px solid var(--or);
    color: var(--or);
    font-size: 10px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px;
  }

  .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }

  .col {
    background: var(--wh); border-radius: 12px; overflow: hidden;
    display: flex; flex-direction: column; border: 1.5px solid var(--bd);
  }

  .col-head {
    background: var(--nv); padding: 10px 16px;
    display: flex; align-items: center; gap: 10px;
  }
  .col-num {
    width: 24px; height: 24px; background: var(--or); border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 900; color: var(--nv); flex-shrink: 0;
  }
  .col-head-text h2 { font-size: 13px; font-weight: 800; color: var(--wh); }
  .col-head-text p  { font-size: 9.5px; color: rgba(255,255,255,0.4); margin-top: 1px; }

  .col-body { padding: 12px 14px; flex: 1; display: flex; flex-direction: column; gap: 9px; }

  .intro-box {
    background: var(--orl); border-left: 3px solid var(--or);
    border-radius: 0 8px 8px 0; padding: 9px 11px;
    font-size: 11px; color: var(--nv2); line-height: 1.6; font-weight: 500;
  }

  .prob-item {
    border: 1.5px solid var(--bd); border-radius: 9px;
    padding: 10px 12px; position: relative; overflow: hidden;
  }
  .prob-item::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 2.5px; background: var(--or);
  }
  .prob-item h3 {
    font-size: 11.5px; font-weight: 800; color: var(--nv);
    margin-bottom: 5px; display: flex; align-items: center; gap: 6px;
  }
  .prob-item h3 .ico { font-size: 13px; }
  .prob-item ul { list-style: none; }
  .prob-item ul li {
    font-size: 10.5px; color: var(--gr);
    padding: 2px 0 2px 12px; position: relative; line-height: 1.5;
  }
  .prob-item ul li::before { content:'—'; position:absolute; left:0; color:var(--or); font-size:9px; top:4px; }

  .kpi-row { display: flex; gap: 7px; }
  .kpi { flex: 1; background: var(--nv); border-radius: 8px; padding: 9px 7px; text-align: center; }
  .kpi .kl { font-size: 9px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 3px; }
  .kpi .kv { font-size: 13px; font-weight: 900; color: var(--or); line-height: 1.1; }
  .kpi .ks { font-size: 8.5px; color: rgba(255,255,255,0.35); margin-top: 2px; }

  .strat-item { border: 1.5px solid var(--bd); border-radius: 9px; overflow: hidden; flex: 1; }
  .strat-top { background: var(--nv2); padding: 8px 11px; display: flex; align-items: center; gap: 8px; }
  .strat-top .snum { font-size: 9px; font-weight: 700; color: var(--or); letter-spacing: 1.5px; text-transform: uppercase; }
  .strat-top h3 { font-size: 12px; font-weight: 800; color: var(--wh); }
  .strat-body { padding: 9px 11px; }
  .strat-body .slead { font-size: 10.5px; color: var(--nv2); font-weight: 600; margin-bottom: 5px; line-height: 1.45; }
  .strat-body ul { list-style: none; }
  .strat-body ul li {
    font-size: 10.5px; color: var(--gr);
    padding: 2px 0 2px 12px; position: relative; line-height: 1.5;
  }
  .strat-body ul li::before { content:'▶'; position:absolute; left:0; color:var(--or); font-size:7px; top:4px; }
  .strat-body ul li strong { color: var(--or2); }

  .flow { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; margin-top: 7px; }
  .fc {
    background: var(--orl); color: var(--or2);
    border: 1px solid var(--or); border-radius: 12px;
    padding: 2px 8px; font-size: 9.5px; font-weight: 700;
  }
  .fc.dark { background: var(--nv); color: var(--wh); border-color: var(--nv); }
  .fa { color: var(--gr); font-size: 10px; }

  .result-banner {
    background: var(--or); border-radius: 9px;
    padding: 10px 13px; display: flex; align-items: center; gap: 10px;
  }
  .result-banner .rb-icon { font-size: 20px; }
  .result-banner h3 { font-size: 12px; font-weight: 900; color: var(--nv); }
  .result-banner p  { font-size: 10px; color: rgba(26,30,46,0.65); margin-top: 2px; line-height: 1.4; }

  .metric-bar {
    background: var(--nv); border-radius: 9px; padding: 11px 14px;
    display: flex; align-items: center; justify-content: space-around;
  }
  .mb-item { text-align: center; }
  .mb-item .ml { font-size: 8.5px; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px; }
  .mb-item .mv { font-size: 16px; font-weight: 900; }
  .mb-item .mv.bad  { color: #F87171; }
  .mb-item .mv.good { color: #34D399; }
  .mb-item .mv.mid  { color: var(--or); font-size: 13px; }
  .mb-item .ms { font-size: 9px; color: rgba(255,255,255,0.35); margin-top: 2px; }
  .mb-div { width: 1px; height: 38px; background: rgba(255,255,255,0.1); }

  table.rtable { width: 100%; border-collapse: collapse; font-size: 10.5px; flex: 1; }
  table.rtable thead tr { background: #f0ece5; }
  table.rtable thead th {
    padding: 7px 9px; font-size: 9.5px; font-weight: 700;
    color: var(--gr); text-align: left; letter-spacing: 0.4px;
    border-bottom: 1.5px solid var(--bd);
  }
  table.rtable tbody tr { border-bottom: 1px solid var(--bd); }
  table.rtable tbody tr:last-child { border-bottom: none; }
  table.rtable tbody tr:hover { background: #fdf9f3; }
  table.rtable tbody td { padding: 7px 9px; vertical-align: middle; line-height: 1.4; }
  table.rtable tbody td:first-child { font-weight: 700; font-size: 10.5px; }

  .bc { display:inline-block; padding: 2px 7px; border-radius: 12px; font-size: 10px; font-weight: 700; }
  .bc.red  { background: #FEE2E2; color: #B91C1C; }
  .bc.grn  { background: #D1FAE5; color: #065F46; }
  .bc.org  { background: var(--orl); color: var(--or2); }

  .foot {
    background: var(--nv); border-radius: 10px; padding: 9px 18px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .foot span { font-size: 10.5px; color: rgba(255,255,255,0.4); }
  .foot strong { color: var(--or); }
  .foot a { font-size: 10.5px; color: rgba(255,255,255,0.5); text-decoration: none; border-bottom: 1px solid rgba(96,165,250,0.35); }
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="header">
    <div class="header-left">
      <h1>Building an <span>Integrated S&amp;OP Operations System</span> for B2C SCM Excellence</h1>
      <p>Development of an Integrated S&amp;OP System to Enhance SCM Management in B2C Business</p>
    </div>
    <div class="header-right">
      <span class="hbadge">Hyejin Lee · CMO Team Intern</span>
      <span class="hbadge">2026.03.18</span>
      <span class="hbadge">Daewoong Pharm.</span>
    </div>
  </div>

  <!-- 3 COLUMNS -->
  <div class="grid">

    <!-- ① Background & Problem Definition -->
    <div class="col">
      <div class="col-head">
        <div class="col-num">1</div>
        <div class="col-head-text">
          <h2>Background &amp; Problem Definition</h2>
          <p>배경 및 문제 정의</p>
        </div>
      </div>
      <div class="col-body">

        <div class="intro-box">
          B2C demand is hard to predict due to promotions &amp; market fluctuations. Sudden surges lead to <strong>stockouts</strong>; slow periods cause <strong>excess inventory</strong>. Without an integrated S&OP, <strong>proactive response is impossible</strong>.
        </div>

        <div class="prob-item">
          <h3><span class="ico">🗄️</span> No Multi-Source Data Integration Framework</h3>
          <ul>
            <li>Manual merging &amp; preprocessing of multi-source data</li>
            <li>S&OP meeting prep takes <strong>avg. 20 hrs/month</strong></li>
            <li>Human-driven integration → risk of errors &amp; delays</li>
          </ul>
        </div>

        <div class="prob-item">
          <h3><span class="ico">🛡️</span> No Structured Inventory Management Process</h3>
          <ul>
            <li>Inventory reviewed only at monthly S&OP meetings</li>
            <li>Very limited real-time inventory risk visibility</li>
            <li>Risk inventory &lt;9 months shelf life: <strong>~₩250M</strong></li>
          </ul>
        </div>

        <div class="prob-item">
          <h3><span class="ico">🔄</span> No Structured PSI Management Process</h3>
          <ul>
            <li>Order decisions via manual coordination between SCM &amp; Procurement</li>
            <li>Missed order timing → direct stockout risk</li>
            <li><strong>Avg. 1 stockout/month</strong> consistently occurring</li>
          </ul>
        </div>

        <div class="kpi-row">
          <div class="kpi">
            <div class="kl">Prep Time</div>
            <div class="kv">20h/mo</div>
            <div class="ks">Manual basis</div>
          </div>
          <div class="kpi">
            <div class="kl">Risk Inventory</div>
            <div class="kv">₩250M</div>
            <div class="ks">&lt;9 months</div>
          </div>
          <div class="kpi">
            <div class="kl">Forecast Aging</div>
            <div class="kv">₩3.55B</div>
            <div class="ks">2026 estimate</div>
          </div>
        </div>

      </div>
    </div>

    <!-- ② 3 Core Execution Strategies -->
    <div class="col">
      <div class="col-head">
        <div class="col-num">2</div>
        <div class="col-head-text">
          <h2>3 Core Execution Strategies</h2>
          <p>3대 핵심 실행 전략</p>
        </div>
      </div>
      <div class="col-body">

        <div class="strat-item">
          <div class="strat-top">
            <div>
              <div class="snum">Strategy 01</div>
              <h3>🗄️ Data Integration Foundation</h3>
            </div>
          </div>
          <div class="strat-body">
            <p class="slead">Consolidate inventory, sales &amp; supply data into a standardized DB</p>
            <ul>
              <li>SAP data <strong>auto-extraction</strong> scheduling (daily/weekly/monthly)</li>
              <li>Auto preprocessing → analysis-ready DB storage</li>
              <li><strong>Zero manual intervention</strong> from download to analysis</li>
            </ul>
            <div class="flow">
              <span class="fc">Inventory</span><span class="fa">→</span>
              <span class="fc">Sales</span><span class="fa">→</span>
              <span class="fc">Supply</span><span class="fa">→</span>
              <span class="fc dark">Standardized DB</span>
            </div>
          </div>
        </div>

        <div class="strat-item">
          <div class="strat-top">
            <div>
              <div class="snum">Strategy 02</div>
              <h3>🛡️ Proactive Inventory Risk Management</h3>
            </div>
          </div>
          <div class="strat-body">
            <p class="slead">Simulation · monitoring · auto-alerts for proactive response</p>
            <ul>
              <li><strong>Aging Stock (6–12M)</strong>: Depletion plan + daily achievement monitoring</li>
              <li><strong>Forecast Aging</strong>: Future inventory simulation + recommended sales qty</li>
              <li><strong>Stockout Risk</strong>: Days-of-stock dashboard + auto email alerts</li>
            </ul>
            <div class="flow">
              <span class="fc">Std. DB</span><span class="fa">→</span>
              <span class="fc">Web Dashboard</span><span class="fa">→</span>
              <span class="fc dark">Auto Alerts</span>
            </div>
          </div>
        </div>

        <div class="strat-item">
          <div class="strat-top">
            <div>
              <div class="snum">Strategy 03</div>
              <h3>🔄 PSI Simulation Automation</h3>
            </div>
          </div>
          <div class="strat-body">
            <p class="slead">Future inventory forecasting &amp; order optimization with demand/supply</p>
            <ul>
              <li>PSI simulation for <strong>automated future inventory forecasting</strong></li>
              <li><strong>Optimal order timing</strong> considering safety stock &amp; lead time</li>
              <li>Auto-suggested <strong>recommended order quantity</strong> reflecting MOQ</li>
            </ul>
            <div class="flow">
              <span class="fc">PSI Sim.</span><span class="fa">→</span>
              <span class="fc dark">Optimal Order Qty</span>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- ③ Expected Results & Goals -->
    <div class="col">
      <div class="col-head">
        <div class="col-num">3</div>
        <div class="col-head-text">
          <h2>Expected Results &amp; Goals</h2>
          <p>기대 결과 및 목표</p>
        </div>
      </div>
      <div class="col-body">

        <div class="result-banner">
          <div class="rb-icon">🎯</div>
          <div>
            <h3>"Company-wide S&OP System-Based Process"</h3>
            <p>System-driven S&OP: enhanced visibility + proactive risk management + data-based decision making</p>
          </div>
        </div>

        <div class="metric-bar">
          <div class="mb-item">
            <div class="ml">Current AS-IS</div>
            <div class="mv bad">20 hrs/mo</div>
            <div class="ms">S&OP prep time</div>
          </div>
          <div class="mb-div"></div>
          <div class="mb-item">
            <div class="ml">Improvement</div>
            <div class="mv mid">99.5% ↓</div>
            <div class="ms">Time reduction</div>
          </div>
          <div class="mb-div"></div>
          <div class="mb-item">
            <div class="ml">Target TO-BE</div>
            <div class="mv good">6 min/mo</div>
            <div class="ms">Fully automated</div>
          </div>
        </div>

        <table class="rtable">
          <thead>
            <tr>
              <th>Metric</th>
              <th>AS-IS</th>
              <th>TO-BE</th>
              <th>Target Date</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Aging Stock Amount</td>
              <td><span class="bc red">₩250M</span></td>
              <td><span class="bc grn">₩60M</span></td>
              <td><span class="bc org">2026.12</span></td>
            </tr>
            <tr>
              <td>Forecast Aging Stock</td>
              <td><span class="bc red">₩3.55B</span></td>
              <td><span class="bc grn">₩1B</span></td>
              <td><span class="bc org">2026.12</span></td>
            </tr>
            <tr>
              <td>Stockout Frequency</td>
              <td><span class="bc red">1×/month</span></td>
              <td><span class="bc grn">0 (Zero)</span></td>
              <td><span class="bc org">2026.06</span></td>
            </tr>
            <tr>
              <td>Ordering Method</td>
              <td><span class="bc red">Manual</span></td>
              <td><span class="bc grn">PSI Optimized</span></td>
              <td><span class="bc org">2026.06</span></td>
            </tr>
            <tr>
              <td>S&OP Preparation</td>
              <td><span class="bc red">20 hrs/mo</span></td>
              <td><span class="bc grn">6 min/mo</span></td>
              <td><span class="bc org">2026.04</span></td>
            </tr>
          </tbody>
        </table>

      </div>
    </div>

  </div><!-- /grid -->

  <!-- FOOTER -->
  <div class="foot">
    <span>Presenter: <strong>Hyejin Lee</strong> · INTERN CMO Team · Daewoong Pharmaceutical &nbsp;|&nbsp; 2600144@daewoong.co.kr</span>
    <a href="https://snopsystem.streamlit.app/" target="_blank">🔗 snopsystem.streamlit.app</a>
  </div>

</div>
</body>
</html>
""", height=900, scrolling=False)
