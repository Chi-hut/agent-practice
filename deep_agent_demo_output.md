# DeepAgent（deepagents）输出全量解析

- 采集时间：2026-10-13 19:55:53
- 模型：`deepseek-v4-flash-sz`
- deepagents 版本：`0.4.12`
- 问题：先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。
- Agent 构建：`create_deep_agent(model=llm, tools=[calculate], system_prompt=...)`
- 采集方式：invoke、stream(updates+messages) 共两次**独立**执行

> 说明：两次独立执行的回复文本、分片数量天然不同（模型随机性），但输出**结构**一致；
> 严格对照只看同一轮执行的数据（【2】与【3】同轮采集）。

## 【0】deep agent 的定义：与 create_agent 差在哪

create_deep_agent 底层同样是 LangGraph 状态图，但通过中间件自动注入了**todo 计划、虚拟文件系统、子代理**三套能力。本次只给它一个 calculate 工具，内置工具（write_todos、ls、read_file、write_file、edit_file）会在实际运行时以 tool_calls 形式现身（见【2】的每一步记录）。

### 创建代码

````python
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

````
````python
agent = create_deep_agent(
    model=llm,
    tools=[calculate],
    system_prompt="你是一名严谨的助手。涉及计算必须调用 calculate 工具，不要自己心算。",
)
````
- deepagents 版本：`0.4.12`
- 签名要点：`create_deep_agent(model, tools, system_prompt, middleware, subagents, backend, ...)`，不传 backend 时默认 StateBackend（文件存 state）

### 图结构（`agent.get_graph()` 的原始数据）

- 节点（全量）：

````json
[
  {
    "id": "__start__",
    "name": "__start__",
    "type": null,
    "metadata": null
  },
  {
    "id": "model",
    "name": "model",
    "type": null,
    "metadata": null
  },
  {
    "id": "tools",
    "name": "tools",
    "type": null,
    "metadata": null
  },
  {
    "id": "TodoListMiddleware.after_model",
    "name": "TodoListMiddleware.after_model",
    "type": null,
    "metadata": null
  },
  {
    "id": "PatchToolCallsMiddleware.before_agent",
    "name": "PatchToolCallsMiddleware.before_agent",
    "type": null,
    "metadata": null
  },
  {
    "id": "__end__",
    "name": "__end__",
    "type": null,
    "metadata": null
  }
]
````
- 边（全量）：

````json
[
  {
    "source": "PatchToolCallsMiddleware.before_agent",
    "target": "model",
    "conditional": false,
    "data": null
  },
  {
    "source": "TodoListMiddleware.after_model",
    "target": "__end__",
    "conditional": true,
    "data": null
  },
  {
    "source": "TodoListMiddleware.after_model",
    "target": "model",
    "conditional": true,
    "data": null
  },
  {
    "source": "TodoListMiddleware.after_model",
    "target": "tools",
    "conditional": true,
    "data": null
  },
  {
    "source": "__start__",
    "target": "PatchToolCallsMiddleware.before_agent",
    "conditional": false,
    "data": null
  },
  {
    "source": "model",
    "target": "TodoListMiddleware.after_model",
    "conditional": false,
    "data": null
  },
  {
    "source": "tools",
    "target": "model",
    "conditional": true,
    "data": null
  }
]
````
- mermaid 图源码：

````mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	model(model)
	tools(tools)
	TodoListMiddleware\2eafter_model(TodoListMiddleware.after_model)
	PatchToolCallsMiddleware\2ebefore_agent(PatchToolCallsMiddleware.before_agent)
	__end__([<p>__end__</p>]):::last
	PatchToolCallsMiddleware\2ebefore_agent --> model;
	TodoListMiddleware\2eafter_model -.-> __end__;
	TodoListMiddleware\2eafter_model -.-> model;
	TodoListMiddleware\2eafter_model -.-> tools;
	__start__ --> PatchToolCallsMiddleware\2ebefore_agent;
	model --> TodoListMiddleware\2eafter_model;
	tools -.-> model;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

````

## 【1】agent.invoke：阻塞到全部结束，一次拿到最终状态

### 顶层结构（deep agent 与 create_agent 的第一个差异在这里）

- 返回类型：`dict`（最终状态 dict）
- 顶层键：`['messages', 'files', 'todos']`（create_agent 通常只有 messages；deep agent 多出 todos 与 files 两个内置字段）
- messages 共 10 条，序列：`HumanMessage` -> `AIMessage` -> `ToolMessage` -> `ToolMessage` -> `AIMessage` -> `ToolMessage` -> `ToolMessage` -> `AIMessage` -> `ToolMessage` -> `AIMessage`

### 内置字段一：todos（执行计划）

- todos 共 3 项：
  - [completed] 制定 todo 计划
  - [completed] 计算 (2026 * 3 + 114) / 7
  - [completed] 将计算过程和结果写入 result.txt

### 内置字段二：files（虚拟文件系统）

- files 共 1 个文件（存在 state 里，不落真实磁盘）：
  - `/result.txt`（类型 `builtins.dict`）：
````json
{
  "content": [
    "计算过程：",
    "(2026 * 3 + 114) / 7",
    "= (6078 + 114) / 7",
    "= 6192 / 7",
    "= 884.5714285714286",
    "",
    "结果：884.5714285714286"
  ],
  "created_at": "2026-10-13T11:55:57.219592+00:00",
  "modified_at": "2026-10-13T11:55:57.219592+00:00"
}
````

### 完整返回值（原样一体化导出，一个字段不省略）

