# Automated-Security-Testing-Pipeline-for-Large-Language-Models
Automated Security Testing Pipeline for Large Language Models Based on Iterative Adversarial Generation
基於迭代對抗的大型語言模型自動化安全測試管線

本專案目前以「自動化 RAG 攻擊測試流程」為核心，實作範圍以驗證性實驗為主，不以大型主流模型訓練或完整部署為目標。硬體條件下，本地推論上限以 Qwen 3 32B 為準，其餘模型僅作輕量或替代性實驗參考。

## 文件用途

這個倉庫主要是研究與實作說明文件的彙整入口，用來定義專題的研究邊界、系統流程與文獻依據。現有文件分工如下：

- [docs/project_context.md](docs/project_context.md)：說明專題背景、研究轉向、五階段管線與當前開發目標。
- [docs/method.md](docs/method.md)：說明 RAG 攻擊生成、注入、檢索、防禦與評估的流程設計。
- [docs/reference_analysis.md](docs/reference_analysis.md)：整理支撐本專題的攻擊與防禦相關文獻定義。
- [docs/development_implementation_guide.md](docs/development_implementation_guide.md)：提供實作建議、硬體限制下的模型配置與開發順序。

## 專案定位

本專案關注的是可重現、可量化、可分段驗證的 RAG 安全測試流程，重點在於建立攻擊與防禦管線，而不是追求最強模型表現或完整產品化部署。README 只保留高層摘要，細節請以 docs/ 底下的文件為準。
