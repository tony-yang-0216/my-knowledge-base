"""Gemini AI integration for knowledge organization."""

import re
import json
from clients import get_gemini_client
from constants import GEMINI_MODEL
from categories import get_categories_prompt
from prompts import build_organize_prompt


def organize_with_ai(raw_text):
    client = get_gemini_client()
    categories_text = get_categories_prompt()
    prompt = build_organize_prompt(raw_text, categories_text)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    json_str = response.text.strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: content 欄位的 Markdown 可能破壞 JSON 結構，
        # 因為 Gemini 回傳的 content 含有未轉義的換行、引號等字元，
        # 導致 json.loads 無法解析。此處用 regex 手動提取各欄位。
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
