---
name: hn-recommend
description: >
  Personalized Hacker News recommendations for Leo. Dual-time push (13:30 + 20:30)
  with interest profile learning, dedup, and feedback loop.
---

# HN Recommender — L-09

每小時推送 Leo 感興趣的 Hacker News 文章到 Discord（09:00-22:00）。

## Architecture

```
[Cron 每小時整點 09-22]
  → LLM session (isolated, g53s)
    → Step 1: python3 hn_recommend.py fetch --limit 8 --session hourly
    → Step 2: LLM reads candidates, writes personalized "why it matters"
    → Step 3: Send to Discord #general (≤5 articles, formatted)
    → Step 4: Mark sent articles as seen (avoid PM repeat)
```

## Cron Prompt (hourly, 09-22)

```
Run the HN recommender for Leo.

1. Run: python3 ~/.openclaw/workspace/skills/hn-recommend/scripts/hn_recommend.py fetch --limit 8 --session hourly
2. From the JSON output, pick the top 3-5 most interesting items (interest_score ≥ 3).
3. For each picked item, write a 1-sentence "why it matters" tailored to Leo's research interests
   (mechanistic interpretability, speech/audio ML, AI safety, tooling).
4. Format and send to Discord user:756053339913060392 (Leo DM):

   📰 **HN 推薦** ({date} {HH:MM})

   **1. [Title](url)**
   💡 {why it matters}
   📊 {score}pts · {comments} comments · {suggested_action}

   **2. [Title](url)**
   ...

   > 回覆 👍 / 👎 + 編號 來調整推薦偏好

5. After sending, mark all sent article IDs as seen:
   echo '["id1","id2",...]' | python3 ~/.openclaw/workspace/skills/hn-recommend/scripts/hn_recommend.py mark-seen

6. If no items score >= 3 after LLM review, skip silently (HEARTBEAT_OK).
```

## Data Files

| File | Purpose |
|------|---------|
| `memory/hn/preferences.json` | Interest profile (boost/penalty keywords, weights) |
| `memory/hn/seen.jsonl` | Seen article IDs (7-day window, auto-GC) |
| `memory/hn/feedback.jsonl` | Leo's 👍/👎 feedback history |

## Feedback Loop

When Leo reacts with 👍 or 👎 to a recommendation:
1. Run `hn_recommend.py feedback <id> +/-`
2. Periodically (weekly): analyze feedback patterns → adjust `preferences.json` weights

## Profile Tuning

View: `python3 hn_recommend.py profile`
Stats: `python3 hn_recommend.py stats`

Weights can be manually edited in `memory/hn/preferences.json`.
