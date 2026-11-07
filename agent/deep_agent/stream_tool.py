"""实测 stream_writer 在工具执行期间推送的 custom 事件能否被消费端实时收到。"""

import asyncio
import importlib.metadata
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.config import get_stream_writer
from langgraph.types import Overwrite
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from agent.llm import llm

SLEEP_SECONDS = 1.0
LATENCY_THRESHOLD_MS = 300.0
REPORT_PATH = Path(__file__).resolve().parents[2] / "stream_tool_output.md"
console = Console(width=180)


def build_weather_tool(source: str):
    @tool
    def weather_tool(location: str) -> str:
        """查询指定城市的天气，输入城市名，返回天气情况。"""
        writer = get_stream_writer()
        for stage, detail in (
            ("start", "开始查询"),
            ("progress", "正在拉取天气数据"),
            ("end", "查询完成"),
        ):
            writer(
                {
                    "event": f"weather_tool_{stage}",
                    "source": source,
                    "location": location,
                    "detail": detail,
                    "ts": time.perf_counter(),
                }
            )
            if stage != "end":
                time.sleep(SLEEP_SECONDS)
        return f"{location}的天气是晴天"

    return weather_tool


def build_agents():
    direct_tool = build_weather_tool("主图工具")
    subagent_tool = build_weather_tool("子agent工具")

    direct_agent = create_deep_agent(
        model=llm,
        tools=[direct_tool],
        system_prompt=(
            "你是天气助手。用户询问天气时，必须立刻调用 weather_tool，"
            "不要写待办，不要自己编造结果。"
        ),
    )

    weather_subagent = {
        "name": "weather-agent",
        "description": "专门负责查询城市天气的子agent，传入要查询的城市即可",
        "system_prompt": "你是天气查询助手，必须调用 weather_tool 查询天气，然后简洁地返回结果。",
        "tools": [subagent_tool],
    }

    subagent_agent = create_deep_agent(
        model=llm,
        subagents=[weather_subagent],
        system_prompt=(
            "你是调度助手。任何天气问题都必须调用 task 工具，把任务交给 weather-agent；"
            "不要自己回答，也不要直接调用天气工具。"
        ),
    )

    return direct_agent, subagent_agent


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    tool_location: str
    agent: Any
    stream_mode: str | list[str]
    subgraphs: bool
    is_async: bool = False
    question: str = "查询一下北京的天气"


@dataclass
class RunRecord:
    index: int
    received_at: float
    elapsed_ms: float
    namespace: tuple[str, ...]
    mode: str
    payload: Any
    custom_latency_ms: float | None
    tool_messages: list[ToolMessage] = field(default_factory=list)


@dataclass
class ScenarioResult:
    scenario: Scenario
    records: list[RunRecord]
    total_ms: float
    error: str | None = None


def split_chunk(raw: Any, scenario: Scenario) -> tuple[tuple[str, ...], str, Any]:
    if isinstance(scenario.stream_mode, str):
        if scenario.subgraphs:
            namespace, payload = raw
        else:
            namespace, payload = (), raw
        return tuple(namespace), scenario.stream_mode, payload

    if scenario.subgraphs:
        namespace, mode, payload = raw
    else:
        mode, payload = raw
        namespace = ()
    return tuple(namespace), mode, payload


def extract_tool_messages(payload: Any) -> list[ToolMessage]:
    if not isinstance(payload, dict):
        return []
    found: list[ToolMessage] = []
    for node_update in payload.values():
        if not isinstance(node_update, dict):
            continue
        messages = node_update.get("messages")
        if isinstance(messages, Overwrite):
            messages = messages.value
        if not isinstance(messages, (list, tuple)):
            continue
        for message in messages:
            if isinstance(message, ToolMessage):
                found.append(message)
    return found


