# Automated-Security-Testing-Pipeline-for-Large-Language-Models
Automated Security Testing Pipeline for Large Language Models Based on Iterative Adversarial Generation
基於迭代對抗的大型語言模型自動化安全測試管線

本專案目前以「自動化 RAG 攻擊測試流程」為核心，實作範圍以驗證性實驗為主，不以大型主流模型訓練或完整部署為目標。硬體條件下，本地推論上限以 Qwen 3 32B 為準，其餘模型僅作輕量或替代性實驗參考。

## 文件結構

```
docs/
├── project_background.md          # 專題背景、研究轉向、文獻綜述、技術選型、指標定義
├── development_implementation_guide.md  # 實作落地指南：程式結構、硬體配置、開發順序
├── phase1_attack_generation.md    # 攻擊生成模組：三種攻擊類型、Prompt 架構、Metadata 規範
├── phase2_injection_indexing.md   # 注入索引模組：Chunking 規則、Embedding 選型、向量庫規範
├── phase3_trigger_retrieval.md    # 觸發檢索模組：RSR 計算、Top-K 實驗組、查詢集分割
├── phase4_defense.md              # 防禦攔截模組：特徵萃取、XGBoost 分類器、Fallback 機制
└── phase5_generation_evaluation.md # 生成評估模組：ASR 計算、Judge Prompt 設計、批次執行約束
```

閱讀建議：先看 `project_background.md` 了解研究背景與整體架構，再查閱對應 `phase*.md` 的實作細節，硬體與工程策略請見 `development_implementation_guide.md`。

## 專案定位

本專案關注的是可重現、可量化、可分段驗證的 RAG 安全測試流程，重點在於建立攻擊與防禦管線，而不是追求最強模型表現或完整產品化部署。README 只保留高層摘要，細節請以 docs/ 底下的文件為準。
