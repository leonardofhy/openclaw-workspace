# TOOLS.md - Service Registry & Tool Notes

> ⚡ 這個檔案每次 session 自動載入。保持精簡但完整。
> 最後更新：2026-02-22

## 已啟用的服務

### 🔀 Git (Version Control)
- **Repo：** `git@github.com:leonardofhy/openclaw-workspace.git`（Private）
- **Branch：** `main`
- **規則：** 每次大改動後 `git add -A && git commit && git push`
- **追蹤範圍：** scripts、config .md、skills、memory 持久筆記
- **忽略：** `secrets/`、`memory/tags/`、`memory/????-??-??.md`、`*.json`、`.openclaw/`
- **注意：** 不含敏感資料（.gitignore 已配置），但 MEMORY.md 含個人資訊，repo 必須保持 Private

### 📧 Email (SMTP)
- **Ops 帳號：** zerotracenetwork01@gmail.com
- **收件人：** leonardofoohy@gmail.com
- **憑證位置：** `secrets/email_ops.env`
- **共用模組：** `skills/leo-diary/scripts/email_utils.py`
- **用法：** `from email_utils import send_email`

### ✅ Todoist
- **API Base：** `https://api.todoist.com/api/v1`
- **憑證位置：** `secrets/todoist.env`（TODOIST_API_TOKEN）
- **腳本：** `skills/leo-diary/scripts/todoist_sync.py`
- **功能：** `--limit N`（未完成任務）、`--completed-today`（今日已完成）
- **注意：** v2 API 已 deprecated (410)，用 v1

### 📅 Google Calendar
- **Service Account：** `little-leo-reader@little-leo-487708.iam.gserviceaccount.com`
- **權限：** Make changes to events（Leo 主日曆）
- **Cal ID：** `leonardofoohy@gmail.com`
- **憑證位置：** `secrets/google-service-account.json`
- **腳本：** `skills/leo-diary/scripts/gcal_today.py`
- **用法：** `python3 gcal_today.py --days-ahead 0 --days-range 7`

### 📝 Google Sheets (日記)
- **Service Account：** 同上
- **權限：** Readonly
- **Sheet ID：** `1CRY53JyLUXdRNDtHRCJwbPMZBo7Azhpowl15-3UigWg`
- **腳本：** `skills/leo-diary/scripts/read_diary.py`

### 💬 Discord
- **Leo User ID：** `756053339913060392`
- **Guild ID：** `978709246462013450`
- **發送方式：** `message` tool（channel=discord）
- **Target 格式：** `user:756053339913060392`（DM）、`channel:ID`（頻道）
- **頻道：**
  - `#general`（`978709248978599979`）— **只發真正重要的**（系統故障、需要 Leo 決策、重大 milestone）。Bot 之間不准用
  - `#bot-logs`（`1477354525378744543`）— 機器日誌、routine 記錄、growth report、bot 工作匯報
  - `#bot-sync`（`1476624495702966506`）— bot 之間的即時通訊、@mention、mailbox 通知
- **用途：** Todoist 提醒、日終摘要、週報、行事曆提醒

### 🔑 Google OAuth (Desktop)
- **Client Secret：** `/Users/leonardo/.openclaw/secrets/gog/client_secret.json`
- **狀態：** 有 client_secret，但**尚未生成 token.json**（需要 OAuth 授權流程）
- **用途：** 備用，目前用 Service Account 即可

### 🎤 Whisper (語音轉文字)
- **macbook 工具：** `whisper-cli`（whisper-cpp via Homebrew）
- **macbook 模型：** `~/.local/share/whisper-cpp/ggml-base.bin`（base, 147MB）
- **macbook 用法：** `ffmpeg -y -i input.ogg -ar 16000 -ac 1 /tmp/voice.wav && whisper-cli -m ~/.local/share/whisper-cpp/ggml-base.bin -l zh /tmp/voice.wav`
- **lab-desktop 工具：** `openai-whisper`（Python, via ~/miniconda3）
- **lab-desktop 用法：** `ffmpeg -y -i input.ogg -ar 16000 -ac 1 /tmp/voice.wav && ~/miniconda3/bin/python3 -c "import whisper; m=whisper.load_model('base'); print(m.transcribe('/tmp/voice.wav', language='zh')['text'])"`
- **注意：** 只接受 WAV 格式，需先用 ffmpeg 轉檔。支援中文

### 🛰️ Lab WSL2 SSH Tunnel（MacBook ↔ Lab）
- **Lab Host:** `DESKTOP-Q1L6LLN`（WSL2 Ubuntu）
- **User:** `leonardo`
- **Jump Host:** `iso_leo`
- **Route:** `Mac → iso_leo:2222 → WSL2:22`
- **一條指令連線：** `ssh -J iso_leo -p 2222 leonardo@localhost`
- **分步驟：** 先 `ssh iso_leo`，再 `ssh -p 2222 leonardo@localhost`
- **Secrets 搬運：** `scp -o ProxyJump=iso_leo -P 2222 -r ~/.openclaw/workspace/secrets/ leonardo@localhost:~/.openclaw/workspace/`
- **注意（Lab PATH）:** WSL2 的 OpenClaw 在 nvm 路徑，非互動 shell 需先加 PATH：
  - `export PATH=$HOME/.nvm/versions/node/v22.22.0/bin:$PATH`
  - 然後再跑 `openclaw gateway restart` / `openclaw gateway status`

## 未啟用 / 待設定

