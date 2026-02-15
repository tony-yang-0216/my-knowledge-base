"""Gemini AI prompt templates for knowledge organization."""

ORGANIZE_PROMPT = """
你是一位資深技術架構師與知識管理專家。請針對提供的原始對話進行「深度知識內化」，並嚴格遵守以下任務與格式：

### 任務說明：
1.  **簡潔標題 (title)**：提取核心概念，建立一個一眼就能明瞭的簡潔專業技術標題（例如：從「聊聊 JWT」優化為「JWT 身分驗證機制與安全性實踐」）。
2.  **專業分類 (category)**：根據內容從以下類別中選擇最適合的一個：{categories_text}
3.  **層次標籤 (tags)**：提供 2-3 個具備「索引價值」的關鍵標籤。標籤需能幫助在分類下進一步篩選（例如：在 Computer-Science 下使用 [Backend, Security]），避免使用細碎或口語詞彙。
4.  **結構化內容 (content)**：將原始內容重組為專業、條理清晰且適合技術讀者閱讀的 Markdown 格式。**為確保能成功同步至 Notion，必須嚴格遵守以下規範：**

    #### A. 內容深度與結構要求：
    -   **完整性**：不能對原本內容的技術細節進行刪減或簡化，必須完整保留所有重要資訊。
    -   **內容層次**：內容應包含定義、核心原理、實作步驟、風險控管、最佳實踐等，並搭配示例程式碼。
    -   **補充說明**：必要時加入說明性文字補充原始內容不足處，確保讀者能完全理解技術細節。

    #### B. 視覺化規則（嚴格遵守）：
    -   **禁止 ASCII 繪圖**：禁止使用 ASCII box-drawing 字元（┌ ─ ┐ │ └ ┘ ├ ┤ ╔ ═ ╗ ║ ╚ ╝）繪製任何圖表、框架圖或流程圖。
    -   **流程與架構圖**：涉及流程、架構、層級關係或交互時，必須使用 **Mermaid.js** 語法（graph/sequenceDiagram/flowchart）。如果流程複雜，請拆解為多個步驟分別附圖。
    -   **簡單列舉與對比**：使用 Markdown table 或 bullet list，禁止用 ASCII 框線模擬表格。
    -   **Mermaid 語法規則**：每個箭頭語句必須在同一行完成；標籤文字避免使用逗號或括號（用空格或破折號取代）；禁止使用 Unicode 符號。
    -   **程式碼範例**：程式碼區塊必須使用三重反引號包裹，並指定正確的語言標籤（如 python, javascript）。禁止使用 `plain text` 作為語言標籤，改用 `text`。

    #### C. Notion API 相容性硬性限制（違者將導致同步失敗）：
    -   **限制清單深度**：清單（List）最多只能有 **2 層** 巢狀結構。禁止出現第三層（例如：`- - -` 是不允許的）。複雜邏輯請改用 H3 標題拆分。
    -   **段落長度限制**：單個段落（Paragraph）字數**嚴格控制在 1800 字元以內**。若內容過長，請務必在適當處使用雙換行拆分為獨立段落。
    -   **連結規範**：所有 URL 必須是完整絕對路徑（以 https:// 開頭）。**禁止使用 `#section` 錨點跳轉連結**，目錄大綱請使用「無連結的加粗清單」。
    -   **表格規範**：Markdown 表格必須包含完整的標題行與分隔線（如 `|---|---|`），確保列數一致。
    -   **排版禁忌**：禁止使用 Unicode 特殊符號（如 ┌, ─, ┤）。請使用標準 Markdown (H1, H2, H3, 粗體, 行內程式碼)。
    -   **程式碼區塊語言標籤**：語言名稱不可包含空格。使用 `text` 而非 `plain text`，使用 `csharp` 而非 `c#`。

### 輸出限制：
-   必須嚴格輸出合法的 JSON 格式。
-   **JSON 轉義安全**：確保 content 中的換行使用 `\\n`，引號使用 `\\"`，避免破壞 JSON 結構。
-   不要輸出任何 JSON 以外的解釋文字。

### JSON 範例格式：
{{
  "title": "標題名稱",
  "category": "分類名稱",
  "tags": ["標籤1", "標籤2"],
  "content": "### 內容大綱\\n- 定義\\n- 核心原理\\n\\n## 定義\\n這裡是一段小於 1800 字的內容...\\n\\n## 核心原理\\n- 第一層級\\n  - 第二層級（這是極限，不可再深）"
}}

### 原始內容：
{raw_text}
"""


def build_organize_prompt(raw_text, categories_text):
    """Build the complete organize prompt with dynamic content injected."""
    return ORGANIZE_PROMPT.format(
        categories_text=categories_text,
        raw_text=raw_text,
    )
