/**
 * dashboard.js - Main dashboard page logic
 */

const DEFAULT_YEAR  = new Date().getFullYear();
const DEFAULT_MONTH = new Date().getMonth() + 1;

// ECharts instances
let agingChart   = null;
let stockoutChart = null;

// ── Init ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildYearOptions(document.getElementById('selYear'),   DEFAULT_YEAR);
  buildMonthOptions(document.getElementById('selMonth'), DEFAULT_MONTH);

  document.getElementById('btnLoad').addEventListener('click', loadDashboard);
  loadDashboard();
});

async function loadDashboard() {
  const year  = parseInt(document.getElementById('selYear').value);
  const month = parseInt(document.getElementById('selMonth').value);

  // Show spinners
  document.getElementById('stockoutKpi').innerHTML  = '<div class="loading-state"><div class="spinner"></div></div>';
  document.getElementById('agingKpi').innerHTML     = '<div class="loading-state"><div class="spinner"></div></div>';
  document.getElementById('forecastTable').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

  try {
    const [stockoutData, agingData, forecastedData] = await Promise.all([
      fetchSubCollection(year, month, 'stockout',   2000),
      fetchSubCollection(year, month, 'aging_inventory', 2000),
      fetchSubCollection(year, month, 'forecasted', 2000)
    ]);

    renderStockoutKpi(stockoutData, year, month);
    renderAgingKpi(agingData, year, month);
    renderAgingBucketChart(agingData);
    renderStockoutTopChart(stockoutData);
    renderForecastTop10(forecastedData);

  } catch (err) {
    console.error(err);
    showError(document.getElementById('stockoutKpi'),  '데이터 로드 실패: ' + err.message);
    showError(document.getElementById('agingKpi'),     '데이터 로드 실패: ' + err.message);
    showError(document.getElementById('forecastTable'), '데이터 로드 실패: ' + err.message);
  }
}

// ── Stockout KPIs ────────────────────────────────────────────
function renderStockoutKpi(data, year, month) {
  const el = document.getElementById('stockoutKpi');
  if (!data || data.length === 0) {
    el.innerHTML = buildKpiCard(`${year}년 ${month}월 데이터 없음`, '-', '', '');
    return;
  }

  const danger  = data.filter(r => parseFloat(r['재고일수']) < 30);
  const warning = data.filter(r => {
    const d = parseFloat(r['재고일수']);
    return d >= 30 && d < 60;
  });

  el.innerHTML = `
    ${buildKpiCard('위험 (30일 미만)', danger.length, '종', 'var(--color-danger)')}
    ${buildKpiCard('주의 (60일 미만)', warning.length, '종', 'var(--color-warning)')}
    ${buildKpiCard('분석 대상 총 자재', data.length, '종', '')}
  `;

  // Apply card colors
  const cards = el.querySelectorAll('.kpi-card');
  if (cards[0]) cards[0].classList.add('danger');
  if (cards[1]) cards[1].classList.add('warning');
  if (cards[2]) cards[2].classList.add('neutral');
}

// ── Aging KPIs ───────────────────────────────────────────────
function renderAgingKpi(data, year, month) {
  const el = document.getElementById('agingKpi');
  if (!data || data.length === 0) {
    el.innerHTML = buildKpiCard(`${year}년 ${month}월 데이터 없음`, '-', '', '');
    return;
  }

  const BUCKETS_6  = ['폐기확정', '폐기확정(유효기한 지남)', '1개월 미만', '2개월 미만', '3개월 미만', '4개월 미만', '5개월 미만', '6개월 미만'];
  const BUCKETS_7  = ['7개월 미만'];
  const BUCKETS_9  = ['8개월 미만', '9개월 미만'];
  const BUCKETS_12 = ['10개월 미만', '11개월 미만', '12개월 미만'];

  function sum(buckets) {
    return data.filter(r => buckets.includes(r['유효기한구간']))
               .reduce((acc, r) => acc + (parseFloat(r['기말금액']) || 0), 0);
  }

  el.innerHTML = `
    ${buildKpiCard('⚠ 6개월 미만',  formatCurrency(sum(BUCKETS_6)),  '', 'var(--color-danger)')}
    ${buildKpiCard('🔔 7개월 미만',  formatCurrency(sum(BUCKETS_7)),  '', 'var(--color-warning)')}
    ${buildKpiCard('ℹ 9개월 미만',  formatCurrency(sum(BUCKETS_9)),  '', '#d97706')}
    ${buildKpiCard('📅 12개월 미만', formatCurrency(sum(BUCKETS_12)), '', 'var(--color-success)')}
  `;

  const cards = el.querySelectorAll('.kpi-card');
  if (cards[0]) cards[0].classList.add('danger');
  if (cards[1]) cards[1].classList.add('warning');
  if (cards[2]) cards[2].classList.add('warning');
  if (cards[3]) cards[3].classList.add('success');
}

