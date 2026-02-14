import os
import requests
from google import genai
import json

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
    prompt = f"""
    你是一位資深技術架構師與知識管理專家。請針對提供的原始對話進行「深度知識內化」，並嚴格遵守以下任務與格式：

    ### 任務說明：
    1.  **簡潔標題 (title)**：提取核心概念，建立一個一眼就能明瞭的簡潔專業技術標題（例如：從「聊聊 JWT」優化為「JWT 身分驗證機制與安全性實踐」）。
    2.  **專業分類 (category)**：從此清單選一：[10-Computer-Science, 20-Finance, 30-Lifestyle, 40-News, 99-Inbox]。
    3.  **層次標籤 (tags)**：提供 2-3 個關鍵標籤。標籤需具備「索引價值」，能幫助在該分類下進一步篩選（例如：在 Computer-Science 下使用 [Backend, Security]），避免使用過於細碎或口語的詞彙。
    4.  **結構化內容 (content)**：將原始內容重組為專業且易於理解的 Markdown 格式。內容應該清晰、有條理，並且適合技術讀者閱讀。請確保：
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

def parse_inline_markdown(text):
    """將 inline Markdown（粗體、斜體、行內程式碼）轉成 Notion rich_text 陣列"""
    import re
    rich_text = []
    # 匹配: `code`, **bold**, *italic*, __bold__, _italic_
    pattern = re.compile(r'(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_)')
    last_end = 0
    for match in pattern.finditer(text):
        # 前面的普通文字
        if match.start() > last_end:
            plain = text[last_end:match.start()]
            if plain:
                rich_text.append({"text": {"content": plain}})
        token = match.group()
        if token.startswith('`'):
            rich_text.append({"text": {"content": token[1:-1]}, "annotations": {"code": True}})
        elif token.startswith('**') or token.startswith('__'):
            rich_text.append({"text": {"content": token[2:-2]}, "annotations": {"bold": True}})
        elif token.startswith('*') or token.startswith('_'):
            rich_text.append({"text": {"content": token[1:-1]}, "annotations": {"italic": True}})
        last_end = match.end()
    # 剩餘的普通文字
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            rich_text.append({"text": {"content": remaining}})
    # 如果完全沒匹配到，回傳原始文字
    if not rich_text:
        rich_text.append({"text": {"content": text}})
    return rich_text

def make_rich_block(block_type, text):
    """建立帶有 inline 格式的 Notion block"""
    return {"object": "block", "type": block_type, block_type: {"rich_text": parse_inline_markdown(text)}}

def markdown_to_notion_blocks(markdown_text):
    """將 Markdown 文字轉換成 Notion block 結構"""
    import re
    blocks = []
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]

        # Code block（``` 開頭）
        if line.strip().startswith('```'):
            lang = line.strip().lstrip('`').strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code_text = '\n'.join(code_lines)[:2000]
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": code_text}}],
                    "language": lang if lang else "plain text"
                }
            })
            i += 1
            continue

        # Heading
        if line.startswith('### '):
            blocks.append(make_rich_block("heading_3", line[4:].strip()))
        elif line.startswith('## '):
            blocks.append(make_rich_block("heading_2", line[3:].strip()))
        elif line.startswith('# '):
            blocks.append(make_rich_block("heading_1", line[2:].strip()))

        # Bulleted list
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            blocks.append(make_rich_block("bulleted_list_item", line.strip()[2:]))

        # Numbered list
        elif re.match(r'^\d+\.\s', line.strip()):
            text = re.sub(r'^\d+\.\s', '', line.strip())
            blocks.append(make_rich_block("numbered_list_item", text))

        # Divider
        elif line.strip() in ('---', '***', '___'):
            blocks.append({"object": "block", "type": "divider", "divider": {}})

        # Quote
        elif line.strip().startswith('> '):
            blocks.append(make_rich_block("quote", line.strip()[2:]))

        # 普通段落（跳過空行）
        elif line.strip():
            blocks.append(make_rich_block("paragraph", line.strip()))

        i += 1
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

    # 將 Markdown 轉成 Notion blocks 並寫入
    all_blocks = markdown_to_notion_blocks(ai_data["content"])

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
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {ai_result['title']}\n\n> Updated: {now}\n\n{content}")

            # 更新 Notion（也需要轉換）
            ai_result['content'] = content
            update_notion(page_id, ai_result)
            print(f"成功存檔至: {file_path}")


if __name__ == "__main__":
    print("開始執行 Notion 筆記整理與同步流程...")
    main()