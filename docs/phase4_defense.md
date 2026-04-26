# Phase 4：防禦攔截模組（Post-Retrieval Defense）

## 目標

在 Top-K 文本進入目標 LLM 前進行攔截，識別並剔除惡意的中毒文本，輸出清洗後的安全上下文。

---

## 輸入 / 輸出

| 項目 | 內容 |
|------|------|
| **輸入** | Phase 3 輸出的 Top-K 候選上下文 |
| **輸出** | 清洗後的安全上下文（Sanitized Contexts），被標記為惡意的 Chunk 丟棄 |
| **執行約束** | 不需要 LLM，只需特徵萃取 + 機器學習分類器，CPU 即可執行 |

---

## 核心指標

```
Defense Block Rate (DBR) = 被防禦器攔截的 poison chunk 數 / 被檢索到的 poison chunk 數
Clean Drop Rate (CDR)    = 被誤攔截的 clean chunk 數 / 被檢索到的 clean chunk 數
```

- DBR 越高越好（盡量攔截所有毒文本）
- CDR 越低越好（盡量不誤傷乾淨文本）
- 優先控制 **Recall（DBR）**，確保毒文本不漏掉；再調 **Precision（降低 CDR）**

---

## 理論依據：為何 Poisoned Chunk 特徵異常

中毒文本為了同時滿足「語意偽裝」與「指令注入」，在統計特徵上往往出現異常：

| 異常特徵 | 原因 |
|---------|------|
| 困惑度（PPL）突然升高 | 文本在「正常語句」→「惡意指令」轉折處出現語言風格突變 |
| 指令語氣詞密度高 | 包含 ignore / override / system / 忽略 等控制性詞彙 |
| 字元熵異常 | 特殊符號或格式標記（※、---、[]）集中出現 |
| 語意不連貫 | 前後段主題跳躍，語意偽裝段與指令段語意距離遠 |

**語意偽裝型（Stealth）** 是例外，其 PPL 接近正常，是防禦器最大的挑戰。

---

## 特徵萃取（Feature Extraction）

建議從 8～12 個特徵開始：

| 特徵 | 說明 | 計算方式 |
|------|------|---------|
| **PPL（困惑度）** | 語言模型對該文本的預測困難度，越高代表越不自然 | 使用輕量 LM（如 GPT-2 或 Qwen3 7B）計算 |
| **字元熵（Char Entropy）** | 字元分佈均勻程度，異常符號集中時熵值下降 | Shannon entropy on char distribution |
| **特殊字元比例** | `※ [] --- // \n\n` 等格式符號佔比 | count(special_chars) / len(text) |
| **重複 n-gram 比例** | 重複短語比例，模板法生成的文本常有重複 | 重複 bigram / 總 bigram 數 |
| **指令語氣詞密度** | ignore / override / system / 忽略 / 請注意 等詞頻 | count(keywords) / word_count |
| **文本長度** | 偏短或偏長的 Chunk 可能是注入片段 | len(text) |
| **語意跳躍分數** | 文本前後半段的 Embedding 距離，轉折點語意不連貫 | cosine_distance(embed(前半段), embed(後半段)) |
| **詞彙豐富度（TTR）** | Type-Token Ratio，低 TTR 代表詞彙單調（模板特徵） | unique_words / total_words |

---

## 分類器架構

### 第一層：Rule-Based 基準（必做）

先做規則過濾，作為 baseline 和 ablation 比較對象：

```python
def rule_based_filter(chunk_text: str) -> bool:
    """返回 True 代表判定為惡意"""
    keywords = ["ignore", "override", "system prompt", "忽略", "請注意以下指令"]
    if any(kw in chunk_text.lower() for kw in keywords):
        return True
    if special_char_ratio(chunk_text) > 0.05:
        return True
    return False
```

### 第二層：ML 分類器（主要防禦）

將特徵向量送入預先訓練的分類器，輸出 0（安全）或 1（惡意）：

```python
from xgboost import XGBClassifier

clf = XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1)
clf.fit(X_train, y_train)   # X: 特徵矩陣，y: is_poison 標籤

def ml_filter(features: list) -> bool:
    prob = clf.predict_proba([features])[0][1]
    return prob > THRESHOLD   # 可調整閾值控制 DBR / CDR 平衡
```

---

## Fallback 機制

當 Top-K 中所有 Chunk 都被攔截時，不可直接報錯或輸出空回答，需有 fallback：

| 選項 | 說明 |
|------|------|
| **回退 Clean-only Retrieval** | 改從已知乾淨的語料重新檢索（需維護獨立的 clean 索引） |
| **安全拒答模板** | 輸出固定回覆：「系統偵測到可疑資訊，無法回答此問題」 |
| **降低攔截閾值重試** | 放寬判定標準，取次可信的 Chunk |

---

## 防禦器訓練資料來源

| 資料 | 標籤 | 來源 |
|------|------|------|
| Phase 1 生成的 Poisoned Chunks | `is_poison = True` | Phase 1 輸出 |
| 正常語料的 Clean Chunks | `is_poison = False` | Phase 2 原始語料 |

注意：訓練集的 Query 不可與測試集重疊（Train/Dev/Test 分割需與 Phase 3 一致）。

---

## Ablation Study 建議

實驗中需保留以下三種設定的完整結果，供消融分析：

| 設定 | 描述 |
|------|------|
| 無防禦 | 直接將 Top-K 全部傳給 LLM |
| Rule-Based 防禦 | 僅用關鍵詞/統計規則過濾 |
| XGBoost 防禦 | 使用 ML 分類器 |

---

## 參考：RAGuard 防禦框架（2025）

RAGuard 提出非參數化多階段過濾，實測對抗 PoisonedRAG 達 90%+ 偵測率：

1. **檢索擴展（Retrieval Expansion）**：擴大 Top-K 範圍稀釋毒文本比例
2. **區塊困惑度過濾（Chunk-wise PPL Filtering）**：針對每個 Chunk 做細粒度流暢度檢測
3. **相似度偵測**：偵測資料庫中高度相似的重複攻擊模板

本專題 Phase 4 的 XGBoost 方法是 RAGuard PPL Filtering 思路的延伸，加入更多統計特徵。

---

## 實作注意事項

1. Baseline 先做 rule-based，再做 ML 分類器，兩者結果都要保留供 ablation
2. 優先控制 Recall（DBR），再調 Precision（降低 CDR）
3. 若 Top-K 全被攔截，需有 fallback 機制
4. 常見踩雷：只看分類準確率，不看 ASR 是否真的下降（分類器準確但 ASR 未降，代表仍有繞過）
