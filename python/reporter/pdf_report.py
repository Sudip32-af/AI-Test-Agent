import os


def generate_pdf_report(html_path: str) -> str:
    # Try WeasyPrint first (works on Linux/Mac)
    try:
        import weasyprint
        pdf_path = html_path.replace(".html", ".pdf")
        weasyprint.HTML(filename=html_path).write_pdf(pdf_path)
        print(f"[Report] PDF saved: {pdf_path}")
        return pdf_path
    except Exception:
        pass

    # Fallback: Playwright Chromium (works on Windows too)
    try:
        from playwright.sync_api import sync_playwright
        pdf_path = html_path.replace(".html", ".pdf")
        abs_path = os.path.abspath(html_path).replace("\\", "/")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file:///{abs_path}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            )
            browser.close()

        print(f"[Report] PDF saved (Playwright): {pdf_path}")
        return pdf_path

    except Exception as e:
        print(f"[Report] PDF skip: {e}")
        return None
