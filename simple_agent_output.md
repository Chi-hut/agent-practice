# LangChain Agent 输出全量解析

- 采集时间：2026-10-13 18:10:25
- 模型：`deepseek-v4-flash-sz`
- 问题：帮我算一下 (2026 * 3 + 114) / 7，另外现在几点了？
- 工具清单：`calculate`、`get_current_time`
- Agent 构建：`create_agent(model=llm, tools=[...], system_prompt=...)`（langchain 1.x，底层是 LangGraph 状态图）
- 调用方式：`agent.invoke(...)` ｜ `agent.stream(...)` ｜ `agent.astream(...)`（后两者均用 `stream_mode=["updates", "messages"]` 组合采集两路视图）

> Agent 执行机制：`model` 节点调 LLM；回复带 tool_calls 则转到 `tools` 节点执行工具，
> 结果以 ToolMessage 追加进消息列表后回到 `model` 节点；循环到模型不再调工具，
> 此时它的 content 即最终回答。下面把各视图的完整数据原样导出（含全部消息的全字段与全部分片）。

## 【1】agent.invoke：阻塞到全部结束，一次性返回

### 顶层结构

- 返回类型：`dict`（注意与 llm.invoke 的区别：那里返回的是一条 AIMessage）
- 顶层键：`['messages']`
- messages 共 5 条，序列：`HumanMessage` -> `AIMessage` -> `ToolMessage` -> `ToolMessage` -> `AIMessage`

### 完整返回值（原样一体化导出，一个字段不省略）

`agent.invoke()` 返回值的原样全量内容已直接写入本文件：外层是状态 dict，messages 里是本次执行的全部消息，每条消息的 id / content / tool_calls / tool_call_id / usage_metadata / response_metadata 等全字段在内。

````json
{
  "messages": [
    {
      "content": "帮我算一下 (2026 * 3 + 114) / 7，另外现在几点了？",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "human",
      "name": null,
      "id": "61a6f04d-f9cc-4564-bc98-01292f89300e"
    },
    {
      "content": "",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 133,
          "prompt_tokens": 445,
          "total_tokens": 578,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 63,
            "rejected_prediction_tokens": null,
            "text_tokens": 70
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "d51d3b03b00d4511a3430f4a04647d42",
        "finish_reason": "tool_calls",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a134bd-ef91-78a0-b43b-e648cf5a9993-0",
      "tool_calls": [
        {
          "name": "calculate",
          "args": {
            "expression": "(2026 * 3 + 114) / 7"
          },
          "id": "call_1be03124328e4cce923a5424",
          "type": "tool_call"
        },
        {
          "name": "get_current_time",
          "args": {},
          "id": "call_710c558513ff4c8c94b948ef",
          "type": "tool_call"
        }
      ],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 445,
        "output_tokens": 133,
        "total_tokens": 578,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 63
        }
      }
    },
    {
      "content": "884.5714285714286",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "tool",
      "name": "calculate",
      "id": "193bc6d5-93e3-44ac-b894-66669d060e10",
      "tool_call_id": "call_1be03124328e4cce923a5424",
      "artifact": null,
      "status": "success"
    },
    {
      "content": "2026-10-13 18:10:26",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "tool",
      "name": "get_current_time",
      "id": "52581a51-3ccd-4f74-9807-0ebba5211d58",
      "tool_call_id": "call_710c558513ff4c8c94b948ef",
      "artifact": null,
      "status": "success"
    },
    {
      "content": "计算结果如下：\n\n- **(2026 × 3 + 114) ÷ 7 = 884.5714285714286**（约等于 884.57）\n\n另外，当前本地时间是 **2026年10月13日 18:10:26**。",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 58,
          "prompt_tokens": 554,
          "total_tokens": 612,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 1,
            "rejected_prediction_tokens": null,
            "text_tokens": 57
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "3c977496a3e1434592a306bf0edce25d",
        "finish_reason": "stop",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a134bd-f581-7ae0-8b9a-917f887292b7-0",
      "tool_calls": [],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 554,
        "output_tokens": 58,
        "total_tokens": 612,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 1
        }
      }
    }
  ]
}
````

### 逐条消息全量导出

#### [1] HumanMessage ｜ 用户输入


可读全文（pretty_repr）：

````text
================================ Human Message =================================

帮我算一下 (2026 * 3 + 114) / 7，另外现在几点了？
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "帮我算一下 (2026 * 3 + 114) / 7，另外现在几点了？",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "human",
  "name": null,
  "id": "61a6f04d-f9cc-4564-bc98-01292f89300e"
}
````

#### [2] AIMessage ｜ 模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答

