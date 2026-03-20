---
name: browser-automation
description: >
  Playwright-based browser automation for JS-rendered page crawling, form filling,
  screenshot/PDF capture, and cookie/session management. Anti-detection measures
  built in. Serves as backend for feed-recommend and funding-hunter.
metadata:
  { "openclaw": { "emoji": "🌐", "requires": { "anyBins": ["python3"] } } }
---

# Browser Automation

Playwright (Chromium) 驅動的無頭瀏覽器工具，可爬取 SPA/動態頁面、自動填表、截圖/PDF 輸出，並管理 cookie/session。

## Architecture

```
scripts/
  browser.py        — 主 CLI（fetch / screenshot / pdf / form / session）
  test_browser.py   — 單元測試（mock playwright）
```

## Commands

```bash
# 爬取 JS-rendered 頁面，輸出 HTML/文字
python3 browser.py fetch <url> [--text] [--wait-for <selector>] [--timeout 30000]

# 截圖
python3 browser.py screenshot <url> --output shot.png [--full-page] [--width 1280] [--height 800]

# 儲存為 PDF
python3 browser.py pdf <url> --output page.pdf [--format A4]

# 填表並提交
python3 browser.py form <url> --fill '{"#name":"Leo","#email":"x@x.com"}' [--submit "#submit"] [--screenshot result.png]

# Session 管理
python3 browser.py session save --name mysite --url https://example.com  # 互動登入後儲存 cookie
python3 browser.py session list
python3 browser.py session delete --name mysite

# 使用已儲存的 session 爬取
python3 browser.py fetch <url> --session mysite

# JSON 輸出（供其他 skill 呼叫）
python3 browser.py fetch <url> --json
```

## Integration

```python
# 作為模組使用
import sys
sys.path.insert(0, "skills/browser-automation/scripts")
from browser import fetch_page, take_screenshot, save_pdf, fill_form

html = fetch_page("https://example.com", wait_for=".content")
take_screenshot("https://example.com", "shot.png", full_page=True)
```

## Anti-Detection Measures

- 隨機 User-Agent（桌面 Chrome 版本池）
- 隱藏 `navigator.webdriver` 屬性
- 偽造 `window.chrome` 物件
- 隨機視窗大小（1280–1920 × 768–1080）
- 停用自動化相關 flag

## Data Files

| File | Purpose |
|------|---------|
| `memory/browser/sessions/<name>.json` | 已儲存的 cookie/session |

## Dependencies

```
playwright>=1.50  (pip3 install playwright && python3 -m playwright install chromium)
```
