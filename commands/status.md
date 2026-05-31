---
description: Check vision-proxy status — is it running, what models are configured, recent logs.
allowed-tools: Bash, Read
---

# Vision Proxy Status

## Check if proxy is running

```bash
# Health check
curl -s --max-time 3 http://127.0.0.1:8082/ 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "PROXY_NOT_REACHABLE"
```

## Check process

```bash
pgrep -f "vision-proxy.py" >/dev/null && echo "Process: running" || echo "Process: NOT running"
```

## Check daemon status

**macOS:**
```bash
launchctl list | grep vision-proxy 2>/dev/null || echo "No launchd service"
```

**Linux:**
```bash
systemctl --user status vision-proxy 2>/dev/null || echo "No systemd service"
```

## Check Claude Code config

```bash
python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print('ANTHROPIC_BASE_URL:', d.get('env',{}).get('ANTHROPIC_BASE_URL','NOT SET'))" 2>/dev/null || echo "No settings.json"
```

## Recent logs

```bash
tail -10 ~/.claude/vision-proxy.log 2>/dev/null || echo "No log file"
```

## Summary

Display a status card:

```
┌─ Vision Proxy ─────────────────────┐
│ Status:  ✅ running / ❌ stopped    │
│ URL:     http://127.0.0.1:8082     │
│ Text:    mimo-v2.5-pro             │
│ Vision:  mimo-v2.5                 │
│ Upstream: https://...              │
│ Config:  ✅ / ❌ not configured     │
└────────────────────────────────────┘
```
