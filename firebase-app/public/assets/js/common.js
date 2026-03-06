/**
 * common.js - Shared utilities for S&OP Dashboard
 */

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------
function formatNumber(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return '-';
  return n.toLocaleString('ko-KR', { maximumFractionDigits: 0 });
}

function formatCurrency(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return '-';
  return '₩' + n.toLocaleString('ko-KR', { maximumFractionDigits: 0 });
}

function formatDate(v) {
  if (!v || v === 'NaT' || v === 'nan' || v === 'None' || v === 'null') return '-';
  try {
    const d = new Date(v);
    if (isNaN(d.getTime())) return String(v).split('T')[0] || '-';
    return d.toISOString().split('T')[0];
  } catch {
    return String(v).split('T')[0] || '-';
  }
}

function formatDecimal(v, digits = 1) {
  const n = parseFloat(v);
  if (isNaN(n)) return '-';
  return n.toFixed(digits);
}

// ---------------------------------------------------------------------------
// Color helpers
// ---------------------------------------------------------------------------
const BUCKET_COLORS = {
  '폐기확정': '#7f1d1d',
  '폐기확정(유효기한 지남)': '#7f1d1d',
  '1개월 미만': '#dc2626',
  '2개월 미만': '#ef4444',
  '3개월 미만': '#f87171',
  '4개월 미만': '#fb923c',
  '5개월 미만': '#f97316',
  '6개월 미만': '#ea580c',
  '7개월 미만': '#d97706',
  '8개월 미만': '#ca8a04',
  '9개월 미만': '#a16207',
  '10개월 미만': '#65a30d',
  '11개월 미만': '#4d7c0f',
  '12개월 미만': '#166534',
  '12개월 이상': '#15803d',
  '18개월 미만': '#15803d',
  '24개월 미만': '#166534',
  '24개월 이상': '#14532d',
  '유효기한 없음': '#94a3b8'
};

function getBucketColor(bucket) {
  return BUCKET_COLORS[bucket] || '#64748b';
}

function getRiskColor(days) {
  const d = parseFloat(days);
  if (isNaN(d) || d >= 999) return '#64748b';
  if (d < 30) return '#dc2626';
  if (d < 60) return '#d97706';
  return '#059669';
}

function getRiskBadgeClass(days) {
  const d = parseFloat(days);
  if (isNaN(d) || d >= 999) return 'badge-neutral';
  if (d < 30) return 'badge-danger';
  if (d < 60) return 'badge-warning';
  return 'badge-success';
}

// ---------------------------------------------------------------------------
// Period selector helpers
// ---------------------------------------------------------------------------
function buildYearOptions(selectEl, defaultYear) {
  selectEl.innerHTML = '';
  for (let y = 2023; y <= 2040; y++) {
    const opt = document.createElement('option');
    opt.value = y;
    opt.textContent = `${y}년`;
    if (y === defaultYear) opt.selected = true;
    selectEl.appendChild(opt);
  }
}

function buildMonthOptions(selectEl, defaultMonth) {
  selectEl.innerHTML = '';
  for (let m = 1; m <= 12; m++) {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = `${m}월`;
    if (m === defaultMonth) opt.selected = true;
    selectEl.appendChild(opt);
  }
}

function getDocId(year, month) {
  return `${year}_${String(month).padStart(2, '0')}`;
}

function getPeriodLabel(year, month) {
  return `${year}년 ${month}월`;
}

// ---------------------------------------------------------------------------
// Loading / Error states
// ---------------------------------------------------------------------------
function showLoading(el, msg = '데이터를 불러오는 중...') {
  el.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>${msg}</p>
    </div>`;
}

function showEmpty(el, msg = '데이터가 없습니다.') {
  el.innerHTML = `
    <div class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <p>${msg}</p>
    </div>`;
}

function showError(el, msg) {
  el.innerHTML = `
    <div class="error-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <p>${msg}</p>
    </div>`;
}

// ---------------------------------------------------------------------------
// Firestore helpers
// ---------------------------------------------------------------------------
async function fetchSubCollection(year, month, subcollection, limitCount = 2000) {
  const docId = getDocId(year, month);
  const colRef = db.collection('reports').document
    ? db.collection('reports').doc(docId).collection(subcollection)
    : null;
  if (!colRef) return [];

  let q = db.collection('reports').doc(docId).collection(subcollection).limit(limitCount);
  const snap = await q.get();
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

async function fetchReportMeta(year, month) {
  const docId = getDocId(year, month);
  const snap = await db.collection('reports').doc(docId).get();
  return snap.exists ? snap.data() : null;
}

// ---------------------------------------------------------------------------
// Table builder
// ---------------------------------------------------------------------------
function buildTable(container, columns, rows, opts = {}) {
  const { rowColorFn, maxHeight = 500 } = opts;

  if (!rows || rows.length === 0) {
    showEmpty(container, '표시할 데이터가 없습니다.');
    return;
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'table-wrapper';
  wrapper.style.maxHeight = maxHeight + 'px';

  const table = document.createElement('table');
  table.className = 'data-table';

  // Header
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  columns.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col.label || col.key;
    if (col.width) th.style.width = col.width;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement('tbody');
  rows.forEach((row, idx) => {
    const tr = document.createElement('tr');
    if (rowColorFn) {
      const style = rowColorFn(row);
      if (style) tr.style.cssText = style;
    }
    columns.forEach(col => {
      const td = document.createElement('td');
      const val = row[col.key];
      if (col.render) {
        const result = col.render(val, row);
        if (typeof result === 'string' && result.startsWith('<')) {
          td.innerHTML = result;
        } else {
          td.textContent = result;
        }
      } else if (col.type === 'currency') {
        td.textContent = formatCurrency(val);
        td.style.textAlign = 'right';
      } else if (col.type === 'number') {
        td.textContent = formatNumber(val);
        td.style.textAlign = 'right';
      } else if (col.type === 'date') {
        td.textContent = formatDate(val);
      } else {
        td.textContent = val == null || val === 'nan' || val === 'None' ? '-' : val;
      }
      if (col.bold) td.style.fontWeight = '600';
      if (col.highlight) td.style.background = col.highlight;
      tbody.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  wrapper.appendChild(table);
  container.innerHTML = '';
  container.appendChild(wrapper);
}

// ---------------------------------------------------------------------------
// KPI Card builder
// ---------------------------------------------------------------------------
function buildKpiCard(label, value, unit = '', color = '') {
  return `
    <div class="kpi-card">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value" style="${color ? 'color:' + color : ''}">${value}<span class="kpi-unit">${unit}</span></div>
    </div>`;
}
