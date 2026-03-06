/**
 * aging-stock.js - Aging Stock Analysis page
 */

const DEFAULT_YEAR  = new Date().getFullYear();
const DEFAULT_MONTH = new Date().getMonth() + 1;

// Cached data
let agingData     = [];
let forecastedData = [];
let simulationData = [];
let showSlugOnly   = false;

// ECharts instance
let matBarChart = null;

// ── Risk bucket definitions ──────────────────────────────────
const BUCKETS_6  = new Set(['폐기확정', '폐기확정(유효기한 지남)', '1개월 미만', '2개월 미만', '3개월 미만', '4개월 미만', '5개월 미만', '6개월 미만']);
const BUCKETS_7  = new Set(['7개월 미만']);
const BUCKETS_9  = new Set(['8개월 미만', '9개월 미만']);
const BUCKETS_12 = new Set(['10개월 미만', '11개월 미만', '12개월 미만']);

// ── Tab logic ────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

// ── Filter buttons ───────────────────────────────────────────
document.getElementById('filterAll').addEventListener('click', () => {
  showSlugOnly = false;
  document.getElementById('filterAll').classList.add('active');
  document.getElementById('filterSlug').classList.remove('active');
  renderSimTable();
});
document.getElementById('filterSlug').addEventListener('click', () => {
  showSlugOnly = true;
  document.getElementById('filterSlug').classList.add('active');
  document.getElementById('filterAll').classList.remove('active');
  renderSimTable();
});

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildYearOptions(document.getElementById('selYear'),   DEFAULT_YEAR);
  buildMonthOptions(document.getElementById('selMonth'), DEFAULT_MONTH);

  document.getElementById('btnLoad').addEventListener('click', loadPage);
  document.getElementById('btnMatLookup').addEventListener('click', () => {
    const code = document.getElementById('matInput').value.trim();
    if (code) renderMatDetail(code);
  });
  document.getElementById('matInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const code = document.getElementById('matInput').value.trim();
      if (code) renderMatDetail(code);
    }
  });

  loadPage();
});

// ── Main load ────────────────────────────────────────────────
async function loadPage() {
  const year  = parseInt(document.getElementById('selYear').value);
  const month = parseInt(document.getElementById('selMonth').value);

  // Reset spinners
  ['t6','t7','t9','t12'].forEach(id => {
    document.getElementById(id).innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  });
  document.getElementById('agingKpi').innerHTML  = '<div class="loading-state"><div class="spinner"></div></div>';
  document.getElementById('simTable').innerHTML  = '<div class="loading-state"><div class="spinner"></div></div>';
  document.getElementById('simKpi').innerHTML    = '';
  document.getElementById('topNBtns').innerHTML  = '';

  try {
    [agingData, forecastedData, simulationData] = await Promise.all([
      fetchSubCollection(year, month, 'aging_inventory',   2000),
      fetchSubCollection(year, month, 'forecasted',        2000),
      fetchSubCollection(year, month, 'simulation_detail', 3000)
    ]);

    // Info bar
    const infoBar = document.getElementById('infoBar');
    const infoText = document.getElementById('infoText');
    infoBar.style.display = 'flex';
    infoText.textContent = `${year}년 ${month}월 데이터 로드 완료 | 재고 ${agingData.length.toLocaleString()}건 / 시뮬레이션 ${simulationData.length.toLocaleString()}건 / 예측 ${forecastedData.length.toLocaleString()}건`;

    renderAgingKpi(year, month);
    renderRiskTabs();
    renderSimKpi();
    renderSimTable();
    renderTopNButtons();

  } catch (err) {
    console.error(err);
    const msg = '데이터 로드 실패: ' + err.message;
    ['t6','t7','t9','t12'].forEach(id => showError(document.getElementById(id), msg));
    showError(document.getElementById('agingKpi'), msg);
  }
}

// ── Aging KPIs ───────────────────────────────────────────────
function renderAgingKpi(year, month) {
  const el = document.getElementById('agingKpi');

  function sumValue(bucketSet) {
    return agingData.filter(r => bucketSet.has(r['유효기한구간']))
                    .reduce((s, r) => s + (parseFloat(r['기말금액']) || 0), 0);
  }

  el.innerHTML = `
    ${buildKpiCard('⚠ 6개월 미만 금액',  formatCurrency(sumValue(BUCKETS_6)),  '', 'var(--color-danger)')}
    ${buildKpiCard('🔔 7개월 미만 금액',  formatCurrency(sumValue(BUCKETS_7)),  '', 'var(--color-warning)')}
    ${buildKpiCard('ℹ 9개월 미만 금액',  formatCurrency(sumValue(BUCKETS_9)),  '', '#d97706')}
    ${buildKpiCard('📅 12개월 미만 금액', formatCurrency(sumValue(BUCKETS_12)), '', 'var(--color-success)')}
  `;
  const cards = el.querySelectorAll('.kpi-card');
  ['danger','warning','warning','success'].forEach((cls, i) => cards[i]?.classList.add(cls));
}

