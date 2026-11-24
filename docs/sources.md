# 來源與證據範圍

本專案依六份官方資料編纂釣魚防護知識。儲存庫只發布精選摘要、主張定位及一段MITRE短引文，**不包含完整原始網頁或PDF**。來源取得日期為2026-11-12；重新執行本機管線不代表文獻已重新查核或網站已更新。

| ID | 官方文獻 | 版本或日期 | 主要依據 |
|---|---|---|---|
| S02 | [FTC — Email or social media hacked? Here’s what to do](https://consumer.ftc.gov/consumer-alerts/2024/10/email-or-social-media-hacked-heres-what-do) | 2024-10 | 改密碼、登出裝置、復原資訊及轉寄規則 |
| S03 | [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) | 2025-07 | 密碼政策、OTP限制、WebAuthn與抗釣魚驗證 |
| S05 | [CISA — Implementing Phishing-Resistant MFA](https://www.cisa.gov/sites/default/files/publications/fact-sheet-implementing-phishing-resistant-mfa-508c.pdf) | 2022-10 | MFA差異、推播疲勞、FIDO/WebAuthn |
| S07 | [MITRE ATT&CK — Phishing, T1566](https://attack.mitre.org/techniques/T1566/) | 取得時頁面標示更新2026-09-18 | 釣魚屬電子傳遞的社交工程 |
| S08 | [NIST — Phishing](https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing) | 取得時頁面標示更新2026-10-16 | 警訊、獨立查證、通報及疑似受害後處理 |
| S11 | [CISA — Phishing Tip Sheet](https://www.cisa.gov/sites/default/files/publications/phishing_and_spoofing_tip_sheet_2022_092022.pdf) | 2022-09 | 冒充情境、查證、獨特密碼與防護習慣 |

## 可追溯的內容

[`sources/evidence-cards.json`](../sources/evidence-cards.json)包含六張精選證據卡。每項主張有穩定ID與章節或頁碼，另列適用限制。[`sources/manifest.json`](../sources/manifest.json)保留文獻網址、機構、取得時間及各卡的SHA-256。這些雜湊驗證的是發布的證據卡，不是完整原文。

S02依官方FTC搜尋擷取文字編纂；不宣稱儲存庫保存完整HTML。S07僅使用短引文支持定義，不以此推論攻擊案例或統計。其他卡依所列官方文獻的相關段落編纂；完整版應從官方連結查閱。

Wiki段落引用來源ID並保留定位，來源頁反向連回Wiki。簡報再以Wiki條目為依據，保留逐頁映射。虛構企業IT通知是情境改寫，並非真實事件或有效登入頁。

## 解讀差異

- NIST的密碼15／8字元要求有單因素與多因素的不同條件；FTC的12至15字元建議面向不同讀者，不能直接混為一個規範。
- OTP仍可遭釣魚。HTTPS只描述連線保護，不能單獨判斷服務是否為預期對象。
- 美國來源中的通報與金融規則不是其他地區或組織的通用要求；實際事件應使用所屬組織及服務商的正式流程。

## 更新方式

先取得並核對新版官方資料，再由LLM或編者更新證據卡、Wiki條目與相關連結。若修改證據卡，需同步計算canonical JSON的SHA-256（UTF-8、鍵名排序、不加額外空白）並更新manifest。`ingest`只把已保存的卡片匯入資料庫；`compile`與`rebuild`重播已保存的LLM內容，不會自行擷取網站或呼叫模型。
