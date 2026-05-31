# vision-proxy

Zero-dependency transparent proxy for routing Claude Code to third-party Anthropic-compatible APIs with smart model routing and vision support.

## Problem

When using Claude Code with a third-party Anthropic-compatible API (e.g. a Chinese model provider), you face two issues:

1. **Vision requests fail** — the upstream may route text and image requests to different models, but Claude Code sends everything to one endpoint.
2. **Model-name quirks** — Claude Code appends context-window suffixes like `[1m]` to model names, which some upstreams reject.

vision-proxy sits between Claude Code and your upstream API, automatically splitting traffic:

- **Text requests** go to the text-specialized model (e.g. `mimo-v2.5-pro`)
- **Image requests** go to the vision-capable model (e.g. `mimo-v2.5`)
- Model-name suffixes are cleaned before forwarding

## Quick Start

### 1. Download

```bash
curl -O https://raw.githubusercontent.com/ping/vision-proxy/main/vision-proxy.py
```

Or clone the repo:

```bash
git clone https://github.com/ping/vision-proxy.git
cd vision-proxy
```

### 2. Configure environment variables

```bash
export ANTHROPIC_UPSTREAM_URL="https://your-upstream.example.com/anthropic"
export ANTHROPIC_API_KEY="your-api-key"
```

### 3. Run

```bash
python3 vision-proxy.py
```

Then point Claude Code at the proxy:

```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:8082"
claude
```

That's it. Claude Code will transparently route through the proxy.

## Configuration

All configuration is via environment variables — no config files needed.

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_UPSTREAM_URL` | `https://token-plan-cn.xiaomimimo.com/anthropic` | Upstream Anthropic-compatible API base URL |
| `VISION_PROXY_UPSTREAM` | *(same as above)* | Alias for `ANTHROPIC_UPSTREAM_URL` |
| `VISION_PROXY_TEXT_MODEL` | `mimo-v2.5-pro` | Model for text-only requests |
| `VISION_PROXY_VISION_MODEL` | `mimo-v2.5` | Model for requests containing images |
| `VISION_PROXY_PORT` | `8082` | Port the proxy listens on |

Environment priority: `ANTHROPIC_UPSTREAM_URL` > `VISION_PROXY_UPSTREAM` > built-in default.

## How It Works

```
┌──────────────┐        ┌────────────────┐        ┌──────────────────┐
│  Claude Code  │──────▶│  vision-proxy  │──────▶│  Upstream API    │
│  (client)     │◀──────│  :8082         │◀──────│  (Anthropic-     │
│               │  SSE   │                │  SSE   │   compatible)    │
└──────────────┘        └────────────────┘        └──────────────────┘

Request flow:
  1. Claude Code sends POST /v1/messages
  2. Proxy inspects message content:
     - Has images?  → forward with VISION_MODEL
     - Text only?   → forward with TEXT_MODEL (+ strip [1m] suffix)
  3. Proxy streams upstream response back to Claude Code
```

The proxy is fully transparent for all other endpoints (`/v1/complete`, etc.) — they pass through unchanged.

## Supported Features

- **Smart model routing** — automatically detects image content and routes to the appropriate model
- **SSE streaming** — full Server-Sent Events pass-through (Claude Code's default mode)
- **Tool result image detection** — finds images nested inside `tool_result` blocks (screenshots, etc.)
- **Model name cleaning** — strips `[1m]` and similar suffixes that upstream APIs reject
- **Beta header filtering** — forwards only supported `anthropic-beta` features
- **Health check endpoint** — `GET /` and `GET /health` return proxy status JSON
- **Zero dependencies** — uses only Python 3 standard library (`http.server`, `json`, `subprocess`)
- **Thread-safe** — uses `ThreadingHTTPServer` for concurrent requests

## Requirements

- Python 3.7+
- `curl` (used for upstream forwarding)
- No pip packages required

## License

MIT License. See [LICENSE](LICENSE) for details.
