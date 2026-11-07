"""对照组：普通工具返回超大结果时，FilesystemMiddleware 会把它改写成什么样（离线测试）。

与 read_large_file_test.py 的 read_file 路径对比：
- 这里的工具不在排除名单里，结果会被转存到 /large_tool_results/<tool_call_id>；
- state 和下一次模型请求里只剩一段约 1.1k 字符的提示 + 头尾预览。

运行（项目根目录）：
    PYTHONUTF8=1 PYTHONPATH=. .venv/Scripts/python -m agent.deep_agent.file_agent.large_result_eviction_test
"""

import json
from datetime import datetime

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import NUM_CHARS_PER_TOKEN, TOOLS_EXCLUDED_FROM_EVICTION
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from agent.deep_agent.file_agent._fixture import OUT, WORKSPACE, build_workspace
from agent.deep_agent.file_agent._harness import (
    RawToolProbe,
    ScriptedChatModel,
    check,
    details,
    fence,
    render_checks,
    tool_call_message,
)

TOKEN_LIMIT = 20000
CHAR_LIMIT = NUM_CHARS_PER_TOKEN * TOKEN_LIMIT
CALL_ID = "call_dump_logs_1"


@tool
def dump_logs() -> str:
    """一次性导出全部服务日志，返回完整原始文本。"""
    return (WORKSPACE / "huge.log").read_text(encoding="utf-8")


def main() -> None:
    build_workspace()
    OUT.mkdir(parents=True, exist_ok=True)
    raw_text = (WORKSPACE / "huge.log").read_text(encoding="utf-8")

    model = ScriptedChatModel([tool_call_message("dump_logs", {}, CALL_ID), AIMessage(content="已完成")])
    probe = RawToolProbe()
    agent = create_deep_agent(
        model=model,
        backend=FilesystemBackend(root_dir=WORKSPACE, virtual_mode=True),
        tools=[dump_logs],
        middleware=[probe],
    )
    response = agent.invoke({"messages": [HumanMessage(content="导出全部日志并总结")]})

    raw = probe.records[-1]
    state_msg = [m for m in response["messages"] if isinstance(m, ToolMessage)][-1]
    next_tool = [m for m in model.requests[-1]["messages"] if m.get("role") == "tool"][-1]
    evicted = WORKSPACE / "large_tool_results" / CALL_ID
    evicted_text = evicted.read_text(encoding="utf-8") if evicted.exists() else ""

    checks = []
    check(checks, "工具原始返回就是完整文件", raw.content == raw_text,
          f"{len(raw.content)} 字符 / {len(raw.content.splitlines())} 行")
    check(checks, "超过阈值需要转存", len(raw.content) > CHAR_LIMIT, f"{len(raw.content)} > {CHAR_LIMIT}")
    check(checks, "中间件改写了内容", state_msg.content != raw.content,
          f"{len(raw.content)} -> {len(state_msg.content)} 字符")
    check(checks, "转存文件存在且与原始全文逐字一致", evicted_text == raw_text, str(evicted))
    check(checks, "下一次请求里的 tool 消息就是改写后的内容", next_tool["content"] == state_msg.content,
          f"{len(next_tool['content'])} 字符")
    check(checks, "原始全文没有进入任何一次请求", all(
        raw_text[:2000] not in json.dumps(r, ensure_ascii=False) for r in model.requests), "")
    check(checks, "FilesystemBackend 下 state 无 files 字段", response.get("files") is None, str(response.get("files")))

    table = render_checks(checks)
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    print(f"raw {len(raw.content)} -> state {len(state_msg.content)} 字符；文件 {evicted}")
    print(f"report 内容见 {OUT / 'large_result_eviction_report.md'}")

    report = "\n".join([
        "# 普通工具返回超大结果：FilesystemMiddleware 改写实录（离线实测）",
        "",
        f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "- 运行方式：`PYTHONUTF8=1 PYTHONPATH=. .venv/Scripts/python -m agent.deep_agent.file_agent.large_result_eviction_test`",
        f"- 工作区：`{WORKSPACE}`",
        f"- 排除名单（不参与转存）：`{', '.join(TOOLS_EXCLUDED_FROM_EVICTION)}`",
        "",
        "## 1. 校验",
        "",
        table,
        "",
        "## 2. 改写前后",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 工具名 | dump_logs（不在排除名单） |",
        f"| 原始返回 | {len(raw.content)} 字符 / {len(raw.content.splitlines())} 行 |",
        f"| 阈值 | {NUM_CHARS_PER_TOKEN} × {TOKEN_LIMIT} = {CHAR_LIMIT} 字符 |",
        f"| state 中的 ToolMessage | {len(state_msg.content)} 字符 |",
        f"| 虚拟路径 | `/large_tool_results/{CALL_ID}` |",
        f"| 真实路径 | `{evicted}` |",
        f"| response['files'] | {response.get('files')} |",
        "",
        "## 3. 模型实际看到的内容（逐字）",
        "",
        fence(state_msg.content),
        "",
        "## 4. state 中 ToolMessage 的完整字段",
        "",
        fence(json.dumps({
            "type": type(state_msg).__name__,
            "id": state_msg.id,
            "name": state_msg.name,
            "tool_call_id": state_msg.tool_call_id,
            "status": state_msg.status,
            "content": state_msg.content,
        }, ensure_ascii=False, indent=2), "json"),
        "",
        "## 5. 转存文件",
        "",
        details(f"文件开头 10 行（完整 {len(evicted_text)} 字符见文件）",
                fence("\n".join(evicted_text.splitlines()[:10]))),
        "",
        "## 6. 与 read_file 的对比",
        "",
        "| | 本用例（普通工具） | read_file 读大文件 |",
        "|---|---|---|",
        "| 改写位置 | `FilesystemMiddleware.wrap_tool_call` | read_file 工具内部 |",
        "| 是否落盘 | 是 | 否 |",
        f"| 模型看到 | 约 {len(state_msg.content)} 字符的提示 + 头尾预览 | 最多 {CHAR_LIMIT} 字符原文 + 截断提示 |",
        "| 能否拿回全文 | 能，read_file 分页读转存文件 | 不能，继续用 offset/limit 读原文件 |",
        "",
    ])
    report_path = OUT / "large_result_eviction_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"report: {report_path} ({report_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
