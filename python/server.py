import os
import sys
import json
import uuid
import threading
from queue import Queue, Empty
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

app = FastAPI(title="AI Test Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PYTHON_DIR = os.path.dirname(__file__)
SCREENSHOTS_DIR = os.path.join(PYTHON_DIR, "screenshots")
REPORTS_DIR = os.path.join(PYTHON_DIR, "reports", "output")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

app.mount("/screenshots", StaticFiles(directory=SCREENSHOTS_DIR), name="screenshots")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

# Thread ID → Queue mapping for stdout capture
_thread_queues: dict[int, Queue] = {}
_tq_lock = threading.Lock()


class CapturingOutput:
    """Routes each thread's print() to its own SSE queue."""

    def __init__(self, original):
        self._original = original
        self._local = threading.local()

    def _buf(self):
        if not hasattr(self._local, "chars"):
            self._local.chars = ""
        return self._local

    def write(self, text):
        self._original.write(text)
        self._original.flush()
        tid = threading.current_thread().ident
        with _tq_lock:
            q = _thread_queues.get(tid)
        if q:
            b = self._buf()
            b.chars += text
            while "\n" in b.chars:
                line, b.chars = b.chars.split("\n", 1)
                if line.strip():
                    q.put({"type": "log", "msg": line})

    def flush(self):
        self._original.flush()


sys.stdout = CapturingOutput(sys.stdout)

active_runs: dict[str, dict] = {}


def _register(run_id: str) -> Queue:
    q: Queue = Queue()
    tid = threading.current_thread().ident
    with _tq_lock:
        _thread_queues[tid] = q
    active_runs[run_id] = {"queue": q, "done": False, "result": None, "error": None}
    return q


def _finish(run_id: str, result: dict | None, error: str | None):
    q = active_runs[run_id]["queue"]
    active_runs[run_id]["result"] = result
    active_runs[run_id]["error"] = error
    tid = threading.current_thread().ident
    with _tq_lock:
        _thread_queues.pop(tid, None)
    q.put({"type": "done"})
    active_runs[run_id]["done"] = True


class PromptRequest(BaseModel):
    url: str = ""
    task: str = ""


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 20


class AdvancedTestRequest(BaseModel):
    url: str
    task: str = ""


class RegressionRequest(BaseModel):
    url: str
    suite_name: str = "default"
    save_baseline: bool = False


class SmartRequest(BaseModel):
    url: str
    task: str = ""


@app.post("/api/run/prompt")
async def start_prompt(req: PromptRequest):
    run_id = str(uuid.uuid4())[:8]

    def run():
        _register(run_id)
        try:
            from agents.test_planner import generate_test_plan
            from agents.ui_analyzer import analyze_all_screenshots
            from runner.executor import run_tests
            from reporter.html_report import generate_html_report

            url = req.url.strip()
            task = req.task.strip()
            if url and not url.startswith("http"):
                url = "https://" + url

            if url and task:
                prompt = f"Test {url} - {task}"
            elif url:
                prompt = f"Test all main features of {url} including navigation, UI elements, and core functionality"
            else:
                prompt = task

            steps = generate_test_plan(prompt)
            results = run_tests(steps)
            results = analyze_all_screenshots(results)
            html_path = generate_html_report(prompt, results, url=url)

            _finish(run_id, {
                "html_report": os.path.basename(html_path),
                "total": len(results),
                "passed": sum(1 for r in results if r["status"] == "pass"),
                "failed": sum(1 for r in results if r["status"] == "fail"),
                "warnings": sum(1 for r in results if r["status"] == "warn"),
            }, None)
        except Exception as e:
            _finish(run_id, None, str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"run_id": run_id}


def _run_advanced(run_id: str, url: str, task: str, test_type: str):
    """Shared runner for functional, integration, and system test types."""
    _register(run_id)
    try:
        from agents.test_planner_advanced import generate_advanced_test_plan
        from agents.ui_analyzer import analyze_all_screenshots
        from runner.executor import run_tests
        from reporter.html_report import generate_html_report

        if url and not url.startswith("http"):
            url = "https://" + url

        if url and task:
            prompt = f"Test {url} — {task}"
        elif url:
            prompt = f"Test all features of {url}"
        else:
            prompt = task

        prefix_map = {
            "functional":  "Functional",
            "integration": "Integration",
            "system":      "System",
        }
        prefix = prefix_map.get(test_type, "Report")

        steps = generate_advanced_test_plan(prompt, test_type)
        results = run_tests(steps)
        results = analyze_all_screenshots(results)
        html_path = generate_html_report(prompt, results, url=url, prefix=prefix)

        _finish(run_id, {
            "html_report": os.path.basename(html_path),
            "total":    len(results),
            "passed":   sum(1 for r in results if r["status"] == "pass"),
            "failed":   sum(1 for r in results if r["status"] == "fail"),
            "warnings": sum(1 for r in results if r["status"] == "warn"),
        }, None)
    except Exception as e:
        _finish(run_id, None, str(e))


@app.post("/api/run/smart")
async def start_smart(req: SmartRequest):
    run_id = str(uuid.uuid4())[:8]

    def run():
        _register(run_id)
        try:
            from agents.smart_analyzer import scan_page, generate_smart_plan
            from agents.ui_analyzer import analyze_all_screenshots
            from runner.executor import run_tests
            from reporter.html_report import generate_html_report
            from regression.baseline_store import compare_with_baseline, save_baseline

            url = req.url.strip()
            if url and not url.startswith("http"):
                url = "https://" + url

            print(f"\n[Smart] Step 1/4 — Page scan: {url}")
            page_info = scan_page(url)

            print(f"[Smart] Step 2/4 — Test plan generate ho raha hai...")
            steps = generate_smart_plan(page_info, extra_task=req.task.strip())

            print(f"[Smart] Step 3/4 — {len(steps)} steps browser pe run ho rahe hain...")
            results = run_tests(steps)
            results = analyze_all_screenshots(results)

            comparison = compare_with_baseline(url, "smart-auto", results)
            if not comparison["has_baseline"]:
                print(f"[Smart] Pehla run — baseline save ho raha hai...")
                save_baseline(url, "smart-auto", results)
            else:
                rc = comparison["regression_count"]
                print(f"[Smart] Baseline comparison: {rc} regression(s) found")

            print(f"[Smart] Step 4/4 — Report generate ho rahi hai...")
            prompt_text = f"Smart Auto Test: {url}" + (f" — {req.task}" if req.task else "")
            html_path = generate_html_report(prompt_text, results, url=url, prefix="Smart")

            _finish(run_id, {
                "html_report":          os.path.basename(html_path),
                "total":                len(results),
                "passed":               sum(1 for r in results if r["status"] == "pass"),
                "failed":               sum(1 for r in results if r["status"] == "fail"),
                "warnings":             sum(1 for r in results if r["status"] == "warn"),
                "page_info_summary": {
                    "forms":       len(page_info.get("forms", [])),
                    "nav_links":   len(page_info.get("nav_links", [])),
                    "third_party": len(page_info.get("third_party", [])),
                    "api_calls":   len(page_info.get("api_calls", [])),
                },
                "baseline_comparison":  comparison,
            }, None)
        except Exception as e:
            _finish(run_id, None, str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"run_id": run_id}


@app.post("/api/run/functional")
async def start_functional(req: AdvancedTestRequest):
    run_id = str(uuid.uuid4())[:8]
    threading.Thread(
        target=_run_advanced,
        args=(run_id, req.url.strip(), req.task.strip(), "functional"),
        daemon=True,
    ).start()
    return {"run_id": run_id}


@app.post("/api/run/integration")
async def start_integration(req: AdvancedTestRequest):
    run_id = str(uuid.uuid4())[:8]
    threading.Thread(
        target=_run_advanced,
        args=(run_id, req.url.strip(), req.task.strip(), "integration"),
        daemon=True,
    ).start()
    return {"run_id": run_id}


@app.post("/api/run/system")
async def start_system(req: AdvancedTestRequest):
    run_id = str(uuid.uuid4())[:8]
    threading.Thread(
        target=_run_advanced,
        args=(run_id, req.url.strip(), req.task.strip(), "system"),
        daemon=True,
    ).start()
    return {"run_id": run_id}


@app.post("/api/run/regression")
async def start_regression(req: RegressionRequest):
    run_id = str(uuid.uuid4())[:8]

    def run():
        _register(run_id)
        try:
            from agents.test_planner_advanced import generate_advanced_test_plan
            from agents.ui_analyzer import analyze_all_screenshots
            from runner.executor import run_tests
            from reporter.html_report import generate_html_report
            from regression.baseline_store import compare_with_baseline, save_baseline

            url = req.url.strip()
            if not url.startswith("http"):
                url = "https://" + url
            suite = req.suite_name.strip() or "default"

            prompt = f"Regression test suite '{suite}' for {url}"
            steps = generate_advanced_test_plan(prompt, "regression")
            results = run_tests(steps)
            results = analyze_all_screenshots(results)

            comparison = compare_with_baseline(url, suite, results)

            if comparison["has_baseline"]:
                reg_count = comparison["regression_count"]
                imp_count = comparison["improvement_count"]
                print(f"\n[Regression] Baseline comparison: {reg_count} regression(s), {imp_count} improvement(s)")
                if comparison["regressions"]:
                    for r in comparison["regressions"]:
                        print(f"  REGRESSION: {r['test']} ({r['was']} → {r['now']})")
            else:
                print(f"\n[Regression] No baseline found for suite '{suite}'. Saving current results as baseline...")

            if not comparison["has_baseline"] or req.save_baseline:
                save_baseline(url, suite, results)

            html_path = generate_html_report(prompt, results, url=url, prefix="Regression")

            result_data = {
                "html_report": os.path.basename(html_path),
                "total":    len(results),
                "passed":   sum(1 for r in results if r["status"] == "pass"),
                "failed":   sum(1 for r in results if r["status"] == "fail"),
                "warnings": sum(1 for r in results if r["status"] == "warn"),
                "baseline_comparison": comparison,
            }
            _finish(run_id, result_data, None)
        except Exception as e:
            _finish(run_id, None, str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"run_id": run_id}


@app.post("/api/run/crawl")
async def start_crawl(req: CrawlRequest):
    run_id = str(uuid.uuid4())[:8]

    def run():
        _register(run_id)
        try:
            from runner.crawler import crawl_and_test
            from agents.ui_analyzer import analyze_screenshot
            from reporter.crawl_report import generate_crawl_report
            import runner.crawler as crawler_mod

            url = req.url.strip()
            if not url.startswith("http"):
                url = "https://" + url

            crawler_mod.MAX_PAGES = min(req.max_pages, 30)
            crawl_data = crawl_and_test(url)

            for r in crawl_data["page_results"]:
                if r.get("screenshot"):
                    r["ui_analysis"] = analyze_screenshot(r["screenshot"], f"Page: {r['title'] or r['url']}")

            html_path = generate_crawl_report(crawl_data)
            summary = crawl_data["summary"]

            _finish(run_id, {
                "html_report": os.path.basename(html_path),
                **summary,
            }, None)
        except Exception as e:
            _finish(run_id, None, str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"run_id": run_id}


@app.get("/api/stream/{run_id}")
async def stream(run_id: str):
    if run_id not in active_runs:
        return {"error": "Run not found"}

    async def generator():
        run = active_runs[run_id]
        q = run["queue"]
        while True:
            try:
                item = q.get_nowait()
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") == "done":
                    final = {
                        "type": "result",
                        "result": run.get("result"),
                        "error": run.get("error"),
                    }
                    yield f"data: {json.dumps(final)}\n\n"
                    break
            except Empty:
                await asyncio.sleep(0.05)
                yield ": ping\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/reports")
async def list_reports():
    files = []
    if os.path.exists(REPORTS_DIR):
        for f in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if f.endswith(".html"):
                files.append(f)
    return {"reports": files[:30]}


WEB_DIR = os.path.join(PYTHON_DIR, "web")
if os.path.exists(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None, log_level="info")
