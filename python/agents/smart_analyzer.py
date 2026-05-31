"""
Smart Page Analyzer — URL dene par page structure automatically detect karta hai,
phir Claude ek comprehensive test plan generate karta hai covering:
  Functional, Integration, System E2E, and Regression basics.
"""

import re
import json
import anthropic
from playwright.sync_api import sync_playwright
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def scan_page(url: str) -> dict:
    """
    Playwright se page open karo, structure extract karo.
    Returns: forms, nav links, buttons, 3rd party scripts, API calls found.
    """
    print(f"[Smart] Page scan ho rahi hai: {url}")
    api_calls: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = context.new_page()

        # Intercept network requests to find API calls
        def on_request(req):
            u = req.url
            if any(k in u for k in ["/api/", "/v1/", "/v2/", ".json", "graphql"]):
                if u not in api_calls:
                    api_calls.append(u)

        page.on("request", on_request)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
        except Exception as e:
            browser.close()
            return {"url": url, "error": str(e), "forms": [], "nav_links": [],
                    "buttons": [], "third_party": [], "api_calls": [], "title": "", "h1": "", "links": 0}

        info = page.evaluate("""() => {
            // Forms
            const forms = [...document.querySelectorAll('form')].slice(0, 5).map(f => {
                const inputs = [...f.querySelectorAll('input:not([type=hidden]):not([type=submit]), textarea, select')]
                    .slice(0, 8)
                    .map(i => ({
                        type: i.type || i.tagName.toLowerCase(),
                        name: i.name || i.id || i.placeholder || '',
                        id: i.id || '',
                        selector: i.id ? '#' + i.id : i.name ? '[name="' + i.name + '"]' : i.tagName.toLowerCase(),
                    }));
                const submitBtns = [...f.querySelectorAll('button[type=submit], input[type=submit], button')]
                    .slice(0, 2).map(b => b.textContent.trim().slice(0, 30));
                return {
                    selector: f.id ? '#' + f.id : f.className ? '.' + f.className.split(' ')[0] : 'form',
                    inputs,
                    submit_buttons: submitBtns,
                };
            });

            // Navigation links
            const navLinks = [...document.querySelectorAll('nav a, header a, .nav a, .navbar a, .menu a, [role=navigation] a')]
                .slice(0, 12)
                .map(a => ({ text: a.textContent.trim().slice(0, 40), href: a.href }))
                .filter(a => a.href && a.href.startsWith('http') && a.text);

            // Buttons (outside forms)
            const buttons = [...document.querySelectorAll('button:not(form button), a.btn, a.button, [role=button]')]
                .slice(0, 10)
                .map(b => ({
                    text: b.textContent.trim().slice(0, 40),
                    selector: b.id ? '#' + b.id : b.className ? '.' + b.className.split(' ')[0] : 'button',
                }))
                .filter(b => b.text);

            // 3rd party scripts
            const thirdParty = [...document.querySelectorAll('script[src]')]
                .map(s => s.src)
                .filter(s => s && !s.includes(window.location.hostname))
                .map(s => {
                    try { return new URL(s).hostname; } catch { return null; }
                })
                .filter(Boolean)
                .slice(0, 8);

            return {
                title:      document.title,
                h1:         (document.querySelector('h1') || {}).textContent?.trim().slice(0, 80) || '',
                h2_count:   document.querySelectorAll('h2').length,
                links:      document.querySelectorAll('a[href]').length,
                images:     document.querySelectorAll('img').length,
                has_footer: !!document.querySelector('footer'),
                has_nav:    !!document.querySelector('nav, [role=navigation], header nav'),
                forms,
                nav_links:    navLinks,
                buttons,
                third_party:  [...new Set(thirdParty)],
            };
        }""")

        browser.close()

    info["url"]       = url
    info["api_calls"] = list(set(api_calls))[:10]
    print(f"[Smart] Scan complete — forms: {len(info['forms'])}, nav: {len(info['nav_links'])}, "
          f"buttons: {len(info['buttons'])}, 3rd-party: {len(info['third_party'])}, "
          f"api-calls: {len(info['api_calls'])}")
    return info


