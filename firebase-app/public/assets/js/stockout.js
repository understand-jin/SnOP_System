/**
 * stockout.js - Stockout Risk Analysis page
 */

const DEFAULT_YEAR  = new Date().getFullYear();
const DEFAULT_MONTH = new Date().getMonth() + 1;

let stockoutData = [];
let currentFilter = 'all'; // 'all' | 'danger' | 'warning'
let chartInstance = null;

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildYearOptions(document.getElementById('selYear'),   DEFAULT_YEAR);
  buildMonthOptions(document.getElementById('selMonth'), DEFAULT_MONTH);

  document.getElementById('btnLoad').addEventListener('click', loadPage);

  document.getElementById('filterAll').addEventListener('click',     () => setFilter('all'));
  document.getElementById('filterDanger').addEventListener('click',  () => setFilter('danger'));
  document.getElementById('filterWarning').addEventListener('click', () => setFilter('warning'));

  loadPage();
});

function setFilter(f) {
  currentFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(
    f === 'all' ? 'filterAll' : f === 'danger' ? 'filterDanger' : 'filterWarning'
  ).classList.add('active');
  renderTableAndChart();
}

// ── Load ─────────────────────────────────────────────────────
async function loadPage() {
  const year  = parseInt(document.getElementById('selYear').value);
  const month = parseInt(document.getElementById('selMonth').value);

  document.getElementById('stockoutKpi').innerHTML   = '<div class="loading-state"><div class="spinner"></div></div>';
  document.getElementById('stockoutTable').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

  try {
    stockoutData = await fetchSubCollection(year, month, 'stockout', 2000);

    if (!stockoutData || stockoutData.length === 0) {
      const msg = `${year}년 ${month}월 Stockout 데이터가 없습니다. Python 업로더로 먼저 데이터를 업로드하세요.`;
      showEmpty(document.getElementById('stockoutKpi'), msg);
      showEmpty(document.getElementById('stockoutTable'), msg);
      return;
    }

    renderKpi();
    renderTableAndChart();

  } catch (err) {
    console.error(err);
    const msg = '데이터 로드 실패: ' + err.message;
    showError(document.getElementById('stockoutKpi'),   msg);
    showError(document.getElementById('stockoutTable'), msg);
  }
}

// ── KPI ──────────────────────────────────────────────────────
function renderKpi() {
  const el = document.getElementById('stockoutKpi');

  const risk60 = stockoutData.filter(r => parseFloat(r['재고일수']) < 60);
  const danger  = risk60.filter(r => parseFloat(r['재고일수']) < 30);
  const warning = risk60.filter(r => {
    const d = parseFloat(r['재고일수']);
    return d >= 30 && d < 60;
  });

  el.innerHTML = `
    ${buildKpiCard('위험 (30일 미만)', danger.length, '종', 'var(--color-danger)')}
    ${buildKpiCard('주의 (60일 미만)', warning.length, '종', 'var(--color-warning)')}
    ${buildKpiCard('분석 대상 총 자재', stockoutData.length, '종', '')}
    ${buildKpiCard('리스크 자재 (60일 미만)', risk60.length, '종', '#d97706')}
  `;
  const cards = el.querySelectorAll('.kpi-card');
  ['danger','warning','neutral','warning'].forEach((cls, i) => cards[i]?.classList.add(cls));
}

// ── Get filtered rows ────────────────────────────────────────
function getFilteredRows() {
  // Only show materials with < 60 days stock
  const risk60 = stockoutData
    .filter(r => parseFloat(r['재고일수']) < 60)
    .map(r => {
      const d = parseFloat(r['재고일수']);
      return { ...r, _grade: d < 30 ? '위험' : '주의', _days: d };
    })
    .sort((a, b) => a._days - b._days);

  if (currentFilter === 'danger')  return risk60.filter(r => r._grade === '위험');
  if (currentFilter === 'warning') return risk60.filter(r => r._grade === '주의');
  return risk60;
}

