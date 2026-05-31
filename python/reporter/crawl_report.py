import os
import re
from datetime import datetime
from urllib.parse import urlparse
from jinja2 import Template
from config import REPORT_OUTPUT_DIR


def build_test_cases(r: dict) -> list[dict]:
    """Har page ke liye test cases generate karo automatically."""
    cases = []

    # Scenario 1: Page Load
    cases.append({
        "scenario": "Page Load",
        "tc_id": "TC-PL-01",
        "name": "Page loads without error",
        "result": "pass" if r["status"] != "fail" else "fail",
        "detail": f"HTTP status OK" if r["status"] != "fail" else r.get("error", "Page failed to load"),
    })
    cases.append({
        "scenario": "Page Load",
        "tc_id": "TC-PL-02",
        "name": "Page has a title",
        "result": "pass" if r.get("title") else "fail",
        "detail": r.get("title") or "No title found",
    })

    # Scenario 2: Performance
    lt = r.get("load_time_ms")
    cases.append({
        "scenario": "Performance",
        "tc_id": "TC-PF-01",
        "name": "Load time under 3 seconds",
        "result": "pass" if lt and lt < 3000 else ("warn" if lt and lt < 5000 else "fail"),
        "detail": f"{lt}ms" if lt else "Load time not measured",
    })
    cases.append({
        "scenario": "Performance",
        "tc_id": "TC-PF-02",
        "name": "Load time under 5 seconds",
        "result": "pass" if lt and lt < 5000 else "fail",
        "detail": f"{lt}ms" if lt else "Load time not measured",
    })

    # Scenario 3: Console Errors
    errs = r.get("console_errors", [])
    cases.append({
        "scenario": "JavaScript Health",
        "tc_id": "TC-JS-01",
        "name": "No console errors",
        "result": "pass" if not errs else "fail",
        "detail": f"{len(errs)} error(s) found" if errs else "No errors",
    })

    # Scenario 4: Navigation
    cases.append({
        "scenario": "Navigation",
        "tc_id": "TC-NV-01",
        "name": "Page URL is accessible",
        "result": "pass" if r["status"] != "fail" else "fail",
        "detail": r["url"],
    })
    cases.append({
        "scenario": "Navigation",
        "tc_id": "TC-NV-02",
        "name": "Internal links found on page",
        "result": "pass" if r.get("links_found", 0) > 0 else "warn",
        "detail": f"{r.get('links_found', 0)} links found",
    })

    # Scenario 5: UI Quality (if analyzed)
    ui = r.get("ui_analysis")
    if ui and ui.get("ui_score") is not None:
        score = ui["ui_score"]
        cases.append({
            "scenario": "UI Quality",
            "tc_id": "TC-UI-01",
            "name": "UI score 7 or above",
            "result": "pass" if score >= 7 else ("warn" if score >= 5 else "fail"),
            "detail": f"Score: {score}/10 — {ui.get('summary', '')}",
        })
        high_issues = [i for i in ui.get("issues", []) if i.get("severity") == "high"]
        cases.append({
            "scenario": "UI Quality",
            "tc_id": "TC-UI-02",
            "name": "No high severity UI issues",
            "result": "pass" if not high_issues else "fail",
            "detail": f"{len(high_issues)} high severity issue(s)" if high_issues else "No high severity issues",
        })

    return cases


