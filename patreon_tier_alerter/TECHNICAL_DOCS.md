# Patreon Tier Alerter - Technical Docs

## 1) Scope and Baseline

- Repository: `/Users/williamb/patreon-bot`
- Dominant baseline: `origin/main` at `ceb67ffd6686639ca65b925775d969dcf44295a8`
- Date of sync/cleanup implementation: 2026-02-27

This repository currently contains two runtime paths:

1. Python polling bot in `patreon_tier_alerter/`
2. Cloudflare Worker in `cloudflare_worker/src/worker.js`

## 2) Repository Structure

- `patreon_tier_alerter/src/alerter.py`: Python bot runtime loop, scraping, alerting, config reload.
- `patreon_tier_alerter/config/config.json`: Tracked sanitized local default.
- `patreon_tier_alerter/config/config.example.json`: Canonical template for operators.
- `patreon_tier_alerter/README.md`: Operator-facing usage documentation.
- `cloudflare_worker/src/worker.js`: Worker runtime.
- `tests/`: Python tests for Python runtime logic.
- `wrangler.toml`: Worker deployment and trigger configuration.

## 3) Python Runtime Architecture

Main loop behavior:

1. Resolve config path using deterministic precedence.
2. Load config through `ConfigManager` (with change-detection reload support).
3. For each configured creator:
   - fetch Patreon membership page
   - parse tier availability
   - check watched tiers against alert cache
   - send alerts (console/log + optional SMS provider)
4. Sleep for configured interval and repeat.

State model:

- `alerted_tiers_cache` is in-memory and process-local.
- Cache resets on process restart.

## 4) Config Loading Contract

`main()` now resolves config in this exact order:

1. `PATREON_CONFIG_PATH` environment variable (if present)
2. `../config/config.json` (when started from `patreon_tier_alerter/src`)
3. `patreon_tier_alerter/config/config.json` (when started from repo root)

This replaces server-only drift and makes local/server startup behavior reproducible.

## 5) SMS Provider Contract

Supported providers in Python runtime:

- `aws_sns`
- `twilio`
- `textbelt`

Provider keys are documented in README and represented in `config.example.json`.

## 6) Artifact Policy (Tracked vs Runtime Data)

The following are explicitly runtime/build artifacts and must not be tracked:

- `node_modules/`
- `.wrangler/state/`
- `logs/`
- `patreon_tier_alerter/src/logs/`
- `*.log`

Root `.gitignore` enforces this policy.

## 7) Test Status and Consistency

Current Python tests:

- `tests/test_check_tiers.py`: active
- `tests/test_send_alerts_twilio.py`: active
- `tests/test_worker_async.py`: intentionally skipped

Reason for skip:

- Legacy test targeted removed Python worker module (`cloudflare_worker.worker`).
- Active worker implementation is JavaScript-only at `cloudflare_worker/src/worker.js`.

## 8) Remote Server Audit Snapshot (2026-02-27)

Target host:

- `ubuntu@131.153.154.167` (`web-monitor`)
- Repo path: `/home/ubuntu/patreon-bot`

Observed runtime:

- Detached `screen` session running `python alerter.py` from `patreon_tier_alerter/src`
- Logs actively updating in `patreon_tier_alerter/src/logs/patreon_bot.log`
- Polling interval observed: 60 seconds

Git state observed on remote:

- `HEAD == origin/main == ceb67ffd6686639ca65b925775d969dcf44295a8`
- One uncommitted server-only patch existed in `patreon_tier_alerter/src/alerter.py` (config path handling)
- This cleanup ports equivalent config-resolution behavior into tracked code.

## 9) Security Remediation (Phase 2 Scope)

Historical committed credentials are treated as compromised.

Required Phase 2 actions:

1. Rotate all exposed credentials (Twilio, Textbelt, AWS, etc.).
2. Move live secrets to operator-managed untracked config and/or environment variables.
3. Rewrite git history (`git filter-repo` or BFG) to purge:
   - committed secrets
   - tracked runtime artifacts
4. Force-push rewritten history and require hard reset for all clones/runners.

## 10) Operational Checklist

Before deployment:

1. Confirm sanitized tracked config only.
2. Confirm active runtime config is provided out-of-band.
3. Confirm `git status` is clean after starting/stopping local runs.
4. Run Python tests and confirm expected pass/skip status.

After deployment:

1. Verify process exists (screen/system process list).
2. Verify current timestamp lines appear in `patreon_bot.log`.
3. Verify creator checks and interval logging are advancing.
