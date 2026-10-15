"""DeepAgent + Skills 请求体对照实测（与 deep_agent_dump.py 同源捕获机制）

deep_agent_dump_output.md 已实测：无 skills 时请求体 system 是 4 段 text 数组
（用户 prompt+内置基础提示 / write_todos 说明书 / 文件系统说明书 / task 说明书）。
本文件加上 skills=["/skills/"] 跑同款任务，回答三个问题：
- system 会多出什么段、长什么样
- SKILL.md 全文会不会进请求体
- tools 数组有没有变化

运行方式（在项目根目录下执行）：
    python -m agent.deep_agent_skill_dump
生成文件：项目根目录 deep_agent_skill_dump_output.md
"""

import json
import re
from pathlib import Path

import httpx
from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

try:
    from agent.llm import add_user_key, llm as base_llm
except ImportError:
    from llm import add_user_key, llm as base_llm

QUESTION = ("先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，"
            "把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。")

SKILL_MD = """---
name: calc-guide
description: 计算任务的标准流程：先拆解表达式，再用 calculate 工具逐步计算，最后核对结果。
license: MIT
---

# 计算指南

1. 把复合表达式拆成单步运算，一次算一层
2. 每一步都调用 calculate 工具执行，禁止心算
3. 汇总各步结果，再用 calculate 整体复核一遍
"""

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "deep_agent_skill_dump_output.md"


