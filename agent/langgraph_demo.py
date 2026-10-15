"""
手写 LangGraph 最小图 Demo：START -> prepare -> call_llm -> END，输出全量解析报告

与 simple_agent.py（create_agent 封装好的图）不同，本文件用 StateGraph 手工搭建
最小图，看得见图的每个部件：状态 schema、节点函数、边。目的：看「LangGraph 框架
下的原始输出」长什么样——invoke 拿到什么、stream 四种视图各吐什么形状的数据。

图的结构（线性三段，llm 节点在中间）：
    START -> prepare（普通节点：加工状态） -> call_llm（LLM 节点：调模型） -> END

把所有输出视图的完整数据原样导出为 markdown 报告：
- 【0】图的定义：状态 schema、节点源码、图结构原始数据（含 __start__/__end__）
- 【1】invoke 的完整返回值（最终状态 dict）
- 【2】stream 默认模式（values）：每步一次完整状态快照
- 【3】stream_mode="updates"：框架把输入当 __start__ 上报，之后每节点一次增量
- 【4】stream_mode="messages"：token 级分片，逐事件全量导出（与【3】同一轮执行）
- 【5】聚合校验：messages 分片用 + 拼回完整消息，与 updates 严格对照

无需盯控制台，直接打开项目根目录的 langgraph_demo_output.md 查看即可。

运行方式（在项目根目录下执行）：
    python -m agent.langgraph_demo
生成文件：项目根目录 langgraph_demo_output.md
"""

import inspect
import json
import operator
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph, add_messages

# 兼容两种运行方式（与 simple_agent.py 同样的处理）
try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系"
ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "langgraph_demo_output.md"

# 每种消息在图执行中扮演的角色（报告里作为注解）
ROLE_NOTE = {
    "human": "用户输入（invoke 初始状态里带进来的）",
    "system": "prepare 节点追加的系统提示（验证 add_messages 的「追加」语义）",
    "ai": "call_llm 节点调 LLM 得到的回复",
}


# ==================== 1. 图的三要素：状态、节点、边 ====================
class State(TypedDict):
    """图的状态 schema：所有节点共享同一份状态，节点返回值是「增量」而非全量。

    - messages：用 add_messages reducer，节点返回的消息按 id 追加进列表
      （新消息没有 id 就直接 append 到尾部，所以 SystemMessage 不会插队到最前面）
    - question：普通字段，没有 reducer，后写的值直接覆盖旧值
    """

    messages: Annotated[list, add_messages]
    question: str


def prepare(state: State) -> dict:
    """普通节点：不调模型，只加工状态。返回的 dict 就是「状态增量」。

    两种字段更新语义都在这一步发生：
    - messages（add_messages）：SystemMessage 追加到消息列表尾部
    - question（无 reducer）：输入的 None 被新值覆盖
    """
    print("  [节点] prepare：加工状态（不调模型）")
    question = state["messages"][-1].content
    return {
        "question": question,
        "messages": [SystemMessage(content=f"请围绕用户问题用中文简短回答：{question}")],
    }


def call_llm(state: State) -> dict:
    """LLM 节点：把当前消息列表原样交给模型，回复追加进 messages。"""
    print("  [节点] call_llm：调用 LLM ...")
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def build_graph():
    """搭图 + 编译。节点用字符串注册，边用字符串连线，compile 后才是可执行对象。"""
    builder = StateGraph(State)
    builder.add_node("prepare", prepare)      # 注册普通节点
    builder.add_node("call_llm", call_llm)    # 注册 LLM 节点
    builder.add_edge(START, "prepare")        # 入口 -> prepare
    builder.add_edge("prepare", "call_llm")   # 顺序执行
    builder.add_edge("call_llm", END)         # LLM 回复完即到终点
    return builder.compile()                  # 编译成 Runnable，之后就能 invoke / stream


app = build_graph()


# ==================== 2. 双通道输出：控制台 + markdown 报告 ====================
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
    if getattr(msg, "usage_metadata", None):
        rep.out(f"- token 用量：`{msg.usage_metadata}`")
    rep.out("\n可读全文（pretty_repr）：\n")
    rep.fence(msg.pretty_repr(), "text")
    rep.out("\n完整字段（model_dump，一个字段不省略）：\n")
    rep.fence(to_json(msg.model_dump()), "json")


