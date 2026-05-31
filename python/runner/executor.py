import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from config import SCREENSHOT_DIR, BROWSER_HEADLESS, BROWSER_TIMEOUT

# Common selectors for error messages across popular UI frameworks
_ERROR_SELECTORS = [
    ".error", ".error-message", ".errors", ".error-text",
    ".alert-danger", ".alert-error",
    ".invalid-feedback", ".field-error", ".form-error",
    "[role='alert']", "[aria-live='polite']", "[aria-live='assertive']",
    "[class*='error']", "[class*='invalid']", "[class*='Error']",
    ".help-block", ".validation-message", ".text-danger", ".text-red",
    "span.required", ".form-text.text-danger",
]

# Typical valid values to fill in forms during positive testing
_POSITIVE_FIELD_VALUES = {
    "email":    "testuser@example.com",
    "password": "TestPass@123",
    "name":     "Test User",
    "first":    "Test",
    "last":     "User",
    "phone":    "9876543210",
    "mobile":   "9876543210",
    "address":  "123 Test Street",
    "city":     "Mumbai",
    "zip":      "400001",
    "postal":   "400001",
    "username": "testuser123",
    "message":  "This is a test message for QA purposes.",
    "comment":  "Test comment",
    "search":   "test",
    "query":    "test",
    "subject":  "Test Subject",
    "title":    "Test Title",
    "default":  "test_value",
}


def _screenshot(page: Page, name: str, step_index: int, full_page: bool = False) -> str:
    """Viewport screenshot (full_page only when explicitly needed)."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    filename = f"step_{step_index:02d}_{name}_{ts}.png"
    path = os.path.join(SCREENSHOT_DIR, filename)
    try:
        page.screenshot(path=path, full_page=full_page)
    except Exception:
        try:
            page.screenshot(path=path)
        except Exception:
            return ""
    return path


def _element_screenshot(page: Page, selector: str, name: str, step_index: int) -> str:
    """Screenshot of a specific element; falls back to viewport only."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    filename = f"step_{step_index:02d}_{name}_{ts}.png"
    path = os.path.join(SCREENSHOT_DIR, filename)
    try:
        el = page.locator(selector).first
        if el.count() > 0 and el.is_visible():
            el.scroll_into_view_if_needed()
            el.screenshot(path=path)
            return path
    except Exception:
        pass
    # fallback: viewport only (not full page)
    try:
        page.screenshot(path=path, full_page=False)
    except Exception:
        return ""
    return path


def _find(page: Page, selector: str):
    """Try multiple selector strategies to find an element."""
    strategies = [
        selector,
        f"text={selector}",
        f"[placeholder*='{selector}']",
        f"[aria-label*='{selector}']",
    ]
    for s in strategies:
        try:
            el = page.locator(s).first
            if el.count() > 0:
                return el
        except Exception:
            continue
    return page.locator(selector).first


def _guess_field_value(name_or_type: str) -> str:
    key = name_or_type.lower()
    for k, v in _POSITIVE_FIELD_VALUES.items():
        if k in key:
            return v
    return _POSITIVE_FIELD_VALUES["default"]


# ─── ACTION: check_all_links ───────────────────────────────────────────────────
def _check_all_links(page: Page, result: dict) -> None:
    raw_links = page.eval_on_selector_all(
        "a[href]",
        """els => [...new Set(
            els.map(e => e.href)
               .filter(h => h && h.startsWith('http') && !h.startsWith('javascript'))
        )]"""
    )

    links = raw_links[:15]
    print(f"    Found {len(raw_links)} links, testing first {len(links)}...")

    link_results = []
    check_page = page.context.new_page()
    check_page.set_default_timeout(10000)

    for link in links:
        try:
            resp = check_page.goto(link, wait_until="domcontentloaded", timeout=12000)
            status = resp.status if resp else 0
            ok = status < 400
            link_results.append({"url": link, "status": status, "ok": ok})
            marker = "OK" if ok else f"BROKEN({status})"
            short = link[:60] + ("..." if len(link) > 60 else "")
            print(f"      {marker}: {short}")
        except Exception as e:
            link_results.append({"url": link, "status": 0, "ok": False, "error": str(e)[:80]})
            print(f"      ERROR: {link[:60]}")

    check_page.close()

    broken = [l for l in link_results if not l["ok"]]
    result["link_results"]  = link_results
    result["links_tested"]  = len(link_results)
    result["links_broken"]  = len(broken)

    if broken:
        result["status"] = "warn"
        result["error"] = (
            f"{len(broken)} broken link(s): "
            + ", ".join(l["url"][:60] for l in broken[:3])
        )


