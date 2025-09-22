# Telegram Outreach Manager

Pipeline to identify Telegram users who have messaged you but haven’t joined your channel yet, then send a personalized invite with safe throttling.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/settings.example.json config/settings.json  # fill in your values
python -m src.main collect-inbox
python -m src.main collect-members
python -m src.main send --dry   # dry run first
```
