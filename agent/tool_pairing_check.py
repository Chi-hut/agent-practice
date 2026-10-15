"""
消息配对校验实测：孤立 ToolMessage / 无应答 tool_calls 是否真的返回 400？

被验证的说法："配对清洗：丢弃孤立 ToolMessage / 无应答 tool_calls，否则 DeepSeek/OpenAI 返回 400"。

OpenAI 协议把 role=tool 消息定义为"对某个 tool_call 的回执"：assistant 消息的
tool_calls 数组里每个 id，都必须在后续的 tool 消息里以 tool_call_id 出现一次。
本脚本用 4 个用例 × 2 个模型直接裸发 httpx 验证（不经 langchain 转换层，报错即
服务端原文；所有消息手工构造，也不传 tools 参数——校验的是消息序列本身）：

  用例 1  正确配对（对照组）：user -> assistant(tool_calls) -> tool(id 匹配)
  用例 2  孤立 ToolMessage：  user -> tool（前面没有带 tool_calls 的 assistant）
  用例 3  无应答 tool_calls： user -> assistant(tool_calls)（之后没有 tool 回包）
  用例 4  id 不匹配：        调用的是 call_001，回包却写 call_999

运行（项目根目录）：python -m agent.tool_pairing_check
生成：tool_pairing_check_output.md（每用例请求消息序列与响应原文全量）
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API_KEY = os.getenv("LLM_API_KEY")
USER_KEY = os.getenv("LLM_USER_KEY")

# 两个模型代表两大家族：gpt-5.6-terra 走 OpenAI 兼容网关；deepseek-v4-flash-sz 是 DeepSeek 系列
MODELS = [
    ("gpt-5.6-terra-ptu", os.getenv("LLM_BASE_URL_HR")),
    ("deepseek-v4-flash-sz", os.getenv("LLM_BASE_URL_V1")),
]

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "tool_pairing_check_output.md"


# ---------------------------------------------------------------------------
# 消息工厂：每次调用现造，避免对象复用
# ---------------------------------------------------------------------------

def m_user() -> dict:
    return {"role": "user", "content": "青岛今天天气怎么样？"}


def m_assistant(call_id: str = "call_001") -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": "get_weather", "arguments": "{\"city\": \"青岛\"}"},
        }],
    }


def m_tool(call_id: str = "call_001") -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": "晴，26 度，东南风 3 级"}


CASES = [
    ("1 正确配对（对照组）", lambda: [m_user(), m_assistant(), m_tool()]),
    ("2 孤立 ToolMessage（前面没有带 tool_calls 的 assistant）", lambda: [m_user(), m_tool()]),
    ("3 无应答 tool_calls（assistant 发起调用后没有 tool 回包）", lambda: [m_user(), m_assistant()]),
    ("4 tool_call_id 不匹配（调用 call_001，回包写 call_999）",
     lambda: [m_user(), m_assistant("call_001"), m_tool("call_999")]),
]


def add_user_key(request: httpx.Request) -> None:
    sep = "&" if "?" in str(request.url) else "?"
    request.url = httpx.URL(f"{request.url}{sep}user_key={USER_KEY}")


def main() -> None:
    results = []
    with httpx.Client(timeout=120, event_hooks={"request": [add_user_key]}) as client:
        for model, base in MODELS:
            for title, make_msgs in CASES:
                url = base.rstrip("/") + "/chat/completions"
                msgs = make_msgs()
                print(f">> {model} × {title} ...", flush=True)
                t0 = time.perf_counter()
                try:
                    r = client.post(url, headers={"Authorization": f"Bearer {API_KEY}"},
                                    json={"model": model, "messages": msgs})
                    status, body = r.status_code, r.text
                except Exception as e:
                    status, body = "ERR", repr(e)
                elapsed = time.perf_counter() - t0
                results.append({
                    "model": model, "case": title,
                    "messages": msgs, "status": status,
                    "body": body[:4000], "elapsed": round(elapsed, 2),
                })
                print(f"   HTTP {status}（{elapsed:.2f}s）", flush=True)

    # ---- 渲染 md 全量报告 ----
    md = ["# tool 消息配对校验实测：孤立 ToolMessage / 无应答 tool_calls 会 400 吗\n"]
    md.append(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("- 方式：httpx 裸发 chat/completions，消息手工构造，不传 tools 参数"
              "（校验的是消息序列本身），报错即服务端原文\n")
    md.append("## 结论总览\n")
    md.append("| 模型 | 用例 | HTTP | 服务端反应 |")
    md.append("| --- | --- | --- | --- |")
    for rec in results:
        if rec["status"] == 200:
            try:
                content = json.loads(rec["body"])["choices"][0]["message"]["content"] or ""
                reaction = "✅ 正常回答：" + content.replace("\n", " ")[:60]
            except Exception:
                reaction = "✅ 正常返回"
        elif isinstance(rec["status"], int):
            try:
                msg = json.loads(rec["body"])["error"]["message"]
                reaction = "❌ 400 拒绝：" + msg.replace("\n", " ")[:80]
            except Exception:
                reaction = f"❌ {rec['status']}"
        else:
            reaction = "连接层异常"
        md.append(f"| `{rec['model']}` | {rec['case']} | {rec['status']} | {reaction} |")
    md.append("")
    for rec in results:
        md.append(f"## `{rec['model']}` × {rec['case']}\n")
        md.append(f"HTTP 状态：**{rec['status']}** ｜ 耗时：{rec['elapsed']}s\n")
        md.append("请求 messages：")
        md.append("```json")
        md.append(json.dumps(rec["messages"], ensure_ascii=False, indent=2))
        md.append("```\n")
        md.append("响应原文（截断至 4000 字符）：")
        md.append("```json")
        md.append(rec["body"])
        md.append("```\n")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\n已生成: {OUT_MD}")


if __name__ == "__main__":
    main()