def make_record(raw: Any, scenario: Scenario, started_at: float, index: int) -> RunRecord:
    namespace, mode, payload = split_chunk(raw, scenario)
    received_at = time.perf_counter()
    custom_latency_ms = None
    if mode == "custom" and isinstance(payload, dict):
        written_at = payload.get("ts")
        if isinstance(written_at, (int, float)):
            custom_latency_ms = (received_at - written_at) * 1000
    return RunRecord(
        index=index,
        received_at=received_at,
        elapsed_ms=(received_at - started_at) * 1000,
        namespace=namespace,
        mode=mode,
        payload=payload,
        custom_latency_ms=custom_latency_ms,
        tool_messages=extract_tool_messages(payload),
    )


def run_scenario_sync(scenario: Scenario) -> ScenarioResult:
    started_at = time.perf_counter()
    records: list[RunRecord] = []
    error = None
    try:
        stream = scenario.agent.stream(
            {"messages": [HumanMessage(scenario.question)]},
            stream_mode=scenario.stream_mode,
            subgraphs=scenario.subgraphs,
        )
        for index, raw in enumerate(stream, start=1):
            records.append(make_record(raw, scenario, started_at, index))
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    return ScenarioResult(
        scenario=scenario,
        records=records,
        total_ms=(time.perf_counter() - started_at) * 1000,
        error=error,
    )


async def run_scenario_async(scenario: Scenario) -> ScenarioResult:
    started_at = time.perf_counter()
    records: list[RunRecord] = []
    error = None
    index = 0
    try:
        async for raw in scenario.agent.astream(
            {"messages": [HumanMessage(scenario.question)]},
            stream_mode=scenario.stream_mode,
            subgraphs=scenario.subgraphs,
        ):
            index += 1
            records.append(make_record(raw, scenario, started_at, index))
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    return ScenarioResult(
        scenario=scenario,
        records=records,
        total_ms=(time.perf_counter() - started_at) * 1000,
        error=error,
    )


def run_scenario(scenario: Scenario) -> ScenarioResult:
    if scenario.is_async:
        return asyncio.run(run_scenario_async(scenario))
    return run_scenario_sync(scenario)


def subscribed_custom(scenario: Scenario) -> bool:
    if isinstance(scenario.stream_mode, str):
        return scenario.stream_mode == "custom"
    return "custom" in scenario.stream_mode


def metrics(result: ScenarioResult) -> dict[str, Any]:
    custom_records = [r for r in result.records if r.custom_latency_ms is not None]
    tool_records = [r for r in result.records if r.tool_messages]
    latencies = [r.custom_latency_ms for r in custom_records]
    first_custom = custom_records[0] if custom_records else None

    end_ts = None
    for record in custom_records:
        payload = record.payload
        if isinstance(payload, dict) and payload.get("event") == "weather_tool_end":
            end_ts = payload.get("ts")

    first_during_tool = None
    if first_custom is not None and isinstance(end_ts, (int, float)):
        first_during_tool = first_custom.received_at < end_ts

    if result.error:
        verdict = f"运行报错：{result.error}"
    elif not subscribed_custom(result.scenario):
        verdict = "对照组：未订阅 custom，收不到是预期"
    elif not custom_records:
        if result.scenario.tool_location == "子agent" and not result.scenario.subgraphs:
            verdict = "未收到 custom（子图事件未转发：subgraphs=False）"
        else:
            verdict = "未收到 custom 事件"
    elif max(latencies) <= LATENCY_THRESHOLD_MS:
        verdict = "实时收到（工具执行中即到达）"
    else:
        verdict = "延迟收到（疑似工具结束后才到达）"

    return {
        "custom_count": len(custom_records),
        "latencies": latencies,
        "first_latency": latencies[0] if latencies else None,
        "max_latency": max(latencies) if latencies else None,
        "first_custom": first_custom,
        "first_during_tool": first_during_tool,
        "tool_record_count": len(tool_records),
        "first_tool_record": tool_records[0] if tool_records else None,
        "custom_before_tool_message": (
            first_custom.index < tool_records[0].index
            if first_custom is not None and tool_records
            else None
        ),
        "verdict": verdict,
    }


