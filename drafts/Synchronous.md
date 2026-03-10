# Python 異步物件與 Pytest Mock 完全指南

> 從零開始理解異步程式設計與測試
>
> 適合對象：不熟悉異步程式設計、第一次寫 pytest mock 的開發者

## 目錄
- [Part 1: 同步與異步基礎](#part-1-同步與異步基礎)
- [Part 2: 物件、方法與異步](#part-2-物件方法與異步)
- [Part 3: aiohttp 實戰案例](#part-3-aiohttp-實戰案例)
- [Part 4: Pytest Mock 基礎](#part-4-pytest-mock-基礎)
- [Part 5: Mock 異步上下文管理器](#part-5-mock-異步上下文管理器)
- [Part 6: 常見陷阱與疑問](#part-6-常見陷阱與疑問)
- [Part 7: 完整測試範例](#part-7-完整測試範例)

---

## Part 1: 同步與異步基礎

### 1.1 什麼是同步（Synchronous）？

**立即執行，等待結果，阻塞程式**

```python
import time

def download_file(url):
    """同步函數：下載檔案"""
    print(f"開始下載 {url}")
    time.sleep(2)  # 模擬網路延遲，程式停在這裡等待
    print(f"完成下載 {url}")
    return f"data from {url}"

# 執行
result1 = download_file("http://site1.com")  # 等 2 秒
result2 = download_file("http://site2.com")  # 再等 2 秒
result3 = download_file("http://site3.com")  # 再等 2 秒

# 總共花費：6 秒
```

**執行流程圖**：
```
時間軸：0s -----> 2s -----> 4s -----> 6s

       [下載1]
              等待
                   [下載2]
                          等待
                               [下載3]
                                      等待
                                           完成

CPU:   忙碌   閒置   忙碌   閒置   忙碌   閒置
```

**特徵**：
- 程式會停下來等待每個操作完成
- 一次只能做一件事
- 簡單易懂，但效率低

---

### 1.2 什麼是異步（Asynchronous）？

**發起請求後不等待，繼續執行其他任務**

```python
import asyncio

async def download_file(url):
    """異步函數：下載檔案"""
    print(f"開始下載 {url}")
    await asyncio.sleep(2)  # 模擬網路延遲，但讓出控制權
    print(f"完成下載 {url}")
    return f"data from {url}"

# 執行
async def main():
    # 同時發起 3 個下載
    results = await asyncio.gather(
        download_file("http://site1.com"),
        download_file("http://site2.com"),
        download_file("http://site3.com"),
    )
    return results

# 總共花費：約 2 秒（並發執行）
asyncio.run(main())
```

**執行流程圖**：
```
時間軸：0s -----> 2s

       [下載1]
       [下載2]  ← 三個下載同時進行
       [下載3]
              等待
                   完成

CPU:   忙碌    閒置（但可以處理其他任務）
```

**特徵**：
- `async def` 定義異步函數
- `await` 等待異步操作完成
- 可以並發執行多個任務
- 效率高，但較複雜

---

### 1.3 核心差異對比表

| 特性 | 同步 (Sync) | 異步 (Async) |
|------|-------------|--------------|
| **定義** | `def func()` | `async def func()` |
| **呼叫** | `result = func()` | `result = await func()` |
| **返回** | 直接返回結果 | 返回 coroutine 物件 |
| **等待** | 阻塞（blocking） | 非阻塞（non-blocking） |
| **並發** | ❌ 無法並發 | ✅ 可以並發 |
| **適用場景** | CPU 密集運算 | I/O 密集操作（網路、檔案） |

---

### 1.4 何時使用異步？

**✅ 適合異步的場景**：
- HTTP 請求（呼叫 API、webhook）
- 資料庫查詢
- 檔案讀寫
- 任何需要「等待」的 I/O 操作

**❌ 不適合異步的場景**：
- 純計算（如：排序、加密）
- 簡單的記憶體操作
- 單一任務，沒有並發需求

---

## Part 2: 物件、方法與異步

### 2.1 函數 vs 物件

#### 函數（Function）
```python
def greet(name):
    """一個獨立的函數"""
    return f"Hello {name}"

result = greet("Alice")
```

#### 物件（Object）
```python
class Person:
    """一個類別"""
    def __init__(self, name):
        self.name = name  # 屬性

    def greet(self):
        """物件的方法"""
        return f"Hello {self.name}"

# 創建物件
person = Person("Alice")

# 呼叫物件的方法
result = person.greet()
```

**物件 = 數據（屬性）+ 行為（方法）的組合**

---

### 2.2 同步物件

**所有方法都是同步的**

```python
class FileReader:
    """純同步物件"""

    def __init__(self, path):
        self.path = path

    def read(self):
        """同步方法：阻塞讀取"""
        with open(self.path, 'r') as f:
            return f.read()

    def get_size(self):
        """同步方法：取得檔案大小"""
        import os
        return os.path.getsize(self.path)

# 使用
reader = FileReader("data.txt")
content = reader.read()        # 不需要 await
size = reader.get_size()       # 不需要 await
```

---

### 2.3 異步物件

**所有方法都是異步的**

```python
class AsyncFileReader:
    """純異步物件"""

    def __init__(self, path):
        self.path = path

    async def read(self):
        """異步方法：非阻塞讀取"""
        import aiofiles
        async with aiofiles.open(self.path, 'r') as f:
            return await f.read()

    async def get_size(self):
        """異步方法：非阻塞取得檔案大小"""
        import aiofiles.os
        stat = await aiofiles.os.stat(self.path)
        return stat.st_size

# 使用
reader = AsyncFileReader("data.txt")
content = await reader.read()        # 需要 await
size = await reader.get_size()       # 需要 await
```

---

### 2.4 混合型物件 ⭐（重點）

**同時有同步方法和異步方法**

```python
class MixedObject:
    """混合型物件"""

    def __init__(self, value):
        self.value = value  # 屬性（同步）

    # === 同步方法 ===
    def get_value(self):
        """讀取記憶體中的值 → 同步"""
        return self.value

    def validate(self):
        """純計算 → 同步"""
        if self.value < 0:
            raise ValueError("Value must be positive")

    # === 異步方法 ===
    async def fetch_from_api(self):
        """網路請求 → 異步"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://api.com/{self.value}") as resp:
                return await resp.json()

    async def save_to_db(self):
        """資料庫寫入 → 異步"""
        # 模擬資料庫操作
        await asyncio.sleep(1)
        return "saved"

# 使用
obj = MixedObject(42)

# 同步方法（不需要 await）
value = obj.get_value()
obj.validate()

# 異步方法（需要 await）
data = await obj.fetch_from_api()
result = await obj.save_to_db()
```

---

### 2.5 如何判斷一個方法是同步還是異步？

**看方法的定義**：

```python
class Example:
    def sync_method(self):      # ← 用 def
        return "sync"

    async def async_method(self):  # ← 用 async def
        return "async"

# 使用
obj = Example()
obj.sync_method()        # 同步：直接調用
await obj.async_method() # 異步：需要 await
```

**判斷流程圖**：
```
看到方法調用
    ↓
查看方法定義
    ↓
    ├─ def method()       → 同步方法，不需要 await
    └─ async def method() → 異步方法，需要 await
```

---

## Part 3: aiohttp 實戰案例

### 3.1 aiohttp.ClientSession（異步物件）

```python
import aiohttp

async def example():
    # 創建 ClientSession 物件
    session = aiohttp.ClientSession()

    # === 所有方法都是異步的 ===
    response = await session.get("http://example.com")     # 需要 await
    response = await session.post("http://api.com", json={})  # 需要 await
    await session.close()                                   # 需要 await
```

**為什麼都是異步？** 因為涉及網路 I/O 操作。

---

### 3.2 aiohttp.ClientResponse（混合型物件）⭐

```python
async def example():
    async with session.get("http://example.com") as response:
        # response 是 ClientResponse 物件

        # === 同步屬性/方法（不需要 await）===
        status = response.status           # 讀記憶體
        headers = response.headers         # 讀記憶體
        url = response.url                 # 讀記憶體
        response.raise_for_status()        # 純計算

        # === 異步方法（需要 await）===
        text = await response.text()       # 讀取 response body（I/O）
        json_data = await response.json()  # 讀取並解析 JSON（I/O）
        bytes_data = await response.read() # 讀取 bytes（I/O）
```

---

### 3.3 為什麼 `raise_for_status()` 是同步的？

**看它的實作**：

```python
class ClientResponse:
    def raise_for_status(self):
        """檢查 HTTP 狀態碼"""
        if self.status >= 400:  # self.status 已經在記憶體中
            # 只是拋出異常，沒有 I/O 操作
            raise ClientResponseError(
                request_info=self.request_info,
                history=self.history,
                status=self.status,
            )
```

**邏輯**：
1. `self.status` 在 HTTP 回應的 header 中，已經讀取到記憶體
2. 檢查 `self.status >= 400` 只是純計算
3. 拋出異常不需要任何 I/O 操作
4. **所以是同步方法**

**對比：為什麼 `text()` 是異步的？**

```python
class ClientResponse:
    async def text(self):
        """讀取 response body 的文字內容"""
        if self._body is None:
            # 需要從網路讀取 body
            self._body = await self._read_body()  # I/O 操作
        return self._body.decode('utf-8')
```

**邏輯**：
1. Response body 可能很大，不會自動讀取
2. 需要從網路連接中讀取數據（I/O 操作）
3. **所以是異步方法**

---

### 3.4 aiohttp 完整使用範例

```python
import aiohttp
import asyncio

async def fetch_user(user_id):
    """取得使用者資料"""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.example.com/users/{user_id}"

        async with session.get(url) as response:
            # 同步：檢查狀態碼
            if response.status == 404:
                return None

            # 同步：如果錯誤就拋出異常
            response.raise_for_status()

            # 異步：讀取 JSON
            data = await response.json()
            return data

# 執行
user = asyncio.run(fetch_user(123))
```

---

## Part 4: Pytest Mock 基礎

### 4.1 為什麼需要 Mock？

**問題場景**：
```python
async def send_webhook(url, data):
    """發送 webhook 到外部 API"""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            response.raise_for_status()
            return await response.json()

# 測試時的問題：
# 1. 需要真的發 HTTP 請求？ → 太慢（每次數秒）
# 2. 需要外部 API 正常運作？ → 不穩定
# 3. 如何測試錯誤情況（503, 429）？ → 難以模擬
# 4. 測試會產生副作用（真的發送請求）？ → 不安全
```

**Mock 解決方案**：
```python
from unittest.mock import AsyncMock

async def test_send_webhook():
    # 用假的 session 替換真的 session
    mock_session = AsyncMock()

    # 完全控制它的行為
    mock_session.post.return_value = ...

    # 不需要真的網路請求，測試快速且穩定
```

---

### 4.2 MagicMock - 模擬同步物件

```python
from unittest.mock import MagicMock

# === 基本用法 ===
mock_obj = MagicMock()

# 自動回應任何方法調用
result = mock_obj.any_method()        # 不報錯
value = mock_obj.any_attribute        # 不報錯
mock_obj.foo.bar.baz()               # 不報錯

# === 設定返回值 ===
mock_obj.get_status.return_value = 200
status = mock_obj.get_status()  # 返回 200

# === 設定拋出異常 ===
mock_obj.validate.side_effect = ValueError("Error")
mock_obj.validate()  # 拋出 ValueError

# === 驗證調用 ===
mock_obj.method(1, 2, key="value")
mock_obj.method.assert_called_once_with(1, 2, key="value")
```

**適用場景**：模擬**同步**物件/方法

---

### 4.3 AsyncMock - 模擬異步物件

```python
from unittest.mock import AsyncMock
import asyncio

# === 基本用法 ===
mock_obj = AsyncMock()

# 方法返回可以 await 的 coroutine
result = await mock_obj.any_method()  # 需要 await

# === 設定返回值 ===
mock_obj.fetch_data.return_value = {"status": "ok"}
data = await mock_obj.fetch_data()  # 返回 {"status": "ok"}

# === 設定拋出異常 ===
mock_obj.connect.side_effect = ConnectionError("Failed")
await mock_obj.connect()  # 拋出 ConnectionError

# === 驗證調用 ===
await mock_obj.method(1, 2)
mock_obj.method.assert_awaited_once_with(1, 2)
```

**適用場景**：模擬**異步**物件/方法

---

### 4.4 如何選擇：MagicMock vs AsyncMock

**決策流程圖**：
```
要 mock 的東西
    ↓
真實代碼如何使用？
    ↓
    ├─ await obj.method()  → 用 AsyncMock
    ├─ obj.method()        → 用 MagicMock
    └─ async with obj      → MagicMock + 設定 __aenter__/__aexit__ (AsyncMock)
```

**對應表**：

| 真實代碼 | Mock 類型 | 原因 |
|---------|----------|------|
| `await session.get(url)` | `AsyncMock` | 方法本身是 async |
| `response.status` | 不需要 mock | 只是屬性 |
| `response.raise_for_status()` | `MagicMock` | 同步方法 |
| `await response.json()` | `AsyncMock` | 異步方法 |
| `async with session.get(url)` | `MagicMock` + 設定 `__aenter__`/`__aexit__` | 上下文管理器 |

---

### 4.5 return_value vs side_effect

#### return_value - 設定返回值
```python
mock = MagicMock()
mock.method.return_value = 42

result = mock.method()  # 返回 42
result = mock.method()  # 返回 42（每次都一樣）
```

#### side_effect - 設定副作用

**1. 拋出異常**：
```python
mock.method.side_effect = ValueError("Error")
mock.method()  # 拋出 ValueError
```

**2. 自訂函數**：
```python
def custom_logic(x):
    return x * 2

mock.method.side_effect = custom_logic
result = mock.method(21)  # 返回 42
```

**3. 多次調用返回不同值**：
```python
mock.method.side_effect = [1, 2, 3]
mock.method()  # 返回 1
mock.method()  # 返回 2
mock.method()  # 返回 3
```

---

## Part 5: Mock 異步上下文管理器

### 5.1 什麼是上下文管理器？

#### 同步上下文管理器（with）
```python
# 使用
with open("file.txt") as f:
    content = f.read()
# 自動關閉檔案

# 等同於
f = open("file.txt")
f.__enter__()  # 進入
try:
    content = f.read()
finally:
    f.__exit__()  # 離開（自動執行）
```

#### 異步上下文管理器（async with）
```python
# 使用
async with session.get(url) as response:
    data = await response.json()
# 自動釋放連接

# 等同於
response = session.get(url)
await response.__aenter__()  # 進入
try:
    data = await response.json()
finally:
    await response.__aexit__()  # 離開（自動執行）
```

---

### 5.2 aiohttp 的上下文管理器

```python
async with session.post(url, json=data) as response:
    response.raise_for_status()
```

**執行流程**：
```
1. session.post(url, json=data)
   ↓
   返回 ClientResponse 物件（同步返回，不需要 await）

2. await response.__aenter__()
   ↓
   進入 async with 區塊，返回 response 本身

3. 執行區塊內的代碼
   response.raise_for_status()

4. await response.__aexit__(...)
   ↓
   離開 async with 區塊，釋放網路連接
```

---

### 5.3 如何 Mock 異步上下文管理器

**完整範例**：
```python
from unittest.mock import AsyncMock, MagicMock

# Step 1: 創建 mock response
mock_response = MagicMock()

# Step 2: 設定 __aenter__（進入 async with）
mock_response.__aenter__ = AsyncMock(return_value=mock_response)
# 意思：進入 async with 時，response 變數 = mock_response

# Step 3: 設定 __aexit__（離開 async with）
mock_response.__aexit__ = AsyncMock(return_value=None)
# 意思：正常離開，不壓制異常

# Step 4: 設定 response 的方法
mock_response.raise_for_status = MagicMock()  # 同步方法
mock_response.json = AsyncMock(return_value={"ok": True})  # 異步方法
mock_response.status = 200  # 屬性

# Step 5: 創建 mock session
mock_session = AsyncMock()

# Step 6: 讓 session.post() 返回 mock_response
mock_session.post = MagicMock(return_value=mock_response)
# 注意：用 MagicMock，因為 session.post() 本身不是 async

# 使用
async with mock_session.post(url, json=data) as response:
    # response 就是 mock_response
    response.raise_for_status()
    data = await response.json()
```

---

### 5.4 為什麼 `__aenter__` 和 `__aexit__` 要用 AsyncMock？

**因為它們是異步方法**：

```python
class ClientResponse:
    async def __aenter__(self):  # ← async def
        """進入 async with 區塊"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # ← async def
        """離開 async with 區塊"""
        await self.release()  # 釋放連接（I/O 操作）
        return None
```

**真實使用時**：
```python
async with session.get(url) as response:
    #      ↑
    #      這裡會 await response.__aenter__()
    #      所以 __aenter__ 必須是異步的
```

---

### 5.5 視覺化：Mock 上下文管理器的結構

```
mock_session (AsyncMock)
    │
    └─ post (MagicMock)
           │
           └─ return_value = mock_response (MagicMock)
                                 │
                                 ├─ __aenter__ (AsyncMock)
                                 │      └─ return_value = mock_response
                                 │
                                 ├─ __aexit__ (AsyncMock)
                                 │      └─ return_value = None
                                 │
                                 ├─ raise_for_status (MagicMock)
                                 ├─ json (AsyncMock)
                                 └─ status = 200
```

---

## Part 6: 常見陷阱與疑問

### 6.1 疑問：`mock_client.post = MagicMock(...)` vs `mock_client.post.return_value = ...`

這是我們對話中最重要的疑問！

#### 方式 1：直接替換（✅ 推薦）
```python
mock_client = AsyncMock()
mock_client.post = MagicMock(return_value=mock_response)

# mock_client.post 是 MagicMock
# 調用時：
result = mock_client.post(url)  # 不需要 await，直接返回 mock_response
```

#### 方式 2：設定 return_value（⚠️ 需要額外 await）
```python
mock_client = AsyncMock()
mock_client.post.return_value = mock_response

# mock_client.post 是 AsyncMock
# 調用時：
result = await mock_client.post(url)  # 需要 await 才能得到 mock_response
```

---

#### 實驗：兩種方式的差異

```python
from unittest.mock import AsyncMock, MagicMock
import asyncio

mock_response = MagicMock()

# === 方式 1 ===
mock_client_1 = AsyncMock()
mock_client_1.post = MagicMock(return_value=mock_response)

print(type(mock_client_1.post))
# 輸出：<class 'unittest.mock.MagicMock'>

result = mock_client_1.post("http://example.com")
print(result is mock_response)
# 輸出：True （不需要 await）

# === 方式 2 ===
mock_client_2 = AsyncMock()
mock_client_2.post.return_value = mock_response

print(type(mock_client_2.post))
# 輸出：<class 'unittest.mock.AsyncMock'>

coro = mock_client_2.post("http://example.com")
print(type(coro))
# 輸出：<class 'coroutine'> （需要 await）

result = asyncio.run(coro)
print(result is mock_response)
# 輸出：True （await 之後才得到 mock_response）
```

---

#### 真實的 aiohttp 行為

```python
# 真實代碼
async with session.post(url) as response:
    #          ^^^^^^^^^^^^
    #          session.post() 不需要 await！
    #          它直接返回 ClientResponse 物件
```

**所以方式 1 更接近真實行為**。

---

#### 視覺化對比

**方式 1 的調用鏈**：
```
mock_client.post(url)
    ↓
【MagicMock.__call__() 被調用】
    ↓
直接返回 return_value
    ↓
得到 mock_response
```

**方式 2 的調用鏈**：
```
mock_client.post(url)
    ↓
【AsyncMock.__call__() 被調用】
    ↓
返回 coroutine 物件
    ↓
await coroutine
    ↓
取出 return_value
    ↓
得到 mock_response
```

---

### 6.2 陷阱：異步方法用 MagicMock

```python
# ❌ 錯誤
mock_session = MagicMock()
result = await mock_session.get(url)
# TypeError: object MagicMock can't be used in 'await' expression

# ✅ 正確
mock_session = AsyncMock()
result = await mock_session.get(url)
```

---

### 6.3 陷阱：同步方法用 AsyncMock

```python
# ❌ 錯誤
mock_response.raise_for_status = AsyncMock(side_effect=error)
mock_response.raise_for_status()
# 返回 coroutine，不會拋出異常！

# ✅ 正確
mock_response.raise_for_status = MagicMock(side_effect=error)
mock_response.raise_for_status()
# 立即拋出異常
```

---

### 6.4 陷阱：忘記設定 return_value

```python
# ❌ 錯誤
mock_client.post = MagicMock()
async with mock_client.post(url) as response:
    # TypeError: 'MagicMock' object does not support the asynchronous context manager protocol
    ...

# ✅ 正確
mock_response = MagicMock()
mock_response.__aenter__ = AsyncMock(return_value=mock_response)
mock_response.__aexit__ = AsyncMock(return_value=None)
mock_client.post = MagicMock(return_value=mock_response)

async with mock_client.post(url) as response:
    # 正常運作
    ...
```

---

### 6.5 決策樹：我應該用哪個 Mock？

```
看真實代碼怎麼用
    ↓
    ├─ await obj.method()
    │   └─ 用 AsyncMock
    │
    ├─ obj.method()
    │   └─ 用 MagicMock
    │
    ├─ async with obj
    │   └─ MagicMock，但設定：
    │      obj.__aenter__ = AsyncMock(return_value=obj)
    │      obj.__aexit__ = AsyncMock(return_value=None)
    │
    └─ obj.attribute
        └─ 直接賦值：obj.attribute = value
```

---

## Part 7: 完整測試範例

### 7.1 被測試的函數

```python
# vlm_worker.py
import aiohttp
from aiohttp import ClientConnectionError, ClientResponseError

async def _send_result_via_hook(client, hook_endpoint, result, msg_id):
    """
    發送結果到 webhook endpoint，包含重試邏輯

    - 503 錯誤：重試 3 次後拋出 ClientResponseError（觸發 circuit breaker）
    - 429 錯誤：重試 3 次後拋出 WebhookClientError（不觸發 circuit breaker）
    - 400 錯誤：不重試，直接拋出 WebhookClientError
    """
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            async with client.post(hook_endpoint, json=result) as response:
                response.raise_for_status()
                return  # 成功

        except (ClientConnectionError, ClientResponseError) as e:
            if not _is_retryable(e):
                # 不可重試的錯誤（如 400）
                raise WebhookClientError(f"Non-retryable error: {e}") from e

            if attempt == max_retries:
                # 最後一次重試失敗
                if _should_trigger_circuit_breaker(e):
                    raise e  # 5xx 錯誤，觸發 circuit breaker
                else:
                    raise WebhookClientError(f"Exhausted retries: {e}") from e

            # 等待後重試
            await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
```

---

### 7.2 測試案例 1：503 錯誤觸發 Circuit Breaker

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientResponseError, RequestInfo
from yarl import URL

def create_client_response_error(url, status, message):
    """輔助函數：創建 ClientResponseError"""
    request_info = RequestInfo(
        url=URL(url),
        method="POST",
        headers={},
        real_url=URL(url)
    )
    return ClientResponseError(
        request_info=request_info,
        history=(),
        status=status,
        message=message
    )

@pytest.mark.asyncio
async def test_webhook_503_triggers_circuit_breaker():
    """測試：503 錯誤應該觸發 circuit breaker"""

    # === Step 1: 創建 503 錯誤 ===
    error_503 = create_client_response_error(
        "http://hook.com",
        503,
        "Service Unavailable"
    )

    # === Step 2: 創建 mock response ===
    mock_response = MagicMock()

    # 設定異步上下文管理器
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    # raise_for_status 拋出 503 錯誤
    mock_response.raise_for_status = MagicMock(side_effect=error_503)

    # === Step 3: 創建 mock client ===
    mock_client = AsyncMock()
    mock_client.post = MagicMock(return_value=mock_response)

    # === Step 4: Patch sleep（避免真的等待）===
    with patch("vlm_worker.sleep", new_callable=AsyncMock):
        # === Step 5: 執行並驗證 ===
        with pytest.raises(ClientResponseError) as exc:
            await _send_result_via_hook(
                mock_client,
                "http://hook.com",
                {"data": "test"},
                "msg-123"
            )

        # 驗證拋出的是 503 錯誤
        assert exc.value.status == 503

# 執行流程：
# 1. 第 1 次：拋出 503 → 捕捉 → 可重試 → sleep → retry
# 2. 第 2 次：拋出 503 → 捕捉 → 可重試 → sleep → retry
# 3. 第 3 次：拋出 503 → 捕捉 → 達到 max_retries → 觸發 circuit breaker → raise ClientResponseError
```

---

### 7.3 測試案例 2：429 錯誤不觸發 Circuit Breaker

```python
@pytest.mark.asyncio
async def test_webhook_429_does_not_trigger_circuit_breaker():
    """測試：429 錯誤不應該觸發 circuit breaker"""

    # === 創建 429 錯誤 ===
    error_429 = create_client_response_error(
        "http://hook.com",
        429,
        "Too Many Requests"
    )

    # === 設定 mock ===
    mock_response = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.raise_for_status = MagicMock(side_effect=error_429)

    mock_client = AsyncMock()
    mock_client.post = MagicMock(return_value=mock_response)

    # === 執行並驗證 ===
    with patch("vlm_worker.sleep", new_callable=AsyncMock):
        with pytest.raises(WebhookClientError):  # 不是 ClientResponseError
            await _send_result_via_hook(
                mock_client,
                "http://hook.com",
                {"data": "test"},
                "msg-123"
            )

# 執行流程：
# 1-3 次重試後，拋出 WebhookClientError（不觸發 circuit breaker）
```

---

### 7.4 測試案例 3：400 錯誤立即失敗

```python
@pytest.mark.asyncio
async def test_webhook_400_no_retry():
    """測試：400 錯誤應該立即失敗，不重試"""

    # === 創建 400 錯誤 ===
    error_400 = create_client_response_error(
        "http://hook.com",
        400,
        "Bad Request"
    )

    # === 設定 mock ===
    mock_response = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.raise_for_status = MagicMock(side_effect=error_400)

    mock_client = AsyncMock()
    mock_client.post = MagicMock(return_value=mock_response)

    # === 執行並驗證 ===
    with pytest.raises(WebhookClientError):
        await _send_result_via_hook(
            mock_client,
            "http://hook.com",
            {"data": "test"},
            "msg-123"
        )

    # 驗證只調用了 1 次（沒有重試）
    assert mock_client.post.call_count == 1
```

---

### 7.5 測試案例 4：成功情況

```python
@pytest.mark.asyncio
async def test_webhook_success():
    """測試：正常情況應該成功發送"""

    # === 設定 mock response（不拋出異常）===
    mock_response = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.raise_for_status = MagicMock()  # 不拋出異常
    mock_response.status = 200

    # === 設定 mock client ===
    mock_client = AsyncMock()
    mock_client.post = MagicMock(return_value=mock_response)

    # === 執行 ===
    await _send_result_via_hook(
        mock_client,
        "http://hook.com",
        {"data": "test"},
        "msg-123"
    )

    # === 驗證 ===
    mock_client.post.assert_called_once_with(
        "http://hook.com",
        json={"data": "test"}
    )
    mock_response.raise_for_status.assert_called_once()
```

---

### 7.6 執行測試

```bash
# 執行單一測試
pytest tests/test_vlm_worker.py::test_webhook_503_triggers_circuit_breaker -v

# 執行所有測試
pytest tests/test_vlm_worker.py -v

# 執行測試並顯示覆蓋率
pytest tests/test_vlm_worker.py --cov=vlm_worker --cov-report=term
```

---

## 總結

### 核心概念回顧

1. **同步 vs 異步**
   - 同步：`def func()` → `result = func()`
   - 異步：`async def func()` → `result = await func()`

2. **物件類型**
   - 純同步物件：所有方法都是 `def`
   - 純異步物件：所有方法都是 `async def`
   - 混合型物件：同時有 `def` 和 `async def`（如 `ClientResponse`）

3. **Mock 選擇**
   - 同步方法 → `MagicMock`
   - 異步方法 → `AsyncMock`
   - 異步上下文管理器 → `MagicMock` + 設定 `__aenter__`/`__aexit__`（`AsyncMock`）

4. **常見模式**
   ```python
   # Session: 用 AsyncMock
   mock_session = AsyncMock()

   # Response: 用 MagicMock（但有異步方法）
   mock_response = MagicMock()
   mock_response.__aenter__ = AsyncMock(return_value=mock_response)
   mock_response.__aexit__ = AsyncMock(return_value=None)

   # 連接：用 MagicMock（因為 session.post() 同步返回）
   mock_session.post = MagicMock(return_value=mock_response)
   ```

### 檢查清單

寫測試時，問自己：

- [ ] 真實代碼這個方法需要 `await` 嗎？
- [ ] 真實代碼用 `async with` 嗎？
- [ ] 我的 mock 行為跟真實物件一致嗎？
- [ ] 我設定了正確的 `return_value` 或 `side_effect` 嗎？
- [ ] 我驗證了正確的調用次數和參數嗎？

### 延伸閱讀

- [Python asyncio 官方文檔](https://docs.python.org/3/library/asyncio.html)
- [aiohttp 官方文檔](https://docs.aiohttp.org/)
- [unittest.mock 官方文檔](https://docs.python.org/3/library/unittest.mock.html)
- [Pytest 官方文檔](https://docs.pytest.org/)

---

**祝你測試愉快！🚀**
