#!/usr/bin/env python3
"""Fetch today's (or tomorrow's) Google Calendar events for Leo."""
import json, argparse
from datetime import datetime, timedelta, timezone
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

CREDS_PATH = '/Users/leonardo/.openclaw/workspace/secrets/google-service-account.json'
CAL_ID = 'leonardofoohy@gmail.com'
TZ = timezone(timedelta(hours=8))


def get_events(days_ahead=0, days_range=1):
    """Get events starting from `days_ahead` days from now, spanning `days_range` days."""
    creds = Credentials.from_service_account_file(
        CREDS_PATH, scopes=['https://www.googleapis.com/auth/calendar.readonly'])
    service = build('calendar', 'v3', credentials=creds)

    now = datetime.now(TZ)
    base = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = base + timedelta(days=days_range)

    result = service.events().list(
        calendarId=CAL_ID,
        timeMin=base.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = []
    for e in result.get('items', []):
        start = e['start'].get('dateTime', e['start'].get('date'))
        end_t = e['end'].get('dateTime', e['end'].get('date'))
        events.append({
            'summary': e.get('summary', '(no title)'),
            'start': start,
            'end': end_t,
            'location': e.get('location'),
            'description': (e.get('description') or '')[:200],
            'all_day': 'date' in e['start'],
        })
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days-ahead', type=int, default=0,
                    help='0=today, 1=tomorrow, etc.')
    ap.add_argument('--days-range', type=int, default=1,
                    help='How many days to span')
    args = ap.parse_args()

    events = get_events(args.days_ahead, args.days_range)
    date_label = (datetime.now(TZ) + timedelta(days=args.days_ahead)).strftime('%Y-%m-%d')

    output = {
        'date': date_label,
        'count': len(events),
        'events': events
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
