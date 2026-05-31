---
description: Install and start vision-proxy — auto-routes Claude Code to your third-party Anthropic API with smart model routing.
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# Setup Vision Proxy

This command sets up a local proxy between Claude Code and your third-party Anthropic-compatible API.

## Step 0: Check Python

```bash
command -v python3 && python3 --version
```

If not found, tell the user to install Python 3.7+ first.

## Step 1: Ask for upstream configuration

Use AskUserQuestion to get:

**Q1: Upstream API URL**
- header: "API URL"
- question: "What is your Anthropic-compatible API base URL?"
- multiSelect: false
- options:
  - "https://token-plan-cn.xiaomimimo.com/anthropic" — Xiaomi MiMo (default)
  - "Custom URL" — Enter your own endpoint

If custom, ask for the URL.

**Q2: API Key**
- header: "API Key"
- question: "Enter your API key for the upstream service:"
- multiSelect: false
- options:
  - "Use existing ANTHROPIC_AUTH_TOKEN from settings" — Read from ~/.claude/settings.json
  - "Enter new key" — Provide the key

**Q3: Models**
- header: "Models"
- question: "Which models should the proxy route to?"
- multiSelect: false
- options:
  - "mimo-v2.5-pro (text) + mimo-v2.5 (vision)" — Default MiMo setup
  - "Custom models" — Enter text and vision model names

## Step 2: Copy proxy script

```bash
# Determine plugin install path
PLUGIN_DIR=$(ls -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/vision-proxy/vision-proxy/*/ 2>/dev/null | awk -F/ '{ print $(NF-1) "\t" $0 }' | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n | tail -1 | cut -f2-)

# Copy proxy to a stable location
mkdir -p ~/.claude/bin
cp "${PLUGIN_DIR}vision-proxy.py" ~/.claude/bin/vision-proxy.py
chmod +x ~/.claude/bin/vision-proxy.py
echo "Copied to ~/.claude/bin/vision-proxy.py"
```

## Step 3: Kill any existing proxy

```bash
pkill -f "vision-proxy.py" 2>/dev/null || true
sleep 1
```

## Step 4: Start proxy as background daemon

Based on platform:

**macOS (launchd — auto-restarts on crash, starts on login):**

Create `~/Library/LaunchAgents/com.vision-proxy.plist`:

```bash
cat > ~/Library/LaunchAgents/com.vision-proxy.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vision-proxy</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(command -v python3)</string>
        <string>$HOME/.claude/bin/vision-proxy.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_UPSTREAM_URL</key>
        <string>{UPSTREAM_URL}</string>
        <key>VISION_PROXY_TEXT_MODEL</key>
        <string>{TEXT_MODEL}</string>
        <key>VISION_PROXY_VISION_MODEL</key>
        <string>{VISION_MODEL}</string>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/.claude/vision-proxy.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.claude/vision-proxy.log</string>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.vision-proxy.plist
```

**Linux (systemd user service):**

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/vision-proxy.service << EOF
[Unit]
Description=Vision Proxy for Claude Code

[Service]
ExecStart=$(command -v python3) $HOME/.claude/bin/vision-proxy.py
Environment=ANTHROPIC_UPSTREAM_URL={UPSTREAM_URL}
Environment=VISION_PROXY_TEXT_MODEL={TEXT_MODEL}
Environment=VISION_PROXY_VISION_MODEL={VISION_MODEL}
Restart=always

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable vision-proxy
systemctl --user start vision-proxy
```

**Fallback (nohup — works everywhere):**

```bash
ANTHROPIC_UPSTREAM_URL="{UPSTREAM_URL}" \
VISION_PROXY_TEXT_MODEL="{TEXT_MODEL}" \
VISION_PROXY_VISION_MODEL="{VISION_MODEL}" \
nohup python3 ~/.claude/bin/vision-proxy.py > ~/.claude/vision-proxy.log 2>&1 &
echo $! > ~/.claude/vision-proxy.pid
```

Replace `{UPSTREAM_URL}`, `{TEXT_MODEL}`, `{VISION_MODEL}` with the values from Step 1.

## Step 5: Verify proxy is running

```bash
sleep 2
curl -s --max-time 5 http://127.0.0.1:8082/ | python3 -m json.tool
```

Should return `{"status": "ok", ...}`. If not, check the log:

```bash
tail -5 ~/.claude/vision-proxy.log
```

## Step 6: Configure Claude Code settings

Read `~/.claude/settings.json`. Merge in the `env` block:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8082"
  }
}
```

**IMPORTANT**: Only set `ANTHROPIC_BASE_URL`. Do NOT overwrite other env vars like `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_MODEL` — merge them.

If the file doesn't exist, create it. If it has invalid JSON, report the error.

## Step 7: Done

Tell the user:

> ✅ Vision proxy is running on http://127.0.0.1:8082
>
> **Please restart Claude Code now** — quit and run `claude` again.
> After restart, all API requests will route through the proxy:
> - Text → `{TEXT_MODEL}`
> - Images → `{VISION_MODEL}`
>
> The proxy runs as a background daemon and auto-starts on login.
> Use `/vision-proxy:status` to check, `/vision-proxy:stop` to stop.