def dump_state(rep: Report, snap: dict, title: str) -> None:
    """导出一份完整状态快照：顶层键、消息序列、自定义字段、全量 JSON。"""
    rep.out(f"#### {title}\n")
    rep.out(f"- 顶层键：`{list(snap.keys())}`")
    msgs = snap.get("messages", [])
    rep.out(f"- messages 共 {len(msgs)} 条，序列：" + " -> ".join(f"`{type(m).__name__}`" for m in msgs))
    if "question" in snap:
        rep.out(f"- question：`{snap['question']!r}`")
    else:
        rep.out("- question：（此键还不存在）")
    rep.out("\n完整快照（全量 JSON，一个字段不省略）：\n")
    rep.fence(to_json(snap), "json", file_only=True)
    rep.out()


# ==================== 3.【0】图的定义 ====================
def write_graph_def(rep: Report) -> None:
    rep.out("\n## 【0】图的定义：状态 schema、节点、边\n")
    rep.out("LangGraph 的三要素：**State**（所有节点共享的状态）、**Node**（读写状态的函数）、"
            "**Edge**（节点间的走向）。节点返回 dict 表示增量，同名字段怎么合并由 reducer 决定。\n")

    rep.out("### 状态 schema（State，实测 `State.__annotations__`）\n")
    for name, ann in State.__annotations__.items():
        note = "  <- add_messages reducer：按 id 追加" if name == "messages" else "  <- 无 reducer：后写覆盖"
        rep.out(f"- `{name}`：`{ann!r}`{note}")

    rep.out("\n### 节点函数（inspect.getsource 原样取自本文件）\n")
    for fn in (prepare, call_llm):
        rep.out(f"`{fn.__name__}`：")
        rep.fence(inspect.getsource(fn), "python")

    rep.out("### 搭图与编译（inspect.getsource）\n")
    rep.fence(inspect.getsource(build_graph), "python")

    g = app.get_graph()
    rep.out("### 图结构（`app.get_graph()` 的原始数据）\n")
    rep.out("注意：编译后的图里不止你注册的两个节点——框架自动补了 `__start__` 和 `__end__` "
            "两个虚拟节点，真实节点序列为 5 个。\n")
    nodes_list = [{"id": n.id, "name": n.name, "type": getattr(n, "type", None), "metadata": getattr(n, "metadata", None)}
                  for n in g.nodes.values()]
    edges_list = [{"source": e.source, "target": e.target, "conditional": e.conditional, "data": e.data}
                  for e in g.edges]
    rep.out("- 节点（全量）：\n")
    rep.fence(to_json(nodes_list), "json", file_only=True)
    rep.out("- 边（全量）：\n")
    rep.fence(to_json(edges_list), "json", file_only=True)

    rep.out("- mermaid 图源码（可粘贴到支持 mermaid 的查看器渲染）：\n")
    try:
        rep.fence(g.draw_mermaid(), "mermaid")
    except Exception as exc:
        rep.out(f"  - mermaid 生成失败：{exc}")
    rep.out("- ASCII 图（需要 grandalf 依赖，没装不影响其它章节）：\n")
    try:
        rep.fence(g.draw_ascii(), "text")
    except Exception as exc:
        rep.out(f"  - 生成失败：{exc}")


# ==================== 4.【1】invoke：一次性拿到最终状态 ====================
def run_invoke(rep: Report) -> None:
    print("\n>> 【1】invoke ...")
    rep.out("\n## 【1】graph.invoke：阻塞到全部结束，一次拿到最终状态\n")
    result = app.invoke({"messages": [HumanMessage(QUESTION)]})
    msgs = result["messages"]

    rep.out("### 顶层结构\n")
    rep.out(f"- 返回类型：`{type(result).__name__}`（LangGraph 返回的是**最终状态 dict**，不是消息对象；"
            "对比 llm.invoke 返回单条 AIMessage）")
    rep.out(f"- 顶层键：`{list(result.keys())}`（messages 按序累积了全程消息；question 被 prepare 写入）")
    rep.out(f"- messages 共 {len(msgs)} 条，序列：" + " -> ".join(f"`{type(m).__name__}`" for m in msgs))
    rep.out("\n### 完整返回值（原样一体化导出，一个字段不省略）\n")
    rep.fence(to_json(result), "json", file_only=True)

    rep.out("\n### 逐条消息全量导出\n")
    for i, msg in enumerate(msgs, 1):
        rep.out(f"#### [{i}] {type(msg).__name__} ｜ {ROLE_NOTE.get(msg.type, '')}\n")
        dump_message(rep, msg)
        rep.out()

    rep.out("### 最终回答（最后一条 AI 消息的 content）\n")
    rep.fence(msgs[-1].content, "text")


