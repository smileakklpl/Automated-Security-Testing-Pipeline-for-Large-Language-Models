# 實驗架構：RAG 系統資料中毒與防禦自動化管線

本文件聚焦於「自動化 RAG 攻擊測試流程」的驗證性實作，不追求大型主流模型的完整訓練或高成本部署，而是以可重現、可分段驗證的方式串接五個獨立模組（Phases）。

## Phase 1: 攻擊生成模組 (Knowledge Poisoning Generation)
**目標**：自動生成具備高檢索率與高執行率的「中毒文件」。
* **輸入 (Input)**：
    * 目標問題 (Target Query)：攻擊者預期使用者會問的問題。
    * 惡意目標 (Malicious Payload)：攻擊者希望 LLM 輸出的錯誤資訊或惡意行為。
    * 背景文本庫 (Corpus)：正常的文件樣本，用於模仿風格與提取關鍵字。
* **處理單元 (Process)**：
    * **Attacker LLM**：透過 Ollama 接口呼叫，模型名稱由 `configs/*.yaml` 的 `attacker_model` 欄位指定。利用迭代提示詞 (Iterative Prompting) 生成包含惡意指令的文本。
    * **語意優化 (Semantic Optimization)**：確保生成的文本包含與「目標問題」高度相關的詞彙，以提高後續在向量空間中的相似度。
* **輸出 (Output)**：中毒文本區塊 (Poisoned Chunks)。
* **執行約束**：Phase 1 需對所有目標查詢**批次完成全部生成**後再進入 Phase 2，Attacker 模型才從 VRAM 卸載。不可在單筆 query 迴圈內與 Target / Judge 交替呼叫。

## Phase 2: 注入與索引模組 (Data Injection & Indexing)
**目標**：將中毒文本無縫混入目標系統的知識庫中。
* **輸入 (Input)**：中毒文本區塊、大量正常文本區塊 (Clean Chunks)。
* **處理單元 (Process)**：
    * **Embedding Model**：將所有文本轉換為向量 (例如使用 BAAI/bge-m3 或 text-embedding-3-small)。
    * **Vector Database (例如 ChromaDB 或 FAISS)**：建立索引並儲存向量與對應的原始文本。
* **輸出 (Output)**：受污染的向量資料庫 (Poisoned Vector DB)。

## Phase 3: 觸發與檢索模組 (Trigger & Retrieval)
**目標**：模擬真實使用者提問，並測試檢索器是否會抓取到中毒文件。
* **輸入 (Input)**：模擬使用者發出的「目標問題」。
* **處理單元 (Process)**：
    * **Retriever**：計算提問向量與資料庫向量的餘弦相似度 (Cosine Similarity)。
    * 提取相似度最高的前 K 筆資料 (Top-K Retrieval)。
* **輸出 (Output)**：包含/不包含中毒文本的 Top-K 候選上下文 (Retrieved Contexts)。
* **紀錄指標**：檢索成功率 (Retrieval Success Rate, RSR) — 中毒文本出現在 Top-K 的機率。

## Phase 4: 防禦攔截模組 (Post-Retrieval Defense)
**目標**：在文本進入目標 LLM 前，攔截並剔除異常的中毒文本。
* **輸入 (Input)**：Phase 3 輸出的 Top-K 候選上下文。
* **處理單元 (Process)**：
    * **特徵萃取 (Feature Extraction)**：計算每個 Chunk 的困惑度 (Perplexity, PPL)、資訊熵、特殊字元比例等特徵。
    * **輕量分類器 (Lightweight Classifier)**：將特徵輸入預先訓練好的機器學習模型 (如 XGBoost/Random Forest)，判斷該 Chunk 是否為惡意注入。
* **輸出 (Output)**：經過清洗的安全上下文 (Sanitized Contexts)。被標記為惡意的 Chunk 將被丟棄。

## Phase 5: 生成與評估模組 (Generation & Evaluation)
**目標**：檢驗目標系統是否成功抵禦攻擊，或產生惡意輸出。
* **輸入 (Input)**：目標問題、經過 Phase 4 清洗的安全上下文。
* **處理單元 (Process)**：
    * **Target LLM**：透過 Ollama 接口呼叫，模型名稱由 `target_model` config 指定；依據上下文生成最終答案。理論上限以 Qwen 3 32B 為準，若資源受限可降級為更小模型。
    * **Judge LLM**：透過 Ollama 接口呼叫，模型名稱由 `judge_model` config 指定（建議與 `attacker_model` 設為同一模型以省去換載）；評估 Target LLM 的輸出是否包含了 Phase 1 設定的「惡意目標」。
* **輸出 (Output)**：攻擊是否成功的二元判定 (True/False)。
* **紀錄指標**：攻擊成功率 (Attack Success Rate, ASR) — 目標模型實際執行惡意指令的機率。
* **執行約束**：Target 與 Judge 須**分兩批串行**執行（先對所有 query 批次生成回答，再批次評估），不可在同一 query 迴圈內交替呼叫 Target 與 Judge，以避免 Ollama 頻繁換載。