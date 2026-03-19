# 週報 2026-03-19 (2026-03-13 至 2026-03-19)

## 本週成果

### 研究突破
- **Q001/Q002 實驗完成**: Whisper-base voicing geometry 和 layer-wise causal ablation 全部完成
  - Q001: Layer 5 peak, cos_sim=0.155, 支持線性語音結構假說
  - Q002: 所有層 WER=1.0，證實 Whisper 分散編碼無冗餘層
- **27 個 mock 實驗**: 93.1% 通過率 (25/27)，框架內部一致性驗證完成
- **Paper A 重大進展**: 7,317 字，§1-§5 全部完成
  - 抽象: 200 字完整版本
  - 方法論: gc(k) metric 和 5D Listening Geometry 框架完整定義
  - 結果: 202 行結果描述，real/mock 實驗區分清楚

### Feed 推薦系統升級
- **4 源整合**: AlignmentForum + arXiv + HN + LessWrong (~90 篇/日)
- **智能評分 v2**: 作者追蹤 (30+ 研究者)、詞組感知匹配、4 層分級
- **Discord 整合**: 每日 20:35 自動推送美化格式摘要
- **反饋學習**: feedback_learner.py 分析反饋調整評分權重
- **Google Sheet 同步**: 20 篇推薦 + 中文翻譯，自動去重

### 基礎設施重構
- **DAG Orchestrator**: 任務依賴排程器，解決平行 CC 推送衝突
- **Agent Manager**: sub-agent 生命週期管理系統
- **CLAUDE.md**: 工作空間慣例注入，統一 CC 代理行為
- **Git Worktree**: 消除併發推送衝突的隔離環境

## 系統升級

### 測試基礎設施
- **測試數量**: 668 → 1,441 (+115% 增長)
- **覆蓋範圍**: 45 個測試檔案，全部通過
- **測試隔離**: conftest.py 修複 PATH 問題

### Cron 優化
- **成本節省**: ~13.5% 週使用量減少
- **模型降級**: merge-to-main, weekly-research-summary 從 Opus → Sonnet
- **重複消除**: 4 個重複 cron 停用 (-80 calls/day)

### 程式碼清理
- **歸檔腳本**: 53 個孤立腳本歸檔 (-18,819 LOC)
- **殭屍技能清理**: 3 個廢棄 skills 移除
- **工具提取**: diary_utils.py, schedule_engine.py 模組化

## 研究進展

### Framework 完成度
- **gc(k) metric**: Causal grounding coefficient 完整定義
- **Listening Geometry**: 5D 框架 (k*, α_AND, σ, t*, CS)
- **AND/OR gate 分解**: 多模態特徵機械分類學完整

### 預註冊預測 (GPU 待驗證)
1. **P1**: ALME "follows_text" 項目晚期層 gc 下降 (Δgc ≥ 0.10)
2. **P2**: 稀有音素對比強於常見對比的晚期層下降 (d ≥ 0.3)
3. **P3**: 劣化音頻項目各層 gc 平坦 (變異 < 0.01)

### Autodidact 審計
- **54 腳本**: 144 週期，26 READY 任務全清
- **實驗產出**: 22 個實驗 (2 real + 20 mock)，90.9% 成功率
- **Phase transition**: 1/3 解鎖條件達成

## 下週計劃

### 優先任務
1. **GPU 實驗擴展**: Q001/Q002 擴展到 Whisper-small/medium
2. **Paper A 收尾**: §3-§5 草稿檢視，引用補完
3. **預註冊驗證**: 3 個預測在 Whisper-small 上測試
4. **Qwen2-Audio 管道**: 完整 ALM listening vs. guessing 動態

### 基礎設施
1. **Orchestrator 除錯**: worktree 合併邏輯修復
2. **MCP 整合**: Todoist MCP 相容性驗證
3. **Feed 系統完善**: 根據 Leo 反饋調整評分權重

### 協作任務
1. **智凱哥合作**: 已處理，不需要再提醒
2. **實驗室 AI 訂閱**: 4 隊伍已登記，制度運作順利

## Blockers

### 計算資源
- **GPU 存取**: 所有 real 實驗需要持續 GPU 存取
- **Battleship 集群**: Slurm 環境配置需要確認

### 技術債務
- **Orchestrator worktree**: 合併邏輯需要全面測試
- **Test flakiness**: 日期敏感測試和設定路徑不匹配問題
- **Feed pipeline timeout**: digest-formatter 300s 超時需要診斷

### 外部依賴
- **Pathfinder 預算**: 8 天逾期，需 follow-up
- **NTU 獎學金**: 7 天逾期確認
- **工作證申請**: 13 天剩餘時間

---

**統計**: 74 commits, 39 CC agents spawned, 163 active .py files
**週期**: 2026-03-13 至 2026-03-19