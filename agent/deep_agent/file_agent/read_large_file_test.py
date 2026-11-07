"""read_file 读取大文件时，到底被改写成什么样（离线确定性测试）。

结论先行：read_file 在 TOOLS_EXCLUDED_FROM_EVICTION 名单里，FilesystemMiddleware
不会把它转存到 /large_tool_results/；真正的截断发生在 read_file 工具内部
（deepagents/middleware/filesystem.py:596-611）：
  1. 先按 offset/limit 取行；
  2. 字符数 >= 4 * 20000 = 80000 时，按字符截断；
  3. 末尾追加 READ_FILE_TRUNCATION_MSG。

运行（项目根目录）：
    PYTHONUTF8=1 PYTHONPATH=. .venv/Scripts/python -m agent.deep_agent.file_agent.read_large_file_test

输出：
    控制台摘要 + agent/deep_agent/file_agent/_out/read_large_file_report.md
"""

import json
from datetime import datetime

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import (
    NUM_CHARS_PER_TOKEN,
    READ_FILE_TRUNCATION_MSG,
    TOOLS_EXCLUDED_FROM_EVICTION,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.deep_agent.file_agent._fixture import OUT, WORKSPACE, build_workspace, file_stats
from agent.deep_agent.file_agent._harness import (
    RawToolProbe,
    ScriptedChatModel,
    check,
    fence,
    head_tail_lines,
    render_checks,
    tool_call_message,
)

TOKEN_LIMIT = 20000
CHAR_LIMIT = NUM_CHARS_PER_TOKEN * TOKEN_LIMIT  # 80000

CASES = [
    ("A 默认分页", {"file_path": "/huge.log", "offset": 0, "limit": 100}),
    ("B 一次性读 4000 行", {"file_path": "/huge.log", "offset": 0, "limit": 4000}),
    ("C 从第 1000 行读 2000 行", {"file_path": "/huge.log", "offset": 999, "limit": 2000}),
]


def run_case(name: str, args: dict, stats: dict) -> tuple[dict, str]:
    model = ScriptedChatModel([tool_call_message("read_file", args, "call_read_1"), AIMessage(content="已完成")])
    probe = RawToolProbe()
    agent = create_deep_agent(
        model=model,
        backend=FilesystemBackend(root_dir=WORKSPACE, virtual_mode=True),
        middleware=[probe],
    )
    response = agent.invoke({"messages": [HumanMessage(content=f"读取 /huge.log，参数 {args}")]})

    raw = probe.records[-1]
    state_msg = [m for m in response["messages"] if isinstance(m, ToolMessage)][-1]
    next_tool = [m for m in model.requests[-1]["messages"] if m.get("role") == "tool"][-1]
    evicted_files = sorted(p.name for p in (WORKSPACE / "large_tool_results").glob("*")) \
        if (WORKSPACE / "large_tool_results").exists() else []
    truncation_msg = READ_FILE_TRUNCATION_MSG.format(file_path=args["file_path"])
    truncated = raw.content.endswith(truncation_msg)

    checks = []
    check(checks, "工具返回未被中间件改写（state == 工具原始返回）", state_msg.content == raw.content,
          f"{len(raw.content)} 字符")
    check(checks, "下一次模型请求里的 tool 消息与其一致", next_tool["content"] == raw.content,
          f"{len(next_tool['content'])} 字符")
    check(checks, "返回长度不超过 80000 字符", len(raw.content) <= CHAR_LIMIT, f"{len(raw.content)}")
    if truncated:
        check(checks, "发生截断时长度正好等于 80000", len(raw.content) == CHAR_LIMIT, f"{len(raw.content)}")
        check(checks, "截断标记出现且仅在末尾", raw.content.count(truncation_msg) == 1
              and raw.content.endswith(truncation_msg), "")
    else:
        check(checks, "未发生截断", len(raw.content) < CHAR_LIMIT, f"{len(raw.content)}")
    check(checks, "没有被转存到 /large_tool_results", evicted_files == [], str(evicted_files))

    row = {
        "name": name,
        "args": args,
        "stats": stats,
        "raw_len": len(raw.content),
        "raw_lines": len(raw.content.splitlines()),
        "raw": raw.content,
        "truncated": truncated,
        "truncation_msg": truncation_msg,
        "state_len": len(state_msg.content),
        "next_len": len(next_tool["content"]),
        "evicted_files": evicted_files,
        "checks": checks,
    }
    print(f"[{name}] 请求 limit={args['limit']} offset={args['offset']} -> "
          f"返回 {row['raw_len']} 字符 / {row['raw_lines']} 行，截断={truncated}，"
          f"state==raw={'是' if state_msg.content == raw.content else '否'}，转存文件={evicted_files or '无'}")
    return row, render_checks(checks)


def build_report(rows: list, stats: dict, check_tables: list) -> str:
    lines = [
        "# read_file 读取大文件：改写结果全量实录（离线实测）",
        "",
        f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "- 运行方式：`PYTHONUTF8=1 PYTHONPATH=. .venv/Scripts/python -m agent.deep_agent.file_agent.read_large_file_test`",
        "- 说明：模型回复是脚本化的，工具、中间件、backend、state、请求体全部真实执行。",
        f"- 工作区：`{WORKSPACE}`",
        "",
        "## 0. 结论",
        "",
        "| 问题 | 答案 |",
        "|---|---|",
        "| 是 `FilesystemMiddleware.wrap_tool_call` 转存的吗？ | **不是**。`read_file` 在 `TOOLS_EXCLUDED_FROM_EVICTION` 里 |",
        f"| 排除名单 | `{', '.join(TOOLS_EXCLUDED_FROM_EVICTION)}` |",
        "| 那是谁改的？ | `read_file` 工具自己（filesystem.py:596-611） |",
        f"| 怎么改？ | 先按 offset/limit 取行，再按 {CHAR_LIMIT} 字符硬截断，末尾追加提示 |",
        "| 截断粒度 | **字符**，不是行，最后一行可能被从中间切断 |",
        "| 模型知道被截断吗？ | 知道，末尾有明确的英文提示 |",
        "| 会不会产生 `/large_tool_results/<id>`？ | 不会 |",
        "",
        "`read_file` 截断源码：",
        "",
        fence(
            "if token_limit and len(result) >= NUM_CHARS_PER_TOKEN * token_limit:\n"
            "    truncation_msg = READ_FILE_TRUNCATION_MSG.format(file_path=validated_path)\n"
            "    max_content_length = NUM_CHARS_PER_TOKEN * token_limit - len(truncation_msg)\n"
            "    result = result[:max_content_length]\n"
            "    result += truncation_msg",
            "python",
        ),
        "",
        "## 1. 测试文件",
        "",
        "| 文件 | 行数 | 字符数 | 字节数 |",
        "|---|---|---|---|",
        f"| huge.log | {stats['lines']} | {stats['chars']} | {stats['bytes']} |",
        "",
    ]
    for row, table in zip(rows, check_tables):
        truncated_tail = row["raw"][-len(row["truncation_msg"]) - 260:]
        lines += [
            f"## 2.{ord(row['name'][0]) - 64} 用例 {row['name']}",
            "",
            "| 项 | 值 |",
            "|---|---|",
            f"| 请求参数 | `{json.dumps(row['args'], ensure_ascii=False)}` |",
            f"| 工具返回 | {row['raw_len']} 字符 / {row['raw_lines']} 行 |",
            f"| 是否截断 | {'是' if row['truncated'] else '否'} |",
            f"| state 里的 ToolMessage | {row['state_len']} 字符 |",
            f"| 下一次请求里的 tool 消息 | {row['next_len']} 字符 |",
            f"| /large_tool_results | {row['evicted_files'] or '无'} |",
            "",
            table,
            "",
            "### 返回内容（头 10 行 + 尾 5 行）",
            "",
            fence(head_tail_lines(row["raw"], 10, 5)),
            "",
        ]
        if row["truncated"]:
            lines += [
                "### 截断处（最后 260 字符 + 截断提示）",
                "",
                fence(truncated_tail),
                "",
                f"截断提示原文（{len(row['truncation_msg'])} 字符）：",
                "",
                fence(row["truncation_msg"].strip()),
                "",
            ]
    lines += [
        "## 3. 和转存路径的区别",
        "",
        "| | `read_file` 读大文件 | 自定义工具返回大结果 |",
        "|---|---|---|",
        "| 谁处理 | read_file 工具内部 | `FilesystemMiddleware.wrap_tool_call` |",
        "| 是否写文件 | 否 | 是，写到 `/large_tool_results/<tool_call_id>` |",
        f"| 模型看到的长度 | 固定不超过 {CHAR_LIMIT} 字符 | 约 1~2k 字符的转存提示 + 头尾预览（随路径与预览长度变化） |",
        "| 模型能否拿回全文 | 不能，只能继续用 offset/limit 读 | 能，用 read_file 分页读转存文件 |",
        "| 实测脚本 | 本文件 | `large_result_eviction_test.py` |",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    build_workspace()
    OUT.mkdir(parents=True, exist_ok=True)
    stats = file_stats(WORKSPACE / "huge.log")
    print(f"huge.log: {stats['lines']} 行 / {stats['chars']} 字符 / {stats['bytes']} 字节，阈值 {CHAR_LIMIT}")
    rows, tables = [], []
    for name, args in CASES:
        row, table = run_case(name, args, stats)
        rows.append(row)
        tables.append(table)
    report = build_report(rows, stats, tables)
    report_path = OUT / "read_large_file_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"report: {report_path} ({report_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
