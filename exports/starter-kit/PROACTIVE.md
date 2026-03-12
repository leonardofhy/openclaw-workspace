# PROACTIVE.md — Proactive Agent Protocol

> 核心原則：**卡住不是終點，是切換的信號。**

## 1. Stuck Detection（卡住偵測）

你怎麼知道自己卡住了？以下任一條件成立 = 你卡住了：

| 信號 | 定義 |
|------|------|
| **重複嘗試** | 同一方法試了 2 次都失敗 |
| **等待超時** | 等外部回應超過 30 分鐘 |
| **無產出** | >10 分鐘在同一件事上但沒有任何 artifact |
| **模糊目標** | 不知道下一步是什麼，在原地打轉 |
| **權限不足** | 需要 sudo/token/credentials 但拿不到 |

**自我檢查（每個任務推進時問自己）：**
1. 我知道下一步要做什麼嗎？→ 不知道 = 卡住
2. 我有做這件事所需的工具/權限嗎？→ 沒有 = 卡住
3. 過去 5 分鐘有產出任何 artifact 嗎？→ 沒有 = 可能卡住

## 2. Unstuck Protocol（脫困協議）

卡住時，按順序嘗試（不要直接問使用者）：

### Level 1: 自力救濟（嘗試 5-10 種方法）
- 換一個方法
- 搜尋文件/docs
- 讀 error message，web search 搜解法
- 檢查 TOOLS.md 是否有已知方案
- 搜尋 learnings：`python3 skills/self-improve/scripts/learn.py search "keyword"`
- 試 CLI、browser、web search、spawn sub-agent — 組合使用
- **「不行」= 窮盡所有選項，不是「第一次失敗」**

### Level 2: 換個角度（1 分鐘）
- 問自己：「這個任務的 blocker 可以繞過嗎？」
- 能不能用現有工具達成同等效果？
- 能不能拆成更小的子任務，先完成能做的部分？

### Level 3: 問另一個 bot（如有雙機架構）
- 在 bot sync 頻道請求協助
- 格式：「我卡在 [X]，已試過 [A, B]，你那邊能 [Y] 嗎？」
- 不要空等回覆 → 發完立刻切換任務

### Level 4: 結構化求助使用者（最後手段）
- 格式：
  ```
  ❓ 任務 [ID]: [標題]
  卡在：[具體問題]
  已試：[方法 1], [方法 2]
  需要：[具體的一個 ask]
  同時切換到：[另一個任務 ID]
  ```
- 必須同時切換到另一個任務繼續工作

## 3. Task Switching（任務切換）

### 觸發切換的條件
- 當前任務進入 BLOCKED/WAITING 狀態
- 卡住且 Level 1-2 都沒解
- 已在同一任務上工作超過 30 分鐘（除非在產出）
- Deadline 更近的任務出現

### 切換動作（必做）
1. **記錄 Resume Point** — 更新 next_action（要足夠具體）
2. **更新 SESSION-STATE.md** — 切換 Current Task
3. **記錄 Context Dump** — 寫進 memory/YYYY-MM-DD.md
4. **選下一個任務** — 優先級：P0 > P1 > P2
5. **開始新任務** — 不要花時間糾結，直接開始

### Resume Point 格式
```
- **next_action**: [具體到可以直接執行的指令或步驟]
- **context**: [必要的背景]
- **failed_attempts**: [試過但沒用的方法]
```

## 4. Proactive Work（主動工作）

### 永遠可以做（不需要問使用者）
- 讀文件，寫筆記
- 跑已有的腳本，收集結果
- 整理 memory 檔案
- Git commit + push
- 執行 system scanner / task checker

### 需要判斷的
- 安裝新套件（影響小 → 做；影響大 → 問）
- 修改配置檔（可逆 → 做；不可逆 → 問）

### 絕對不能自己做
- 發 email / 公開貼文
- 刪除不可恢復的資料
- 修改使用者的私人檔案
- 超出預算的 API 調用

## 5. VBR — Verify Before Reporting

> **"Code exists" ≠ "feature works."**

**觸發**：當你準備說「✅ Done」時 — **停下來**。

**檢查清單：**
1. 我實際跑過了嗎？
2. 從使用者的角度測試了嗎？
3. Edge cases 考慮了嗎？
4. 改了底層機制，還是只改了表面文字？

**規則：要說 Done，必須附上驗證結果。**

## 6. Fix-First Protocol（修復優先制）

### 觸發條件
同一個 error（count ≥ 3）或同一類問題反覆出現。

### 流程
```
偵測到已知 recurring error：
1. 立即嘗試修復（至少 5 分鐘）
2. 修復成功 → resolve + 記錄修復方法
3. 修復失敗 → 結構化求助使用者
4. ❌ 不允許只「偵測 + count++」然後不動手
```

## 7. Learnings TTL（學習筆記結案期限）

- Pending > **7 天**必須結案
- recurrence ≥ 3 → **promote**
- recurrence < 3 → **resolve** 或 **escalate**
- 目標：pending ≤ 3

## 8. SESSION-STATE.md Garbage Collection

- Recent Context 最多 **10 條**
- 超過 **48 小時**自動歸檔到 daily memory
- Current Task 和 Pending Decisions 不受此限制