- **Gmail API：** Service Account 無權限，需另外授權
- **memory_search：** 缺少 embedding API key（OpenAI/Voyage），語義搜尋不可用

## 腳本總覽

| 腳本 | 位置 | 功能 |
|------|------|------|
| `read_diary.py` | leo-diary/scripts/ | 讀取日記（Google Sheets 優先，CSV 備援）|
| `todoist_sync.py` | leo-diary/scripts/ | Todoist 任務同步 |
| `gcal_today.py` | leo-diary/scripts/ | Google Calendar 事件查詢 |
| `daily_coach_v3.py` | leo-diary/scripts/ | 綜合教練信（日記+睡眠+行事曆+Todoist）|
| `sleep_calc.py` | leo-diary/scripts/ | 睡眠時長與趨勢分析 |
| `system_health.py` | leo-diary/scripts/ | 系統健檢（10 項）|
| `email_utils.py` | leo-diary/scripts/ | 共用寄信模組 |
| `insights.py` | leo-diary/scripts/ | 日記洞察報告 |
| `search_diary.py` | leo-diary/scripts/ | 日記搜尋（多關鍵詞/別名/regex/日期範圍）|
| `generate_tags.py` | leo-diary/scripts/ | 日記標籤提取（純 Python，批量回填）|
| `query_tags.py` | leo-diary/scripts/ | 標籤查詢（人物/主題/共現/時間線）|
| `keyword_freq.py` | leo-diary/scripts/ | 關鍵字頻率（純 Python）|
| `weekly_data.py` | daily-scheduler/scripts/ | 7天排程數據（Calendar+Todoist）|
| `sync_schedule_to_gcal.py` | daily-scheduler/scripts/ | 將最新 `memory/schedules/YYYY-MM-DD.md` 同步到 Google Calendar |
| `sync_schedule_to_todoist.py` | daily-scheduler/scripts/ | 將最新 `memory/schedules/YYYY-MM-DD.md` 同步到 Todoist（支援去重） |
| `weather_scout.py` | leo-diary/scripts/ | 天氣檢查+通知 |
| `fetch_latest_diary.py` | leo-diary/scripts/ | 拉取最新日記（供記憶反芻）|
| `append_memory.py` | remember/scripts/ | 寫入長期記憶 |
| `sync_diary_to_memory.py` | ~/Workspace/little-leo-tools/scripts/ | 日記同步到 memory/*.md |

## Secrets 清單
- `secrets/email_ops.env` — Email SMTP 憑證
- `secrets/todoist.env` — Todoist API Token
- `secrets/google-service-account.json` — Google Service Account
- `/Users/leonardo/.openclaw/secrets/gog/client_secret.json` — Google OAuth Desktop

## Cron 排程

### Mac Bot（原有）
- 04:15 日記同步 + LLM 標籤提取
- **08:00 每日排程刷新**（讀取/更新 memory/schedules/YYYY-MM-DD.md，sonnet）
- **08:12 排程同步到 Google Calendar + Todoist**（從 schedule 檔案自動 upsert）
- 08:30 早晨總覽（Todoist + Calendar + 自動設會議提醒）
- 12:00 Daily Coach v3（email）+ 記憶反芻
- 13:00 午間行事曆掃描
- 22:30 Todoist 晚間回顧（Discord）
- 23:50 日終摘要（Discord）
- **週日 21:00 週排程生成**（產生下週 7 天 schedule 草稿，sonnet，Discord 通知）
- 週日 21:00 週報（Discord）
- 週五 20:00 天氣偵察（email）

### Lab Bot（WSL2, 24/7）
- **每小時 09-22 HN 蒐集** `df22eb11`（isolated, spark, 60s）— 靜默蒐集 HN 候選到 `memory/hn/candidates/`
- **20:30 HN Daily Digest** `76817b6d`（isolated, g53s, 120s）— 整理當日 top 10 推送 Leo DM
- ***/30 08-23 Heartbeat**（main session, g53s）— 沉默優先；有 alert 才通知 #general；**含 deadline watchdog**
- **:15/:45 08-23 Autodidact**（isolated, sonnet, 300s timeout）— v2：precheck gate → phase-aware cycle
- **14:00 News Scout** `366e373d`（isolated, g53s, 180s timeout）— HN + Alignment Forum 掃描 → LLM 相關度評分 → 加入 autodidact queue
- **06:00 System Scanner**（isolated, g53s）— 每日健檢，🔴 時 Discord 通知 Leo
- **08:00 Daily Merge**（isolated, g53s）— 自動 fetch + merge macbook-m3
- **13:00 Afternoon Calendar**（isolated, g53s）— 3 小時內事件提醒
- ***/2h Tunnel Watchdog**（isolated, g53s）— SSH 反向隧道自動修復
- **21:00 Daily Research Briefing**（isolated, g53s, 120s timeout）— 綜合新聞 + autodidact + artifacts → email
- **23:30 Daily Growth Report**（isolated, g53s）— 每日成長量化，常規→#bot-logs，異常→#general

### Deadline Watchdog（取代舊 one-shot cron jobs）
- **位置**: `skills/deadline_watch.py`
- **資料**: `memory/finance/deadlines.json`（11 個 deadlines）
- **觸發**: heartbeat 時跑 `deadline_watch.py --days 14`，有 alert 就通知 #general
- **舊 cron 已清除**: pathfinder-followup, ntu-intl-scholarship, ctci-scholarship-prep, ctci-registration-open, mats-research-task-prep, sept-scholarship-batch, ctci-written-deadline
