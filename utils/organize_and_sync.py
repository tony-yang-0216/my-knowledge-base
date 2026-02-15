import os
import re
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from google import genai
from notion_client import Client
from md2notionpage.core import parse_markdown_to_notion_blocks
from categories import get_categories_prompt
from prompts import build_organize_prompt

# 環境變數設定（本地從 .env 載入，CI 從 GitHub Secrets 讀取）
load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
notion = Client(auth=NOTION_TOKEN, notion_version="2022-06-28")

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


def _strip_invalid_links(blocks):
    """深度掃描所有 blocks，移除非 http/https 的 link"""
    for block in blocks:
        btype = block.get("type", "")
        if not btype:
            continue

        block_data = block.get(btype, {})
        # 1. 處理當前 block 的文本
        if isinstance(block_data, dict) and "rich_text" in block_data:
            for rt in block_data.get("rich_text", []):
                text_obj = rt.get("text", {})
                link = text_obj.get("link")
                if link:
                    url = link.get("url", "")
                    if not (url.startswith("http://") or url.startswith("https://")):
                        text_obj["link"] = None
                        rt["href"] = None

        # 2. 處理子 blocks (例如 Nested Lists, Toggle 等)
        # 注意：有些 SDK 版本 children 是直接掛在 block 下，有些是在 block_data 裡
        children = block_data.get("children") or block.get("children", [])
        if children:
            _strip_invalid_links(children)

    return blocks

def postprocess_blocks(blocks):
    """
    1. 徹底移除 AI 生成的 Markdown 文字目錄
    2. 在頁面最頂端插入 Notion 原生 TOC 區塊
    """
    filtered = []
    skip_toc = False
    
    # 常用於目錄的關鍵字
    toc_keywords = ("目錄", "table of contents", "toc", "內容大綱", "outline")

    for block in blocks:
        btype = block.get("type", "")
        if not btype:
            continue

        # 安全地取得該 block 的內容資料
        block_data = block.get(btype, {})

        # A. 偵測目錄標題 (H1, H2, 或 H3)
        if btype.startswith("heading_"):
            rich_text = block_data.get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in rich_text).strip().lower()

            # 如果標題包含關鍵字，開啟「跳過模式」
            if any(k in text for k in toc_keywords):
                skip_toc = True
                print(f"🗑️ 偵測到假目錄標題: '{text}'，開始跳過後續列表...")
                continue

        # B. 跳過模式：連續跳過清單項目 (假目錄的內容)
        if skip_toc:
            if btype in ("bulleted_list_item", "numbered_list_item"):
                continue
            else:
                # 遇到非列表區塊，代表假目錄結束，關閉跳過模式
                skip_toc = False

        filtered.append(block)

    # C. 插入 Notion 原生 TOC (Table of Contents)
    # 我們不再找 H1，直接強制插在 index 0 (最頂端)，保證成功
    notion_toc = {
        "object": "block", 
        "type": "table_of_contents",
        "table_of_contents": {"color": "default"}
    }
    
    filtered.insert(0, notion_toc)
    print("✅ 已在頁面頂端插入 Notion 原生 TOC")
    
    return filtered


def _fix_malformed_tables(md_text):
    """修復 md2notionpage 的 table parser bug：單行 pipe 格式會觸發 IndexError。
    確保所有 table 至少有 header + delimiter 兩行，否則 escape pipes。"""
    lines = md_text.split('\n')
    result = []
    table_buf = []
    table_row_re = re.compile(r'^\|.+\|$')

    def flush_table():
        if len(table_buf) < 2:
            # 單行 pipe，escape 避免 md2notionpage 誤判
            for line in table_buf:
                result.append(line.replace('|', '\\|'))
            table_buf.clear()
            return

        # 檢查第二行是否為分隔線（|---|---|）
        delimiter_re = re.compile(r'^\|[\s:\-]+(\|[\s:\-]+)*\|$')
        if not delimiter_re.match(table_buf[1].strip()):
            # 缺少分隔線，根據第一行欄數自動補齊
            col_count = table_buf[0].count('|') - 1
            delimiter = '| ' + ' | '.join(['---'] * max(col_count, 1)) + ' |'
            table_buf.insert(1, delimiter)

        result.extend(table_buf)
        table_buf.clear()

    for line in lines:
        if table_row_re.match(line.strip()):
            table_buf.append(line)
        else:
            if table_buf:
                flush_table()
            result.append(line)
    if table_buf:
        flush_table()

    return '\n'.join(result)


