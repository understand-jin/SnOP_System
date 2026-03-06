"""
app.py - S&OP Local Upload Server
=====================================
로컬에서 실행하여 웹 브라우저로 파일을 업로드하고 Firestore에 저장합니다.

실행 방법:
  cd python
  python app.py

접속 주소: http://localhost:8080
"""

import sys
import io
import os
import json
import time
import threading
import traceback
from pathlib import Path

# Windows UTF-8 콘솔
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

# Firebase
import firebase_admin
from firebase_admin import credentials, firestore as fb_firestore

# 경로 설정 (로컬과 Cloud Run 모두 대응)
PY_DIR   = Path(__file__).parent
SA_PATH  = PY_DIR / "serviceAccountKey.json"

# Cloud Run: inventory_utils2.py, utils.py 가 같은 디렉토리에 있음
# 로컬: 상위 디렉토리에 있음
if (PY_DIR / "inventory_utils2.py").exists():
    BASE_DIR = PY_DIR          # Cloud Run 환경
else:
    BASE_DIR = PY_DIR.parent   # 로컬 환경

BATCH_SIZE = 400
IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None  # Cloud Run 환경 변수

# Firebase 초기화
# 우선순위: 1) 환경변수(Render 등) 2) 로컬 키 파일 3) ADC(Cloud Run)
if not firebase_admin._apps:
    sa_json_env = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json_env:
        # Render 등 클라우드 배포: 환경변수에서 JSON 읽기
        sa_dict = json.loads(sa_json_env)
        cred = credentials.Certificate(sa_dict)
        firebase_admin.initialize_app(cred)
    elif SA_PATH.exists() and not IS_CLOUD_RUN:
        # 로컬 개발: 서비스 계정 키 파일
        cred = credentials.Certificate(str(SA_PATH))
        firebase_admin.initialize_app(cred)
    else:
        # Cloud Run: Application Default Credentials
        firebase_admin.initialize_app()
db = fb_firestore.client()

# 진행 상황 저장 (간단한 메모리 딕셔너리)
JOB_STATUS: dict[str, dict] = {}

# ── Flask App ────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ── HTML 페이지 ──────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>S&OP 데이터 업로드</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" />
<style>
:root {
  --primary:#1e40af; --primary-h:#1d4ed8; --accent:#3b82f6;
  --danger:#dc2626;  --warning:#d97706;    --success:#059669;
  --bg:#f1f5f9; --surface:#fff; --border:#e2e8f0;
  --text:#0f172a; --muted:#64748b;
  --sidebar:#0f172a; --sidebar-w:230px;
  --font:'Inter',-apple-system,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--text);display:flex;min-height:100vh}
a{text-decoration:none;color:inherit}

