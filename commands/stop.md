---
description: Stop the vision-proxy daemon and optionally restore original API settings.
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# Stop Vision Proxy

## Step 1: Confirm

Use AskUserQuestion:
- header: "Confirm"
- question: "Stop the vision proxy? Claude Code will revert to direct API calls."
- multiSelect: false
- options:
  - "Stop proxy only" — Keep ANTHROPIC_BASE_URL pointing to localhost (can restart later)
  - "Stop and restore settings" — Remove ANTHROPIC_BASE_URL from settings.json

## Step 2: Stop the daemon

**macOS:**
```bash
launchctl unload ~/Library/LaunchAgents/com.vision-proxy.plist 2>/dev/null || true
```

**Linux:**
```bash
systemctl --user stop vision-proxy 2>/dev/null || true
```

**Fallback:**
```bash
pkill -f "vision-proxy.py" 2>/dev/null || true
```

## Step 3: Restore settings (if chosen)

Read `~/.claude/settings.json`, remove `ANTHROPIC_BASE_URL` from the `env` block. Preserve all other env vars.

## Step 4: Done

> ✅ Vision proxy stopped.
> {If settings restored: "ANTHROPIC_BASE_URL removed — Claude Code will use the upstream API directly."}
> {If settings kept: "Run `/vision-proxy:setup` or `python3 ~/.claude/bin/vision-proxy.py` to restart."}
