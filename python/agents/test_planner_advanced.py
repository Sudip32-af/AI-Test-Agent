import re
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_ACTIONS_TABLE = """
AVAILABLE ACTIONS:
| action               | selector       | value                        | purpose                                         |
|----------------------|----------------|------------------------------|-------------------------------------------------|
| navigate             | null           | "https://..."                | Open a URL                                      |
| screenshot           | null           | "label_name"                 | Capture current state                           |
| scroll               | null           | null                         | Scroll down 400px                               |
| click                | CSS selector   | null                         | Click an element                                |
| hover                | CSS selector   | null                         | Hover over an element                           |
| type                 | CSS selector   | "text to type"               | Type into an input field                        |
| assert_text          | null           | "expected text"              | Assert text exists on page                      |
| assert_visible       | CSS selector   | null                         | Assert element is visible                       |
| assert_not_visible   | CSS selector   | null                         | Assert element is NOT visible                   |
| assert_url           | null           | "expected_url_fragment"      | Assert current URL contains value               |
| assert_count         | CSS selector   | "N"                          | Assert exactly N elements match selector        |
| check_all_links      | null           | null                         | Find & test ALL links on page                   |
| check_text_structure | null           | null                         | Check H1/H2/H3 heading hierarchy                |
| check_console_errors | null           | null                         | Check for JavaScript console errors             |
| fill_form_negative   | form CSS       | "empty"                      | Clear form & submit to trigger validation       |
| fill_form_positive   | form CSS       | null                         | Fill form with valid data & submit              |
| assert_error_message | null           | null                         | Verify error messages appeared                  |
| api_check            | null           | "https://api-endpoint-url"   | Check API endpoint returns 2xx status           |
| performance_check    | null           | null                         | Measure page load speed & core web vitals       |
| wait                 | null           | "milliseconds"               | Wait for specified time                         |

RETURN FORMAT: Strict JSON array only — no markdown, no explanation.
[{"action":"navigate","description":"...","selector":null,"value":"https://...","wait_after":2000}, ...]
"""

FUNCTIONAL_SYSTEM = _ACTIONS_TABLE + """
You are a senior QA engineer. Generate a FUNCTIONAL test plan that tests specific business features and logic.

WHAT TO TEST:
1. Does each feature work as intended? (buttons, links, modals, dropdowns)
2. Input validation — empty, boundary values, invalid formats
3. State changes — verify UI updates after actions (button disabled, counter changes, message appears)
4. Form flows — negative test (empty submit → error messages) AND positive test (valid data → success)
5. Error handling — what happens when wrong data is entered
6. Feature-specific assertions — assert the right content appears after interactions
7. Console errors — check no JS errors during interactions

MANDATORY:
- Start with navigate + screenshot
- For any form: fill_form_negative → assert_error_message → fill_form_positive → screenshot
- Use assert_not_visible to check elements hidden by default
- Use check_console_errors after major interactions
- Use assert_count to verify lists, items count
- Max 20 steps
"""

INTEGRATION_SYSTEM = _ACTIONS_TABLE + """
You are a senior QA engineer. Generate an INTEGRATION test plan that tests how components and services work together.

WHAT TO TEST:
1. API endpoints — do backend calls return correct data? (use api_check)
2. Third-party service loading — analytics, maps, payment widgets, social login buttons
3. Data flow — does submitting a form actually update the UI with backend data?
4. Network integration — do page components load data from APIs without errors?
5. Cross-page data consistency — data set on page A appears correctly on page B
6. Session/cookie behavior — auth state persists across navigation
7. Performance of integrations — third-party scripts don't slow page below threshold
8. Console errors — third-party integration errors

MANDATORY:
- Start with navigate + screenshot
- Use api_check for any /api/ URLs visible in the page or network
- Use check_console_errors to catch integration errors
- Use performance_check to verify integrations don't degrade performance
- Navigate to multiple pages and verify data consistency
- Max 20 steps
"""

SYSTEM_E2E_SYSTEM = _ACTIONS_TABLE + """
You are a senior QA engineer. Generate a SYSTEM (end-to-end) test plan simulating complete real user workflows.

WHAT TO TEST:
1. Happy path — complete user journey from start to final goal (e.g., land → search → view → contact)
2. User flow correctness — navigation moves user to expected pages
3. Data persistence — info entered on step 1 is still there on step 3
4. Multi-feature interaction — feature A + feature B + feature C all working together
5. Error recovery — user makes mistake mid-flow, can they correct and continue?
6. Final state validation — after completing the workflow, assert the outcome is correct
7. Performance across the full journey — page load at each major step

MANDATORY:
- Start with navigate + screenshot
- Simulate a COMPLETE user journey with multiple steps (visit → interact → achieve goal)
- Take screenshot at each major workflow milestone
- After the happy path, test one error path (wrong input, go back, correct, complete)
- Final step: assert_text or assert_url to confirm successful completion
- Max 25 steps (E2E tests cover more ground)
"""

REGRESSION_SYSTEM = _ACTIONS_TABLE + """
You are a senior QA engineer. Generate a comprehensive REGRESSION test plan to catch regressions.

PURPOSE: This plan will be run repeatedly on every release to ensure nothing broke.

WHAT TO TEST (must cover ALL of these):
1. Core page structure — check_text_structure, assert_visible for logo/nav/footer/main heading
2. All links — check_all_links
3. Every major feature on the page — test each interactive element
4. Every form — fill_form_negative + assert_error_message + fill_form_positive
5. Navigation — click every nav link, assert_url to verify correct page
6. Performance baseline — performance_check (will flag regressions if page gets slower)
7. Console errors — check_console_errors to catch newly introduced JS bugs
8. Critical text content — assert_text for key copy that must always appear
9. Element counts — assert_count for critical lists/items that should have fixed counts

MANDATORY:
- Start with navigate + screenshot
- MUST include: check_text_structure, check_all_links, check_console_errors, performance_check
- MUST test all forms found (both negative and positive paths)
- MUST assert_visible for: logo, main navigation, primary CTA, footer
- Max 25 steps — be thorough, this is the safety net
"""

_SYSTEM_PROMPTS = {
    "functional":  FUNCTIONAL_SYSTEM,
    "integration": INTEGRATION_SYSTEM,
    "system":      SYSTEM_E2E_SYSTEM,
    "regression":  REGRESSION_SYSTEM,
}

_TYPE_LABELS = {
    "functional":  "Functional",
    "integration": "Integration",
    "system":      "System E2E",
    "regression":  "Regression",
}


def generate_advanced_test_plan(user_prompt: str, test_type: str) -> list[dict]:
    label = _TYPE_LABELS.get(test_type, test_type.capitalize())
    system = _SYSTEM_PROMPTS.get(test_type, FUNCTIONAL_SYSTEM)
    print(f"\n[AI] {label} test plan generate ho raha hai...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system=system,
        messages=[
            {
                "role": "user",
                "content": f"Generate a {label} test plan for: {user_prompt}",
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
        print(f"[Debug] Raw:\n{raw[:500]}")
        raise

    print(f"[AI] {len(steps)} {label} test steps generate hue")
    return steps
