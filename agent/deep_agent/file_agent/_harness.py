"""离线测试基础设施：脚本化模型、原始工具结果探针、报告片段工具。

模型回复是脚本化的，但请求体由 langchain-openai 的 _get_request_payload 真实生成，
工具、中间件、backend、state 全部真实执行，不需要联网。
"""

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI


class ScriptedChatModel(ChatOpenAI):
    def __init__(self, messages: list):
        super().__init__(model="scripted-offline", api_key="offline")
        object.__setattr__(self, "script", list(messages))
        object.__setattr__(self, "requests", [])

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        self.requests.append(payload)
        message = self.script.pop(0)
        return ChatResult(generations=[ChatGeneration(message=message)])


def tool_call_message(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


class RawToolProbe(AgentMiddleware):
    """位于内置中间件内层：记录工具刚返回、还没被 FilesystemMiddleware 改写的 ToolMessage。"""

    def __init__(self):
        self.records = []

    def wrap_tool_call(self, request, handler):
        result = handler(request)
        self.records.append(result)
        return result


def fence(text: str, lang: str = "") -> str:
    return f"````{lang}\n{text}\n````"


def details(summary: str, body: str) -> str:
    return f"<details><summary>{summary}</summary>\n\n{body}\n\n</details>"


def head_tail_lines(text: str, n_head: int = 10, n_tail: int = 5) -> str:
    lines = text.splitlines()
    if len(lines) <= n_head + n_tail:
        return "\n".join(lines)
    omitted = len(lines) - n_head - n_tail
    return "\n".join(lines[:n_head] + [f"... 省略 {omitted} 行 ..."] + lines[-n_tail:])


def check(rows: list, name: str, ok: bool, detail: str = "") -> bool:
    rows.append((name, ok, detail))
    return ok


def render_checks(rows: list) -> str:
    out = ["| 校验项 | 结果 | 说明 |", "|---|---|---|"]
    for name, ok, detail in rows:
        out.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    return "\n".join(out)
