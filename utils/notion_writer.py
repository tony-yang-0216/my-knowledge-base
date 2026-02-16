"""Notion write/update operations."""

from datetime import datetime
from clients import get_notion_client
from constants import NOTION_API_BATCH_SIZE, TW_TIMEZONE


def create_page_in_database(database_id, title, category, tags, children=None):
    """在 Notion 資料庫中建立新頁面，回傳 page_id"""
    notion = get_notion_client()
    now = datetime.now(TW_TIMEZONE).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    properties = {
        "Name": {"title": [{"text": {"content": title}}]},
        "Status": {"status": {"name": "Draft"}},
        "Category": {"select": {"name": category}},
        "Tags": {"multi_select": [{"name": tag} for tag in tags]},
        "Updated Time": {"date": {"start": now}},
    }

    # Notion API 限制：建立頁面時最多帶 100 個 children blocks
    first_batch = children[:NOTION_API_BATCH_SIZE] if children else None
    remaining = children[NOTION_API_BATCH_SIZE:] if children else []

    create_kwargs = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    if first_batch:
        create_kwargs["children"] = first_batch

    response = notion.pages.create(**create_kwargs)
    page_id = response["id"]
    print(f"📝 [Notion] 新頁面已建立: {page_id}")

    # 超過 100 blocks 用 append_blocks_batched 補上
    if remaining:
        append_blocks_batched(page_id, remaining)

    return page_id


def update_page_status(page_id, status):
    """僅更新 Notion 頁面的 Status 屬性"""
    notion = get_notion_client()
    notion.pages.update(
        page_id=page_id,
        properties={"Status": {"status": {"name": status}}},
    )
    print(f"✨ [Notion] 頁面狀態已更新為 {status}: {page_id}")


def append_blocks_batched(page_id, blocks):
    notion = get_notion_client()
    for start in range(0, len(blocks), NOTION_API_BATCH_SIZE):
        batch = blocks[start:start + NOTION_API_BATCH_SIZE]
        notion.blocks.children.append(block_id=page_id, children=batch)