````json
{
  "messages": [
    {
      "content": "先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "human",
      "name": null,
      "id": "f74d225b-f9a0-496c-a33b-8d3084bbb0a6"
    },
    {
      "content": "",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 523,
          "prompt_tokens": 6133,
          "total_tokens": 6656,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 375,
            "rejected_prediction_tokens": null,
            "text_tokens": 148
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "9e42c4008466401da6ec8bcc8a3f3414",
        "finish_reason": "tool_calls",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a1351e-81cc-7270-8f08-802147c6426e-0",
      "tool_calls": [
        {
          "name": "write_todos",
          "args": {
            "todos": [
              {
                "content": "制定 todo 计划",
                "status": "in_progress"
              },
              {
                "content": "计算 (2026 * 3 + 114) / 7",
                "status": "pending"
              },
              {
                "content": "将计算过程和结果写入 result.txt",
                "status": "pending"
              }
            ]
          },
          "id": "call_6e4cd01346ac4848b44af2f2",
          "type": "tool_call"
        },
        {
          "name": "calculate",
          "args": {
            "expression": "(2026 * 3 + 114) / 7"
          },
          "id": "call_9a4b62c8e24e42019affc10e",
          "type": "tool_call"
        }
      ],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 6133,
        "output_tokens": 523,
        "total_tokens": 6656,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 375
        }
      }
    },
    {
      "content": "Updated todo list to [{'content': '制定 todo 计划', 'status': 'in_progress'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'pending'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}]",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "tool",
      "name": "write_todos",
      "id": "595388e8-1824-4b17-ac2a-a41cea2444e0",
      "tool_call_id": "call_6e4cd01346ac4848b44af2f2",
      "artifact": null,
      "status": "success"
    },
    {
      "content": "884.5714285714286",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "tool",
      "name": "calculate",
      "id": "a6fc62e3-9d23-4cf0-b74b-67dfddb6de9a",
      "tool_call_id": "call_9a4b62c8e24e42019affc10e",
      "artifact": null,
      "status": "success"
    },
    {
      "content": "",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 232,
          "prompt_tokens": 6376,
          "total_tokens": 6608,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 20,
            "rejected_prediction_tokens": null,
            "text_tokens": 212
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "383e89243298468c9cada15831eb71bf",
        "finish_reason": "tool_calls",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a1351e-8abf-76d3-bcfa-3938391fc958-0",
      "tool_calls": [
        {
          "name": "write_todos",
          "args": {
            "todos": [
              {
                "content": "制定 todo 计划",
                "status": "completed"
              },
              {
                "content": "计算 (2026 * 3 + 114) / 7",
                "status": "completed"
              },
              {
                "content": "将计算过程和结果写入 result.txt",
                "status": "in_progress"
              }
            ]
          },
          "id": "call_7b01b5c6c8f14a498ff610a0",
          "type": "tool_call"
        },
        {
          "name": "write_file",
          "args": {
            "file_path": "/result.txt",
            "content": "计算过程：\n(2026 * 3 + 114) / 7\n= (6078 + 114) / 7\n= 6192 / 7\n= 884.5714285714286\n\n结果：884.5714285714286"
          },
          "id": "call_e744b4848a894b548252e7ba",
          "type": "tool_call"
        }
      ],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 6376,
        "output_tokens": 232,
        "total_tokens": 6608,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 20
        }
      }
    },
    {
      "content": "Updated todo list to [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}]",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "tool",
      "name": "write_todos",
      "id": "eb2ccc60-f6c9-4a6e-bbae-41e07ad7f36c",
      "tool_call_id": "call_7b01b5c6c8f14a498ff610a0",
      "artifact": null,
      "status": "success"
    },
    {
      "content": "Updated file /result.txt",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "tool",
      "name": "write_file",
      "id": "83707fc7-eb3c-4390-9b86-4d2821637063",
      "tool_call_id": "call_e744b4848a894b548252e7ba",
      "artifact": null,
      "status": "success"
    },
    {
      "content": "",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 106,
          "prompt_tokens": 6680,
          "total_tokens": 6786,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 1,
            "rejected_prediction_tokens": null,
            "text_tokens": 105
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "1272d09156b3423395690d28de37867a",
        "finish_reason": "tool_calls",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a1351e-8e27-7c73-820a-41ab52322eb8-0",
      "tool_calls": [
        {
          "name": "write_todos",
          "args": {
            "todos": [
              {
                "content": "制定 todo 计划",
                "status": "completed"
              },
              {
                "content": "计算 (2026 * 3 + 114) / 7",
                "status": "completed"
              },
              {
                "content": "将计算过程和结果写入 result.txt",
                "status": "completed"
              }
            ]
          },
          "id": "call_76a2766ad7034bfabb15cf8c",
          "type": "tool_call"
        }
      ],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 6680,
        "output_tokens": 106,
        "total_tokens": 6786,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 1
        }
      }
    },
    {
      "content": "Updated todo list to [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}]",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "tool",
      "name": "write_todos",
      "id": "cd175240-fb0e-43f2-ae6c-ec5beff3c765",
      "tool_call_id": "call_76a2766ad7034bfabb15cf8c",
      "artifact": null,
      "status": "success"
    },
    {
      "content": "(2026 * 3 + 114) / 7 = 6192 / 7 ≈ 884.571，计算过程已写入 result.txt。",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 35,
          "prompt_tokens": 6863,
          "total_tokens": 6898,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 1,
            "rejected_prediction_tokens": null,
            "text_tokens": 34
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "d17950dc8ef94f059dce5f78515d9b4f",
        "finish_reason": "stop",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a1351e-90df-7143-8d67-bb36787fdc41-0",
      "tool_calls": [],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 6863,
        "output_tokens": 35,
        "total_tokens": 6898,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 1
        }
      }
    }
  ],
  "files": {
    "/result.txt": {
      "content": [
        "计算过程：",
        "(2026 * 3 + 114) / 7",
        "= (6078 + 114) / 7",
        "= 6192 / 7",
        "= 884.5714285714286",
        "",
        "结果：884.5714285714286"
      ],
      "created_at": "2026-10-13T11:55:57.219592+00:00",
      "modified_at": "2026-10-13T11:55:57.219592+00:00"
    }
  },
  "todos": [
    {
      "content": "制定 todo 计划",
      "status": "completed"
    },
    {
      "content": "计算 (2026 * 3 + 114) / 7",
      "status": "completed"
    },
    {
      "content": "将计算过程和结果写入 result.txt",
      "status": "completed"
    }
  ]
}
````

### 逐条消息全量导出

#### [1] HumanMessage ｜ 用户输入


可读全文（pretty_repr）：

````text
================================ Human Message =================================

先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "human",
  "name": null,
  "id": "f74d225b-f9a0-496c-a33b-8d3084bbb0a6"
}
````

#### [2] AIMessage ｜ 模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答

- 工具调用指令：`write_todos`，参数 `{'todos': [{'content': '制定 todo 计划', 'status': 'in_progress'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'pending'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}]}`，id `call_6e4cd01346ac4848b44af2f2`
- 工具调用指令：`calculate`，参数 `{'expression': '(2026 * 3 + 114) / 7'}`，id `call_9a4b62c8e24e42019affc10e`
- token 用量：`{'input_tokens': 6133, 'output_tokens': 523, 'total_tokens': 6656, 'input_token_details': {}, 'output_token_details': {'reasoning': 375}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  write_todos (call_6e4cd01346ac4848b44af2f2)
 Call ID: call_6e4cd01346ac4848b44af2f2
  Args:
    todos: [{'content': '制定 todo 计划', 'status': 'in_progress'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'pending'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}]
  calculate (call_9a4b62c8e24e42019affc10e)
 Call ID: call_9a4b62c8e24e42019affc10e
  Args:
    expression: (2026 * 3 + 114) / 7
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 523,
      "prompt_tokens": 6133,
      "total_tokens": 6656,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 375,
        "rejected_prediction_tokens": null,
        "text_tokens": 148
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "9e42c4008466401da6ec8bcc8a3f3414",
    "finish_reason": "tool_calls",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-81cc-7270-8f08-802147c6426e-0",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {
        "todos": [
          {
            "content": "制定 todo 计划",
            "status": "in_progress"
          },
          {
            "content": "计算 (2026 * 3 + 114) / 7",
            "status": "pending"
          },
          {
            "content": "将计算过程和结果写入 result.txt",
            "status": "pending"
          }
        ]
      },
      "id": "call_6e4cd01346ac4848b44af2f2",
      "type": "tool_call"
    },
    {
      "name": "calculate",
      "args": {
        "expression": "(2026 * 3 + 114) / 7"
      },
      "id": "call_9a4b62c8e24e42019affc10e",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6133,
    "output_tokens": 523,
    "total_tokens": 6656,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 375
    }
  }
}
````

#### [3] ToolMessage ｜ 工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）

- 执行工具：`write_todos`，tool_call_id `call_6e4cd01346ac4848b44af2f2`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_todos

Updated todo list to [{'content': '制定 todo 计划', 'status': 'in_progress'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'pending'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated todo list to [{'content': '制定 todo 计划', 'status': 'in_progress'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'pending'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "595388e8-1824-4b17-ac2a-a41cea2444e0",
  "tool_call_id": "call_6e4cd01346ac4848b44af2f2",
  "artifact": null,
  "status": "success"
}
````

#### [4] ToolMessage ｜ 工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）

- 执行工具：`calculate`，tool_call_id `call_9a4b62c8e24e42019affc10e`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: calculate

884.5714285714286
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "884.5714285714286",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "calculate",
  "id": "a6fc62e3-9d23-4cf0-b74b-67dfddb6de9a",
  "tool_call_id": "call_9a4b62c8e24e42019affc10e",
  "artifact": null,
  "status": "success"
}
````

#### [5] AIMessage ｜ 模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答

- 工具调用指令：`write_todos`，参数 `{'todos': [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}]}`，id `call_7b01b5c6c8f14a498ff610a0`
- 工具调用指令：`write_file`，参数 `{'file_path': '/result.txt', 'content': '计算过程：\n(2026 * 3 + 114) / 7\n= (6078 + 114) / 7\n= 6192 / 7\n= 884.5714285714286\n\n结果：884.5714285714286'}`，id `call_e744b4848a894b548252e7ba`
- token 用量：`{'input_tokens': 6376, 'output_tokens': 232, 'total_tokens': 6608, 'input_token_details': {}, 'output_token_details': {'reasoning': 20}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  write_todos (call_7b01b5c6c8f14a498ff610a0)
 Call ID: call_7b01b5c6c8f14a498ff610a0
  Args:
    todos: [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}]
  write_file (call_e744b4848a894b548252e7ba)
 Call ID: call_e744b4848a894b548252e7ba
  Args:
    file_path: /result.txt
    content: 计算过程：
