# 開發落地指南：RAG 中毒測試管線（含硬體配置建議）

本文件提供兩部分內容：
1. 你們目前專題（Phase 1~5）的具體實作建議與踩雷提醒。
2. 在 5070 Ti + 32GB RAM 的環境下，哪些模型與任務建議本地執行。

本專案目前的研究重點是「自動化 RAG 攻擊測試流程」，實作性質為驗證性實作，不以大型主流模型的完整部署為目標；Qwen 3 32B 只作為 Target Model 的理論上限，Attacker 與驗證模型仍以 7B 級模型為主。

---

## 0. 核心工程策略：Ollama 統一接口 + 批次執行（已採用）

### 0.1 以 Ollama 作為統一 LLM 接口

本專案採用 **Ollama** 作為所有 LLM 推論的統一接口，程式碼中不硬編碼任何具體模型名稱。好處如下：

- 模型選擇完全由 `configs/*.yaml` 控制，切換模型只需改 yaml，不改程式碼。
- Ollama 提供統一 REST API（`http://localhost:11434`），底層模型隨時可替換。
- 不依賴 LangChain / LlamaIndex 等重型框架也可直接運作，降低環境複雜度。

**LLMClient 接口規範**（所有 Phase 共用同一個類別）：

```python
# src/llm_client.py
import ollama

class LLMClient:
    def __init__(self, model: str):
        self.model = model  # 由 config 傳入，例如 "qwen3:7b"

    def generate(self, prompt: str, system: str = "") -> str:
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ]
        )
        return response["message"]["content"]
```

**Config 結構**（各角色模型分離，統一由 yaml 管理）：

```yaml
# configs/experiment_01.yaml
attacker_model:  "qwen3:7b"
target_model:    "qwen3:14b"
judge_model:     "qwen3:7b"    # 與 attacker 相同時，Ollama 無需重新換載
embedding_model: "bge-m3"
top_k: [3, 5, 10]
poison_ratio: [0.01, 0.05, 0.10]
seed: 42
```

Phase 1 使用 `LLMClient(config.attacker_model)`，Phase 5 使用 `LLMClient(config.target_model)`，換模型只改 yaml，框架不動。

---

### 0.2 VRAM 資源限制解法：批次執行（Attacker 與 Target 不需同時運行）

**常見疑問**：「同時執行 Attacker 和 Target 會不會爆顯存？」— **不會，因為兩者根本不需要同時運行。**

Pipeline 各階段的時序是**嚴格串行**的：

```
Phase 1（Attacker 批次生成全部 poison chunks）  → 完成後 Attacker 卸載
Phase 2（Embedding + 向量庫注入）               → 無需 LLM
Phase 3（批次檢索，記錄 RSR）                   → 無需 LLM
Phase 4（XGBoost 防禦分類）                     → 無需 LLM
Phase 5（Target 批次生成全部回答）               → Attacker 早已結束
         Judge 批次評估全部結果                  → 與 Target 分開執行
```

Ollama 預設只在 VRAM 中保留一個模型，切換時自動 unload 前一個（約 10–30 秒換載時間）。只要維持批次模式，整個實驗最多換載 2 次（Attacker→Target、Target→Judge），不構成顯存壓力。

**批次執行模式（必須遵守）**：

```python
# ✅ 正確：每個模型角色批次完成，再換下一個
all_poison_chunks = [attacker.generate(q) for q in queries]  # Phase 1 全批完成
# Phase 2、3、4 無需 LLM
all_answers    = [target.generate(q) for q in queries]        # Phase 5 全批完成
all_judgements = [judge.evaluate(a)  for a in all_answers]    # Judge 全批完成

# ❌ 錯誤：per-query 交替呼叫，每筆 query 換 3 次模型 → 極慢
for query in queries:
    attacker.generate(query)  # 載入 Attacker
    target.generate(query)    # 卸載 Attacker，載入 Target
    judge.evaluate(query)     # 卸載 Target，載入 Judge
```

**額外優化**：將 `judge_model` 設為與 `attacker_model` 相同（例如都是 `qwen3:7b`），Ollama 不需重新換載，整個實驗只換載**一次**（Attacker/Judge → Target）。

---

## 1. 建議先完成的最小可行版本（MVP）

