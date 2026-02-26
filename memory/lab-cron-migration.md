# Lab Cron Migration Checklist

> 目標：把不需要 MacBook secrets 的 cron 搬到 Lab 機（24/7）
> 狀態：待執行（等 Leo 下次到實驗室）

## Step 1: 確認 Lab 機 repo 同步
```bash
cd ~/.openclaw/workspace && git pull origin main
```

## Step 2: 合併 autodidact skill 到 main
MacBook 端（Leo 或 Little Leo 執行）：
```bash
git checkout main
git merge macbook-m3 -- skills/autodidact/ memory/learning/
git push origin main
```

## Step 3: 在 Lab 機建立 cron
跟 Lab bot 說：
> 建立兩個 cron：
> 1. `ai-learning-30min` — `cron 0,30 * * * *`，isolated session，sonnet，timeout 180s，announce to Discord
> 2. `weekly-research-summary` — `cron 0 21 * * 0 @ Asia/Taipei`，isolated session，sonnet，announce to Discord

## Step 4: MacBook 端刪除對應 cron
```
openclaw cron delete 9d3b5e54-5c30-4c61-a61c-ae32203c8b36  # ai-learning-30min
openclaw cron delete b563a3ee-97ef-4920-9262-c15c7051962a  # weekly-research-summary
```

## Step 5: 驗證
- 等一個 :00 或 :30，確認 Lab 機跑了 cycle
- 確認 MacBook 沒有重複跑

## 未來擴展（可選）
如果要搬更多 cron，需要先：
1. 把 `secrets/` 部署到 Lab 機（Google SA JSON + Todoist token + Email creds）
2. 安裝 Python 依賴（google-auth, todoist-api-python 等）
3. 測試各腳本能跑
