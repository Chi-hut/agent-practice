"""
DeepAgent（deepagents 包）最小示例 + 输出全量解析报告

deepagents 是 LangChain 官方出的「深度智能体」库，create_deep_agent 与 create_agent
同为 LangGraph 状态图，但内置了三件套（middleware 形式注入）：
- todo 计划工具 write_todos：复杂任务先拆步骤、逐步更新状态
- 虚拟文件系统：ls / read_file / write_file / edit_file，文件内容存在 state["files"]
  （默认 StateBackend，不落真实磁盘）
- 子代理 SubAgent：可派生隔离上下文的子任务 agent（本示例未配置，只看默认形态）

本文件的任务刻意覆盖两条内置能力：先写 todo 计划 -> calculate 计算 -> write_file
落盘 -> 总结，这样输出里能看到 todos / files 两个 create_agent 没有的 state 字段。

把所有输出视图的完整数据原样导出为 markdown 报告：
- 【1】invoke 的完整返回值（最终状态 dict：messages + todos + files）
- 【2】stream_mode="updates"：agent 循环每一步的增量（含工具调用与 todos/files 更新）
- 【3】stream_mode="messages"：token 级分片，逐事件全量导出（与【2】同一轮执行）
- 【4】与 create_agent（simple_agent.py）的输出差异速查

无需盯控制台，直接打开项目根目录的 deep_agent_demo_output.md 查看即可。

运行方式（在项目根目录下执行）：
    python -m agent.deep_agent_demo
生成文件：项目根目录 deep_agent_demo_output.md
"""

import importlib.metadata as md
import inspect
import json
from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.tools import tool
from deepagents import create_deep_agent

# 兼容两种运行方式（与 simple_agent.py 同样的处理）
try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = ("先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，"
            "把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。")
ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "deep_agent_demo_output.md"

# 每种消息在 deep agent 输出里扮演的角色（报告里作为注解）
ROLE_NOTE = {
    "human": "用户输入",
    "ai": "模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答",
    "tool": "工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）",
}


# ==================== 1. 自定义工具（deep agent 自带工具之外我们只加这一个） ====================
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


# ==================== 2. 创建 deep agent ====================
# 与 create_agent 的主要区别：不传任何「深度能力」配置，deep agent 也会自动注入
# write_todos + 文件系统工具和相应的长系统提示（本次实测见报告里的工具调用记录）
agent = create_deep_agent(
    model=llm,
    tools=[calculate],
    system_prompt="你是一名严谨的助手。涉及计算必须调用 calculate 工具，不要自己心算。",
)


# ==================== 3. 双通道输出：控制台 + markdown 报告 ====================
class Report:
    """写入的每一行缓冲进内存、运行结束统一落盘为 markdown 文件；
    默认同时打印到控制台，file_only=True 的行只进文件（适合动辄上千行的大块 JSON）。"""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def out(self, text: str = "", file_only: bool = False) -> None:
        if not isinstance(text, str):
            # 兜底防线：意外对象转 JSON 落盘，保证报告一定能生成（不掩盖：类型信息仍可见）
            text = to_json(text)
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


def dump_todos(rep: Report, todos, indent: str = "") -> None:
    """导出 todos 列表（deep agent 特有字段：内置 write_todos 工具写入的执行计划）。"""
    if not todos:
        rep.out(f"{indent}- todos：空（本次未使用计划工具）")
        return
    rep.out(f"{indent}- todos 共 {len(todos)} 项：")
    for t in todos:
        if isinstance(t, dict):
            rep.out(f"{indent}  - [{t.get('status')}] {t.get('content')}")
        else:
            rep.out(f"{indent}  - {to_json(t)}")


def dump_files(rep: Report, files, indent: str = "") -> None:
    """导出 files（deep agent 特有字段：虚拟文件系统）。实测值可能是 str 或 dict，均按原样导出。"""
    if not files:
        rep.out(f"{indent}- files：空（本次未写文件）")
        return
    rep.out(f"{indent}- files 共 {len(files)} 个文件（存在 state 里，不落真实磁盘）：")
    for fname, content in files.items():
        if isinstance(content, str):
            rep.out(f"{indent}  - `{fname}`（str，{len(content)} 字符）：")
            rep.fence(content, "text")
        else:
            rep.out(f"{indent}  - `{fname}`（类型 `{type(content).__module__}.{type(content).__qualname__}`）：")
            rep.fence(to_json(content), "json")