_SMART_SYSTEM = """You are a senior QA engineer. You receive real page information extracted from a live website.
Generate ONE comprehensive test plan covering ALL 4 test types based on what actually exists on the page.

AVAILABLE ACTIONS:
| action               | selector          | value                   | purpose                                        |
|----------------------|-------------------|-------------------------|------------------------------------------------|
| navigate             | null              | "https://..."           | Open a URL                                     |
| screenshot           | null              | "label"                 | Capture current state                          |
| scroll               | null              | null                    | Scroll down 400px                              |
| click                | CSS selector      | null                    | Click an element                               |
| hover                | CSS selector      | null                    | Hover over element                             |
| type                 | CSS selector      | "text"                  | Type into input                                |
| assert_text          | null              | "expected text"         | Assert text exists on page                     |
| assert_visible       | CSS selector      | null                    | Assert element visible                         |
| assert_not_visible   | CSS selector      | null                    | Assert element NOT visible                     |
| assert_url           | null              | "fragment"              | Assert URL contains value                      |
| assert_count         | CSS selector      | "N"                     | Assert exactly N elements                      |
| check_all_links      | null              | null                    | Test all links on page                         |
| check_text_structure | null              | null                    | Check H1/H2 heading hierarchy                  |
| check_console_errors | null              | null                    | Check JavaScript console errors                |
| fill_form_negative   | "form selector"   | "empty"                 | Submit empty form → trigger validation errors  |
| fill_form_positive   | "form selector"   | null                    | Fill with valid data → submit                  |
| assert_error_message | null              | null                    | Verify validation errors appeared              |
| api_check            | null              | "https://api-url"       | Check API returns 2xx                          |
| performance_check    | null              | null                    | Measure page load time & TTFB                  |
| wait                 | null              | "ms"                    | Wait milliseconds                              |

STRICT RULES:
1. Use the EXACT selectors from the page info provided (form id/class, input names, etc.)
2. Cover all 4 test categories based on what's on the page:
   - FUNCTIONAL: Test every form (negative + positive), every button, every interactive element
   - INTEGRATION: Check API calls found, 3rd party scripts loading, performance
   - SYSTEM E2E: Simulate a complete user journey using the actual nav links found
   - REGRESSION: check_text_structure + check_all_links + check_console_errors + performance_check
3. Always start with navigate + screenshot
4. For each form found: fill_form_negative → assert_error_message → screenshot → fill_form_positive → screenshot
5. For API calls found: use api_check
6. Use performance_check once
7. Use check_console_errors at least once
8. Max 30 steps
9. Return ONLY a JSON array — no markdown, no explanation

FORMAT: [{"action":"...","description":"...","selector":null,"value":"...","wait_after":1000}, ...]"""


def generate_smart_plan(page_info: dict, extra_task: str = "") -> list[dict]:
    """Claude ko page info pass karo, ek comprehensive test plan wapas milega."""
    url = page_info.get("url", "")

    context_lines = [
        f"URL: {url}",
        f"Page title: {page_info.get('title', '')}",
        f"H1: {page_info.get('h1', '')}",
        f"Total links: {page_info.get('links', 0)}",
        f"Has navigation: {page_info.get('has_nav', False)}",
        f"Has footer: {page_info.get('has_footer', False)}",
    ]

    forms = page_info.get("forms", [])
    if forms:
        context_lines.append(f"\nFORMS FOUND ({len(forms)}):")
        for i, f in enumerate(forms):
            inp_list = ", ".join(f"{x['type']}:{x['name']}" for x in f.get("inputs", []))
            context_lines.append(f"  Form {i+1}: selector='{f['selector']}' | inputs: {inp_list} | submit: {f.get('submit_buttons', [])}")
    else:
        context_lines.append("\nFORMS: None found")

    nav = page_info.get("nav_links", [])
    if nav:
        context_lines.append(f"\nNAVIGATION LINKS ({len(nav)}):")
        for lnk in nav[:8]:
            context_lines.append(f"  '{lnk['text']}' → {lnk['href']}")

    btns = page_info.get("buttons", [])
    if btns:
        context_lines.append(f"\nBUTTONS ({len(btns)}): " + ", ".join(f"'{b['text']}' ({b['selector']})" for b in btns[:6]))

    tp = page_info.get("third_party", [])
    if tp:
        context_lines.append(f"\nTHIRD-PARTY SCRIPTS: {', '.join(tp)}")

    apis = page_info.get("api_calls", [])
    if apis:
        context_lines.append(f"\nAPI CALLS DETECTED: {', '.join(apis[:5])}")

    if extra_task:
        context_lines.append(f"\nADDITIONAL FOCUS: {extra_task}")

    context = "\n".join(context_lines)
    print(f"[Smart] Claude ko page info bhej raha hai...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=5000,
        system=_SMART_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate a comprehensive test plan for this page:\n\n{context}\n\n"
                    "Cover ALL 4 test types (Functional, Integration, System E2E, Regression basics) "
                    "using the exact page information above."
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    match = re.search(r'\[[\s\S]*\]', raw)
    if match:
        raw = match.group(0)
    elif "```" in raw:
        for part in raw.split("```"):
            part = part.strip().lstrip("json").strip()
            if part.startswith("["):
                raw = part
                break

    raw = raw.replace('\n', ' ').replace('\r', '')
    raw = re.sub(r',\s*([}\]])', r'\1', raw)

    steps = json.loads(raw)
    print(f"[Smart] {len(steps)} comprehensive test steps generate hue")
    return steps