// ── Aging Bucket Bar Chart ───────────────────────────────────
function renderAgingBucketChart(data) {
  const container = document.getElementById('agingBucketChart');
  if (!agingChart) {
    agingChart = echarts.init(container);
  }

  const BUCKET_ORDER = [
    '폐기확정', '폐기확정(유효기한 지남)',
    '1개월 미만', '2개월 미만', '3개월 미만', '4개월 미만', '5개월 미만', '6개월 미만',
    '7개월 미만', '8개월 미만', '9개월 미만',
    '10개월 미만', '11개월 미만', '12개월 미만',
    '12개월 이상', '18개월 미만', '24개월 미만', '24개월 이상', '유효기한 없음'
  ];

  // Sum 기말금액 by bucket
  const bucketSum = {};
  (data || []).forEach(r => {
    const b = r['유효기한구간'] || '유효기한 없음';
    bucketSum[b] = (bucketSum[b] || 0) + (parseFloat(r['기말금액']) || 0);
  });

  const filtered = BUCKET_ORDER.filter(b => bucketSum[b] > 0);
  const values   = filtered.map(b => bucketSum[b]);
  const colors   = filtered.map(b => getBucketColor(b));

  if (filtered.length === 0) {
    showEmpty(container, '데이터가 없습니다.');
    return;
  }

  agingChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0];
        return `<b>${p.name}</b><br>재고금액: ${formatCurrency(p.value)}`;
      }
    },
    grid: { left: 20, right: 20, top: 10, bottom: 60, containLabel: true },
    xAxis: {
      type: 'category',
      data: filtered,
      axisLabel: { rotate: 40, fontSize: 11, interval: 0 }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: v => {
          if (v >= 1e8) return (v / 1e8).toFixed(1) + '억';
          if (v >= 1e4) return (v / 1e4).toFixed(0) + '만';
          return v;
        }
      }
    },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [4,4,0,0] } })),
      emphasis: { itemStyle: { opacity: 0.85 } }
    }]
  });

  window.addEventListener('resize', () => agingChart.resize());
}

// ── Stockout Horizontal Bar Chart ───────────────────────────
function renderStockoutTopChart(data) {
  const container = document.getElementById('stockoutChart');
  if (!stockoutChart) {
    stockoutChart = echarts.init(container);
  }

  if (!data || data.length === 0) {
    showEmpty(container, '데이터가 없습니다.');
    return;
  }

  // Top 15 by shortest stock days (excluding 999 = no sales)
  const filtered = data
    .filter(r => parseFloat(r['재고일수']) < 999)
    .sort((a, b) => parseFloat(a['재고일수']) - parseFloat(b['재고일수']))
    .slice(0, 15);

  const labels = filtered.map(r => String(r['자재'] || r['자재코드'] || ''));
  const values = filtered.map(r => parseFloat(r['재고일수']) || 0);
  const colors = filtered.map(r => getRiskColor(r['재고일수']));

  stockoutChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0];
        const row = filtered[params[0].dataIndex];
        return `<b>${p.name}</b><br>${row['자재 내역'] || ''}<br>재고일수: ${formatDecimal(p.value)}일`;
      }
    },
    grid: { left: 20, right: 30, top: 10, bottom: 10, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { formatter: v => v + '일' },
      max: 90
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLabel: { fontSize: 11 },
      inverse: true
    },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] }
      })),
      markLine: {
        silent: true,
        lineStyle: { color: '#dc2626', type: 'dashed', width: 1.5 },
        data: [{ xAxis: 30, label: { formatter: '위험(30일)', position: 'end' } }]
      }
    }]
  });

  window.addEventListener('resize', () => stockoutChart.resize());
}

// ── Forecast Top 10 Table ─────────────────────────────────────
function renderForecastTop10(data) {
  const el = document.getElementById('forecastTable');

  if (!data || data.length === 0) {
    showEmpty(el, '예측 부진재고 데이터가 없습니다.');
    return;
  }

  // Filter rows with 예측부진재고 > 0, deduplicate by 자재코드 (take highest 예측부진재고금액)
  const slugRows = data.filter(r => parseFloat(r['예측부진재고']) > 0);
  const matMap = new Map();
  slugRows.forEach(r => {
    const mat = r['자재코드'];
    const amt = parseFloat(r['예측부진재고금액']) || 0;
    if (!matMap.has(mat) || amt > matMap.get(mat)['예측부진재고금액']) {
      matMap.set(mat, r);
    }
  });

  const top10 = Array.from(matMap.values())
    .sort((a, b) => (parseFloat(b['예측부진재고금액']) || 0) - (parseFloat(a['예측부진재고금액']) || 0))
    .slice(0, 10);

  const columns = [
    { key: '자재코드',        label: '자재코드',    bold: true },
    { key: '자재내역',        label: '자재내역' },
    { key: '유효기한구간',    label: '유효기한구간',
      render: (v) => `<span class="badge" style="background:${getBucketColor(v)}22;color:${getBucketColor(v)}">${v || '-'}</span>` },
    { key: '기말금액',        label: '기말금액',     type: 'currency' },
    { key: '예측부진재고',    label: '예측부진재고', type: 'number',
      highlight: '#fff1f2' },
    { key: '예측부진재고금액',label: '예측부진재고금액', type: 'currency',
      highlight: '#fff1f2' },
    { key: '판매개선율',      label: '판매개선율',
      render: (v) => v ? `<span class="badge badge-success">${v}</span>` : '-' },
    { key: '권장판매량',      label: '권장판매량', type: 'number' }
  ];

  buildTable(el, columns, top10, {
    maxHeight: 400,
    rowColorFn: (r) => parseFloat(r['예측부진재고']) > 0 ? 'background:#fff8f8' : ''
  });
}
