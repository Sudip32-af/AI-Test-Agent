const API = "http://localhost:8000";

// ─── ELEMENTS ─────────────────────────────────────────────────
const smartCard    = document.getElementById("smart-card");
const manualPanel  = document.getElementById("manual-panel");
const manualLabel  = document.getElementById("manual-mode-label");
const backBtn      = document.getElementById("back-btn");
const btnSmart     = document.getElementById("btn-smart");
const btnPrompt    = document.getElementById("btn-prompt");
const btnFunctional  = document.getElementById("btn-functional");
const btnIntegration = document.getElementById("btn-integration");
const btnSystem      = document.getElementById("btn-system");
const btnRegression  = document.getElementById("btn-regression");
const btnCrawl       = document.getElementById("btn-crawl");
const pagesSlider    = document.getElementById("c-pages");
const pagesVal       = document.getElementById("pages-val");
const progressCard   = document.getElementById("progress-card");
const resultCard     = document.getElementById("result-card");
const termLines      = document.getElementById("terminal-lines");
const resultStats    = document.getElementById("result-stats");
const resultExtra    = document.getElementById("result-extra");
const resultActions  = document.getElementById("result-actions");
const stepCounter    = document.getElementById("step-counter");
const statusDot      = document.getElementById("status-dot");
const statusText     = document.getElementById("status-text");
const refreshBtn     = document.getElementById("refresh-btn");

const ALL_BTNS = [btnSmart, btnPrompt, btnFunctional, btnIntegration, btnSystem, btnRegression, btnCrawl];

// ─── SERVER STATUS CHECK ──────────────────────────────────────
async function checkServer() {
  try {
    const res = await fetch(`${API}/api/reports`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      statusDot.className    = "status-dot online";
      statusText.textContent = "Backend Online";
      statusText.style.color = "#4ade80";
    } else { setOffline(); }
  } catch { setOffline(); }
}
function setOffline() {
  statusDot.className    = "status-dot offline";
  statusText.textContent = "Backend Offline";
  statusText.style.color = "#f87171";
}
checkServer();
setInterval(checkServer, 8000);

// ─── MANUAL MODE SWITCHING ────────────────────────────────────
const MANUAL_FORMS = {
  prompt:      document.getElementById("form-prompt"),
  functional:  document.getElementById("form-functional"),
  integration: document.getElementById("form-integration"),
  system:      document.getElementById("form-system"),
  regression:  document.getElementById("form-regression"),
  crawl:       document.getElementById("form-crawl"),
};
const MODE_LABELS = {
  prompt:      "Prompt Mode",
  functional:  "Functional Testing",
  integration: "Integration Testing",
  system:      "System / E2E Testing",
  regression:  "Regression Testing",
  crawl:       "Crawl Mode",
};

document.querySelectorAll(".sc-mbtn").forEach(btn => {
  btn.addEventListener("click", () => {
    const mode = btn.dataset.mode;
    // Show manual panel, hide smart card
    smartCard.classList.add("hidden");
    manualPanel.classList.remove("hidden");
    manualLabel.textContent = MODE_LABELS[mode] || mode;
    // Show correct form
    Object.entries(MANUAL_FORMS).forEach(([k, el]) => {
      el.classList.toggle("hidden", k !== mode);
    });
  });
});

backBtn.addEventListener("click", () => {
  manualPanel.classList.add("hidden");
  smartCard.classList.remove("hidden");
});

if (pagesSlider) {
  pagesSlider.addEventListener("input", () => {
    pagesVal.textContent = pagesSlider.value;
  });
}

