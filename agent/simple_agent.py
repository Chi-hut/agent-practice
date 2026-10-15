"""
LangChain Agent 最小示例 + 输出全量解析报告

Agent = LLM + 工具 + 循环。和直接 llm.invoke 相比：
- 普通调用：一问一答，模型只生成文字，不能采取行动
- Agent 调用：把工具清单和问题一起给模型，模型可自主决定“调哪个工具、参数填什么”，
  框架自动执行工具、把结果塞回对话，再让模型继续判断，循环到模型不再调工具为止

本文件用 LangChain 1.x 的 create_agent 构建一个带「计算器 + 时间」两个工具的最小 agent，
把所有输出视图的完整数据（含全部消息的全字段、全部分片）原样导出为 markdown 报告：

- 【1】invoke 的完整返回值
- 【2】stream 的节点级视图（stream_mode="updates"）：agent 循环每一步的、聚合后的完整消息
- 【3】stream 的 token 级视图（stream_mode="messages"）：聚合前的 LLM 分片，与【2】严格对照
- 【4】同步 stream 与异步 astream 的输出结构对照（含异步侧逐事件全量导出）

无需盯控制台，直接打开项目根目录的 simple_agent_output.md 查看即可。

运行方式（在项目根目录下执行）：
    python -m agent.simple_agent            # 跑 invoke + stream（两路视图）+ 同步/异步对照，生成完整报告
    python -m agent.simple_agent invoke     # 只跑 invoke
    python -m agent.simple_agent stream     # 跑 stream（两路视图）+ 同步/异步对照
生成文件：项目根目录 simple_agent_output.md
"""

import asyncio
import json
import operator
import sys
from datetime import datetime
from functools import reduce
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.tools import tool

# 兼容两种运行方式（与 llm_stream.py 同样的处理）
try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = "帮我算一下 (2026 * 3 + 114) / 7，另外现在几点了？"
ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "simple_agent_output.md"


# ==================== 1. 定义工具 ====================
# @tool 把普通函数包装成 LangChain 工具，两部分信息会随工具定义一起发给模型：
#   函数名 + 参数类型注解 -> 工具的入参 schema（模型按 schema 填参数）
#   docstring            -> 工具说明（模型靠它判断“什么时候该调这个工具”）
@tool
def calculate(expression) -> str:
    """计算数学表达式并返回结果，例如 "3 * (4 + 5)"。"""
    # 只放行数字与四则运算符，避免把任意代码交给 eval 执行（演示级防护）
    if not set(expression) <= set("0123456789+-*/(). "):
        return f"表达式含非法字符，拒绝计算：{expression}"
    try:
        return str(eval(expression))
    except Exception as exc:  # 例如除零
        return f"计算失败：{exc}"

@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果，例如 "3 * (4 + 5)"。"""
    # 只放行数字与四则运算符，避免把任意代码交给 eval 执行（演示级防护）
    if not set(expression) <= set("0123456789+-*/(). "):
        return f"表达式含非法字符，拒绝计算：{expression}"
    try:
        return str(eval(expression))
    except Exception as exc:  # 例如除零
        return f"计算失败：{exc}"


@tool
def get_current_time() -> str:
    """获取当前本地日期时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS = [calculate, get_current_time]

# ==================== 2. 创建 agent ====================
# create_agent 把「模型 + 工具清单」编译成一个小状态图（底层就是 LangGraph），执行逻辑：
#   model 节点：调 LLM。若回复里带 tool_calls，则转到 tools 节点；否则它的 content 就是最终回答，结束
#   tools 节点：逐个执行工具，把结果包成 ToolMessage 追加进消息列表，然后回到 model 节点
agent = create_agent(
    model=llm,
    tools=TOOLS,
    # system_prompt="你是一名助手。只要问题涉及计算，就必须调用 calculate 工具，不要自己心算。",
    system_prompt="你是一名计算助手。",
)

# 每种消息在 agent 输出里扮演的角色（报告里作为注解）
ROLE_NOTE = {
    "human": "用户输入",
    "ai": "模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答",
    "tool": "工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）",
}