建議先用 2 週完成以下成果，再逐步加強攻擊與防禦強度：

1. 可重現的基礎 RAG：clean corpus -> chunk -> embedding -> vector DB -> top-k retrieval -> target answer。
2. 初版 poisoning：先用 7B 模型或模板生成，至少 20~50 筆有毒 chunk。
3. 初版評估：輸出 RSR、ASR、平均延遲，重點在驗證流程是否完整運作。
4. 初版防禦：先 rule-based，再升級到 XGBoost/RandomForest。

這樣可先確保資料流完整，避免一開始就卡在模型微調或提示工程。

---

## 2. 建議的程式結構（可直接採用）

建議在專案根目錄新增以下結構：

- `configs/`：所有實驗設定（模型、top-k、poison ratio、seed）。
- `data/clean/`：乾淨語料。
- `data/poison/`：中毒語料（模板版與 LLM 版分開）。
- `artifacts/index/`：向量庫索引。
- `artifacts/logs/`：retrieval log、defense log、judge log。
- `artifacts/results/`：每次實驗的 metrics（json/csv）。
- `src/pipeline/phase1_generate.py`
- `src/pipeline/phase2_index.py`
- `src/pipeline/phase3_retrieve.py`
- `src/pipeline/phase4_defense.py`
- `src/pipeline/phase5_evaluate.py`
- `src/run_experiment.py`：統一入口，使用 `--config` 啟動。

重點：每次 run 都要落盤「config + seed + commit hash + metrics」，確保可重現。

---

## 3. 各 Phase 的技術實現注意事項

## Phase 1: 攻擊文本生成

1. 不要一開始只用單一 prompt。至少準備 3 種攻擊模板：
   - 指令覆寫型（hijack）
   - 阻斷型（blocker/DoS）
   - 語意偽裝型（看起來像正常知識）
2. 先做模板法，再接 7B 生成法，便於比較「模板 vs LLM 生成」的攻擊效果。
3. 每筆 poison 必須記錄 metadata：`attack_type`、`target_query_id`、`stealth_level`、`payload_strength`。

常見踩雷：只看最終 ASR，卻沒追蹤 poison 是否真的被檢索到（RSR），導致無法診斷問題點。

## Phase 2: 注入與索引

1. chunk 規則固定化（例如 300~500 tokens, overlap 50~100），避免因分塊差異造成結果不可比較。
2. 向量庫需同時保存：`embedding`、`raw_text`、`doc_id`、`is_poison`、`source`。
3. 若用 FAISS，注意索引類型一致（Flat / IVF / HNSW）會顯著影響 RSR。

常見踩雷：只存向量不存原文與標籤，後續無法做防禦分析與錯誤追蹤。

## Phase 3: 觸發與檢索

1. 查詢集（queries）要分 train/dev/test，避免防禦器在測試時資料洩漏。
2. Top-k 至少跑 3、5、10 三組，並記錄 poison 是否出現在 top-k（布林值 + rank）。
3. 若採 hybrid retrieval（BM25 + 向量），需分開報告，不可混在同一結果表。

常見踩雷：只記錄是否命中，不記錄命中位置 rank，導致無法分析攻擊強度。

## Phase 4: 檢索後防禦

1. 特徵建議先從 8~12 個開始：
   - PPL
   - 長度
   - 特殊字元比例
   - 字元熵
   - 重複 n-gram 比例
   - 指令語氣詞密度（例如 ignore, system, override）
2. baseline 先做 rule-based，再做 ML 分類器，並保留兩者結果供 ablation。
3. 優先控制 Recall（毒文本不要漏掉），再調 Precision（降低誤殺乾淨文本）。
4. 若 top-k 全被攔截，需有 fallback：
   - 回退 clean-only retrieval
   - 或輸出安全拒答模板

常見踩雷：只看分類準確率，不看 ASR 是否真的下降。

## Phase 5: 生成與評估

1. Judge 輸入模板固定化（同一批樣本要同一評估規則）。
2. Judge 輸出建議包含：`label`、`confidence`、`reason`。
3. 除 ASR 外至少再報：
   - 防禦後效能損失（延遲上升、正常回答品質下降）
   - 誤攔截率（clean chunk 被擋掉的比例）