(2026 * 3 + 114) / 7
= (6078 + 114) / 7
= 6192 / 7
= 884.5714285714286

结果：884.5714285714286
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 232,
      "prompt_tokens": 6376,
      "total_tokens": 6608,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 20,
        "rejected_prediction_tokens": null,
        "text_tokens": 212
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "383e89243298468c9cada15831eb71bf",
    "finish_reason": "tool_calls",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-8abf-76d3-bcfa-3938391fc958-0",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {
        "todos": [
          {
            "content": "制定 todo 计划",
            "status": "completed"
          },
          {
            "content": "计算 (2026 * 3 + 114) / 7",
            "status": "completed"
          },
          {
            "content": "将计算过程和结果写入 result.txt",
            "status": "in_progress"
          }
        ]
      },
      "id": "call_7b01b5c6c8f14a498ff610a0",
      "type": "tool_call"
    },
    {
      "name": "write_file",
      "args": {
        "file_path": "/result.txt",
        "content": "计算过程：\n(2026 * 3 + 114) / 7\n= (6078 + 114) / 7\n= 6192 / 7\n= 884.5714285714286\n\n结果：884.5714285714286"
      },
      "id": "call_e744b4848a894b548252e7ba",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6376,
    "output_tokens": 232,
    "total_tokens": 6608,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 20
    }
  }
}
````

#### [6] ToolMessage ｜ 工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）

- 执行工具：`write_todos`，tool_call_id `call_7b01b5c6c8f14a498ff610a0`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_todos

Updated todo list to [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated todo list to [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "eb2ccc60-f6c9-4a6e-bbae-41e07ad7f36c",
  "tool_call_id": "call_7b01b5c6c8f14a498ff610a0",
  "artifact": null,
  "status": "success"
}
````

#### [7] ToolMessage ｜ 工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）

- 执行工具：`write_file`，tool_call_id `call_e744b4848a894b548252e7ba`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_file

Updated file /result.txt
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated file /result.txt",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_file",
  "id": "83707fc7-eb3c-4390-9b86-4d2821637063",
  "tool_call_id": "call_e744b4848a894b548252e7ba",
  "artifact": null,
  "status": "success"
}
````

#### [8] AIMessage ｜ 模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答

- 工具调用指令：`write_todos`，参数 `{'todos': [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}]}`，id `call_76a2766ad7034bfabb15cf8c`
- token 用量：`{'input_tokens': 6680, 'output_tokens': 106, 'total_tokens': 6786, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  write_todos (call_76a2766ad7034bfabb15cf8c)
 Call ID: call_76a2766ad7034bfabb15cf8c
  Args:
    todos: [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 106,
      "prompt_tokens": 6680,
      "total_tokens": 6786,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1,
        "rejected_prediction_tokens": null,
        "text_tokens": 105
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "1272d09156b3423395690d28de37867a",
    "finish_reason": "tool_calls",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-8e27-7c73-820a-41ab52322eb8-0",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {
        "todos": [
          {
            "content": "制定 todo 计划",
            "status": "completed"
          },
          {
            "content": "计算 (2026 * 3 + 114) / 7",
            "status": "completed"
          },
          {
            "content": "将计算过程和结果写入 result.txt",
            "status": "completed"
          }
        ]
      },
      "id": "call_76a2766ad7034bfabb15cf8c",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6680,
    "output_tokens": 106,
    "total_tokens": 6786,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 1
    }
  }
}
````

#### [9] ToolMessage ｜ 工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）

- 执行工具：`write_todos`，tool_call_id `call_76a2766ad7034bfabb15cf8c`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_todos

Updated todo list to [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated todo list to [{'content': '制定 todo 计划', 'status': 'completed'}, {'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "cd175240-fb0e-43f2-ae6c-ec5beff3c765",
  "tool_call_id": "call_76a2766ad7034bfabb15cf8c",
  "artifact": null,
  "status": "success"
}
````

#### [10] AIMessage ｜ 模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答

- token 用量：`{'input_tokens': 6863, 'output_tokens': 35, 'total_tokens': 6898, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================

(2026 * 3 + 114) / 7 = 6192 / 7 ≈ 884.571，计算过程已写入 result.txt。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "(2026 * 3 + 114) / 7 = 6192 / 7 ≈ 884.571，计算过程已写入 result.txt。",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 35,
      "prompt_tokens": 6863,
      "total_tokens": 6898,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1,
        "rejected_prediction_tokens": null,
        "text_tokens": 34
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "d17950dc8ef94f059dce5f78515d9b4f",
    "finish_reason": "stop",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-90df-7143-8d67-bb36787fdc41-0",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6863,
    "output_tokens": 35,
    "total_tokens": 6898,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 1
    }
  }
}
````

### 最终回答（最后一条 AI 消息的 content）

````text
(2026 * 3 + 114) / 7 = 6192 / 7 ≈ 884.571，计算过程已写入 result.txt。
````

## 【2】stream_mode="updates"：agent 循环每一步的增量

deep agent 的循环形态与 create_agent 一致：`model` 节点（LLM 决策）与 `tools` 节点（执行工具）交替，直到模型不再调工具。区别在于 model 可以调**内置工具**：write_todos 更新计划、write_file 写虚拟文件——它们都会以增量形式出现在 update 里。

### 第 1 步 ｜ 节点：`PatchToolCallsMiddleware.before_agent`

- 增量键：`['messages']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `messages`（被 `langgraph.types.Overwrite` 包装：语义是「该键整体覆盖而非追加」，真实内容在其 value 中），共 1 条：
  - 产出 `HumanMessage`（用户输入）：

可读全文（pretty_repr）：

````text
================================ Human Message =================================

先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "human",
  "name": null,
  "id": "ab427ef1-071e-4bb8-8c30-514346779c69"
}
````

### 第 2 步 ｜ 节点：`model`

- 增量键：`['messages']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `messages`，共 1 条：
  - 产出 `AIMessage`（工具调用指令：`write_todos`、`calculate`）：