# ─── ACTION: check_text_structure ─────────────────────────────────────────────
def _check_text_structure(page: Page, result: dict) -> None:
    h1 = page.locator("h1").count()
    h2 = page.locator("h2").count()
    h3 = page.locator("h3").count()
    paras = page.locator("p").count()
    links = page.locator("a").count()

    issues = []
    if h1 == 0:
        issues.append("No H1 heading found")
    if h1 > 1:
        issues.append(f"Multiple H1 headings ({h1}) — should be exactly 1")

    result["text_structure"] = {
        "h1": h1, "h2": h2, "h3": h3,
        "paragraphs": paras, "links": links,
        "issues": issues,
    }

    if issues:
        raise AssertionError("Text structure issues: " + " | ".join(issues))


# ─── ACTION: fill_form_negative ────────────────────────────────────────────────
def _fill_form_negative(page: Page, selector: str, result: dict) -> None:
    form_sel = selector or "form"
    inputs = page.locator(
        f"{form_sel} input:not([type='hidden']):not([type='submit']):not([type='checkbox']):not([type='radio'])"
    )
    textareas = page.locator(f"{form_sel} textarea")

    count = inputs.count()
    for i in range(count):
        try:
            inputs.nth(i).fill("")
        except Exception:
            pass

    ta_count = textareas.count()
    for i in range(ta_count):
        try:
            textareas.nth(i).fill("")
        except Exception:
            pass

    print(f"    Cleared {count} input(s), {ta_count} textarea(s). Submitting empty form...")

    submit = page.locator(
        f"{form_sel} button[type='submit'], {form_sel} input[type='submit'], "
        f"{form_sel} button:has-text('Submit'), {form_sel} button:has-text('Send'), "
        f"{form_sel} button:has-text('Login'), {form_sel} button:has-text('Register'), "
        f"{form_sel} button:has-text('Sign')"
    ).first
    if submit.count() > 0:
        try:
            submit.click()
        except Exception:
            pass

    result["form_negative_tested"] = True


# ─── ACTION: fill_form_positive ────────────────────────────────────────────────
def _fill_form_positive(page: Page, selector: str, result: dict) -> None:
    form_sel = selector or "form"
    inputs = page.locator(
        f"{form_sel} input:not([type='hidden']):not([type='submit']):not([type='checkbox']):not([type='radio'])"
    )
    textareas = page.locator(f"{form_sel} textarea")

    count = inputs.count()
    filled = 0
    for i in range(count):
        el = inputs.nth(i)
        try:
            itype = el.get_attribute("type") or ""
            iname = (el.get_attribute("name") or el.get_attribute("placeholder") or itype).lower()
            val = _guess_field_value(iname)
            el.fill(val)
            filled += 1
        except Exception:
            pass

    ta_count = textareas.count()
    for i in range(ta_count):
        try:
            textareas.nth(i).fill("This is a test message for QA purposes.")
            filled += 1
        except Exception:
            pass

    print(f"    Filled {filled} field(s) with valid data. Submitting...")

    submit = page.locator(
        f"{form_sel} button[type='submit'], {form_sel} input[type='submit'], "
        f"{form_sel} button:has-text('Submit'), {form_sel} button:has-text('Send'), "
        f"{form_sel} button:has-text('Login'), {form_sel} button:has-text('Register'), "
        f"{form_sel} button:has-text('Sign')"
    ).first
    if submit.count() > 0:
        try:
            submit.click()
        except Exception:
            pass

    result["form_positive_tested"] = True
    result["fields_filled"]        = filled


# ─── ACTION: assert_error_message ─────────────────────────────────────────────
def _assert_error_message(page: Page, result: dict) -> None:
    found_texts = []
    for sel in _ERROR_SELECTORS:
        try:
            els = page.locator(sel)
            n = els.count()
            for i in range(min(n, 5)):
                el = els.nth(i)
                if el.is_visible():
                    txt = el.inner_text().strip()
                    if txt:
                        found_texts.append(txt[:120])
        except Exception:
            continue

    # Also check aria-invalid fields
    invalid_count = page.locator("[aria-invalid='true']").count()
    if invalid_count:
        found_texts.append(f"{invalid_count} field(s) marked aria-invalid")

    result["error_messages"] = found_texts
    result["error_count"]    = len(found_texts)

    if not found_texts and invalid_count == 0:
        raise AssertionError(
            "No error messages found after empty form submit — "
            "form may be missing validation"
        )


