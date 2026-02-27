# Phase 2 Secret Remediation Runbook

## Purpose

This runbook executes Phase 2 of the sync/cleanup program:

1. Rotate exposed credentials.
2. Purge sensitive and generated artifacts from git history.
3. Force-push rewritten history and coordinate hard resets.

## Preconditions

- Branch protection/merge freeze window is active.
- All maintainers are informed that history will be rewritten.
- Fresh mirror backup is created before rewrite.

## Step 1: Rotate Credentials (External Systems)

Rotate and replace all credentials ever committed in this repository:

- Twilio account/auth credentials
- Textbelt API key(s)
- AWS credentials used for SNS
- Any other secrets found in committed config snapshots

Replacement policy:

- Store live values only in untracked operator-managed config or environment variables.
- Keep tracked config files placeholder-only.

## Step 2: Backup Before Rewrite

From a safe workstation:

```bash
git clone --mirror https://github.com/wbell2000/patreon-bot.git patreon-bot-mirror-backup.git
```

Archive `patreon-bot-mirror-backup.git` offline before proceeding.

## Step 3: Rewrite History

Install `git-filter-repo` if needed, then run from a fresh non-working clone:

```bash
git clone https://github.com/wbell2000/patreon-bot.git patreon-bot-rewrite
cd patreon-bot-rewrite
```

Purge generated artifacts from all history:

```bash
git filter-repo --path node_modules --path logs --path .wrangler/state --invert-paths --force
```

Optional pattern-based secret purge pass (maintain this file in secure local storage only):

```bash
cat > /tmp/replacements.txt <<'EOF'
regex:(AC[0-9a-zA-Z]{32})==>TWILIO_SID_REDACTED
regex:([0-9a-f]{40}p[A-Za-z0-9]+)==>TEXTBELT_KEY_REDACTED
EOF

git filter-repo --replace-text /tmp/replacements.txt --force
```

## Step 4: Force Push Rewritten History

```bash
git remote -v
git push origin --force --all
git push origin --force --tags
```

## Step 5: Post-Rewrite Verification

Run checks in rewritten clone:

```bash
git log --oneline -n 5
git grep -n "textbelt_api_key\\|twilio_auth_token\\|aws_secret_access_key" $(git rev-list --all) || true
git count-objects -vH
```

Then validate app behavior:

```bash
./venv/bin/pytest -q
```

## Step 6: Clone Reset Instructions (Team/CI)

Every collaborator and CI runner must hard reset/reclone:

```bash
git fetch --all --prune
git checkout main
git reset --hard origin/main
```

For long-lived CI runners, prefer full clean clone after rewrite.

## Step 7: Server Re-Sync

On remote host:

```bash
cd /home/ubuntu/patreon-bot
git fetch --all --prune
git checkout main
git reset --hard origin/main
```

Restart monitor process and verify active logs.