def msg_brief(msg) -> str:
    """一步 update 里单条消息的一句话概要（updates 视图的人读线索）。"""
    if getattr(msg, "tool_calls", None):
        return "工具调用指令：" + "、".join(f"`{tc['name']}`" for tc in msg.tool_calls)
    if msg.type == "tool":
        return f"工具结果：`{msg.name}`"
    if msg.type == "human":
        return "用户输入"
    return "最终回答（无工具调用）"


def dump_update_value(rep: Report, key: str, val) -> None:
    """导出 update 里单个键的增量值，形态自适应。

    实测坑：中间件钩子节点（如 PatchToolCallsMiddleware.before_agent）返回的 messages
    不是 list 而是 Overwrite 包装对象（语义是「该键整体覆盖而非追加」，真实内容在 .value），
    直接迭代会 TypeError——updates 流里能看到这种 reducer 指令包装，是 deep agent 的中间件痕迹。
    """
    real, wrapper_note = val, ""
    if not isinstance(val, (list, tuple, dict, str)):
        inner = getattr(val, "value", None)
        if inner is not None:
            real = inner
            wrapper_note = (f"（被 `{type(val).__module__}.{type(val).__qualname__}` 包装："
                            "语义是「该键整体覆盖而非追加」，真实内容在其 value 中）")
    if key == "messages" and isinstance(real, list):
        rep.out(f"- 键 `messages`{wrapper_note}，共 {len(real)} 条：")
        for msg in real:
            rep.out(f"  - 产出 `{type(msg).__name__}`（{msg_brief(msg)}）：")
            dump_message(rep, msg)
    elif key == "todos":
        rep.out(f"- 键 `todos`{wrapper_note}：")
        dump_todos(rep, real, indent="  ")
    elif key == "files":
        rep.out(f"- 键 `files`{wrapper_note}：")
        dump_files(rep, real, indent="  ")
    else:
        rep.out(f"- 键 `{key}`{wrapper_note}：")
        rep.fence(to_json(real), "json", file_only=True)


# ==================== 4.【0】deep agent 的定义 ====================
def write_intro(rep: Report) -> None:
    rep.out("\n## 【0】deep agent 的定义：与 create_agent 差在哪\n")
    rep.out("create_deep_agent 底层同样是 LangGraph 状态图，但通过中间件自动注入了"
            "**todo 计划、虚拟文件系统、子代理**三套能力。本次只给它一个 calculate 工具，"
            "内置工具会以 tool_calls 形式现身（见【2】的每一步记录）。HTTP 层实测注入的完整工具清单"
            "共 8 个：write_todos、ls、read_file、write_file、edit_file、glob、grep、task（见 "
            "deep_agent_dump_output.md 的请求体 tools 字段）。\n")

    rep.out("### 创建代码\n")
    # @tool 装饰后 calculate 不再是普通函数而是 StructuredTool 对象，原始函数在 .func 里
    try:
        rep.fence(inspect.getsource(calculate.func), "python")
    except Exception as exc:
        rep.out(f"- 工具源码获取失败：{exc}")
    rep.fence(
        "agent = create_deep_agent(\n"
        "    model=llm,\n"
        "    tools=[calculate],\n"
        '    system_prompt="你是一名严谨的助手。涉及计算必须调用 calculate 工具，不要自己心算。",\n'
        ")",
        "python",
    )
    rep.out("- deepagents 版本：`" + md.version("deepagents") + "`")
    rep.out("- 签名要点：`create_deep_agent(model, tools, system_prompt, middleware, subagents, "
            "backend, ...)`，不传 backend 时默认 StateBackend（文件存 state）\n")

    g = agent.get_graph()
    rep.out("### 图结构（`agent.get_graph()` 的原始数据）\n")
    nodes_list = [{"id": n.id, "name": n.name, "type": getattr(n, "type", None), "metadata": getattr(n, "metadata", None)}
                  for n in g.nodes.values()]
    edges_list = [{"source": e.source, "target": e.target, "conditional": e.conditional, "data": e.data}
                  for e in g.edges]
    rep.out("- 节点（全量）：\n")
    rep.fence(to_json(nodes_list), "json", file_only=True)
    rep.out("- 边（全量）：\n")
    rep.fence(to_json(edges_list), "json", file_only=True)
    rep.out("- mermaid 图源码：\n")
    try:
        rep.fence(g.draw_mermaid(), "mermaid")
    except Exception as exc:
        rep.out(f"  - mermaid 生成失败：{exc}")


