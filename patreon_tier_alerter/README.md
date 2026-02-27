# Patreon Tier Alerter Bot

## Description

Patreon Tier Alerter monitors Patreon membership pages and alerts when watched tiers are available.
The repository includes:

- A Python polling bot (`patreon_tier_alerter/src/alerter.py`)
- A Cloudflare Worker implementation (`cloudflare_worker/src/worker.js`)

## Runtime Baseline

As of 2026-02-27, the dominant baseline is `origin/main` (`ceb67ff...`).
Local feature work should branch from this baseline.

## Features

- Monitors multiple creators and tier names.
- Supports SMS delivery through AWS SNS, Twilio, or Textbelt.
- Hot-reloads JSON config when the file changes.
- Rotating logs for main events, SMS events, and errors.

## Requirements

- Python 3
- `pip`
- Optional: Docker for containerized runs
- Optional: Node.js + Wrangler for Cloudflare Worker deployment

## Install (Python Bot)

From `patreon_tier_alerter`:

```bash
pip install -r requirements.txt
```

## Configuration

Default config path is `patreon_tier_alerter/config/config.json`.

### Config path resolution order

The Python bot resolves config in this exact order:

1. `PATREON_CONFIG_PATH` environment variable (if set)
2. `../config/config.json` (when running from `patreon_tier_alerter/src`)
3. `patreon_tier_alerter/config/config.json` (when running from repo root)

Use `patreon_tier_alerter/config/config.example.json` as your template.

### Top-level config keys

- `creators`: array of creator configs (`name`, `url`, `tiers_to_watch`)
- `check_interval_seconds`: polling interval
- `user_agent`: request user agent
- `sms_settings`: provider-specific SMS settings
- `dev_mode`: local debugging behavior

### SMS provider keys

- `provider=aws_sns`:
  - `aws_access_key_id`
  - `aws_secret_access_key`
  - `aws_region`
  - `recipient_phone_number`
- `provider=twilio`:
  - `twilio_account_sid`
  - `twilio_auth_token`
  - `twilio_from_number`
  - `recipient_phone_number`
- `provider=textbelt`:
  - `textbelt_api_key`
  - `recipient_phone_number`

## Run (Python Bot)

From repo root:

```bash
python patreon_tier_alerter/src/alerter.py
```

From `patreon_tier_alerter/src`:

```bash
python alerter.py
```

With explicit config path:

```bash
PATREON_CONFIG_PATH=/absolute/path/to/config.json python patreon_tier_alerter/src/alerter.py
```

## Run (Docker)

From `patreon_tier_alerter`:

```bash
docker build -t patreon-tier-alerter .
docker run -d --name patreon-alerter \
  -v /absolute/path/config.json:/app/config/config.json \
  patreon-tier-alerter
```

## Cloudflare Worker

Worker entrypoint:

- `cloudflare_worker/src/worker.js`

Wrangler config is in `wrangler.toml` (KV bindings + cron trigger).

## Artifact Policy (Repo Hygiene)

The following are runtime/build artifacts and must remain untracked:

- `node_modules/`
- `.wrangler/state/`
- `logs/`
- `patreon_tier_alerter/src/logs/`
- `*.log`

## Security Notes

- Do not commit real credentials to tracked files.
- Treat previously committed credentials as compromised and rotate them.
- Keep live secrets in untracked/operator-managed config or environment variables.

## Known Limitations

- Scraping depends on Patreon page structure and may break when markup changes.
- Alert deduplication cache is in-process memory and resets on restart.

## License

Apache 2.0.