- 工具调用指令：`calculate`，参数 `{'expression': '(2026 * 3 + 114) / 7'}`，id `call_1be03124328e4cce923a5424`
- 工具调用指令：`get_current_time`，参数 `{}`，id `call_710c558513ff4c8c94b948ef`
- token 用量：`{'input_tokens': 445, 'output_tokens': 133, 'total_tokens': 578, 'input_token_details': {}, 'output_token_details': {'reasoning': 63}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  calculate (call_1be03124328e4cce923a5424)
 Call ID: call_1be03124328e4cce923a5424
  Args:
    expression: (2026 * 3 + 114) / 7
  get_current_time (call_710c558513ff4c8c94b948ef)
 Call ID: call_710c558513ff4c8c94b948ef
  Args:
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
      "completion_tokens": 133,
      "prompt_tokens": 445,
      "total_tokens": 578,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 63,
        "rejected_prediction_tokens": null,
        "text_tokens": 70
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "d51d3b03b00d4511a3430f4a04647d42",
    "finish_reason": "tool_calls",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a134bd-ef91-78a0-b43b-e648cf5a9993-0",
  "tool_calls": [
    {
      "name": "calculate",
      "args": {
        "expression": "(2026 * 3 + 114) / 7"
      },
      "id": "call_1be03124328e4cce923a5424",
      "type": "tool_call"
    },
    {
      "name": "get_current_time",
      "args": {},
      "id": "call_710c558513ff4c8c94b948ef",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 445,
    "output_tokens": 133,
    "total_tokens": 578,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 63
    }
  }
}
````

#### [3] ToolMessage ｜ 工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）

- 执行工具：`calculate`，tool_call_id `call_1be03124328e4cce923a5424`

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
  "id": "193bc6d5-93e3-44ac-b894-66669d060e10",
  "tool_call_id": "call_1be03124328e4cce923a5424",
  "artifact": null,
  "status": "success"
}
````

#### [4] ToolMessage ｜ 工具的被执行结果（框架自动执行后注入对话，模型下一轮会看到）

- 执行工具：`get_current_time`，tool_call_id `call_710c558513ff4c8c94b948ef`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: get_current_time

2026-10-13 18:10:26
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "2026-10-13 18:10:26",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "get_current_time",
  "id": "52581a51-3ccd-4f74-9807-0ebba5211d58",
  "tool_call_id": "call_710c558513ff4c8c94b948ef",
  "artifact": null,
  "status": "success"
}
````

#### [5] AIMessage ｜ 模型输出：带 tool_calls 时是「工具调用指令」，不带时是最终回答

- token 用量：`{'input_tokens': 554, 'output_tokens': 58, 'total_tokens': 612, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================

计算结果如下：

- **(2026 × 3 + 114) ÷ 7 = 884.5714285714286**（约等于 884.57）

另外，当前本地时间是 **2026年10月13日 18:10:26**。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "计算结果如下：\n\n- **(2026 × 3 + 114) ÷ 7 = 884.5714285714286**（约等于 884.57）\n\n另外，当前本地时间是 **2026年10月13日 18:10:26**。",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 58,
      "prompt_tokens": 554,
      "total_tokens": 612,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1,
        "rejected_prediction_tokens": null,
        "text_tokens": 57
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "3c977496a3e1434592a306bf0edce25d",
    "finish_reason": "stop",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a134bd-f581-7ae0-8b9a-917f887292b7-0",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 554,
    "output_tokens": 58,
    "total_tokens": 612,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 1
    }
  }
}
````

### 最终回答（messages 里最后一条 AI 消息的 content）

````text
计算结果如下：

- **(2026 × 3 + 114) ÷ 7 = 884.5714285714286**（约等于 884.57）

另外，当前本地时间是 **2026年10月13日 18:10:26**。
````

## 【2】agent.stream：一次执行，同时观察两种粒度

本次用 `stream_mode=["updates", "messages"]` 一次执行采集两路视图（数据来自同一轮执行，可严格对照）：
- `updates`（节点级）：每个节点执行完成上报一次，内容是聚合后的完整消息
- `messages`（消息事件级）：LLM 的 token 分片逐个转发（聚合前的原始增量）；节点产出的完整消息（如工具结果）也会被转发


### 节点级视图（updates）：agent 循环的每一步

#### 第 1 步 ｜ 节点：`model`

产出 `AIMessage`（工具调用指令）:

- 工具调用指令：`calculate`，参数 `{'expression': '(2026 * 3 + 114) / 7'}`，id `call_0dd6511d4092427f9cfb29c6`
- 工具调用指令：`get_current_time`，参数 `{}`，id `call_7c27e49975f443e68918c44d`
- token 用量：`{'input_tokens': 445, 'output_tokens': 123, 'total_tokens': 568, 'input_token_details': {}, 'output_token_details': {'reasoning': 53}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================
Tool Calls:
  calculate (call_0dd6511d4092427f9cfb29c6)
 Call ID: call_0dd6511d4092427f9cfb29c6
  Args:
    expression: (2026 * 3 + 114) / 7
  get_current_time (call_7c27e49975f443e68918c44d)
 Call ID: call_7c27e49975f443e68918c44d
  Args:
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "\n\n",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "tool_calls",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
  "tool_calls": [
    {
      "name": "calculate",
      "args": {
        "expression": "(2026 * 3 + 114) / 7"
      },
      "id": "call_0dd6511d4092427f9cfb29c6",
      "type": "tool_call"
    },
    {
      "name": "get_current_time",
      "args": {},
      "id": "call_7c27e49975f443e68918c44d",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 445,
    "output_tokens": 123,
    "total_tokens": 568,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 53
    }
  }
}
````

#### 第 2 步 ｜ 节点：`tools`

产出 `ToolMessage`（calculate 执行结果 = 884.5714285714286）:

- 执行工具：`calculate`，tool_call_id `call_0dd6511d4092427f9cfb29c6`

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
  "id": "1cdf2024-3664-4521-b33e-6dc40738419b",
  "tool_call_id": "call_0dd6511d4092427f9cfb29c6",
  "artifact": null,
  "status": "success"
}
````

#### 第 3 步 ｜ 节点：`tools`

产出 `ToolMessage`（get_current_time 执行结果 = 2026-10-13 18:10:27）:

- 执行工具：`get_current_time`，tool_call_id `call_7c27e49975f443e68918c44d`

可读全文（pretty_repr）：

````text
================================= Tool Message =================================
Name: get_current_time

2026-10-13 18:10:27
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "2026-10-13 18:10:27",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "get_current_time",
  "id": "36b6f290-d97d-4e0a-80b9-f7e7895b336d",
  "tool_call_id": "call_7c27e49975f443e68918c44d",
  "artifact": null,
  "status": "success"
}
````

#### 第 4 步 ｜ 节点：`model`

产出 `AIMessage`（最终回答）:

- token 用量：`{'input_tokens': 554, 'output_tokens': 150, 'total_tokens': 704, 'input_token_details': {}, 'output_token_details': {'reasoning': 45}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================

计算结果如下：

- **(2026 × 3 + 114) ÷ 7 = 884.571428571…**（约等于 884.57）

顺便说明一下中间过程：
- 2026 × 3 = 6078
- 6078 + 114 = 6192
- 6192 ÷ 7 = 884.5714…

另外，**当前时间是 2026 年 10 月 13 日 18:10:27**。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "计算结果如下：\n\n- **(2026 × 3 + 114) ÷ 7 = 884.571428571…**（约等于 884.57）\n\n顺便说明一下中间过程：\n- 2026 × 3 = 6078\n- 6078 + 114 = 6192\n- 6192 ÷ 7 = 884.5714…\n\n另外，**当前时间是 2026 年 10 月 13 日 18:10:27**。",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "stop",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 554,
    "output_tokens": 150,
    "total_tokens": 704,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 45
    }
  }
}
````


### 完整步骤序列（原样一体化导出，一个字段不省略）

本视图本次共上报 4 个步骤对象，完整 JSON 已写入本文件（每个 step 就是 `{节点名: {'messages': [该节点产出的完整消息]}}`）。

````json
[
  {
    "model": {
      "messages": [
        {
          "content": "\n\n",
          "additional_kwargs": {},
          "response_metadata": {
            "finish_reason": "tool_calls",
            "model_name": "deepseek-v4-flash-sz",
            "model_provider": "openai"
          },
          "type": "ai",
          "name": null,
          "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
          "tool_calls": [
            {
              "name": "calculate",
              "args": {
                "expression": "(2026 * 3 + 114) / 7"
              },
              "id": "call_0dd6511d4092427f9cfb29c6",
              "type": "tool_call"
            },
            {
              "name": "get_current_time",
              "args": {},
              "id": "call_7c27e49975f443e68918c44d",
              "type": "tool_call"
            }
          ],
          "invalid_tool_calls": [],
          "usage_metadata": {
            "input_tokens": 445,
            "output_tokens": 123,
            "total_tokens": 568,
            "input_token_details": {},
            "output_token_details": {
              "reasoning": 53
            }
          }
        }
      ]
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
          "id": "1cdf2024-3664-4521-b33e-6dc40738419b",
          "tool_call_id": "call_0dd6511d4092427f9cfb29c6",
          "artifact": null,
          "status": "success"
        }
      ]
    }
  },
  {
    "tools": {
      "messages": [
        {
          "content": "2026-10-13 18:10:27",
          "additional_kwargs": {},
          "response_metadata": {},
          "type": "tool",
          "name": "get_current_time",
          "id": "36b6f290-d97d-4e0a-80b9-f7e7895b336d",
          "tool_call_id": "call_7c27e49975f443e68918c44d",
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
          "content": "计算结果如下：\n\n- **(2026 × 3 + 114) ÷ 7 = 884.571428571…**（约等于 884.57）\n\n顺便说明一下中间过程：\n- 2026 × 3 = 6078\n- 6078 + 114 = 6192\n- 6192 ÷ 7 = 884.5714…\n\n另外，**当前时间是 2026 年 10 月 13 日 18:10:27**。",
          "additional_kwargs": {},
          "response_metadata": {
            "finish_reason": "stop",
            "model_name": "deepseek-v4-flash-sz",
            "model_provider": "openai"
          },
          "type": "ai",
          "name": null,
          "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
          "tool_calls": [],
          "invalid_tool_calls": [],
          "usage_metadata": {
            "input_tokens": 554,
            "output_tokens": 150,
            "total_tokens": 704,
            "input_token_details": {},
            "output_token_details": {
              "reasoning": 45
            }
          }
        }
      ]
    }
  }
]
````

## 【3】messages 视图：token 分片与工具完整消息（与【2】严格对照）

`stream_mode="messages"` 把 agent 执行过程中的消息事件转发出来：LLM 部分是逐 token 的`AIMessageChunk` 分片，工具结果则是完整 `ToolMessage`；每个事件都是 `(消息对象, metadata)` 二元组。本节的核心就是验证：分片如何聚合出【2】里的完整消息。

### 先解剖两个元组：一次 yield 的完整实例