# ==================== 5.【1】invoke：一次性拿到最终状态 ====================
def run_invoke(rep: Report) -> None:
    print("\n>> 【1】invoke ...")
    rep.out("\n## 【1】agent.invoke：阻塞到全部结束，一次拿到最终状态\n")
    result = agent.invoke({"messages": [HumanMessage(QUESTION)]})
    msgs = result["messages"]

    rep.out("### 顶层结构（deep agent 与 create_agent 的第一个差异在这里）\n")
    rep.out(f"- 返回类型：`{type(result).__name__}`（最终状态 dict）")
    rep.out(f"- 顶层键：`{list(result.keys())}`（create_agent 通常只有 messages；"
            "deep agent 多出 todos 与 files 两个内置字段）")
    rep.out(f"- messages 共 {len(msgs)} 条，序列：" + " -> ".join(f"`{type(m).__name__}`" for m in msgs))
    rep.out()

    rep.out("### 内置字段一：todos（执行计划）\n")
    dump_todos(rep, result.get("todos"))
    rep.out("\n### 内置字段二：files（虚拟文件系统）\n")
    dump_files(rep, result.get("files"))

    rep.out("\n### 完整返回值（原样一体化导出，一个字段不省略）\n")
    rep.fence(to_json(result), "json", file_only=True)

    rep.out("\n### 逐条消息全量导出\n")
    for i, msg in enumerate(msgs, 1):
        rep.out(f"#### [{i}] {type(msg).__name__} ｜ {ROLE_NOTE.get(msg.type, '')}\n")
        dump_message(rep, msg)
        rep.out()

    rep.out("### 最终回答（最后一条 AI 消息的 content）\n")
    rep.fence(msgs[-1].content, "text")


# ==================== 6.【2】+【3】stream 组合采集：updates 与 messages 同轮对照 ====================
def run_stream_combined(rep: Report) -> tuple[list[dict], list[tuple]]:
    print("\n>> 【2】【3】stream（updates + messages 组合）...")
    rep.out('\n## 【2】stream_mode="updates"：agent 循环每一步的增量\n')
    rep.out("deep agent 的循环形态与 create_agent 一致：`model` 节点（LLM 决策）与 `tools` 节点"
            "（执行工具）交替，直到模型不再调工具。区别在于 model 可以调**内置工具**："
            "write_todos 更新计划、write_file 写虚拟文件——它们都会以增量形式出现在 update 里。\n")

    updates_list: list[dict] = []     # 节点级：[{节点名: {状态增量}}, ...]
    messages_list: list[tuple] = []   # token 级：[(消息对象, metadata), ...]
    for mode, payload in agent.stream({"messages": [HumanMessage(QUESTION)]},
                                      stream_mode=["updates", "messages"]):
        if mode == "updates":
            updates_list.append(payload)
        else:
            chunk, meta = payload
            messages_list.append((chunk, meta))

    for step_no, step in enumerate(updates_list, 1):
        for node, update in step.items():
            rep.out(f"### 第 {step_no} 步 ｜ 节点：`{node}`\n")
            if update is None:
                # 实测：中间件钩子本步无状态更新时，updates 流仍上报 {节点名: None}
                rep.out("- 增量为 `None`（中间件钩子本步无状态更新，但流里仍以 {节点名: None} 上报一步）\n")
                continue
            rep.out(f"- 增量键：`{list(update.keys())}`（只含该节点 return 的字段；"
                    "节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）")
            for key, val in update.items():
                dump_update_value(rep, key, val)
            rep.out()

    rep.out("### 完整步骤序列（原样一体化导出，一个字段不省略）\n")
    rep.out(f"本视图本次共上报 {len(updates_list)} 个步骤对象，完整 JSON 已写入本文件。\n")
    rep.fence(to_json(updates_list), "json", file_only=True)

    # ---------- messages 视图 ----------
    rep.out('\n## 【3】stream_mode="messages"：token 级分片（与【2】同一轮执行）\n')
    n_chunks = sum(1 for c, _ in messages_list if isinstance(c, AIMessageChunk))
    kinds: dict[str, int] = {}
    for c, _ in messages_list:
        kinds[type(c).__name__] = kinds.get(type(c).__name__, 0) + 1
    nodes_seen = sorted({str(m.get("langgraph_node")) for _, m in messages_list})

    rep.out("### 总览\n")
    rep.out(f"- 事件总数：**{len(messages_list)}**，类型分布：`{kinds}`")
    rep.out(f"- 事件来源节点：`{nodes_seen}`")
    rep.out("- 解读：结构与 create_agent 完全同构——LLM 决策是逐 token 的 `AIMessageChunk` 分片，"
            "工具结果是完整 `ToolMessage`；每个事件都是 `(消息对象, metadata)` 二元组。\n")

    if messages_list:
        m1, md1 = messages_list[0]
        rep.out("### 先解剖一次 yield：`(message, metadata)` 的完整实例\n")
        rep.fence(repr(("messages", (m1, md1))), "text")
        rep.out(f"\n第 1 项 message 是 `{type(m1).__module__}.{type(m1).__qualname__}`，"
                f"第 2 项 metadata 是 `{type(md1).__name__}`，键：`{list(md1.keys())}`。\n")

    rep.out("### 逐事件全量导出（按流的原始结构，一个字段不省略）\n")
    rep.out(f"按 yield 的原始顺序，把全部 {len(messages_list)} 个事件原样端出。"
            "每个事件的第 1 项是消息对象（真实类型全路径 + 原始 repr + 全字段 model_dump），"
            "第 2 项是 metadata（真实流中每个事件都重复携带一份，不提取到组外）。\n")
    for idx, (c, m) in enumerate(messages_list, 1):
        rep.out(f"#### 事件 {idx}/{len(messages_list)}\n", file_only=True)
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

    return updates_list, messages_list


