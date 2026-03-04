---
name: hn-recommend
description: >
  Personalized Hacker News recommendations for Leo. Hourly silent collection,
  daily 20:30 digest (top 10), interest profile learning, dedup, feedback loop.
---

# HN Recommender — L-09

每小時靜默蒐集 HN 文章 → 每天 20:30 整理 top 10 推送 Leo。

## Architecture

```
[Cron 每小時 09-22] hn-collect (spark, 60s)
  → python3 hn_recommend.py collect
  → 靜默寫入 memory/hn/candidates/YYYY-MM-DD.jsonl（不發訊息）

[Cron 20:30] hn-daily-digest (g53s, 120s)
  → python3 hn_recommend.py digest --limit 10
  → LLM 寫 "why it matters" × 10 篇
  → Discord DM 一次推送
  → mark-seen
```

## Commands

| Command | 說明 |
|---------|------|
| `collect` | 靜默蒐集：fetch HN → score → 新候選寫入當日 JSONL |
| `digest --limit 10` | 整理：讀當日候選 → 重新排序 → 輸出 top N JSON |
| `fetch --limit N` | 舊版一次性 fetch + score（仍可用） |
| `mark-seen` | stdin JSON array → 標記為已推送 |
| `feedback <id> +/-` | 記錄 Leo 的 👍/👎 |
| `profile` | 顯示興趣 profile |
| `stats` | 統計（seen 數、feedback 數） |

## Data Files

| File | Purpose |
|------|---------|
| `memory/hn/preferences.json` | Interest profile (boost/penalty keywords) |
| `memory/hn/candidates/YYYY-MM-DD.jsonl` | 當日蒐集的候選文章（每小時追加） |
| `memory/hn/seen.jsonl` | 已推送 article IDs（7 天 dedup） |
| `memory/hn/feedback.jsonl` | Leo 的 👍/👎 反饋 |

## Feedback Loop

Leo 回覆 👍/👎 + 文章編號 → `feedback <id> +/-`
每週分析 feedback patterns → 調整 `preferences.json` 權重