常見踩雷：Judge prompt 每次改動卻不版本化，導致結果不可重現。

---

## 4. 指標定義（建議統一）

- Retrieval Success Rate (RSR)

  RSR = 命中 poison 的 query 數 / 總 query 數

- Attack Success Rate (ASR)

  ASR = 被 Judge 判定為攻擊成功的 query 數 / 總 query 數

- Defense Block Rate (DBR)

  DBR = 被防禦器攔截的 poison chunk 數 / 檢索到的 poison chunk 數

- Clean Drop Rate (CDR)

  CDR = 被誤攔截的 clean chunk 數 / 被檢索到的 clean chunk 數

---

## 5. 5070 Ti + 32GB RAM：本地模型能跑到哪裡

以下以「單卡、推論為主」做規劃。若你的 5070 Ti 為 16GB VRAM，配置會最平衡；若 VRAM 更低，請降級到更小模型或更高量化。就本專題而言，Qwen 3 32B 只作為 Target Model 的理論上限。

## 建議本地執行的部分

1. Phase 1 Attacker（可本地）：
   - 以 7B 量化版為主。
   - 優先關注能否穩定生成測試用 poison chunk，而不是追求高質量創作。
2. Phase 2 Embedding（可本地）：
   - bge-small/bge-base 或 e5-small/e5-base 可在本地穩定跑。
3. Phase 3 Retrieval（可本地）：
   - FAISS/Chroma 主要吃 CPU/RAM，32GB RAM 足夠中小型實驗。
4. Phase 4 Defense（強烈建議本地）：
   - 特徵抽取 + XGBoost/RandomForest 在此硬體非常足夠。
5. Phase 5 Target（可本地）+ Judge（建議雲端或人工標註）：
   - Target 以驗證流程為主，可先用 Qwen 3 32B 量化版或更小模型。
   - Judge 建議用 7B 驗證模型、雲端 API；若經費受限，改用人工標註或簡化規則判定。

## 不建議一開始就本地硬跑的部分

1. 超過 Qwen 3 32B 的更大主流模型不列入本專題規劃。
2. 在單次 query 的迴圈內交替呼叫 Attacker / Target / Judge（應改為分階段批次完成，參見 §0.2）。Attacker 與 Target 本身不需同時在 VRAM 中，串行批次執行即可，Ollama 自動管理換載。
3. 長 context（例如 8k~16k）會大幅拉高 KV cache 記憶體需求，先用 2k~4k 驗證流程。

## 建議模型角色分工

1. Attacker（本地）：7B 量化模型。
2. Target（本地）：Qwen 3 32B 量化版或更小模型，與 Attacker 可同型不同 prompt。
3. Judge（本地或雲端）：7B 驗證模型、雲端 API 或人工標註，以穩定可重現為優先。
4. Embedding（本地）：bge/e5 系列小中型模型。

---

## 6. 實驗設計建議（最少要做）

至少做下面這組矩陣，才有足夠說服力：

1. Poison ratio：1%、5%、10%。
2. Top-k：3、5、10。
3. 防禦：無防禦 / rule-based / XGBoost。
4. 攻擊類型：hijack 與 blocker 分開報告。
5. 每組 3 個 random seeds，報平均與標準差。
6. 加入「流程通過率」與「模組成功率」作為主要驗證指標，確保自動化流程每一段都可被重跑與追蹤。

---

## 7. 風險控管與工程品質建議

1. 所有輸入輸出資料都做 schema 驗證（避免欄位漏失導致整批實驗失效）。
2. 每個 phase 都要可單獨重跑（避免 pipeline 任一段失敗就全毀）。
3. 實驗資料與程式碼版本綁定（至少記錄 git commit hash）。
4. 先做一組固定 smoke test（10 筆 query）當回歸測試。

---

## 8. 推薦開發順序（你們目前最適合）

1. 先完成 Phase 2/3（可穩定計算 RSR）。
2. 補齊模板型 Phase 1 資料。
3. 接 Phase 5，拿到第一版 ASR。
4. 導入 Phase 4（rule-based -> XGBoost）。
5. 最後再優化 LLM 生成攻擊文本的隱蔽性與遷移能力。

以上順序可以最快產出可展示成果，並保留後續研究深度（攻擊強化與防禦消融）。