# ==================== 7.【4】差异速查 + 字段速查 ====================
def write_cheatsheet(rep: Report) -> None:
    rep.out("\n## 【4】与 create_agent（simple_agent.py）输出差异速查\n")
    rep.out("| 维度 | create_agent（simple_agent.py） | create_deep_agent（本次） |")
    rep.out("| --- | --- | --- |")
    rep.out("| 顶层 state 键 | `messages` | `messages` + **`todos`** + **`files`** |")
    rep.out("| 可用工具 | 只有你传的 tools | 你的 tools + 内置 8 个：write_todos / ls / read_file / write_file / edit_file / glob / grep / task |")
    rep.out("| 系统提示 | 只用你传的 system_prompt | 内置长提示（规划与文件使用指引）再拼接你的 system_prompt |")
    rep.out("| 循环形态 | model <-> tools | 相同（model <-> tools） |")
    rep.out("| 消息 / 分片结构 | `AIMessageChunk` / `ToolMessage` | 完全一致（同构 LangGraph） |")
    rep.out("| 文件去哪了 | 概念不存在 | `state[\"files\"]`（StateBackend，虚拟文件系统，不落盘） |")
    rep.out("\n- 本次任务触发的内置工具以【2】的实测 tool_calls 为准（write_todos / write_file 等）。")
    rep.out("- `todos`：list[dict]，每项含 `content`（做什么）与 `status`（pending / in_progress / completed）。")
    rep.out("- `files`：dict[文件名, 文件内容字符串]，写入即可在后续轮次 read_file 读回，跨轮持久在 state 中。")
    rep.out("- invoke 返回的仍不是消息而是最终状态：拿回答用 `result[\"messages\"][-1]` 的最后一条 AI 消息。")


def main() -> None:
    rep = Report()

    # ---------- 报告头 ----------
    rep.out("# DeepAgent（deepagents）输出全量解析")
    rep.out()
    rep.out(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    rep.out(f"- 模型：`{llm.model_name}`")
    rep.out(f"- deepagents 版本：`{md.version('deepagents')}`")
    rep.out(f"- 问题：{QUESTION}")
    rep.out("- Agent 构建：`create_deep_agent(model=llm, tools=[calculate], system_prompt=...)`")
    rep.out("- 采集方式：invoke、stream(updates+messages) 共两次**独立**执行")
    rep.out()
    rep.out("> 说明：两次独立执行的回复文本、分片数量天然不同（模型随机性），但输出**结构**一致；")
    rep.out("> 严格对照只看同一轮执行的数据（【2】与【3】同轮采集）。")

    write_intro(rep)
    run_invoke(rep)
    run_stream_combined(rep)
    write_cheatsheet(rep)

    rep.save(REPORT_PATH)


if __name__ == "__main__":
    main()