# ─── ACTION: assert_not_visible ───────────────────────────────────────────────
def _assert_not_visible(page: Page, selector: str, result: dict) -> None:
    el = page.locator(selector).first
    if el.count() > 0 and el.is_visible():
        raise AssertionError(f"Element should NOT be visible but is: {selector}")
    result["assert_not_visible"] = True


# ─── ACTION: assert_count ─────────────────────────────────────────────────────
def _assert_count(page: Page, selector: str, value: str, result: dict) -> None:
    expected = int(value) if value and str(value).isdigit() else 0
    actual = page.locator(selector).count()
    result["element_count"] = {"selector": selector, "expected": expected, "actual": actual}
    if actual != expected:
        raise AssertionError(
            f"Element count mismatch for '{selector}': expected {expected}, got {actual}"
        )


# ─── ACTION: check_console_errors ─────────────────────────────────────────────
def _check_console_errors(console_errors: list[str], page_errors: list[str], result: dict) -> None:
    all_errors = list(console_errors) + list(page_errors)
    result["console_errors"] = all_errors
    result["console_error_count"] = len(all_errors)
    if all_errors:
        raise AssertionError(
            f"{len(all_errors)} console error(s): " + " | ".join(all_errors[:3])
        )


# ─── ACTION: api_check ────────────────────────────────────────────────────────
def _api_check(page: Page, api_url: str, result: dict) -> None:
    resp = page.evaluate(
        """(url) => fetch(url).then(r => ({status: r.status, ok: r.ok}))
                              .catch(e => ({status: 0, ok: false, error: e.message}))""",
        api_url,
    )
    result["api_response"] = resp
    if not resp.get("ok"):
        raise AssertionError(
            f"API check failed: {api_url} → HTTP {resp.get('status', 0)}"
        )


