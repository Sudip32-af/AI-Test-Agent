import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(__file__))

from agents.test_planner import generate_test_plan
from agents.ui_analyzer import analyze_all_screenshots
from runner.executor import run_tests
from runner.crawler import crawl_and_test
from reporter.html_report import generate_html_report
from reporter.pdf_report import generate_pdf_report
from reporter.crawl_report import generate_crawl_report


def mode_crawl():
    url = input("Website URL do (crawl karega saari pages):\n> ").strip()
    if not url:
        print("URL nahi diya. Exit.")
        return
    if not url.startswith("http"):
        url = "https://" + url

    max_p = input("Max kitni pages test karni hain? (default 20, max 30):\n> ").strip()
    if max_p.isdigit():
        from runner import crawler
        crawler.MAX_PAGES = min(int(max_p), 30)

    print(f"\n[Crawl Mode] URL: {url}")
    print("=" * 60)

    crawl_data = crawl_and_test(url)

    print("\n[AI] Screenshots analyze ho rahi hain...")
    for r in crawl_data["page_results"]:
        if r.get("screenshot"):
            from agents.ui_analyzer import analyze_screenshot
            print(f"  Analyzing: {r['url'][:60]}...", end=" ")
            r["ui_analysis"] = analyze_screenshot(r["screenshot"], f"Page: {r['title'] or r['url']}")
            score = r["ui_analysis"].get("ui_score", "N/A")
            issues = len(r["ui_analysis"].get("issues", []))
            print(f"Score: {score}, Issues: {issues}")

    print("\n[Report] Generating crawl report...")
    html_path = generate_crawl_report(crawl_data)
    pdf_path = generate_pdf_report(html_path)

    print("\n" + "=" * 60)
    print("CRAWL COMPLETE!")
    print(f"Pages tested : {crawl_data['summary']['total']}")
    print(f"Passed       : {crawl_data['summary']['passed']}")
    print(f"Failed       : {crawl_data['summary']['failed']}")
    print(f"Warnings     : {crawl_data['summary']['warnings']}")
    print(f"HTML Report  : {html_path}")
    if pdf_path:
        print(f"PDF  Report  : {pdf_path}")
    print("=" * 60)

    open_now = input("\nReport browser mein kholein? (y/n): ").strip().lower()
    if open_now == "y":
        webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")


def mode_prompt():
    url_input  = input("Website ka URL do (ya Enter skip karo):\n> ").strip()
    task_input = input("Kya test karna hai?\n> ").strip()

    if not url_input and not task_input:
        print("Kuch toh do! Exit.")
        return

    if url_input and not url_input.startswith("http"):
        url_input = "https://" + url_input

    if url_input and task_input:
        prompt = f"Test {url_input} - {task_input}"
    elif url_input:
        prompt = f"Test all main features of {url_input} including navigation, UI elements, and core functionality"
    else:
        prompt = task_input

    print(f"\n[Prompt Mode] {prompt}")
    print("=" * 60)

    print("\n[1/4] Test plan generate ho raha hai...")
    try:
        steps = generate_test_plan(prompt)
    except Exception as e:
        print(f"Test plan error: {e}")
        return

    print(f"\n[2/4] {len(steps)} steps browser pe chal rahe hain...")
    print("-" * 60)
    try:
        results = run_tests(steps)
    except Exception as e:
        print(f"Test run error: {e}")
        return

    passed  = sum(1 for r in results if r["status"] == "pass")
    failed  = sum(1 for r in results if r["status"] == "fail")
    print(f"\nResults: {passed} passed, {failed} failed")

    print("\n[3/4] UI analysis chal rahi hai...")
    try:
        results = analyze_all_screenshots(results)
    except Exception as e:
        print(f"UI analysis skip: {e}")

    print("\n[4/4] Report generate ho rahi hai...")
    try:
        html_path = generate_html_report(prompt, results, url=url_input)
        pdf_path  = generate_pdf_report(html_path)
    except Exception as e:
        print(f"Report error: {e}")
        return

    print("\n" + "=" * 60)
    print("TEST COMPLETE!")
    print(f"HTML Report: {html_path}")
    if pdf_path:
        print(f"PDF  Report: {pdf_path}")
    print("=" * 60)

    open_now = input("\nReport browser mein kholein? (y/n): ").strip().lower()
    if open_now == "y":
        webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")


def main():
    print("=" * 60)
    print("   AI TEST AGENT — Claude + Playwright")
    print("=" * 60)
    print()
    print("  1. Prompt Mode  — Specific test cases likho")
    print("  2. Crawl Mode   — Poori website ki saari pages test karo")
    print()

    choice = input("Mode chuno (1 ya 2):\n> ").strip()

    if choice == "2":
        mode_crawl()
    else:
        mode_prompt()


if __name__ == "__main__":
    main()