- 工具调用指令：`write_todos`，参数 `{'todos': [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'in_progress'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}, {'content': '一句话告知答案', 'status': 'pending'}]}`，id `call_9614a623bd0343d0b4c02f5f`
- 工具调用指令：`calculate`，参数 `{'expression': '(2026 * 3 + 114) / 7'}`，id `call_f9cd0c65e7d0493d9b16edae`
- token 用量：`{'input_tokens': 6133, 'output_tokens': 289, 'total_tokens': 6422, 'input_token_details': {}, 'output_token_details': {'reasoning': 142}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  write_todos (call_9614a623bd0343d0b4c02f5f)
 Call ID: call_9614a623bd0343d0b4c02f5f
  Args:
    todos: [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'in_progress'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}, {'content': '一句话告知答案', 'status': 'pending'}]
  calculate (call_f9cd0c65e7d0493d9b16edae)
 Call ID: call_f9cd0c65e7d0493d9b16edae
  Args:
    expression: (2026 * 3 + 114) / 7
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "tool_calls",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {
        "todos": [
          {
            "content": "计算 (2026 * 3 + 114) / 7",
            "status": "in_progress"
          },
          {
            "content": "将计算过程和结果写入 result.txt",
            "status": "pending"
          },
          {
            "content": "一句话告知答案",
            "status": "pending"
          }
        ]
      },
      "id": "call_9614a623bd0343d0b4c02f5f",
      "type": "tool_call"
    },
    {
      "name": "calculate",
      "args": {
        "expression": "(2026 * 3 + 114) / 7"
      },
      "id": "call_f9cd0c65e7d0493d9b16edae",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6133,
    "output_tokens": 289,
    "total_tokens": 6422,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 142
    }
  }
}
````

### 第 3 步 ｜ 节点：`TodoListMiddleware.after_model`

- 增量为 `None`（中间件钩子本步无状态更新，但流里仍以 {节点名: None} 上报一步）

### 第 4 步 ｜ 节点：`tools`

- 增量键：`['todos', 'messages', 'files']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `todos`：
  - todos 共 3 项：
    - [in_progress] 计算 (2026 * 3 + 114) / 7
    - [pending] 将计算过程和结果写入 result.txt
    - [pending] 一句话告知答案
- 键 `messages`，共 1 条：
  - 产出 `ToolMessage`（工具结果：`write_todos`）：
- 执行工具：`write_todos`，tool_call_id `call_9614a623bd0343d0b4c02f5f`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_todos

Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'in_progress'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}, {'content': '一句话告知答案', 'status': 'pending'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'in_progress'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}, {'content': '一句话告知答案', 'status': 'pending'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "e95dd6d7-2acb-450b-b52f-8058e06d5fa4",
  "tool_call_id": "call_9614a623bd0343d0b4c02f5f",
  "artifact": null,
  "status": "success"
}
````
- 键 `files`：
  - files：空（本次未写文件）

### 第 5 步 ｜ 节点：`tools`

- 增量键：`['messages']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `messages`，共 1 条：
  - 产出 `ToolMessage`（工具结果：`calculate`）：
- 执行工具：`calculate`，tool_call_id `call_f9cd0c65e7d0493d9b16edae`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: calculate

884.5714285714286
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "884.5714285714286",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "calculate",
  "id": "fee384b1-895a-4bc8-a803-74d1480a788b",
  "tool_call_id": "call_f9cd0c65e7d0493d9b16edae",
  "artifact": null,
  "status": "success"
}
````

### 第 6 步 ｜ 节点：`model`

- 增量键：`['messages']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `messages`，共 1 条：
  - 产出 `AIMessage`（工具调用指令：`write_todos`、`write_file`）：
- 工具调用指令：`write_todos`，参数 `{'todos': [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}, {'content': '一句话告知答案', 'status': 'pending'}]}`，id `call_6b6b5f3f2f884b8b9fd5ab84`
- 工具调用指令：`write_file`，参数 `{'file_path': '/result.txt', 'content': '计算过程：\n2026 * 3 = 6078\n6078 + 114 = 6192\n6192 / 7 = 884.5714285714286\n\n结果：(2026 * 3 + 114) / 7 = 884.5714285714286'}`，id `call_9e512914662340a0a1119406`
- token 用量：`{'input_tokens': 6374, 'output_tokens': 239, 'total_tokens': 6613, 'input_token_details': {}, 'output_token_details': {'reasoning': 23}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  write_todos (call_6b6b5f3f2f884b8b9fd5ab84)
 Call ID: call_6b6b5f3f2f884b8b9fd5ab84
  Args:
    todos: [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}, {'content': '一句话告知答案', 'status': 'pending'}]
  write_file (call_9e512914662340a0a1119406)
 Call ID: call_9e512914662340a0a1119406
  Args:
    file_path: /result.txt
    content: 计算过程：
2026 * 3 = 6078
6078 + 114 = 6192
6192 / 7 = 884.5714285714286

结果：(2026 * 3 + 114) / 7 = 884.5714285714286
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "tool_calls",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {
        "todos": [
          {
            "content": "计算 (2026 * 3 + 114) / 7",
            "status": "completed"
          },
          {
            "content": "将计算过程和结果写入 result.txt",
            "status": "in_progress"
          },
          {
            "content": "一句话告知答案",
            "status": "pending"
          }
        ]
      },
      "id": "call_6b6b5f3f2f884b8b9fd5ab84",
      "type": "tool_call"
    },
    {
      "name": "write_file",
      "args": {
        "file_path": "/result.txt",
        "content": "计算过程：\n2026 * 3 = 6078\n6078 + 114 = 6192\n6192 / 7 = 884.5714285714286\n\n结果：(2026 * 3 + 114) / 7 = 884.5714285714286"
      },
      "id": "call_9e512914662340a0a1119406",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6374,
    "output_tokens": 239,
    "total_tokens": 6613,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 23
    }
  }
}
````

### 第 7 步 ｜ 节点：`TodoListMiddleware.after_model`

- 增量为 `None`（中间件钩子本步无状态更新，但流里仍以 {节点名: None} 上报一步）

### 第 8 步 ｜ 节点：`tools`

- 增量键：`['todos', 'messages', 'files']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `todos`：
  - todos 共 3 项：
    - [completed] 计算 (2026 * 3 + 114) / 7
    - [in_progress] 将计算过程和结果写入 result.txt
    - [pending] 一句话告知答案
- 键 `messages`，共 1 条：
  - 产出 `ToolMessage`（工具结果：`write_todos`）：
- 执行工具：`write_todos`，tool_call_id `call_6b6b5f3f2f884b8b9fd5ab84`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_todos

Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}, {'content': '一句话告知答案', 'status': 'pending'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}, {'content': '一句话告知答案', 'status': 'pending'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "166cf204-b704-409d-be7e-4d13fb28c55c",
  "tool_call_id": "call_6b6b5f3f2f884b8b9fd5ab84",
  "artifact": null,
  "status": "success"
}
````
- 键 `files`：
  - files：空（本次未写文件）

### 第 9 步 ｜ 节点：`tools`

- 增量键：`['files', 'messages']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `files`：
  - files 共 1 个文件（存在 state 里，不落真实磁盘）：
    - `/result.txt`（类型 `builtins.dict`）：
````json
{
  "content": [
    "计算过程：",
    "2026 * 3 = 6078",
    "6078 + 114 = 6192",
    "6192 / 7 = 884.5714285714286",
    "",
    "结果：(2026 * 3 + 114) / 7 = 884.5714285714286"
  ],
  "created_at": "2026-10-13T11:56:00.554525+00:00",
  "modified_at": "2026-10-13T11:56:00.554525+00:00"
}
````
- 键 `messages`，共 1 条：
  - 产出 `ToolMessage`（工具结果：`write_file`）：
- 执行工具：`write_file`，tool_call_id `call_9e512914662340a0a1119406`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_file

Updated file /result.txt
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated file /result.txt",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_file",
  "id": "f919e82e-2bdc-41b2-8f6f-4fd1aed33cc9",
  "tool_call_id": "call_9e512914662340a0a1119406",
  "artifact": null,
  "status": "success"
}
````

### 第 10 步 ｜ 节点：`model`

- 增量键：`['messages']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `messages`，共 1 条：
  - 产出 `AIMessage`（工具调用指令：`write_todos`）：
