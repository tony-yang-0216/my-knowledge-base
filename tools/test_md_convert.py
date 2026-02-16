#!/usr/bin/env python3
"""測試 Markdown 檔案經 mistune AST 轉換後的 Notion blocks 結構。"""
import argparse
import json
import os
import sys

# 加入 utils/ 目錄以匯入模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from md_to_notion import markdown_to_notion_blocks


def strip_frontmatter(text):
    """如果內容以 YAML frontmatter 開頭（---），則剝離並回傳 body。"""
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2].lstrip("\n")


def convert_md_to_blocks(md_text, for_notion=True):
    """執行 Markdown → Notion blocks 轉換（使用 mistune AST parser）。"""
    return markdown_to_notion_blocks(md_text, for_notion=for_notion)


def print_summary(blocks, preview_count=5):
    """印出 block 統計、潛在問題與前 N 個 blocks 預覽。"""
    # 統計各類型 block 數量
    type_counts = {}
    issues = []

    def count_blocks(block_list, depth=0):
        for block in block_list:
            btype = block.get("type", "unknown")
            type_counts[btype] = type_counts.get(btype, 0) + 1

            block_data = block.get(btype, {})
            if isinstance(block_data, dict):
                # 檢查 rich_text 長度
                for rt in block_data.get("rich_text", []):
                    content = rt.get("text", {}).get("content", "")
                    if len(content) > 1800:
                        issues.append(
                            f"[超長 rich_text] {btype} block, "
                            f"{len(content)} 字元 (前 50 字: {content[:50]}...)"
                        )

                # 檢查空語言 code block
                if btype == "code":
                    lang = block_data.get("language", "")
                    if not lang:
                        code_preview = "".join(
                            t.get("text", {}).get("content", "")
                            for t in block_data.get("rich_text", [])
                        )[:50]
                        issues.append(f"[空語言 code block] 前 50 字: {code_preview}...")

                # 遞迴處理子 blocks
                children = block_data.get("children", [])
                if children:
                    count_blocks(children, depth + 1)

    count_blocks(blocks)

    # 印出統計
    total = sum(type_counts.values())
    print(f"=== Block 統計 (共 {total} 個) ===")
    for btype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {btype}: {count}")

    # 印出潛在問題
    if issues:
        print(f"\n=== 潛在問題 ({len(issues)} 個) ===")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n=== 未偵測到潛在問題 ===")

    # 前 N 個 blocks 預覽
    print(f"\n=== 前 {min(preview_count, len(blocks))} 個 Blocks 預覽 ===")
    for i, block in enumerate(blocks[:preview_count]):
        btype = block.get("type", "unknown")
        block_data = block.get(btype, {})
        if isinstance(block_data, dict):
            rich_text = block_data.get("rich_text", [])
            text = "".join(t.get("text", {}).get("content", "") or t.get("plain_text", "") for t in rich_text)
            if len(text) > 80:
                text = text[:80] + "..."
            print(f"  [{i}] {btype}: {text}")
        else:
            print(f"  [{i}] {btype}")


def filter_blocks(blocks, block_type):
    """遞迴篩選特定類型的 blocks。"""
    result = []
    for block in blocks:
        btype = block.get("type", "")
        if btype == block_type:
            result.append(block)
        block_data = block.get(btype, {})
        if isinstance(block_data, dict):
            children = block_data.get("children", [])
            if children:
                result.extend(filter_blocks(children, block_type))
    return result


def main():
    parser = argparse.ArgumentParser(
        description="測試 Markdown 轉 Notion blocks（mistune AST parser）"
    )
    parser.add_argument("file", nargs="?", default="-",
                        help="Markdown 檔案路徑（省略則從 stdin 讀取）")
    parser.add_argument("--json", action="store_true",
                        help="輸出完整 Notion block JSON")
    parser.add_argument("--filter", metavar="TYPE",
                        help="只顯示特定類型的 blocks（例如 code, table, heading_2）")
    parser.add_argument("--raw", action="store_true",
                        help="不剝離 YAML frontmatter，不啟用 for_notion 過濾（除錯用）")
    args = parser.parse_args()

    # 讀取 Markdown 內容
    if args.file == "-":
        if sys.stdin.isatty():
            parser.error("請提供檔案路徑或透過 stdin 傳入 Markdown 內容")
        md_text = sys.stdin.read()
    else:
        with open(args.file, "r", encoding="utf-8") as f:
            md_text = f.read()

    print(f"讀取 Markdown: {len(md_text)} 字元")

    # 預設行為：模擬實際寫入 Notion 的流程（剝離 frontmatter + for_notion=True）
    if not args.raw:
        md_text = strip_frontmatter(md_text)
        print(f"剝離 frontmatter 後: {len(md_text)} 字元\n")
    else:
        print("(--raw 模式：不剝離 frontmatter，不啟用 for_notion 過濾)\n")

    # 轉換
    blocks = convert_md_to_blocks(md_text, for_notion=not args.raw)

    # 篩選
    if args.filter:
        blocks = filter_blocks(blocks, args.filter)
        print(f"篩選 type={args.filter}: {len(blocks)} 個 blocks\n")

    # 輸出
    if args.json:
        print(json.dumps(blocks, ensure_ascii=False, indent=2))
    else:
        print_summary(blocks)


if __name__ == "__main__":
    main()
