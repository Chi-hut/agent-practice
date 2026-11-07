# -*- coding: utf-8 -*-
"""
deepagents response 序列化工具
==============================

把 deepagents `agent.invoke(...)` 返回的 response（内含 LangChain 消息对象，
如 HumanMessage / AIMessage / ToolMessage）递归转换为纯 JSON 结构：

    - 所有字段完全保留（content / additional_kwargs / response_metadata /
      tool_calls / usage_metadata / id / files 等，不丢失、不裁剪）
    - 输出带缩进美化，中文不转义（ensure_ascii=False）
    - 可作为独立模块 import，方便在测试中调用

常用 API：
    response_to_dict(response)   -> dict，可做断言/比较
    response_to_json(response)   -> str ，美化后的 JSON 字符串
    print_response(response)     -> 打印美化 JSON
    save_response(response, path)-> 写入 .json 文件（做 golden 快照对比）

兼容性：
    - LangChain / pydantic v2 消息对象（有 model_dump）优先
    - pydantic v1（有 dict）兼容
    - 其余对象兜底用 repr() 保留完整信息，绝不静默丢弃
"""

import json
import datetime
from typing import Any, Dict


def _serialize(obj: Any) -> Any:
    """递归把任意对象转成 JSON 可序列化的纯数据结构。"""
    # pydantic v2 模型（LangChain 新版消息对象都走这里）
    if hasattr(obj, "model_dump"):
        return _serialize(obj.model_dump())
    # pydantic v1 兼容
    if hasattr(obj, "dict"):
        return _serialize(obj.dict())

    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize(v) for v in obj]

    # 基础类型原样返回
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # 时间类型转 ISO 字符串（保证可 JSON 序列化且信息不丢）
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()

    # bytes 尝试按 utf-8 解码
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")

    # 兜底：未知对象用 repr 保留完整信息
    return repr(obj)


def response_to_dict(response: Any) -> Dict[str, Any]:
    """把 deepagents 的 response 转为纯 dict，字段完全保留。"""
    result = _serialize(response)
    if not isinstance(result, dict):
        raise TypeError(f"response 序列化后不是 dict，实际为 {type(result)}")
    return result


def response_to_json(
    response: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
) -> str:
    """转为美化后的 JSON 字符串。

    默认保持字段原始顺序（sort_keys=False），如需排序可传 True。
    """
    return json.dumps(
        response_to_dict(response),
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys,
    )


def save_response(response: Any, path: str, indent: int = 2) -> str:
    """保存为 JSON 文件，返回文件路径。适合生成 golden 快照用于回归对比。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(response_to_json(response, indent=indent))
    return path


def print_response(response: Any, indent: int = 2) -> None:
    """打印美化后的 JSON（控制台查看用）。"""
    print(response_to_json(response, indent=indent))


if __name__ == "__main__":
    # ---------- 演示 ----------
    # 真实使用时直接把 agent.invoke() 的返回值传进来即可。
    # 这里用带 model_dump 的模拟对象复现你贴的返回结构，保证脚本可独立运行。

    class FakeMessage:
        """模拟 LangChain 消息对象（HumanMessage/AIMessage/ToolMessage）。"""

        def __init__(self, content: str, **kwargs):
            self._data = {"content": content, **kwargs}

        def model_dump(self) -> dict:
            return dict(self._data)

    demo_response = {
        "messages": [
            FakeMessage(
                "你好，我的爱好是唱歌，帮我记录到like.txt文件中",
                additional_kwargs={},
                response_metadata={},
                type="human",
                id="9ab65f19-4142-4720-81c0-3f3fe6c07a80",
            ),
            FakeMessage(
                "",
                additional_kwargs={"refusal": None},
                response_metadata={
                    "token_usage": {
                        "completion_tokens": 150,
                        "prompt_tokens": 6025,
                        "total_tokens": 6175,
                    },
                    "model_provider": "openai",
                    "model_name": "deepseek-v4-flash-sz",
                    "finish_reason": "tool_calls",
                },
                type="ai",
                id="lc_run--01a15958-7899-7821-a7cd-f0b85d045f41-0",
                tool_calls=[
                    {
                        "name": "ls",
                        "args": {"path": "/"},
                        "id": "call_6fbe6b00a0cb4110b436a395",
                        "type": "tool_call",
                    }
                ],
                invalid_tool_calls=[],
                usage_metadata={
                    "input_tokens": 6025,
                    "output_tokens": 150,
                    "total_tokens": 6175,
                },
            ),
            FakeMessage(
                "[]",
                name="ls",
                type="tool",
                id="f0528ee1-6e2d-48ac-8e60-7db0263dc23c",
                tool_call_id="call_6fbe6b00a0cb4110b436a395",
            ),
            FakeMessage(
                "已记录到 `/like.txt`，内容为「我的爱好：唱歌」。",
                additional_kwargs={"refusal": None},
                type="ai",
                id="1dcdbf7695df4638b8e27957bb31dae3",
                tool_calls=[],
                invalid_tool_calls=[],
                usage_metadata={
                    "input_tokens": 6164,
                    "output_tokens": 18,
                    "total_tokens": 6182,
                },
            ),
        ],
        "files": {
            "/like.txt": {
                "content": ["我的爱好：唱歌"],
                "created_at": "2026-10-20T12:45:34.304867+00:00",
                "modified_at": "2026-10-20T12:45:34.304867+00:00",
            }
        },
        "interrupted": False,
        "status": "completed",
    }

    print_response(demo_response)




"""


from response_dump import response_to_dict, response_to_json, save_response, print_response

response = agent.invoke("你的测试输入")

# 方式一：转成 dict 做断言（最常用）
data = response_to_dict(response)
assert data["status"] == "completed"
assert data["messages"][-1]["content"] == "已记录到 `/like.txt`"

# 方式二：存成 golden 快照，做回归对比
save_response(response, "snapshot.json")
with open("snapshot.json", encoding="utf-8") as f:
    old = json.load(f)
assert response_to_dict(response) == old

# 方式三：控制台直接看
print_response(response)


"""