// ─── TERMINAL ────────────────────────────────────────────────
let stepCount = 0;
function clearTerminal() {
  termLines.innerHTML     = "";
  stepCount               = 0;
  stepCounter.textContent = "";
}
function addLine(text, cls = "") {
  const line = document.createElement("div");
  line.className   = "log-line" + (cls ? " " + cls : "");
  line.textContent = "> " + text;
  termLines.appendChild(line);
  document.getElementById("terminal").scrollTop = 999999;
}
function classifyLine(msg) {
  const m = msg.toLowerCase();
  if (m.includes("regression") && (m.includes("found") || m.includes("detect"))) return "fail";
  if (m.includes("pass"))    return "pass";
  if (m.includes("fail"))    return "fail";
  if (m.includes("warn"))    return "warn";
  if (m.includes("[ai]") || m.includes("[smart]") || m.includes("[crawler]") || m.includes("[regression]")) return "ai";
  if (m.includes("step ") || /\[\d+\/\d+\]/.test(m)) return "step";
  if (m.includes("complete") || m.includes("done") || m.includes("report")) return "done";
  if (m.includes("===") || m.includes("───")) return "sep";
  return "info";
}
function updateStepCounter(msg) {
  const m = msg.match(/step\s+(\d+)[:/]/i);
  if (m) {
    stepCount               = parseInt(m[1]);
    stepCounter.textContent = `Step ${stepCount}`;
  }
}