`for mode, payload in agent.stream(..., stream_mode=["updates", "messages"])` —— 每循环一次，就从流里接到一个二元组 `(mode, payload)`；当 `mode == "messages"` 时，`payload` 本身又是一个二元组 `(message, metadata)`。层级关系如下：

````text
一次 yield = (mode, payload)                              ← 外层：二元组
  ├─ mode = "updates"  → payload：dict {节点名: {"messages": [完整消息, ...]}}
  └─ mode = "messages" → payload：tuple (message, metadata)          ← 内层：又一个二元组
                                            ├─ message ：AIMessageChunk（token 分片）/ ToolMessage（完整消息）
                                            └─ metadata：dict（框架附加的上下文：节点名、步数、模型信息等）
````

#### 实例一：`mode == "messages"` 的第 1 次 yield（本次运行的真实对象，repr 原样不裁切）

````text
('messages', (AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[]), {'langgraph_step': 1, 'langgraph_node': 'model', 'langgraph_triggers': ('branch:to:model',), 'langgraph_path': ('__pregel_pull', 'model'), 'langgraph_checkpoint_ns': 'model:afabe560-38f1-068b-6a35-8a5874170360', 'checkpoint_ns': 'model:afabe560-38f1-068b-6a35-8a5874170360', 'ls_provider': 'openai', 'ls_model_name': 'deepseek-v4-flash-sz', 'ls_model_type': 'chat', 'ls_temperature': None}))
````

逐层分解：
- `mode` = `'messages'`（`str`）——流的名字，决定 payload 的形态
- `payload` = 二元组 `(message, metadata)`（`tuple`，长度 2）
  - `message`：`langchain_core.messages.ai.AIMessageChunk` 对象（content=``、id=`lc_run--01a134bd-f751-7b10-a52c-47347a319080`、tool_call_chunks 0 项）——第 1 个分片常是「骨架」：content 为空，后续分片才带入增量
  - `metadata`：`dict`，键：`['langgraph_step', 'langgraph_node', 'langgraph_triggers', 'langgraph_path', 'langgraph_checkpoint_ns', 'checkpoint_ns', 'ls_provider', 'ls_model_name', 'ls_model_type', 'ls_temperature']`
  - 两项的完整字段展开就是【3.3】的「事件 1」块，可直接对照。

#### 实例二：`mode == "updates"` 的第 1 次 yield（本次运行的真实对象，repr 原样不裁切）

````text
('updates', {'model': {'messages': [AIMessage(content='\n\n', additional_kwargs={}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[{'name': 'calculate', 'args': {'expression': '(2026 * 3 + 114) / 7'}, 'id': 'call_0dd6511d4092427f9cfb29c6', 'type': 'tool_call'}, {'name': 'get_current_time', 'args': {}, 'id': 'call_7c27e49975f443e68918c44d', 'type': 'tool_call'}], invalid_tool_calls=[], usage_metadata={'input_tokens': 445, 'output_tokens': 123, 'total_tokens': 568, 'input_token_details': {}, 'output_token_details': {'reasoning': 53}})]}})
````

逐层分解：
- `mode` = `'updates'`（`str`）
- `payload` = dict（`dict`），键 = `['model']`（键就是上报的节点名）
  - `payload['model']` = 该节点的状态更新 dict，键 = `['messages']`
  - `payload['model']['messages']` = 长 1 的列表，里面是节点产出的**完整消息**（聚合后的成品，不是分片）
  - 完整字段展开见【2】第 1 步的导出。

两层解包的代码形态：

````python
for mode, payload in agent.stream(...):        # 第 1 层：(mode, payload)
    if mode == "updates":
        for node, update in payload.items():    # 节点名 → 状态更新
            for m in update["messages"]: ...
    else:  # mode == "messages"
        message, metadata = payload             # 第 2 层：(message, metadata)
````
### 两种粒度的对照总览

- messages 视图事件总数：**67** 个，来自 3 段节点活动
  - 其中 LLM token 分片（`AIMessageChunk`）：**65** 个；工具完整消息（`ToolMessage`）：**2** 条
  - 第 1 组（token 分片组）：26 个事件 ｜ 来源节点 `model` ｜ langgraph_step=1
  - 第 2 组（完整消息组）：2 个事件 ｜ 来源节点 `tools` ｜ langgraph_step=2
  - 第 3 组（token 分片组）：39 个事件 ｜ 来源节点 `model` ｜ langgraph_step=3
- 同一轮执行里 updates 视图只上报 4 个节点级步骤：token 分片是「原料」，节点步骤里的完整消息是「聚合后的成品」。
- 工具没有 token 流：其结果以完整 `ToolMessage` 的形式出现在 messages 视图，没有分片过程。

metadata 不单独提取展示（提取会让 `(message, metadata)` 的真实二元组结构失真），它的原样内容见本章【3.3 逐事件全量导出】里每个事件内部的【第 2 项】。

### 聚合演示：分片用 + 累加，还原成完整消息（与 updates 严格对照）

聚合方式即 merge_chunks_demo.py 里演示过的 `reduce(operator.add, chunks)`：content 首尾相接、tool_calls 由 tool_call_chunks 增量拼出、usage 随末块合并。
注意：`+` 聚合只对 `AIMessageChunk` 成立（它重载了 `__add__` 做增量合并）；普通消息的 `+` 是「拼进 ChatPromptTemplate」的语义，所以聚合消息对象必须用分片。

