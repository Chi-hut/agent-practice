"""
DeepAgent 请求与返回值全量实例导出（HTTP 层，与 dump_request/dump_response 同源机制）

deep agent 执行一轮任务 = 多次真实 HTTP 调用（模型每决策一次就发一次请求）。
本文件用 httpx 请求/响应钩子把 deep agent 发出的每一轮请求和拿回的每一份原始
响应完整截获，回答一个问题：**deep agent 场景下，HTTP 层的请求和返回值长什么样**。

报告主体就一件事：按轮次成对呈现真实的输入与输出，每一轮结构相同、全字段无省略：
- 输入：请求行 + 全部请求头 + 请求体完整 JSON（内置系统提示全文、全部工具 schema、
  累积的 messages）
- 输出：状态行 + 全部响应头 + 响应体完整 JSON（choices / tool_calls / usage 全字段）

4 轮各自完整成对，不做"精讲 + 补全"式拆分；请求体只保留美化版（原始单行内容相同，
不重复呈现）；末尾附程序化比对结论与实测要点。

运行方式（在项目根目录下执行）：
    python -m agent.deep_agent_dump
生成文件：项目根目录 deep_agent_dump_output.md
"""

import json
import re
import time
from pathlib import Path

import httpx
from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# 兼容两种运行方式（与 dump_request.py 同样的处理）
try:
    from agent.llm import add_user_key, llm as base_llm
except ImportError:
    from llm import add_user_key, llm as base_llm

# 与 agent/deep_agent_demo.py 相同的任务，便于两份报告对照
QUESTION = ("先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，"
            "把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。")

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "deep_agent_dump_output.md"


