# Finance Automation Skill

## Overview
This skill automates financial tracking for Leo.
- **Email**: `zerotracenetwork01@gmail.com` (Ops)
- **Goal**: Monitor burn rate and runway.

## Workflow
1.  **Export**: User exports accounting data (CSV/Excel) from their app.
2.  **Send**: User emails the file to `zerotracenetwork01@gmail.com` with subject "Finance Report" or similar.
3.  **Process**: 
    -   `scripts/finance_monitor.py` checks for unread emails with attachments.
    -   Parses the attachment.
    -   Updates `memory/finance_status.json`.
    -   Calculates Burn Rate & Runway.
4.  **Report**: Sends a summary back via Discord or Email.

## Setup
- **Credentials**: Stored in `TOOLS.md`.
- **Scripts**: 
    - `scripts/finance_monitor.py`: Main logic.
    - `scripts/check_burn_rate.py`: Quick check.

## TODO
- [ ] Need sample data format (CSV headers) to write the parser.
