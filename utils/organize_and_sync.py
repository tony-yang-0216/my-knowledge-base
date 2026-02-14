import os
import re
import time
import requests
from google import genai
import json
import mistune
from categories import get_categories_prompt

# 1. 環境變數設定 (從 GitHub Secrets 讀取)
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化 Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

NOTES_DIR = "notes"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_draft_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {"filter": {"property": "Status", "status": {"equals": "Draft"}}}
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code != 200:
        raise ValueError(f"API error: {res.status_code}, {res.text}")
    return res.json().get("results", [])

def get_page_content(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=headers)
    blocks = res.json().get("results", [])
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
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    json_str = response.text.strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # content 欄位的 Markdown 可能破壞 JSON，手動提取各欄位
        import re
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

def inline_to_rich_text(children):
    """將 mistune inline AST tokens 轉成 Notion rich_text 陣列"""
    rich_text = []
    if not children:
        return [{"text": {"content": ""}}]
    for token in children:
        ttype = token.get('type', '')
        if ttype == 'text':
            rich_text.append({"text": {"content": token['raw']}})
        elif ttype == 'strong':
            inner = _extract_plain_text(token.get('children', []))
            rich_text.append({"text": {"content": inner}, "annotations": {"bold": True}})
        elif ttype == 'emphasis':
            inner = _extract_plain_text(token.get('children', []))
            rich_text.append({"text": {"content": inner}, "annotations": {"italic": True}})
        elif ttype == 'codespan':
            rich_text.append({"text": {"content": token.get('raw', '')}, "annotations": {"code": True}})
        elif ttype == 'link':
            link_text = _extract_plain_text(token.get('children', []))
            url = token.get('attrs', {}).get('url', '')
            if url.startswith('#'):
                # Anchor link — 在 Notion 裡顯示為純文字
                rich_text.append({"text": {"content": link_text}})
            else:
                rich_text.append({"text": {"content": link_text, "link": {"url": url}}})
        elif ttype in ('softbreak', 'linebreak'):
            rich_text.append({"text": {"content": "\n"}})
        else:
            if 'children' in token:
                rich_text.extend(inline_to_rich_text(token['children']))
            elif 'raw' in token:
                rich_text.append({"text": {"content": token['raw']}})
    if not rich_text:
        rich_text.append({"text": {"content": ""}})
    return rich_text

def _extract_plain_text(children):
    """從 inline AST tokens 提取純文字"""
    parts = []
    for token in children:
        if 'raw' in token:
            parts.append(token['raw'])
        elif 'children' in token:
            parts.append(_extract_plain_text(token['children']))
    return ''.join(parts)

def _get_inline_children(item_children):
    """從 list_item 的 children 取得 inline tokens（paragraph 或 block_text 內的）"""
    for child in item_children:
        if child['type'] in ('paragraph', 'block_text'):
            return child.get('children', [])
    return []

def _is_toc_list(list_token):
    """檢查一個 list 是否為 TOC（所有 items 都是 anchor links）"""
    for item in list_token.get('children', []):
        inline = _get_inline_children(item.get('children', []))
        has_anchor = False
        for token in inline:
            if token.get('type') == 'link':
                url = token.get('attrs', {}).get('url', '')
                if url.startswith('#'):
                    has_anchor = True
        if not has_anchor:
            return False
    return True

def _make_block(block_type, inline_children):
    """建立 Notion block（帶 rich_text）"""
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": inline_to_rich_text(inline_children)}
    }

def _convert_list(list_token):
    """將 mistune list AST 轉成 Notion blocks，正確處理巢狀結構"""
    blocks = []
    ordered = list_token.get('attrs', {}).get('ordered', False)
    block_type = "numbered_list_item" if ordered else "bulleted_list_item"

    for item in list_token.get('children', []):
        if item.get('type') != 'list_item':
            continue

        inline_children = _get_inline_children(item.get('children', []))
        nested_blocks = []

        # 找巢狀 list（子清單）
        for child in item.get('children', []):
            if child['type'] == 'list':
                nested_blocks.extend(_convert_list(child))

        block = _make_block(block_type, inline_children)
        if nested_blocks:
            block[block_type]["children"] = nested_blocks
        blocks.append(block)

    return blocks

