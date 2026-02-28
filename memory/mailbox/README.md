# Mailbox (Lab ↔ Mac)

Durable fallback channel for bot-to-bot communication.

- Store: `memory/mailbox/messages.jsonl`
- IDs: `MB-xxx`
- Status: `open` -> `acked` -> `done`

Use script:
- `python3 skills/coordinator/scripts/mailbox.py send ...`
- `python3 skills/coordinator/scripts/mailbox.py list --to mac --status open`
- `python3 skills/coordinator/scripts/mailbox.py ack MB-001`
- `python3 skills/coordinator/scripts/mailbox.py done MB-001`

SLA rule:
- If no ACK in 10 minutes on Discord path, write mailbox entry with `--urgent`.