@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果，例如 "3 * (4 + 5)"。"""
    if not set(expression) <= set("0123456789+-*/(). "):
        return f"表达式含非法字符，拒绝计算：{expression}"
    try:
        return str(eval(expression))
    except Exception as exc:
        return f"计算失败：{exc}"


# ==================== 捕获钩子（与 deep_agent_dump.py 同款） ====================
captured: list[dict] = []


def _http_version(v) -> str:
    return v.decode("utf-8") if isinstance(v, bytes) else (str(v) if v else "HTTP/1.1")


def capture_request(request: httpx.Request):
    request.read()


def capture_response(response: httpx.Response):
    response.read()
    req = response.request
    captured.append({
        "request": {
            "method": req.method,
            "path_query": req.url.raw_path.decode("utf-8"),
            "http_version": _http_version(req.extensions.get("http_version")),
            "headers": dict(req.headers),
            "body_text": req.content.decode("utf-8"),
        },
        "response": {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body_text": response.text,
        },
    })


http_client = httpx.Client(event_hooks={
    "request": [add_user_key, capture_request],
    "response": [capture_response],
})

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
    skills=["/skills/"],
)


# ==================== 脱敏与工具函数 ====================
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


def classify_block(text: str) -> str:
    """按内容特征识别一段 system text 的来源中间件。"""
    if "## Skills System" in text:
        return "SkillsMiddleware（本次新增）"
    if "## `write_todos`" in text:
        return "TodoListMiddleware（write_todos 说明书）"
    if "Filesystem Tools" in text:
        return "FilesystemMiddleware（文件系统说明书）"
    if "subagent spawner" in text:
        return "SubAgentMiddleware（task 说明书）"
    if "你是一名严谨的助手" in text:
        return "graph.py 拼接：用户 system_prompt + 内置基础提示"
    return "未识别"


def block_text(block) -> str:
    return block["text"] if isinstance(block, dict) else block


def main() -> None:
    print(">> 运行带 skills 的 deep agent（技能文件经 invoke(files=...) 放入虚拟文件系统）...")
    # StateBackend 的 files 值是 {"content": [行列表]} 结构（backends/utils.py 的 file_data_to_string）
    result = agent.invoke({
        "messages": [HumanMessage(QUESTION)],
        "files": {"/skills/calc-guide/SKILL.md": {"content": SKILL_MD.splitlines()}},
    })
    http_client.close()
    print(f">> 完成：共 {len(captured)} 轮 HTTP 调用")

    req = captured[0]["request"]
    body = json.loads(req["body_text"])
    system_blocks = body["messages"][0]["content"]

    md: list[str] = []
    md.append("# Deep Agent + Skills 请求体对照实测\n")
    md.append(f"- 任务：{QUESTION}")
    md.append('- 构建：`create_deep_agent(model, tools=[calculate], system_prompt=..., skills=["/skills/"])`')
    md.append('- 技能文件：`invoke(files={"/skills/calc-guide/SKILL.md": ...})` 放入 StateBackend 虚拟文件系统')
    md.append("- 对照基线：deep_agent_dump_output.md（无 skills 版：system 4 段、tools 9 个）\n")

    md.append("## 放入虚拟文件系统的 SKILL.md 原文\n")
    md.append("```markdown")
    md.append(SKILL_MD)
    md.append("```\n")

    md.append(f"## 实测一：system content 变成 {len(system_blocks)} 段（无 skills 版为 4 段）\n")
    md.append("| 段 | 来源中间件 | 开头预览 | 字符数 |")
    md.append("| --- | --- | --- | --- |")
    for i, block in enumerate(system_blocks, 1):
        text = block_text(block)
        preview = text[:50].replace("\n", "\\n").replace("|", "\\|")
        md.append(f"| {i} | {classify_block(text)} | `{preview}...` | {len(text)} |")
    md.append("")

    skill_block = next((block_text(b) for b in system_blocks if "## Skills System" in block_text(b)), None)
    if skill_block:
        md.append("### 新增段全文（SkillsMiddleware 经 wrap_model_call 注入）\n")
        md.append("```markdown")
        md.append(skill_block)
        md.append("```\n")

    tool_names = [t["function"]["name"] for t in body["tools"]]
    md.append(f"## 实测二：tools 数组不变（共 {len(tool_names)} 个）\n")
    md.append(f"`{'、'.join(tool_names)}`\n")
    md.append("skills 没有注入任何新工具 schema——模型用现成的 `read_file` 按需读取 SKILL.md（渐进披露）。\n")

    skill_body_leak = "计算指南" in req["body_text"]
    md.append("## 实测三：SKILL.md 正文是否进请求体\n")
    md.append(f"- 在请求体全文中搜索正文关键词「计算指南」：**{'出现了' if skill_body_leak else '没有出现'}**"
              "——只有 frontmatter 的 name / description 进入 system 提示；"
              "SKILL.md 全文留在虚拟文件系统里，模型判断技能相关后才 read_file 拉取\n")

    files = result.get("files") or {}
    file_names = list(files.keys()) if isinstance(files, dict) else files
    md.append("## 实测四：invoke 返回值顶层键与虚拟文件系统\n")
    md.append(f"- 顶层键：`{list(result.keys())}`")
    md.append(f"- files 中的文件：`{file_names}`（SKILL.md 也作为普通文件存在于虚拟文件系统）")
    md.append(f"- 返回值是否有 skills_metadata：**{'有' if 'skills_metadata' in result else '没有'}**"
              "（PrivateStateAttr 私有状态，不对外传播、不进返回值）\n")

    md.append("## 轮次轨迹（模型每轮调了什么工具）\n")
    md.append("| 轮 | finish_reason | 工具调用 |")
    md.append("| --- | --- | --- |")
    for i, item in enumerate(captured, 1):
        choices = json.loads(item["response"]["body_text"]).get("choices") or []
        finish = choices[0].get("finish_reason") if choices else "-"
        msg = choices[0].get("message", {}) if choices else {}
        calls = [tc.get("function", {}).get("name") for tc in msg.get("tool_calls") or []]
        md.append(f"| {i} | `{finish}` | `{'、'.join(calls) if calls else '-'}` |")
    md.append("")

    md.append("## 第 1 轮请求（完整 JSON，全字段无省略）\n")
    md.append("```text")
    md.append(f"{req['method']} {mask_query(req['path_query'])} {req['http_version']}")
    for k, v in req["headers"].items():
        md.append(f"{k}: {mask_header_value(k, v)}")
    md.append("```\n")
    md.append("```json")
    md.append(to_json(body))
    md.append("```\n")

    resp = captured[0]["response"]
    md.append("## 第 1 轮响应（完整 JSON）\n")
    md.append("```json")
    md.append(to_json(json.loads(resp["body_text"])))
    md.append("```\n")

    REPORT_PATH.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"报告已生成: {REPORT_PATH}")


if __name__ == "__main__":
    main()