// ── Risk Tab tables ───────────────────────────────────────────
function renderRiskTabs() {
  renderRiskTab('t6',  '6개월 미만',  [...BUCKETS_6]);
  renderRiskTab('t7',  '7개월 미만',  [...BUCKETS_7]);
  renderRiskTab('t9',  '9개월 미만',  [...BUCKETS_9]);
  renderRiskTab('t12', '12개월 미만', [...BUCKETS_12]);
}

function renderRiskTab(tabId, label, buckets) {
  const el = document.getElementById(tabId);
  const bucketSet = new Set(buckets);

  const rows = agingData
    .filter(r => bucketSet.has(r['유효기한구간']))
    .sort((a, b) => {
      const dA = parseFloat(a['남은일']) || 9999;
      const dB = parseFloat(b['남은일']) || 9999;
      const vA = parseFloat(a['기말금액']) || 0;
      const vB = parseFloat(b['기말금액']) || 0;
      return dA !== dB ? dA - dB : vB - vA;
    });

  if (rows.length === 0) {
    el.innerHTML = `<div class="empty-state" style="padding:32px"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><p style="color:var(--color-success)">✅ ${label} 이내 위험 자재가 없습니다.</p></div>`;
    return;
  }

  // Summary metrics
  const totalBatches = rows.length;
  const totalValue   = rows.reduce((s, r) => s + (parseFloat(r['기말금액']) || 0), 0);

  const summaryHtml = `
    <div class="kpi-grid" style="margin-bottom:14px">
      ${buildKpiCard(`${label} 대상 배치 수`, formatNumber(totalBatches), '건', '')}
      ${buildKpiCard('총 위험 재고 금액', formatCurrency(totalValue), '', 'var(--color-danger)')}
    </div>`;

  el.innerHTML = summaryHtml + '<div id="risk-table-' + tabId + '"></div>';

  const columns = [
    { key: '자재코드',     label: '자재코드', bold: true },
    { key: '자재내역',     label: '자재내역' },
    { key: '플랜트',       label: '플랜트' },
    { key: '배치',         label: '배치' },
    { key: '기말수량',     label: '기말수량',     type: 'number' },
    { key: '기말금액',     label: '기말금액',     type: 'currency', highlight: '#fff3e0' },
    { key: '단가',         label: '단가',         type: 'currency' },
    { key: '대분류',       label: '대분류' },
    { key: '소분류',       label: '소분류' },
    { key: '유효기한',     label: '유효기한',     type: 'date',     highlight: '#fff3e0' },
    { key: '남은일',       label: '남은일',
      render: (v) => {
        const d = parseFloat(v);
        if (isNaN(d)) return '-';
        const cls = d < 0 ? 'badge-danger' : d < 90 ? 'badge-warning' : 'badge-info';
        return `<span class="badge ${cls}">${Math.round(d)}일</span>`;
      }
    },
    { key: '유효기한구간', label: '유효기한구간',
      render: (v) => `<span class="badge" style="background:${getBucketColor(v)}22;color:${getBucketColor(v)};border:1px solid ${getBucketColor(v)}44">${v || '-'}</span>`,
      highlight: '#fff3e0'
    },
    { key: '3평판', label: '3평판(월평균)', type: 'number' }
  ];

  buildTable(
    document.getElementById('risk-table-' + tabId),
    columns,
    rows,
    { maxHeight: 500 }
  );
}

// ── Simulation result KPIs ───────────────────────────────────
function renderSimKpi() {
  const el = document.getElementById('simKpi');
  if (!forecastedData || forecastedData.length === 0) {
    el.innerHTML = '';
    return;
  }

  const total     = forecastedData.length;
  const slugCount = forecastedData.filter(r => parseFloat(r['예측부진재고']) > 0).length;
  const soldCount = forecastedData.filter(r => parseFloat(r['예측부진재고']) <= 0).length;
  const slugAmt   = forecastedData.reduce((s, r) => s + (parseFloat(r['예측부진재고금액']) || 0), 0);

  el.innerHTML = `
    ${buildKpiCard('전체 행 수', formatNumber(total), '건', '')}
    ${buildKpiCard('잔량 > 0 배치', formatNumber(slugCount), '건', 'var(--color-danger)')}
    ${buildKpiCard('완전 소진 배치', formatNumber(soldCount), '건', 'var(--color-success)')}
    ${buildKpiCard('예측 부진재고 금액', formatCurrency(slugAmt), '', 'var(--color-danger)')}
  `;
  const cards = el.querySelectorAll('.kpi-card');
  ['neutral','danger','success','danger'].forEach((cls, i) => cards[i]?.classList.add(cls));
}

