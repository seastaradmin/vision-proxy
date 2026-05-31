#!/usr/bin/env python3
"""
vision-proxy.py — Transparent proxy that auto-routes image requests to vision-capable models.

- Text requests  -> TEXT_MODEL  (default: mimo-v2.5-pro)
- Image requests -> VISION_MODEL (default: mimo-v2.5)

Features:
  • Strips unsupported model-name suffixes (e.g. [1m]) before forwarding
  • SSE streaming pass-through (Claude Code default)
  • Health-check endpoint on GET / and GET /health
"""
__version__ = "1.0.0"

import http.server
import json
import subprocess
import sys
import os
import re

UPSTREAM = os.environ.get("ANTHROPIC_UPSTREAM_URL",
           os.environ.get("VISION_PROXY_UPSTREAM", "https://token-plan-cn.xiaomimimo.com/anthropic"))
TEXT_MODEL = os.environ.get("VISION_PROXY_TEXT_MODEL", "mimo-v2.5-pro")
VISION_MODEL = os.environ.get("VISION_PROXY_VISION_MODEL", "mimo-v2.5")
PORT = int(os.environ.get("VISION_PROXY_PORT", "8082"))


def clean_model(name):
    """Strip context-window suffixes like [1m] that upstream does not support."""
    return re.sub(r'\[.*?\]', '', name)


def has_image(messages):
    """Check whether any message contains image content.

    Detects images in top-level content blocks AND nested inside tool_result
    blocks (e.g. Claude Code screenshot attachments).
    """
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                # Direct image block
                if block.get("type") == "image":
                    return True
                # Image nested inside a tool_result block
                if block.get("type") == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, list):
                        for sub in inner:
                            if isinstance(sub, dict) and sub.get("type") == "image":
                                return True
    return False


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[proxy] {fmt % args}", file=sys.stderr)

    # ── Health check ────────────────────────────────────────────────
    def do_GET(self):
        if self.path in ("/", "/health"):
            body = json.dumps({"status": "ok", "version": __version__,
                               "text_model": TEXT_MODEL,
                               "vision_model": VISION_MODEL,
                               "upstream": UPSTREAM}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    # ── Main proxy logic ────────────────────────────────────────────
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": {"message": "Invalid JSON"}})
            return

        # Only intercept /v1/messages; pass everything else through
        if not self.path.startswith("/v1/messages"):
            self._forward(body, self.headers)
            return

        messages = data.get("messages", [])
        original_model = data.get("model", "")
        use_vision = has_image(messages)

        if use_vision:
            data["model"] = VISION_MODEL
            print(f"[proxy] Image request: {original_model} -> {VISION_MODEL}", file=sys.stderr)
        else:
            cleaned = clean_model(original_model)
            data["model"] = cleaned
            print(f"[proxy] Text request:  {original_model} -> {cleaned}", file=sys.stderr)

        out_body = json.dumps(data).encode()
        self._forward(out_body, self.headers)

    # ── Upstream forwarding ─────────────────────────────────────────
    def _forward(self, body, headers):
        """Forward request to upstream API (supports SSE streaming)."""
        url = f"{UPSTREAM}{self.path}"

        try:
            data = json.loads(body)
            is_stream = data.get("stream", False)
        except (json.JSONDecodeError, AttributeError):
            is_stream = False

        cmd = ["curl", "-N", "-s", url,
               "-H", f"Content-Type: {headers.get('Content-Type', 'application/json')}",
               "-H", f"x-api-key: {headers.get('x-api-key', '')}",
               "-H", f"anthropic-version: {headers.get('anthropic-version', '2023-06-01')}"]

        # Claude Code uses Authorization: Bearer — forward it
        auth = headers.get('Authorization', '')
        if auth:
            cmd.extend(["-H", f"Authorization: {auth}"])

        # Forward anthropic-beta (filter to only supported features)
        beta = headers.get('anthropic-beta', '')
        if beta:
            supported = [b.strip() for b in beta.split(',')
                         if b.strip() in ('prompt-caching-2024-07-31', 'max-tokens-3-5-sonnet-2024-07-15')]
            if supported:
                cmd.extend(["-H", f"anthropic-beta: {','.join(supported)}"])

        cmd.extend(["-d", "@-"])

        if is_stream:
            self._stream_forward(cmd, body)
        else:
            self._buffered_forward(cmd, body)

    def _stream_forward(self, cmd, body):
        """SSE streaming: read upstream chunks and flush to client immediately."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.stdin.write(body)
            proc.stdin.close()

            # Unbuffered read via os.read to avoid Python block-buffering SSE
            fd = proc.stdout.fileno()
            while True:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()

            proc.wait()
        except (BrokenPipeError, ConnectionResetError):
            proc.kill()
        except Exception as e:
            print(f"[proxy] stream error: {e}", file=sys.stderr)

    def _buffered_forward(self, cmd, body):
        """Non-streaming: wait for full response then return."""
        try:
            result = subprocess.run(cmd, input=body, capture_output=True, timeout=300)
            output = result.stdout
            if output:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(output)))
                self.end_headers()
                self.wfile.write(output)
            else:
                self._respond(502, {"error": {"message": "Empty response from upstream"}})
        except subprocess.TimeoutExpired:
            self._respond(504, {"error": {"message": "Upstream timeout"}})
        except Exception as e:
            self._respond(502, {"error": {"message": str(e)}})

    def _respond(self, code, body, raw=False):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if raw:
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            out = json.dumps(body).encode()
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"[proxy] Vision proxy v{__version__} on http://127.0.0.1:{PORT}", file=sys.stderr)
    print(f"[proxy]   Text   -> {TEXT_MODEL}", file=sys.stderr)
    print(f"[proxy]   Vision -> {VISION_MODEL}", file=sys.stderr)
    print(f"[proxy]   Upstream -> {UPSTREAM}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[proxy] Shutting down.", file=sys.stderr)
        server.shutdown()