# ==================== 5.【2】stream 默认模式（values）：状态快照流 ====================
def run_stream_values(rep: Report) -> None:
    print("\n>> 【2】stream（values）...")
    rep.out("\n## 【2】stream 默认模式（values）：每步吐一次完整状态快照\n")
    rep.out('`app.stream(input)` 不传 stream_mode 时默认 `stream_mode="values"`：'
            "每执行完一个「超级步」就把**全量状态**复制一份吐出来。"
            "观察点是消息列表逐步变长、question 键从无到有。\n")

    snaps = list(app.stream({"messages": [HumanMessage(QUESTION)]}, stream_mode="values"))
    rep.out(f"本次共 yield **{len(snaps)}** 个快照（1 个输入态 + 每个节点执行后各 1 个），逐一全量导出：\n")
    for i, snap in enumerate(snaps, 1):
        dump_state(rep, snap, f"快照 {i}/{len(snaps)}")

    rep.out("观察点：每个快照都是**全量复制**（后面的快照包含前面快照的全部消息，重复是真实形态，不是导出 bug）；"
            "所以图大、消息多时 values 流很冗长，只想看「谁贡献了什么」应该用 updates 视图（下一章）。")


# ==================== 6.【3】+【4】stream 组合采集：updates 与 messages 同轮对照 ====================
def run_stream_combined(rep: Report) -> tuple[list[dict], list[tuple]]:
    print("\n>> 【3】【4】stream（updates + messages 组合）...")
    rep.out("\n## 【3】stream_mode=\"updates\"：每个节点执行完，上报一次增量\n")
    rep.out("updates 视图每步 yield `{节点名: {增量字段}}`，上报的只是**注册节点**：图结构里虽自动补了 "
            "`__start__`/`__end__` 虚拟节点（见【0】），但本版本实测 updates 流不把输入单独上报——"
            "输入经 add_messages 直接并入初始状态，不出现在任何步骤里。\n")

    updates_list: list[dict] = []     # 节点级：[{节点名: {状态增量}}, ...]
    messages_list: list[tuple] = []   # token 级：[(消息对象, metadata), ...]
    for mode, payload in app.stream({"messages": [HumanMessage(QUESTION)]},
                                    stream_mode=["updates", "messages"]):
        if mode == "updates":
            updates_list.append(payload)
        else:
            chunk, meta = payload
            messages_list.append((chunk, meta))

    # ---------- updates 视图 ----------
    for step_no, step in enumerate(updates_list, 1):
        for node, update in step.items():
            rep.out(f"### 第 {step_no} 步 ｜ 上报节点：`{node}`"
                    + ("（框架虚拟节点：输入从这里进来）" if node == "__start__" else "") + "\n")
            rep.out(f"- 增量键：`{list(update.keys())}`（只含该节点 return 的字段，不是全量状态）")
            for msg in update.get("messages", []):
                rep.out(f"- 产出 `{type(msg).__name__}`：{ROLE_NOTE.get(msg.type, '')}")
                dump_message(rep, msg)
            if "question" in update:
                rep.out(f"- question 增量值：`{update['question']}`")
            rep.out()

    rep.out("### 完整步骤序列（原样一体化导出，一个字段不省略）\n")
    rep.out(f"本视图本次共上报 {len(updates_list)} 个步骤对象，完整 JSON 已写入本文件。\n")
    rep.fence(to_json(updates_list), "json", file_only=True)

    # ---------- messages 视图 ----------
    rep.out("\n## 【4】stream_mode=\"messages\"：token 级分片（与【3】同一轮执行）\n")
    rep.out("messages 视图转发的是 LLM 的流式事件：每个 yield 是 `(消息对象, metadata)` 二元组。"
            "本章先给类型分布与来源节点统计，再按 yield 原始顺序逐事件全量导出。\n")

    n_chunks = sum(1 for c, _ in messages_list if isinstance(c, AIMessageChunk))
    kinds: dict[str, int] = {}
    for c, _ in messages_list:
        kinds[type(c).__name__] = kinds.get(type(c).__name__, 0) + 1
    nodes_seen = sorted({str(m.get("langgraph_node")) for _, m in messages_list})
    n_human = sum(1 for c, _ in messages_list if isinstance(c, HumanMessage))
    n_system = sum(1 for c, _ in messages_list if isinstance(c, SystemMessage))

    rep.out("### 总览\n")
    rep.out(f"- 事件总数：**{len(messages_list)}**，类型分布：`{kinds}`")
    rep.out(f"- 事件来源节点：`{nodes_seen}`")
    rep.out(f"- 其中 HumanMessage（invoke 的输入）{n_human} 条；SystemMessage（prepare 节点 return 的）{n_system} 条")
    rep.out("- 解读：messages 流 = LLM 的 token 分片（逐片转发）+ **节点 return 的消息（完整形态转发，无分片过程）**；"
            "invoke 的输入消息不属于任何节点的产出，不进此流（看它请用 values / updates 视图）")
    rep.out(f"- 对照：同一轮执行里 updates 只上报 {len(updates_list)} 步，"
            f"messages 却有 {len(messages_list)} 个事件——分片是「原料」，节点增量是「成品」。\n")

    # 第一次 yield 的原样解剖（真实对象 repr 不裁切）
    if messages_list:
        m1, md1 = messages_list[0]
        rep.out("### 先解剖一次 yield：`(message, metadata)` 的完整实例\n")
        rep.fence(repr(("messages", (m1, md1))), "text")
        kind1 = ("节点 return 的完整消息（非分片，完整形态直接转发）" if not isinstance(m1, AIMessageChunk)
                 else "LLM 的 token 分片（本组第 1 片常是空骨架：content 为空）")
        rep.out(f"\n逐层分解：`mode` = `'messages'`；`payload` 是二元组；第 1 项 message 是 "
                f"`{type(m1).__module__}.{type(m1).__qualname__}`（{kind1}），"
                f"第 2 项 metadata 是 `{type(md1).__name__}`，键：`{list(md1.keys())}`。\n")

    export_events_detail(rep, messages_list)
    return updates_list, messages_list


