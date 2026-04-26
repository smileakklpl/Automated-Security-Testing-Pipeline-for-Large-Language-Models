# 專案名稱：RAG 系統自動化安全性測試管線 (RAG Automated Security Testing Pipeline)
**專案性質**：資料科學與機器學習期末專題

**當前實作邊界**：本專題以「自動化 RAG 攻擊測試流程」為研究重點，定位為驗證性實作（proof-of-concept / verification prototype）。受限於經費與硬體條件，無法實作大型主流模型的完整訓練或高成本多模型部署；Qwen 3 32B 只作為 Target Model 的理論上限，Attacker 與驗證模型仍以 7B 級模型為主。

## 1. 專案背景與演進 (Project Background & Evolution)
* **初始階段**：本專題最初設計為「利用 7B 小模型自動生成惡意提示詞（Prompt Injection），對大型語言模型進行安全性壓力測試」。
* **架構轉型 (Pivot)**：經指導教授建議，直接的提示詞注入在學術與實務上已較為陳舊。因此，專題方向正式轉向 **RAG 系統的資料中毒（RAG Data Poisoning / Indirect Prompt Injection）**。
* **新目標**：設計一套自動化管線，模擬攻擊者將「包含隱蔽惡意指令的文本」注入至向量資料庫中，並測試當使用者發出正常查詢時，系統是否會檢索到有毒文本並導致模型執行惡意行為。同時，需實作基於「檢索後 (Post-Retrieval)」的防禦機制。

## 2. 理論基礎與參考文獻 (Theoretical Foundation)
實作邏輯基於以下近五年核心學術文獻：
1. **PoisonedRAG (2024)**：將知識中毒視為最佳化問題，攻擊文件需同時滿足「高檢索率（語意偽裝）」與「高執行率（覆寫原模型邏輯）」。
2. **Jamming Attack (USENIX 2025)**：除了引導錯誤輸出，也會測試注入「阻擋文件 (Blocker Documents)」，造成系統拒絕服務 (DoS)。
3. **RAGuard (2025)**：防禦機制的參考框架，強調在文本進入 LLM 前，透過「區塊困惑度 (Chunk-wise Perplexity)」與特徵過濾來攔截惡意文本，而非在向量空間處理。

## 3. 五階段系統架構設計 (System Architecture Pipeline)

管線需模組化開發，包含以下五個獨立階段：

### Phase 1: 攻擊生成模組 (Poisoning Generation)
* **任務**：給定「目標問題」與「惡意指令」，呼叫本地 7B 模型生成高度相關且夾帶指令的中毒文本 (Poisoned Chunks)。

### Phase 2: 注入與索引模組 (Data Injection & Indexing)
* **任務**：將正常語料庫 (Clean Chunks) 與中毒文本混合。
* **處理**：使用 Embedding Model 將文本向量化，並存入 Vector Database（需同時儲存向量與原始 payload）。

### Phase 3: 觸發與檢索模組 (Trigger & Retrieval)
* **任務**：模擬使用者輸入目標問題，透過 Retriever 進行相似度搜尋。
* **輸出**：返回 Top-K 的文本片段 (Contexts)。
* **追蹤指標**：檢索成功率 (Retrieval Success Rate, RSR)。

### Phase 4: 防禦攔截模組 (Post-Retrieval Defense) - **[重點開發項目]**
* **任務**：在 Top-K 文本進入生成階段前進行攔截。
* **實作細節**：針對每個 Chunk 計算特徵（如困惑度 PPL、特殊字元比例、資訊熵）。將這些特徵送入輕量級機器學習分類器（XGBoost 或 Random Forest）進行二元分類（安全/有毒）。拋棄有毒 Chunk。

### Phase 5: 生成與評估模組 (Generation & Evaluation)
* **任務**：Target LLM 接收清洗後的上下文並生成回答；理論上限以 Qwen 3 32B 為準，實作時可依資源降級。
* **評估**：使用 7B 驗證模型、Judge LLM 或人工標註判定最終回答是否成功防禦攻擊。
* **追蹤指標**：攻擊成功率 (Attack Success Rate, ASR)。

## 4. 技術選型與預期環境 (Tech Stack)
* **LLM 推論接口**：**Ollama**（統一接口，所有模型角色透過同一 `LLMClient` 呼叫，模型名稱由 `configs/*.yaml` 控制，不寫死在程式碼中）。
* **基礎框架**：以 Ollama Python 套件 + 原生向量庫 API 直接串接為主；不依賴 LangChain / LlamaIndex 等重型框架，降低環境複雜度。
* **向量資料庫 (Vector DB)**：ChromaDB, FAISS 或 Qdrant（以易於本地部署為主）。
* **語言模型 (LLMs)**：具體模型名稱由 config 決定，角色分工如下：
    * `attacker_model`：預設 7B 量化模型，負責 Phase 1 poison chunk 生成。
    * `target_model`：預設 14B 量化模型，理論上限 Qwen 3 32B；負責 Phase 5 回答生成。
    * `judge_model`：建議與 `attacker_model` 設為同一模型（例如同為 7B），可省去 Ollama 換載開銷；負責 Phase 5 攻擊成效評估。
    * 三個角色採**批次串行**執行，Ollama 自動管理 VRAM 換載，不需同時載入多個模型。
* **防禦分類器**：Scikit-learn, XGBoost。

## 5. 當前開發目標 (Current Development Goal)
目前團隊正處於 IDE 開發起步階段。首要任務是建立基礎的 RAG 環境（Phase 2 & Phase 3），並撰寫腳本自動化處理 Phase 1 的資料生成，最後再整合 XGBoost 分類器進入 Phase 4。整體定位以驗證性實作為主，重點是把攻擊測試流程跑通、可重現、可量化，而非堆疊大型模型能力。