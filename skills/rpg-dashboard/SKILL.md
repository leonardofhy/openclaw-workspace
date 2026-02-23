---
name: rpg-dashboard
description: 顯示 Leo 的個人 RPG 狀態面板（精力、心情、睡眠、任務、主線任務、狀態效果）。當 Leo 問「顯示我的狀態」、「今天怎麼樣」、「status panel」、「RPG 面板」、「character sheet」時使用。
---

# RPG Dashboard Skill

Show Leo's personal status as an RPG character sheet, pulling live data from
diary, Todoist, and memory files.

## When to use

Load this skill when Leo asks things like:
- 「顯示我的狀態」/ 「show my status」
- 「我今天怎麼樣」/ 「RPG 面板」
- 「status panel」/ 「character sheet」
- 「今天任務/心情/睡眠怎麼樣」

## How to run

```bash
cd /Users/leonardo/.openclaw/workspace
python3 skills/leo-diary/scripts/rpg_dashboard.py
```

Output is Discord-formatted text. Copy it directly into your reply.

## Options

```bash
python3 rpg_dashboard.py              # Discord text (default)
python3 rpg_dashboard.py --send-email # send HTML version via email
```

## What it shows

- ❤️ 精力 / 💙 心情 — from latest diary entry (1–5 scale → 0–100%)
- 😴 睡眠 — hours + quality stars
- 📋 任務 — today's due + overdue count from Todoist
- ⚔️ 主線任務 — top 3 tasks by urgency (soonest due + highest priority)
- 🌡️ 狀態效果 — auto-detected (生病/睡眠不足/論文衝刺/…) + streak
