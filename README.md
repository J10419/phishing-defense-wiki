# Phishing Defense Wiki

**釣魚郵件辨識、帳號防護與復原的可追溯知識庫。**

以六份官方資料為依據，整理十個互連 Wiki 條目與十五頁互動簡報。從可疑訊息的警訊、獨立查證，到密碼、多因素驗證與帳號復原，每項建議均可追溯至來源。

## 瀏覽

| 入口 | 內容 |
|---|---|
| [首頁](index.html) | 專案入口與快速導覽 |
| [互動簡報](slides.html) | 十五頁、兩個情境判讀、目錄與鍵盤操作 |
| [LLM Wiki](wiki.html) | 十個互連條目、關鍵字搜尋與來源索引 |
| [流程與驗證](evidence.html) | 編纂流程圖、資料映射與驗證說明 |

HTML 不依賴外部字型、套件或 API 金鑰。下載後可開啟 `index.html`；也可在此目錄執行 `python -m http.server 8765`，再開啟 `http://localhost:8765`。簡報支援前後按鈕、方向鍵、Home／End 與目錄，窄螢幕可捲動當頁內容。

## 知識流程

來源證據 → 格式與引用驗證 → ingest → LLM 編纂 Wiki → 查詢 → 逐頁內容 → 來源與表述檢查 → HTML → 瀏覽器驗證。

`sources/` 保存六份官方來源的精選摘要、短引文、定位資訊與取得時間。這些是編纂使用的證據卡，不是完整原文鏡像；完整內容請循官方連結閱讀。`wiki/pages.json` 保存經 LLM 編纂的持久知識，條目包含引用及交叉連結；`slides/slides.json` 依該 Wiki 整理。HTML 是瀏覽介面，搜尋是本地文字檢索。

來源機構包含 CISA、NIST、MITRE ATT&CK 與 FTC。來源的讀者、版本與適用條件保留在條目中，避免把不同驗證要求混為一談。

## 重建與查詢

需要 Python 3.10 以上，僅使用標準函式庫：

```sh
python scripts/pipeline.py rebuild
python scripts/pipeline.py query "帳號 復原 MFA"
python scripts/validate.py
```

重建會將保存的證據卡登錄為 SQLite 資料、輸出 Wiki Markdown，並重新產生四份 HTML。它重播既有 LLM 產出，不會發出新的模型 API 請求。更新知識時，應先核對官方來源，再由 LLM 重新編纂、審閱引用並保存新版本。

## 專案結構

```text
sources/       來源中繼資料與精選證據卡
wiki/          結構化條目、Markdown 與 SQLite
slides/        簡報結構資料
scripts/       ingest、編譯、查詢、渲染與驗證
docs/          流程、來源、內容對照與驗證說明
```

[來源](docs/sources.md) · [流程圖](docs/workflow.md) · [內容對照](docs/content-map.md) · [驗證範圍](docs/validation.md) · [來源與使用說明](NOTICE.md)

示例郵件均為虛構，不含可操作的釣魚連結。實際通報與復原操作應依服務提供者的官方流程進行。