# ─── ACTION: performance_check ────────────────────────────────────────────────
def _performance_check(page: Page, result: dict) -> None:
    metrics = page.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0];
        if (!nav) return {dom_load: 0, page_load: 0, ttfb: 0};
        return {
            dom_load: Math.round(nav.domContentLoadedEventEnd),
            page_load: Math.round(nav.loadEventEnd),
            ttfb: Math.round(nav.responseStart - nav.requestStart),
        };
    }""")
    result["performance"] = metrics
    load_ms = metrics.get("page_load", 0)
    print(f"\n    Load: {load_ms}ms  TTFB: {metrics.get('ttfb', 0)}ms", end=" ")
    if load_ms > 5000:
        result["status"] = "warn"
        result["error"] = f"Slow page load: {load_ms}ms (threshold: 5000ms)"


# ─── MAIN RUNNER ──────────────────────────────────────────────────────────────
def run_tests(steps: list[dict]) -> list[dict]:
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=BROWSER_HEADLESS)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        # Capture JS console errors & uncaught exceptions for check_console_errors
        _console_errors: list[str] = []
        _page_errors: list[str] = []
        page.on("console", lambda msg: _console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: _page_errors.append(str(exc)))

        for i, step in enumerate(steps):
            action      = step.get("action", "")
            description = step.get("description", "")
            selector    = step.get("selector")
            value       = step.get("value")
            wait_after  = step.get("wait_after", 1000)

            result = {
                "step":        i + 1,
                "action":      action,
                "description": description,
                "status":      "pass",
                "screenshot":  None,
                "error":       None,
                "url":         page.url if page.url else "",
            }

            print(f"  Step {i+1}: [{action}] {description}...", end=" ")

            try:
                # ── navigate ──────────────────────────────────────────────
                if action == "navigate":
                    page.goto(value, wait_until="domcontentloaded")

                # ── click ─────────────────────────────────────────────────
                elif action == "click":
                    _find(page, selector).click()

                # ── type ──────────────────────────────────────────────────
                elif action == "type":
                    el = _find(page, selector)
                    el.clear()
                    el.type(value)

                # ── hover ─────────────────────────────────────────────────
                elif action == "hover":
                    el = page.locator(selector).first
                    if el.count() == 0:
                        raise AssertionError(f"No element found for hover: {selector}")
                    el.hover()
                    page.wait_for_timeout(600)

                # ── scroll ────────────────────────────────────────────────
                elif action == "scroll":
                    page.evaluate("window.scrollBy(0, 400)")

                # ── assert_text ───────────────────────────────────────────
                elif action == "assert_text":
                    if value.lower() not in page.content().lower():
                        raise AssertionError(f"Text '{value}' not found on page")

                # ── assert_visible ────────────────────────────────────────
                elif action == "assert_visible":
                    el = page.locator(selector).first
                    if el.count() == 0 or not el.is_visible():
                        raise AssertionError(f"Element not visible: {selector}")

                # ── assert_url ────────────────────────────────────────────
                elif action == "assert_url":
                    if value not in page.url:
                        raise AssertionError(f"URL mismatch: expected '{value}' in '{page.url}'")

                # ── check_all_links ───────────────────────────────────────
                elif action == "check_all_links":
                    _check_all_links(page, result)

                # ── check_text_structure ──────────────────────────────────
                elif action == "check_text_structure":
                    _check_text_structure(page, result)

                # ── fill_form_negative ────────────────────────────────────
                elif action == "fill_form_negative":
                    _fill_form_negative(page, selector, result)

                # ── fill_form_positive ────────────────────────────────────
                elif action == "fill_form_positive":
                    _fill_form_positive(page, selector, result)

                # ── assert_error_message ──────────────────────────────────
                elif action == "assert_error_message":
                    _assert_error_message(page, result)

                # ── assert_not_visible ────────────────────────────────────
                elif action == "assert_not_visible":
                    _assert_not_visible(page, selector, result)

                # ── assert_count ──────────────────────────────────────────
                elif action == "assert_count":
                    _assert_count(page, selector, value, result)

                # ── check_console_errors ──────────────────────────────────
                elif action == "check_console_errors":
                    _check_console_errors(_console_errors, _page_errors, result)

                # ── api_check ─────────────────────────────────────────────
                elif action == "api_check":
                    _api_check(page, value, result)

                # ── performance_check ─────────────────────────────────────
                elif action == "performance_check":
                    _performance_check(page, result)

                # ── select / wait / screenshot ────────────────────────────
                elif action == "select":
                    page.select_option(selector, value)
                elif action == "wait":
                    page.wait_for_timeout(int(value) if value else wait_after)
                elif action == "screenshot":
                    pass  # just takes screenshot below

                page.wait_for_timeout(wait_after)

                # Element-specific screenshot where it makes sense
                if action == "navigate":
                    result["screenshot"] = _screenshot(page, "navigate", i, full_page=True)
                elif action == "hover" and selector:
                    result["screenshot"] = _element_screenshot(page, selector, "hover", i)
                elif action in ("click", "assert_visible") and selector:
                    result["screenshot"] = _element_screenshot(page, selector, action, i)
                elif action == "check_text_structure":
                    result["screenshot"] = _element_screenshot(page, "h1, h2, h3", "text_structure", i)
                elif action in ("fill_form_negative", "fill_form_positive", "assert_error_message"):
                    form_sel = selector or "form"
                    result["screenshot"] = _element_screenshot(page, form_sel, action, i)
                elif action == "screenshot":
                    result["screenshot"] = _screenshot(page, value or "capture", i, full_page=True)
                elif action in ("scroll", "assert_text", "assert_url", "check_all_links",
                               "check_console_errors", "api_check", "performance_check",
                               "assert_count", "assert_not_visible"):
                    result["screenshot"] = _screenshot(page, action, i, full_page=False)
                else:
                    result["screenshot"] = _screenshot(page, action, i, full_page=False)

                result["url"] = page.url
                print("PASS")

            except PlaywrightTimeout as e:
                result["status"] = "fail"
                result["error"]  = f"Timeout: {str(e)[:200]}"
                try:
                    result["screenshot"] = _screenshot(page, f"error_{action}", i)
                except Exception:
                    pass
                print("FAIL (timeout)")

            except AssertionError as e:
                result["status"] = "fail"
                result["error"]  = str(e)
                try:
                    result["screenshot"] = _screenshot(page, f"error_{action}", i)
                except Exception:
                    pass
                print(f"FAIL (assertion)")

            except Exception as e:
                result["status"] = "warn"
                result["error"]  = str(e)[:300]
                try:
                    result["screenshot"] = _screenshot(page, f"warn_{action}", i)
                except Exception:
                    pass
                print("WARN")

            results.append(result)

        browser.close()

    return results