// ── Simulation result table ───────────────────────────────────
function renderSimTable() {
  const el = document.getElementById('simTable');
  if (!forecastedData || forecastedData.length === 0) {
    showEmpty(el, '시뮬레이션 결과가 없습니다. 데이터를 업로드/업로드 후 다시 조회하세요.');
    return;
  }

  let rows = [...forecastedData].sort((a, b) =>
    (parseFloat(b['예측부진재고금액']) || 0) - (parseFloat(a['예측부진재고금액']) || 0)
  );

  if (showSlugOnly) {
    rows = rows.filter(r => parseFloat(r['예측부진재고']) > 0);
  }

  const columns = [
    { key: '자재코드',         label: '자재코드', bold: true },
    { key: '자재내역',         label: '자재내역' },
    { key: '배치',             label: '배치' },
    { key: '기말수량',         label: '기말수량',         type: 'number' },
    { key: '기말금액',         label: '기말금액',         type: 'currency' },
    { key: '3평판',            label: '3평판(월평균)',     type: 'number' },
    { key: '예측부진재고',     label: '예측부진재고',     type: 'number',   highlight: '#fff1f2' },
    { key: '예측부진재고금액', label: '예측부진재고금액', type: 'currency', highlight: '#fff1f2' },
    { key: '판매개선율',       label: '판매개선율',
      render: (v) => v ? `<span class="badge badge-success">${v}</span>` : '-',
      highlight: '#f0fdf4'
    },
    { key: '권장판매량',       label: '권장판매량', type: 'number', highlight: '#f0fdf4' },
    { key: '유효기한구간',     label: '유효기한구간',
      render: (v) => v ? `<span class="badge" style="background:${getBucketColor(v)}22;color:${getBucketColor(v)}">${v}</span>` : '-'
    },
    { key: '남은일', label: '남은일',
      render: (v) => {
        const d = parseFloat(v);
        if (isNaN(d)) return '-';
        return `${Math.round(d)}일`;
      }
    }
  ];

  buildTable(el, columns, rows, {
    maxHeight: 480,
    rowColorFn: (r) => parseFloat(r['예측부진재고']) > 0 ? 'background:#fff8f8' : ''
  });
}

