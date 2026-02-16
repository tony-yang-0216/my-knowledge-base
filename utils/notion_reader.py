"""Notion read-only operations."""

import os
from clients import get_notion_client
from constants import NOTION_API_BATCH_SIZE


def _paginate_blocks(block_id):
    """分頁取得所有子 blocks"""
    notion = get_notion_client()
    results = []
    has_more = True
    start_cursor = None
    while has_more:
        response = notion.blocks.children.list(
            block_id=block_id,
            start_cursor=start_cursor,
            page_size=NOTION_API_BATCH_SIZE
        )
        results.extend(response.get("results", []))
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    return results


def get_draft_pages():
    notion = get_notion_client()
    database_id = os.environ.get("NOTION_DATABASE_ID")
    results = []
    start_cursor = None
    while True:
        response = notion.databases.query(
            database_id=database_id,
            # 加上 page_size=100 減少 HTTP 請求次數
            page_size=NOTION_API_BATCH_SIZE,
            filter={"property": "Status", "status": {"equals": "Draft"}},
            start_cursor=start_cursor
        )
        batch = response.get("results", [])
        results.extend(batch)

        # 如果沒有下一頁，直接 break
        if not response.get("has_more"):
            break

        start_cursor = response.get("next_cursor")
    return results


def get_page_content(page_id):
    blocks = _paginate_blocks(page_id)
    text = ""
    for block in blocks:
        btype = block["type"]

        # 有 rich_text 的 block 類型（paragraph, headings, lists, quotes, callout, toggle）
        if btype in ("paragraph", "heading_1", "heading_2", "heading_3",
                      "bulleted_list_item", "numbered_list_item",
                      "quote", "callout", "toggle"):
            rich_text = block[btype].get("rich_text", [])
            line = "".join([t["plain_text"] for t in rich_text])
            if btype.startswith("heading"):
                level = btype[-1]  # "1", "2", or "3"
                text += "#" * int(level) + " " + line + "\n"
            elif btype == "bulleted_list_item":
                text += "- " + line + "\n"
            elif btype == "numbered_list_item":
                text += "1. " + line + "\n"
            elif btype == "quote":
                text += "> " + line + "\n"
            else:
                text += line + "\n"

        # Code block
        elif btype == "code":
            rich_text = block["code"].get("rich_text", [])
            code = "".join([t["plain_text"] for t in rich_text])
            lang = block["code"].get("language", "")
            text += f"```{lang}\n{code}\n```\n"

        # 圖片
        elif btype == "image":
            image_data = block["image"]
            if image_data["type"] == "file":
                img_url = image_data["file"]["url"]
            elif image_data["type"] == "external":
                img_url = image_data["external"]["url"]
            else:
                img_url = ""
            caption = "".join([t["plain_text"] for t in image_data.get("caption", [])])
            text += f"![{caption}]({img_url})\n"

        # 分隔線
        elif btype == "divider":
            text += "---\n"

        # To-do
        elif btype == "to_do":
            rich_text = block["to_do"].get("rich_text", [])
            line = "".join([t["plain_text"] for t in rich_text])
            checked = "x" if block["to_do"].get("checked") else " "
            text += f"- [{checked}] {line}\n"

    return text