// ─── SHOW RESULT ─────────────────────────────────────────────
function showResult(result, error) {
  resultCard.classList.remove("hidden");
  resultStats.innerHTML   = "";
  resultExtra.innerHTML   = "";
  resultActions.innerHTML = "";

  const label       = document.getElementById("result-label");
  const passBarWrap = document.getElementById("pass-bar-wrap");

  if (error) {
    label.textContent = "Run Failed";
    passBarWrap.classList.add("hidden");
    resultStats.innerHTML = `<div class="error-banner">&#9888; ${error}</div>`;
    return;
  }
  if (!result) return;
  label.textContent = "Test Results";

  const total    = result.total    || 0;
  const passed   = result.passed   || 0;
  const failed   = result.failed   || 0;
  const warnings = result.warnings || 0;
  const passPct  = total ? Math.round(passed  / total * 100) : 0;
  const warnPct  = total ? Math.round(warnings / total * 100) : 0;
  const failPct  = total ? Math.round(failed   / total * 100) : 0;

  [
    { label: "Total",    num: total,    cls: "total" },
    { label: "Passed",   num: passed,   cls: "pass"  },
    { label: "Failed",   num: failed,   cls: "fail"  },
    { label: "Warnings", num: warnings, cls: "warn"  },
  ].forEach(s => {
    const pill = document.createElement("div");
    pill.className = `stat-pill ${s.cls}`;
    pill.innerHTML = `<div class="num">${s.num}</div><div class="lbl">${s.label}</div>`;
    resultStats.appendChild(pill);
  });

  // Page scan summary (smart mode)
  const pi = result.page_info_summary;
  if (pi) {
    const scanDiv = document.createElement("div");
    scanDiv.className = "scan-summary";
    scanDiv.innerHTML = `
      <span class="scan-chip">&#128269; ${pi.forms} form${pi.forms !== 1 ? "s" : ""}</span>
      <span class="scan-chip">&#128279; ${pi.nav_links} nav link${pi.nav_links !== 1 ? "s" : ""}</span>
      <span class="scan-chip">&#127760; ${pi.third_party} 3rd-party script${pi.third_party !== 1 ? "s" : ""}</span>
      <span class="scan-chip">&#9889; ${pi.api_calls} API call${pi.api_calls !== 1 ? "s" : ""}</span>
    `;
    resultExtra.appendChild(scanDiv);
  }

  // Regression baseline comparison
  const bc = result.baseline_comparison;
  if (bc) {
    if (!bc.has_baseline) {
      const note = document.createElement("div");
      note.className = "baseline-note success";
      note.innerHTML = `&#10003; Pehla run — baseline save ho gaya. Agli baar regressions detect honge.`;
      resultExtra.appendChild(note);
    } else {
      const regCount = bc.regression_count || 0;
      const impCount = bc.improvement_count || 0;
      const regPill  = document.createElement("div");
      regPill.className = `stat-pill ${regCount > 0 ? "fail" : "pass"}`;
      regPill.innerHTML = `<div class="num">${regCount}</div><div class="lbl">Regressions</div>`;
      resultStats.appendChild(regPill);
      if (impCount > 0) {
        const impPill = document.createElement("div");
        impPill.className = "stat-pill pass";
        impPill.innerHTML = `<div class="num">${impCount}</div><div class="lbl">Improved</div>`;
        resultStats.appendChild(impPill);
      }
      if (regCount > 0) {
        const banner = document.createElement("div");
        banner.className = "baseline-note danger";
        banner.innerHTML = `<strong>&#9888; ${regCount} Regression(s) detected:</strong><br>` +
          bc.regressions.slice(0, 5).map(r => `&bull; ${r.test} (${r.was} &rarr; ${r.now})`).join("<br>");
        resultExtra.appendChild(banner);
      } else {
        const note = document.createElement("div");
        note.className = "baseline-note success";
        note.innerHTML = `&#10003; Koi regression nahi (baseline: ${new Date(bc.baseline_date).toLocaleDateString("en-IN")})`;
        resultExtra.appendChild(note);
      }
    }
  }

  if (total > 0) {
    passBarWrap.classList.remove("hidden");
    document.getElementById("pass-bar-fill").style.width = passPct + "%";
    document.getElementById("warn-bar-fill").style.width = warnPct + "%";
    document.getElementById("fail-bar-fill").style.width = failPct + "%";
    document.getElementById("pass-bar-labels").innerHTML = `
      <span><span class="dot" style="background:#22c55e"></span> Pass ${passed} (${passPct}%)</span>
      <span><span class="dot" style="background:#f59e0b"></span> Warn ${warnings} (${warnPct}%)</span>
      <span><span class="dot" style="background:#ef4444"></span> Fail ${failed} (${failPct}%)</span>
    `;
  }

  if (result.html_report) {
    const a      = document.createElement("a");
    a.href        = `${API}/reports/${encodeURIComponent(result.html_report)}`;
    a.target      = "_blank";
    a.className   = "action-btn btn-view";
    a.innerHTML   = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg> View Report`;
    resultActions.appendChild(a);
  }

  loadReports();
}

// ─── RUN HELPER ───────────────────────────────────────────────
function enableAllBtns() {
  ALL_BTNS.forEach(b => { if (b) b.disabled = false; });
}

async function startRun(endpoint, body) {
  clearTerminal();
  progressCard.classList.remove("hidden");
  resultCard.classList.add("hidden");
  addLine("Backend se connect ho raha hai...", "ai");

  let runId;
  try {
    const res = await fetch(`${API}${endpoint}`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    if (!res.ok) { addLine(`Backend error: ${await res.text()}`, "fail"); enableAllBtns(); return; }
    runId = (await res.json()).run_id;
  } catch {
    addLine("Backend connect nahi ho raha. Terminal mein chalao: python server.py", "fail");
    enableAllBtns();
    return;
  }

  addLine(`Run ID: ${runId}`, "ai");
  addLine("Browser open ho raha hai...", "info");

  const es = new EventSource(`${API}/api/stream/${runId}`);
  es.onmessage = e => {
    const item = JSON.parse(e.data);
    if (item.type === "log") {
      addLine(item.msg, classifyLine(item.msg));
      updateStepCounter(item.msg);
    } else if (item.type === "result") {
      es.close();
      enableAllBtns();
      addLine("─".repeat(55), "sep");
      addLine(item.error ? "ERROR: " + item.error : "Complete! Report ready hai.", item.error ? "fail" : "done");
      showResult(item.result, item.error);
    }
  };
  es.onerror = () => { es.close(); enableAllBtns(); addLine("Connection lost.", "warn"); };
}

// ─── BUTTON HANDLERS ─────────────────────────────────────────
btnSmart.addEventListener("click", () => {
  const url  = document.getElementById("smart-url").value.trim();
  const task = (document.getElementById("smart-task") || {value:""}).value.trim();
  if (!url) { alert("Website URL dalo!"); return; }
  btnSmart.disabled = true;
  startRun("/api/run/smart", { url, task });
});

// Enter key on URL input triggers smart run
const smartUrlInput = document.getElementById("smart-url");
if (smartUrlInput) {
  smartUrlInput.addEventListener("keydown", e => {
    if (e.key === "Enter") btnSmart.click();
  });
}

btnPrompt.addEventListener("click", () => {
  const url  = document.getElementById("p-url").value.trim();
  const task = document.getElementById("p-task").value.trim();
  if (!url && !task) { alert("URL ya task kuch toh do!"); return; }
  btnPrompt.disabled = true;
  startRun("/api/run/prompt", { url, task });
});

btnFunctional.addEventListener("click", () => {
  const url  = document.getElementById("fn-url").value.trim();
  const task = document.getElementById("fn-task").value.trim();
  if (!url) { alert("Website URL do!"); return; }
  btnFunctional.disabled = true;
  startRun("/api/run/functional", { url, task });
});

btnIntegration.addEventListener("click", () => {
  const url  = document.getElementById("in-url").value.trim();
  const task = document.getElementById("in-task").value.trim();
  if (!url) { alert("Website URL do!"); return; }
  btnIntegration.disabled = true;
  startRun("/api/run/integration", { url, task });
});

btnSystem.addEventListener("click", () => {
  const url  = document.getElementById("sy-url").value.trim();
  const task = document.getElementById("sy-task").value.trim();
  if (!url) { alert("Website URL do!"); return; }
  btnSystem.disabled = true;
  startRun("/api/run/system", { url, task });
});

btnRegression.addEventListener("click", () => {
  const url   = document.getElementById("rg-url").value.trim();
  const suite = document.getElementById("rg-suite").value.trim() || "default";
  const save  = document.getElementById("rg-save-baseline").checked;
  if (!url) { alert("Website URL do!"); return; }
  btnRegression.disabled = true;
  startRun("/api/run/regression", { url, suite_name: suite, save_baseline: save });
});

btnCrawl.addEventListener("click", () => {
  const url = document.getElementById("c-url").value.trim();
  if (!url) { alert("Website URL do!"); return; }
  btnCrawl.disabled = true;
  startRun("/api/run/crawl", { url, max_pages: parseInt(pagesSlider.value) });
});

// ─── REPORTS ─────────────────────────────────────────────────
let _allReports  = [];
let _activeRtype = "smart";

document.querySelectorAll(".report-tab").forEach(t => {
  t.addEventListener("click", () => {
    document.querySelectorAll(".report-tab").forEach(x => x.classList.remove("active"));
    t.classList.add("active");
    _activeRtype = t.dataset.rtype;
    renderReports();
  });
});

const _PREFIX_MAP = {
  smart:       "smart -",
  prompt:      "report -",
  crawl:       "crawl",
  functional:  "functional -",
  integration: "integration -",
  system:      "system -",
  regression:  "regression -",
};

function renderReports() {
  const list     = document.getElementById("reports-list");
  list.innerHTML = "";
  const prefix   = _PREFIX_MAP[_activeRtype] || _activeRtype;
  const filtered = _allReports.filter(n => n.toLowerCase().startsWith(prefix));
  if (!filtered.length) {
    list.innerHTML = `<div class="empty-text">Koi ${_activeRtype} report nahi abhi.</div>`;
    return;
  }
  filtered.forEach(name => {
    const item = document.createElement("div");
    item.className = "report-item";
    item.innerHTML = `
      <div class="report-left"><span class="report-name">${name}</span></div>
      <a href="${API}/reports/${encodeURIComponent(name)}" target="_blank" class="report-view">Open &rarr;</a>
    `;
    list.appendChild(item);
  });
}

async function loadReports() {
  const list     = document.getElementById("reports-list");
  list.innerHTML = `<div class="loading-text">Loading...</div>`;
  try {
    const data  = await (await fetch(`${API}/api/reports`)).json();
    _allReports = data.reports;
    renderReports();
  } catch {
    list.innerHTML = `<div class="empty-text">Backend offline. <code style="color:#a78bfa;background:#0d1117;padding:2px 6px;border-radius:4px;">python server.py</code> chalao.</div>`;
  }
}

refreshBtn.addEventListener("click", loadReports);
loadReports();
