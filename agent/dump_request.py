"""
LLM 请求全量信息导出 Demo（与 dump_response.py 恰好一对：那个看回来的响应，这个看发出去的请求）

在 httpx 客户端上再挂一个"请求捕获钩子"——与 agent/llm.py 里注入 user_key 的钩子是同一机制、
同一时机（请求已拼装完成、即将发上网络的前一刻）——把 LangChain ChatOpenAI 实际发出的
HTTP 请求原样截获：请求行、全部请求头、请求体 JSON 一个不落，全量落盘成 markdown。

三次真实调用刻意做成递进关系，方便对比"参数都是怎么进到请求里的"：
1. invoke 最小请求：只给一条 user 消息，其余全默认 —— 看"什么都不配置"时请求体还剩几个字段
2. stream 流式请求：消息与上一步完全相同 —— 只看调用方式不同给请求体带来的差异
3. invoke 常用可选参数：system 提示词 + 多轮对话 + temperature + max_tokens —— 看可选参数怎么传

运行方式（在项目根目录下执行）：
    python -m agent.dump_request
    python agent\\dump_request.py

生成文件：项目根目录下 request_payload.md
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 兼容两种运行方式（与 dump_response.py 同样的处理）：
#   python -m agent.dump_request        -> 能找到 agent 包，走 agent.llm
#   python agent\\dump_request.py       -> sys.path 里只有 agent 目录，直接 import 同级的 llm
try:
    from agent.llm import add_user_key, llm as base_llm
except ImportError:
    from llm import add_user_key, llm as base_llm

QUESTION = "用一句话说明什么是 HTTP 请求头"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_MD = ROOT / "request_payload.md"

CN_NUM = ["一", "二", "三", "四", "五", "六", "七"]

# HTTP 消息里的 role 字符串 -> LangChain 的消息类（对照着看就明白两者是一一对应的）
ROLE_TO_LC = {
    "system": "SystemMessage",
    "user": "HumanMessage",
    "assistant": "AIMessage",
    "tool": "ToolMessage",
}

# 请求头逐项说明（渲染时只解释实际出现的头；x-stainless-* 是 openai SDK 的遥测头，见第七章）
HEADER_NOTES = {
    "authorization": "鉴权凭证，来自 ChatOpenAI(api_key=...)，格式 `Bearer <key>`",
    "content-type": "请求体格式：JSON",
    "accept": "期望的服务端响应类型",
    "host": "目标主机，从 base_url 解析出来",
    "connection": "连接策略（httpx 默认 keep-alive 长连接）",
    "content-length": "请求体的字节数",
    "accept-encoding": "本端可接受的响应压缩算法",
    "user-agent": "openai SDK 的自我标识：`OpenAI/Python <版本号>`",
    "x-stainless-lang": "openai SDK 遥测头：SDK 语言",
    "x-stainless-package-version": "openai SDK 遥测头：openai 包版本",
    "x-stainless-os": "openai SDK 遥测头：操作系统",
    "x-stainless-arch": "openai SDK 遥测头：CPU 架构",
    "x-stainless-runtime": "openai SDK 遥测头：Python 实现（CPython 等）",
    "x-stainless-runtime-version": "openai SDK 遥测头：Python 版本",
    "x-stainless-retry-count": "openai SDK 遥测头：当前第几次重试（0 = 首次发送）",
    "x-stainless-timeout": "openai SDK 遥测头：本次请求设置的超时秒数",
    "x-stainless-async": "openai SDK 遥测头：是否走异步请求",
    "x-stainless-raw-response": "openai SDK 遥测头：本次走了 with_raw_response 包装（LangChain 的非流式路径会启用，stream 不带）",
    "x-stainless-read-timeout": "openai SDK 遥测头：读超时秒数",
    "x-stainless-write-timeout": "openai SDK 遥测头：写超时秒数",
    "cookie": "网关（F5 负载均衡）在第一次响应里 Set-Cookie 下发的会话粘性标识，之后 httpx 的 cookie jar 自动携带（同 Java HttpClient 的 cookie store）：所以首个请求没有它、后续请求才有",
}

# 请求体字段逐项说明（同样只解释实际出现的字段；全量可传字段见第六章速查表）
BODY_FIELD_NOTES = {
    "messages": "对话消息数组，整段历史每次请求都全量带上",
    "model": "要调用的模型名，对应 ChatOpenAI(model=...)",
    "stream": "是否流式返回：false = 生成完一次性返回；true = SSE 分块返回",
    "stream_options": "流式附加项，include_usage=true 让最后一个分块带上 token 用量",
    "temperature": "采样随机度 0~2，越高越发散，对应 ChatOpenAI(temperature=...)",
    "max_tokens": "本次回复最多生成的 token 数，对应 ChatOpenAI(max_tokens=...)",
    "max_completion_tokens": "max_tokens 的新版字段名（OpenAI 新模型推荐用这个）",
    "top_p": "核采样参数 0~1，对应 ChatOpenAI(top_p=...)",
    "n": "一次生成几个候选回复",
    "stop": "命中即停止生成的字符串列表（最多 4 个）",
}


# ---------------------------------------------------------------------------
# 捕获：httpx 请求钩子，请求发出前把它完整抄下来
# ---------------------------------------------------------------------------

# 每个元素是一次真实发出的 HTTP 请求的完整报文信息
captured_requests = []


def capture_request(request: httpx.Request):
    """请求钩子：请求拼装完成、即将发上网络的前一刻被调用。

    与 agent/llm.py 的 add_user_key 挂在同一条链上，且注册在它之后，
    因此截到的 URL 已是注入 user_key 之后的最终形态（即真正发出去的样子）。
    read() 只是把请求体读进缓存，之后 httpx 照常发送，不影响调用本身。
    """
    captured_requests.append(
        {
            "method": request.method,
            # raw_path = 路径 + 查询串（不含协议和 host），与请求行里写的一致
            "path_query": request.url.raw_path.decode("utf-8"),
            # Request 对象没有 http_version 属性（那是 Response 的）；
            # 实际版本放在 extensions 里，未显式开启 http2 时就是 HTTP/1.1
            "http_version": request.extensions.get("http_version", "HTTP/1.1"),
            "url": str(request.url),
            "headers": dict(request.headers),
            "body_text": request.read().decode("utf-8"),
        }
    )


def build_capture_client() -> httpx.Client:
    """带捕获钩子的 httpx 同步客户端。

    钩子顺序有讲究：先 add_user_key 把网关要的查询参数追加到 URL，
    再 capture_request 抄下最终形态。本脚本只做同步调用，不需要 async 版钩子。
    """
    return httpx.Client(event_hooks={"request": [add_user_key, capture_request]})


def build_capture_llm(http_client: httpx.Client, **kwargs) -> ChatOpenAI:
    """创建用于捕获的 ChatOpenAI：模型 / key / base_url 全部沿用 agent.llm 的配置，
    避免在这里再抄一遍密钥；可选参数（temperature 等）通过 kwargs 传入。"""
    return ChatOpenAI(
        model=base_llm.model_name,
        api_key=base_llm.openai_api_key,
        base_url=base_llm.openai_api_base,
        http_client=http_client,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 脱敏：凭证只保留前几位，完整值就在 agent/llm.py 里，导出文件不携带完整密钥
# ---------------------------------------------------------------------------

def mask_secret(value: str, keep: int = 6) -> str:
    return value[:keep] + "***" if len(value) > keep else "***"


def mask_header_value(name: str, value: str) -> str:
    if name == "authorization":
        scheme, _, key = value.partition(" ")
        return f"{scheme} {mask_secret(key)}" if key else mask_secret(value)
    return value


def mask_query(text: str) -> str:
    """把 URL / 请求行里的 user_key=xxx 查询参数打码。"""
    return re.sub(r"(user_key=)([^&]+)", lambda m: m.group(1) + mask_secret(m.group(2)), text)


# ---------------------------------------------------------------------------
# 渲染 markdown
# ---------------------------------------------------------------------------

def to_json(obj) -> str:
    """dict -> 格式化 JSON 文本（美化用，数据本身与原始形态完全相同）。"""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def to_inline_json(obj) -> str:
    """单行 JSON，用于表格单元格（多行会撑破表格）。"""
    return json.dumps(obj, ensure_ascii=False, default=str)


def table_cell(text: str) -> str:
    """管道符和换行会破坏 markdown 表格，先转义掉。"""
    return text.replace("|", "\\|").replace("\n", " ")


def field_cell(key: str, value) -> str:
    """字段解读表里"本次值"列的显示：messages 只报条数（逐条展开见下一节），标量原样。"""
    if key == "messages":
        return f"数组，共 {len(value)} 条（逐条展开见下节）"
    if isinstance(value, (dict, list)):
        return f"`{to_inline_json(value)}`"
    return f"`{json.dumps(value, ensure_ascii=False)}`"


def render_request_section(idx: int, name: str, purpose: str, req: dict) -> list[str]:
    """把一次截获的请求渲染成一个完整章节：请求行 → 原始报文 → 请求头 → 请求体 → 解读 → curl。"""
    md = []
    md.append(f"## {CN_NUM[idx - 1]}、请求 {idx}：{name}\n")
    md.append(f"**这一步在干什么**：{purpose}\n")

    # --- 1. 请求行 ---
    md.append("### 1. 请求行（打到哪里去）\n")
    md.append("```text")
    md.append(f"{req['method']} {mask_query(req['path_query'])} {req['http_version']}")
    md.append(f"完整 URL：{mask_query(req['url'])}")
    md.append("```")
    md.append("地址规则：OpenAI 协议把对话接口固定在 `base_url + /chat/completions`，")
    md.append("所以端点与模型无关、永远这一个；`user_key` 是 agent/llm.py 的钩子追加的网关鉴权参数。\n")

    # --- 2. 原始 HTTP 报文 ---
    md.append("### 2. 原始 HTTP 报文（抓包视角，凭证已脱敏）\n")
    md.append("这就是本次请求在网络上真实的字节形态：请求行 + 一行一个请求头 + 空行 + 请求体。")
    md.append("```text")
    md.append(f"{req['method']} {mask_query(req['path_query'])} {req['http_version']}")
    for k, v in req["headers"].items():
        md.append(f"{k}: {mask_header_value(k, v)}")
    md.append("")
    md.append(req["body_text"])
    md.append("```\n")

    # --- 3. 请求头全量 ---
    md.append("### 3. 请求头全量（逐项导出，附来源说明）\n")
    md.append("| 请求头 | 本次值 | 它是哪来的 / 干什么用 |")
    md.append("| --- | --- | --- |")
    for k, v in req["headers"].items():
        note = HEADER_NOTES.get(k, "openai SDK / httpx 自动附加")
        md.append(f"| `{k}` | `{table_cell(mask_header_value(k, v))}` | {note} |")
    md.append("")

    # --- 4. 请求体 ---
    body = json.loads(req["body_text"])
    md.append("### 4. 请求体（JSON 全字段，先原始后美化）\n")
    md.append("原始形态（网络上传的就是这个单行字节串，与上面的报文里完全一致）：")
    md.append("```text")
    md.append(req["body_text"])
    md.append("```")
    md.append("美化形态（同一份数据，只加了缩进便于阅读）：")
    md.append("```json")
    md.append(to_json(body))
    md.append("```\n")

    # --- 5. 字段逐项解读 ---
    md.append("### 5. 请求体字段逐项解读\n")
    md.append("| 字段 | 本次值 | 说明 |")
    md.append("| --- | --- | --- |")
    for k, v in body.items():
        md.append(f"| `{k}` | {field_cell(k, v)} | {BODY_FIELD_NOTES.get(k, '（见第六章速查表）')} |")
    md.append("")

    # --- 6. messages 逐条展开 ---
    if isinstance(body.get("messages"), list):
        md.append("### 6. messages 数组逐条展开（role 与 LangChain 消息类的对应）\n")
        md.append("| # | role | content | 对应的 LangChain 类型 |")
        md.append("| --- | --- | --- | --- |")
        for i, m in enumerate(body["messages"], 1):
            role = m.get("role", "?")
            content = m.get("content", "")
            if not isinstance(content, str):
                content = to_inline_json(content)
            md.append(f"| {i} | `{role}` | {table_cell(content)} | `{ROLE_TO_LC.get(role, '?')}` |")
        md.append("")

    # --- 7. 等价 curl ---
    md.append("### 7. 等价 curl 命令（把脱敏值换成完整密钥即可直接复现）\n")
    md.append("```bash")
    parts = [f'curl -X {req["method"]} "{mask_query(req["url"])}"']
    for k in ("authorization", "content-type", "accept"):
        if k in req["headers"]:
            parts.append(f'  -H "{k}: {mask_header_value(k, req["headers"][k])}"')
    parts.append(f"  -d '{req['body_text']}'")
    md.append(" \\\n".join(parts))
    md.append("```\n")
    return md


def render_compare_section(bodies: list[dict]) -> list[str]:
    """三个请求体放同一张表：哪些字段三个都有、哪些只有部分请求才有。"""
    md = ["## 四、三次请求的请求体对比\n"]
    keys = []
    for b in bodies:
        for k in b:
            if k not in keys:
                keys.append(k)
    md.append("| 请求体字段 | 请求 1（最小 invoke） | 请求 2（stream） | 请求 3（带可选参数） |")
    md.append("| --- | --- | --- | --- |")
    for k in keys:
        cells = []
        for b in bodies:
            if k not in b:
                cells.append("—（未传）")
            elif k == "messages":
                cells.append(f"{len(b[k])} 条消息")
            elif isinstance(b[k], (dict, list)):
                cells.append(f"`{to_inline_json(b[k])}`")
            else:
                cells.append(f"`{json.dumps(b[k], ensure_ascii=False)}`")
        md.append(f"| `{k}` | " + " | ".join(cells) + " |")
    md.append("")
    return md


def render_mapping_section() -> list[str]:
    md = ["## 五、LangChain 写法 → 请求内容的映射（对照着记）\n"]
    md.append("你在 Python 里写的每一行，最终都会变成请求里的某一部分；反过来，没写的参数不会出现在请求里：\n")
    md.append("| 你在代码里写的 | 变成请求里的什么 |")
    md.append("| --- | --- |")
    md.append("| `ChatOpenAI(base_url=...)` | 请求的 URL 前缀，后面拼 `/chat/completions` |")
    md.append("| `ChatOpenAI(api_key=...)` | 请求头 `authorization: Bearer <key>`（在头里，不在 body 里！） |")
    md.append("| `ChatOpenAI(model=...)` | 请求体顶层字段 `\"model\"` |")
    md.append("| `ChatOpenAI(temperature=0.7)` | 请求体顶层字段 `\"temperature\"`（同名直传） |")
    md.append("| `ChatOpenAI(max_tokens=512)` | 请求体顶层字段 `\"max_completion_tokens\"`（新版字段名，本次实测如此，见请求 3） |")
    md.append("| `SystemMessage(\"...\")` | messages 里一条 `{\"role\":\"system\",\"content\":\"...\"}` |")
    md.append("| `HumanMessage(\"...\")` | messages 里一条 `{\"role\":\"user\",\"content\":\"...\"}` |")
    md.append("| `AIMessage(\"...\")` | messages 里一条 `{\"role\":\"assistant\",\"content\":\"...\"}`（用来传历史回复） |")
    md.append("| `llm.invoke(...)` / `llm.stream(...)` | 请求体 `\"stream\"`: false / true（同一接口，靠这个字段分流） |")
    md.append("| `agent/llm.py` 里的 user_key 钩子 | URL 查询参数 `?user_key=...`（网关要求的额外鉴权） |")
    md.append("| 没写的参数（如 top_p、stop、seed） | **不会出现在请求体里**，服务端按它自己的默认值处理 |")
    md.append("")
    return md


def render_cheatsheet_section() -> list[str]:
    md = ["## 六、OpenAI Chat Completions 协议常用可选参数速查（本次未传，但都可以传）\n"]
    md.append("| 请求体字段 | 类型 / 取值 | 作用 | ChatOpenAI 对应写法 |")
    md.append("| --- | --- | --- | --- |")
    md.append("| `temperature` | float，0~2 | 采样随机度，越高越发散（0 尽量确定） | `temperature=` |")
    md.append("| `top_p` | float，0~1 | 核采样：只在累计概率前 p 的词里挑，与 temperature 二选一 | `top_p=` |")
    md.append("| `max_tokens` / `max_completion_tokens` | int | 回复的 token 上限；新字段名是后者，langchain-openai 1.x 实际发的是它（本次实测） | `max_tokens=` |")
    md.append("| `n` | int，默认 1 | 一次生成几个候选回复 | `n=` |")
    md.append("| `stop` | str 或 list（≤4 个） | 生成命中这些串就停 | `stop=` |")
    md.append("| `presence_penalty` | -2.0~2.0 | 已出现主题再出现的惩罚（促新话题） | `presence_penalty=` |")
    md.append("| `frequency_penalty` | -2.0~2.0 | 已出现内容按频率惩罚（减少复读） | `frequency_penalty=` |")
    md.append("| `seed` | int | 随机种子，尽量让同请求可复现 | `seed=` |")
    md.append("| `response_format` | `{\"type\":\"json_object\"}` | 强制输出合法 JSON | `response_format=` |")
    md.append("| `tools` + `tool_choice` | 工具定义数组 | 工具 / 函数调用（Agent 的底座） | `llm.bind_tools([...])` |")
    md.append("| `stream_options` | `{\"include_usage\":true}` | 流式时最后一个分块带上 token 用量 | `stream_usage=True` |")
    md.append("| `logprobs` / `top_logprobs` | bool / 0~20 | 返回每个 token 的对数概率（看模型\"犹豫度\"） | `logprobs=` |")
    md.append("| `user` | str | 终端用户标识，供服务端审计 / 计费区分 | `user=` |")
    md.append("")
    return md


def render_stainless_section(req: dict) -> list[str]:
    md = ["## 七、请求头里那排 x-stainless-* 是什么\n"]
    md.append("`user-agent: OpenAI/Python x.x.x` 和一排 `x-stainless-*` 头不是 LangChain 加的，")
    md.append("而是底层的 openai 官方 Python SDK 自动附加的遥测头，用来说明 SDK 版本与运行环境，")
    md.append("服务端借此统计各版本调用量——类比 Java 里 OkHttp 默认带上自己的 User-Agent。")
    md.append("它们**不参与**鉴权与业务逻辑，纯属 SDK 自报家门。本次请求里实际出现的有：\n")
    found = {k: v for k, v in req["headers"].items() if k.startswith("x-stainless") or k == "user-agent"}
    md.append("| 请求头 | 本次实际值 | 含义 |")
    md.append("| --- | --- | --- |")
    for k, v in found.items():
        md.append(f"| `{k}` | `{table_cell(v)}` | {HEADER_NOTES.get(k, '')} |")
    md.append("")
    return md


def render_md() -> str:
    r1, r2, r3 = captured_requests  # 依次对应下面的三次调用
    bodies = [json.loads(r["body_text"]) for r in captured_requests]

    md = []
    md.append("# LLM 请求全量信息（httpx 钩子截获的真实 HTTP 请求）\n")
    md.append(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- 模型：`{base_llm.model_name}`")
    md.append(f"- base_url：`{base_llm.openai_api_base}`")
    md.append(f"- 实际请求端点：`POST {base_llm.openai_api_base}/chat/completions`（OpenAI 协议对话接口的固定路径）")
    md.append("- 捕获方式：给 httpx 客户端挂请求钩子（与 agent/llm.py 注入 user_key 同一机制），")
    md.append("  截获时机是请求拼装完成、即将发上网络的前一刻，因此与真实发出的字节一致")
    md.append("- 凭证脱敏：`authorization` 头与 `user_key` 参数只保留前 6 位，完整值就在 `agent/llm.py`")
    md.append("- 共 3 份请求，递进关系：最小 invoke → 同样消息的 stream → 带可选参数的 invoke\n")

    md += render_request_section(
        1, "invoke 最小请求（一条消息 + 全默认参数）",
        "只传一条 HumanMessage，不给任何可选参数——看看\"什么都不配置\"时请求体到底剩哪几个字段。", r1)
    md += render_request_section(
        2, "stream 流式请求（消息与请求 1 完全相同）",
        "用 llm.stream() 发出，唯一变量是调用方式——对比请求 1 看请求体多了 / 少了什么。", r2)
    md += render_request_section(
        3, "invoke 常用可选参数（system + 多轮 + temperature + max_tokens）",
        "演示一条\"配置比较全\"的调用：system 提示词、多轮历史消息、两个采样参数都是怎么进请求体的。", r3)

    md += render_compare_section(bodies)
    md += render_mapping_section()
    md += render_cheatsheet_section()
    md += render_stainless_section(r1)
    return "\n".join(md)


# ---------------------------------------------------------------------------
# 主流程：三次真实调用，每次只关心"发出了什么"，响应内容让 dump_response.py 去管
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("LLM 请求全量信息导出（3 次真实调用，捕获发出的 HTTP 请求）")
    print("=" * 70)

    http_client = build_capture_client()
    plain_llm = build_capture_llm(http_client)
    rich_llm = build_capture_llm(http_client, temperature=0.7, max_tokens=512)

    print(">> [1/3] invoke 最小请求（一条 user 消息，其余默认）...")
    t0 = time.perf_counter()
    plain_llm.invoke([HumanMessage(QUESTION)])
    print(f"   完成，耗时 {time.perf_counter() - t0:.2f}s")

    print(">> [2/3] stream 流式请求（消息与上一步完全相同）...")
    t0 = time.perf_counter()
    for _ in plain_llm.stream([HumanMessage(QUESTION)]):
        pass  # 请求在最开始的一瞬就已发出并捕获；消费完整个流只为让调用正常收尾
    print(f"   完成，耗时 {time.perf_counter() - t0:.2f}s")

    print(">> [3/3] invoke 带常用可选参数（system + 多轮 + temperature + max_tokens）...")
    t0 = time.perf_counter()
    rich_llm.invoke(
        [
            SystemMessage("你是一个严谨的 Python 助手，每次回答不超过 60 字"),
            HumanMessage("什么是生成器？"),
            AIMessage("生成器是带 yield 的函数，调用后返回一个按需惰性产值的迭代器。"),
            HumanMessage("它和列表最大的区别是什么？"),
        ]
    )
    print(f"   完成，耗时 {time.perf_counter() - t0:.2f}s")

    http_client.close()

    print(f"\n共捕获 {len(captured_requests)} 个请求，正在渲染 markdown ...")
    OUTPUT_MD.write_text(render_md(), encoding="utf-8")
    print(f"已生成: {OUTPUT_MD}")
    print("用编辑器或 Markdown 预览打开即可查看（3 份请求均为全量导出，无任何省略）")


if __name__ == "__main__":
    main()
