---
title: "Claude Code CLI - 企業級 Git Repo 學習與開發完整指南"
category: "15-Dev-Tools"
tags: ["Claude-Code", "Git-Workflow", "Token-Optimization"]
updated: "2026-02-18"
---

# Claude Code CLI - 企業級 Git Repo 學習與開發完整指南

## 目錄
- [1. 核心概念: Context Window 與 Token 心態](#1-核心概念-context-window-與-token-心態)
    - [1.1. Context Window 是你最重要的資源](#11-context-window-是你最重要的資源)
    - [1.2. Token 節省的核心心態](#12-token-節省的核心心態)
- [2. 全域環境設定 (一台電腦只做一次)](#2-全域環境設定-一台電腦只做一次)
    - [2.1. 安裝 Claude Code 與相依工具](#21-安裝-claude-code-與相依工具)
    - [2.2. 全域安全設定 ~/.claude/settings.json](#22-全域安全設定-claudesettingsjson)
    - [2.3. 全域 CLAUDE.md - 個人風格與技術背景](#23-全域-claudemd---個人風格與技術背景)
    - [2.4. 全域 Custom Commands](#24-全域-custom-commands)
- [3. 專案級設定 (每個 Repo 做一次)](#3-專案級設定-每個-repo-做一次)
    - [3.1. 一鍵生成 CLAUDE.md 與 docs 分層](#31-一鍵生成-claudemd-與-docs-分層)
    - [3.2. 專案權限設定 .claude/settings.json](#32-專案權限設定-claudesettingsjson)
    - [3.3. 專案 Custom Commands 部署腳本](#33-專案-custom-commands-部署腳本)
- [4. 學習階段: 理解陌生 Repo](#4-學習階段-理解陌生-repo)
    - [4.1. Onboard 流程與持久化](#41-onboard-流程與持久化)
    - [4.2. 提問策略: 由大到小](#42-提問策略-由大到小)
- [5. 開發階段: 高效寫 Code](#5-開發階段-高效寫-code)
    - [5.1. Plan Mode - 先想再做](#51-plan-mode---先想再做)
    - [5.2. 精準指令與 Sub-agents](#52-精準指令與-sub-agents)
    - [5.3. Sub-agent 使用原則](#53-sub-agent-使用原則)
- [6. Review 與 Commit 階段](#6-review-與-commit-階段)
    - [6.1. 自我 Code Review /review](#61-自我-code-review-review)
    - [6.2. 審查同事的 PR](#62-審查同事的-pr)
    - [6.3. Commit 規範 /commit](#63-commit-規範-commit)
    - [6.4. 開 PR 的完整流程](#64-開-pr-的完整流程)
- [7. Token 節省實戰技巧](#7-token-節省實戰技巧)
    - [7.1. 黃金法則速查表](#71-黃金法則速查表)
    - [7.2. Session 管理心法](#72-session-管理心法)
    - [7.3. Model 切換策略](#73-model-切換策略)
- [8. 完整工作流程總覽: 常見場景](#8-完整工作流程總覽-常見場景)
    - [8.1. 場景 A: 第一天加入新專案](#81-場景-a-第一天加入新專案)
    - [8.2. 場景 B: 日常開發 Feature](#82-場景-b-日常開發-feature)
    - [8.3. 場景 C: 修 Bug (已知位置)](#83-場景-c-修-bug-已知位置)
    - [8.4. 場景 D: 修 Bug (未知位置)](#84-場景-d-修-bug-未知位置)
    - [8.5. 場景 E: Review 同事的 PR](#85-場景-e-review-同事的-pr)
    - [8.6. 場景 F: 大規模重構](#86-場景-f-大規模重構)
    - [8.7. 場景 G: 接手遺留系統 (Legacy Code)](#87-場景-g-接手遺留系統-legacy-code)
    - [8.8. 每日流程速查圖](#88-每日流程速查圖)

---

## 1. 核心概念: Context Window 與 Token 心態

### 1.1. Context Window 是你最重要的資源

Claude Code 和一般聊天 AI 最大的差異在於: 它能直接讀取你的檔案、執行指令、修改程式碼。但它有一個關鍵限制 -- context window (上下文視窗)，可以想像成電腦的 RAM:

- 每一次對話、每讀一個檔案、每執行一個指令的輸出，都會佔用 context
- 當 context 接近滿載時，Claude 會開始 "遺忘" 早期的指令，導致回答品質下降
- 管理 context = 管理你與 Claude 合作的品質與成本

### 1.2. Token 節省的核心心態

把 token 想成一種貨幣。省 token 不是小氣，而是為了:

- 讓 Claude 在一個 session 內能做更多事
- 減少 Claude "失憶" 導致的重工
- 在公司的使用額度內最大化產出

核心原則: **給 Claude 精確的資訊，而不是讓它自己去翻遍整個 repo 找答案。**

---

## 2. 全域環境設定 (一台電腦只做一次)

這些設定跟著你的電腦走，所有 repo 都會生效。

完整的全域設定檔案可參考: https://github.com/tony-yang-0216/claude-config/tree/main/global-config

### 2.1. 安裝 Claude Code 與相依工具

```bash
# Claude Code (推薦官方腳本, 支援自動更新)
curl -fsSL https://claude.ai/install.sh | bash

# 驗證
claude --version

# GitHub CLI (PR/Review 功能需要)
brew install gh
gh auth login
```

首次執行 `claude` 會引導登入。登入選項: Claude Pro/Max 訂閱帳號，或 Claude Console API (企業可能透過 AWS Bedrock 提供)。

### 2.2. 全域安全設定 ~/.claude/settings.json

保護電腦上所有機密目錄，所有專案 session 都會套用:

```json
{
  "preferences": {
    "defaultModel": "sonnet"
  },
  "permissions": {
    "deny": [
      "Read(~/.ssh/**)",
      "Read(~/.aws/**)",
      "Read(~/.gnupg/**)",
      "Read(~/.kube/**)",
      "Read(~/.docker/**)",
      "Read(~/.npmrc)",
      "Read(~/.netrc)",
      "Read(~/.config/gh/**)"
    ]
  }
}
```

defaultModel 設為 sonnet 避免日常開發不小心燒 opus 額度。deny 清單先手動加上已知的機密路徑，設定完成後可以讓 Claude 在專案目錄內掃描是否還有漏網之魚 (但不要讓它掃整台電腦)。

### 2.3. 全域 CLAUDE.md - 個人風格與技術背景

存放在 `~/.claude/CLAUDE.md`，所有專案 session 自動載入。這份檔案定義你的溝通偏好和技術背景，讓 Claude 在任何 repo 中都知道你是誰:

```markdown
# SWE Global Rules

## Response Style
- 語言：回覆使用繁體中文，程式碼註解與系統 Log 使用英文。
- 精簡原則：禁止複述問題、禁止開場白、禁止結尾問候語。
- 知識過濾：回答盡量精簡，避免重複解釋已問過的概念或基礎操作。
  對 Infra/Backend 可以用 Senior 程度溝通；不熟悉的領域請多給 context。
- 決策建議：針對 EKS、Auth、Azure 等複雜架構，直接給出最佳實踐方案。

## Coding Style (Context-Aware)
- 非同步處理：優先使用 async/await。
- 命名規範：Python 遵循 PEP 8 使用 snake_case；Web/JSON 預設 camelCase。
- 強健性：錯誤處理必須明確，禁止 silent catch 或空的 except 區塊。
- 基礎設施：處理 YAML 或 Helm 模板時，保持與現有檔案命名慣例一致。

## Execution & Token Saving
- 檔案操作：讀取前優先使用已知路徑。不確定時先 ls 確認結構，禁止盲目搜尋。
- 自動化執行：唯讀操作 (ls, cat, git status) 不需詢問；
  具變動性的操作 (rm, git push) 必須經過確認。
- 流程優化：不重述問題，直接產出解決方案、代碼或執行結果。

## Technical Stack Context
- Backend: FastAPI, Django, Redis.
- Infra: EKS, K8s, Helm, Prometheus.
- Auth: Auth0, Keycloak.
- Tooling: Azure, MS Teams, Notion, Getoutline.
```

關鍵設計: Technical Stack Context 讓 Claude 在你問 K8s 問題時直接用 Helm 語境回答，不會先問 "你用什麼部署工具"。換電腦時只需調整這個段落。全域 CLAUDE.md 建議控制在 50 行以內，因為每個 session 都會載入。

### 2.4. 全域 Custom Commands

存放在 `~/.claude/commands/`，所有專案都能用:

**`~/.claude/commands/init-repo.md` - 一鍵初始化專案 (最重要)**

```markdown
# Task: Initialize Project for Claude Code

請深入掃描 Repo 並自動執行必要的 ls 與 cat 操作，隨後生成以下檔案：

## 1. CLAUDE.md (專案根目錄)
內容需包含：
1. 專案概述與技術棧：一句話描述目標與核心技術。
2. 常用指令：列出精確的 Build, Dev, Test, Lint 指令（請檢查 package.json 或 Makefile）。
3. 目錄結構：僅列出主要目錄及其權責。
4. 代碼風格慣例：分析變數命名、匯入順序、專案中常見的錯誤處理模式。
5. 架構摘要：一句話說明資料流向，並指向 docs/ 下的詳細文件。

嚴格限制：
- 內容控制在 100-150 行內。
- 優先使用 Markdown 表格或條列式以節省空間。
- 只包含不會頻繁變動的資訊。會變動的細節 (TODO, 當前 Bug) 不應出現。

## 2. docs/ARCHITECTURE.md
將複雜的架構資訊拆到此檔案：
- 模組間的依賴關係與資料流 (用 Mermaid 圖)
- 每個核心模組的職責與 public API
- 資料庫 schema 摘要 (如果有)
- 關鍵設計決策與原因

## 3. CLAUDE.md 中加入指引
在 CLAUDE.md 的對應段落加上：
- `Architecture details: docs/ARCHITECTURE.md`
- 以及其他拆分出去的 docs 檔案路徑

確保以後 Claude 在需要深入資訊時知道去哪裡找。
```

**`~/.claude/commands/commit.md` - 標準化 Commit**

```markdown
# Task: Generate Conventional Commit

請分析當前 git staged (暫存區) 的變動，並直接產出一個符合 Conventional Commits 規範的提交指令：

1. Type 規範 (嚴格執行)：
   - build, ci, docs, feat, fix, perf, refactor, revert, style, test, chore

2. 格式要求：
   - 格式：<type>(<scope>): <description>
   - Description：使用英文 (Imperative mood)，簡潔且標準化。
   - 禁止出現任何與 Claude 或 AI 協作相關的文字。

3. 內容架構：
   - 標題：描述改動的核心。
   - 正文 (Body)：使用 Bullet Points 摘要說明變動目的與核心邏輯。

4. 原子性檢查：
   - 若 staged 變動包含多個不相關的邏輯，主動提醒拆分，並建議每個 commit 的範圍。

5. 輸出規範：
   - 僅產出 `git commit -m "標題" -m "點列式內容"` 指令。
```

**`~/.claude/commands/explain.md` - 快速解釋程式碼**

```markdown
# Task: Code Explanation
# Input: $ARGUMENTS

用繁體中文解釋指定程式碼的運作邏輯：
1. 這段 code 的目的
2. 關鍵的設計決策
3. 可能的 edge case
```

**`~/.claude/commands/gentest.md` - 產生測試**

```markdown
# Task: Generate Unit Tests
# Input: $ARGUMENTS

為指定目標生成單元測試：
- 參照專案現有的測試風格與框架
- 覆蓋 happy path + edge case + error case
- 測試命名用 describe/it 風格描述行為
```

全域設定完成後的完整結構:

```text
~/.claude/
├── settings.json           <-- 全域安全與模型偏好
├── CLAUDE.md               <-- 個人風格與技術背景
└── commands/
    ├── init-repo.md        <-- /init-repo 初始化專案
    ├── commit.md           <-- /commit 標準化提交
    ├── explain.md          <-- /explain 解釋程式碼
    └── gentest.md          <-- /gentest 產生測試
```

---

## 3. 專案級設定 (每個 Repo 做一次)

完整的專案級設定範例可參考: https://github.com/tony-yang-0216/claude-config/tree/main/project-config

### 3.1. 一鍵生成 CLAUDE.md 與 docs 分層

Clone 新 repo 後，用全域指令一鍵完成:

```bash
cd your-project
claude
```

```text
> /init-repo
```

Claude 會自動掃描專案結構、讀取配置文件，生成:

```text
<project-root>/
├── CLAUDE.md                  <-- 精簡版 (100-150 行, 自動載入)
└── docs/
    └── ARCHITECTURE.md        <-- 詳細架構 (需要時才讀取)
```

CLAUDE.md 中會包含指向 docs/ 的指引，例如:

```markdown
## Architecture
Pattern: Controller -> Service -> Repository
Full details: docs/ARCHITECTURE.md
```

這樣 Claude 在大多數 session 中只載入精簡的 CLAUDE.md，只在需要深入資訊時才去讀 docs/ 下的文件，大幅減少每次 session 的基礎 token 消耗。

生成後務必 review 一下內容是否正確，然後 commit 到 git 讓團隊共用。

### 3.2. 專案權限設定 .claude/settings.json

commit 到 git，團隊共用的安全規則。採用三層權限模型 -- allow (自動執行)、deny (完全禁止)、ask (每次詢問確認):

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Grep",
      "LS",
      "Bash(npm run test:*)",
      "Bash(npm run lint:*)",
      "Bash(npm run build)"
    ],
    "deny": [
      "Read(./.env*)",
      "Read(./secrets/**)",
      "Read(./**/credentials*)",
      "Read(~/.ssh/**)",
      "Bash(rm -rf /)",
      "Bash(git config --global:*)"
    ],
    "ask": [
      "WebFetch",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(npm install:*)",
      "Bash(pip install:*)",
      "Bash(npm run dev)"
    ]
  }
}
```

三層權限的設計邏輯:

- **allow**: 唯讀操作和跑測試/lint/build，這些不會改變系統狀態，放行讓 Claude 自動執行以節省互動次數
- **deny**: 讀取機密檔案、破壞性指令、修改全域 git config，這些完全禁止沒有例外
- **ask**: 網路請求、安裝套件、啟動 dev server，這些有潛在風險但有時必要，讓 Claude 每次執行前詢問你確認

設定後可以讓 Claude 在專案目錄內用 Grep 搜尋可能包含 secret/password/api_key/token 的檔案名稱 (不讀內容)，補上漏掉的 deny 路徑。

### 3.3. 專案 Custom Commands 部署腳本

以下腳本一鍵部署專案級的指令集，commit 到 git 讓團隊共用。執行一次即可:

```bash
#!/bin/bash
mkdir -p .claude/commands
mkdir -p docs

echo "Deploying project-scoped Claude commands..."

# --- /onboard (專案入職與持久化知識) ---
cat > .claude/commands/onboard.md << 'EOF'
# Task: Project Onboarding & Persistence

請分三階段執行，並將所有進度實體化記錄於檔案中：

### Phase 1: 掃描與同步
- 檢查是否存在 docs/CODEBASE.md。
- 若已存在：讀取並驗證與目前代碼是否一致，指出差異點。
- 若不存在：掃描目錄結構、package.json、CLAUDE.md，建立初版 docs/CODEBASE.md。
- 匯報：簡述目前對技術棧與架構的理解。

### Phase 2: 邏輯深挖
- 追蹤核心資料流 (Data Flow) 與關鍵進入點。
- 更新 docs/CODEBASE.md，加入模組權責與關鍵商務邏輯。
- 提問：條列不確定或代碼中模糊的地方。請等待回覆再繼續。

### Phase 3: 知識封存
- 根據回覆，產出 docs/ONBOARDING.md 作為新人指南。
- 確保以後即使執行 /clear，只要讀取 docs/CODEBASE.md 就能立刻接手任務。
EOF

# --- /task (任務分析與實作計畫) ---
cat > .claude/commands/task.md << 'EOF'
# Task: Task Analysis & Implementation Plan
# Input: $ARGUMENTS

步驟：
1. 背景檢索：閱讀 CLAUDE.md 與 docs/CODEBASE.md。
2. 影響分析：針對 $ARGUMENTS 的需求，識別需修改的檔案清單。
3. 實作提案：給出邏輯步驟 (不直接寫 code)，包含對現有架構的改動。
4. 規範檢查：確保計畫符合 CLAUDE.md 的風格要求。
5. 確認：等待確認 (或輸入 "GO") 後再開始實作。
EOF

# --- /bug (問題診斷與修復) ---
cat > .claude/commands/bug.md << 'EOF'
# Task: Bug Diagnosis & Root Cause Analysis
# Input: $ARGUMENTS

步驟：
1. 重現分析：分析錯誤訊息或異常行為描述。
2. 代碼搜尋：使用 grep 或 ls 定位可能的出錯點。
   若需大範圍搜尋 (超過 3 個檔案)，使用 sub-agent 執行，僅回傳摘要至主 session。
3. 原因解釋：說明為何會發生此問題 (Root Cause)。
4. 修復建議：提出修復方案，並檢查是否會對其他模組造成 Side Effect。
EOF

# --- /review (資深工程師等級的程式碼審查) ---
cat > .claude/commands/review.md << 'EOF'
# Task: Senior Code Review

你是一位擁有 10 年以上 Production 系統經驗的資深軟體工程師。

## Context Detection
- 若透過 --from-pr 啟動：自動執行 gh pr diff 取得該 PR 的完整 diff 作為審查範圍。
- 若在一般 session 中：審查 git staged changes (git diff --staged)。
- 若指定 $ARGUMENTS：審查指定的檔案或路徑。

## Review Focus
1. Logic & Safety：識別 bug、不正確的邏輯、不安全的操作、race condition、
   缺少的驗證、edge-case 失敗。
2. Code Quality：評估可讀性、結構、可維護性、命名、模組化，
   以及是否符合 CLAUDE.md 定義的慣例。
3. Stability & Performance：確保 API 穩定性與效能約束。

## Execution Rules
- Scope Restriction：嚴格針對審查範圍操作。不引入新功能或無關的重構。
- Minimalist Fixes：修復保持最小化但正確。優先小範圍精準修改，避免全面重寫。
- Justification：若重寫必要，必須清楚說明原始設計為何不足。
- Concrete Solutions：指出問題時，必須同時提供具體的修復程式碼。
- Style Consistency：維持現有 codebase 的風格慣例。
- No Placeholders：禁止輸出 "TODO"，提供完整可運作的程式碼。
- Non-Destructive：提供修正後的程式碼，但不自動加入 git stage。

## Output Format
- 每個問題包含：問題描述、嚴重程度 (Critical/Warning/Info)、修正程式碼。
- 若缺少架構或標準的上下文，基於業界最佳實踐推斷，並明確說明假設。
- 最後檢查：是否需要更新 docs/CODEBASE.md。
EOF

# --- /pr-desc (PR 描述產生器) ---
cat > .claude/commands/pr-desc.md << 'EOF'
# Task: Pull Request Description Generator

分析目前 branch 相對於 main 的所有變更，產出：

## Summary
一句話說明核心變更。

## Changes
檔案路徑與變更邏輯摘要。

## Test Plan
如何驗證變更 (包含指令或手動測試步驟)。

## Risks
潛在風險或需要 Reviewer 特別關注的地方。
EOF

echo "Done! Project commands deployed to .claude/commands/"
echo "Run /onboard to start exploring."
```

部署後的專案完整結構:

```text
<project-root>/
├── .claude/
│   ├── settings.json           <-- 專案權限 (commit to git)
│   └── commands/
│       ├── onboard.md          <-- /onboard 入職與持久化
│       ├── task.md             <-- /task 任務分析
│       ├── bug.md              <-- /bug 問題診斷
│       ├── review.md           <-- /review 資深審查
│       └── pr-desc.md          <-- /pr-desc PR 描述
├── CLAUDE.md                   <-- AI 入職手冊 (commit)
├── docs/
│   ├── ARCHITECTURE.md         <-- 詳細架構
│   ├── CODEBASE.md             <-- /onboard 產出的知識庫
│   └── ONBOARDING.md           <-- /onboard 產出的新人指南
├── src/
└── ...
```

---

## 4. 學習階段: 理解陌生 Repo

### 4.1. Onboard 流程與持久化

/onboard 的核心設計: docs/CODEBASE.md 是跨 session 的記憶體。

```text
# 第一次: 從零探索, 生成知識庫
> /onboard
# Claude 掃描 -> 提問 -> 你回答 -> 生成 CODEBASE.md + ONBOARDING.md

# 第 N 次: 增量更新
> /onboard
# Claude 讀取既有 CODEBASE.md -> diff 出差異 -> 提問 -> 更新
```

這比每次都重新探索整個 repo 省非常多 token。即使 `/clear` 後，Claude 只要讀取 CODEBASE.md 就能立刻恢復 context。

```mermaid
flowchart TD
    A[clone repo] --> B[/init-repo 生成 CLAUDE.md + docs]
    B --> C[/onboard 第一次探索]
    C --> D[Claude 提問 - 你回答]
    D --> E[生成 CODEBASE.md + ONBOARDING.md]
    E --> F{日後再次 /onboard}
    F --> G[讀取既有 CODEBASE.md]
    G --> H[驗證是否過時 - 增量更新]
    H --> I[知識持續累積]
```

### 4.2. 提問策略: 由大到小

遵循 macro to micro 原則，每一層用 `/clear` 隔開以節省 token:

**第一層: 全局架構**

```text
> 這個專案的整體架構是什麼? 主要模組之間的關係?
> 一個請求從進入到回傳 response 的完整資料流?
```

```text
> /clear
```

**第二層: 模組理解**

```text
> src/services/auth/ 這個模組負責什麼? 和哪些模組互動?
```

```text
> /clear
```

**第三層: 實作細節**

```text
> 看 src/services/auth/jwt.ts 第 45-80 行,
> refreshToken 函式如何處理 token 過期?
```

省 token 提問技巧: 已知檔案路徑時直接告訴 Claude。一次問一個具體問題。換主題一定 `/clear`。

---

## 5. 開發階段: 高效寫 Code

### 5.1. Plan Mode - 先想再做

在 Claude Code 中按 **Shift+Tab 兩次** 進入 Plan Mode。讓 Claude 先推理規劃再寫 code，大幅減少反覆修改的浪費。

```text
> [Shift+Tab x2 進入 Plan Mode]
> /task PROJ-789 新增使用者資料匯出 API 支援 CSV 和 JSON
```

Plan Mode 搭配 /task 指令，Claude 會先讀取 CLAUDE.md 和 CODEBASE.md，分析影響範圍，給出計畫後等你確認才開始寫 code。

**Model 切換設定 (Plan Mode 用 Opus 推理, 寫 Code 用 Sonnet):**

```text
# 方式一: session 內切換 (推薦, 按需使用)
> /model opusplan

# 方式二: 環境變數 (永久生效)
# 加到 ~/.bashrc 或 ~/.zshrc
export CLAUDE_CODE_PLAN_MODEL=opus
export CLAUDE_CODE_MODEL=sonnet
```

不是每次 Plan 都需要 Opus。簡單 feature 用 Sonnet plan 就夠了，複雜架構決策才切 opusplan。

確認計畫後:

```text
> [退出 Plan Mode]
> GO
```

### 5.2. 精準指令與 Sub-agents

精準的 prompt 是省 token 最有效的手段:

| 壞的 Prompt (燒 token) | 好的 Prompt (省 token) |
|---|---|
| "幫我修 bug" | "src/controllers/user.ts L67 的 getUserById 在 userId 為 null 時回傳 500, 應回傳 400" |
| "加一個新功能" | "在 src/routes/v2/ 新增 export.ts, 參照 src/routes/v2/import.ts 的 pattern" |
| "看看有沒有問題" | "對 src/services/payment.ts L30-50 做 null safety 檢查" |

### 5.3. Sub-agent 使用原則

Sub-agent 在獨立 context 中執行，不污染主 session，但本身也消耗 token。

| 情境 | 建議 | 原因 |
|---|---|---|
| 探索型研究 (讀很多檔案) | 用 sub-agent | 避免大量檔案內容污染主 context |
| 修一個已知檔案的 bug | 不用 | 直接在主 session 做更快更省 |
| 平行處理多個獨立任務 | 用多個 agent | 各自隔離互不干擾 |
| 簡單提問 | 絕對不用 | 啟動 agent 本身就有 overhead |

判斷原則: 如果任務需要讀超過 3 個檔案來找答案，考慮用 sub-agent。已知答案在哪就直接在主 session 做。

```text
# 壞: 範圍模糊
> 用 sub-agent 研究一下我們的 auth 系統

# 好: 精確範圍 + 預期輸出
> 用 sub-agent 只看 src/services/auth/ 和 src/middleware/auth.ts,
> 回答: refresh token 的流程是什麼? 回傳 3-5 句摘要就好。
```

---

## 6. Review 與 Commit 階段

### 6.1. 自我 Code Review /review

在 commit 之前，用 /review 讓 Claude 以資深工程師的標準審查你的 staged changes:

```text
# 審查目前的 staged changes
> /review

# Claude 會:
# 1. 偵測 context (staged changes / PR diff / 指定檔案)
# 2. 檢查 Logic & Safety, Code Quality, Stability & Performance
# 3. 每個問題附上嚴重程度 (Critical/Warning/Info) 和修正程式碼
# 4. 提醒是否需要更新 docs/CODEBASE.md
```

/review 的設計原則: Claude 只提供修正後的程式碼讓你手動 apply，不會自動改你的檔案或加入 git stage (Non-Destructive)，確保你保有完全控制權。

### 6.2. 審查同事的 PR

/review 的 Context Detection 會自動判斷審查範圍，三種用法:

```bash
# 用法一: --from-pr (推薦, 不需 checkout)
# Claude 自動透過 gh pr diff 取得變更, 本地不需要 pull
claude --from-pr 456
```

```text
> /review
```

```bash
# 用法二: 手動 checkout (需要本地跑測試驗證時)
gh pr checkout 456
claude
```

```text
> /review
```

```text
# 用法三: 指定特定檔案深入審查
> /review src/services/payment.ts
```

針對可疑的地方追問:

```text
> src/services/payment.ts L89-102 的 Stripe webhook handler,
> 重複的 event 有做冪等處理嗎?
```

Session 會自動綁定到 PR。同事修改後需要 re-review 時，`claude --from-pr 456` 恢復 context 繼續討論。

### 6.3. Commit 規範 /commit

使用全域的 /commit 指令 (定義在 `~/.claude/commands/commit.md`):

```text
# 先 stage 你的變更
> git add src/services/export.ts src/tests/export.test.ts

# 用 /commit 產生標準化 commit
> /commit

# Claude 會:
# 1. 分析 staged changes
# 2. 檢查原子性 (如果混了不相關的改動會提醒拆分)
# 3. 產出 Conventional Commits 格式的 git commit 指令
# 4. 你確認後執行
```

輸出範例:

```bash
git commit -m "feat(export): add user data export endpoint" -m "- Add ExportService with CSV/JSON formatters
- Register GET /api/v2/users/export route
- Add input validation for format parameter"
```

好的 commit 習慣 -- 小步快跑:

```text
> 完成 service layer -> /commit
> 完成 controller -> /commit
> 完成 tests -> /commit
```

頻繁 commit 的好處: 如果 Claude 後續走偏，你可以 `/rewind` 回到上一個 checkpoint，而不是從頭來過。也讓你能大膽 `/clear` 不怕丟失進度。

### 6.4. 開 PR 的完整流程

```text
# Step 1: 確認所有變更都已 commit
> git status

# Step 2: 產生 PR description
> /pr-desc

# Step 3: 用 Claude 建立 PR
> 建立 PR, title 用 /pr-desc 產生的 summary,
> 加上 label "needs-review", assign 給我自己。

# 或者使用內建的一鍵指令 (如果有安裝 commit-commands plugin):
> /commit-push-pr
```

---

## 7. Token 節省實戰技巧

### 7.1. 黃金法則速查表

| 技巧 | 節省幅度 | 說明 |
|---|---|---|
| `/clear` 切換任務 | 50-70% | 不同任務之間必須清 context |
| 精簡 CLAUDE.md + 分層 docs | 30-40% | CLAUDE.md 100-150 行, 細節拆到 docs/ |
| 指定檔案路徑 | 20-30% | 避免 Claude 全 repo 搜尋 |
| Sub-agents 做研究 | 40-60% | 大量讀檔的任務隔離到獨立 context |
| `/compact` 壓縮 | 20-30% | 長 session 在 70% 容量時手動壓縮 |
| Model 切換 | 50-80% | 簡單任務用 Haiku, 日常用 Sonnet |
| 頻繁 /commit | 間接節省 | 可以大膽 /clear 不怕丟失進度 |
| /onboard 持久化 | 大幅節省 | 不用每次重新探索整個 repo |

### 7.2. Session 管理心法

```mermaid
flowchart LR
    A[開始任務 A] --> B[完成任務 A]
    B --> C{下一步?}
    C -->|切換任務| D[/clear]
    D --> E[開始任務 B]
    C -->|context 太長| F[/compact]
    F --> G[繼續任務 A]
    C -->|繼續相同任務| G
    C -->|今天結束| H[/resume 命名 session]
```

- **一個 session 做一件事**: 不要混合不同任務
- **失敗兩次就重來**: Claude 修了兩次還不對，`/clear` 重寫更好的 prompt
- **善用 `/resume`**: 給 session 命名，明天可以接續

```text
# 為 session 命名
> /resume  # 打開 picker, 按 R 重命名為 "feat-export-api"

# 隔天恢復
> claude
> /resume  # 選擇 "feat-export-api" 繼續
```

自訂 compact 保留重點:

```text
> /compact 保留: 已修改的檔案清單、測試指令、目前的實作進度
```

### 7.3. Model 切換策略

```text
> /model sonnet      # 80% 日常開發 (建議預設)
> /model opus        # 複雜架構決策、大規模重構
> /model haiku       # 簡單語法問題、格式化、快速查詢
> /model opusplan    # Plan Mode 用 Opus, 寫 code 用 Sonnet
```

---

## 8. 完整工作流程總覽: 常見場景

### 8.1. 場景 A: 第一天加入新專案

你剛 clone 了一個完全陌生的大型 repo。

```bash
git clone git@github.com:company/big-project.git
cd big-project
claude
```

```text
# 1. 一鍵初始化 (生成 CLAUDE.md + docs/ARCHITECTURE.md)
> /init-repo

# 2. review 生成的檔案, 確認正確後 commit
> git add CLAUDE.md docs/
> /commit

# 3. 系統化 onboard (生成 CODEBASE.md + ONBOARDING.md)
> /onboard
# Claude 探索 -> 提問 -> 你回答 -> 知識封存

# 4. 由大到小深入學習
> /clear
> 我被分配到 payment 相關的工作,
> 解釋 src/services/payment/ 的架構和主要流程
```

結果: 半天內建立完整認知地圖，並產出可供團隊使用的文件。

### 8.2. 場景 B: 日常開發 Feature

Ticket PROJ-789: "新增使用者資料匯出 API, 支援 CSV/JSON"。

```bash
git checkout -b feature/PROJ-789-user-export
claude
```

```text
# 1. Plan Mode 規劃
> [Shift+Tab x2]
> /task PROJ-789 新增 /api/v2/users/export 支援 CSV 和 JSON

# 2. 確認計畫, 開始實作
> [退出 Plan Mode]
> GO

# 3. 小步快跑
> /commit
# "feat(export): add ExportService with CSV/JSON formatters"

> /commit
# "feat(export): add export controller and route"

# 4. 產生測試
> /gentest src/services/export.service.ts
> /commit
# "test(export): add unit tests for ExportService"

# 5. 自我審查
> /review

# 6. 開 PR
> /pr-desc
> 建立 PR, 加上 label "needs-review"

# 7. 清 context 做下一件事
> /clear
```

### 8.3. 場景 C: 修 Bug (已知位置)

QA 回報: "匯出時 email 欄位為 null 會 500"。你知道問題在哪。

```text
# 直接精準指示, 不需探索
> src/services/export.service.ts 的 formatUserRow 函式約 L45,
> user.email 為 null 時會 crash。
> 加上 null check, email 為空時填入空字串。
> 同時補上對應測試在 tests/export.service.test.ts。

# 確認 + 提交
> npm test
> /commit
# "fix(export): handle null email in user data export"
> git push
```

精準 prompt + 已知路徑 = 最低 token 消耗。

### 8.4. 場景 D: 修 Bug (未知位置)

Production 報錯: "TypeError: Cannot read property 'id' of undefined", 只有 stack trace。

```text
# 用 /bug 指令 (自動判斷是否需要 sub-agent)
> /bug TypeError: Cannot read property 'id' of undefined
> Stack trace: at OrderService.processOrder (src/services/order.ts:123)

# Claude 會:
# 1. 分析 stack trace
# 2. 若需讀超過 3 個檔案, 自動用 sub-agent
# 3. 回傳 root cause + 修復建議

# 確認修復方案後
> 按修復建議修改, 補上測試
> /commit
# "fix(order): add null check for customer in processOrder"
```

### 8.5. 場景 E: Review 同事的 PR

同事開了 PR #456, 改了 payment 相關程式碼。

```bash
# 不需 checkout, Claude 自動取得 PR diff
claude --from-pr 456
```

```text
# 資深等級審查
> /review

# 深入可疑處
> src/services/payment.ts L89-102 的 Stripe webhook handler,
> 重複的 event 有做冪等處理嗎?

# 結束, session 自動綁定 PR #456
# 同事修改後 re-review: claude --from-pr 456
```

### 8.6. 場景 F: 大規模重構

把所有 callback-style DB query 改成 async/await, 影響 30+ 個檔案。

```text
# 1. Plan Mode 規劃分批策略
> [Shift+Tab x2]
> /model opusplan
> 需要把所有 callback-style Sequelize query 重構為 async/await。
> 分析影響範圍, 建議分批策略 (每批 PR 不超過 5 個檔案)。
```

```bash
# 2. 用 Git Worktree 隔離
git worktree add ../project-refactor-batch1 -b refactor/async-batch-1
cd ../project-refactor-batch1
claude
```

```text
# 3. 按批次執行
> 重構第一批: src/services/user.ts 和 src/services/order.ts。
> 每改完一個跑對應測試。

> /commit
> /commit
> /pr-desc
> 建立 PR

# 4. 清 context, 切下一批
> /clear
```

```bash
git worktree add ../project-refactor-batch2 -b refactor/async-batch-2
cd ../project-refactor-batch2
claude
# ... 重複 ...
```

### 8.7. 場景 G: 接手遺留系統 (Legacy Code)

沒文件、測試覆蓋率低的老系統。

```text
# 1. 初始化 + 考古
> /init-repo
> /onboard

# 2. 先建安全網 (補測試)
> /clear
> 為 src/services/billing.ts 的 calculateInvoice 函式補上測試。
> 根據現有程式碼邏輯推斷 expected behavior。
> 覆蓋 happy path + edge case。

> /commit
# "test(billing): add baseline tests for calculateInvoice"

# 3. 理解後再改
> /clear
> /task 在 calculateInvoice 中支援折扣碼

# 4. 實作 + 確認既有測試不壞
> GO
> npm test
> /commit
# "feat(billing): add discount code support to invoice calculation"
```

### 8.8. 每日流程速查圖

```mermaid
flowchart TD
    START[開始工作] --> CHECK{今天做什麼?}

    CHECK -->|新專案| A1[clone + claude]
    A1 --> A2[/init-repo]
    A2 --> A3[/onboard]
    A3 --> A4[由大到小學習]

    CHECK -->|開發 Feature| B1[checkout branch + claude]
    B1 --> B2[Plan Mode + /task]
    B2 --> B3[精準指令實作]
    B3 --> B4[/commit 小步快跑]
    B4 --> B5[/review 自審]
    B5 --> B6[/pr-desc + 開 PR]

    CHECK -->|修 Bug| C1{知道位置?}
    C1 -->|是| C2[精準指令直接修]
    C1 -->|否| C3[/bug 調查]
    C3 --> C2
    C2 --> C4[/commit]

    CHECK -->|Review PR| D1[claude --from-pr N]
    D1 --> D2[/review]
    D2 --> D3[深入可疑處]

    A4 --> END[/clear 切下一個任務]
    B6 --> END
    C4 --> END
    D3 --> END
```

> 請下載此 Artifact 並放入本地 /drafts 資料夾，隨後啟動 New Chat。