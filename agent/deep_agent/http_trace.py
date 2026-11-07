"""
HTTP 层输入输出观测：截获 agent 每一次调模型的完整请求与原始响应。

用法（包住任意一次 invoke / stream）：
    from agent.deep_agent.http_trace import trace_http

    with trace_http():
        response = agent.invoke({...})

退出 with 时按轮次打印：请求行 + 请求头 + 请求体完整 JSON，状态行 + 响应头 + 响应体完整 JSON，
并写入同内容的 Markdown 文件（默认项目根目录 deep_agent_http_trace.md，含内网域名，已 gitignore）。
authorization 头与 user_key 参数只保留前 6 位。
"""

import json
import re
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

from agent.llm import async_http_client, http_client

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "deep_agent_http_trace.md"


def _mask(value: str) -> str:
    return value[:6] + "***" if len(value) > 6 else "***"


def _mask_url(url: str) -> str:
    return re.sub(r"(user_key=)([^&]+)", lambda m: m.group(1) + _mask(m.group(2)), url)


def _mask_headers(headers: httpx.Headers) -> dict:
    out = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            scheme, _, token = v.partition(" ")
            v = f"{scheme} {_mask(token)}"
        out[k] = v
    return out


def _pretty(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return text  # 流式 SSE 等非 JSON 响应原样输出


def _summary(req_body: bytes, resp_body: bytes) -> str:
    try:
        req = json.loads(req_body)
        roles = [m.get("role") for m in req.get("messages", [])]
        tools = [t["function"]["name"] for t in req.get("tools", [])]
        parts = [f"messages={len(roles)} {roles}", f"tools={tools}"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return ""
    try:
        resp = json.loads(resp_body)
        choice = resp["choices"][0]
        calls = [c["function"]["name"] for c in choice["message"].get("tool_calls") or []]
        parts.append(f"finish_reason={choice.get('finish_reason')} tool_calls={calls}")
        parts.append(f"usage={resp.get('usage')}")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        pass
    return "\n".join(parts)


def _render(records: list[dict]) -> str:
    lines = [f"# HTTP 调用全量记录（共 {len(records)} 次请求）", ""]
    for i, r in enumerate(records, 1):
        lines += [
            f"## 第 {i} 次请求（耗时 {r['elapsed_ms']} ms）", "",
            "### 摘要", "```", r["summary"], "```", "",
            "### 请求", "```http", f"{r['method']} {r['url']}",
            *[f"{k}: {v}" for k, v in r["req_headers"].items()], "```", "",
            "### 请求体", "```json", r["req_body"], "```", "",
            "### 响应", "```http", f"HTTP {r['status']}",
            *[f"{k}: {v}" for k, v in r["resp_headers"].items()], "```", "",
            "### 响应体", "```json", r["resp_body"], "```", "",
        ]
    return "\n".join(lines)


@contextmanager
def trace_http(output: str | Path | None = DEFAULT_OUTPUT, console: bool = True):
    """output=None 时不写文件；console=False 时不打印。"""
    records: list[dict] = []
    started: dict[int, float] = {}

    def on_request(request: httpx.Request):
        request.read()
        started[id(request)] = time.perf_counter()

    def on_response(response: httpx.Response):
        response.read()
        req = response.request
        t0 = started.pop(id(req), time.perf_counter())
        records.append({
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
            "method": req.method,
            "url": _mask_url(str(req.url)),
            "req_headers": _mask_headers(req.headers),
            "req_body": _pretty(req.content),
            "status": response.status_code,
            "resp_headers": dict(response.headers),
            "resp_body": _pretty(response.content),
            "summary": _summary(req.content, response.content),
        })

    async def on_request_async(request: httpx.Request):
        await request.aread()
        started[id(request)] = time.perf_counter()

    async def on_response_async(response: httpx.Response):
        await response.aread()
        on_response(response)

    hooks = [
        (http_client, "request", on_request), (http_client, "response", on_response),
        (async_http_client, "request", on_request_async), (async_http_client, "response", on_response_async),
    ]
    for client, kind, fn in hooks:
        client.event_hooks[kind].append(fn)
    try:
        yield records
    finally:
        for client, kind, fn in hooks:
            client.event_hooks[kind].remove(fn)
        report = _render(records)
        if console:
            print("\n" + report)
        if output is not None:
            Path(output).write_text(report, encoding="utf-8")
            print(f"\n[http_trace] 已写入 {output}")