# ==================== 3. 双通道输出：控制台 + markdown 报告 ====================
class Report:
    """写入的每一行缓冲进内存、运行结束统一落盘为 markdown 文件；
    默认同时打印到控制台，file_only=True 的行只进文件（适合动辄上千行的大块 JSON）。"""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def out(self, text: str = "", file_only: bool = False) -> None:
        if not file_only:
            print(text)
        self.lines.append(text)

    def fence(self, text: str, lang: str = "", file_only: bool = False) -> None:
        """用四反引号围栏包住任意文本（内容里若出现三反引号也不会破坏 md 结构）。"""
        self.out("````" + lang, file_only=file_only)
        self.out(text, file_only=file_only)
        self.out("````", file_only=file_only)

    def save(self, path: Path) -> None:
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print(f"\n报告已生成: {path}")


def _json_default(obj):
    """Pydantic 对象（如消息实例）-> model_dump；其余非 JSON 原生类型兜底 str，保证一定能导出。"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)


def to_json(obj) -> str:
    """任意结构 -> 格式化 JSON 文本；遇到消息对象会自动 model_dump，字段一个不省。"""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default)


def dump_message(rep: Report, msg) -> None:
    """导出一条消息：先给关键字段摘要（人读），再给 model_dump 全量字段（一个不省略）。"""
    if getattr(msg, "tool_calls", None):
        for tc in msg.tool_calls:
            rep.out(f"- 工具调用指令：`{tc['name']}`，参数 `{tc['args']}`，id `{tc['id']}`")
    if msg.type == "tool":
        rep.out(f"- 执行工具：`{msg.name}`，tool_call_id `{msg.tool_call_id}`")
    if msg.type == "ai" and msg.usage_metadata:
        rep.out(f"- token 用量：`{msg.usage_metadata}`")
    rep.out("\n可读全文（pretty_repr）：\n")
    rep.fence(msg.pretty_repr(), "text")
    rep.out("\n完整字段（model_dump，一个字段不省略）：\n")
    rep.fence(to_json(msg.model_dump()), "json")


# ==================== 4. invoke：一次性拿到最终结果 ====================
def run_invoke(rep: Report) -> None:
    rep.out("\n## 【1】agent.invoke：阻塞到全部结束，一次性返回\n")
    result = agent.invoke({"messages": [HumanMessage(QUESTION)]})
    msgs = result["messages"]

    rep.out("### 顶层结构\n")
    rep.out(f"- 返回类型：`{type(result).__name__}`（注意与 llm.invoke 的区别：那里返回的是一条 AIMessage）")
    rep.out(f"- 顶层键：`{list(result.keys())}`")
    rep.out(f"- messages 共 {len(msgs)} 条，序列：" + " -> ".join(f"`{type(m).__name__}`" for m in msgs))

    rep.out("\n### 完整返回值（原样一体化导出，一个字段不省略）\n")
    rep.out("`agent.invoke()` 返回值的原样全量内容已直接写入本文件：外层是状态 dict，messages 里是本次执行的"
            "全部消息，每条消息的 id / content / tool_calls / tool_call_id / usage_metadata / response_metadata 等全字段在内。\n")
    rep.fence(to_json(result), "json", file_only=True)

    rep.out("\n### 逐条消息全量导出\n")
    for i, msg in enumerate(msgs, 1):
        rep.out(f"#### [{i}] {type(msg).__name__} ｜ {ROLE_NOTE.get(msg.type, '')}\n")
        dump_message(rep, msg)
        rep.out()

    rep.out("### 最终回答（messages 里最后一条 AI 消息的 content）\n")
    rep.fence(msgs[-1].content, "text")


# ==================== 5. stream：一次执行，同时观察两种粒度 ====================
def run_stream(rep: Report) -> tuple[list[dict], list[tuple]]:
    rep.out("\n## 【2】agent.stream：一次执行，同时观察两种粒度\n")
    rep.out('本次用 `stream_mode=["updates", "messages"]` 一次执行采集两路视图（数据来自同一轮执行，可严格对照）：')
    rep.out("- `updates`（节点级）：每个节点执行完成上报一次，内容是聚合后的完整消息")
    rep.out("- `messages`（消息事件级）：LLM 的 token 分片逐个转发（聚合前的原始增量）；节点产出的完整消息（如工具结果）也会被转发\n")

    updates_list: list[dict] = []     # 节点级：[{节点名: {状态更新}}, ...]
    messages_list: list[tuple] = []   # token 级：[(AIMessageChunk, metadata), ...]
    for mode, payload in agent.stream({"messages": [HumanMessage(QUESTION)]},
                                      stream_mode=["updates", "messages"]):
        if mode == "updates":
            updates_list.append(payload)
        else:
            chunk, meta = payload
            messages_list.append((chunk, meta))

    render_updates_view(rep, updates_list)
    render_messages_view(rep, updates_list, messages_list)
    return updates_list, messages_list


def render_updates_view(rep: Report, updates_list: list[dict]) -> None:
    """【2】节点级视图（updates）：agent 循环每一步的解析 + 完整步骤序列原样导出。"""
    rep.out("\n### 节点级视图（updates）：agent 循环的每一步\n")
    for step_no, step in enumerate(updates_list, 1):
        for node, update in step.items():
            rep.out(f"#### 第 {step_no} 步 ｜ 节点：`{node}`\n")
            for msg in update.get("messages", []):
                if getattr(msg, "tool_calls", None):
                    rep.out(f"产出 `{type(msg).__name__}`（工具调用指令）:\n")
                elif msg.type == "tool":
                    rep.out(f"产出 `{type(msg).__name__}`（{msg.name} 执行结果 = {msg.content}）:\n")
                else:
                    rep.out(f"产出 `{type(msg).__name__}`（最终回答）:\n")
                dump_message(rep, msg)
                rep.out()

    rep.out("\n### 完整步骤序列（原样一体化导出，一个字段不省略）\n")
    rep.out(f"本视图本次共上报 {len(updates_list)} 个步骤对象，完整 JSON 已写入本文件"
            "（每个 step 就是 `{节点名: {'messages': [该节点产出的完整消息]}}`）。\n")
    rep.fence(to_json(updates_list), "json", file_only=True)


def group_events(messages_list: list[tuple]) -> list[list[tuple]]:
    """把消息事件按 (langgraph_step, 节点名) 相邻切分成分组；metadata 缺失时兜底用分片 id 变化。"""
    groups: list[list[tuple]] = []
    cur_key = None
    for chunk, meta in messages_list:
        key = (meta.get("langgraph_step"), meta.get("langgraph_node"))
        if key == (None, None):
            key = chunk.id
        if not groups or cur_key != key:
            groups.append([])
            cur_key = key
        groups[-1].append((chunk, meta))
    return groups


def render_messages_view(rep: Report, updates_list: list[dict], messages_list: list[tuple]) -> None:
    """【3】token 级视图（messages）：分片分组、聚合演示（与 updates 严格对照）、逐事件全量导出。"""
    if not messages_list:
        rep.out("\n## 【3】token 级视图（messages）：本次未采集到任何分片")
        return

    groups = group_events(messages_list)

    # updates 视图里的 AI 消息（决策 + 最终回答），作为严格对照对象
    ai_updates = [m for step in updates_list for upd in step.values()
                  for m in upd.get("messages", []) if m.type == "ai"]

    n_chunks = sum(1 for c, _ in messages_list if isinstance(c, AIMessageChunk))
    n_msgs = len(messages_list) - n_chunks

    rep.out('\n## 【3】messages 视图：token 分片与工具完整消息（与【2】严格对照）\n')
    rep.out('`stream_mode="messages"` 把 agent 执行过程中的消息事件转发出来：LLM 部分是逐 token 的'
            "`AIMessageChunk` 分片，工具结果则是完整 `ToolMessage`；每个事件都是 `(消息对象, metadata)` 二元组。"
            "本节的核心就是验证：分片如何聚合出【2】里的完整消息。\n")

    render_tuple_anatomy(rep, updates_list, messages_list)

    # ---------- 3.1 对照总览 ----------
    rep.out("### 两种粒度的对照总览\n")
    rep.out(f"- messages 视图事件总数：**{len(messages_list)}** 个，来自 {len(groups)} 段节点活动")
    rep.out(f"  - 其中 LLM token 分片（`AIMessageChunk`）：**{n_chunks}** 个；工具完整消息（`ToolMessage`）：**{n_msgs}** 条")
    for gi, g in enumerate(groups, 1):
        meta = g[0][1]
        kind = "token 分片组" if all(isinstance(c, AIMessageChunk) for c, _ in g) else "完整消息组"
        rep.out(f"  - 第 {gi} 组（{kind}）：{len(g)} 个事件 ｜ 来源节点 `{meta.get('langgraph_node')}` ｜ langgraph_step={meta.get('langgraph_step')}")
    rep.out(f"- 同一轮执行里 updates 视图只上报 {len(updates_list)} 个节点级步骤："
            "token 分片是「原料」，节点步骤里的完整消息是「聚合后的成品」。")
    rep.out("- 工具没有 token 流：其结果以完整 `ToolMessage` 的形式出现在 messages 视图，没有分片过程。")
    rep.out("\nmetadata 不单独提取展示（提取会让 `(message, metadata)` 的真实二元组结构失真），"
            "它的原样内容见本章【3.3 逐事件全量导出】里每个事件内部的【第 2 项】。")

    # ---------- 3.2 聚合演示 ----------
    rep.out("\n### 聚合演示：分片用 + 累加，还原成完整消息（与 updates 严格对照）\n")
    rep.out("聚合方式即 merge_chunks_demo.py 里演示过的 `reduce(operator.add, chunks)`："
            "content 首尾相接、tool_calls 由 tool_call_chunks 增量拼出、usage 随末块合并。")
    rep.out("注意：`+` 聚合只对 `AIMessageChunk` 成立（它重载了 `__add__` 做增量合并）；"
            "普通消息的 `+` 是「拼进 ChatPromptTemplate」的语义，所以聚合消息对象必须用分片。\n")
    rep.out("下面是逐组结果与【2】对照（工具消息组无 token 流可聚合，直接展示原消息）：\n")

    ai_idx = 0
    for gi, g in enumerate(groups, 1):
        is_ai_group = all(isinstance(c, AIMessageChunk) for c, _ in g)
        if not is_ai_group:
            rep.out(f"#### 第 {gi} 组 ｜ {len(g)} 条完整消息（工具结果，无 token 流可聚合）\n")
            for c, _ in g:
                rep.out(f"- `{type(c).__name__}`：`{c.name}` 的执行结果，tool_call_id `{c.tool_call_id}`：")
                rep.fence(c.content, "text")
            rep.out()
            continue

        ai_idx += 1
        merged = reduce(operator.add, [c for c, _ in g])
        if len(ai_updates) == 1:
            role = "回答消息"
        elif ai_idx == 1:
            role = "决策消息（对应【2】第 1 步）"
        elif ai_idx == len(ai_updates):
            role = "最终回答（对应【2】最后一步）"
        else:
            role = f"中间决策消息（对应【2】第 {ai_idx} 条 AI 消息）"
        rep.out(f"#### 第 {gi} 组 ｜ {len(g)} 个 token 分片 -> {role}\n")
        if ai_idx <= len(ai_updates):
            umsg = ai_updates[ai_idx - 1]
            rep.out(f"- id 是否一致：**{'是' if merged.id == umsg.id else '否'}**（聚合 `{merged.id}` vs updates `{umsg.id}`）")
            rep.out(f"- content 是否一致：**{'是' if merged.content == umsg.content else '否'}**（聚合 {len(merged.content)} 字 vs updates {len(umsg.content)} 字）")
            rep.out(f"- tool_calls 是否一致：**{'是' if merged.tool_calls == umsg.tool_calls else '否'}**（聚合 {len(merged.tool_calls)} 个 vs updates {len(umsg.tool_calls)} 个）")
            rep.out(f"- usage_metadata 是否一致：**{'是' if merged.usage_metadata == umsg.usage_metadata else '否'}**（聚合 `{merged.usage_metadata}`）")
        for tc in merged.tool_calls:
            rep.out(f"- 聚合出的工具调用：`{tc['name']}`，参数 `{tc['args']}`，id `{tc['id']}`")
        if merged.content:
            rep.out(f"- 聚合出的完整文本（{len(merged.content)} 字）：")
            rep.fence(merged.content, "text")
        rep.out()

    # ---------- 3.3 逐事件全量导出（按流的原始结构原样端出） ----------
    rep.out("### 逐事件全量导出（按流的原始结构，一个字段不省略）\n")
    rep.out(f"按 yield 的原始顺序，把全部 {len(messages_list)} 个事件原样端出。每个事件的真实结构就是一个"
            " `(message, metadata)` 二元组：第 1 项是消息对象（真实类型全路径 + 原始 repr + 全字段 model_dump），"
            "第 2 项是框架附加的 metadata（真实流中每个事件都会携带一份，内容同组相同，但确实逐事件重复出现）。\n")
    rep.out("观察要点：决策组 token 分片的 `tool_call_chunks` 字段——args 是逐片到达的残缺 JSON 片段，拼完才是完整参数。\n")
    export_events_detail(rep, messages_list, groups)

    # ---------- 3.4 差异速查 ----------
    rep.out("\n### 两种视图差异速查\n")
    rep.out("| 维度 | 节点级 updates（【2】） | token 级 messages（【3】） |")
    rep.out("| --- | --- | --- |")
    rep.out("| 上报单位 | 节点执行完成（一次事件 = 一个节点的完整产物） | LLM token 分片 + 节点产出的完整消息（如工具结果） |")
    rep.out("| 消息形态 | 聚合后的完整消息（直接用） | 未聚合的 `AIMessageChunk`（需 `+` 累加）；工具为完整 `ToolMessage` |")
    rep.out("| tool_calls 形态 | 完整解析后的 JSON 参数 | `tool_call_chunks` 增量片段（残缺 JSON） |")
    rep.out("| usage_metadata | 每条 AI 消息都带全 | 仅每组的末分片带 |")
    rep.out("| 工具执行过程 | 可见（ToolMessage） | 可见，但为完整 ToolMessage（无 token 流可聚合） |")
    rep.out("| 典型用途 | 观察循环进度、取最终状态 | 打字机效果、TTFT 观测、理解聚合过程 |")


def render_tuple_anatomy(rep: Report, updates_list: list[dict], messages_list: list[tuple]) -> None:
    """解剖两个元组：用本次运行的真实数据，把 (mode, payload) 和 (message, metadata) 端出完整实例。"""
    rep.out("### 先解剖两个元组：一次 yield 的完整实例\n")
    rep.out('`for mode, payload in agent.stream(..., stream_mode=["updates", "messages"])` —— 每循环一次，'
            '就从流里接到一个二元组 `(mode, payload)`；当 `mode == "messages"` 时，`payload` 本身又是一'
            "个二元组 `(message, metadata)`。层级关系如下：\n")
    rep.out("````text")
    rep.out("一次 yield = (mode, payload)                              ← 外层：二元组")
    rep.out('  ├─ mode = "updates"  → payload：dict {节点名: {"messages": [完整消息, ...]}}')
    rep.out('  └─ mode = "messages" → payload：tuple (message, metadata)          ← 内层：又一个二元组')
    rep.out("                                            ├─ message ：AIMessageChunk（token 分片）/ ToolMessage（完整消息）")
    rep.out("                                            └─ metadata：dict（框架附加的上下文：节点名、步数、模型信息等）")
    rep.out("````")

    mode1 = "messages"
    m1, md1 = messages_list[0]
    rep.out('\n#### 实例一：`mode == "messages"` 的第 1 次 yield（本次运行的真实对象，repr 原样不裁切）\n')
    rep.fence(repr((mode1, (m1, md1))), "text")
    rep.out("\n逐层分解：")
    rep.out(f"- `mode` = `'messages'`（`{type(mode1).__name__}`）——流的名字，决定 payload 的形态")
    rep.out(f"- `payload` = 二元组 `(message, metadata)`（`{type((m1, md1)).__name__}`，长度 {len((m1, md1))}）")
    rep.out(f"  - `message`：`{type(m1).__module__}.{type(m1).__qualname__}` 对象"
            f"（content=`{m1.content}`、id=`{m1.id}`、tool_call_chunks {len(getattr(m1, 'tool_call_chunks', None) or [])} 项）"
            "——第 1 个分片常是「骨架」：content 为空，后续分片才带入增量")
    rep.out(f"  - `metadata`：`{type(md1).__name__}`，键：`{list(md1.keys())}`")
    rep.out("  - 两项的完整字段展开就是【3.3】的「事件 1」块，可直接对照。")

    mode2 = "updates"
    payload2 = updates_list[0]
    node2 = next(iter(payload2))
    upd2 = payload2[node2]
    rep.out('\n#### 实例二：`mode == "updates"` 的第 1 次 yield（本次运行的真实对象，repr 原样不裁切）\n')
    rep.fence(repr((mode2, payload2)), "text")
    rep.out("\n逐层分解：")
    rep.out(f"- `mode` = `'updates'`（`{type(mode2).__name__}`）")
    rep.out(f"- `payload` = dict（`{type(payload2).__name__}`），键 = `{list(payload2.keys())}`（键就是上报的节点名）")
    rep.out(f"  - `payload['{node2}']` = 该节点的状态更新 dict，键 = `{list(upd2.keys())}`")
    rep.out(f"  - `payload['{node2}']['messages']` = 长 {len(upd2.get('messages', []))} 的列表，"
            "里面是节点产出的**完整消息**（聚合后的成品，不是分片）")
    rep.out("  - 完整字段展开见【2】第 1 步的导出。")

    rep.out("\n两层解包的代码形态：\n")
    rep.out("````python")
    rep.out("for mode, payload in agent.stream(...):        # 第 1 层：(mode, payload)")
    rep.out('    if mode == "updates":')
    rep.out("        for node, update in payload.items():    # 节点名 → 状态更新")
    rep.out('            for m in update["messages"]: ...')
    rep.out('    else:  # mode == "messages"')
    rep.out("        message, metadata = payload             # 第 2 层：(message, metadata)")
    rep.out("````")


def export_events_detail(rep: Report, messages_list: list[tuple], groups: list[list[tuple]]) -> None:
    """逐事件全量导出：每个事件按其流的原始结构（(message, metadata) 二元组）原样端出。"""
    event_no = 0
    for gi, g in enumerate(groups, 1):
        meta0 = g[0][1]
        rep.out(f"#### 第 {gi} 组 ｜ 来源节点 `{meta0.get('langgraph_node')}` ｜ langgraph_step={meta0.get('langgraph_step')} ｜ 共 {len(g)} 个事件\n", file_only=True)
        for c, m in g:
            event_no += 1
            rep.out(f"##### 事件 {event_no}/{len(messages_list)}（第 {gi} 组）\n", file_only=True)
            rep.out("**原始结构 = `(message, metadata)` 二元组，两项如下：**\n", file_only=True)
            rep.out("**【第 1 项】message：**\n", file_only=True)
            rep.out(f"- 真实类型：`{type(c).__module__}.{type(c).__qualname__}`", file_only=True)
            rep.out("- 原始 repr（Python 对对象的原样打印）：\n", file_only=True)
            rep.fence(repr(c), "text", file_only=True)
            rep.out("- 完整字段（model_dump，一个不省略）：\n", file_only=True)
            rep.fence(to_json(c.model_dump()), "json", file_only=True)
            rep.out("", file_only=True)
            rep.out("**【第 2 项】metadata（本事件原样携带）：**\n", file_only=True)
            rep.fence(to_json(m), "json", file_only=True)
            rep.out("", file_only=True)


# ==================== 6. 同步 stream vs 异步 astream 对照 ====================
async def collect_astream() -> tuple[list[dict], list[tuple]]:
    """异步采集：与 run_stream 完全相同的 stream_mode 组合，只是把消费方式换成 async for。"""
    updates_list: list[dict] = []
    messages_list: list[tuple] = []
    async for mode, payload in agent.astream({"messages": [HumanMessage(QUESTION)]},
                                             stream_mode=["updates", "messages"]):
        if mode == "updates":
            updates_list.append(payload)
        else:
            chunk, meta = payload
            messages_list.append((chunk, meta))
    return updates_list, messages_list


def shape_rle(messages_list: list[tuple]) -> list[dict]:
    """事件序列 -> 运行长度编码：形状 =（消息类名, 产出节点, 步数, metadata 键集），相邻同形状合并计数。"""
    rle: list[dict] = []
    for c, m in messages_list:
        sig = (type(c).__name__, m.get("langgraph_node"), m.get("langgraph_step"), tuple(sorted(m.keys())))
        if rle and rle[-1]["sig"] == sig:
            rle[-1]["count"] += 1
        else:
            rle.append({"sig": sig, "count": 1})
    return rle


def render_stream_vs_astream(rep: Report, sync_updates: list[dict], sync_msgs: list[tuple],
                             async_updates: list[dict], async_msgs: list[tuple]) -> None:
    """【4】同步 stream 与异步 astream 的输出结构对照（程序化判断）+ 异步侧逐事件全量导出。"""
    sync_rle, async_rle = shape_rle(sync_msgs), shape_rle(async_msgs)
    sync_nodes = [next(iter(s)) for s in sync_updates]
    async_nodes = [next(iter(s)) for s in async_updates]
    sync_n_chunks = sum(1 for c, _ in sync_msgs if isinstance(c, AIMessageChunk))
    async_n_chunks = sum(1 for c, _ in async_msgs if isinstance(c, AIMessageChunk))

    rep.out("\n## 【4】同步 stream vs 异步 astream：输出会变化吗\n")
    rep.out("结论先行：**输出结构完全一致，换成异步不会有任何形状变化**。两个接口消费同一套流式管道：")
    rep.out("- 都 yield `(mode, payload)`；messages 的 payload 都是 `(消息对象, metadata)` 二元组")
    rep.out("- 消息对象类型相同（`AIMessageChunk` / `ToolMessage`）、metadata 键集相同、updates 步骤形状相同")
    rep.out("- 两点区别与「输出」无关：① 消费代码形态（`for` vs `async for`）；② 两次独立调用自身的内容随机性"
            "（分片数、措辞每次本就不同，同步连跑两次也一样）\n")
    rep.out("下面是两侧各跑一次的程序化对照证据（同一问题）。\n")

    # ---------- 4.1 总览 ----------
    rep.out("### 两侧运行总览\n")
    rep.out("| 维度 | 同步 `agent.stream` | 异步 `agent.astream` |")
    rep.out("| --- | --- | --- |")
    rep.out("| 消费代码 | `for mode, payload in agent.stream(...)` | `async for mode, payload in agent.astream(...)` |")
    rep.out(f"| messages 事件总数 | {len(sync_msgs)} | {len(async_msgs)} |")
    rep.out(f"| 其中 token 分片 / 工具消息 | {sync_n_chunks} / {len(sync_msgs) - sync_n_chunks} | {async_n_chunks} / {len(async_msgs) - async_n_chunks} |")
    rep.out(f"| updates 步骤数 | {len(sync_updates)} | {len(async_updates)} |")
    rep.out(f"| updates 节点序列 | `{' -> '.join(sync_nodes)}` | `{' -> '.join(async_nodes)}` |")
    rep.out(f"| 事件形状段数 | {len(sync_rle)} | {len(async_rle)} |")
    rep.out()

    # ---------- 4.2 形状对照 ----------
    rep.out("### 事件形状对照（运行长度编码）\n")
    rep.out("把事件序列折叠成形状序列（形状 = 消息类名 + 产出节点 + 步数，相邻同形状合并计数）：\n")
    rep.out("同步侧：")
    for i, item in enumerate(sync_rle, 1):
        tname, node, step, _keys = item["sig"]
        rep.out(f"{i}. `{tname}` ｜ node=`{node}` ｜ step={step} ｜ × {item['count']}")
    rep.out("\n异步侧：")
    for i, item in enumerate(async_rle, 1):
        tname, node, step, _keys = item["sig"]
        rep.out(f"{i}. `{tname}` ｜ node=`{node}` ｜ step={step} ｜ × {item['count']}")
    same_shape = [x["sig"][:3] for x in sync_rle] == [x["sig"][:3] for x in async_rle]
    rep.out(f"\n形状序列逐项一致：**{'是' if same_shape else '否'}**"
            "（只有每段计数不同——那是两次调用各自的分片随机性，与同步/异步无关）\n")

    # ---------- 4.3 metadata 键集对照 ----------
    rep.out("### metadata 键集对照\n")
    rep.out("metadata 的键集也是结构的一部分，逐段对照（段编号与 4.2 对应）：\n")
    if len(sync_rle) == len(async_rle):
        for i, (s, a) in enumerate(zip(sync_rle, async_rle), 1):
            tname, node, _step, s_keys = s["sig"]
            a_keys = a["sig"][3]
            verdict = "**一致**" if s_keys == a_keys else "**不一致**"
            rep.out(f"- 第 {i} 段（`{tname}` ｜ node=`{node}`）：同步 {list(s_keys)} ｜ 异步 {list(a_keys)} → {verdict}")
    else:
        rep.out("- 两侧形状段数不同，跳过逐段对照")
    rep.out()

    # ---------- 4.4 异步侧聚合校验 ----------
    rep.out("### 异步侧聚合校验（astream 的分片能否同样还原）\n")
    rep.out("对异步侧每组 token 分片做 `reduce(operator.add, ...)` 聚合，与异步 updates 里的完整 AI 消息逐项对照：\n")
    async_ai_updates = [m for step in async_updates for upd in step.values()
                        for m in upd.get("messages", []) if m.type == "ai"]
    ai_idx = 0
    for gi, g in enumerate(group_events(async_msgs), 1):
        if not all(isinstance(c, AIMessageChunk) for c, _ in g):
            continue
        ai_idx += 1
        if ai_idx > len(async_ai_updates):
            continue
        merged = reduce(operator.add, [c for c, _ in g])
        umsg = async_ai_updates[ai_idx - 1]
        rep.out(f"- 第 {gi} 组（{len(g)} 个分片 -> 第 {ai_idx} 条 AI 消息）："
                f"id {'一致' if merged.id == umsg.id else '不一致'} ｜ "
                f"content {'一致' if merged.content == umsg.content else '不一致'}（{len(merged.content)} 字） ｜ "
                f"tool_calls {'一致' if merged.tool_calls == umsg.tool_calls else '不一致'}（{len(merged.tool_calls)} 个） ｜ "
                f"usage_metadata {'一致' if merged.usage_metadata == umsg.usage_metadata else '不一致'}")
    rep.out()

    # ---------- 4.5 异步侧逐事件全量导出 ----------
    rep.out("### 异步侧逐事件全量导出（与【3.3】同格式，一个字段不省略）\n")
    rep.out(f"异步流同样按 `(message, metadata)` 二元组原样端出全部 {len(async_msgs)} 个事件；"
            "格式与【3.3】完全相同，可直接与同步侧对照。\n")
    export_events_detail(rep, async_msgs, group_events(async_msgs))


# ==================== 7. 字段速查 + 入口 ====================
def write_field_help(rep: Report) -> None:
    rep.out("\n## 附：消息字段速查\n")
    rep.out("- `type`：消息类型（human / ai / tool），打印时的 `HumanMessage` 等类名与之对应")
    rep.out("- `content`：消息正文；AI 决策消息的 content 通常为空（它只负责表达“要调工具”）")
    rep.out("- `tool_calls`：AI 消息特有字段，模型请求调用的工具清单，每项含 name / args / id")
    rep.out("- `tool_call_id`：Tool 消息特有字段，与某条 tool_calls[i].id 配对，标明“这条结果是哪个请求的执行结果”")
    rep.out("- `name`：Tool 消息特有字段，实际被执行工具的名字")
    rep.out("- `usage_metadata`：AI 消息特有字段，token 用量（输入 / 输出 / 合计，含 reasoning 明细）；分片模式下只有每组的末分片带")
    rep.out("- `tool_call_chunks`：`AIMessageChunk` 特有字段，流式中 tool_calls 的增量片段（args 为残缺 JSON，拼完才完整）")
    rep.out("- `additional_kwargs` / `response_metadata`：厂商扩展字段与原始响应元数据（全量内容都在 model_dump 里）")


def main() -> None:
    choice = sys.argv[1] if len(sys.argv) > 1 else "all"
    rep = Report()

    # ---------- 报告头 ----------
    tool_names = "、".join(f"`{t.name}`" for t in TOOLS)
    rep.out("# LangChain Agent 输出全量解析")
    rep.out()
    rep.out(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    rep.out(f"- 模型：`{llm.model_name}`")
    rep.out(f"- 问题：{QUESTION}")
    rep.out(f"- 工具清单：{tool_names}")
    rep.out("- Agent 构建：`create_agent(model=llm, tools=[...], system_prompt=...)`（langchain 1.x，底层是 LangGraph 状态图）")
    rep.out("- 调用方式：`agent.invoke(...)` ｜ `agent.stream(...)` ｜ `agent.astream(...)`（后两者均用 `stream_mode=[\"updates\", \"messages\"]` 组合采集两路视图）")
    rep.out()
    rep.out("> Agent 执行机制：`model` 节点调 LLM；回复带 tool_calls 则转到 `tools` 节点执行工具，")
    rep.out("> 结果以 ToolMessage 追加进消息列表后回到 `model` 节点；循环到模型不再调工具，")
    rep.out("> 此时它的 content 即最终回答。下面把各视图的完整数据原样导出（含全部消息的全字段与全部分片）。")

    # ---------- 执行所选模式并收集输出 ----------
    if choice in ("all", "invoke"):
        run_invoke(rep)
    if choice in ("all", "stream"):
        sync_updates, sync_msgs = run_stream(rep)
        async_updates, async_msgs = asyncio.run(collect_astream())
        render_stream_vs_astream(rep, sync_updates, sync_msgs, async_updates, async_msgs)

    write_field_help(rep)
    rep.save(REPORT_PATH)


if __name__ == "__main__":
    # main()
    result = agent.invoke({"messages": [HumanMessage(QUESTION)]})
    print(result)
