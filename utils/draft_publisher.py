"""Publish markdown drafts from drafts/ to Notion and notes/."""

import glob
import os
import shutil
import sys
import time

import yaml

from categories import CATEGORIES
from clients import get_notion_client  # noqa: F401 – ensures env is loaded
from constants import (
    DRAFTS_DIR,
    NOTES_DIR,
    PAGE_DELAY_SECONDS,
    TW_TIMEZONE,
)
from datetime import datetime
from md_to_notion import markdown_to_notion_blocks, _sanitize_mermaid_in_markdown
from notion_writer import create_page_in_database, update_page_status

FALLBACK_CATEGORY = "99-Inbox"
STATUS_UPDATE_MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(file_path):
    """讀取 markdown 檔案，分離 YAML frontmatter 和正文。

    回傳 (metadata dict, body str)。
    驗證必要欄位：title, category, tags。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        print(f"❌ [Parse] 缺少 YAML frontmatter: {file_path}")
        sys.exit(1)

    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"❌ [Parse] YAML frontmatter 格式錯誤: {file_path}")
        sys.exit(1)

    raw_yaml = parts[1]
    body = parts[2].lstrip("\n")

    try:
        metadata = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as e:
        print(f"❌ [Parse] YAML 解析失敗: {file_path}\n{e}")
        sys.exit(1)

    if not metadata or not isinstance(metadata, dict):
        print(f"❌ [Parse] YAML 內容無效: {file_path}")
        sys.exit(1)

    # 驗證必要欄位
    for field in ("title", "category", "tags"):
        if field not in metadata:
            print(f"❌ [Parse] 缺少必要欄位 '{field}': {file_path}")
            sys.exit(1)

    # tags 若為 string 自動轉 list
    if isinstance(metadata["tags"], str):
        metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]

    # 驗證 category
    if metadata["category"] not in CATEGORIES:
        print(f"⚠️ [Parse] 未知分類 '{metadata['category']}'，使用 {FALLBACK_CATEGORY}")
        metadata["category"] = FALLBACK_CATEGORY

    return metadata, body


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def move_draft_to_notes(source_path, body, category, title):
    """將 draft 內容寫入 notes/{category}/{title}.md 並刪除來源檔案。

    回傳目標檔案路徑。
    """
    # 確保分類資料夾存在
    category_dir = f"{NOTES_DIR}/{category}"
    os.makedirs(category_dir, exist_ok=True)

    # 安全標題
    safe_title = title.replace("/", "-").replace("\\", "-")
    dest_path = f"{category_dir}/{safe_title}.md"

    # 在 H1 標題後插入 Updated Time 註記
    now = datetime.now(TW_TIMEZONE).strftime("%Y-%m-%d %H:%M")
    content_lines = body.split("\n")
    if content_lines and content_lines[0].startswith("# "):
        content_lines.insert(1, f"\n> Updated: {now}\n")
    md_content = "\n".join(content_lines)

    # Sanitize Mermaid 區塊
    md_content = _sanitize_mermaid_in_markdown(md_content)

    # 寫入目標檔案
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 刪除來源檔案
    os.remove(source_path)

    print(f"💾 [File] {source_path} → {dest_path}")
    return dest_path


# ---------------------------------------------------------------------------
# Single draft pipeline
# ---------------------------------------------------------------------------

def process_single_draft(file_path):
    """處理單一 draft 檔案的完整 pipeline。"""
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        print("❌ [Config] 缺少 NOTION_DATABASE_ID 環境變數")
        sys.exit(1)

    # 1. Parse frontmatter
    metadata, body = parse_frontmatter(file_path)
    title = metadata["title"]
    category = metadata["category"]
    tags = metadata["tags"]
    print(f"📄 [Draft] 處理: {title} ({category})")

    # 2. Markdown → Notion blocks
    content_blocks = markdown_to_notion_blocks(body, for_notion=True)

    # 插入 TOC block 到頁面最頂端
    toc_block = {
        "object": "block",
        "type": "table_of_contents",
        "table_of_contents": {"color": "default"},
    }
    content_blocks.insert(0, toc_block)

    # 3. 建立 Notion page（Status: Draft）
    page_id = create_page_in_database(
        database_id=database_id,
        title=title,
        category=category,
        tags=tags,
        children=content_blocks,
    )

    # 4. 搬移檔案到 notes/
    dest_path = None
    try:
        dest_path = move_draft_to_notes(file_path, body, category, title)
    except Exception as e:
        print(f"⚠️ [File] 搬移失敗，Notion page 維持 Draft 狀態: {e}")
        return

    # 5. 更新 Notion 狀態為 Processed
    for attempt in range(1, STATUS_UPDATE_MAX_RETRIES + 1):
        try:
            update_page_status(page_id, "Processed")
            break
        except Exception as e:
            print(f"⚠️ [Notion] 狀態更新失敗 (第 {attempt} 次): {e}")
            if attempt == STATUS_UPDATE_MAX_RETRIES:
                # Rollback: 將檔案從 notes/ 搬回 drafts/
                print("🔄 [Rollback] 將檔案搬回 drafts/，下次重新處理")
                _rollback_file(dest_path, file_path, metadata, body)
                return

    print(f"✅ [Done] {title}")


def _rollback_file(dest_path, original_path, metadata, body):
    """將檔案從 notes/ 搬回 drafts/，重建原始 frontmatter"""
    try:
        # 重建原始 draft 內容（frontmatter + body）
        frontmatter = yaml.dump(metadata, allow_unicode=True, default_flow_style=False)
        original_content = f"---\n{frontmatter}---\n\n{body}"
        with open(original_path, "w", encoding="utf-8") as f:
            f.write(original_content)
        # 刪除 notes/ 中的檔案
        if os.path.exists(dest_path):
            os.remove(dest_path)
        print(f"🔄 [Rollback] 已還原: {original_path}")
    except Exception as e:
        print(f"🚨 [Rollback] 還原失敗: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    drafts = sorted(glob.glob(f"{DRAFTS_DIR}/*.md"))
    if not drafts:
        print("📭 [Draft Publisher] 沒有待處理的 draft 檔案")
        return

    print(f"📬 [Draft Publisher] 找到 {len(drafts)} 個 draft 檔案")

    for i, file_path in enumerate(drafts):
        process_single_draft(file_path)

        # 節流（最後一個不需要 delay）
        if i < len(drafts) - 1:
            time.sleep(PAGE_DELAY_SECONDS)


if __name__ == "__main__":
    main()
