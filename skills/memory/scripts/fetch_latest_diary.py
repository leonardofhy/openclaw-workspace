#!/usr/bin/env python3
"""Fetch latest diary entry for memory rumination.

Output format: structured text that the cron agent can read and reflect on.
The agent (not this script) does the LLM thinking and decides what to save.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'leo-diary' / 'scripts'))

from read_diary import load_diary


def main():
    entries = load_diary()
    if not entries:
        print("No diary entries found.")
        return

    entries.sort(key=lambda x: x.get('date', ''), reverse=True)
    latest = entries[0]

    date = latest.get('date', 'Unknown')
    mood = latest.get('mood', '?')
    energy = latest.get('energy', '?')
    content = latest.get('diary', '')
    completed = latest.get('completed', '')

    print("---DIARY_CONTENT_START---")
    print(f"Diary Date: {date}")
    print(f"Mood: {mood}/5  Energy: {energy}/5")
    print(f"Content: {content}")
    if completed:
        print(f"Completed: {completed}")
    print("---DIARY_CONTENT_END---")


if __name__ == "__main__":
    main()