def export_events_detail(rep: Report, messages_list: list[tuple]) -> None:
    """逐事件全量导出：每个事件按其流的原始结构（(message, metadata) 二元组）原样端出。"""
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


# ==================== 7.【5】聚合校验：分片拼回 vs updates 对照 ====================
def render_merge_check(rep: Report, updates_list: list[dict], messages_list: list[tuple]) -> None:
    print("\n>> 【5】聚合校验 ...")
    rep.out("\n## 【5】聚合校验：messages 分片用 + 拼回，与 updates 里的完整消息对照\n")
    rep.out("聚合方式即 merge_chunks_demo.py 演示过的 `reduce(operator.add, chunks)`："
            "content 首尾相接、usage 随末块合并。注意 `+` 只对 `AIMessageChunk` 成立"
            "（普通消息的 `+` 是「拼进 ChatPromptTemplate」的语义）。\n")

    chunks = [c for c, _ in messages_list if isinstance(c, AIMessageChunk)]
    ai_updates = [m for step in updates_list for upd in step.values()
                  for m in upd.get("messages", []) if getattr(m, "type", "") == "ai"]
    if not chunks or not ai_updates:
        rep.out("- 本次未采集到足够的分片或完整消息，跳过对照")
        return

    merged = reduce(operator.add, chunks)
    umsg = ai_updates[-1]
    rep.out(f"- call_llm 节点共 yield {len(chunks)} 个 token 分片，`reduce(operator.add, ...)` 拼回 1 个 "
            f"`{type(merged).__name__}`")
    rep.out(f"- 与 updates 视图里 call_llm 上报的完整 AIMessage 逐项对照：")
    rep.out(f"  - id 一致：**{'是' if merged.id == umsg.id else '否'}**（`{merged.id}`）")
    rep.out(f"  - content 一致：**{'是' if merged.content == umsg.content else '否'}**（{len(merged.content)} 字）")
    rep.out(f"  - usage_metadata 一致：**{'是' if merged.usage_metadata == umsg.usage_metadata else '否'}**")
    rep.out(f"  - response_metadata.model_name 一致：**{'是' if merged.response_metadata.get('model_name') == umsg.response_metadata.get('model_name') else '否'}**")
    rep.out("\n结论：messages 视图的分片就是 updates 视图完整消息的「原料」，两种视图来自同一轮执行，可互相还原。")


