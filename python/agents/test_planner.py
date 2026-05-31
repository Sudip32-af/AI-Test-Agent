import re
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a senior QA engineer. Generate a thorough test plan as a JSON array.

AVAILABLE ACTIONS (use exactly these action names):
| action               | selector       | value                        | purpose                              |
|----------------------|----------------|------------------------------|--------------------------------------|
| navigate             | null           | "https://..."                | Open a URL                           |
| screenshot           | null           | "label_name"                 | Capture current state                |
| scroll               | null           | null                         | Scroll down 400px                    |
| click                | CSS selector   | null                         | Click an element                     |
| hover                | CSS selector   | null                         | Hover to check hover effect          |
| type                 | CSS selector   | "text to type"               | Type into an input field             |
| assert_text          | null           | "expected text"              | Assert text exists on page           |
| assert_visible       | CSS selector   | null                         | Assert element is visible            |
| assert_url           | null           | "expected_url_fragment"      | Assert current URL contains value    |
| check_all_links      | null           | null                         | Find & test ALL links on page        |
| check_text_structure | null           | null                         | Check H1/H2/H3 hierarchy & structure |
| fill_form_negative   | form CSS       | "empty"                      | Clear form & submit to trigger errors|
| fill_form_positive   | form CSS       | null                         | Fill form with valid data & submit   |
| assert_error_message | null           | null                         | Verify error messages appeared       |

MANDATORY RULES — always follow these:
1. ALWAYS start with navigate + screenshot
2. ALWAYS run check_text_structure to verify heading hierarchy (H1 must exist, no duplicate H1s)
3. ALWAYS run check_all_links to find broken links
4. ALWAYS hover over every major button (CTA, submit, nav links) to verify hover effects
5. ALWAYS check visibility of key elements: logo, nav, main heading, footer
6. IF a form exists on the page → MUST do BOTH:
   a. fill_form_negative → assert_error_message → screenshot (capture validation errors)
   b. fill_form_positive → screenshot (capture success state)
7. Max 15 steps total
8. Return ONLY the JSON array — no markdown, no extra text

RETURN FORMAT (strict JSON array):
[
  {"action":"navigate",             "description":"Open website",              "selector":null,     "value":"https://example.com","wait_after":2000},
  {"action":"screenshot",           "description":"Capture homepage",          "selector":null,     "value":"homepage",           "wait_after":500},
  {"action":"check_text_structure", "description":"Verify heading hierarchy",  "selector":null,     "value":null,                 "wait_after":500},
  {"action":"assert_visible",       "description":"Check logo is visible",     "selector":"img[alt*='logo'], .logo, #logo", "value":null, "wait_after":500},
  {"action":"hover",                "description":"Check CTA button hover",    "selector":"button, .btn, a.button",         "value":null, "wait_after":800},
  {"action":"check_all_links",      "description":"Test all page links",       "selector":null,     "value":null,                 "wait_after":500},
  {"action":"scroll",               "description":"Scroll to see more content","selector":null,     "value":null,                 "wait_after":800},
  {"action":"screenshot",           "description":"Capture scrolled view",     "selector":null,     "value":"scrolled",           "wait_after":500}
]"""


def generate_test_plan(user_prompt: str) -> list[dict]:
    print(f"\n[AI] Test plan generate ho raha hai...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate a comprehensive test plan for: {user_prompt}\n\n"
                    "Remember:\n"
                    "- Always check_text_structure and check_all_links\n"
                    "- Hover over every button/CTA\n"
                    "- If the page has a form: negative test first (empty submit), then positive test (valid data)\n"
                    "- Assert error messages appear after negative form test\n"
                    "- Check visibility of logo, navigation, headings, footer"
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

    try:
        steps = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"\n[Debug] JSON parse failed: {e}")
        print(f"[Debug] Raw response:\n{raw[:500]}")
        raise

    print(f"[AI] {len(steps)} test steps generate hue")
    return steps