/* Sidebar */
.sidebar{width:var(--sidebar-w);background:var(--sidebar);display:flex;flex-direction:column;position:fixed;top:0;left:0;bottom:0;z-index:100}
.logo{padding:24px 20px 18px;border-bottom:1px solid rgba(255,255,255,.07)}
.logo-t{font-size:1.1rem;font-weight:800;color:#f8fafc;letter-spacing:-.3px}
.logo-s{font-size:.72rem;color:#94a3b8;margin-top:2px}
.nav{flex:1;padding:14px 0}
.nav-lbl{font-size:.67rem;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:.08em;padding:10px 20px 4px}
.nav-a{display:flex;align-items:center;gap:10px;padding:10px 20px;color:#cbd5e1;font-size:.87rem;font-weight:500;transition:background .15s,color .15s;position:relative}
.nav-a:hover{background:rgba(255,255,255,.06);color:#f1f5f9}
.nav-a.active{background:rgba(59,130,246,.15);color:#93c5fd}
.nav-a.active::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:#3b82f6;border-radius:0 2px 2px 0}
.nav-icon{width:17px;height:17px;opacity:.8;flex-shrink:0}
.sidebar-ft{padding:14px 20px;border-top:1px solid rgba(255,255,255,.07);font-size:.71rem;color:#475569;line-height:1.8}

/* Main */
.main{margin-left:var(--sidebar-w);flex:1;display:flex;flex-direction:column}
.topbar{background:var(--surface);border-bottom:1px solid var(--border);height:62px;display:flex;align-items:center;justify-content:space-between;padding:0 32px;position:sticky;top:0;z-index:50}
.topbar-title{font-size:1.05rem;font-weight:700}
.topbar-sub{font-size:.76rem;color:var(--muted);margin-top:1px}
.ext-link{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border:1px solid var(--border);border-radius:8px;font-size:.82rem;font-weight:600;color:var(--primary);transition:all .15s}
.ext-link:hover{background:var(--primary);color:#fff;border-color:var(--primary)}
.page{padding:28px 32px;flex:1}

/* Tabs */
.tab-list{display:flex;gap:4px;border-bottom:2px solid var(--border);margin-bottom:24px}
.tab-btn{padding:9px 20px;border:none;background:transparent;font-size:.875rem;font-weight:600;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-2px;cursor:pointer;transition:color .15s,border-color .15s}
.tab-btn:hover{color:var(--primary)}
.tab-btn.active{color:var(--primary);border-bottom-color:var(--primary)}
.tab-panel{display:none}.tab-panel.active{display:block}

/* Card */
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:20px}
.card-h{padding:18px 24px 14px;border-bottom:1px solid #f1f5f9;font-size:.93rem;font-weight:700;display:flex;align-items:center;gap:8px}
.card-b{padding:20px 24px}

/* Upload Zone */
.upload-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.upload-item{border:1.5px dashed var(--border);border-radius:10px;padding:14px 16px;transition:border-color .15s,background .15s;cursor:pointer}
.upload-item:hover,.upload-item.has-file{border-color:var(--accent);background:#eff6ff}
.upload-item.has-file{border-style:solid}
.upload-item label{display:block;cursor:pointer}
.upload-lbl{font-size:.78rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
.upload-name{font-size:.82rem;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.upload-name.empty{color:var(--muted)}
input[type=file]{display:none}

/* Period selector */
.period-row{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.period-row label{font-size:.82rem;font-weight:600;color:var(--muted)}
.period-row select{padding:7px 12px;border:1px solid var(--border);border-radius:8px;font-size:.875rem;font-weight:600;color:var(--primary);font-family:var(--font);outline:none;cursor:pointer}

/* Button */
.btn{display:inline-flex;align-items:center;gap:7px;padding:10px 22px;border:none;border-radius:9px;font-size:.9rem;font-weight:700;cursor:pointer;transition:all .15s;font-family:var(--font)}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover{background:var(--primary-h);box-shadow:0 4px 12px rgba(30,64,175,.3)}
.btn-primary:disabled{opacity:.5;cursor:not-allowed}

/* Progress */
.progress-box{border:1px solid var(--border);border-radius:10px;padding:18px 20px;margin-top:16px;display:none}
.progress-box.show{display:block}
.progress-track{background:#e2e8f0;border-radius:99px;height:10px;margin:12px 0 10px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--primary));border-radius:99px;transition:width .4s ease;width:0%}
.progress-log{font-size:.78rem;color:var(--muted);line-height:1.9;max-height:160px;overflow-y:auto;background:#f8fafc;border-radius:8px;padding:10px 14px;margin-top:8px;font-family:monospace}

/* Result banner */
.banner{border-radius:10px;padding:14px 18px;margin-top:16px;font-size:.87rem;font-weight:600;display:none;align-items:center;gap:10px}
.banner.show{display:flex}
.banner.success{background:#d1fae5;color:#065f46;border:1px solid #a7f3d0}
.banner.error  {background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}

/* Period selector in topbar */
.ps{display:flex;align-items:center;gap:8px;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:6px 12px}
.ps label{font-size:.75rem;font-weight:600;color:var(--muted)}
.ps select{border:none;background:transparent;font-size:.875rem;font-weight:700;color:var(--primary);font-family:var(--font);cursor:pointer;outline:none}
</style>
</head>
<body>
<aside class="sidebar">
  <div class="logo">
    <div class="logo-t">S&amp;OP Dashboard</div>
    <div class="logo-s">SCM Intelligence Platform</div>
  </div>
  <nav class="nav">
    <div class="nav-lbl">Overview</div>
    <a href="https://snop-system.web.app/index.html" target="_blank" class="nav-a">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
      대시보드
    </a>
    <div class="nav-lbl">분석</div>
    <a href="https://snop-system.web.app/aging-stock.html" target="_blank" class="nav-a">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
      부진재고 분석
    </a>
    <a href="https://snop-system.web.app/stockout.html" target="_blank" class="nav-a">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      품절 리스크
    </a>
    <div class="nav-lbl">데이터</div>
    <a href="/" class="nav-a active">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      데이터 업로드
    </a>
  </nav>
  <div class="sidebar-ft">SCM Innovation TFT<br>© 2026 LEE HYE JIN</div>
</aside>

<div class="main">
  <header class="topbar">
    <div>
      <div class="topbar-title">데이터 업로드</div>
      <div class="topbar-sub">로컬 파일을 처리하여 Firestore에 저장합니다</div>
    </div>
    <a href="https://snop-system.web.app" target="_blank" class="ext-link">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      대시보드 열기
    </a>
  </header>

  <main class="page">

    <div class="tab-list">
      <button class="tab-btn active" onclick="switchTab('aging',this)">부진재고 분석 (5개 파일)</button>
      <button class="tab-btn" onclick="switchTab('stockout',this)">품절 리스크 CSV</button>
    </div>

    <!-- ── Aging Tab ─────────────────────────────── -->
    <div id="tab-aging" class="tab-panel active">
      <div class="card">
        <div class="card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
          부진재고 분석 데이터 업로드
        </div>
        <div class="card-b">

          <div class="period-row">
            <label>기준 연도/월:</label>
            <select id="a-year"></select>
            <select id="a-month"></select>
          </div>

          <div class="upload-grid">
            <div class="upload-item" id="zone-std" onclick="document.getElementById('f-std').click()">
              <label>
                <div class="upload-lbl">1. 재고개요 (Standard)</div>
                <div class="upload-name empty" id="name-std">파일 선택...</div>
                <input type="file" id="f-std" accept=".xlsx,.xls,.csv" onchange="onFile(this,'std')"/>
              </label>
            </div>
            <div class="upload-item" id="zone-cost" onclick="document.getElementById('f-cost').click()">
              <label>
                <div class="upload-lbl">2. 자재수불부 (Cost)</div>
                <div class="upload-name empty" id="name-cost">파일 선택...</div>
                <input type="file" id="f-cost" accept=".xlsx,.xls,.csv" onchange="onFile(this,'cost')"/>
              </label>
            </div>
            <div class="upload-item" id="zone-exp" onclick="document.getElementById('f-exp').click()">
              <label>
                <div class="upload-lbl">3. 배치별유효기한 (Expiry)</div>
                <div class="upload-name empty" id="name-exp">파일 선택...</div>
                <input type="file" id="f-exp" accept=".xlsx,.xls,.csv" onchange="onFile(this,'exp')"/>
              </label>
            </div>
            <div class="upload-item" id="zone-sales" onclick="document.getElementById('f-sales').click()">
              <label>
                <div class="upload-lbl">4. 3개월매출 (Sales)</div>
                <div class="upload-name empty" id="name-sales">파일 선택...</div>
                <input type="file" id="f-sales" accept=".xlsx,.xls,.csv" onchange="onFile(this,'sales')"/>
              </label>
            </div>
            <div class="upload-item" id="zone-cls" onclick="document.getElementById('f-cls').click()">
              <label>
                <div class="upload-lbl">5. 대분류_소분류 (Classification)</div>
                <div class="upload-name empty" id="name-cls">파일 선택...</div>
                <input type="file" id="f-cls" accept=".xlsx,.xls,.csv" onchange="onFile(this,'cls')"/>
              </label>
            </div>
          </div>

          <button class="btn btn-primary" id="btn-aging" onclick="submitAging()" disabled>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            전처리 + 시뮬레이션 + Firestore 저장
          </button>
          <div class="progress-box" id="prog-aging">
            <strong id="prog-aging-label">처리 중...</strong>
            <div class="progress-track"><div class="progress-fill" id="prog-aging-fill"></div></div>
            <div class="progress-log" id="prog-aging-log"></div>
          </div>
          <div class="banner" id="banner-aging"></div>
        </div>
      </div>
    </div>

    <!-- ── Stockout Tab ──────────────────────────── -->
    <div id="tab-stockout" class="tab-panel">
      <div class="card">
        <div class="card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          품절 리스크 CSV 업로드
        </div>
        <div class="card-b">

          <div class="period-row">
            <label>기준 연도/월:</label>
            <select id="s-year"></select>
            <select id="s-month"></select>
          </div>

          <p style="font-size:.85rem;color:var(--muted);margin-bottom:14px">
            재고개요(Standard) + 3개월매출(Sales) 두 파일을 업로드하면 품절 리스크 데이터를 자동 생성합니다.
          </p>
          <div class="upload-grid" style="grid-template-columns:1fr 1fr">
            <div class="upload-item" id="zone-sstd" onclick="document.getElementById('f-sstd').click()">
              <label>
                <div class="upload-lbl">재고개요 (Standard)</div>
                <div class="upload-name empty" id="name-sstd">파일 선택...</div>
                <input type="file" id="f-sstd" accept=".xlsx,.xls,.csv" onchange="onFile(this,'sstd')"/>
              </label>
            </div>
            <div class="upload-item" id="zone-ssales" onclick="document.getElementById('f-ssales').click()">
              <label>
                <div class="upload-lbl">3개월매출 (Sales)</div>
                <div class="upload-name empty" id="name-ssales">파일 선택...</div>
                <input type="file" id="f-ssales" accept=".xlsx,.xls,.csv" onchange="onFile(this,'ssales')"/>
              </label>
            </div>
          </div>

          <button class="btn btn-primary" id="btn-stockout" onclick="submitStockout()" disabled>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            품절 분석 + Firestore 저장
          </button>
          <div class="progress-box" id="prog-stockout">
            <strong id="prog-stockout-label">처리 중...</strong>
            <div class="progress-track"><div class="progress-fill" id="prog-stockout-fill"></div></div>
            <div class="progress-log" id="prog-stockout-log"></div>
          </div>
          <div class="banner" id="banner-stockout"></div>
        </div>
      </div>
    </div>

  </main>
</div>

<script>
// ── Init dropdowns ────────────────────────────────────────
function buildSelects(yId, mId) {
  const now = new Date();
  const yEl = document.getElementById(yId);
  const mEl = document.getElementById(mId);
  for (let y = 2023; y <= 2040; y++) {
    const o = document.createElement('option');
    o.value = y; o.textContent = y + '년';
    if (y === now.getFullYear()) o.selected = true;
    yEl.appendChild(o);
  }
  for (let m = 1; m <= 12; m++) {
    const o = document.createElement('option');
    o.value = m; o.textContent = m + '월';
    if (m === now.getMonth() + 1) o.selected = true;
    mEl.appendChild(o);
  }
}
buildSelects('a-year', 'a-month');
buildSelects('s-year', 's-month');

// ── Tab switching ─────────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
}

// ── File selection ────────────────────────────────────────
const agingFiles = { std: null, cost: null, exp: null, sales: null, cls: null };
const stockoutFiles = { sstd: null, ssales: null };

function onFile(input, key) {
  const file = input.files[0];
  if (!file) return;

  const nameEl   = document.getElementById('name-' + key);
  const zoneEl   = document.getElementById('zone-' + key);
  nameEl.textContent = file.name;
  nameEl.classList.remove('empty');
  zoneEl.classList.add('has-file');

  if (key in agingFiles) {
    agingFiles[key] = file;
    document.getElementById('btn-aging').disabled =
      !Object.values(agingFiles).every(Boolean);
  } else {
    stockoutFiles[key] = file;
    document.getElementById('btn-stockout').disabled =
      !Object.values(stockoutFiles).every(Boolean);
  }
}

// ── Submit helpers ────────────────────────────────────────
function setProgress(prefix, pct, msg) {
  const fill = document.getElementById('prog-' + prefix + '-fill');
  const log  = document.getElementById('prog-' + prefix + '-log');
  const lbl  = document.getElementById('prog-' + prefix + '-label');
  if (fill) fill.style.width = pct + '%';
  if (lbl)  lbl.textContent = msg || '처리 중...';
  if (log)  log.innerHTML += msg + '\n';
  if (log)  log.scrollTop = log.scrollHeight;
}

function showBanner(prefix, ok, msg) {
  const el = document.getElementById('banner-' + prefix);
  el.textContent = msg;
  el.className = 'banner show ' + (ok ? 'success' : 'error');
}

async function doUpload(url, formData, prefix) {
  const box = document.getElementById('prog-' + prefix);
  const log = document.getElementById('prog-' + prefix + '-log');
  box.classList.add('show');
  if (log) log.innerHTML = '';

  try {
    const resp = await fetch(url, { method: 'POST', body: formData });
    const data = await resp.json();

    if (resp.ok && data.status === 'ok') {
      setProgress(prefix, 100, '완료!');
      showBanner(prefix, true,
        `완료! ${data.message || ''} | 대시보드에서 바로 확인하세요.`);
    } else {
      setProgress(prefix, 0, '오류');
      showBanner(prefix, false, '오류: ' + (data.error || '알 수 없는 오류'));
    }
  } catch (e) {
    setProgress(prefix, 0, '서버 연결 오류');
    showBanner(prefix, false, '서버 연결 실패: ' + e.message);
  }
}

// SSE progress stream
function listenProgress(jobId, prefix, onDone) {
  const es = new EventSource('/api/progress/' + jobId);
  es.onmessage = (e) => {
    const d = JSON.parse(e.data);
    setProgress(prefix, d.pct, d.msg);
    if (d.done) {
      es.close();
      if (d.ok) {
        showBanner(prefix, true, '완료! ' + (d.summary || '') + '  대시보드에서 바로 확인하세요.');
      } else {
        showBanner(prefix, false, '오류: ' + (d.error || ''));
      }
      onDone && onDone(d.ok);
    }
  };
  es.onerror = () => {
    es.close();
    showBanner(prefix, false, 'SSE 연결 오류. 진행 상황을 확인할 수 없습니다.');
    onDone && onDone(false);
  };
}

// ── Submit Aging ──────────────────────────────────────────
async function submitAging() {
  const btn = document.getElementById('btn-aging');
  btn.disabled = true;

  const fd = new FormData();
  fd.append('year',  document.getElementById('a-year').value);
  fd.append('month', document.getElementById('a-month').value);
  fd.append('standard',   agingFiles.std);
  fd.append('cost',       agingFiles.cost);
  fd.append('expiration', agingFiles.exp);
  fd.append('sales',      agingFiles.sales);
  fd.append('cls',        agingFiles.cls);

  const box = document.getElementById('prog-aging');
  const log = document.getElementById('prog-aging-log');
  box.classList.add('show');
  log.innerHTML = '';
  setProgress('aging', 5, '파일 전송 중...');

  try {
    const resp = await fetch('/api/upload/aging', { method: 'POST', body: fd });
    const data = await resp.json();

    if (data.job_id) {
      setProgress('aging', 10, '서버에서 처리 시작...');
      listenProgress(data.job_id, 'aging', (ok) => { if (!ok) btn.disabled = false; });
    } else {
      showBanner('aging', false, '오류: ' + (data.error || ''));
      btn.disabled = false;
    }
  } catch (e) {
    showBanner('aging', false, '서버 연결 실패: ' + e.message);
    btn.disabled = false;
  }
}

// ── Submit Stockout ───────────────────────────────────────
async function submitStockout() {
  const btn = document.getElementById('btn-stockout');
  btn.disabled = true;

  const fd = new FormData();
  fd.append('year',     document.getElementById('s-year').value);
  fd.append('month',    document.getElementById('s-month').value);
  fd.append('standard', stockoutFiles.sstd);
  fd.append('sales',    stockoutFiles.ssales);

  const box = document.getElementById('prog-stockout');
  const log = document.getElementById('prog-stockout-log');
  box.classList.add('show');
  log.innerHTML = '';
  setProgress('stockout', 5, '파일 전송 중...');

  try {
    const resp = await fetch('/api/upload/stockout', { method: 'POST', body: fd });
    const data = await resp.json();

    if (data.job_id) {
      setProgress('stockout', 10, '서버에서 처리 시작...');
      listenProgress(data.job_id, 'stockout', (ok) => { if (!ok) btn.disabled = false; });
    } else {
      showBanner('stockout', false, '오류: ' + (data.error || ''));
      btn.disabled = false;
    }
  } catch (e) {
    showBanner('stockout', false, '서버 연결 실패: ' + e.message);
    btn.disabled = false;
  }
}
</script>
</body>
</html>"""


# ── Helper: clean for Firestore ─────────────────────────────
def clean_for_fs(record: dict) -> dict:
    out = {}
    for k, v in record.items():
        key = str(k)
        if v is None:
            out[key] = None
        elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            out[key] = None
        elif isinstance(v, (np.integer,)):
            out[key] = int(v)
        elif isinstance(v, (np.floating,)):
            out[key] = float(v)
        elif isinstance(v, pd.Timestamp):
            out[key] = v.isoformat() if not pd.isna(v) else None
        elif hasattr(v, "isoformat"):
            out[key] = v.isoformat()
        elif isinstance(v, str) and v in ("nan", "NaT", "None", "null", "NaN"):
            out[key] = None
        else:
            out[key] = v
    return out


def upload_df(db, year: str, month: str, subcol: str, df: pd.DataFrame, id_cols=None):
    doc_id  = f"{year}_{month.zfill(2)}"
    col_ref = db.collection("reports").document(doc_id).collection(subcol)

    records = df.to_dict(orient="records")
    total   = len(records)
    batch   = db.batch()
    count   = 0

    for i, rec in enumerate(records):
        cleaned = clean_for_fs(rec)
        if id_cols:
            key = "_".join(str(cleaned.get(c, "")) for c in id_cols) + f"_{i}"
        else:
            key = str(i)
        key = key.replace("/", "_").replace(".", "").replace(" ", "_")[:150] or f"doc_{i}"
        batch.set(col_ref.document(key), cleaned)
        count += 1
        if count >= BATCH_SIZE:
            batch.commit()
            batch = db.batch()
            count = 0

    if count:
        batch.commit()
    return total


def read_uploaded_file(file_storage) -> pd.DataFrame:
    """Flask FileStorage → DataFrame (Excel or CSV)"""
    sys.path.insert(0, str(BASE_DIR))
    from utils import read_excel_with_smart_header, preprocess_df, load_csv_any_encoding

    fname = file_storage.filename.lower()
    raw   = file_storage.read()

    if fname.endswith(".csv"):
        df = load_csv_any_encoding(raw)
    else:
        try:
            df = read_excel_with_smart_header(raw, scan_rows=80)
        except Exception:
            from utils import parse_html_tables
            try:
                df = parse_html_tables(raw)
            except Exception:
                import io as _io
                ext    = "xls" if fname.endswith(".xls") else "xlsx"
                engine = "xlrd" if ext == "xls" else "openpyxl"
                df     = pd.read_excel(_io.BytesIO(raw), engine=engine)
    return preprocess_df(df)


def push_progress(job_id: str, pct: int, msg: str, done=False, ok=True, summary="", error=""):
    JOB_STATUS[job_id] = {
        "pct": pct, "msg": msg, "done": done,
        "ok": ok, "summary": summary, "error": error,
        "ts": time.time()
    }


# ── Background job: Aging ────────────────────────────────────
def run_aging_job(job_id, year, month, files_bytes: dict):
    try:
        sys.path.insert(0, str(BASE_DIR))
        from inventory_utils2 import (
            aging_inventory_preprocess,
            simulate_batches_by_product,
            binary_search,
        )
        from utils import read_excel_with_smart_header, preprocess_df, load_csv_any_encoding

        def load(raw, fname):
            if fname.lower().endswith(".csv"):
                return preprocess_df(load_csv_any_encoding(raw))
            try:
                return preprocess_df(read_excel_with_smart_header(raw, scan_rows=80))
            except Exception:
                from utils import parse_html_tables
                try:
                    return preprocess_df(parse_html_tables(raw))
                except Exception:
                    import io as _io
                    ext = "xls" if fname.lower().endswith(".xls") else "xlsx"
                    engine = "xlrd" if ext == "xls" else "openpyxl"
                    return pd.read_excel(_io.BytesIO(raw), engine=engine)

        push_progress(job_id, 15, "파일 파싱 중...")
        standard_df   = load(files_bytes["standard"],   files_bytes["standard_name"])
        cost_df        = load(files_bytes["cost"],        files_bytes["cost_name"])
        expiration_df  = load(files_bytes["expiration"], files_bytes["expiration_name"])
        sales_df       = load(files_bytes["sales"],      files_bytes["sales_name"])
        cls_df         = load(files_bytes["cls"],        files_bytes["cls_name"])

        push_progress(job_id, 30, "재고 전처리 중 (aging_inventory_preprocess)...")
        aging_df = aging_inventory_preprocess(
            cost_df=cost_df,
            standard_df=standard_df,
            expiration_df=expiration_df,
            sales_df=sales_df,
            cls_df=cls_df,
            year_str=f"{year}년",
            month_str=f"{month}월",
        )

        push_progress(job_id, 50, f"FEFO 시뮬레이션 중... ({len(aging_df):,}행)")
        detail_df, updated_df = simulate_batches_by_product(aging_df)

        push_progress(job_id, 70, "최적 판매개선율 탐색 중 (binary_search)... 잠시 기다려 주세요")
        forecasted_df = binary_search(aging_df, updated_df)

        push_progress(job_id, 80, "Firestore에 저장 중...")
        doc_id = f"{year}_{str(month).zfill(2)}"
        db.collection("reports").document(doc_id).set({
            "year":        f"{year}년",
            "month":       f"{month}월",
            "yearNum":     int(year),
            "monthNum":    int(month),
            "processedAt": fb_firestore.SERVER_TIMESTAMP,
        })

        push_progress(job_id, 83, f"aging_inventory 저장 중 ({len(aging_df):,}건)...")
        upload_df(db, year, month, "aging_inventory",   aging_df,      ["자재코드", "배치"])
        push_progress(job_id, 90, f"simulation_detail 저장 중 ({len(detail_df):,}건)...")
        upload_df(db, year, month, "simulation_detail", detail_df,     ["자재코드", "배치"])
        push_progress(job_id, 96, f"forecasted 저장 중 ({len(forecasted_df):,}건)...")
        upload_df(db, year, month, "forecasted",        forecasted_df, ["자재코드", "배치"])

        summary = (
            f"{year}년 {month}월 | "
            f"재고 {len(aging_df):,}건 / "
            f"시뮬레이션 {len(detail_df):,}건 / "
            f"예측 {len(forecasted_df):,}건"
        )
        push_progress(job_id, 100, "완료!", done=True, ok=True, summary=summary)

    except Exception as e:
        push_progress(job_id, 0, "오류 발생", done=True, ok=False, error=str(e) + "\n" + traceback.format_exc())


# ── Background job: Stockout ─────────────────────────────────
def run_stockout_job(job_id, year, month, files_bytes: dict):
    try:
        sys.path.insert(0, str(BASE_DIR))
        from utils import read_excel_with_smart_header, preprocess_df, load_csv_any_encoding

        def load(raw, fname):
            if fname.lower().endswith(".csv"):
                return preprocess_df(load_csv_any_encoding(raw))
            try:
                return preprocess_df(read_excel_with_smart_header(raw, scan_rows=80))
            except Exception:
                import io as _io
                engine = "xlrd" if fname.lower().endswith(".xls") else "openpyxl"
                return pd.read_excel(_io.BytesIO(raw), engine=engine)

        push_progress(job_id, 20, "파일 파싱 중...")
        standard_df = load(files_bytes["standard"], files_bytes["standard_name"])
        sales_df    = load(files_bytes["sales"],    files_bytes["sales_name"])

        push_progress(job_id, 45, "품절 리스크 계산 중...")

        # 컬럼명 탐지
        mat_col   = next((c for c in standard_df.columns if "자재" in c and "내역" not in c and "코드" not in c), None) \
                    or next((c for c in standard_df.columns if "자재" in c), standard_df.columns[0])
        name_col  = next((c for c in standard_df.columns if "내역" in c), None)
        qty_col   = next((c for c in standard_df.columns if "기말" in c and "수량" in c), None) \
                    or next((c for c in standard_df.columns if "재고" in c and "수량" in c), None) \
                    or next((c for c in standard_df.columns if "수량" in c), None)

        # 3평판: sales_df에서 계산
        sales_df["자재코드"] = sales_df[next((c for c in sales_df.columns if "자재" in c), sales_df.columns[0])]\
                               .astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        qty_s = next((c for c in sales_df.columns if "수량" in c), None)
        ym_s  = next((c for c in sales_df.columns if "년월" in c or "월" in c), None)

        if qty_s and ym_s:
            sales_df[qty_s] = pd.to_numeric(sales_df[qty_s], errors="coerce").fillna(0)
            month_count = sales_df.groupby("자재코드")[ym_s].nunique()
            month_qty   = sales_df.groupby("자재코드")[qty_s].sum()
            sales_avg   = (month_qty / month_count.replace(0, pd.NA)).fillna(0)
        else:
            sales_avg = pd.Series(dtype=float)

        # 자재코드 정규화
        standard_df["_matcode"] = standard_df[mat_col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        standard_df[qty_col]    = pd.to_numeric(standard_df[qty_col], errors="coerce").fillna(0)

        agg_dict = {qty_col: "sum"}
        if name_col:
            agg_dict[name_col] = "first"
        for c in ["대분류", "소분류"]:
            if c in standard_df.columns:
                agg_dict[c] = "first"

        agg_df = standard_df.groupby("_matcode", as_index=False).agg(agg_dict)
        agg_df.rename(columns={"_matcode": "자재", qty_col: "총재고량"}, inplace=True)
        if name_col:
            agg_df.rename(columns={name_col: "자재 내역"}, inplace=True)

        agg_df["총재고량"] = pd.to_numeric(agg_df["총재고량"], errors="coerce").fillna(0)
        agg_df["3평판"]   = agg_df["자재"].map(sales_avg).fillna(0)
        agg_df["재고일수"] = agg_df.apply(
            lambda r: r["총재고량"] / (r["3평판"] / 30.0) if r["3평판"] > 0 else 999.0, axis=1
        )

        push_progress(job_id, 70, f"Firestore 저장 중 ({len(agg_df):,}건)...")
        doc_id = f"{year}_{str(month).zfill(2)}"
        db.collection("reports").document(doc_id).set({
            "year":        f"{year}년",
            "month":       f"{month}월",
            "yearNum":     int(year),
            "monthNum":    int(month),
            "processedAt": fb_firestore.SERVER_TIMESTAMP,
        }, merge=True)

        upload_df(db, year, month, "stockout", agg_df, ["자재"])
        push_progress(job_id, 100, "완료!", done=True, ok=True,
                      summary=f"{year}년 {month}월 | 품절 분석 {len(agg_df):,}건")

    except Exception as e:
        push_progress(job_id, 0, "오류 발생", done=True, ok=False,
                      error=str(e) + "\n" + traceback.format_exc())


# ── Routes ───────────────────────────────────────────────────
@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/upload/aging", methods=["POST"])
def upload_aging():
    required = ["standard", "cost", "expiration", "sales", "cls"]
    for k in required:
        if k not in request.files:
            return jsonify({"error": f"'{k}' 파일이 없습니다."}), 400

    year  = request.form.get("year",  "").strip()
    month = request.form.get("month", "").strip()
    if not year or not month:
        return jsonify({"error": "year/month 필요"}), 400

    files_bytes = {}
    for k in required:
        f = request.files[k]
        files_bytes[k]          = f.read()
        files_bytes[k + "_name"] = f.filename

    job_id = f"aging_{year}_{month}_{int(time.time())}"
    push_progress(job_id, 5, "작업 준비 중...")
    t = threading.Thread(target=run_aging_job, args=(job_id, year, month, files_bytes), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/upload/stockout", methods=["POST"])
def upload_stockout():
    year  = request.form.get("year",  "").strip()
    month = request.form.get("month", "").strip()
    if not year or not month:
        return jsonify({"error": "year/month 필요"}), 400

    files_bytes = {}
    for k in ["standard", "sales"]:
        if k not in request.files:
            return jsonify({"error": f"'{k}' 파일이 없습니다."}), 400
        f = request.files[k]
        files_bytes[k]          = f.read()
        files_bytes[k + "_name"] = f.filename

    job_id = f"stockout_{year}_{month}_{int(time.time())}"
    push_progress(job_id, 5, "작업 준비 중...")
    t = threading.Thread(target=run_stockout_job, args=(job_id, year, month, files_bytes), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def progress_stream(job_id):
    """Server-Sent Events: 진행 상황 스트림"""
    def generate():
        last_ts   = 0
        heartbeat = 0
        for _ in range(3600):  # 최대 60분 대기
            status = JOB_STATUS.get(job_id)
            if status and status["ts"] != last_ts:
                last_ts = status["ts"]
                yield f"data: {json.dumps(status, ensure_ascii=False)}\n\n"
                if status.get("done"):
                    return
            else:
                # 15초마다 heartbeat (Cloud Run / 로드밸런서 연결 유지)
                heartbeat += 1
                if heartbeat % 15 == 0:
                    yield ": heartbeat\n\n"
            time.sleep(1)
        yield f'data: {{"done":true,"ok":false,"error":"timeout","pct":0,"msg":"시간 초과"}}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  S&OP 업로드 서버 시작")
    print("=" * 55)
    print("  URL: http://localhost:8080")
    print("  대시보드: https://snop-system.web.app")
    print("  종료: Ctrl+C")
    print("=" * 55)
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
