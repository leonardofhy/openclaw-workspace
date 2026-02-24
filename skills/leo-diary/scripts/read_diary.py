#!/usr/bin/env python3
"""
讀取並解析 Leo 的 Daily Meta-Awareness Log
優先從 Google Sheets 讀取（即時），CSV 為備援
"""
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

_WS = Path(__file__).resolve().parent.parent.parent.parent

# Google Sheets 設定
SHEET_ID = "1CRY53JyLUXdRNDtHRCJwbPMZBo7Azhpowl15-3UigWg"
CREDS_PATH = str(_WS / 'secrets' / 'google-service-account.json')

# CSV 備援路徑
CSV_PATH = str(Path.home() / "Downloads" / "Daily Meta-Awareness Log (Responses) - MetaLog.csv")

COLUMNS = {
    "timestamp": "Timestamp",
    "diary": "今天想記點什麼？",
    "mood": "今日整體心情感受",
    "energy": "今日整體精力水平如何？",
    "sleep_in": "昨晚實際入睡時間",
    "wake_up": "今天實際起床時間",
    "sleep_quality": "昨晚睡眠品質如何？",
    "completed": "今天完成了哪些？",
}

def parse_date(ts_str):
    for fmt in ('%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S'):
        try:
            return datetime.strptime(ts_str.strip(), fmt).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            continue
    return None

def load_from_sheets():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SHEET_ID).get_worksheet(0)
        return ws.get_all_records(expected_headers=list(COLUMNS.values()))
    except Exception as e:
        print(f"[warn] Google Sheets 讀取失敗，改用 CSV：{e}", file=sys.stderr)
        return None

def load_from_csv():
    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def parse_entries(raw_rows, has_diary_only=True, start_date=None, end_date=None):
    entries = []
    for row in raw_rows:
        date = parse_date(str(row.get(COLUMNS["timestamp"], "")))
        if not date:
            continue
        if start_date and date < start_date:
            continue
        if end_date and date > end_date:
            continue
        diary_text = str(row.get(COLUMNS["diary"], "")).strip()
        if has_diary_only and not diary_text:
            continue
        entries.append({
            "date": date,
            "diary": diary_text,
            "mood": str(row.get(COLUMNS["mood"], "")).strip(),
            "energy": str(row.get(COLUMNS["energy"], "")).strip(),
            "sleep_in": str(row.get(COLUMNS["sleep_in"], "")).strip(),
            "wake_up": str(row.get(COLUMNS["wake_up"], "")).strip(),
            "sleep_quality": str(row.get(COLUMNS["sleep_quality"], "")).strip(),
            "completed": str(row.get(COLUMNS["completed"], "")).strip(),
        })
    return sorted(entries, key=lambda x: x["date"])

def load_diary(start_date=None, end_date=None, has_diary_only=True, source="auto"):
    raw = None
    if source in ("auto", "sheets"):
        raw = load_from_sheets()
    if raw is None:
        raw = load_from_csv()
    return parse_entries(raw, has_diary_only=has_diary_only,
                         start_date=start_date, end_date=end_date)

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else None
    end = sys.argv[2] if len(sys.argv) > 2 else None
    entries = load_diary(start_date=start, end_date=end)
    print(f"讀取到 {len(entries)} 筆日記", file=sys.stderr)
    print(json.dumps(entries, ensure_ascii=False, indent=2))