# ==================== 8. 速查表 + 入口 ====================
def write_cheatsheet(rep: Report) -> None:
    rep.out("\n## 附一：四种视图差异速查\n")
    rep.out("| 调用形态 | yield / 返回的东西 | 粒度 | 典型用途 |")
    rep.out("| --- | --- | --- | --- |")
    rep.out("| `app.invoke(input)` | 一次性返回**最终状态 dict** | 无流 | 只要最终结果 |")
    rep.out('| `app.stream(input)`（values 默认） | 每步一个**完整状态快照** | 超级步 | 观察状态演变、调试 |')
    rep.out('| `stream_mode="updates"` | 每步 `{节点名: 增量dict}` | 节点 | 看每个节点贡献了什么 |')
    rep.out('| `stream_mode="messages"` | 每事件 `(消息对象, metadata)` | token | 打字机效果、TTFT 观测 |')
    rep.out("\n- 同一次 stream 可传列表组合采集：`stream_mode=[\"updates\", \"messages\"]`，"
            "此时每个 yield 变成 `(mode, payload)` 二元组（本报告【3】【4】即同轮数据）。")
    rep.out("- invoke 返回的**不是消息**而是最终状态：拿回答要用 `result[\"messages\"][-1]`。")
    rep.out("- `__start__` / `__end__` 只存在于编译后的图结构（get_graph）里；本版本实测 updates 流只上报注册节点，"
            "invoke 的输入不单独上报")
    rep.out("- 与 simple_agent.py（create_agent）的关系：create_agent 底层就是 LangGraph，"
            "本报告的输出结构与那边完全同构，只是图形状更简单（无工具循环）。")

    rep.out("\n## 附二：LangGraph 概念速查（本文件对应代码）\n")
    rep.out("- `StateGraph(State)`：以 State 为 schema 建图（builder）")
    rep.out("- `add_node(\"名字\", 函数)`：注册节点；函数签名 `(state) -> dict`，返回值是状态增量")
    rep.out("- `add_edge(START, \"a\")` / `add_edge(\"a\", \"b\")` / `add_edge(\"b\", END)`：连线")
    rep.out("- reducer（`Annotated[list, add_messages]`）：同名键多处写入时的合并规则；"
            "没标 reducer 的键就是后写覆盖")
    rep.out("- `compile()`：图编译成 Runnable，之后 invoke / stream / astream 与普通 LangChain 组件一致")


def main() -> None:
    rep = Report()

    # ---------- 报告头 ----------
    rep.out("# 手写 LangGraph 最小图：输出全量解析")
    rep.out()
    rep.out(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    rep.out(f"- 模型：`{llm.model_name}`")
    rep.out(f"- 问题：{QUESTION}")
    rep.out("- 图：`START -> prepare -> call_llm -> END`（prepare 为普通节点，call_llm 为 LLM 节点）")
    rep.out("- 采集方式：invoke、stream(values)、stream(updates+messages) 共三次**独立**执行")
    rep.out()
    rep.out("> 说明：三次独立执行的模型回复文本、分片数量天然不同（模型随机性），但输出**结构**完全一致；")
    rep.out("> 严格对照只看同一轮执行的数据（【3】与【4】同轮采集）。")

    write_graph_def(rep)
    run_invoke(rep)
    run_stream_values(rep)
    updates_list, messages_list = run_stream_combined(rep)
    render_merge_check(rep, updates_list, messages_list)
    write_cheatsheet(rep)

    rep.save(REPORT_PATH)


if __name__ == "__main__":
    main()
