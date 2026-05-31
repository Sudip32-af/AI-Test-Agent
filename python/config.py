import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY nahi mila! .env file mein set karo.")

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
REPORT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "reports", "output")

CLAUDE_MODEL = "claude-sonnet-4-6"
BROWSER_HEADLESS = False
BROWSER_TIMEOUT = 30000
