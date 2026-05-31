import os
import re
from datetime import datetime
from urllib.parse import urlparse
from jinja2 import Template
from config import REPORT_OUTPUT_DIR

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Test Report</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f1f5f9; color: #1e293b; }

  /* HEADER */
  .header { background: linear-gradient(135deg, #1e3a5f 0%, #7c3aed 100%); padding: 36px 40px; }
  .header h1 { color: white; font-size: 1.8rem; font-weight: 700; letter-spacing: 1px; }
  .header .sub { color: #c4b5fd; margin-top: 6px; font-size: 0.9rem; }
  .header .prompt-box { margin-top: 14px; background: rgba(255,255,255,0.1); border-left: 4px solid #a78bfa; padding: 10px 16px; border-radius: 0 8px 8px 0; color: #e9d5ff; font-size: 0.95rem; }

  /* SUMMARY CARDS */
  .summary { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; padding: 24px 40px; }
  .card { background: white; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-top: 4px solid #e2e8f0; }
  .card.total  { border-color: #6366f1; }
  .card.pass   { border-color: #22c55e; }
  .card.fail   { border-color: #ef4444; }
  .card.warn   { border-color: #f59e0b; }
  .card.score  { border-color: #0ea5e9; }
  .card .num   { font-size: 2.2rem; font-weight: 800; }
  .card.total .num { color: #6366f1; }
  .card.pass  .num { color: #22c55e; }
  .card.fail  .num { color: #ef4444; }
  .card.warn  .num { color: #f59e0b; }
  .card.score .num { color: #0ea5e9; }
  .card .lbl { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; font-weight: 600; }

  /* PROGRESS BAR */
  .progress-wrap { padding: 0 40px 20px; }
  .progress-bar { height: 10px; background: #e2e8f0; border-radius: 10px; overflow: hidden; display: flex; }
  .progress-pass { background: #22c55e; transition: width 0.5s; }
  .progress-fail { background: #ef4444; }
  .progress-warn { background: #f59e0b; }
  .progress-labels { display: flex; gap: 20px; margin-top: 8px; font-size: 0.8rem; color: #64748b; }
  .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 4px; }

  /* TABLE */
  .section { padding: 0 40px 40px; }
  .section-title { font-size: 1rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  .section-title::after { content: ''; flex: 1; height: 1px; background: #e2e8f0; }

  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  thead { background: #1e293b; color: white; }
  thead th { padding: 14px 16px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
  tbody tr { border-bottom: 1px solid #f1f5f9; transition: background 0.15s; }
  tbody tr:hover { background: #f8fafc; }
  tbody td { padding: 14px 16px; font-size: 0.88rem; vertical-align: middle; }
  .tc-num { font-weight: 700; color: #6366f1; }
  .tc-action { font-family: monospace; background: #f1f5f9; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; color: #475569; }
  .tc-desc { color: #1e293b; }
  .tc-url { font-family: monospace; font-size: 0.75rem; color: #94a3b8; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* BADGES */
  .badge { display: inline-flex; align-items: center; gap: 5px; padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
  .badge-pass { background: #dcfce7; color: #15803d; }
  .badge-fail { background: #fee2e2; color: #b91c1c; }
  .badge-warn { background: #fef3c7; color: #92400e; }
  .badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  /* UI SCORE */
  .ui-score { display: inline-flex; align-items: center; gap: 6px; font-size: 0.82rem; font-weight: 600; }
  .score-pill { padding: 2px 8px; border-radius: 10px; font-size: 0.78rem; font-weight: 700; }
  .score-good { background: #dcfce7; color: #15803d; }
  .score-mid  { background: #fef3c7; color: #92400e; }
  .score-bad  { background: #fee2e2; color: #b91c1c; }

  /* DETAIL SECTION */
  .detail-section { margin-top: 30px; }
  .step-card { background: white; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); overflow: hidden; }
  .step-card-header { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #f1f5f9; cursor: pointer; }
  .step-card-header:hover { background: #f8fafc; }
  .step-num-badge { background: #1e293b; color: white; border-radius: 6px; padding: 4px 10px; font-size: 0.78rem; font-weight: 700; }
  .step-title { flex: 1; font-weight: 600; color: #1e293b; font-size: 0.9rem; }
  .step-body { padding: 16px 20px; }
  .error-box { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; padding: 12px 16px; font-family: monospace; font-size: 0.82rem; color: #b91c1c; margin-bottom: 14px; }
  .ss-wrap img { width: 100%; border-radius: 8px; border: 1px solid #e2e8f0; }
  .ui-issues { margin-top: 14px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 14px 16px; }
  .ui-issues h5 { color: #0369a1; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
  .issue-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; font-size: 0.83rem; }
  .sev { padding: 1px 7px; border-radius: 10px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; }
  .sev-high   { background: #fee2e2; color: #b91c1c; }
  .sev-medium { background: #fef3c7; color: #92400e; }
  .sev-low    { background: #dcfce7; color: #15803d; }
  .rec-list { margin-top: 10px; border-top: 1px solid #bae6fd; padding-top: 10px; }
  .rec-list li { font-size: 0.82rem; color: #0369a1; margin-left: 16px; margin-bottom: 3px; }

  /* EXTRA DATA BLOCKS */
  .data-block { margin-top: 12px; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; font-size: 0.82rem; }
  .data-block-title { background: #1e293b; color: white; padding: 8px 14px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
  .data-block-body  { padding: 12px 14px; background: white; }
  .link-row { display: flex; align-items: center; gap: 8px; padding: 5px 0; border-bottom: 1px solid #f8fafc; }
  .link-row:last-child { border-bottom: none; }
  .link-status-ok   { color: #15803d; font-weight: 700; font-size: 0.75rem; min-width: 40px; }
  .link-status-fail { color: #b91c1c; font-weight: 700; font-size: 0.75rem; min-width: 40px; }
  .link-url { font-family: monospace; font-size: 0.76rem; color: #475569; word-break: break-all; }
  .struct-row { display: flex; gap: 20px; flex-wrap: wrap; }
  .struct-item { text-align: center; background: #f8fafc; border-radius: 8px; padding: 8px 14px; }
  .struct-item .snum { font-size: 1.4rem; font-weight: 800; color: #6366f1; }
  .struct-item .slbl { font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
  .struct-issue { background: #fef2f2; color: #b91c1c; border-radius: 6px; padding: 6px 10px; margin-top: 8px; font-size: 0.8rem; }
  .err-msg-row { background: #fef2f2; border-left: 3px solid #ef4444; padding: 6px 10px; margin-bottom: 4px; border-radius: 0 6px 6px 0; font-size: 0.8rem; color: #7f1d1d; font-family: monospace; }
  .form-badge { display: inline-flex; align-items: center; gap: 5px; background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; border-radius: 6px; padding: 4px 10px; font-size: 0.78rem; font-weight: 600; margin-right: 6px; }
  .action-tag { font-family: monospace; background: #f1f5f9; color: #334155; padding: 2px 7px; border-radius: 4px; font-size: 0.75rem; }

  /* FOOTER */
  .footer { text-align: center; padding: 24px; color: #94a3b8; font-size: 0.8rem; border-top: 1px solid #e2e8f0; margin-top: 20px; }
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <h1>AI Test Report</h1>
  <div class="sub">Generated on {{ timestamp }}</div>
  <div class="prompt-box"><strong>Test Prompt:</strong> {{ prompt }}</div>
</div>

<!-- SUMMARY CARDS -->
<div class="summary">
  <div class="card total"><div class="num">{{ total }}</div><div class="lbl">Total Test Cases</div></div>
  <div class="card pass"><div class="num">{{ passed }}</div><div class="lbl">Passed</div></div>
  <div class="card fail"><div class="num">{{ failed }}</div><div class="lbl">Failed</div></div>
  <div class="card warn"><div class="num">{{ warnings }}</div><div class="lbl">Warnings</div></div>
  <div class="card score"><div class="num">{{ pass_pct }}%</div><div class="lbl">Pass Rate</div></div>
</div>

<!-- PROGRESS BAR -->
<div class="progress-wrap">
  <div class="progress-bar">
    <div class="progress-pass" style="width:{{ pass_pct }}%"></div>
    <div class="progress-warn" style="width:{{ warn_pct }}%"></div>
    <div class="progress-fail" style="width:{{ fail_pct }}%"></div>
  </div>
  <div class="progress-labels">
    <span><span class="dot" style="background:#22c55e"></span>Pass {{ passed }}</span>
    <span><span class="dot" style="background:#f59e0b"></span>Warning {{ warnings }}</span>
    <span><span class="dot" style="background:#ef4444"></span>Fail {{ failed }}</span>
  </div>
</div>

<!-- TEST CASE TABLE -->
<div class="section">
  <div class="section-title">Test Case Summary</div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Test Case</th>
        <th>Action</th>
        <th>Status</th>
        <th>UI Score</th>
        <th>URL</th>
      </tr>
    </thead>
    <tbody>
      {% for r in results %}
      <tr>
        <td><span class="tc-num">TC-{{ '%02d' % r.step }}</span></td>
        <td class="tc-desc">{{ r.description }}</td>
        <td><span class="tc-action">{{ r.action }}</span></td>
        <td>
          <span class="badge badge-{{ r.status }}">{{ r.status }}</span>
        </td>
        <td>
          {% if r.ui_analysis and r.ui_analysis.ui_score is not none %}
            {% set s = r.ui_analysis.ui_score %}
            <span class="score-pill {% if s >= 8 %}score-good{% elif s >= 5 %}score-mid{% else %}score-bad{% endif %}">
              {{ s }}/10
            </span>
          {% else %}
            <span style="color:#cbd5e1">—</span>
          {% endif %}
        </td>
        <td class="tc-url" title="{{ r.url }}">{{ r.url }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- DETAILED STEPS -->
<div class="section">
  <div class="section-title">Detailed Test Steps</div>
  <div class="detail-section">
    {% for r in results %}
    <div class="step-card">
      <div class="step-card-header">
        <span class="step-num-badge">TC-{{ '%02d' % r.step }}</span>
        <span class="step-title">{{ r.description }}</span>
        <span class="badge badge-{{ r.status }}">{{ r.status }}</span>
        {% if r.ui_analysis and r.ui_analysis.ui_score is not none %}
          {% set s = r.ui_analysis.ui_score %}
          <span class="score-pill {% if s >= 8 %}score-good{% elif s >= 5 %}score-mid{% else %}score-bad{% endif %}" style="margin-left:8px">
            UI {{ s }}/10
          </span>
        {% endif %}
      </div>
      <div class="step-body">

        {% if r.error %}
        <div class="error-box">&#9888; {{ r.error }}</div>
        {% endif %}

        <!-- Form test badges -->
        {% if r.form_negative_tested or r.form_positive_tested or r.fields_filled %}
        <div style="margin-bottom:10px;">
          {% if r.form_negative_tested %}<span class="form-badge">&#10007; Negative Test</span>{% endif %}
          {% if r.form_positive_tested %}<span class="form-badge">&#10003; Positive Test</span>{% endif %}
          {% if r.fields_filled %}<span class="form-badge">{{ r.fields_filled }} fields filled</span>{% endif %}
        </div>
        {% endif %}

        <!-- Error messages found -->
        {% if r.error_messages %}
        <div class="data-block">
          <div class="data-block-title">&#9888; Validation Error Messages Found ({{ r.error_count }})</div>
          <div class="data-block-body">
            {% for msg in r.error_messages %}<div class="err-msg-row">{{ msg }}</div>{% endfor %}
          </div>
        </div>
        {% endif %}

        <!-- Text structure -->
        {% if r.text_structure %}
        <div class="data-block">
          <div class="data-block-title">
            &#182; Text Structure Check
            {% if r.text_structure.issues %}&nbsp;&#9888; Issues Found{% else %}&nbsp;&#10003; OK{% endif %}
          </div>
          <div class="data-block-body">
            <div class="struct-row">
              <div class="struct-item"><div class="snum">{{ r.text_structure.h1 }}</div><div class="slbl">H1</div></div>
              <div class="struct-item"><div class="snum">{{ r.text_structure.h2 }}</div><div class="slbl">H2</div></div>
              <div class="struct-item"><div class="snum">{{ r.text_structure.h3 }}</div><div class="slbl">H3</div></div>
              <div class="struct-item"><div class="snum">{{ r.text_structure.paragraphs }}</div><div class="slbl">Paragraphs</div></div>
              <div class="struct-item"><div class="snum">{{ r.text_structure.links }}</div><div class="slbl">Links</div></div>
            </div>
            {% for issue in r.text_structure.issues %}
            <div class="struct-issue">&#9888; {{ issue }}</div>
            {% endfor %}
          </div>
        </div>
        {% endif %}

        <!-- Links tested -->
        {% if r.link_results %}
        <div class="data-block">
          <div class="data-block-title">
            &#128279; Links Tested: {{ r.links_tested }}
            &nbsp;|&nbsp; Broken: {{ r.links_broken }}
          </div>
          <div class="data-block-body">
            {% for lnk in r.link_results %}
            <div class="link-row">
              {% if lnk.ok %}
                <span class="link-status-ok">{{ lnk.status }}</span>
              {% else %}
                <span class="link-status-fail">{{ lnk.status or 'ERR' }}</span>
              {% endif %}
              <span class="link-url"><a href="{{ lnk.url }}" target="_blank">{{ lnk.url[:90] }}</a></span>
            </div>
            {% endfor %}
          </div>
        </div>
        {% endif %}

        {% if r.screenshot_b64 %}
        <div class="ss-wrap" style="margin-top:12px;">
          <img src="{{ r.screenshot_b64 }}" alt="Screenshot TC-{{ r.step }}" />
        </div>
        {% endif %}

        {% if r.ui_analysis and r.ui_analysis.issues %}
        <div class="ui-issues">
          <h5>AI UI Analysis — {{ r.ui_analysis.summary }}</h5>
          {% for issue in r.ui_analysis.issues %}
          <div class="issue-row">
            <span class="sev sev-{{ issue.severity }}">{{ issue.severity }}</span>
            <span style="color:#475569">[{{ issue.type }}]</span>
            <span>{{ issue.description }}</span>
          </div>
          {% endfor %}
          {% if r.ui_analysis.recommendations %}
          <div class="rec-list">
            <ul>{% for rec in r.ui_analysis.recommendations %}<li>{{ rec }}</li>{% endfor %}</ul>
          </div>
          {% endif %}
        </div>
        {% endif %}

      </div>
    </div>
    {% endfor %}
  </div>
</div>

<div class="footer">
  AI Test Agent &bull; Powered by Claude + Playwright &bull; {{ timestamp }}
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


def generate_html_report(prompt: str, results: list[dict], url: str = "", prefix: str = "Report") -> str:
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")

    total    = len(results)
    passed   = sum(1 for r in results if r["status"] == "pass")
    failed   = sum(1 for r in results if r["status"] == "fail")
    warnings = sum(1 for r in results if r["status"] == "warn")

    pass_pct = round(passed / total * 100) if total else 0
    fail_pct = round(failed / total * 100) if total else 0
    warn_pct = round(warnings / total * 100) if total else 0

    for result in results:
        result["screenshot_b64"] = _screenshot_src(result["screenshot"]) if result.get("screenshot") else ""

    template = Template(HTML_TEMPLATE)
    html = template.render(
        prompt=prompt,
        timestamp=timestamp,
        total=total,
        passed=passed,
        failed=failed,
        warnings=warnings,
        pass_pct=pass_pct,
        fail_pct=fail_pct,
        warn_pct=warn_pct,
        results=results,
    )

    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    slug = _url_to_slug(url) if url else f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    filename = f"{prefix} - {slug}.html"
    path = os.path.join(REPORT_OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n[Report] HTML report saved: {path}")
    return path
