import os
import json
import hashlib
from datetime import datetime

BASELINE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "baselines")
os.makedirs(BASELINE_DIR, exist_ok=True)


def _key(url: str, suite: str) -> str:
    raw = f"{url.rstrip('/')}::{suite.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def get_baseline(url: str, suite: str) -> dict | None:
    path = os.path.join(BASELINE_DIR, f"{_key(url, suite)}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_baseline(url: str, suite: str, results: list[dict]) -> str:
    path = os.path.join(BASELINE_DIR, f"{_key(url, suite)}.json")
    data = {
        "url": url,
        "suite": suite,
        "saved_at": datetime.now().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r["status"] == "pass"),
        "failed": sum(1 for r in results if r["status"] == "fail"),
        "steps": [
            {
                "description": r.get("description", ""),
                "action": r.get("action", ""),
                "status": r.get("status", ""),
            }
            for r in results
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[Regression] Baseline saved: {path}")
    return path


def compare_with_baseline(url: str, suite: str, current: list[dict]) -> dict:
    baseline = get_baseline(url, suite)
    if not baseline:
        return {"has_baseline": False}

    base_map = {s["description"]: s["status"] for s in baseline.get("steps", [])}

    regressions = []
    improvements = []
    new_tests = []

    for r in current:
        desc = r.get("description", "")
        cur_status = r.get("status", "")
        if desc not in base_map:
            new_tests.append(desc)
            continue
        base_status = base_map[desc]
        if base_status == "pass" and cur_status in ("fail", "warn"):
            regressions.append({"test": desc, "was": base_status, "now": cur_status})
        elif base_status in ("fail", "warn") and cur_status == "pass":
            improvements.append({"test": desc, "was": base_status, "now": cur_status})

    return {
        "has_baseline": True,
        "baseline_url": baseline.get("url", ""),
        "baseline_suite": baseline.get("suite", ""),
        "baseline_date": baseline.get("saved_at", ""),
        "baseline_passed": baseline.get("passed", 0),
        "baseline_total": baseline.get("total", 0),
        "regressions": regressions,
        "improvements": improvements,
        "new_tests": new_tests,
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
    }