下面是逐组结果与【2】对照（工具消息组无 token 流可聚合，直接展示原消息）：

#### 第 1 组 ｜ 26 个 token 分片 -> 决策消息（对应【2】第 1 步）

- id 是否一致：**是**（聚合 `lc_run--01a134bd-f751-7b10-a52c-47347a319080` vs updates `lc_run--01a134bd-f751-7b10-a52c-47347a319080`）
- content 是否一致：**是**（聚合 2 字 vs updates 2 字）
- tool_calls 是否一致：**是**（聚合 2 个 vs updates 2 个）
- usage_metadata 是否一致：**是**（聚合 `{'input_tokens': 445, 'output_tokens': 123, 'total_tokens': 568, 'input_token_details': {}, 'output_token_details': {'reasoning': 53}}`）
- 聚合出的工具调用：`calculate`，参数 `{'expression': '(2026 * 3 + 114) / 7'}`，id `call_0dd6511d4092427f9cfb29c6`
- 聚合出的工具调用：`get_current_time`，参数 `{}`，id `call_7c27e49975f443e68918c44d`
- 聚合出的完整文本（2 字）：
````text



````

#### 第 2 组 ｜ 2 条完整消息（工具结果，无 token 流可聚合）

- `ToolMessage`：`calculate` 的执行结果，tool_call_id `call_0dd6511d4092427f9cfb29c6`：
````text
884.5714285714286
````
- `ToolMessage`：`get_current_time` 的执行结果，tool_call_id `call_7c27e49975f443e68918c44d`：
````text
2026-10-13 18:10:27
````

#### 第 3 组 ｜ 39 个 token 分片 -> 最终回答（对应【2】最后一步）

- id 是否一致：**是**（聚合 `lc_run--01a134bd-f99c-7c53-bb62-839037ea847b` vs updates `lc_run--01a134bd-f99c-7c53-bb62-839037ea847b`）
- content 是否一致：**是**（聚合 179 字 vs updates 179 字）
- tool_calls 是否一致：**是**（聚合 0 个 vs updates 0 个）
- usage_metadata 是否一致：**是**（聚合 `{'input_tokens': 554, 'output_tokens': 150, 'total_tokens': 704, 'input_token_details': {}, 'output_token_details': {'reasoning': 45}}`）
- 聚合出的完整文本（179 字）：
````text
计算结果如下：

- **(2026 × 3 + 114) ÷ 7 = 884.571428571…**（约等于 884.57）

顺便说明一下中间过程：
- 2026 × 3 = 6078
- 6078 + 114 = 6192
- 6192 ÷ 7 = 884.5714…

另外，**当前时间是 2026 年 10 月 13 日 18:10:27**。
````

### 逐事件全量导出（按流的原始结构，一个字段不省略）

按 yield 的原始顺序，把全部 67 个事件原样端出。每个事件的真实结构就是一个 `(message, metadata)` 二元组：第 1 项是消息对象（真实类型全路径 + 原始 repr + 全字段 model_dump），第 2 项是框架附加的 metadata（真实流中每个事件都会携带一份，内容同组相同，但确实逐事件重复出现）。

观察要点：决策组 token 分片的 `tool_call_chunks` 字段——args 是逐片到达的残缺 JSON 片段，拼完才是完整参数。

#### 第 1 组 ｜ 来源节点 `model` ｜ langgraph_step=1 ｜ 共 26 个事件

