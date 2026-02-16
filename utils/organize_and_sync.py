import os
import re
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from google import genai
from notion_client import Client
import mistune
from categories import get_categories_prompt
from prompts import build_organize_prompt
from notion_languages import normalize_notion_language

# 環境變數設定（本地從 .env 載入，CI 從 GitHub Secrets 讀取）
load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化（條件式，讓只需要轉換函式的工具不必設定 API key）
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
notion = Client(auth=NOTION_TOKEN, notion_version="2022-06-28") if NOTION_TOKEN else None

NOTES_DIR = "notes"


def get_draft_pages():
    # temp_meta = notion.databases.retrieve(database_id=DATABASE_ID)
    # print(f"物件類型: {temp_meta.get('object')}")
    results = []
    start_cursor = None
    while True:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            # 加上 page_size=100 減少 HTTP 請求次數
            page_size=100, 
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


def _paginate_blocks(block_id):
    """分頁取得所有子 blocks"""
    results = []
    has_more = True
    start_cursor = None
    while has_more:
        response = notion.blocks.children.list(
            block_id=block_id,
            start_cursor=start_cursor,
            page_size=100
        )
        results.extend(response.get("results", []))
        has_more = response.get("has_more", False)
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

def organize_with_ai(raw_text):
    categories_text = get_categories_prompt()
    prompt = build_organize_prompt(raw_text, categories_text)
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
    """
    最後的結案步驟：使用 AI 提取的專業標題更新 Notion 頁面屬性，
    包括狀態(Status)、分類(Category)、標籤(Tags)與更新時間。
    """
    try:
        # 取得台灣時間 (UTC+8) 的 ISO 8601 格式
        now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        
        # 封裝要更新的屬性
        # 注意：這裡的 ai_data["title"] 是由 AI 根據內容分析後產出的專業標題
        props = {
            "Name": {"title": [{"text": {"content": ai_data["title"]}}]},
            "Status": {"status": {"name": "Processed"}},
            "Category": {"select": {"name": ai_data["category"]}},
            "Tags": {"multi_select": [{"name": tag} for tag in ai_data["tags"]]},
            "Updated Time": {"date": {"start": now}}
        }

        # 呼叫 Notion API 更新頁面屬性
        notion.pages.update(
            page_id=page_id,
            properties=props
        )
        print(f"✨ [Notion Properties] 屬性與標題更新成功: {page_id}")
        
    except Exception as e:
        print(f"❌ [Notion Properties] 更新失敗: {e}")
        # 向上拋出錯誤，讓 main() 標記此頁面處理未完成，以便下一小時重新嘗試
        raise


def delete_all_blocks(page_id):
    """刪除頁面內的所有頂層區塊"""
    blocks = _paginate_blocks(page_id)
    for b in blocks:
        bid = b["id"]
        try:
            notion.blocks.delete(block_id=bid)
        except Exception as e:
            if "archived" in str(e).lower():
                continue
            else:
                print(f"⚠️ 刪除區塊 {bid} 時發生非預期錯誤: {e}")
                raise

def _chunk_text(text, size=2000):
    """將文字切成不超過 size 的片段（Notion rich_text 上限 2000 字元）"""
    return [text[i:i+size] for i in range(0, len(text), size)] or [""]


def append_blocks_batched(page_id, blocks):
    for start in range(0, len(blocks), 100):
        batch = blocks[start:start + 100]
        notion.blocks.children.append(block_id=page_id, children=batch)


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
        elif ttype == 'strikethrough':
            inner = _extract_plain_text(token.get('children', []))
            rich_text.append({"text": {"content": inner}, "annotations": {"strikethrough": True}})
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

        # 找巢狀 list（子清單）與 code blocks
        for child in item.get('children', []):
            if child['type'] == 'list':
                nested_blocks.extend(_convert_list(child))
            elif child['type'] == 'block_code':
                code = child.get('raw', '')[:2000]
                lang = child.get('attrs', {}).get('info', '') or 'plain text'
                lang = normalize_notion_language(lang)
                nested_blocks.append({
                    "object": "block", "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": code}}],
                        "language": lang
                    }
                })

        block = _make_block(block_type, inline_children)
        if nested_blocks:
            block[block_type]["children"] = nested_blocks
        blocks.append(block)

    return blocks