def markdown_to_notion_blocks(markdown_text, for_notion=False):
    """使用 mistune AST parser 將 Markdown 轉成 Notion blocks"""
    # 清理 HTML anchor tags
    markdown_text = re.sub(r'<a\s+id="[^"]*">\s*</a>', '', markdown_text)

    md = mistune.create_markdown(renderer='ast')
    tokens = md(markdown_text)

    blocks = []
    skip_toc = False

    for token in tokens:
        ttype = token.get('type', '')

        if ttype == 'blank_line':
            continue

        # Heading
        if ttype == 'heading':
            text = _extract_plain_text(token.get('children', []))
            level = token.get('attrs', {}).get('level', 1)

            # For Notion: 跳過 TOC heading
            if for_notion and text.strip().lower() in ('目錄', 'table of contents', 'toc'):
                skip_toc = True
                continue
            skip_toc = False

            block_type = f"heading_{min(level, 3)}"
            blocks.append(_make_block(block_type, token.get('children', [])))

        # Paragraph
        elif ttype == 'paragraph':
            blocks.append(_make_block("paragraph", token.get('children', [])))

        # List
        elif ttype == 'list':
            # For Notion: 跳過 TOC list（所有 items 都是 anchor links）
            if for_notion and (skip_toc or _is_toc_list(token)):
                skip_toc = False
                continue
            list_blocks = _convert_list(token)
            blocks.extend(list_blocks)

        # Code block
        elif ttype == 'block_code':
            code = token.get('raw', '')[:2000]
            lang = token.get('attrs', {}).get('info', '') or 'plain text'
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": code}}],
                    "language": lang
                }
            })

        # Divider
        elif ttype == 'thematic_break':
            blocks.append({"object": "block", "type": "divider", "divider": {}})

        # Block quote
        elif ttype == 'block_quote':
            for child in token.get('children', []):
                if child['type'] == 'paragraph':
                    blocks.append(_make_block("quote", child.get('children', [])))

    return blocks

def update_notion(page_id, ai_data):
    # 更新屬性 (Status, Category, Tags)
    url = f"https://api.notion.com/v1/pages/{page_id}"
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    properties = {
        "properties": {
            "Name": {"title": [{"text": {"content": ai_data["title"]}}]},
            "Status": {"status": {"name": "Processed"}},
            "Category": {"select": {"name": ai_data["category"]}},
            "Tags": {"multi_select": [{"name": tag} for tag in ai_data["tags"]]},
            "Updated Time": {"date": {"start": now}}
        }
    }
    requests.patch(url, json=properties, headers=headers)

    # 先刪除頁面原有的所有 blocks
    children_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    existing = requests.get(children_url, headers=headers).json().get("results", [])
    for block in existing:
        requests.delete(f"https://api.notion.com/v1/blocks/{block['id']}", headers=headers)

    # 將 Markdown 轉成 Notion blocks（for_notion=True 會自動過濾 TOC 和 HTML anchors）
    content_blocks = markdown_to_notion_blocks(ai_data["content"], for_notion=True)

    # 在第一個 H1 標題後插入 Notion 原生 Table of Contents block
    toc_block = {"object": "block", "type": "table_of_contents", "table_of_contents": {"color": "default"}}
    insert_idx = 0
    for idx, block in enumerate(content_blocks):
        if block.get("type") == "heading_1":
            insert_idx = idx + 1
            break
    content_blocks.insert(insert_idx, toc_block)
    all_blocks = content_blocks

    # Notion API 一次最多 100 個 blocks，分批送出
    for start in range(0, len(all_blocks), 100):
        batch = all_blocks[start:start + 100]
        requests.patch(children_url, json={"children": batch}, headers=headers)

# 執行主流程
def main():
    pages = get_draft_pages()
    for page in pages:
        page_id = page["id"]
        print(f"正在處理: {page_id}")
        raw_content = get_page_content(page_id)
        print(f"原始內容:\n{raw_content}\n{'-'*40}")
        if raw_content.strip():
            # AI 處理
            ai_result = organize_with_ai(raw_content)
            # print(f"AI 整理結果:\n{json.dumps(ai_result, indent=2, ensure_ascii=False)}\n{'='*60}")
            
            # 建立資料夾並存檔至 GitHub
            category_dir = f"{NOTES_DIR}/{ai_result['category']}"
            os.makedirs(category_dir, exist_ok=True)
            
            safe_title = ai_result["title"].replace("/", "-")
            file_path = f"{category_dir}/{safe_title}.md"
            from datetime import datetime, timezone, timedelta
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


if __name__ == "__main__":
    print("開始執行 Notion 筆記整理與同步流程...")
    main()