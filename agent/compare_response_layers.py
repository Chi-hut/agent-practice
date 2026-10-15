"""
响应两层对照 Demo：服务端原始 JSON vs LangChain AIMessage

背景：直接用 curl 调模型 API（或看网关日志）时看到的是一层 JSON（OpenAI 协议的
chat.completion 对象），而 llm.invoke() 返回的是 LangChain 的 AIMessage——两者字段
长得完全不一样，但其实是同一份数据经过两层加工后的形态。本脚本就做这件事：

同一次 llm.invoke() 调用，从两个抽象层各截一份、并排导出：
- 原始层（第二章）：httpx 响应钩子在响应到达时抄下的 HTTP 响应体——与 curl 直接调
  API 拿到的 JSON 完全一致（dump_request.md 里的等价 curl 命令拿到的就是它）
- LangChain 层（第三章）：invoke() 返回的 AIMessage 的 model_dump（与 dump_response.py
  同款导出方式）

第四章把两层字段逐一对照（同一行并排两边的实测值），第五章列出两层各自的完整
字段清单（一个叶子字段都不漏），第六章讲 LangChain 为什么要隔这一层。

运行方式（在项目根目录下执行）：
    python -m agent.compare_response_layers

生成文件：项目根目录下 response_layers.md
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import httpx
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

# 兼容两种运行方式（与 dump_response.py 同样的处理）：
#   python -m agent.compare_response_layers    -> 能找到 agent 包，走 agent.llm
#   python agent\\compare_response_layers.py   -> sys.path 里只有 agent 目录，直接 import 同级的 llm
try:
    from agent.llm import add_user_key, llm as base_llm
except ImportError:
    from llm import add_user_key, llm as base_llm

# 与 dump_request.py 用同一个问题，保持三个导出文件之间的连续性
QUESTION = "用一句话说明什么是 HTTP 请求头"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_MD = ROOT / "response_layers.md"

# ---------------------------------------------------------------------------
# 捕获：httpx 响应钩子，响应到达时把原始响应体抄下来（与请求钩子互为镜像）
# ---------------------------------------------------------------------------

captured_responses = []


def capture_response(response: httpx.Response):
    """响应钩子：响应状态行和响应头一到就被调用。

    read() 把响应体读进缓存，之后 openai SDK 照常 .json()（用的就是这份缓存），
    因此截到的字节与网络上收到的一字不差，也不影响调用本身。
    """
    captured_responses.append(
        {
            "status_code": response.status_code,
            "http_version": response.http_version,
            "headers": dict(response.headers),
            "body_text": response.read().decode("utf-8"),
        }
    )


# ---------------------------------------------------------------------------
# 说明字典：渲染表格时按实际出现的字段取用
# ---------------------------------------------------------------------------

RESP_HEADER_NOTES = {
    "content-type": "响应体格式：JSON",
    "content-length": "响应体字节数",
    "date": "服务端生成响应的时间",
    "connection": "连接策略（keep-alive 复用连接）",
    "set-cookie": "网关（F5 负载均衡）种下的会话粘性标识，httpx 的 cookie jar 存起来、后续请求自动携带",
    "server": "处理本次请求的服务端组件（网关）",
    "x-request-id": "请求追踪 ID（排查问题时报给网关用）",
    "vary": "缓存协商头",
    "cache-control": "缓存策略",
    "transfer-encoding": "传输编码（分块传输时出现）",
}

# 原始响应 JSON 的字段说明（OpenAI 协议 chat.completion 对象）
RAW_FIELD_NOTES = {
    "id": "本次调用的唯一 ID（服务端生成）",
    "object": "对象类型标记：chat.completion = 非流式完整结果（流式分块叫 chat.completion.chunk）",
    "created": "响应生成的 Unix 时间戳（秒）",
    "model": "实际服务本次请求的模型名",
    "choices": "候选回复数组：n=1 时永远只有 1 个元素",
    "finish_reason": "停止原因：stop=自然讲完；length=被 token 上限截断；tool_calls=要调工具",
    "index": "候选序号（n>1 生成多个候选时才有意义）",
    "message": "消息本体：role + content（+ 厂商扩展字段）",
    "content": "回复正文——日常代码里用的就是它",
    "role": "恒为 assistant：表示这条是模型说的",
    "reasoning_content": "思维链：推理模型先'想'再'答'，这段是它想的过程（DeepSeek 的扩展字段）",
    "provider_specific_fields": "厂商/网关扩展字段的统一收纳处（本字段由网关补充）",
    "usage": "token 用量统计",
    "prompt_tokens": "输入消耗的 token 数",
    "completion_tokens": "输出消耗的 token 数（含思维链）",
    "total_tokens": "总 token 数",
    "completion_tokens_details": "输出 token 的细分（本次重点看 reasoning_tokens）",
    "reasoning_tokens": "思维链占的 token 数",
    "metadata": "网关附加的元数据（weight_version=本次命中的权重版本）",
}

# AIMessage 的字段说明（与 dump_response.md 的字段速查一致）
LC_FIELD_NOTES = {
    "id": "消息 ID：LangChain 自己生成的运行 ID（lc_run-- 前缀）——不是响应 JSON 里那个 id（那个在 response_metadata.id）",
    "content": "回复正文，搬运自 choices[0].message.content",
    "additional_kwargs": "厂商扩展字段收纳处（本次只收了 refusal；reasoning_content 并没有被搬进来）",
    "response_metadata": "厂商响应元数据（token_usage / model_name / finish_reason / 原始 id 等）",
    "usage_metadata": "LangChain 标准化的 token 用量（input/output/total_tokens + output_token_details.reasoning 细分）",
    "type": "消息类型：'ai' 表示这是模型说的话（表达 role=assistant 这个事实）",
    "name": "可选的说话者名字（本次未用）",
    "tool_calls": "模型发起的工具调用列表（绑定工具后才有内容，本次为空）",
    "invalid_tool_calls": "解析失败的工具调用（本次为空）",
}

# ---------------------------------------------------------------------------
# 核心对照表：原始响应字段 → AIMessage 字段（值为 None 表示该字段在 AIMessage 里消失）
# ---------------------------------------------------------------------------

MAPPINGS = [
    ("id", "response_metadata.id", "服务端调用 ID 存进 response_metadata；注意 AIMessage 顶层的 id 是 LangChain 另生成的运行 ID（lc_run-- 前缀），两者不是一回事"),
    ("choices[0].message.content", "content", "回复正文，一字不差搬过来"),
    ("choices[0].message.role", "type", "assistant 这个事实改用 type='ai' 表达（LangChain 自己的命名）"),
    ("choices[0].message.reasoning_content", None, "思维链：本次实测被丢弃——langchain-openai 1.x 的转换没搬运它，只在原始层可见（排查思维链丢失要记住这点）"),
    ("choices[0].finish_reason", "response_metadata.finish_reason", "停止原因"),
    ("model", "response_metadata.model_name", "模型名"),
    ("usage.prompt_tokens", "usage_metadata.input_tokens", "输入 token：字段名被标准化为 input_tokens"),
    ("usage.completion_tokens", "usage_metadata.output_tokens", "输出 token：字段名被标准化为 output_tokens"),
    ("usage.total_tokens", "usage_metadata.total_tokens", "总 token"),
    ("usage.completion_tokens_details.reasoning_tokens", "usage_metadata.output_token_details.reasoning", "思维链 token：注意 LangChain 的键名是 output_token_details.reasoning（没有 s、词尾也不同）"),
    ("usage", "response_metadata.token_usage", "openai 的 usage 原始结构整包也保留一份（双份并存：标准化版 + 原始版）"),
    ("choices[0].message.provider_specific_fields", "additional_kwargs", "厂商扩展收纳：本次只有 refusal 进了 additional_kwargs，里面的 reasoning_content 同样没被搬运"),
    ("object", None, "类型标记：openai SDK 反序列化时就消费掉了，用完即弃"),
    ("created", None, "Unix 时间戳：LangChain 不保留"),
    ("choices[0].index", None, "候选序号：n=1 时无意义"),
    ("metadata", None, "网关元数据（weight_version）：LangChain 不认识的字段直接丢弃"),
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def to_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def to_inline_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


_MISSING = object()


def get_path(obj, path: str):
    """按 'choices[0].message.content' 这样的路径从嵌套 dict/list 里取值。

    取不到返回 _MISSING 哨兵（区别于值本身是 None，比如 refusal: null）。
    """
    cur = obj
    for token in path.split("."):
        m = re.match(r"^(\w+)(?:\[(\d+)\])?$", token)
        if not m or not isinstance(cur, dict) or m.group(1) not in cur:
            return _MISSING
        cur = cur[m.group(1)]
        if m.group(2) is not None:
            i = int(m.group(2))
            if not isinstance(cur, list) or i >= len(cur):
                return _MISSING
            cur = cur[i]
    return cur


def leaf_paths(obj, prefix: str = "") -> list[str]:
    """列出嵌套 dict/list 的全部叶子路径（比如 'usage.completion_tokens_details.reasoning_tokens'）。"""
    paths = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths += leaf_paths(v, p) if isinstance(v, (dict, list)) and v else [p]
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            paths += leaf_paths(v, p) if isinstance(v, (dict, list)) and v else [p]
    return paths


def short(value, limit: int = 60) -> str:
    """表格单元格里的值：标量直接显示，长文本截断（完整值见对应章节的全量 JSON）。"""
    if value is None:
        return "`null`"
    if value is _MISSING:
        return "—（本次没有这个字段）"
    text = value if isinstance(value, str) else to_inline_json(value)
    if len(text) > limit:
        text = text[:limit] + "…"
    return f"`{table_cell(text)}`"


# ---------------------------------------------------------------------------
# 渲染 markdown
# ---------------------------------------------------------------------------

def render_chain_section() -> list[str]:
    md = ["## 一、先看结论：同一份数据的三层加工链条\n"]
    md.append("你贴的那种 JSON 与 `llm.invoke()` 返回值不同，不是数据丢了，而是隔着两层加工：\n")
    md.append("```text")
    md.append("服务端返回的 HTTP 响应体（JSON 文本，chat.completion 对象）")
    md.append("        │")
    md.append("        │  ① openai SDK：json.loads 反序列化 + pydantic 字段校验")
    md.append("        ▼")
    md.append("ChatCompletion 对象（openai SDK 的厂商 DTO：字段与 JSON 一一对应，文本变对象）")
    md.append("        │")
    md.append("        │  ② langchain-openai：字段搬运 + 名称标准化（prompt_tokens→input_tokens、role→type）")
    md.append("        ▼")
    md.append("AIMessage 对象（LangChain 的跨厂商统一消息模型）")
    md.append("        │")
    md.append("        │  ③ llm.invoke() 把它作为返回值交给你")
    md.append("        ▼")
    md.append("代码里拿到的 response（dump_response.md 导出的就是这一层的 model_dump）")
    md.append("```\n")
    md.append("本文件同时截获链条的首尾两端：第二章 = 第 1 层原始 JSON，第三章 = 第 3 层 AIMessage；")
    md.append("中间的 ChatCompletion（第 2 层）字段与原始 JSON 完全同名同结构，不再单独导出。\n")
    return md


def render_raw_section(resp: dict, raw: dict, total: float) -> list[str]:
    md = ["## 二、第 1 层：服务端返回的原始响应（HTTP 视角，curl 拿到的就是它）\n"]

    md.append("### 1. 状态行与响应头全量\n")
    md.append("```text")
    md.append(f"HTTP {resp['status_code']}（{resp['http_version']} 协议）")
    for k, v in resp["headers"].items():
        md.append(f"{k}: {v}")
    md.append("```\n")
    md.append("| 响应头 | 本次值 | 说明 |")
    md.append("| --- | --- | --- |")
    for k, v in resp["headers"].items():
        note = RESP_HEADER_NOTES.get(k, "网关 / 服务端附加")
        md.append(f"| `{k}` | `{table_cell(v)}` | {note} |")
    md.append("")

    md.append("### 2. 响应体（JSON 全字段，先原始后美化）\n")
    md.append("原始形态（网络上传回来的就是这个单行字节串）：")
    md.append("```text")
    md.append(resp["body_text"])
    md.append("```")
    md.append("美化形态（同一份数据，只加了缩进便于阅读）：")
    md.append("```json")
    md.append(to_json(raw))
    md.append("```\n")

    md.append("### 3. 顶层字段逐项解读\n")
    md.append("| 字段 | 本次值 | 说明 |")
    md.append("| --- | --- | --- |")
    for k, v in raw.items():
        if k == "choices":
            shown = f"数组，共 {len(v)} 个元素（展开见下节）"
        elif isinstance(v, (dict, list)):
            shown = f"`{to_inline_json(v)}`"
        else:
            shown = f"`{json.dumps(v, ensure_ascii=False)}`"
        note = RAW_FIELD_NOTES.get(k, "（见 4. 嵌套字段展开）")
        md.append(f"| `{k}` | {shown} | {note} |")
    md.append("")

    md.append("### 4. 嵌套字段展开（choices[0] / message / usage 逐个到叶子）\n")
    md.append("| 原始响应里的字段路径 | 本次值 | 说明 |")
    md.append("| --- | --- | --- |")
    for p in leaf_paths(raw):
        if "." not in p and "[" not in p:
            continue  # 顶层字段上一节讲过了
        leaf = get_path(raw, p)
        key = p.rsplit(".", 1)[-1].split("[")[0]
        note = RAW_FIELD_NOTES.get(key, "（厂商 / 网关扩展字段）")
        md.append(f"| `{p}` | {short(leaf, 80)} | {note} |")
    md.append("")
    return md


def render_lc_section(dump: dict, content_len: int) -> list[str]:
    md = ["## 三、第 3 层：llm.invoke() 返回的 AIMessage\n"]
    md.append(f"同一份响应经过 ①② 两层加工后，你在代码里拿到的对象长这样（`model_dump()` 全字段导出，")
    md.append(f"与 invoke_response.md 的导出方式一致；content 长度 {content_len} 字）：\n")
    md.append("```json")
    md.append(to_json(dump))
    md.append("```\n")
    md.append("| AIMessage 字段 | 说明 |")
    md.append("| --- | --- |")
    for k in dump:
        md.append(f"| `{k}` | {LC_FIELD_NOTES.get(k, '（见 dump_response.md 字段速查）')} |")
    md.append("")
    return md


def render_mapping_section(raw: dict, dump: dict) -> list[str]:
    md = ["## 四、字段映射对照表（核心：两边实测值并排，逐行对照看）\n"]
    md.append("| 原始响应里的字段 | AIMessage 里去哪了 | 第 1 层实测值 | 第 3 层实测值 | 说明 |")
    md.append("| --- | --- | --- | --- | --- |")
    for raw_path, lc_path, note in MAPPINGS:
        raw_cell = short(get_path(raw, raw_path), 46)
        if lc_path is None:
            lc_path_cell = "（消失，不再往下传）"
            lc_val_cell = "—"
        else:
            lc_path_cell = f"`{lc_path}`"
            lc_val_cell = short(get_path(dump, lc_path), 46)
        md.append(f"| `{raw_path}` | {lc_path_cell} | {raw_cell} | {lc_val_cell} | {note} |")
    md.append("")
    md.append("> 表里只列主要的映射关系；两边**全部**字段的完整清单见第五章（一个叶子字段都不漏）。\n")
    return md


def render_inventory_section(raw: dict, dump: dict) -> list[str]:
    md = ["## 五、两层完整字段清单（全量，无省略）\n"]
    md.append("### 1. 第 1 层（原始 JSON）的全部叶子字段\n")
    md.append("| # | 字段路径 | 本次值 |")
    md.append("| --- | --- | --- |")
    for i, p in enumerate(leaf_paths(raw), 1):
        md.append(f"| {i} | `{p}` | {short(get_path(raw, p), 70)} |")
    md.append("")
    md.append("### 2. 第 3 层（AIMessage model_dump）的全部顶层字段\n")
    md.append("| # | 字段 | 本次值 |")
    md.append("| --- | --- | --- |")
    for i, k in enumerate(dump, 1):
        md.append(f"| {i} | `{k}` | {short(dump[k], 70)} |")
    md.append("")
    md.append("### 3. 哪些是搬运、哪些是消失、哪些是新增（以本次实测为准）\n")
    md.append("- **搬运**：`content`、`finish_reason`、`model`、`usage` 全家、原始 `id`（进 response_metadata.id）")
    md.append("- **消失**：`object`、`created`（SDK 层消费掉）、`choices[0].index`（单候选无意义）、`metadata.weight_version`（网关扩展不认识）、")
    md.append("  **`reasoning_content`（思维链！langchain-openai 1.x 的转换没搬运它，要看思维链只能去原始层）**")
    md.append("- **新增（LangChain 自有）**：`type: 'ai'`（表达 role=assistant）、`id`（lc_run-- 前缀的运行 ID）、`name`、`tool_calls` / `invalid_tool_calls`（工具调用槽位，本次为空）")
    md.append("- **双份保留**：token 用量既有标准化版 `usage_metadata`，又有原始版 `response_metadata.token_usage`；")
    md.append("  `response_metadata` 里的 `model_provider` / `system_fingerprint` / `logprobs` 则是转换层补齐的元数据槽位\n")
    return md


def render_why_section() -> list[str]:
    md = ["## 六、为什么要隔这一层：LangChain 的设计动机\n"]
    md.append("类比 Java：外部第三方 API 的响应 DTO 一般不会直接渗透进业务层，而是转成自己的")
    md.append("domain model（适配器模式）。LangChain 做的就是这件事，收益有三：\n")
    md.append("1. **跨厂商统一**：LangChain / LangGraph 的上层组件（agent、memory、graph）只认")
    md.append("   AIMessage 这套模型。哪天把 OpenAI 换成 Anthropic、Ollama，响应 JSON 的字段名")
    md.append("   各不相同（比如 token 用量各家叫法都不一样），但 `invoke()` 的返回值结构不变，")
    md.append("   上层代码一行不用改。")
    md.append("2. **字段名标准化**：`prompt_tokens`→`input_tokens`、`role: assistant`→`type: 'ai'`，")
    md.append("   把各家的方言翻译成一套统一词汇。")
    md.append("3. **厂商扩展尽量不丢（但不保证全搬）**：统一的同时开了两个\"杂物抽屉\"——`additional_kwargs`")
    md.append("   （消息级扩展，本次收了 `refusal`）和 `response_metadata`（响应级元数据，原始 `id`、`token_usage` 都在）。")
    md.append("   但注意本次实测：**`reasoning_content` 没有被搬运**——想拿思维链得自己去原始层截（第二章那种），")
    md.append("   这是用统一模型要留意的代价。\n")
    md.append("另外注意：流式调用时第 1 层的形态不是单个 JSON，而是 SSE 分块文本流")
    md.append("（`chat.completion.chunk` 序列，见 stream_response.md 与 sse_raw_demo.py）；")
    md.append("分块累加（merge_chunks_demo.py 的 `+`）后与 invoke 的 AIMessage 同构——")
    md.append("统一模型让\"流式 / 非流式\"在上层看起来也是一套东西。\n")
    return md


def render_howto_section() -> list[str]:
    md = ["## 七、想自己拿到原始 JSON 的三种办法\n"]
    md.append("1. **curl 直接调**：request_payload.md 每一章第 7 节都有现成的等价 curl 命令，")
    md.append("   把脱敏值换成 agent/llm.py 里的完整密钥即可，拿到的就是本文件第二章这种 JSON。")
    md.append("2. **httpx 响应钩子**：本脚本的做法，与请求钩子（dump_request.py）互为镜像，")
    md.append("   适合想在 LangChain 体系里顺手截一份的场景。")
    md.append("3. **绕过 LangChain 直用 openai SDK**：`OpenAI(...).chat.completions.create(...)`")
    md.append("   返回 `ChatCompletion` 对象（链条第 2 层），`model_dump_json()` 一下就是与原始 JSON")
    md.append("   同构的文本——LangChain 底下用的正是它。\n")
    return md


def render_md(resp: dict, raw: dict, dump: dict, total: float) -> str:
    md = []
    md.append("# 响应两层对照：服务端原始 JSON vs LangChain AIMessage\n")
    md.append(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- 模型：`{base_llm.model_name}`")
    md.append(f"- 问题：{QUESTION}")
    md.append(f"- 调用方式：一次 `llm.invoke()`，总耗时 {total:.2f}s")
    md.append("- 截获方式：httpx **响应**钩子抄下原始响应体（第 1 层）+ `invoke()` 返回值（第 3 层），")
    md.append("  两份是**同一次调用**的数据，可逐字段对上")
    md.append("- 结论先行：你 curl 看到的 JSON 与 invoke 返回值是同一份数据的不同抽象层，映射关系见第四章\n")

    md += render_chain_section()
    md += render_raw_section(resp, raw, total)
    md += render_lc_section(dump, len(raw["choices"][0]["message"]["content"]))
    md += render_mapping_section(raw, dump)
    md += render_inventory_section(raw, dump)
    md += render_why_section()
    md += render_howto_section()
    return "\n".join(md)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("响应两层对照：同一次 invoke，原始 JSON 与 AIMessage 并排导出")
    print("=" * 70)

    # 响应钩子与请求钩子（user_key 注入）挂在同一个客户端上
    http_client = httpx.Client(
        event_hooks={"request": [add_user_key], "response": [capture_response]}
    )
    llm = ChatOpenAI(
        model=base_llm.model_name,
        api_key=base_llm.openai_api_key,
        base_url=base_llm.openai_api_base,
        http_client=http_client,
    )

    print(">> 正在发起一次 invoke 调用（响应钩子同时截获原始响应体）...")
    t0 = time.perf_counter()
    message = llm.invoke([HumanMessage(QUESTION)])
    total = time.perf_counter() - t0
    print(f"   完成，耗时 {total:.2f}s，已截获 {len(captured_responses)} 个原始响应")

    http_client.close()

    resp = captured_responses[0]
    raw = json.loads(resp["body_text"])
    dump = message.model_dump()

    print("正在渲染 markdown ...")
    OUTPUT_MD.write_text(render_md(resp, raw, dump, total), encoding="utf-8")
    print(f"已生成: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