def _convert_table(table_token):
    """將 mistune table AST 轉成 Notion native table block"""
    rows = []
    num_columns = 0

    for section in table_token.get('children', []):
        stype = section.get('type', '')
        if stype == 'table_head':
            head_cells = [
                inline_to_rich_text(cell.get('children', []))
                for cell in section.get('children', [])
                if cell.get('type') == 'table_cell'
            ]
            num_columns = len(head_cells)
            rows.append({
                "type": "table_row",
                "table_row": {"cells": head_cells}
            })
        elif stype == 'table_body':
            for table_row in section.get('children', []):
                if table_row.get('type') != 'table_row':
                    continue
                row_cells = [
                    inline_to_rich_text(cell.get('children', []))
                    for cell in table_row.get('children', [])
                    if cell.get('type') == 'table_cell'
                ]
                # 確保 cell 數量與 header 一致
                while len(row_cells) < num_columns:
                    row_cells.append([{"text": {"content": ""}}])
                row_cells = row_cells[:num_columns]
                rows.append({
                    "type": "table_row",
                    "table_row": {"cells": row_cells}
                })

    if not rows:
        return None

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": num_columns,
            "has_column_header": True,
            "has_row_header": False,
            "children": rows
        }
    }


def markdown_to_notion_blocks(markdown_text, for_notion=False):
    """使用 mistune AST parser 將 Markdown 轉成 Notion blocks"""
    # 清理 HTML anchor tags
    markdown_text = re.sub(r'<a\s+id="[^"]*">\s*</a>', '', markdown_text)

    md = mistune.create_markdown(renderer='ast', plugins=['table', 'strikethrough'])
    tokens = md(markdown_text)

    blocks = []
    skip_toc = False

    toc_keywords = ('目錄', 'table of contents', 'toc', '內容大綱', 'outline')

    for token in tokens:
        ttype = token.get('type', '')

        if ttype == 'blank_line':
            continue

        # Heading
        if ttype == 'heading':
            text = _extract_plain_text(token.get('children', []))
            level = token.get('attrs', {}).get('level', 1)

            # For Notion: 跳過 TOC heading
            if for_notion and text.strip().lower() in toc_keywords:
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
            lang = normalize_notion_language(lang)
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": code}}],
                    "language": lang
                }
            })

        # Table
        elif ttype == 'table':
            table_block = _convert_table(token)
            if table_block:
                blocks.append(table_block)

        # Divider
        elif ttype == 'thematic_break':
            blocks.append({"object": "block", "type": "divider", "divider": {}})

        # Block quote
        elif ttype == 'block_quote':
            for child in token.get('children', []):
                if child['type'] == 'paragraph':
                    blocks.append(_make_block("quote", child.get('children', [])))

    return blocks


def chunk_raw_content(text, chunk_size=1900):
    """單純將純文字切成片段，用於還原機制"""
    if not text:
        return ["(無內容)"]
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


def update_notion_blocks_only(page_id, ai_data, raw_content):
    """
    僅更新 Notion 頁面的內容區塊 (Blocks)。
    如果失敗，會嘗試還原原始內容為純文字。
    """
    # 1. 預處理：失敗直接 raise，不執行 API 刪除 (避免空刪)
    try:
        content_blocks = markdown_to_notion_blocks(ai_data["content"], for_notion=True)
        # 插入 Notion 原生 TOC (Table of Contents) 在頁面最頂端
        toc_block = {
            "object": "block",
            "type": "table_of_contents",
            "table_of_contents": {"color": "default"}
        }
        content_blocks.insert(0, toc_block)
    except Exception as e:
        print(f"❌ [預處理] 失敗: {e}")
        raise

    # 2. API 操作：執行 刪除 -> 寫入
    try:
        delete_all_blocks(page_id)
        append_blocks_batched(page_id, content_blocks)
        print(f"✅ [Notion Blocks] 內容更新成功: {page_id}")
    except Exception as e:
        print(f"⚠️ [Notion API] 更新失敗，啟動還原機制。錯誤: {e}")
        try:
            text_chunks = chunk_raw_content(raw_content)
            fallback = [
                {
                    "object": "block", 
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
                } for chunk in text_chunks
            ]
            append_blocks_batched(page_id, fallback)
            print("🔄 [Recovery] 原始內容已成功還原。")
        except Exception as recovery_error:
            print(f"🚨 [Fatal] 連還原也失敗了！頁面可能為空。錯誤: {recovery_error}")
        
        # 務必再次拋出錯誤，讓 main() 知曉並跳過後續 GitHub 存檔
        raise


