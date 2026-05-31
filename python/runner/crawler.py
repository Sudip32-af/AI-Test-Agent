import os
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, Page
from config import SCREENSHOT_DIR, BROWSER_HEADLESS, BROWSER_TIMEOUT

MAX_PAGES = 30


def _same_domain(base_url: str, url: str) -> bool:
    base = urlparse(base_url)
    target = urlparse(url)
    return base.netloc == target.netloc


def _normalize(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl().rstrip("/")


def _get_all_links(page: Page, base_url: str) -> list[str]:
    try:
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = []
        for href in hrefs:
            full = urljoin(base_url, href)
            if _same_domain(base_url, full) and full.startswith("http"):
                norm = _normalize(full)
                if norm not in links:
                    links.append(norm)
        return links
    except Exception:
        return []


def _take_screenshot(page: Page, name: str) -> str:
    ts = datetime.now().strftime("%H%M%S%f")[:10]
    safe_name = name.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_")[:60]
    filename = f"page_{safe_name}_{ts}.png"
    path = os.path.join(SCREENSHOT_DIR, filename)
    try:
        page.screenshot(path=path, full_page=True)
        return path
    except Exception:
        return None


def crawl_and_test(start_url: str) -> dict:
    visited = set()
    queue = [_normalize(start_url)]
    page_results = []
    console_errors = {}

    print(f"\n[Crawler] Starting: {start_url}")
    print(f"[Crawler] Max pages: {MAX_PAGES}")
    print("-" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=BROWSER_HEADLESS)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        while queue and len(visited) < MAX_PAGES:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            page_num = len(visited)
            print(f"  [{page_num}/{MAX_PAGES}] Testing: {url[:70]}...", end=" ")

            page = context.new_page()
            errors = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

            result = {
                "page_num": page_num,
                "url": url,
                "status": "pass",
                "load_time_ms": None,
                "screenshot": None,
                "title": "",
                "error": None,
                "console_errors": [],
                "links_found": 0,
                "ui_analysis": None,
            }

            try:
                t_start = time.time()
                response = page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT)
                load_time = round((time.time() - t_start) * 1000)

                result["load_time_ms"] = load_time
                result["title"] = page.title()

                http_status = response.status if response else 0
                if http_status >= 400:
                    result["status"] = "fail"
                    result["error"] = f"HTTP {http_status}"
                elif load_time > 5000:
                    result["status"] = "warn"
                    result["error"] = f"Slow load: {load_time}ms"
                else:
                    result["status"] = "pass"

                page.wait_for_timeout(1500)

                result["screenshot"] = _take_screenshot(page, url)
                result["console_errors"] = errors[:5]

                if errors:
                    if result["status"] == "pass":
                        result["status"] = "warn"
                    result["error"] = (result["error"] or "") + f" | Console errors: {len(errors)}"

                # Collect new links
                new_links = _get_all_links(page, start_url)
                result["links_found"] = len(new_links)
                for link in new_links:
                    norm = _normalize(link)
                    if norm not in visited and norm not in queue:
                        queue.append(norm)

                print(f"{result['status'].upper()} ({load_time}ms) | Links: {len(new_links)}")

            except Exception as e:
                result["status"] = "fail"
                result["error"] = str(e)[:200]
                try:
                    result["screenshot"] = _take_screenshot(page, url)
                except Exception:
                    pass
                print(f"FAIL - {str(e)[:60]}")

            finally:
                page.close()

            page_results.append(result)

        browser.close()

    total   = len(page_results)
    passed  = sum(1 for r in page_results if r["status"] == "pass")
    failed  = sum(1 for r in page_results if r["status"] == "fail")
    warning = sum(1 for r in page_results if r["status"] == "warn")

    print(f"\n[Crawler] Done! {total} pages tested — {passed} pass, {failed} fail, {warning} warn")

    return {
        "start_url": start_url,
        "page_results": page_results,
        "summary": {"total": total, "passed": passed, "failed": failed, "warnings": warning}
    }
