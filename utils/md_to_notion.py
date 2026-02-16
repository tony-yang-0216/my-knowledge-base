"""Pure markdown -> Notion block conversion. Zero API calls, zero side effects."""

import re
import mistune
from constants import NOTION_RICH_TEXT_LIMIT
from notion_languages import normalize_notion_language


# ---------------------------------------------------------------------------
# Inline helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Mermaid sanitization
# ---------------------------------------------------------------------------

def _sanitize_mermaid(code):
    """Quote Mermaid node/edge labels that contain parentheses to prevent parse errors."""
    # Quote [...] labels containing ( or ) that aren't already quoted
    code = re.sub(
        r'\[([^"\[\]]*\([^"\[\]]*)\]',
        lambda m: f'["{m.group(1)}"]',
        code
    )
    # Quote |...| edge labels containing ( or ) that aren't already quoted
    code = re.sub(
        r'\|([^"|]*\([^"|]*)\|',
        lambda m: f'|"{m.group(1)}"|',
        code
    )
    return code


def _sanitize_mermaid_in_markdown(content):
    """對 Markdown 原文中所有 ```mermaid 區塊套用 _sanitize_mermaid，確保 GitHub 也能正確渲染。"""
    return re.sub(
        r'(```mermaid\s*\n)(.*?)(```)',
        lambda m: m.group(1) + _sanitize_mermaid(m.group(2)) + m.group(3),
        content,
        flags=re.DOTALL,
    )


# ---------------------------------------------------------------------------
# Block-level helpers
# ---------------------------------------------------------------------------

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
                code = child.get('raw', '')[:NOTION_RICH_TEXT_LIMIT]
                lang = child.get('attrs', {}).get('info', '') or 'plain text'
                lang = normalize_notion_language(lang)
                if lang == 'mermaid':
                    code = _sanitize_mermaid(code)
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

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
            code = token.get('raw', '')[:NOTION_RICH_TEXT_LIMIT]
            lang = token.get('attrs', {}).get('info', '') or 'plain text'
            lang = normalize_notion_language(lang)
            if lang == 'mermaid':
                code = _sanitize_mermaid(code)
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