def save_to_github(ai_result, content):
    """
    建立分類資料夾並將 AI 處理後的 Markdown 內容存檔至本地目錄（後續由 GitHub Action Commit）。
    """
    try:
        # 1. 確保分類資料夾存在
        category_dir = f"{NOTES_DIR}/{ai_result['category']}"
        os.makedirs(category_dir, exist_ok=True)

        # 2. 處理安全標題（移除檔案系統不允許的字元）
        safe_title = ai_result["title"].replace("/", "-").replace("\\", "-")
        file_path = f"{category_dir}/{safe_title}.md"
        
        # 3. 取得當前時間 (台灣時間)
        now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")

        # 4. 在 H1 標題後插入 Updated Time 註記
        md_content = content
        content_lines = md_content.split('\n')
        if content_lines and content_lines[0].startswith('# '):
            # 在第一行 (# Title) 之後插入更新時間
            content_lines.insert(1, f'\n> Updated: {now}\n')
            md_content = '\n'.join(content_lines)

        # 5. 寫入檔案
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print(f"💾 [GitHub Sync] 檔案已寫入: {file_path}")
        return file_path

    except Exception as e:
        print(f"❌ [GitHub Sync] 檔案寫入失敗: {e}")
        raise # 向上拋出錯誤，讓 main() 知曉並跳過後續的 Status 更新


def main():
    pages = get_draft_pages()
    print(f"找到 {len(pages)} 頁待處理...")
    
    # 紀錄是否有任何一頁失敗，用來決定最後 Workflow 的狀態
    has_any_error = False

    for page in pages:
        page_id = page["id"]
        try:
            raw_content = get_page_content(page_id)
            if not raw_content.strip():
                continue

            print(f"正在處理頁面: {page_id}，內容長度: {len(raw_content)} 字元")

            # A. AI 處理
            ai_result = organize_with_ai(raw_content)
            content = ai_result['content'].replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').replace('\\t', '\t')
            ai_result['content'] = content

            # B. 更新 Notion 內容 (此時不改 Status，失敗會自動觸發 fallback)
            # 注意：update_notion 內部不應包含修改 Status 的邏輯
            update_notion_blocks_only(page_id, ai_result, raw_content)

            # C. 存檔至 GitHub
            save_to_github(ai_result, content)

            # D. 最後一步：所有都成功了，才修改 Notion 屬性 (Status: Done)
            # 這樣如果上面 B 或 C 失敗，這篇在下一小時會被重新處理
            update_page_properties(page_id, ai_result)
            
            print(f"✅ 頁面 {page_id} 處理完成。")

        except Exception as e:
            print(f"❌ 處理頁面 {page_id} 時發生錯誤: {e}")
            has_any_error = True  # 標記發生過錯誤
            continue # 跳過這篇，處理下一篇

        # 節流處理
        time.sleep(60)

    # 如果有任何一頁失敗，強制結束程式並拋出錯誤，讓 GitHub Actions 變紅燈
    if has_any_error:
        print("🚨 部分頁面處理失敗，請檢查 Log。")
        sys.exit(1) # 讓 GitHub Action 報錯


# def read_md_from_note(file_path):
#     """從本地 notes 資料夾讀取 md 檔案內容"""
#     with open(file_path, "r", encoding="utf-8") as f:
#         return f.read()


# if __name__ == "__main__":
#     page_id = "dbd86d185388478db501581036f3a042"
#     raw_content = "fake raw content for testing"

#     # 從本地 md 讀取 content
#     md_path = os.path.join(NOTES_DIR, "10-Computer-Science", "Claude AI 知識內化與 LLM Context Token 優化策略.md")
#     content = read_md_from_note(md_path)
#     ai_result = {"content": content}

#     print(f"讀取內容長度: {len(content)} 字元")
#     print(f"開始測試 update_notion_blocks_only...")
#     update_notion_blocks_only(page_id, ai_result, raw_content)
#     print("測試完成！")


if __name__ == "__main__":
    print("開始執行 Notion 筆記整理與同步流程...")
    main()