##### 事件 1/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 2/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 3/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 4/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 5/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 6/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 7/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 8/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 9/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 10/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 11/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 12/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 13/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 14/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 15/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 16/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='\n\n', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "\n\n",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 17/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[{'name': 'calculate', 'args': {}, 'id': 'call_0dd6511d4092427f9cfb29c6', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'calculate', 'args': '', 'id': 'call_0dd6511d4092427f9cfb29c6', 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
  "tool_calls": [
    {
      "name": "calculate",
      "args": {},
      "id": "call_0dd6511d4092427f9cfb29c6",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "calculate",
      "args": "",
      "id": "call_0dd6511d4092427f9cfb29c6",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 18/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 19/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"expression": "(2026 *', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"expression": "(2026 *', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"expression\": \"(2026 *",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"expression\": \"(2026 *",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 20/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 3 + 114)', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 3 + 114)', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 21/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' / 7"}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' / 7"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " / 7\"}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " / 7\"}",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 22/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[{'name': 'get_current_time', 'args': {}, 'id': 'call_7c27e49975f443e68918c44d', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'get_current_time', 'args': '', 'id': 'call_7c27e49975f443e68918c44d', 'index': 1, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
  "tool_calls": [
    {
      "name": "get_current_time",
      "args": {},
      "id": "call_7c27e49975f443e68918c44d",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "get_current_time",
      "args": "",
      "id": "call_7c27e49975f443e68918c44d",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 23/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{}', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
      "args": "{}",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 24/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 25/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 445, 'output_tokens': 123, 'total_tokens': 568, 'input_token_details': {}, 'output_token_details': {'reasoning': 53}}, tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 445,
    "output_tokens": 123,
    "total_tokens": 568,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 53
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 26/67（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a134bd-f751-7b10-a52c-47347a319080', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f751-7b10-a52c-47347a319080",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "checkpoint_ns": "model:afabe560-38f1-068b-6a35-8a5874170360",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 第 2 组 ｜ 来源节点 `tools` ｜ langgraph_step=2 ｜ 共 2 个事件

##### 事件 27/67（第 2 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content='884.5714285714286', name='calculate', id='1cdf2024-3664-4521-b33e-6dc40738419b', tool_call_id='call_0dd6511d4092427f9cfb29c6')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "884.5714285714286",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "calculate",
  "id": "1cdf2024-3664-4521-b33e-6dc40738419b",
  "tool_call_id": "call_0dd6511d4092427f9cfb29c6",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 2,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    0,
    false
  ],
  "langgraph_checkpoint_ns": "tools:2a88513c-fd77-bc28-2318-5dc3e110a047"
}
````

##### 事件 28/67（第 2 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content='2026-10-13 18:10:27', name='get_current_time', id='36b6f290-d97d-4e0a-80b9-f7e7895b336d', tool_call_id='call_7c27e49975f443e68918c44d')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "2026-10-13 18:10:27",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "get_current_time",
  "id": "36b6f290-d97d-4e0a-80b9-f7e7895b336d",
  "tool_call_id": "call_7c27e49975f443e68918c44d",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 2,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    1,
    false
  ],
  "langgraph_checkpoint_ns": "tools:4dd32797-edf3-ee9f-929b-3adc0091f37b"
}
````

#### 第 3 组 ｜ 来源节点 `model` ｜ langgraph_step=3 ｜ 共 39 个事件

##### 事件 29/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 30/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 31/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 32/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 33/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 34/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 35/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 36/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 37/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 38/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 39/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 40/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 41/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='计算结果', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "计算结果",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 42/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='如下：\n\n-', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "如下：\n\n-",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 43/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' **(', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " **(",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 44/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='2026 × 3 +', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "2026 × 3 +",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 45/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 114) ÷ 7', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " 114) ÷ 7",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 46/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' = 884.571428', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " = 884.571428",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 47/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='571…', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "571…",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 48/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='**（约等于', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "**（约等于",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 49/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 884.57）\n\n顺便', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " 884.57）\n\n顺便",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 50/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='说明一下中间', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "说明一下中间",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 51/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='过程', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "过程",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 52/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='：\n- 2026 ×', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "：\n- 2026 ×",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 53/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 3 = 6078', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " 3 = 6078",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 54/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='\n- 6078 +', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "\n- 6078 +",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 55/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 114 = 619', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " 114 = 619",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 56/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='2\n- 6192', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "2\n- 6192",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 57/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' ÷ 7 = 884', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 58/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='.5714…\n\n', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": ".5714…\n\n",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 59/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='另外，', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "另外，",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 60/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='**', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "**",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 61/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='当前时间是 2026 ', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "当前时间是 2026 ",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 62/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='年 10 月 ', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "年 10 月 ",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 63/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='13 日 18:', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "13 日 18:",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 64/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='10:27**。', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "10:27**。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 65/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'stop', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 66/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 554, 'output_tokens': 150, 'total_tokens': 704, 'input_token_details': {}, 'output_token_details': {'reasoning': 45}}, tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 554,
    "output_tokens": 150,
    "total_tokens": 704,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 45
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 67/67（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a134bd-f99c-7c53-bb62-839037ea847b', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-f99c-7c53-bb62-839037ea847b",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "checkpoint_ns": "model:c1685188-0c78-2091-144e-7c43e2469b03",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````


### 两种视图差异速查

| 维度 | 节点级 updates（【2】） | token 级 messages（【3】） |
| --- | --- | --- |
| 上报单位 | 节点执行完成（一次事件 = 一个节点的完整产物） | LLM token 分片 + 节点产出的完整消息（如工具结果） |
| 消息形态 | 聚合后的完整消息（直接用） | 未聚合的 `AIMessageChunk`（需 `+` 累加）；工具为完整 `ToolMessage` |
| tool_calls 形态 | 完整解析后的 JSON 参数 | `tool_call_chunks` 增量片段（残缺 JSON） |
| usage_metadata | 每条 AI 消息都带全 | 仅每组的末分片带 |
| 工具执行过程 | 可见（ToolMessage） | 可见，但为完整 ToolMessage（无 token 流可聚合） |
| 典型用途 | 观察循环进度、取最终状态 | 打字机效果、TTFT 观测、理解聚合过程 |

## 【4】同步 stream vs 异步 astream：输出会变化吗

结论先行：**输出结构完全一致，换成异步不会有任何形状变化**。两个接口消费同一套流式管道：
- 都 yield `(mode, payload)`；messages 的 payload 都是 `(消息对象, metadata)` 二元组
- 消息对象类型相同（`AIMessageChunk` / `ToolMessage`）、metadata 键集相同、updates 步骤形状相同
- 两点区别与「输出」无关：① 消费代码形态（`for` vs `async for`）；② 两次独立调用自身的内容随机性（分片数、措辞每次本就不同，同步连跑两次也一样）

下面是两侧各跑一次的程序化对照证据（同一问题）。

### 两侧运行总览

| 维度 | 同步 `agent.stream` | 异步 `agent.astream` |
| --- | --- | --- |
| 消费代码 | `for mode, payload in agent.stream(...)` | `async for mode, payload in agent.astream(...)` |
| messages 事件总数 | 67 | 42 |
| 其中 token 分片 / 工具消息 | 65 / 2 | 40 / 2 |
| updates 步骤数 | 4 | 4 |
| updates 节点序列 | `model -> tools -> tools -> model` | `model -> tools -> tools -> model` |
| 事件形状段数 | 3 | 3 |

### 事件形状对照（运行长度编码）

把事件序列折叠成形状序列（形状 = 消息类名 + 产出节点 + 步数，相邻同形状合并计数）：

同步侧：
1. `AIMessageChunk` ｜ node=`model` ｜ step=1 ｜ × 26
2. `ToolMessage` ｜ node=`tools` ｜ step=2 ｜ × 2
3. `AIMessageChunk` ｜ node=`model` ｜ step=3 ｜ × 39

异步侧：
1. `AIMessageChunk` ｜ node=`model` ｜ step=1 ｜ × 22
2. `ToolMessage` ｜ node=`tools` ｜ step=2 ｜ × 2
3. `AIMessageChunk` ｜ node=`model` ｜ step=3 ｜ × 18

形状序列逐项一致：**是**（只有每段计数不同——那是两次调用各自的分片随机性，与同步/异步无关）

### metadata 键集对照

metadata 的键集也是结构的一部分，逐段对照（段编号与 4.2 对应）：

- 第 1 段（`AIMessageChunk` ｜ node=`model`）：同步 ['checkpoint_ns', 'langgraph_checkpoint_ns', 'langgraph_node', 'langgraph_path', 'langgraph_step', 'langgraph_triggers', 'ls_model_name', 'ls_model_type', 'ls_provider', 'ls_temperature'] ｜ 异步 ['checkpoint_ns', 'langgraph_checkpoint_ns', 'langgraph_node', 'langgraph_path', 'langgraph_step', 'langgraph_triggers', 'ls_model_name', 'ls_model_type', 'ls_provider', 'ls_temperature'] → **一致**
- 第 2 段（`ToolMessage` ｜ node=`tools`）：同步 ['langgraph_checkpoint_ns', 'langgraph_node', 'langgraph_path', 'langgraph_step', 'langgraph_triggers'] ｜ 异步 ['langgraph_checkpoint_ns', 'langgraph_node', 'langgraph_path', 'langgraph_step', 'langgraph_triggers'] → **一致**
- 第 3 段（`AIMessageChunk` ｜ node=`model`）：同步 ['checkpoint_ns', 'langgraph_checkpoint_ns', 'langgraph_node', 'langgraph_path', 'langgraph_step', 'langgraph_triggers', 'ls_model_name', 'ls_model_type', 'ls_provider', 'ls_temperature'] ｜ 异步 ['checkpoint_ns', 'langgraph_checkpoint_ns', 'langgraph_node', 'langgraph_path', 'langgraph_step', 'langgraph_triggers', 'ls_model_name', 'ls_model_type', 'ls_provider', 'ls_temperature'] → **一致**

### 异步侧聚合校验（astream 的分片能否同样还原）

对异步侧每组 token 分片做 `reduce(operator.add, ...)` 聚合，与异步 updates 里的完整 AI 消息逐项对照：

- 第 1 组（22 个分片 -> 第 1 条 AI 消息）：id 一致 ｜ content 一致（0 字） ｜ tool_calls 一致（2 个） ｜ usage_metadata 一致
- 第 3 组（18 个分片 -> 第 2 条 AI 消息）：id 一致 ｜ content 一致（115 字） ｜ tool_calls 一致（0 个） ｜ usage_metadata 一致

### 异步侧逐事件全量导出（与【3.3】同格式，一个字段不省略）

异步流同样按 `(message, metadata)` 二元组原样端出全部 42 个事件；格式与【3.3】完全相同，可直接与同步侧对照。

#### 第 1 组 ｜ 来源节点 `model` ｜ langgraph_step=1 ｜ 共 22 个事件

##### 事件 1/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 2/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 3/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 4/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 5/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 6/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 7/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 8/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 9/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 10/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 11/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 12/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 13/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[{'name': 'calculate', 'args': {}, 'id': 'call_c3d8acf23bea4614a2df3710', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'calculate', 'args': '', 'id': 'call_c3d8acf23bea4614a2df3710', 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
  "tool_calls": [
    {
      "name": "calculate",
      "args": {},
      "id": "call_c3d8acf23bea4614a2df3710",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "calculate",
      "args": "",
      "id": "call_c3d8acf23bea4614a2df3710",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 14/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 15/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '"expression": "(', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '"expression": "(', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": "\"expression\": \"(",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": "\"expression\": \"(",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 16/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': '2026 * 3 +', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': '2026 * 3 +', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 17/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[{'name': None, 'args': ' 114) / 7"}', 'id': None, 'error': None, 'type': 'invalid_tool_call'}], tool_call_chunks=[{'name': None, 'args': ' 114) / 7"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
  "tool_calls": [],
  "invalid_tool_calls": [
    {
      "name": null,
      "args": " 114) / 7\"}",
      "id": null,
      "error": null,
      "type": "invalid_tool_call"
    }
  ],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": null,
      "args": " 114) / 7\"}",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 18/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[{'name': 'get_current_time', 'args': {}, 'id': 'call_8c95f03e353d47cc9436f12a', 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': 'get_current_time', 'args': '', 'id': 'call_8c95f03e353d47cc9436f12a', 'index': 1, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
  "tool_calls": [
    {
      "name": "get_current_time",
      "args": {},
      "id": "call_8c95f03e353d47cc9436f12a",
      "type": "tool_call"
    }
  ],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [
    {
      "name": "get_current_time",
      "args": "",
      "id": "call_8c95f03e353d47cc9436f12a",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 19/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[{'name': '', 'args': {}, 'id': None, 'type': 'tool_call'}], invalid_tool_calls=[], tool_call_chunks=[{'name': None, 'args': '{}', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
      "args": "{}",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 20/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 21/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 445, 'output_tokens': 113, 'total_tokens': 558, 'input_token_details': {}, 'output_token_details': {'reasoning': 43}}, tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 445,
    "output_tokens": 113,
    "total_tokens": 558,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 43
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 22/42（第 1 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fc11-7681-b15b-3d8cfbfcdad2",
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
  "langgraph_step": 1,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "checkpoint_ns": "model:30959946-96aa-140e-3258-557939cfdef9",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 第 2 组 ｜ 来源节点 `tools` ｜ langgraph_step=2 ｜ 共 2 个事件

##### 事件 23/42（第 2 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content='2026-10-13 18:10:29', name='get_current_time', id='fab8004b-467b-4db4-bae5-f3f690b9b8fa', tool_call_id='call_8c95f03e353d47cc9436f12a')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "2026-10-13 18:10:29",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "get_current_time",
  "id": "fab8004b-467b-4db4-bae5-f3f690b9b8fa",
  "tool_call_id": "call_8c95f03e353d47cc9436f12a",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 2,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    1,
    false
  ],
  "langgraph_checkpoint_ns": "tools:dc80f958-ad97-3e79-bd1d-a4045b921a22"
}
````

##### 事件 24/42（第 2 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.tool.ToolMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
ToolMessage(content='884.5714285714286', name='calculate', id='d45dd2df-e06b-49c8-9dda-996b5e1db13b', tool_call_id='call_c3d8acf23bea4614a2df3710')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "884.5714285714286",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "tool",
  "name": "calculate",
  "id": "d45dd2df-e06b-49c8-9dda-996b5e1db13b",
  "tool_call_id": "call_c3d8acf23bea4614a2df3710",
  "artifact": null,
  "status": "success"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 2,
  "langgraph_node": "tools",
  "langgraph_triggers": [
    "__pregel_push"
  ],
  "langgraph_path": [
    "__pregel_push",
    0,
    false
  ],
  "langgraph_checkpoint_ns": "tools:63d8b394-7c2c-77b6-0090-9ec50fe92bf6"
}
````

#### 第 3 组 ｜ 来源节点 `model` ｜ langgraph_step=3 ｜ 共 18 个事件

##### 事件 25/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 26/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='计算结果：\n\n', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "计算结果：\n\n",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 27/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='**(2026 ×', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "**(2026 ×",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 28/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 3 + 114)', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 29/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' / 7 ≈', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " / 7 ≈",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 30/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 884.571428571', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " 884.571428571",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 31/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='4286**\n\n也就是 **', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "4286**\n\n也就是 **",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 32/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='884又', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "884又",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 33/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='4/7**（', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "4/7**（",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 34/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='约', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "约",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 35/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' 884.57）。\n\n另外', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " 884.57）。\n\n另外",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 36/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='，当前时间是 **2026', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "，当前时间是 **2026",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 37/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='年10月13日 ', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "年10月13日 ",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 38/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='18:10:', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "18:10:",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 39/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='29**。', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "29**。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 40/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'stop', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 41/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 554, 'output_tokens': 62, 'total_tokens': 616, 'input_token_details': {}, 'output_token_details': {'reasoning': 1}}, tool_call_chunks=[])
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
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 554,
    "output_tokens": 62,
    "total_tokens": 616,
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

##### 事件 42/42（第 3 组）

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134bd-fe59-74a2-96c1-694b8f5908ac",
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
  "langgraph_step": 3,
  "langgraph_node": "model",
  "langgraph_triggers": [
    "branch:to:model"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "model"
  ],
  "langgraph_checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "checkpoint_ns": "model:18104bdd-4ad2-b7f7-cf60-0fce9ee17d42",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````


## 附：消息字段速查

- `type`：消息类型（human / ai / tool），打印时的 `HumanMessage` 等类名与之对应
- `content`：消息正文；AI 决策消息的 content 通常为空（它只负责表达“要调工具”）
- `tool_calls`：AI 消息特有字段，模型请求调用的工具清单，每项含 name / args / id
- `tool_call_id`：Tool 消息特有字段，与某条 tool_calls[i].id 配对，标明“这条结果是哪个请求的执行结果”
- `name`：Tool 消息特有字段，实际被执行工具的名字
- `usage_metadata`：AI 消息特有字段，token 用量（输入 / 输出 / 合计，含 reasoning 明细）；分片模式下只有每组的末分片带
- `tool_call_chunks`：`AIMessageChunk` 特有字段，流式中 tool_calls 的增量片段（args 为残缺 JSON，拼完才完整）
- `additional_kwargs` / `response_metadata`：厂商扩展字段与原始响应元数据（全量内容都在 model_dump 里）
