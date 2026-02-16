CATEGORIES = {
    "10-Computer-Science": "電腦科學核心知識，包含資料結構、演算法、作業系統、計算機網路、設計模式、程式語言概念等",
    "12-AI-ML": "人工智慧與機器學習，包含 LLM 原理與架構、Prompt Engineering、Token 機制與優化、AI 應用開發、Agent 框架、機器學習基礎概念等",
    "15-Dev-Tools": "開發工具與工作流，包含套件管理器、版本控制、終端工具、編輯器/IDE、容器化、CI/CD 等",
    "20-Finance": "金融與投資相關知識，包含財務分析、投資策略、加密貨幣、總體經濟、個人理財等",
    "30-Lifestyle": "生活風格與個人成長，包含生產力技巧、健康養生、閱讀筆記、旅遊、興趣嗜好等",
    "40-News": "時事新聞與產業趨勢，包含科技動態、產業分析、重大事件摘要等",
    "99-Inbox": "無法明確歸類的內容，待後續整理分類",
}


def get_categories_prompt():
    """產生供 AI prompt 使用的類別說明文字"""
    lines = []
    for name, description in CATEGORIES.items():
        lines.append(f"- **{name}**：{description}")
    return "\n".join(lines)
