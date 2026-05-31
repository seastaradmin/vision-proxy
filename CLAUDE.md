# vision-proxy

A transparent proxy plugin for Claude Code that routes requests to third-party Anthropic-compatible APIs.

## What it does

- **Smart routing**: text → TEXT_MODEL, images → VISION_MODEL
- **Model name cleaning**: strips `[1m]` and similar suffixes
- **Auth bridging**: handles both `x-api-key` and `Authorization: Bearer`
- **SSE streaming**: full pass-through with unbuffered reads
- **Beta filtering**: strips unsupported `anthropic-beta` features

## Commands

- `/vision-proxy:setup` — Install, configure, and start the proxy daemon
- `/vision-proxy:status` — Check if proxy is running, view config and logs
- `/vision-proxy:stop` — Stop the daemon, optionally restore settings

## Files

- `vision-proxy.py` — The proxy script (zero dependencies, Python 3 stdlib only)
- `commands/setup.md` — Setup command instructions
- `commands/status.md` — Status command instructions
- `commands/stop.md` — Stop command instructions

## Architecture

```
Claude Code → http://127.0.0.1:8082 (vision-proxy) → upstream API
```

The proxy listens on localhost:8082. When `ANTHROPIC_BASE_URL` is set to this address, all Claude Code API traffic routes through it.

## Configuration

All via environment variables on the daemon:

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_UPSTREAM_URL` | `https://token-plan-cn.xiaomimimo.com/anthropic` | Upstream API |
| `VISION_PROXY_TEXT_MODEL` | `mimo-v2.5-pro` | Text model |
| `VISION_PROXY_VISION_MODEL` | `mimo-v2.5` | Vision model |
| `VISION_PROXY_PORT` | `8082` | Listen port |
