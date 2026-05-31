import base64
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

ANALYSIS_PROMPT = """You are a senior UI/UX expert and QA engineer. Analyze this screenshot carefully and report:

1. **Text Structure**: Is there a clear H1? Are headings well-structured? Is text readable?
2. **Button & Interactive Elements**: Do buttons look clickable? Is there visual feedback (hover states visible)?
3. **Layout Issues**: Broken layouts, overlapping elements, cut-off text, misaligned elements
4. **Accessibility**: Poor contrast, very small text, missing focus indicators, small touch targets
5. **Form Issues**: If a form is visible — are fields labeled? Are error messages clearly styled?
6. **Content Issues**: Missing images (broken img), placeholder text left in, 404 indicators visible
7. **Design Consistency**: Inconsistent fonts/colors, unprofessional appearance
8. **Overall UI Score**: rate 1-10 (10 = perfect)

Respond ONLY in this JSON format:
{
  "ui_score": 8,
  "issues": [
    {"type": "text_structure", "severity": "high",   "description": "No H1 heading found on page"},
    {"type": "button",         "severity": "medium", "description": "Submit button has no visible hover state"},
    {"type": "layout",         "severity": "high",   "description": "Navigation menu overflows on right side"},
    {"type": "accessibility",  "severity": "medium", "description": "Low contrast: light grey text on white background"},
    {"type": "form",           "severity": "high",   "description": "Error messages not clearly highlighted"},
    {"type": "content",        "severity": "low",    "description": "Footer placeholder text still visible"}
  ],
  "summary": "One-sentence summary of overall page quality",
  "recommendations": ["Add H1 heading", "Add :hover CSS to submit button", "Increase text contrast to 4.5:1"]
}

Issue types: text_structure, button, layout, accessibility, form, content, design
Severity: high (breaks UX), medium (noticeable but usable), low (minor polish)
If no issues found, return empty issues array with score 9-10."""


def analyze_screenshot(screenshot_path: str, step_description: str) -> dict:
    try:
        with open(screenshot_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Test step was: '{step_description}'\n\n{ANALYSIS_PROMPT}"
                        }
                    ],
                }
            ],
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        import json
        return json.loads(raw)

    except Exception as e:
        return {
            "ui_score": None,
            "issues": [],
            "summary": f"Analysis error: {str(e)[:100]}",
            "recommendations": []
        }


def analyze_all_screenshots(test_results: list[dict]) -> list[dict]:
    print("\n[AI] UI analysis chal rahi hai screenshots ke liye...")
    analyzed = []

    screenshots = [r for r in test_results if r.get("screenshot") and r["status"] != "skip"]
    total = len(screenshots)

    for i, result in enumerate(test_results):
        if result.get("screenshot"):
            print(f"  Analyzing {i+1}/{total}: {result['description'][:50]}...", end=" ")
            analysis = analyze_screenshot(result["screenshot"], result["description"])
            result["ui_analysis"] = analysis
            issue_count = len(analysis.get("issues", []))
            print(f"Score: {analysis.get('ui_score', 'N/A')}, Issues: {issue_count}")
        else:
            result["ui_analysis"] = None
        analyzed.append(result)

    return analyzed