// ── Top N Buttons ────────────────────────────────────────────
function renderTopNButtons() {
  const el = document.getElementById('topNBtns');
  if (!forecastedData || forecastedData.length === 0) {
    el.innerHTML = '';
    return;
  }

  // Deduplicate by material, keep highest slug amount
  const matMap = new Map();
  forecastedData.filter(r => parseFloat(r['예측부진재고']) > 0).forEach(r => {
    const mat = r['자재코드'];
    const amt = parseFloat(r['예측부진재고금액']) || 0;
    if (!matMap.has(mat) || amt > (parseFloat(matMap.get(mat)['예측부진재고금액']) || 0)) {
      matMap.set(mat, r);
    }
  });

  const top10 = Array.from(matMap.values())
    .sort((a, b) => (parseFloat(b['예측부진재고금액']) || 0) - (parseFloat(a['예측부진재고금액']) || 0))
    .slice(0, 10);

  if (top10.length === 0) {
    el.innerHTML = '';
    return;
  }

  el.innerHTML = '<div class="filter-label" style="margin-bottom:8px;display:block">고가치 리스크 자재 Top 10 (빠른 조회)</div>';
  top10.forEach(r => {
    const btn = document.createElement('button');
    btn.className = 'topn-btn';
    const amt = formatCurrency(parseFloat(r['예측부진재고금액']) || 0);
    btn.textContent = `${r['자재코드']}\n(${amt})`;
    btn.style.whiteSpace = 'pre-line';
    btn.addEventListener('click', () => {
      document.querySelectorAll('.topn-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('matInput').value = r['자재코드'];
      renderMatDetail(r['자재코드']);
    });
    el.appendChild(btn);
  });
}

// ── Material Detail ──────────────────────────────────────────
function renderMatDetail(matCode) {
  const resultEl = document.getElementById('matResult');
  const chartsEl = document.getElementById('matCharts');

  // Filter simulation data
  const simRows = simulationData.filter(r => String(r['자재코드']).trim() === String(matCode).trim());

  if (simRows.length === 0) {
    chartsEl.style.display = 'none';
    showError(resultEl, `⚠ "${matCode}"에 해당하는 시뮬레이션 결과가 없습니다.`);
    return;
  }

  const matName = simRows[0]['자재내역'] || '';
  resultEl.innerHTML = `
    <div class="info-bar">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      자재코드: <strong>${matCode}</strong>&nbsp;|&nbsp;${matName}&nbsp;|&nbsp;배치 <strong>${simRows.length}개</strong>
    </div>`;

  chartsEl.style.display = 'block';
  renderMatBarChart(simRows);
  renderMatDetailTable(simRows);
}

function renderMatBarChart(rows) {
  const container = document.getElementById('matBarChart');
  if (!matBarChart) {
    matBarChart = echarts.init(container);
  }

  const labels   = rows.map(r => String(r['배치'] || ''));
  const qtySold  = rows.map(r => parseFloat(r['qty_sold'])      || 0);
  const remaining = rows.map(r => parseFloat(r['remaining_qty']) || 0);

  matBarChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        let html = `<b>${params[0].name}</b><br>`;
        params.forEach(p => {
          html += `${p.marker} ${p.seriesName}: ${formatNumber(p.value)}<br>`;
        });
        return html;
      }
    },
    legend: { data: ['판매량', '예측부진재고'], bottom: 0 },
    grid: { left: 20, right: 20, top: 10, bottom: 40, containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 35, fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    series: [
      {
        name: '판매량',
        type: 'bar',
        stack: 'total',
        data: qtySold,
        itemStyle: { color: '#3b82f6', borderRadius: [0,0,0,0] }
      },
      {
        name: '예측부진재고',
        type: 'bar',
        stack: 'total',
        data: remaining,
        itemStyle: { color: '#ef4444', borderRadius: [4,4,0,0] }
      }
    ]
  });

  window.addEventListener('resize', () => matBarChart?.resize());
}

function renderMatDetailTable(rows) {
  const el = document.getElementById('matDetailTable');

  // Sort: rows with sales first, then no-sales; within each group by sell_end_date asc
  const withSales    = rows.filter(r => !['risk_reached_before_start','no_sales'].includes(r['stop_reason']));
  const withoutSales = rows.filter(r =>  ['risk_reached_before_start','no_sales'].includes(r['stop_reason']));
  withSales.sort((a, b) => {
    const da = new Date(a['sell_end_date'] || 0).getTime();
    const db = new Date(b['sell_end_date'] || 0).getTime();
    return da - db;
  });
  const sorted = [...withSales, ...withoutSales];

  const stopReasonMap = {
    'sold_out':                  '<span class="badge badge-success">완판</span>',
    'risk_reached':              '<span class="badge badge-warning">위험 진입</span>',
    'risk_reached_before_start': '<span class="badge badge-danger">판매 전 위험</span>',
    'no_sales':                  '<span class="badge badge-neutral">매출 없음</span>',
    'stopped':                   '<span class="badge badge-neutral">중단</span>',
    'stopped_with_sales':        '<span class="badge badge-info">부분 판매</span>'
  };

  const columns = [
    { key: '배치',              label: '배치', bold: true },
    { key: 'init_qty',          label: '초기수량',     type: 'number' },
    { key: 'init_days',         label: '초기남은일',
      render: (v) => `${parseFloat(v) || 0}일` },
    { key: 'risk_entry_date',   label: '위험진입일',   type: 'date', highlight: '#fff3e0' },
    { key: 'sell_start_date',   label: '판매시작일',   type: 'date' },
    { key: 'sell_end_date',     label: '판매종료일',   type: 'date' },
    { key: 'qty_sold',          label: '판매량',       type: 'number' },
    { key: 'remaining_qty',     label: '예측부진재고', type: 'number', highlight: '#fff1f2' },
    { key: 'days_left_at_stop', label: '종료시 잔여일',
      render: (v) => v != null ? `${Math.round(parseFloat(v) || 0)}일` : '-' },
    { key: 'stop_reason',       label: '중단 사유',
      render: (v) => stopReasonMap[v] || `<span class="badge badge-neutral">${v || '-'}</span>` }
  ];

  buildTable(el, columns, sorted, {
    maxHeight: 340,
    rowColorFn: (r) => {
      if ((parseFloat(r['remaining_qty']) || 0) > 0) return 'background:#fff8f8';
      if (r['stop_reason'] === 'sold_out') return 'background:#f0fdf4';
      return '';
    }
  });
}