- 工具调用指令：`write_todos`，参数 `{'todos': [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}, {'content': '一句话告知答案', 'status': 'completed'}]}`，id `call_2db32ba713db4237bf5e4d0c`
- token 用量：`{'input_tokens': 6681, 'output_tokens': 105, 'total_tokens': 6786, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  write_todos (call_2db32ba713db4237bf5e4d0c)
 Call ID: call_2db32ba713db4237bf5e4d0c
  Args:
    todos: [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}, {'content': '一句话告知答案', 'status': 'completed'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "tool_calls",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {
        "todos": [
          {
            "content": "计算 (2026 * 3 + 114) / 7",
            "status": "completed"
          },
          {
            "content": "将计算过程和结果写入 result.txt",
            "status": "completed"
          },
          {
            "content": "一句话告知答案",
            "status": "completed"
          }
        ]
      },
      "id": "call_2db32ba713db4237bf5e4d0c",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6681,
    "output_tokens": 105,
    "total_tokens": 6786,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 1
    }
  }
}
````

### 第 11 步 ｜ 节点：`TodoListMiddleware.after_model`

- 增量为 `None`（中间件钩子本步无状态更新，但流里仍以 {节点名: None} 上报一步）

### 第 12 步 ｜ 节点：`tools`

- 增量键：`['todos', 'messages', 'files']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `todos`：
  - todos 共 3 项：
    - [completed] 计算 (2026 * 3 + 114) / 7
    - [completed] 将计算过程和结果写入 result.txt
    - [completed] 一句话告知答案
- 键 `messages`，共 1 条：
  - 产出 `ToolMessage`（工具结果：`write_todos`）：
- 执行工具：`write_todos`，tool_call_id `call_2db32ba713db4237bf5e4d0c`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: write_todos

Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}, {'content': '一句话告知答案', 'status': 'completed'}]
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}, {'content': '一句话告知答案', 'status': 'completed'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "06c9e547-6598-40fc-9e45-1668fa044054",
  "tool_call_id": "call_2db32ba713db4237bf5e4d0c",
  "artifact": null,
  "status": "success"
}
````
- 键 `files`：
  - files：空（本次未写文件）

### 第 13 步 ｜ 节点：`model`

- 增量键：`['messages']`（只含该节点 return 的字段；节点名带 Middleware 后缀的是 deep agent 中间件的钩子节点，create_agent 没有）
- 键 `messages`，共 1 条：
  - 产出 `AIMessage`（最终回答（无工具调用））：
