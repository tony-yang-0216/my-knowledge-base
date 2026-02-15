import os
import re
import time
import json
from datetime import datetime, timezone, timedelta
from google import genai
from notion_client import Client
from notion_client.helpers import collect_paginated_api
from notion_client.errors import APIResponseError
from md2notionpage.core import parse_markdown_to_notion_blocks
from categories import get_categories_prompt

# 1. 環境變數設定 (從 GitHub Secrets 讀取)
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
notion = Client(auth=NOTION_TOKEN)

NOTES_DIR = "notes"

def get_draft_pages():
    return collect_paginated_api(
        notion.databases.query,
        database_id=DATABASE_ID,
        filter={"property": "Status", "status": {"equals": "Draft"}}
    )

def get_page_content(page_id):
    blocks = collect_paginated_api(
        notion.blocks.children.list, block_id=page_id
    )
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

def organize_with_ai(raw_text):
    categories_text = get_categories_prompt()
    prompt = f"""
    你是一位資深技術架構師與知識管理專家。請針對提供的原始對話進行「深度知識內化」，並嚴格遵守以下任務與格式：

    ### 任務說明：
    1.  **簡潔標題 (title)**：提取核心概念，建立一個一眼就能明瞭的簡潔專業技術標題（例如：從「聊聊 JWT」優化為「JWT 身分驗證機制與安全性實踐」）。
    2.  **專業分類 (category)**：根據內容從以下類別中選擇最適合的一個：{categories_text}
    3.  **層次標籤 (tags)**：提供 2-3 個關鍵標籤。標籤需具備「索引價值」，能幫助在該分類下進一步篩選（例如：在 Computer-Science 下使用 [Backend, Security]），避免使用過於細碎或口語的詞彙。
    4.  **結構化內容 (content)**：將原始內容重組為專業且易於理解的 Markdown 格式。內容應該清晰、有條理，並且適合技術讀者閱讀。請確保：
        -   請不要使用 Unicode 符號（如 ┌, ─, ┤）或 ASCII 繪圖。如果需要呈現流程、步驟或結構圖，請使用 Mermaid 語法輸出，並將其包在 ```mermaid 區塊內。
        -   不能對於原本內容的技術細節進行刪減或簡化，必須完整保留所有重要資訊。
        -   使用專業 Markdown 語法(H1, H2, 列表, 程式碼區塊）。
        -   必須加入目錄(Table of Contents)來概覽內容架構, 並使用內部連結(Anchor Links)讓讀者能快速跳轉到各章節。
        -   適當使用粗體、斜體、行內程式碼等格式來強調重點。
        -   必要時加入說明性的文字來補充原始內容的不足，確保讀者能完全理解技術細節。
        -   必要的話加入示例程式碼來說明概念，並確保程式碼格式正確且易於閱讀。
        -   **重點：視覺化架構**。如果原始內容涉及流程、架構或交互（如 HTTP Session 流程），請使用 **Mermaid.js** 語法繪製流程圖 (graph/sequenceDiagram) 放在內容中。
        -   **Mermaid 語法規則（務必遵守）**：每個箭頭語句必須在同一行完成，禁止換行；標籤文字中避免使用逗號、括號等特殊符號（用空格或破折號取代）；生成後請自行驗證語法正確性。
        -   如果一個複雜流程難以用一張圖表達，請將其拆解為多個步驟，並分別附上對應的靜態圖表碼。
        -   內容應包含：定義、核心原理、實作步驟、風險控管、最佳實踐等技術細節，搭配例子說明。

    ### 輸出限制：
    -   必須嚴格輸出合法的 JSON 格式。
    -   **JSON 轉義安全**：確保 content 中的換行使用 `\\n`，引號使用 `\\"`，避免破壞 JSON 結構。
    -   不要輸出任何 JSON 以外的解釋文字。

    ### JSON 範例格式：
    {{
      "title": "標題名稱",
      "category": "分類名稱",
      "tags": ["標籤1", "標籤2"],
      "content": "Markdown 內容..."
    }}

    ### 原始內容：
    {raw_text}
    """
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    json_str = response.text.strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # content 欄位的 Markdown 可能破壞 JSON，手動提取各欄位
        title = re.search(r'"title"\s*:\s*"([^"]*)"', json_str)
        category = re.search(r'"category"\s*:\s*"([^"]*)"', json_str)
        tags = re.search(r'"tags"\s*:\s*\[([^\]]*)\]', json_str)
        # content 是最後一個欄位，取 "content": " 之後到最後的 } 之前
        content_match = re.search(r'"content"\s*:\s*"(.*)', json_str, re.DOTALL)
        content = ""
        if content_match:
            content = content_match.group(1).rstrip().rstrip('}').rstrip().rstrip('"')
        tag_list = []
        if tags:
            tag_list = [t.strip().strip('"') for t in tags.group(1).split(',')]
        return {
            "title": title.group(1) if title else "Untitled",
            "category": category.group(1) if category else "99-Inbox",
            "tags": tag_list,
            "content": content
        }