def _extract_and_replace_tables(md_text):
    """從 markdown 中提取表格，替換為佔位符，避免 md2notionpage 將其轉為 LaTeX。
    回傳 (modified_md, tables_dict)，tables_dict = {N: [table_lines]}。
    """
    lines = md_text.split('\n')
    result = []
    table_buf = []
    tables_dict = {}
    counter = 0
    table_row_re = re.compile(r'^\s*\|.+\|')

    def flush_table():
        nonlocal counter
        if not table_buf:
            return
        # 至少需要 header + delimiter 才算有效表格
        delimiter_re = re.compile(r'^\s*\|[\s:]*-+[\s:]*(\|[\s:]*-+[\s:]*)*\|')
        if len(table_buf) >= 2 and delimiter_re.match(table_buf[1]):
            tables_dict[counter] = list(table_buf)
            result.append(f'TABLEPLACEHOLDER{counter}')
            counter += 1
        else:
            # 不是有效表格，原樣保留
            result.extend(table_buf)
        table_buf.clear()

    for line in lines:
        if table_row_re.match(line):
            table_buf.append(line)
        else:
            if table_buf:
                flush_table()
            result.append(line)
    if table_buf:
        flush_table()

    return '\n'.join(result), tables_dict


def _parse_table_cells(row_line):
    """解析一行表格，回傳 cell 內容清單。"""
    # 去掉首尾的 |
    stripped = row_line.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split('|')]


def _markdown_table_to_notion_blocks(table_lines):
    """將 markdown 表格行轉為 Notion 原生 table block。"""
    if len(table_lines) < 2:
        return []

    header_cells = _parse_table_cells(table_lines[0])
    num_columns = len(header_cells)

    # 建立所有 row（header + data rows，跳過 delimiter row）
    rows = []
    for i, line in enumerate(table_lines):
        if i == 1:
            continue  # 跳過分隔線
        cells = _parse_table_cells(line)
        # 確保 cell 數量與 header 一致
        while len(cells) < num_columns:
            cells.append('')
        cells = cells[:num_columns]

        row = {
            "type": "table_row",
            "table_row": {
                "cells": [
                    [{"type": "text", "text": {"content": cell}}]
                    for cell in cells
                ]
            }
        }
        rows.append(row)

    table_block = {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": num_columns,
            "has_column_header": True,
            "has_row_header": False,
            "children": rows
        }
    }
    return table_block


def _replace_table_placeholders(blocks, tables_dict):
    """將 parse_markdown_to_notion_blocks 產生的佔位符段落替換為 Notion table block。"""
    if not tables_dict:
        return blocks

    placeholder_re = re.compile(r'^TABLEPLACEHOLDER(\d+)$')
    result = []
    for block in blocks:
        replaced = False
        if block.get('type') == 'paragraph':
            rich_text = block.get('paragraph', {}).get('rich_text', [])
            if len(rich_text) == 1:
                text_content = rich_text[0].get('text', {}).get('content', '').strip()
                m = placeholder_re.match(text_content)
                if m:
                    idx = int(m.group(1))
                    if idx in tables_dict:
                        table_block = _markdown_table_to_notion_blocks(tables_dict[idx])
                        if table_block:
                            result.append(table_block)
                            replaced = True
        if not replaced:
            result.append(block)
    return result


