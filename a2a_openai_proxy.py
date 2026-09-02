#!/usr/bin/env python3
"""
A2A -> OpenAI-compatible proxy for Open-LLM-VTuber.

Open-LLM-VTuber's `openai_compatible_llm` backend needs a real
/v1/chat/completions endpoint (with SSE streaming). Neither Hermes (GLaDOS)
nor OpenClaw (Wheatley) serve one natively -- they expose A2A JSON-RPC
`message/send`. This proxy translates between the two:

    POST /v1/chat/completions  {model:"glados"|"wheatley", messages:[...]}
            -> A2A message/send to the matching agent
            -> streams the agent's reply back as OpenAI SSE

    GET  /v1/models            -> lists glados, wheatley

Routing by model name:
    glados   -> Hermes   A2A  (HERMES_A2A_URL, default :9900/a2a/jsonrpc)
    wheatley -> OpenClaw A2A  (OPENCLAW_A2A_URL, default :18800/a2a/jsonrpc)

Configuration is via environment variables (current values are defaults, so
existing deployments keep working unchanged):
    A2A_PROXY_PORT             listen port            (default 8890)
    A2A_PROXY_CONTEXT_PREFIX   A2A contextId prefix   (default ollvtuber)
    OPENCLAW_CONFIG            path to openclaw.json   (~/.openclaw/openclaw.json)
    HERMES_A2A_URL             Hermes A2A endpoint
    OPENCLAW_A2A_URL           OpenClaw A2A endpoint

No external deps (stdlib only). Run: python3 a2a_openai_proxy.py
"""
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("A2A_PROXY_PORT", "8890"))
CONTEXT_PREFIX = os.environ.get("A2A_PROXY_CONTEXT_PREFIX", "ollvtuber")

# A2A endpoints + token (read from OpenClaw config so we don't hardcode secrets)
OPENCLAW_CONFIG = os.environ.get(
    "OPENCLAW_CONFIG", os.path.expanduser("~/.openclaw/openclaw.json")
)


def _load_cfg():
    cfg_path = OPENCLAW_CONFIG
    try:
        with open(cfg_path) as f:
            oc = json.load(f)
        tok = oc["plugins"]["entries"]["a2a-gateway"]["config"]["security"]["token"]
    except Exception:  # noqa: BLE001 (intentional catch-all in standalone server)
        tok = ""
    return tok


A2A_TOKEN = _load_cfg()

HERMES_A2A_URL = os.environ.get("HERMES_A2A_URL", "http://localhost:9900/a2a/jsonrpc")
OPENCLAW_A2A_URL = os.environ.get(
    "OPENCLAW_A2A_URL", "http://localhost:18800/a2a/jsonrpc"
)

# Optional per-route token override. The GLaDOS/Hermes route should carry
# Hermes's A2A token; fall back to the OpenClaw token only if unset (common
# co-resident case where both cores share one token).
HERMES_A2A_TOKEN = os.environ.get("HERMES_A2A_TOKEN")

ROUTES = {
    "glados": {"url": HERMES_A2A_URL, "token": HERMES_A2A_TOKEN or A2A_TOKEN},
    "wheatley": {"url": OPENCLAW_A2A_URL, "token": A2A_TOKEN},
}


def _rpc(endpoint, token, method, params, timeout):
    body = json.dumps({"jsonrpc": "2.0", "id": "proxy1",
                       "method": method, "params": params}).encode()
    req = urllib.request.Request(
        endpoint, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}",
                 "Accept": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _extract_text(result):
    """Pull assistant text out of an A2A result (task/message/artifact shapes)."""
    if not isinstance(result, dict):
        return None
    # artifacts shape (Hermes)
    for art in result.get("artifacts", []):
        for p in art.get("parts", []):
            if isinstance(p, dict) and p.get("text"):
                return p["text"]
    # status.message shape
    msg = result.get("status", {}).get("message")
    if isinstance(msg, dict):
        for p in msg.get("parts", []):
            if isinstance(p, dict) and p.get("text"):
                return p["text"]
    # top-level message shape
    if isinstance(result.get("message"), dict):
        for p in result["message"].get("parts", []):
            if isinstance(p, dict) and p.get("text"):
                return p["text"]
    return None


def call_agent(model, text, timeout=600):
    route = ROUTES.get(model)
    if not route:
        raise ValueError(f"unknown model {model!r}")
    ctx = f"{CONTEXT_PREFIX}-{model}"
    params = {"message": {
        "messageId": f"proxy-{int(time.time()*1000)}",
        "contextId": ctx,
        "role": "user",
        "parts": [{"kind": "text", "text": text}],
    }}
    resp = _rpc(route["url"], route["token"], "message/send", params, timeout)
    result = resp.get("result") if isinstance(resp, dict) else None
    if result is None:
        # maybe error
        err = resp.get("error") if isinstance(resp, dict) else resp
        raise RuntimeError(f"A2A error: {err}")
    # synchronous completion?
    text_out = _extract_text(result)
    if text_out:
        return text_out
    # async task: poll tasks/get
    task_id = result.get("id")
    if task_id:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(3)
            try:
                r2 = _rpc(route["url"], route["token"], "tasks/get",
                         {"id": task_id}, 30)
                res2 = r2.get("result", {})
                state = res2.get("status", {}).get("state", "")
                t = _extract_text(res2)
                if t:
                    return t
                if "COMPLETED" in str(state).upper() or "FAILED" in str(state).upper():
                    # try once more broadly
                    t = _extract_text(res2)
                    if t:
                        return t
                    if "FAILED" in str(state).upper():
                        raise RuntimeError(f"agent task failed: {state}")
            except Exception:  # noqa: BLE001,S112 (intentional catch-all + continue in standalone server)
                continue
        raise TimeoutError("agent did not complete in time")
    raise RuntimeError("no text in A2A response")


def last_user_text(messages):
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return messages[-1].get("content", "") if messages else ""


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def log_message(self, *a):
        pass  # quiet

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") in ("/v1/models", "/models"):
            body = json.dumps({
                "object": "list",
                "data": [{"id": k, "object": "model"} for k in ROUTES],
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n).decode())
        model = (payload.get("model") or "glados").lower().strip()
        if model not in ROUTES:
            # allow friendly names
            model = "glados" if "gla" in model else ("wheatley" if "wheat" in model else model)
        stream = bool(payload.get("stream", False))
        user_text = last_user_text(payload.get("messages", []))

        if not stream:
            try:
                out = call_agent(model, user_text)
            except Exception as e:  # noqa: BLE001 (intentional catch-all in standalone server)
                out = f"[proxy error: {e}]"
            body = json.dumps({
                "id": "chatcmpl-proxy",
                "object": "chat.completion",
                "model": model,
                "choices": [{"index": 0,
                             "message": {"role": "assistant", "content": out},
                             "finish_reason": "stop"}],
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # SSE streaming
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()

        def send(ev):
            self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
            self.wfile.flush()

        try:
            out = call_agent(model, user_text)
            # emit in a few chunks for nicer streaming
            step = max(1, len(out) // 8)
            for i in range(0, len(out), step):
                send({"choices": [{"index": 0, "delta": {"content": out[i:i+step]},
                                   "finish_reason": None}]})
            send({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
        except Exception as e:  # noqa: BLE001 (intentional catch-all in standalone server)
            send({"choices": [{"index": 0, "delta": {"content": f"[proxy error: {e}]"},
                               "finish_reason": "stop"}]})
        send("[DONE]")


if __name__ == "__main__":
    print(f"A2A->OpenAI proxy on :{PORT}  routes={list(ROUTES)}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