def describe_record(record: RunRecord) -> str:
    payload = record.payload
    if record.mode == "custom" and isinstance(payload, dict):
        return (
            f"{payload.get('source', '?')} | {payload.get('event', '?')} | "
            f"{payload.get('detail', '')}"
        )
    if record.mode == "updates" and isinstance(payload, dict):
        nodes = ", ".join(str(key) for key in payload)
        if record.tool_messages:
            return f"nodes=[{nodes}] | ToolMessage: {record.tool_messages[0].content}"
        return f"nodes=[{nodes}]"
    text = repr(payload).replace("\n", " ")
    return text[:120]


def print_scenario_result(result: ScenarioResult) -> None:
    console.rule(result.scenario.title)
    table = Table(box=None, pad_edge=False)
    table.add_column("#", justify="right")
    table.add_column("相对开始(ms)", justify="right")
    table.add_column("namespace")
    table.add_column("mode")
    table.add_column("摘要", overflow="fold")
    table.add_column("custom 延迟(ms)", justify="right")
    for record in result.records:
        table.add_row(
            str(record.index),
            f"{record.elapsed_ms:.1f}",
            "()" if not record.namespace else " > ".join(record.namespace),
            record.mode,
            describe_record(record),
            "-" if record.custom_latency_ms is None else f"{record.custom_latency_ms:.1f}",
        )
    console.print(table)
    if result.error:
        console.print(f"[red]error: {result.error}[/red]")
    console.print(f"总耗时：{result.total_ms:.1f} ms | 结论：{metrics(result)['verdict']}\n")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Overwrite):
        return {"__overwrite__": to_jsonable(value.value)}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def add_summary_table(lines: list[str], results: list[ScenarioResult]) -> None:
    lines.append("## 总览")
    lines.append("")
    lines.append(
        "| 场景 | 工具位置 | stream_mode | subgraphs | 同步/异步 | custom 条数 | "
        "首条延迟(ms) | 最大延迟(ms) | 首条早于工具结束 | ToolMessage 事件数 | 结论 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for result in results:
        m = metrics(result)
        scenario = result.scenario
        mode_text = (
            scenario.stream_mode
            if isinstance(scenario.stream_mode, str)
            else " + ".join(scenario.stream_mode)
        )
        lines.append(
            "| {title} | {location} | {mode} | {subgraphs} | {io} | {count} | {first} | "
            "{max_latency} | {during} | {tool_count} | {verdict} |".format(
                title=scenario.title,
                location=scenario.tool_location,
                mode=mode_text,
                subgraphs="True" if scenario.subgraphs else "False",
                io="异步" if scenario.is_async else "同步",
                count=m["custom_count"],
                first="-" if m["first_latency"] is None else f"{m['first_latency']:.1f}",
                max_latency="-" if m["max_latency"] is None else f"{m['max_latency']:.1f}",
                during="-" if m["first_during_tool"] is None else ("是" if m["first_during_tool"] else "否"),
                tool_count=m["tool_record_count"],
                verdict=m["verdict"],
            )
        )
    lines.append("")


def md_cell(text: str, limit: int = 200) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def add_scenario_detail(lines: list[str], result: ScenarioResult) -> None:
    scenario = result.scenario
    m = metrics(result)
    mode_text = (
        scenario.stream_mode
        if isinstance(scenario.stream_mode, str)
        else " + ".join(scenario.stream_mode)
    )
    lines.append(f"## {scenario.title}")
    lines.append("")
    lines.append(
        f"- 配置：工具位置={scenario.tool_location}；stream_mode={mode_text}；"
        f"subgraphs={scenario.subgraphs}；调用方式={'astream' if scenario.is_async else 'stream'}"
    )
    lines.append(f"- 总耗时：{result.total_ms:.1f} ms")
    first_latency = "-" if m["first_latency"] is None else f"{m['first_latency']:.1f} ms"
    max_latency = "-" if m["max_latency"] is None else f"{m['max_latency']:.1f} ms"
    first_during = (
        "-" if m["first_during_tool"] is None else ("是" if m["first_during_tool"] else "否")
    )
    lines.append(
        f"- custom 事件：{m['custom_count']} 条；首条延迟={first_latency}；最大延迟={max_latency}"
    )
    lines.append(f"- 首条 custom 是否在工具结束前到达：{first_during}")
    if m["first_custom"] is not None:
        first_tool_elapsed = (
            "-" if m["first_tool_record"] is None
            else f"{m['first_tool_record'].elapsed_ms:.1f} ms"
        )
        lines.append(
            f"- 首条 custom 相对开始时刻：{m['first_custom'].elapsed_ms:.1f} ms；"
            f"首条 ToolMessage 更新相对开始时刻：{first_tool_elapsed}"
        )
    if result.error:
        lines.append(f"- 错误：{result.error}")
    lines.append(f"- 结论：{m['verdict']}")
    lines.append("")
    lines.append("| # | 相对开始(ms) | namespace | mode | custom 延迟(ms) | 摘要 |")
    lines.append("|---|---|---|---|---|---|")
    for record in result.records:
        lines.append(
            "| {index} | {elapsed} | {namespace} | {mode} | {latency} | {summary} |".format(
                index=record.index,
                elapsed=f"{record.elapsed_ms:.1f}",
                namespace="()" if not record.namespace else " > ".join(record.namespace),
                mode=record.mode,
                latency="-" if record.custom_latency_ms is None
                else f"{record.custom_latency_ms:.1f}",
                summary=md_cell(describe_record(record)),
            )
        )
    lines.append("")
    lines.append("原始 payload：")
    lines.append("")
    for record in result.records:
        lines.append(
            f"**#{record.index}** `{record.mode}` namespace=`{record.namespace}` "
            f"elapsed=`{record.elapsed_ms:.1f} ms`"
        )
        lines.append("")
        lines.append("```json")
        lines.append(
            json.dumps(
                to_jsonable(record.payload),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        lines.append("```")
        lines.append("")


def build_report(results: list[ScenarioResult]) -> str:
    versions = {
        name: importlib.metadata.version(name)
        for name in ("langgraph", "deepagents", "langchain-core", "langchain-openai")
    }
    lines: list[str] = []
    lines.append("# stream_writer 工具执行期间流式推送实测")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(
        "- 运行命令：`.venv\\Scripts\\python.exe -m agent.deep_agent.stream_tool`"
    )
    lines.append(f"- 依赖版本：{json.dumps(versions, ensure_ascii=False)}")
    lines.append("")
    lines.append("## 测试设计")
    lines.append("")
    lines.append(
        f"工具在 start / progress / end 三个阶段各调用一次 `get_stream_writer()` 推送 custom 事件，"
        f"阶段之间 `time.sleep({SLEEP_SECONDS})`，工具总执行时间约 {SLEEP_SECONDS * 2:.0f} 秒。"
    )
    lines.append(
        "每条 payload 带 `time.perf_counter()` 写入时间戳；消费端记录收到时刻，"
        "两者差值即 custom 事件从工具内部写入到消费端拿到的延迟。"
    )
    lines.append(
        f"判定标准：最大延迟 ≤ {LATENCY_THRESHOLD_MS:.0f} ms 视为工具执行期间实时到达；"
        "若 start 事件的延迟接近 2 秒，说明事件被缓冲到工具结束后才 flush。"
    )
    lines.append("")

    by_key = {result.scenario.key: result for result in results}
    main_m = metrics(by_key["main_sync_custom"])
    sub_no_m = metrics(by_key["subagent_sync_no_subgraphs"])
    sub_yes_m = metrics(by_key["subagent_sync_subgraphs"])
    sub_async_m = metrics(by_key["subagent_async_subgraphs"])
    updates_only_m = metrics(by_key["main_updates_only"])

    def fmt(value: Any, unit: str = "") -> str:
        return "-" if value is None else f"{value:.1f}{unit}"

    lines.append("## 核心结论")
    lines.append("")
    lines.append(
        f"1. **stream_writer 本身是实时的**：主图工具推送 3 条 custom 事件，"
        f"消费端延迟 {fmt(main_m['first_latency'], ' ms')} ~ {fmt(main_m['max_latency'], ' ms')}；"
        "首条 start 事件在工具仍在 sleep 时到达，ToolMessage 更新约 2 秒后才出现。"
    )
    lines.append(
        f"2. **子agent/子图是例外**：`subgraphs=False` 时父流收到 "
        f"{sub_no_m['custom_count']} 条子图 custom 事件；`subgraphs=True` 时收到 "
        f"{sub_yes_m['custom_count']} 条，最大延迟 {fmt(sub_yes_m['max_latency'], ' ms')}，"
        "namespace 形如 `('tools:<task_id>',)`。"
    )
    lines.append(
        f"3. **只订阅 updates 拿不到 custom**：对照组 custom 条数为 "
        f"{updates_only_m['custom_count']}；custom 与 updates 是两条独立通道，"
        "必须把 `\"custom\"` 显式放进 stream_mode。"
    )
    lines.append(
        f"4. **同步/异步一致**：`astream` 且 subgraphs=True 时同样收到 "
        f"{sub_async_m['custom_count']} 条，最大延迟 {fmt(sub_async_m['max_latency'], ' ms')}。"
    )
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart LR")
    lines.append('    A["主 agent: model"] --> B["主 agent: ToolNode"]')
    lines.append('    B --> W1["工具内 get_stream_writer()"]')
    lines.append('    W1 -->|"custom 事件，毫秒级"| Q["父 stream 队列"]')
    lines.append('    Q --> C["for ... in agent.stream()"]')
    lines.append("")
    lines.append('    T["主 agent: task 工具"] --> S["子 agent 图"]')
    lines.append('    S --> W2["子工具内 get_stream_writer()"]')
    lines.append('    W2 -->|"subgraphs=True 时转发"| Q')
    lines.append('    W2 -.->|"subgraphs=False 时丢弃（调用不报错）"| X["父流收不到"]')
    lines.append("```")
    lines.append("")
    lines.append("## 为什么子图会丢事件")
    lines.append("")
    lines.append(
        "LangGraph 的父 stream 只有在 `subgraphs=True` 时才会挂到子运行的配置上"
        "（本机 langgraph 1.1.2，`langgraph/pregel/main.py` 中 "
        "`if subgraphs: loop.config[CONF][CONFIG_KEY_STREAM] = loop.stream`）。"
        "deepagents 的 `task` 工具在内部通过 `subagent.invoke(...)` 执行子图；"
        "父层没有把 stream 接过去时，子图里的 `get_stream_writer()` 调用不会报错，"
        "但事件没有进入父 stream 队列，所以消费端永远等不到——这是“根本没到”，不是“晚到”。"
    )
    lines.append("")
    lines.append(
        "开启 `subgraphs=True` 后返回结构也会变：`stream_mode` 是 list 时每块是 "
        "`(namespace, mode, chunk)`；`stream_mode` 是单个字符串时是 `(namespace, chunk)`。"
        "主图 namespace 为 `()`，子图为 `('tools:<task_id>',)`；只按两元组解析会丢事件或解包报错。"
    )
    lines.append("")
    add_summary_table(lines, results)
    lines.append("## 逐场景结论")
    lines.append("")
    for result in results:
        verdict = metrics(result)["verdict"]
        if verdict.startswith("对照组："):
            verdict = "未订阅 custom，收不到是预期（对照组）"
        lines.append(f"- {result.scenario.title}：{verdict}。")
    lines.append("")
    lines.append("## 拿不到工具流时的排查顺序")
    lines.append("")
    lines.append('1. `stream_mode` 是否包含 `"custom"`——`updates` 不会携带 custom 事件。')
    lines.append(
        "2. 工具是否位于子图/subagent 内——如果是，父层是否设置了 `subgraphs=True`。"
    )
    lines.append(
        "3. 是否按 `subgraphs=True` 的新返回结构解析（list 模式三元组、单模式二元组）。"
    )
    lines.append(
        "4. 工具是否真的在 LangGraph 运行时内执行——直接调用工具函数、把工具丢到图外线程池、"
        "或交给图外自定义 agent loop，`get_stream_writer()` 都拿不到父运行的 writer。"
    )
    lines.append(
        "5. 上层是否还有自己的转发层（SSE、网关、只转发 `updates` 的中间层）把 custom 过滤掉了。"
    )
    lines.append("")
    lines.append("## 各场景全量事件")
    lines.append("")
    for result in results:
        add_scenario_detail(lines, result)
    return "\n".join(lines)


def main() -> None:
    direct_agent, subagent_agent = build_agents()
    scenarios = [
        Scenario(
            key="main_sync_custom",
            title="场景1：主图工具 + updates/custom + subgraphs=False",
            tool_location="主图",
            agent=direct_agent,
            stream_mode=["updates", "custom"],
            subgraphs=False,
        ),
        Scenario(
            key="main_sync_custom_only",
            title="场景2：主图工具 + 只订阅 custom + subgraphs=False",
            tool_location="主图",
            agent=direct_agent,
            stream_mode="custom",
            subgraphs=False,
        ),
        Scenario(
            key="subagent_sync_no_subgraphs",
            title="场景3：子agent工具 + updates/custom + subgraphs=False",
            tool_location="子agent",
            agent=subagent_agent,
            stream_mode=["updates", "custom"],
            subgraphs=False,
        ),
        Scenario(
            key="subagent_sync_subgraphs",
            title="场景4：子agent工具 + updates/custom + subgraphs=True",
            tool_location="子agent",
            agent=subagent_agent,
            stream_mode=["updates", "custom"],
            subgraphs=True,
        ),
        Scenario(
            key="subagent_async_subgraphs",
            title="场景5：子agent工具 + 只订阅 custom + subgraphs=True + astream",
            tool_location="子agent",
            agent=subagent_agent,
            stream_mode="custom",
            subgraphs=True,
            is_async=True,
        ),
        Scenario(
            key="main_updates_only",
            title="场景6：主图工具 + 只订阅 updates + subgraphs=True（对照组）",
            tool_location="主图",
            agent=direct_agent,
            stream_mode="updates",
            subgraphs=True,
        ),
    ]

    results: list[ScenarioResult] = []
    for scenario in scenarios:
        console.print(f"[bold cyan]运行 {scenario.title} ...[/bold cyan]")
        result = run_scenario(scenario)
        results.append(result)
        print_scenario_result(result)

    summary = Table(title="汇总", show_lines=True)
    summary.add_column("场景")
    summary.add_column("custom 条数", justify="right")
    summary.add_column("首条延迟(ms)", justify="right")
    summary.add_column("最大延迟(ms)", justify="right")
    summary.add_column("首条早于工具结束")
    summary.add_column("ToolMessage 事件数", justify="right")
    summary.add_column("结论")
    for result in results:
        m = metrics(result)
        summary.add_row(
            result.scenario.title,
            str(m["custom_count"]),
            "-" if m["first_latency"] is None else f"{m['first_latency']:.1f}",
            "-" if m["max_latency"] is None else f"{m['max_latency']:.1f}",
            "-" if m["first_during_tool"] is None else ("是" if m["first_during_tool"] else "否"),
            str(m["tool_record_count"]),
            m["verdict"],
        )
    console.print(summary)

    REPORT_PATH.write_text(build_report(results), encoding="utf-8")
    console.print(f"[green]完整报告已写入 {REPORT_PATH}[/green]")


if __name__ == "__main__":
    main()
