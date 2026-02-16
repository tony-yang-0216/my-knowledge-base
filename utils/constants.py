"""Centralized magic numbers and configuration values."""

from datetime import timezone, timedelta

# Notion API limits
NOTION_RICH_TEXT_LIMIT = 2000
NOTION_API_BATCH_SIZE = 100

# Fallback / chunking
FALLBACK_CHUNK_SIZE = 1900

# Throttling
PAGE_DELAY_SECONDS = 5

# Notion
NOTION_API_VERSION = "2022-06-28"

# File paths
NOTES_DIR = "notes"
DRAFTS_DIR = "drafts"

# Timezone
TW_TIMEZONE = timezone(timedelta(hours=8))