def update_page_properties(page_id, ai_data):
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    notion.pages.update(
        page_id=page_id,
        properties={
            "Name": {"title": [{"text": {"content": ai_data["title"]}}]},
            "Status": {"status": {"name": "Processed"}},
            "Category": {"select": {"name": ai_data["category"]}},
            "Tags": {"multi_select": [{"name": tag} for tag in ai_data["tags"]]},
            "Updated Time": {"date": {"start": now}}
        }
    )

def delete_all_blocks(page_id):
    block_ids = [b["id"] for b in collect_paginated_api(
        notion.blocks.children.list, block_id=page_id
    )]
    for bid in block_ids:
        notion.blocks.delete(block_id=bid)

def append_blocks_batched(page_id, blocks):
    for start in range(0, len(blocks), 100):
        batch = blocks[start:start + 100]
        notion.blocks.children.append(block_id=page_id, children=batch)

def postprocess_blocks(blocks):
    """過濾 markdown TOC，插入 Notion 原生 TOC"""
    filtered = []
    skip_toc = False
    for block in blocks:
        btype = block.get("type", "")
        # 偵測 TOC 標題（目錄/Table of Contents/TOC）
        if btype.startswith("heading_"):
            text = "".join(t.get("plain_text", "") for t in block[btype].get("rich_text", []))
            if text.strip().lower() in ("目錄", "table of contents", "toc"):
                skip_toc = True
                continue
        # 跳過 TOC 下方的 anchor-link 清單
        if skip_toc and btype in ("bulleted_list_item", "numbered_list_item"):
            continue
        if skip_toc and btype not in ("bulleted_list_item", "numbered_list_item"):
            skip_toc = False
        filtered.append(block)

    # 在第一個 H1 後插入 Notion 原生 TOC
    toc = {"object": "block", "type": "table_of_contents",
           "table_of_contents": {"color": "default"}}
    for i, b in enumerate(filtered):
        if b.get("type") == "heading_1":
            filtered.insert(i + 1, toc)
            break
    return filtered

def update_notion(page_id, ai_data):
    update_page_properties(page_id, ai_data)
    delete_all_blocks(page_id)

    md_text = re.sub(r'<a\s+id="[^"]*">\s*</a>', '', ai_data["content"])
    content_blocks = parse_markdown_to_notion_blocks(md_text)
    content_blocks = postprocess_blocks(content_blocks)
    append_blocks_batched(page_id, content_blocks)

# 執行主流程
def main():
    try:
        pages = get_draft_pages()
    except APIResponseError as e:
        print(f"Failed to query database: {e}")
        return

    for page in pages:
        page_id = page["id"]
        try:
            raw_content = get_page_content(page_id)
            if not raw_content.strip():
                continue

            # AI 處理
            ai_result = organize_with_ai(raw_content)

            # 建立資料夾並存檔至 GitHub
            category_dir = f"{NOTES_DIR}/{ai_result['category']}"
            os.makedirs(category_dir, exist_ok=True)

            safe_title = ai_result["title"].replace("/", "-")
            file_path = f"{category_dir}/{safe_title}.md"
            now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
            # 將 JSON 轉義字元轉成真正的字元
            content = ai_result['content'].replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').replace('\\t', '\t')

            # Markdown 檔案：在 H1 後插入 Updated Time
            md_content = content
            content_lines = md_content.split('\n')
            if content_lines and content_lines[0].startswith('# '):
                content_lines.insert(1, f'\n> Updated: {now}\n')
                md_content = '\n'.join(content_lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            # Notion：用原始 content（不含 Updated Time，Notion 有 property）
            ai_result['content'] = content
            update_notion(page_id, ai_result)
            print(f"成功存檔至: {file_path}")

            # 等待 60 秒避免 Gemini API rate limit
            print("等待 60 秒後處理下一頁...")
            time.sleep(60)

        except APIResponseError as e:
            print(f"Notion API error for page {page_id}: {e}")
            continue
        except Exception as e:
            print(f"Error processing page {page_id}: {e}")
            continue


if __name__ == "__main__":
    print("開始執行 Notion 筆記整理與同步流程...")
    main()