// ── Table + Chart ────────────────────────────────────────────
function renderTableAndChart() {
  const rows = getFilteredRows();
  renderTable(rows);
  renderChart(rows);
}

function renderTable(rows) {
  const el = document.getElementById('stockoutTable');

  if (!rows || rows.length === 0) {
    showEmpty(el, '해당 필터에 부합하는 데이터가 없습니다.');
    return;
  }

  const columns = [
    { key: '_grade',    label: '등급',
      render: (v) => {
        if (v === '위험') return '<span class="badge badge-danger">위험</span>';
        if (v === '주의') return '<span class="badge badge-warning">주의</span>';
        return `<span class="badge badge-neutral">${v}</span>`;
      }
    },
    { key: '자재',      label: '자재코드', bold: true,
      render: (v, r) => v || r['자재코드'] || '-' },
    { key: '자재 내역', label: '자재내역',
      render: (v, r) => v || r['자재내역'] || '-' },
    { key: '_days',     label: '남은 재고일수',
      render: (v) => {
        const d = parseFloat(v);
        const cls = d < 30 ? 'badge-danger' : 'badge-warning';
        return `<span class="badge ${cls}">${formatDecimal(d, 1)}일</span>`;
      },
      highlight: '#fff3e0'
    },
    { key: '3평판',     label: '3평판(월평균)', type: 'number',
      render: (v, r) => {
        const n = parseFloat(v || r['3평판']);
        return isNaN(n) ? '-' : formatNumber(n);
      }
    },
    { key: 'Stock Quantity on Period End', label: '총재고량', type: 'number',
      render: (v, r) => {
        const n = parseFloat(v || r['총재고량'] || r['기말수량']);
        return isNaN(n) ? '-' : formatNumber(n);
      }
    },
    { key: '대분류', label: '대분류' },
    { key: '소분류', label: '소분류' }
  ];

  buildTable(el, columns, rows, {
    maxHeight: Math.max(500, rows.length * 38),
    rowColorFn: (r) => {
      if (r._grade === '위험') return 'background:#fff5f5';
      if (r._grade === '주의') return 'background:#fffbeb';
      return '';
    }
  });
}

function renderChart(rows) {
  const container = document.getElementById('stockoutChart');
  if (!chartInstance) {
    chartInstance = echarts.init(container);
  }

  if (!rows || rows.length === 0) {
    chartInstance.clear();
    showEmpty(container, '차트 데이터가 없습니다.');
    return;
  }

  const labels = rows.map(r => String(r['자재'] || r['자재코드'] || ''));
  const values = rows.map(r => r._days);
  const colors = rows.map(r => r._grade === '위험' ? '#ef4444' : '#f59e0b');

  // Dynamic height based on row count
  const chartHeight = Math.max(400, rows.length * 36 + 80);
  container.style.height = chartHeight + 'px';

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params[0];
        const row = rows[p.dataIndex];
        const name = row['자재 내역'] || row['자재내역'] || '';
        return `<b>${p.name}</b><br>${name}<br>남은 재고일수: <b>${formatDecimal(p.value, 1)}일</b>`;
      }
    },
    grid: { left: 20, right: 60, top: 20, bottom: 20, containLabel: true },
    xAxis: {
      type: 'value',
      min: 0,
      max: 70,
      axisLabel: { formatter: v => v + '일' }
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
        itemStyle: {
          color: colors[i],
          borderRadius: [0, 4, 4, 0]
        }
      })),
      label: {
        show: true,
        position: 'right',
        formatter: (p) => formatDecimal(p.value, 1) + '일',
        fontSize: 11,
        color: '#475569'
      },
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { width: 1.5, type: 'dashed' },
        data: [
          { xAxis: 30, lineStyle: { color: '#dc2626' }, label: { formatter: '위험(30일)', color: '#dc2626', fontSize: 11 } },
          { xAxis: 60, lineStyle: { color: '#d97706' }, label: { formatter: '주의(60일)', color: '#d97706', fontSize: 11 } }
        ]
      }
    }]
  });

  chartInstance.resize();
  window.addEventListener('resize', () => chartInstance?.resize());
}
