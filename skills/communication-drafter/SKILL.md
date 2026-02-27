---
name: communication-drafter
description: >
  Draft professional emails and track follow-ups for Leo's academic and networking communications.
  Use when (1) Leo needs to write an email to professors, collaborators, or contacts,
  (2) drafting funding proposals or follow-ups, (3) tracking who Leo has contacted and when,
  (4) setting follow-up reminders, (5) Leo says "幫我寫 email", "寫信給", "follow up", "追蹤回信",
  "draft", "回覆". NOT for: casual messaging (Discord/Signal), or internal bot communication.
---

# Communication Drafter

## Quick Start

```bash
# 查看所有通訊記錄
python3 skills/communication-drafter/scripts/comms_tracker.py list

# 記錄一封已發送的 email
python3 skills/communication-drafter/scripts/comms_tracker.py log \
  --to "Ziya" \
  --subject "NTUAIS collaboration" \
  --channel email \
  --status sent \
  --followup-days 7

# 查看需要 follow-up 的
python3 skills/communication-drafter/scripts/comms_tracker.py overdue

# 標記已回覆
python3 skills/communication-drafter/scripts/comms_tracker.py resolve COM-001
```

## 起草 Email 流程

1. **確認收件人** — 查 `references/contacts.md` 了解背景和過往互動
2. **確認目的** — 問 Leo：這封信要達成什麼？
3. **起草** — 用學術語氣，簡潔明確
4. **給 Leo 確認** — 永遠不自動發送，先讓 Leo 看過
5. **記錄** — 發送後用 comms_tracker.py 記錄
6. **設 follow-up** — 如果需要回覆，設提醒天數

## 語氣指南

### 學術 Email（給教授/研究者）
- 開頭：Dear Professor X / Dear Dr. X
- 簡短介紹自己和來意（1-2 句）
- 正文直接切入重點
- 結尾：Thank you for your time / Best regards
- 語言：通常英文，除非對方明確用中文

### 同儕 Email（給同學/合作者）
- 語氣可以稍微輕鬆
- 重點放在 action items
- 中英文都 OK

### Funding / 正式申請
- 最正式的語氣
- 明確列出 ask（金額、時程、交付物）
- 附上相關文件連結

## Follow-up 規則

| 對象 | 預設等待天數 | 提醒方式 |
|------|-------------|---------|
| 教授 | 7 天 | Discord 提醒 Leo |
| 合作者 | 5 天 | Discord 提醒 |
| Funding | 14 天 | Discord + email draft |
| 一般聯絡人 | 7 天 | Discord 提醒 |

## 聯絡人資訊

見 `references/contacts.md` — 記錄 Leo 的重要聯絡人、過往互動、注意事項。

## 注意事項

- **永遠不自動發送 email** — 先給 Leo 確認
- 記錄要包含足夠 context，讓未來的自己能理解為什麼聯絡這個人
- 敏感內容（薪資、個人問題）不記錄在通訊記錄裡