CRAWL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Test Report — {{ start_url }}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f1f5f9; color: #1e293b; }

  /* HEADER */
  .header { background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%); padding: 36px 40px; }
  .header h1 { color: white; font-size: 1.8rem; font-weight: 700; }
  .header .sub { color: #93c5fd; margin-top: 6px; font-size: 0.9rem; }
  .header .url-box { margin-top: 14px; background: rgba(255,255,255,0.1); border-left: 4px solid #60a5fa; padding: 10px 16px; border-radius: 0 8px 8px 0; color: #bfdbfe; font-size: 0.95rem; font-family: monospace; word-break: break-all; }

  /* SUMMARY CARDS */
  .summary { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; padding: 24px 40px; }
  .card { background: white; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-top: 4px solid #e2e8f0; }
  .card.total { border-color: #6366f1; } .card.pass { border-color: #22c55e; }
  .card.fail  { border-color: #ef4444; } .card.warn { border-color: #f59e0b; }
  .card.rate  { border-color: #0ea5e9; }
  .card .num  { font-size: 2.2rem; font-weight: 800; }
  .card.total .num { color: #6366f1; } .card.pass .num { color: #22c55e; }
  .card.fail  .num { color: #ef4444; } .card.warn .num { color: #f59e0b; }
  .card.rate  .num { color: #0ea5e9; }
  .card .lbl  { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; font-weight: 600; }

  /* PROGRESS BAR */
  .progress-wrap { padding: 0 40px 20px; }
  .progress-bar { height: 12px; background: #e2e8f0; border-radius: 10px; overflow: hidden; display: flex; }
  .progress-pass { background: #22c55e; } .progress-warn { background: #f59e0b; } .progress-fail { background: #ef4444; }
  .progress-labels { display: flex; gap: 20px; margin-top: 8px; font-size: 0.8rem; color: #64748b; }
  .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 4px; vertical-align: middle; }

  /* SECTIONS */
  .section { padding: 0 40px 30px; }
  .section-title { font-size: 1rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; }
  .section-title::after { content: ''; flex: 1; height: 1px; background: #e2e8f0; }

  /* BADGES */
  .badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 20px; font-size: 0.74rem; font-weight: 700; text-transform: uppercase; white-space: nowrap; }
  .badge::before { content:''; width:6px; height:6px; border-radius:50%; background:currentColor; }
  .badge-pass { background: #dcfce7; color: #15803d; }
  .badge-fail { background: #fee2e2; color: #b91c1c; }
  .badge-warn { background: #fef3c7; color: #92400e; }

  /* TABLES */
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); font-size: 0.85rem; }
  thead { background: #0f172a; color: white; }
  thead th { padding: 13px 16px; text-align: left; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
  tbody tr { border-bottom: 1px solid #f1f5f9; }
  tbody tr:hover { background: #f8fafc; }
  tbody td { padding: 12px 16px; vertical-align: middle; }

  .load-fast { color: #15803d; font-weight: 600; }
  .load-ok   { color: #92400e; font-weight: 600; }
  .load-slow { color: #b91c1c; font-weight: 600; }
  .full-url  { font-family: monospace; font-size: 0.8rem; word-break: break-all; }
  .full-url a { color: #1d4ed8; text-decoration: none; }
  .full-url a:hover { text-decoration: underline; }
  .score-pill { padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 700; }
  .score-good { background: #dcfce7; color: #15803d; }
  .score-mid  { background: #fef3c7; color: #92400e; }
  .score-bad  { background: #fee2e2; color: #b91c1c; }

  /* SCENARIO TABLE inside page card */
  .scenario-block { margin-bottom: 6px; border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; }
  .scenario-header { background: #1e293b; color: white; padding: 9px 16px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; display: flex; align-items: center; gap: 10px; }
  .scenario-header .s-counts { display: flex; gap: 8px; margin-left: auto; }
  .s-count { font-size: 0.72rem; padding: 2px 8px; border-radius: 10px; font-weight: 700; }
  .s-count.pass { background: #14532d; color: #86efac; }
  .s-count.fail { background: #450a0a; color: #fca5a5; }
  .s-count.warn { background: #451a03; color: #fcd34d; }
  .scenario-cases { background: white; }
  .tc-row { display: flex; align-items: center; gap: 12px; padding: 9px 16px; border-bottom: 1px solid #f8fafc; font-size: 0.83rem; }
  .tc-row:last-child { border-bottom: none; }
  .tc-id   { font-family: monospace; color: #6366f1; font-size: 0.75rem; font-weight: 700; min-width: 85px; }
  .tc-name { flex: 1; color: #1e293b; }
  .tc-detail { color: #64748b; font-size: 0.78rem; max-width: 300px; text-align: right; word-break: break-word; }

  /* PAGE DETAIL CARD */
  .page-card { background: white; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #e2e8f0; }
  .page-card-header { display: flex; align-items: flex-start; gap: 12px; padding: 16px 20px; background: #f8fafc; border-bottom: 2px solid #e2e8f0; }
  .page-num-badge { background: #1e293b; color: white; border-radius: 8px; padding: 6px 12px; font-size: 0.8rem; font-weight: 700; white-space: nowrap; }
  .page-info { flex: 1; }
  .page-info .pg-title { font-weight: 700; font-size: 0.95rem; color: #1e293b; margin-bottom: 4px; }
  .page-info .pg-url   { font-family: monospace; font-size: 0.8rem; color: #1d4ed8; word-break: break-all; }
  .page-info .pg-url a { color: #1d4ed8; text-decoration: none; }
  .page-info .pg-url a:hover { text-decoration: underline; }
  .page-meta { display: flex; gap: 20px; padding: 10px 20px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap; }
  .meta-item { font-size: 0.8rem; color: #64748b; } .meta-item strong { color: #1e293b; }
  .page-card-body { padding: 16px 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .left-col {}
  .right-col {}
  .error-box { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; padding: 10px 14px; font-size: 0.8rem; color: #b91c1c; margin-bottom: 14px; font-family: monospace; }
  .console-box { background: #1e293b; border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; }
  .console-title { color: #f59e0b; font-size: 0.75rem; font-weight: 700; margin-bottom: 6px; text-transform: uppercase; }
  .console-box code { font-family: monospace; font-size: 0.77rem; color: #fca5a5; display: block; margin-bottom: 3px; word-break: break-all; }
  .ss-wrap { margin-bottom: 14px; }
  .ss-wrap img { width: 100%; border-radius: 8px; border: 1px solid #e2e8f0; }
  .ui-issues { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 14px; margin-top: 14px; }
  .ui-issues h5 { color: #0369a1; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
  .issue-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; font-size: 0.8rem; }
  .sev { padding: 1px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; white-space: nowrap; }
  .sev-high { background:#fee2e2; color:#b91c1c; } .sev-medium { background:#fef3c7; color:#92400e; } .sev-low { background:#dcfce7; color:#15803d; }
  .rec-list { margin-top: 8px; border-top: 1px solid #bae6fd; padding-top: 8px; }
  .rec-list li { font-size: 0.79rem; color: #0369a1; margin-left: 16px; margin-bottom: 3px; }

  .footer { text-align: center; padding: 24px; color: #94a3b8; font-size: 0.8rem; border-top: 1px solid #e2e8f0; margin-top: 10px; }
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <h1>Website Crawl — AI Test Report</h1>
  <div class="sub">Generated: {{ timestamp }}</div>
  <div class="url-box">{{ start_url }}</div>
</div>

<!-- SUMMARY CARDS -->
<div class="summary">
  <div class="card total"><div class="num">{{ summary.total }}</div><div class="lbl">Pages Tested</div></div>
  <div class="card pass"><div class="num">{{ summary.passed }}</div><div class="lbl">Passed</div></div>
  <div class="card fail"><div class="num">{{ summary.failed }}</div><div class="lbl">Failed</div></div>
  <div class="card warn"><div class="num">{{ summary.warnings }}</div><div class="lbl">Warnings</div></div>
  <div class="card rate"><div class="num">{{ pass_pct }}%</div><div class="lbl">Pass Rate</div></div>
</div>

<!-- PROGRESS BAR -->
<div class="progress-wrap">
  <div class="progress-bar">
    <div class="progress-pass" style="width:{{ pass_pct }}%"></div>
    <div class="progress-warn" style="width:{{ warn_pct }}%"></div>
    <div class="progress-fail" style="width:{{ fail_pct }}%"></div>
  </div>
  <div class="progress-labels">
    <span><span class="dot" style="background:#22c55e"></span>Pass {{ summary.passed }}</span>
    <span><span class="dot" style="background:#f59e0b"></span>Warning {{ summary.warnings }}</span>
    <span><span class="dot" style="background:#ef4444"></span>Fail {{ summary.failed }}</span>
  </div>
</div>

<!-- PAGES OVERVIEW TABLE -->
<div class="section">
  <div class="section-title">All Pages Overview</div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Page Title</th>
        <th>Full URL</th>
        <th>Status</th>
        <th>Load Time</th>
        <th>UI Score</th>
        <th>TC Pass/Fail</th>
      </tr>
    </thead>
    <tbody>
      {% for r in page_results %}
      {% set tc_pass = r.test_cases | selectattr('result','eq','pass') | list | length %}
      {% set tc_fail = r.test_cases | selectattr('result','eq','fail') | list | length %}
      {% set tc_warn = r.test_cases | selectattr('result','eq','warn') | list | length %}
      <tr>
        <td style="font-weight:700;color:#6366f1;">P-{{ '%02d' % r.page_num }}</td>
        <td style="font-size:0.82rem;color:#475569;" title="{{ r.title }}">{{ r.title or '(no title)' }}</td>
        <td class="full-url"><a href="{{ r.url }}" target="_blank">{{ r.url }}</a></td>
        <td><span class="badge badge-{{ r.status }}">{{ r.status }}</span></td>
        <td>
          {% if r.load_time_ms is not none %}
            <span class="{% if r.load_time_ms < 2000 %}load-fast{% elif r.load_time_ms < 5000 %}load-ok{% else %}load-slow{% endif %}">{{ r.load_time_ms }}ms</span>
          {% else %}—{% endif %}
        </td>
        <td>
          {% if r.ui_analysis and r.ui_analysis.ui_score is not none %}
            {% set s = r.ui_analysis.ui_score %}
            <span class="score-pill {% if s >= 8 %}score-good{% elif s >= 5 %}score-mid{% else %}score-bad{% endif %}">{{ s }}/10</span>
          {% else %}—{% endif %}
        </td>
        <td style="font-size:0.82rem;">
          <span style="color:#15803d;font-weight:700;">{{ tc_pass }}P</span> /
          <span style="color:#b91c1c;font-weight:700;">{{ tc_fail }}F</span> /
          <span style="color:#92400e;font-weight:700;">{{ tc_warn }}W</span>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- DETAILED PAGE CARDS -->
<div class="section">
  <div class="section-title">Detailed Page Reports</div>

  {% for r in page_results %}
  {% set scenarios = r.test_cases | groupby('scenario') %}
  <div class="page-card">

    <!-- Page Header -->
    <div class="page-card-header">
      <span class="page-num-badge">P-{{ '%02d' % r.page_num }}</span>
      <div class="page-info">
        <div class="pg-title">{{ r.title or '(no title)' }}</div>
        <div class="pg-url"><a href="{{ r.url }}" target="_blank">{{ r.url }}</a></div>
      </div>
      <span class="badge badge-{{ r.status }}">{{ r.status }}</span>
      {% if r.ui_analysis and r.ui_analysis.ui_score is not none %}
        {% set s = r.ui_analysis.ui_score %}
        <span class="score-pill {% if s >= 8 %}score-good{% elif s >= 5 %}score-mid{% else %}score-bad{% endif %}" style="margin-left:8px;">UI {{ s }}/10</span>
      {% endif %}
    </div>

    <!-- Meta Row -->
    <div class="page-meta">
      <div class="meta-item">Load Time: <strong>{% if r.load_time_ms is not none %}{{ r.load_time_ms }}ms{% else %}N/A{% endif %}</strong></div>
      <div class="meta-item">Links Found: <strong>{{ r.links_found }}</strong></div>
      <div class="meta-item">Console Errors: <strong>{{ r.console_errors|length }}</strong></div>
      <div class="meta-item">Test Cases:
        <strong style="color:#15803d;">{{ r.test_cases|selectattr('result','eq','pass')|list|length }} Pass</strong> /
        <strong style="color:#b91c1c;">{{ r.test_cases|selectattr('result','eq','fail')|list|length }} Fail</strong> /
        <strong style="color:#92400e;">{{ r.test_cases|selectattr('result','eq','warn')|list|length }} Warn</strong>
      </div>
    </div>

    <!-- Body: Test Scenarios + Screenshot side by side -->
    <div class="page-card-body">
      <div class="left-col">

        {% if r.error %}
        <div class="error-box">Error: {{ r.error }}</div>
        {% endif %}

        {% if r.console_errors %}
        <div class="console-box">
          <div class="console-title">Console Errors</div>
          {% for err in r.console_errors %}<code>{{ err }}</code>{% endfor %}
        </div>
        {% endif %}

        <!-- TEST SCENARIOS & TEST CASES -->
        {% for scenario_name, cases in scenarios %}
        {% set s_pass = cases | selectattr('result','eq','pass') | list | length %}
        {% set s_fail = cases | selectattr('result','eq','fail') | list | length %}
        {% set s_warn = cases | selectattr('result','eq','warn') | list | length %}
        <div class="scenario-block">
          <div class="scenario-header">
            {{ scenario_name }}
            <div class="s-counts">
              {% if s_pass %}<span class="s-count pass">{{ s_pass }} P</span>{% endif %}
              {% if s_fail %}<span class="s-count fail">{{ s_fail }} F</span>{% endif %}
              {% if s_warn %}<span class="s-count warn">{{ s_warn }} W</span>{% endif %}
            </div>
          </div>
          <div class="scenario-cases">
            {% for tc in cases %}
            <div class="tc-row">
              <span class="tc-id">{{ tc.tc_id }}</span>
              <span class="tc-name">{{ tc.name }}</span>
              <span class="badge badge-{{ tc.result }}">{{ tc.result }}</span>
              <span class="tc-detail">{{ tc.detail }}</span>
            </div>
            {% endfor %}
          </div>
        </div>
        {% endfor %}

        <!-- UI Issues -->
        {% if r.ui_analysis and r.ui_analysis.issues %}
        <div class="ui-issues" style="margin-top:10px;">
          <h5>AI UI Issues — {{ r.ui_analysis.summary }}</h5>
          {% for issue in r.ui_analysis.issues %}
          <div class="issue-row">
            <span class="sev sev-{{ issue.severity }}">{{ issue.severity }}</span>
            <span style="color:#475569">[{{ issue.type }}]</span>
            <span>{{ issue.description }}</span>
          </div>
          {% endfor %}
          {% if r.ui_analysis.recommendations %}
          <div class="rec-list"><ul>{% for rec in r.ui_analysis.recommendations %}<li>{{ rec }}</li>{% endfor %}</ul></div>
          {% endif %}
        </div>
        {% endif %}

      </div>
      <div class="right-col">
        {% if r.screenshot_b64 %}
        <div class="ss-wrap">
          <img src="{{ r.screenshot_b64 }}" alt="Screenshot P-{{ r.page_num }}" />
        </div>
        {% endif %}
      </div>
    </div>

  </div>
  {% endfor %}
</div>

<div class="footer">
  AI Test Agent &bull; Website Crawler &bull; Powered by Claude + Playwright &bull; {{ timestamp }}
</div>
</body>
</html>"""


def _screenshot_src(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    return "/screenshots/" + os.path.basename(path)


def _url_to_slug(url: str) -> str:
    if not url:
        return "unknown"
    parsed = urlparse(url if url.startswith("http") else "https://" + url)
    path = re.sub(r'\.[a-z]{2,4}$', '', parsed.path.rstrip("/"))
    slug = parsed.netloc + path
    slug = re.sub(r'[\\/*?:"<>|.]', '_', slug)
    slug = re.sub(r'_+', '_', slug)
    return slug[:80].strip("_") or "unknown"


def generate_crawl_report(crawl_data: dict) -> str:
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
    summary = crawl_data["summary"]
    page_results = crawl_data["page_results"]
    total = summary["total"]

    pass_pct = round(summary["passed"] / total * 100) if total else 0
    fail_pct = round(summary["failed"] / total * 100) if total else 0
    warn_pct = round(summary["warnings"] / total * 100) if total else 0

    for r in page_results:
        r["screenshot_b64"] = _screenshot_src(r["screenshot"]) if r.get("screenshot") else ""
        r["test_cases"] = build_test_cases(r)

    template = Template(CRAWL_TEMPLATE)
    html = template.render(
        start_url=crawl_data["start_url"],
        timestamp=timestamp,
        summary=summary,
        pass_pct=pass_pct,
        fail_pct=fail_pct,
        warn_pct=warn_pct,
        page_results=page_results,
    )

    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    slug = _url_to_slug(crawl_data["start_url"])
    filename = f"Crawl Report - {slug}.html"
    path = os.path.join(REPORT_OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Report] Crawl report saved: {path}")
    return path