@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果，例如 "3 * (4 + 5)"。"""
    if not set(expression) <= set("0123456789+-*/(). "):
        return f"表达式含非法字符，拒绝计算：{expression}"
    try:
        return str(eval(expression))
    except Exception as exc:
        return f"计算失败：{exc}"


# ==================== 1. 捕获：请求/响应钩子 ====================
captured: list[dict] = []          # 每项 {"request": {...}, "response": {...}}
_last_req_start: list[float] = []  # 请求发出时刻（算每轮耗时用）


def _http_version(ext_value) -> str:
    """extensions 里的 http_version 实测可能是 bytes（如 b'HTTP/1.1'），统一解码成 str。"""
    if isinstance(ext_value, bytes):
        return ext_value.decode("utf-8")
    return str(ext_value) if ext_value else "HTTP/1.1"


def capture_request(request: httpx.Request):
    """请求钩子：与 add_user_key 同链且注册在其后，截到的 URL 是注入 user_key 后的最终形态。"""
    request.read()  # 把请求体读进缓存（不影响发送），响应钩子里统一取
    _last_req_start.append(time.perf_counter())


def capture_response(response: httpx.Response):
    """响应钩子：response.read() 后可拿完整响应体；response.request 反查配对的请求。"""
    response.read()
    req = response.request
    start = _last_req_start.pop(0) if _last_req_start else time.perf_counter()
    captured.append({
        "request": {
            "method": req.method,
            "path_query": req.url.raw_path.decode("utf-8"),
            "http_version": _http_version(req.extensions.get("http_version")),
            "url": str(req.url),
            "headers": dict(req.headers),
            "body_text": req.content.decode("utf-8"),
        },
        "response": {
            "status_code": response.status_code,
            "http_version": _http_version(response.extensions.get("http_version")),
            "reason_phrase": response.reason_phrase,
            "headers": dict(response.headers),
            "body_text": response.text,
            "elapsed_s": round(time.perf_counter() - start, 2),
        },
    })


http_client = httpx.Client(event_hooks={
    "request": [add_user_key, capture_request],
    "response": [capture_response],
})

# 模型配置沿用 agent/llm.py，只换上带捕获钩子的 http 客户端
capture_llm = ChatOpenAI(
    model=base_llm.model_name,
    api_key=base_llm.openai_api_key,
    base_url=base_llm.openai_api_base,
    http_client=http_client,
)

agent = create_deep_agent(
    model=capture_llm,
    tools=[calculate],
    system_prompt="你是一名严谨的助手。涉及计算必须调用 calculate 工具，不要自己心算。",
)


# ==================== 2. 脱敏（凭证不进导出文件） ====================
def mask_secret(value: str, keep: int = 6) -> str:
    return value[:keep] + "***" if len(value) > keep else "***"


def mask_header_value(name: str, value: str) -> str:
    if name == "authorization":
        scheme, _, key = value.partition(" ")
        return f"{scheme} {mask_secret(key)}" if key else mask_secret(value)
    if name == "set-cookie":
        return mask_secret(value)
    return value


def mask_query(text: str) -> str:
    return re.sub(r"(user_key=)([^&]+)", lambda m: m.group(1) + mask_secret(m.group(2)), text)


def to_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


# ==================== 3. 渲染 ====================
def round_purpose(resp_body: dict, n_msgs: int) -> str:
    """从响应体提炼一句话，说明模型这轮干了什么（轮次标题定位用）。"""
    choices = resp_body.get("choices") or []
    finish = choices[0].get("finish_reason") if choices else "-"
    tool_calls = (choices[0].get("message", {}) if choices else {}).get("tool_calls") or []
    names = [tc.get("function", {}).get("name") for tc in tool_calls]
    what = f"模型发起工具调用 `{', '.join(names)}`" if names else "模型给出最终文本回答"
    return f"{what}（finish_reason=`{finish}`，messages {n_msgs} 条）"


def render_round(i: int, item: dict) -> list[str]:
    """一轮 = 真实输入（请求）+ 真实输出（响应），全字段完整呈现，仅凭证脱敏。"""
    req, resp = item["request"], item["response"]
    req_body = json.loads(req["body_text"])
    resp_body = json.loads(resp["body_text"])
    n_msgs = len(req_body.get("messages", []))

    md = [f"## 第 {i} 轮：{round_purpose(resp_body, n_msgs)}\n"]

    md.append("### 输入（HTTP 请求）\n")
    md.append("```text")
    md.append(f"{req['method']} {mask_query(req['path_query'])} {req['http_version']}")
    for k, v in req["headers"].items():
        md.append(f"{k}: {mask_header_value(k, v)}")
    md.append("```\n")
    md.append("请求体（完整 JSON，全字段无省略）：\n")
    md.append("```json")
    md.append(to_json(req_body))
    md.append("```\n")

    md.append("### 输出（HTTP 响应）\n")
    md.append("```text")
    md.append(f"HTTP/{resp['http_version'].split('/')[-1]} {resp['status_code']} "
              f"{resp['reason_phrase']}  （本轮耗时 {resp['elapsed_s']}s）")
    for k, v in resp["headers"].items():
        md.append(f"{k}: {mask_header_value(k, v)}")
    md.append("```\n")
    md.append("响应体（完整 JSON，全字段无省略）：\n")
    md.append("```json")
    md.append(to_json(resp_body))
    md.append("```\n")
    return md


def render_overview() -> list[str]:
    md = ["## 轮次总览（deep agent 跑一次任务 = 多次 HTTP 调用）\n"]
    md.append("| 轮次 | messages 条数 | 请求体字节 | 响应体字节 | finish_reason | 输出 tokens | 请求带 cookie | 耗时 |")
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for i, item in enumerate(captured, 1):
        req_body = json.loads(item["request"]["body_text"])
        resp_body = json.loads(item["response"]["body_text"])
        usage = (resp_body.get("usage") or {}).get("completion_tokens")
        finish = "-"
        choices = resp_body.get("choices") or []
        if choices:
            finish = choices[0].get("finish_reason")
        has_cookie = "cookie" in item["request"]["headers"]
        md.append(f"| {i} | {len(req_body.get('messages', []))} | {len(item['request']['body_text'])} "
                  f"| {len(item['response']['body_text'])} | `{finish}` | `{usage}` "
                  f"| {'是' if has_cookie else '否'} | {item['response']['elapsed_s']}s |")
    md.append("")
    return md


def verify_rounds_consistency() -> str:
    """程序化比对：第 2 轮起的请求体除 messages 外是否与第 1 轮逐值一致。"""
    first_body = json.loads(captured[0]["request"]["body_text"])
    non_msg_keys = [k for k in first_body if k != "messages"]
    verdicts = []
    for i, item in enumerate(captured[1:], 2):
        body = json.loads(item["request"]["body_text"])
        diff = [k for k in non_msg_keys
                if json.dumps(body.get(k), ensure_ascii=False, sort_keys=True)
                != json.dumps(first_body.get(k), ensure_ascii=False, sort_keys=True)]
        verdicts.append("一致" if not diff else f"差异键 {', '.join(diff)}")
    return "；".join(f"第 {i} 轮{v}" for i, v in enumerate(verdicts, 2))


def main() -> None:
    print(">> 运行 deep agent（每轮模型调用都会被钩子截获）...")
    t0 = time.perf_counter()
    agent.invoke({"messages": [HumanMessage(QUESTION)]})
    total = time.perf_counter() - t0
    http_client.close()
    print(f">> 完成：共 {len(captured)} 轮 HTTP 调用，总耗时 {total:.2f}s")

    md: list[str] = []
    md.append("# Deep Agent HTTP 输入与输出实例\n")
    md.append(f"- 任务：{QUESTION}")
    md.append(f"- 模型：`{base_llm.model_name}` ｜ deepagents：`0.4.12` ｜ 端点：`POST /chat/completions` "
              f"｜ invoke 总耗时：{total:.2f}s")
    md.append(f"- 采集方式：httpx 请求/响应钩子（与 agent/llm.py 注入 user_key 同一机制），"
              f"共截获 **{len(captured)}** 轮；每轮按相同结构完整呈现真实的输入与输出")
    md.append("- 凭证脱敏：`authorization` 头 / `user_key` 参数 / `set-cookie` 只保留前 6 位\n")

    md += render_overview()
    for i, item in enumerate(captured, 1):
        md += render_round(i, item)

    md.append("## 实测要点\n")
    md.append(f"- 请求体比对（程序化）：{verify_rounds_consistency()}——"
              "tools、model、stream 等每轮原样重发，上下文只靠 messages 逐轮累积")
    md.append("- 请求体 `tools` 共 9 个 = 8 个内置（write_todos、ls、read_file、write_file、"
              "edit_file、glob、grep、task）+ calculate（我们传入的）")
    md.append("- messages 第 1 条 system 的 content 是**分段 text 数组**而非纯字符串"
              "（你的 system_prompt 在第一段，deep agent 内置长提示分段跟在后面）")
    md.append("- 响应 `tool_calls[].function.arguments` 是 **JSON 字符串**而非对象，由框架解析后执行工具")
    md.append("- cookie 从第 2 轮起出现：网关首次响应 Set-Cookie 后，httpx 同一 Client 自动回带")
    md.append("- `usage.prompt_tokens` 每轮 6000+：内置长提示每轮重发，这就是 deep agent 的成本特征")

    REPORT_PATH.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"报告已生成: {REPORT_PATH}")


if __name__ == "__main__":
    main()