_TILDE_PLACEHOLDER = '\u200BTILDE\u200B'


def _escape_single_tildes(md_text):
    """將非成對的 ~ 替換為佔位符，防止 md2notionpage 誤判為 strikethrough。

    md2notionpage 用單個 ~ 作為 strikethrough 標記，但標準 Markdown 是 ~~。
    此函式保留 ~~（真正的 strikethrough），只轉義孤立的 ~。
    """
    # 先保護 ~~（標準 strikethrough）
    md_text = md_text.replace('~~', '\x00DOUBLE_TILDE\x00')
    # 轉義剩餘的單 ~
    md_text = md_text.replace('~', _TILDE_PLACEHOLDER)
    # 還原 ~~
    md_text = md_text.replace('\x00DOUBLE_TILDE\x00', '~~')
    return md_text


def _restore_tildes_in_blocks(blocks):
    """還原 blocks 中所有 rich_text 裡的波浪號佔位符。"""
    for block in blocks:
        btype = block.get('type', '')
        block_data = block.get(btype, {})
        if not isinstance(block_data, dict):
            continue
        for rt in block_data.get('rich_text', []):
            text_obj = rt.get('text', {})
            if 'content' in text_obj:
                text_obj['content'] = text_obj['content'].replace(_TILDE_PLACEHOLDER, '~')
            if 'plain_text' in rt:
                rt['plain_text'] = rt['plain_text'].replace(_TILDE_PLACEHOLDER, '~')
        # 遞迴處理子 blocks
        children = block_data.get('children', [])
        if children:
            _restore_tildes_in_blocks(children)
    return blocks


def _normalize_code_fences(md_text):
    """將 code fence 語言名稱中的空格替換為底線，讓 md2notionpage 的 \\w+ regex 能正確匹配。"""
    def _replace_lang(m):
        lang = m.group(1).strip()
        normalized = lang.replace(' ', '_')
        return f'```{normalized}\n'
    md_text = re.sub(r'```([ \w]+)\n', _replace_lang, md_text)
    # 補上 bare ``` (無語言) 的預設語言，避免 md2notionpage 無法解析
    # 只替換 opening fence（非 closing fence）：用狀態追蹤配對
    lines = md_text.split('\n')
    in_code = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('```'):
            if not in_code:
                # opening fence：如果是 bare ```，補上 text
                if stripped == '```':
                    lines[i] = line.replace('```', '```text', 1)
                in_code = True
            else:
                # closing fence
                in_code = False
    return '\n'.join(lines)


def _restore_code_languages(blocks):
    """還原 code block 語言名稱中的底線為空格（例如 plain_text → plain text）。"""
    lang_restore_map = {
        'plain_text': 'plain text',
        'text': 'plain text',
    }
    for block in blocks:
        if block.get('type') == 'code':
            lang = block['code'].get('language', '')
            if lang in lang_restore_map:
                block['code']['language'] = lang_restore_map[lang]
        # 遞迴處理子 blocks
        children = block.get(block.get('type', ''), {})
        if isinstance(children, dict):
            child_blocks = children.get('children', [])
            if child_blocks:
                _restore_code_languages(child_blocks)
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
        md_text = re.sub(r'<a\s+id="[^"]*">\s*</a>', '', ai_data["content"])
        md_text = _fix_malformed_tables(md_text)
        md_text = _normalize_code_fences(md_text)
        md_text = _escape_single_tildes(md_text)
        md_text, tables_dict = _extract_and_replace_tables(md_text)
        content_blocks = parse_markdown_to_notion_blocks(md_text)
        content_blocks = _replace_table_placeholders(content_blocks, tables_dict)
        content_blocks = _restore_code_languages(content_blocks)
        content_blocks = _restore_tildes_in_blocks(content_blocks)
        content_blocks = _strip_invalid_links(content_blocks)
        content_blocks = postprocess_blocks(content_blocks)
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