- token 用量：`{'input_tokens': 6862, 'output_tokens': 37, 'total_tokens': 6899, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================

计算过程和结果已写入 `/result.txt`，答案是 **(2026 × 3 + 114) ÷ 7 = 884.5714285714286**。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "计算过程和结果已写入 `/result.txt`，答案是 **(2026 × 3 + 114) ÷ 7 = 884.5714285714286**。",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "stop",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6862,
    "output_tokens": 37,
    "total_tokens": 6899,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 1
    }
  }
}
````

### 第 14 步 ｜ 节点：`TodoListMiddleware.after_model`

- 增量为 `None`（中间件钩子本步无状态更新，但流里仍以 {节点名: None} 上报一步）

### 完整步骤序列（原样一体化导出，一个字段不省略）

本视图本次共上报 14 个步骤对象，完整 JSON 已写入本文件。

````json
[
  {
    "PatchToolCallsMiddleware.before_agent": {
      "messages": "Overwrite(value=[HumanMessage(content='先制定一个简短的 todo 计划，然后计算 (2026 * 3 + 114) / 7，把计算过程和结果写入文件 result.txt，最后用一句话告诉我答案。', additional_kwargs={}, response_metadata={}, id='ab427ef1-071e-4bb8-8c30-514346779c69')])"
    }
  },
  {
    "model": {
      "messages": [
        {
          "content": "",
          "additional_kwargs": {},
          "response_metadata": {
            "finish_reason": "tool_calls",
            "model_name": "deepseek-v4-flash-sz",
            "model_provider": "openai"
          },
          "type": "ai",
          "name": null,
          "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
          "tool_calls": [
            {
              "name": "write_todos",
              "args": {
                "todos": [
                  {
                    "content": "计算 (2026 * 3 + 114) / 7",
                    "status": "in_progress"
                  },
                  {
                    "content": "将计算过程和结果写入 result.txt",
                    "status": "pending"
                  },
                  {
                    "content": "一句话告知答案",
                    "status": "pending"
                  }
                ]
              },
              "id": "call_9614a623bd0343d0b4c02f5f",
              "type": "tool_call"
            },
            {
              "name": "calculate",
              "args": {
                "expression": "(2026 * 3 + 114) / 7"
              },
              "id": "call_f9cd0c65e7d0493d9b16edae",
              "type": "tool_call"
            }
          ],
          "invalid_tool_calls": [],
          "usage_metadata": {
            "input_tokens": 6133,
            "output_tokens": 289,
            "total_tokens": 6422,
            "input_token_details": {},
            "output_token_details": {
              "reasoning": 142
            }
          }
        }
      ]
    }
  },
  {
    "TodoListMiddleware.after_model": null
  },
  {
    "tools": {
      "todos": [
        {
          "content": "计算 (2026 * 3 + 114) / 7",
          "status": "in_progress"
        },
        {
          "content": "将计算过程和结果写入 result.txt",
          "status": "pending"
        },
        {
          "content": "一句话告知答案",
          "status": "pending"
        }
      ],
      "messages": [
        {
          "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'in_progress'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}, {'content': '一句话告知答案', 'status': 'pending'}]",
          "additional_kwargs": {},
          "response_metadata": {},
          "type": "tool",
          "name": "write_todos",
          "id": "e95dd6d7-2acb-450b-b52f-8058e06d5fa4",
          "tool_call_id": "call_9614a623bd0343d0b4c02f5f",
          "artifact": null,
          "status": "success"
        }
      ],
      "files": {}
    }
  },
  {
    "tools": {
      "messages": [
        {
          "content": "884.5714285714286",
          "additional_kwargs": {},
          "response_metadata": {},
          "type": "tool",
          "name": "calculate",
          "id": "fee384b1-895a-4bc8-a803-74d1480a788b",
          "tool_call_id": "call_f9cd0c65e7d0493d9b16edae",
          "artifact": null,
          "status": "success"
        }
      ]
    }
  },
  {
    "model": {
      "messages": [
        {
          "content": "",
          "additional_kwargs": {},
          "response_metadata": {
            "finish_reason": "tool_calls",
            "model_name": "deepseek-v4-flash-sz",
            "model_provider": "openai"
          },
          "type": "ai",
          "name": null,
          "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
          "tool_calls": [
            {
              "name": "write_todos",
              "args": {
                "todos": [
                  {
                    "content": "计算 (2026 * 3 + 114) / 7",
                    "status": "completed"
                  },
                  {
                    "content": "将计算过程和结果写入 result.txt",
                    "status": "in_progress"
                  },
                  {
                    "content": "一句话告知答案",
                    "status": "pending"
                  }
                ]
              },
              "id": "call_6b6b5f3f2f884b8b9fd5ab84",
              "type": "tool_call"
            },
            {
              "name": "write_file",
              "args": {
                "file_path": "/result.txt",
                "content": "计算过程：\n2026 * 3 = 6078\n6078 + 114 = 6192\n6192 / 7 = 884.5714285714286\n\n结果：(2026 * 3 + 114) / 7 = 884.5714285714286"
              },
              "id": "call_9e512914662340a0a1119406",
              "type": "tool_call"
            }
          ],
          "invalid_tool_calls": [],
          "usage_metadata": {
            "input_tokens": 6374,
            "output_tokens": 239,
            "total_tokens": 6613,
            "input_token_details": {},
            "output_token_details": {
              "reasoning": 23
            }
          }
        }
      ]
    }
  },
  {
    "TodoListMiddleware.after_model": null
  },
  {
    "tools": {
      "todos": [
        {
          "content": "计算 (2026 * 3 + 114) / 7",
          "status": "completed"
        },
        {
          "content": "将计算过程和结果写入 result.txt",
          "status": "in_progress"
        },
        {
          "content": "一句话告知答案",
          "status": "pending"
        }
      ],
      "messages": [
        {
          "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}, {'content': '一句话告知答案', 'status': 'pending'}]",
          "additional_kwargs": {},
          "response_metadata": {},
          "type": "tool",
          "name": "write_todos",
          "id": "166cf204-b704-409d-be7e-4d13fb28c55c",
          "tool_call_id": "call_6b6b5f3f2f884b8b9fd5ab84",
          "artifact": null,
          "status": "success"
        }
      ],
      "files": {}
    }
  },
  {
    "tools": {
      "files": {
        "/result.txt": {
          "content": [
            "计算过程：",
            "2026 * 3 = 6078",
            "6078 + 114 = 6192",
            "6192 / 7 = 884.5714285714286",
            "",
            "结果：(2026 * 3 + 114) / 7 = 884.5714285714286"
          ],
          "created_at": "2026-10-13T11:56:00.554525+00:00",
          "modified_at": "2026-10-13T11:56:00.554525+00:00"
        }
      },
      "messages": [
        {
          "content": "Updated file /result.txt",
          "additional_kwargs": {},
          "response_metadata": {},
          "type": "tool",
          "name": "write_file",
          "id": "f919e82e-2bdc-41b2-8f6f-4fd1aed33cc9",
          "tool_call_id": "call_9e512914662340a0a1119406",
          "artifact": null,
          "status": "success"
        }
      ]
    }
  },
  {
    "model": {
      "messages": [
        {
          "content": "",
          "additional_kwargs": {},
          "response_metadata": {
            "finish_reason": "tool_calls",
            "model_name": "deepseek-v4-flash-sz",
            "model_provider": "openai"
          },
          "type": "ai",
          "name": null,
          "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
          "tool_calls": [
            {
              "name": "write_todos",
              "args": {
                "todos": [
                  {
                    "content": "计算 (2026 * 3 + 114) / 7",
                    "status": "completed"
                  },
                  {
                    "content": "将计算过程和结果写入 result.txt",
                    "status": "completed"
                  },
                  {
                    "content": "一句话告知答案",
                    "status": "completed"
                  }
                ]
              },
              "id": "call_2db32ba713db4237bf5e4d0c",
              "type": "tool_call"
            }
          ],
          "invalid_tool_calls": [],
          "usage_metadata": {
            "input_tokens": 6681,
            "output_tokens": 105,
            "total_tokens": 6786,
            "input_token_details": {},
            "output_token_details": {
              "reasoning": 1
            }
          }
        }
      ]
    }
  },
  {
    "TodoListMiddleware.after_model": null
  },
  {
    "tools": {
      "todos": [
        {
          "content": "计算 (2026 * 3 + 114) / 7",
          "status": "completed"
        },
        {
          "content": "将计算过程和结果写入 result.txt",
          "status": "completed"
        },
        {
          "content": "一句话告知答案",
          "status": "completed"
        }
      ],
      "messages": [
        {
          "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}, {'content': '一句话告知答案', 'status': 'completed'}]",
          "additional_kwargs": {},
          "response_metadata": {},
          "type": "tool",
          "name": "write_todos",
          "id": "06c9e547-6598-40fc-9e45-1668fa044054",
          "tool_call_id": "call_2db32ba713db4237bf5e4d0c",
          "artifact": null,
          "status": "success"
        }
      ],
      "files": {}
    }
  },
  {
    "model": {
      "messages": [
        {
          "content": "计算过程和结果已写入 `/result.txt`，答案是 **(2026 × 3 + 114) ÷ 7 = 884.5714285714286**。",
          "additional_kwargs": {},
          "response_metadata": {
            "finish_reason": "stop",
            "model_name": "deepseek-v4-flash-sz",
            "model_provider": "openai"
          },
          "type": "ai",
          "name": null,
          "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
          "tool_calls": [],
          "invalid_tool_calls": [],
          "usage_metadata": {
            "input_tokens": 6862,
            "output_tokens": 37,
            "total_tokens": 6899,
            "input_token_details": {},
            "output_token_details": {
              "reasoning": 1
            }
          }
        }
      ]
    }
  },
  {
    "TodoListMiddleware.after_model": null
  }
]
````

## 【3】stream_mode="messages"：token 级分片（与【2】同一轮执行）

### 总览

- 事件总数：**132**，类型分布：`{'AIMessageChunk': 127, 'ToolMessage': 5}`
- 事件来源节点：`['model', 'tools']`
- 解读：结构与 create_agent 完全同构——LLM 决策是逐 token 的 `AIMessageChunk` 分片，工具结果是完整 `ToolMessage`；每个事件都是 `(消息对象, metadata)` 二元组。

### 先解剖一次 yield：`(message, metadata)` 的完整实例

````text
('messages', (AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[]), {'ls_integration': 'deepagents', 'langgraph_step': 2, 'langgraph_node': 'model', 'langgraph_triggers': ('branch:to:model',), 'langgraph_path': ('__pregel_pull', 'model'), 'langgraph_checkpoint_ns': 'model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a', 'checkpoint_ns': 'model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a', 'ls_provider': 'openai', 'ls_model_name': 'deepseek-v4-flash-sz', 'ls_model_type': 'chat', 'ls_temperature': None}))
````

第 1 项 message 是 `langchain_core.messages.ai.AIMessageChunk`，第 2 项 metadata 是 `dict`，键：`['ls_integration', 'langgraph_step', 'langgraph_node', 'langgraph_triggers', 'langgraph_path', 'langgraph_checkpoint_ns', 'checkpoint_ns', 'ls_provider', 'ls_model_name', 'ls_model_type', 'ls_temperature']`。

### 逐事件全量导出（按流的原始结构，一个字段不省略）

按 yield 的原始顺序，把全部 132 个事件原样端出。每个事件的第 1 项是消息对象（真实类型全路径 + 原始 repr + 全字段 model_dump），第 2 项是 metadata（真实流中每个事件都重复携带一份，不提取到组外）。

#### 事件 1/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 2/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 3/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 4/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 5/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 6/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 7/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 8/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 9/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 10/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 11/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 12/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 13/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 14/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 15/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 16/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 17/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 18/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 19/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 20/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 21/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 22/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 23/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 24/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 25/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 26/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 27/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 28/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 29/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 30/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 31/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 32/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 33/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[{'name': 'write_todos', 'args': {}, 'id': 'call_9614a623bd0343d0b4c02f5f', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'write_todos', 'args': '', 'id': 'call_9614a623bd0343d0b4c02f5f', 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {},
      "id": "call_9614a623bd0343d0b4c02f5f",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "write_todos",
      "args": "",
      "id": "call_9614a623bd0343d0b4c02f5f",
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 34/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [
    {
      "name": "",
      "args": {},
      "id": null,
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "{",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 35/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"todos": [', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"todos": [', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"todos\": [",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"todos\": [",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 36/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[{'name': '', 'args': {'content': '计算'}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{"content": "计算', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [
    {
      "name": "",
      "args": {
        "content": "计算"
      },
      "id": null,
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "{\"content\": \"计算",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 37/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' (2026 * 3', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' (2026 * 3', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " (2026 * 3",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " (2026 * 3",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 38/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' + 114) /', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' + 114) /', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " + 114) /",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " + 114) /",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 39/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 7", "status": "', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 7", "status": "', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 7\", \"status\": \"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 7\", \"status\": \"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 40/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': 'in_progress"}, {', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': 'in_progress"}, {', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "in_progress\"}, {",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "in_progress\"}, {",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 41/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"content": "将计算过程和结果', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"content": "将计算过程和结果', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"content\": \"将计算过程和结果",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"content\": \"将计算过程和结果",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 42/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '写入 result.txt"', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '写入 result.txt"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "写入 result.txt\"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "写入 result.txt\"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 43/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', "status": "pending"}, {', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', "status": "pending"}, {', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", \"status\": \"pending\"}, {",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", \"status\": \"pending\"}, {",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 44/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"content": "一句话', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"content": "一句话', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"content\": \"一句话",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"content\": \"一句话",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 45/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '告知答案"', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '告知答案"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "告知答案\"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "告知答案\"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 46/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', "status": "pending"}]}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', "status": "pending"}]}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", \"status\": \"pending\"}]}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", \"status\": \"pending\"}]}",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 47/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[{'name': 'calculate', 'args': {}, 'id': 'call_f9cd0c65e7d0493d9b16edae', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'calculate', 'args': '', 'id': 'call_f9cd0c65e7d0493d9b16edae', 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [
    {
      "name": "calculate",
      "args": {},
      "id": "call_f9cd0c65e7d0493d9b16edae",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "calculate",
      "args": "",
      "id": "call_f9cd0c65e7d0493d9b16edae",
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 48/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [
    {
      "name": "",
      "args": {},
      "id": null,
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "{",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 49/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"expression": "(2026 * 3', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"expression": "(2026 * 3', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"expression\": \"(2026 * 3",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"expression\": \"(2026 * 3",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 50/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' + 114) /', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' + 114) /', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " + 114) /",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " + 114) /",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 51/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 7"}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 7"}', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 7\"}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 7\"}",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 52/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "tool_calls",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 53/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 6133, 'output_tokens': 289, 'total_tokens': 6422, 'input_token_details': {}, 'output_token_details': {'reasoning': 142}}, tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6133,
    "output_tokens": 289,
    "total_tokens": 6422,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 142
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 54/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9338-7c60-aed3-5dd29d4221ce",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": "last"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 2,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "checkpoint_ns": "model:1a0e5bd8-b678-dc90-30cc-ecedf6293b0a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 55/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content="Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'in_progress'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}, {'content': '一句话告知答案', 'status': 'pending'}]", name='write_todos', id='e95dd6d7-2acb-450b-b52f-8058e06d5fa4', tool_call_id='call_9614a623bd0343d0b4c02f5f')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'in_progress'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'pending'}, {'content': '一句话告知答案', 'status': 'pending'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "e95dd6d7-2acb-450b-b52f-8058e06d5fa4",
  "tool_call_id": "call_9614a623bd0343d0b4c02f5f",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 4,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    0,
    false
  ],
  "langgraph_checkpoint_ns": "tools:e028bd4b-06d9-6bc7-2e0c-be33098e11f6"
}
````

#### 事件 56/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content='884.5714285714286', name='calculate', id='fee384b1-895a-4bc8-a803-74d1480a788b', tool_call_id='call_f9cd0c65e7d0493d9b16edae')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "884.5714285714286",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "calculate",
  "id": "fee384b1-895a-4bc8-a803-74d1480a788b",
  "tool_call_id": "call_f9cd0c65e7d0493d9b16edae",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 4,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    1,
    false
  ],
  "langgraph_checkpoint_ns": "tools:d233edaa-7ee4-f854-e03d-426c0ddd9fe9"
}
````

#### 事件 57/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 58/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 59/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 60/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 61/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 62/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 63/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 64/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 65/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 66/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[{'name': 'write_todos', 'args': {}, 'id': 'call_6b6b5f3f2f884b8b9fd5ab84', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'write_todos', 'args': '', 'id': 'call_6b6b5f3f2f884b8b9fd5ab84', 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {},
      "id": "call_6b6b5f3f2f884b8b9fd5ab84",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "write_todos",
      "args": "",
      "id": "call_6b6b5f3f2f884b8b9fd5ab84",
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 67/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [
    {
      "name": "",
      "args": {},
      "id": null,
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "{",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 68/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"todos": [{', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"todos": [{', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"todos\": [{",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"todos\": [{",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 69/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"content": "计算 (2026 *', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"content": "计算 (2026 *', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"content\": \"计算 (2026 *",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"content\": \"计算 (2026 *",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 70/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 3 + 114)', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 3 + 114)', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 3 + 114)",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 3 + 114)",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 71/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' / 7"', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' / 7"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " / 7\"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " / 7\"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 72/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', "status": "completed"}, {', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', "status": "completed"}, {', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", \"status\": \"completed\"}, {",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", \"status\": \"completed\"}, {",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 73/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"content": "将计算过程和结果', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"content": "将计算过程和结果', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"content\": \"将计算过程和结果",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"content\": \"将计算过程和结果",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 74/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '写入 result.txt"', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '写入 result.txt"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "写入 result.txt\"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "写入 result.txt\"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 75/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', "status": "in_progress"}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', "status": "in_progress"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", \"status\": \"in_progress\"}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", \"status\": \"in_progress\"}",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 76/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', {"content": "一句话', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', {"content": "一句话', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", {\"content\": \"一句话",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", {\"content\": \"一句话",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 77/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '告知答案"', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '告知答案"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "告知答案\"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "告知答案\"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 78/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', "status": "pending"}]}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', "status": "pending"}]}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", \"status\": \"pending\"}]}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", \"status\": \"pending\"}]}",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 79/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[{'name': 'write_file', 'args': {}, 'id': 'call_9e512914662340a0a1119406', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'write_file', 'args': '', 'id': 'call_9e512914662340a0a1119406', 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [
    {
      "name": "write_file",
      "args": {},
      "id": "call_9e512914662340a0a1119406",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "write_file",
      "args": "",
      "id": "call_9e512914662340a0a1119406",
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 80/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [
    {
      "name": "",
      "args": {},
      "id": null,
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "{",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 81/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"file_path": "/resul', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"file_path": "/resul', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"file_path\": \"/resul",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"file_path\": \"/resul",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 82/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': 't.txt"', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': 't.txt"', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "t.txt\"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "t.txt\"",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 83/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', "content": "计算过程', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', "content": "计算过程', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", \"content\": \"计算过程",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", \"content\": \"计算过程",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 84/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '：\\n202', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '：\\n202', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "：\\n202",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "：\\n202",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 85/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '6 * 3 =', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '6 * 3 =', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "6 * 3 =",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "6 * 3 =",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 86/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 6078\\n607', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 6078\\n607', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 6078\\n607",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 6078\\n607",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 87/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '8 + 114 =', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '8 + 114 =', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "8 + 114 =",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "8 + 114 =",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 88/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 6192\\n6192', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 6192\\n6192', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 6192\\n6192",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 6192\\n6192",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 89/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' / 7 = 884.', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' / 7 = 884.', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " / 7 = 884.",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " / 7 = 884.",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 90/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '5714285714286', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '5714285714286', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "5714285714286",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "5714285714286",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 91/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '\\n\\n结果：(', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '\\n\\n结果：(', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\\n\\n结果：(",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\\n\\n结果：(",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 92/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '2026 * 3 +', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '2026 * 3 +', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "2026 * 3 +",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "2026 * 3 +",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 93/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 114) / 7', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 114) / 7', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 114) / 7",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 114) / 7",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 94/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' = 884.571428', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' = 884.571428', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " = 884.571428",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " = 884.571428",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 95/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '5714286"}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '5714286"}', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "5714286\"}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "5714286\"}",
      "id": null,
      "index": 1,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 96/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "tool_calls",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 97/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 6374, 'output_tokens': 239, 'total_tokens': 6613, 'input_token_details': {}, 'output_token_details': {'reasoning': 23}}, tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6374,
    "output_tokens": 239,
    "total_tokens": 6613,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 23
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 98/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-975e-7ff1-b984-706ffc9c5cd6",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": "last"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 5,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "checkpoint_ns": "model:90f66a54-3647-5b48-d935-941cd4fe185a",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 99/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content="Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}, {'content': '一句话告知答案', 'status': 'pending'}]", name='write_todos', id='166cf204-b704-409d-be7e-4d13fb28c55c', tool_call_id='call_6b6b5f3f2f884b8b9fd5ab84')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'in_progress'}, {'content': '一句话告知答案', 'status': 'pending'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "166cf204-b704-409d-be7e-4d13fb28c55c",
  "tool_call_id": "call_6b6b5f3f2f884b8b9fd5ab84",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 7,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    0,
    false
  ],
  "langgraph_checkpoint_ns": "tools:0f2df3e5-f96b-ce63-4869-a5207e33d035"
}
````

#### 事件 100/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content='Updated file /result.txt', name='write_file', id='f919e82e-2bdc-41b2-8f6f-4fd1aed33cc9', tool_call_id='call_9e512914662340a0a1119406')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "Updated file /result.txt",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_file",
  "id": "f919e82e-2bdc-41b2-8f6f-4fd1aed33cc9",
  "tool_call_id": "call_9e512914662340a0a1119406",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 7,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    1,
    false
  ],
  "langgraph_checkpoint_ns": "tools:e4d7a4a3-2047-0d76-aaf0-0d9c44e966fe"
}
````

#### 事件 101/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 102/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[{'name': 'write_todos', 'args': {}, 'id': 'call_2db32ba713db4237bf5e4d0c', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'write_todos', 'args': '', 'id': 'call_2db32ba713db4237bf5e4d0c', 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [
    {
      "name": "write_todos",
      "args": {},
      "id": "call_2db32ba713db4237bf5e4d0c",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "write_todos",
      "args": "",
      "id": "call_2db32ba713db4237bf5e4d0c",
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 103/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [
    {
      "name": "",
      "args": {},
      "id": null,
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "{",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 104/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"todos": [', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"todos": [', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"todos\": [",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"todos\": [",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 105/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[{'name': '', 'args': {'content': '计算'}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{"content": "计算', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [
    {
      "name": "",
      "args": {
        "content": "计算"
      },
      "id": null,
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "{\"content\": \"计算",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 106/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' (2026 * 3', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' (2026 * 3', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " (2026 * 3",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " (2026 * 3",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 107/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' + 114) /', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' + 114) /', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " + 114) /",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " + 114) /",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 108/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 7", "status": "', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 7", "status": "', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 7\", \"status\": \"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 7\", \"status\": \"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 109/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': 'completed"}, {"content": "', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': 'completed"}, {"content": "', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "completed\"}, {\"content\": \"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "completed\"}, {\"content\": \"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 110/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '将计算过程和结果写入 resul', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '将计算过程和结果写入 resul', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "将计算过程和结果写入 resul",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "将计算过程和结果写入 resul",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 111/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': 't.txt", "status": "', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': 't.txt", "status": "', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "t.txt\", \"status\": \"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "t.txt\", \"status\": \"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 112/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': 'completed"}, {"content": "', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': 'completed"}, {"content": "', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "completed\"}, {\"content\": \"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "completed\"}, {\"content\": \"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 113/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '一句话告知答案"', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '一句话告知答案"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "一句话告知答案\"",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "一句话告知答案\"",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 114/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ', "status": "completed"}]}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ', "status": "completed"}]}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": ", \"status\": \"completed\"}]}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": ", \"status\": \"completed\"}]}",
      "id": null,
      "index": 0,
      "type": "tool_call_chunk"
    }
  ],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 115/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "tool_calls",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 116/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 6681, 'output_tokens': 105, 'total_tokens': 6786, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}, tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6681,
    "output_tokens": 105,
    "total_tokens": 6786,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 1
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 117/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9b47-7612-b352-4319a15fa9ee",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": "last"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 8,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "checkpoint_ns": "model:4b01dd6a-aca9-7df1-e9d6-e389c6f75701",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 118/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content="Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}, {'content': '一句话告知答案', 'status': 'completed'}]", name='write_todos', id='06c9e547-6598-40fc-9e45-1668fa044054', tool_call_id='call_2db32ba713db4237bf5e4d0c')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "Updated todo list to [{'content': '计算 (2026 * 3 + 114) / 7', 'status': 'completed'}, {'content': '将计算过程和结果写入 result.txt', 'status': 'completed'}, {'content': '一句话告知答案', 'status': 'completed'}]",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "write_todos",
  "id": "06c9e547-6598-40fc-9e45-1668fa044054",
  "tool_call_id": "call_2db32ba713db4237bf5e4d0c",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 10,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    0,
    false
  ],
  "langgraph_checkpoint_ns": "tools:76b33037-35ef-ff2a-523b-ca60c1a481b3"
}
````

#### 事件 119/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 120/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='计算', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "计算",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 121/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='过程和结果已', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "过程和结果已",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 122/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='写入 `/', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "写入 `/",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 123/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='result.txt`，答案是', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "result.txt`，答案是",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 124/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' **(202', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " **(202",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 125/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='6 ×', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "6 ×",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 126/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 3 + 114)', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " 3 + 114)",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 127/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' ÷ 7 = 884', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " ÷ 7 = 884",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 128/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='.571428571428', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": ".571428571428",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 129/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='6**。', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "6**。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 130/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'stop', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "stop",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 131/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 6862, 'output_tokens': 37, 'total_tokens': 6899, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}, tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 6862,
    "output_tokens": 37,
    "total_tokens": 6899,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 1
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 132/132

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a1351e-9e06-7380-880c-960461c88c23', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1351e-9e06-7380-880c-960461c88c23",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": "last"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "ls_integration": "deepagents",
  "langgraph_step": 11,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "checkpoint_ns": "model:85fb2b43-3547-5964-4fa7-3dfb520e9a03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````


