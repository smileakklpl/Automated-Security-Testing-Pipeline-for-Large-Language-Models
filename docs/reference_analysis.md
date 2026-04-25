# RAG 安全性研究文獻綜述：攻擊手法與定義

本文件用於支撐「自動化 RAG 攻擊測試流程」的驗證性研究，重點不在大型主流模型的完整訓練，而在於建立可重現、可比較的攻擊與防禦測試流程。Qwen 3 32B 只作為 Target Model 的理論上限，Attacker 與驗證模型仍以 7B 級模型為主。

## 1. PoisonedRAG: Knowledge Poisoning Attacks to RAG (2024)
- **攻擊定義**：將 RAG 的知識中毒定義為一個「雙目標最佳化問題」。攻擊者注入少量惡意文件，旨在讓 LLM 針對特定的「目標問題」產生「特定答案」。
- **核心機制 (Decomposition)**：將惡意文件拆解為兩個部分：
    - **檢索條件 (Retrieval Condition)**：優化文本的 Embedding，確保其與目標問題的語意相似度極高，能優先被檢索器選中。
    - **生成條件 (Generation Condition)**：確保文本進入 Context 後，具備足夠的影響力（或指令權限）誘導 LLM 忽略其他背景資訊，執行惡意指令。
- **主要發現**：在百萬級資料庫中，僅需注入少量精心設計的文件，即可觀察到顯著的攻擊成功率。

## 2. Machine Against the RAG: Jamming Attack (USENIX 2025)
- **攻擊定義**：提出了一種針對 RAG 系統的「阻斷服務攻擊 (DoS)」，稱為 **Jamming**。
- **核心機制 (Blocker Documents)**：
    - 攻擊者不一定要讓模型說謊，而是注入一種「阻礙文件 (Blocker document)」。
    - 這些文件會觸發模型的安全過濾機制或引發邏輯衝突，導致模型輸出「我不知道」、「上下文資訊不足」或「無法回答此問題」。
- **目標類型**：分為 t1 (資訊不足), t2 (觸發安全拒絕), t3 (錯誤資訊引導)。這是一種破壞系統可用性 (Availability) 的新型態威脅。

## 3. RAGuard: Secure RAG against Poisoning Attacks (2025)
- **防禦定義**：提出一個非參數化 (Non-parametric) 的防禦框架，專門偵測與過濾 RAG 中毒文本。
- **防禦機制 (Multi-stage Filtering)**：
    - **檢索擴展 (Retrieval Expansion)**：主動擴大檢索範圍 (Top-K) 以稀釋有毒片段的比例。
    - **區塊困惑度過濾 (Chunk-wise Perplexity Filtering)**：針對檢索出的文本進行細粒度的流暢度檢測。中毒文本通常為了滿足 Embedding 優化，其困惑度會出現異常。
    - **相似度偵測**：偵測資料庫中是否存在高度相似的重複攻擊模板。
- **成效**：在對抗 PoisonedRAG 等進階攻擊時，能達成超過 90% 的偵測準確率，且不影響正常推論效能。