"""Lazy API client initialization.

Uses lazy singletons so importing conversion-only functions
(e.g. markdown_to_notion_blocks in test tools) doesn't require API keys.
"""

import os
from dotenv import load_dotenv
from constants import NOTION_API_VERSION

# Module-level singletons (populated on first call)
_notion_client = None
_gemini_client = None


def _ensure_env():
    """Load .env once (idempotent)."""
    load_dotenv()


def get_notion_client():
    """Return a lazily-initialized Notion client singleton."""
    global _notion_client
    if _notion_client is None:
        _ensure_env()
        from notion_client import Client
        token = os.environ.get("NOTION_TOKEN")
        _notion_client = Client(auth=token, notion_version=NOTION_API_VERSION)
    return _notion_client


def get_gemini_client():
    """Return a lazily-initialized Gemini client singleton."""
    global _gemini_client
    if _gemini_client is None:
        _ensure_env()
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client