## 【4】与 create_agent（simple_agent.py）输出差异速查

| 维度 | create_agent（simple_agent.py） | create_deep_agent（本次） |
| --- | --- | --- |
| 顶层 state 键 | `messages` | `messages` + **`todos`** + **`files`** |
| 可用工具 | 只有你传的 tools | 你的 tools + 内置 write_todos / ls / read_file / write_file / edit_file |
| 系统提示 | 只用你传的 system_prompt | 内置长提示（规划与文件使用指引）再拼接你的 system_prompt |
| 循环形态 | model <-> tools | 相同（model <-> tools） |
| 消息 / 分片结构 | `AIMessageChunk` / `ToolMessage` | 完全一致（同构 LangGraph） |
| 文件去哪了 | 概念不存在 | `state["files"]`（StateBackend，虚拟文件系统，不落盘） |

- 本次任务触发的内置工具以【2】的实测 tool_calls 为准（write_todos / write_file 等）。
- `todos`：list[dict]，每项含 `content`（做什么）与 `status`（pending / in_progress / completed）。
- `files`：dict[文件名, 文件内容字符串]，写入即可在后续轮次 read_file 读回，跨轮持久在 state 中。
- invoke 返回的仍不是消息而是最终状态：拿回答用 `result["messages"][-1]` 的最后一条 AI 消息。
