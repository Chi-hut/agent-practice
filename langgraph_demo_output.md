# 手写 LangGraph 最小图：输出全量解析

- 采集时间：2026-10-13 19:14:39
- 模型：`deepseek-v4-flash-sz`
- 问题：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系
- 图：`START -> prepare -> call_llm -> END`（prepare 为普通节点，call_llm 为 LLM 节点）
- 采集方式：invoke、stream(values)、stream(updates+messages) 共三次**独立**执行

> 说明：三次独立执行的模型回复文本、分片数量天然不同（模型随机性），但输出**结构**完全一致；
> 严格对照只看同一轮执行的数据（【3】与【4】同轮采集）。

## 【0】图的定义：状态 schema、节点、边

LangGraph 的三要素：**State**（所有节点共享的状态）、**Node**（读写状态的函数）、**Edge**（节点间的走向）。节点返回 dict 表示增量，同名字段怎么合并由 reducer 决定。

### 状态 schema（State，实测 `State.__annotations__`）

- `messages`：`typing.Annotated[list, <function _add_messages_wrapper.<locals>._add_messages at 0x000001B8E19FC360>]`  <- add_messages reducer：按 id 追加
- `question`：`<class 'str'>`  <- 无 reducer：后写覆盖

### 节点函数（inspect.getsource 原样取自本文件）

`prepare`：
````python
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

````
`call_llm`：
````python
def call_llm(state: State) -> dict:
    """LLM 节点：把当前消息列表原样交给模型，回复追加进 messages。"""
    print("  [节点] call_llm：调用 LLM ...")
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

````
### 搭图与编译（inspect.getsource）

````python
def build_graph():
    """搭图 + 编译。节点用字符串注册，边用字符串连线，compile 后才是可执行对象。"""
    builder = StateGraph(State)
    builder.add_node("prepare", prepare)      # 注册普通节点
    builder.add_node("call_llm", call_llm)    # 注册 LLM 节点
    builder.add_edge(START, "prepare")        # 入口 -> prepare
    builder.add_edge("prepare", "call_llm")   # 顺序执行
    builder.add_edge("call_llm", END)         # LLM 回复完即到终点
    return builder.compile()                  # 编译成 Runnable，之后就能 invoke / stream

````
### 图结构（`app.get_graph()` 的原始数据）

注意：编译后的图里不止你注册的两个节点——框架自动补了 `__start__` 和 `__end__` 两个虚拟节点，真实节点序列为 5 个。

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
    "id": "prepare",
    "name": "prepare",
    "type": null,
    "metadata": null
  },
  {
    "id": "call_llm",
    "name": "call_llm",
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
    "source": "__start__",
    "target": "prepare",
    "conditional": false,
    "data": null
  },
  {
    "source": "prepare",
    "target": "call_llm",
    "conditional": false,
    "data": null
  },
  {
    "source": "call_llm",
    "target": "__end__",
    "conditional": false,
    "data": null
  }
]
````
- mermaid 图源码（可粘贴到支持 mermaid 的查看器渲染）：

````mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	prepare(prepare)
	call_llm(call_llm)
	__end__([<p>__end__</p>]):::last
	__start__ --> prepare;
	prepare --> call_llm;
	call_llm --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

````
- ASCII 图（需要 grandalf 依赖，没装不影响其它章节）：

  - 生成失败：Install grandalf to draw graphs: `pip install grandalf`.

## 【1】graph.invoke：阻塞到全部结束，一次拿到最终状态

### 顶层结构

- 返回类型：`dict`（LangGraph 返回的是**最终状态 dict**，不是消息对象；对比 llm.invoke 返回单条 AIMessage）
- 顶层键：`['messages', 'question']`（messages 按序累积了全程消息；question 被 prepare 写入）
- messages 共 3 条，序列：`HumanMessage` -> `SystemMessage` -> `AIMessage`

### 完整返回值（原样一体化导出，一个字段不省略）

````json
{
  "messages": [
    {
      "content": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "human",
      "name": null,
      "id": "dac8bc4f-2bc9-4ac3-8e5a-9b0c08dcb382"
    },
    {
      "content": "请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "system",
      "name": null,
      "id": "c16e9f09-1b90-40f7-a6fe-65eb27a4536b"
    },
    {
      "content": "LangGraph 是一个用于构建有状态、可编排的 AI 代理和复杂工作流的框架，特别适合将 LLM 应用建模为图结构，支持循环、分支和人工介入。它由 LangChain 团队开发，可以看作 LangChain 的扩展层——LangChain 提供组件和工具，而 LangGraph 负责控制流程和状态管理，两者常结合使用。",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 94,
          "prompt_tokens": 124,
          "total_tokens": 218,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 11,
            "rejected_prediction_tokens": null,
            "text_tokens": 83
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "4842ebd3a8124866908b68c4a4af9224",
        "finish_reason": "stop",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a134f8-bff1-7211-83bb-e6a68f012e42-0",
      "tool_calls": [],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 124,
        "output_tokens": 94,
        "total_tokens": 218,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 11
        }
      }
    }
  ],
  "question": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系"
}
````

### 逐条消息全量导出

#### [1] HumanMessage ｜ 用户输入（invoke 初始状态里带进来的）


可读全文（pretty_repr）：

````text
================================ Human Message =================================

用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "human",
  "name": null,
  "id": "dac8bc4f-2bc9-4ac3-8e5a-9b0c08dcb382"
}
````

#### [2] SystemMessage ｜ prepare 节点追加的系统提示（验证 add_messages 的「追加」语义）


可读全文（pretty_repr）：

````text
================================ System Message ================================

请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "system",
  "name": null,
  "id": "c16e9f09-1b90-40f7-a6fe-65eb27a4536b"
}
````

#### [3] AIMessage ｜ call_llm 节点调 LLM 得到的回复

- token 用量：`{'input_tokens': 124, 'output_tokens': 94, 'total_tokens': 218, 'input_token_details': {}, 'output_token_details': {'reasoning': 11}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================

LangGraph 是一个用于构建有状态、可编排的 AI 代理和复杂工作流的框架，特别适合将 LLM 应用建模为图结构，支持循环、分支和人工介入。它由 LangChain 团队开发，可以看作 LangChain 的扩展层——LangChain 提供组件和工具，而 LangGraph 负责控制流程和状态管理，两者常结合使用。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "LangGraph 是一个用于构建有状态、可编排的 AI 代理和复杂工作流的框架，特别适合将 LLM 应用建模为图结构，支持循环、分支和人工介入。它由 LangChain 团队开发，可以看作 LangChain 的扩展层——LangChain 提供组件和工具，而 LangGraph 负责控制流程和状态管理，两者常结合使用。",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 94,
      "prompt_tokens": 124,
      "total_tokens": 218,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 11,
        "rejected_prediction_tokens": null,
        "text_tokens": 83
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "4842ebd3a8124866908b68c4a4af9224",
    "finish_reason": "stop",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a134f8-bff1-7211-83bb-e6a68f012e42-0",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 124,
    "output_tokens": 94,
    "total_tokens": 218,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 11
    }
  }
}
````

### 最终回答（最后一条 AI 消息的 content）

````text
LangGraph 是一个用于构建有状态、可编排的 AI 代理和复杂工作流的框架，特别适合将 LLM 应用建模为图结构，支持循环、分支和人工介入。它由 LangChain 团队开发，可以看作 LangChain 的扩展层——LangChain 提供组件和工具，而 LangGraph 负责控制流程和状态管理，两者常结合使用。
````

## 【2】stream 默认模式（values）：每步吐一次完整状态快照

`app.stream(input)` 不传 stream_mode 时默认 `stream_mode="values"`：每执行完一个「超级步」就把**全量状态**复制一份吐出来。观察点是消息列表逐步变长、question 键从无到有。

本次共 yield **3** 个快照（1 个输入态 + 每个节点执行后各 1 个），逐一全量导出：

#### 快照 1/3

- 顶层键：`['messages']`
- messages 共 1 条，序列：`HumanMessage`
- question：（此键还不存在）

完整快照（全量 JSON，一个字段不省略）：

````json
{
  "messages": [
    {
      "content": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "human",
      "name": null,
      "id": "55f523a0-0311-420c-8f6f-11cbdbefd3f5"
    }
  ]
}
````

#### 快照 2/3

- 顶层键：`['messages', 'question']`
- messages 共 2 条，序列：`HumanMessage` -> `SystemMessage`
- question：`'用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系'`

完整快照（全量 JSON，一个字段不省略）：

````json
{
  "messages": [
    {
      "content": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "human",
      "name": null,
      "id": "55f523a0-0311-420c-8f6f-11cbdbefd3f5"
    },
    {
      "content": "请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "system",
      "name": null,
      "id": "ee43d2ad-dc36-4cdb-9450-e193600fd644"
    }
  ],
  "question": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系"
}
````

#### 快照 3/3

- 顶层键：`['messages', 'question']`
- messages 共 3 条，序列：`HumanMessage` -> `SystemMessage` -> `AIMessage`
- question：`'用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系'`

完整快照（全量 JSON，一个字段不省略）：

````json
{
  "messages": [
    {
      "content": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "human",
      "name": null,
      "id": "55f523a0-0311-420c-8f6f-11cbdbefd3f5"
    },
    {
      "content": "请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "additional_kwargs": {},
      "response_metadata": {},
      "type": "system",
      "name": null,
      "id": "ee43d2ad-dc36-4cdb-9450-e193600fd644"
    },
    {
      "content": "LangGraph 是一个用于构建有状态、可编排的 AI 代理和复杂工作流的框架，特别适合实现多步骤、带循环和条件分支的图结构流程。它是 LangChain 生态的一部分，基于 LangChain 的组件构建，但更专注于底层状态机式的执行控制，而 LangChain 则提供模型/工具集成等基础能力。简单说，LangGraph 是 LangChain 的“编排层”，适合需要精细控制流程的复杂场景。",
      "additional_kwargs": {
        "refusal": null
      },
      "response_metadata": {
        "token_usage": {
          "completion_tokens": 112,
          "prompt_tokens": 124,
          "total_tokens": 236,
          "completion_tokens_details": {
            "accepted_prediction_tokens": null,
            "audio_tokens": null,
            "reasoning_tokens": 11,
            "rejected_prediction_tokens": null,
            "text_tokens": 101
          },
          "prompt_tokens_details": null
        },
        "model_provider": "openai",
        "model_name": "deepseek-v4-flash-sz",
        "system_fingerprint": null,
        "id": "f3b1fd432c0d4dd08530e1e5991f20f1",
        "finish_reason": "stop",
        "logprobs": null
      },
      "type": "ai",
      "name": null,
      "id": "lc_run--01a134f8-c2f2-7680-8591-2d1645b15da1-0",
      "tool_calls": [],
      "invalid_tool_calls": [],
      "usage_metadata": {
        "input_tokens": 124,
        "output_tokens": 112,
        "total_tokens": 236,
        "input_token_details": {},
        "output_token_details": {
          "reasoning": 11
        }
      }
    }
  ],
  "question": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系"
}
````

观察点：每个快照都是**全量复制**（后面的快照包含前面快照的全部消息，重复是真实形态，不是导出 bug）；所以图大、消息多时 values 流很冗长，只想看「谁贡献了什么」应该用 updates 视图（下一章）。

## 【3】stream_mode="updates"：每个节点执行完，上报一次增量

updates 视图每步 yield `{节点名: {增量字段}}`，上报的只是**注册节点**：图结构里虽自动补了 `__start__`/`__end__` 虚拟节点（见【0】），但本版本实测 updates 流不把输入单独上报——输入经 add_messages 直接并入初始状态，不出现在任何步骤里。

### 第 1 步 ｜ 上报节点：`prepare`

- 增量键：`['question', 'messages']`（只含该节点 return 的字段，不是全量状态）
- 产出 `SystemMessage`：prepare 节点追加的系统提示（验证 add_messages 的「追加」语义）

可读全文（pretty_repr）：

````text
================================ System Message ================================

请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "system",
  "name": null,
  "id": "a62ecaa2-dd7d-4283-aab5-56be912485f1"
}
````
- question 增量值：`用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系`

### 第 2 步 ｜ 上报节点：`call_llm`

- 增量键：`['messages']`（只含该节点 return 的字段，不是全量状态）
- 产出 `AIMessage`：call_llm 节点调 LLM 得到的回复
- token 用量：`{'input_tokens': 124, 'output_tokens': 106, 'total_tokens': 230, 'input_token_details': {}, 'output_token_details': {'reasoning': 24}}`

可读全文（pretty_repr）：

````text
================================== Ai Message ==================================

LangGraph 是一个用于构建有状态、可编排的智能体（Agent）应用的框架，它通过图结构来管理复杂的工作流、循环和分支，特别适合需要精细控制状态的 LLM 应用。它基于 LangChain 构建，可以视为 LangChain 的扩展，专注于把 LangChain 的组件（如工具、模型）编排成多步骤的图任务。
````

完整字段（model_dump，一个字段不省略）：

````json
{
  "content": "LangGraph 是一个用于构建有状态、可编排的智能体（Agent）应用的框架，它通过图结构来管理复杂的工作流、循环和分支，特别适合需要精细控制状态的 LLM 应用。它基于 LangChain 构建，可以视为 LangChain 的扩展，专注于把 LangChain 的组件（如工具、模型）编排成多步骤的图任务。",
  "additional_kwargs": {},
  "response_metadata": {
    "finish_reason": "stop",
    "model_name": "deepseek-v4-flash-sz",
    "model_provider": "openai"
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 124,
    "output_tokens": 106,
    "total_tokens": 230,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 24
    }
  }
}
````

### 完整步骤序列（原样一体化导出，一个字段不省略）

本视图本次共上报 2 个步骤对象，完整 JSON 已写入本文件。

````json
[
  {
    "prepare": {
      "question": "用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
      "messages": [
        {
          "content": "请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
          "additional_kwargs": {},
          "response_metadata": {},
          "type": "system",
          "name": null,
          "id": "a62ecaa2-dd7d-4283-aab5-56be912485f1"
        }
      ]
    }
  },
  {
    "call_llm": {
      "messages": [
        {
          "content": "LangGraph 是一个用于构建有状态、可编排的智能体（Agent）应用的框架，它通过图结构来管理复杂的工作流、循环和分支，特别适合需要精细控制状态的 LLM 应用。它基于 LangChain 构建，可以视为 LangChain 的扩展，专注于把 LangChain 的组件（如工具、模型）编排成多步骤的图任务。",
          "additional_kwargs": {},
          "response_metadata": {
            "finish_reason": "stop",
            "model_name": "deepseek-v4-flash-sz",
            "model_provider": "openai"
          },
          "type": "ai",
          "name": null,
          "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
          "tool_calls": [],
          "invalid_tool_calls": [],
          "usage_metadata": {
            "input_tokens": 124,
            "output_tokens": 106,
            "total_tokens": 230,
            "input_token_details": {},
            "output_token_details": {
              "reasoning": 24
            }
          }
        }
      ]
    }
  }
]
````

## 【4】stream_mode="messages"：token 级分片（与【3】同一轮执行）

messages 视图转发的是 LLM 的流式事件：每个 yield 是 `(消息对象, metadata)` 二元组。本章先给类型分布与来源节点统计，再按 yield 原始顺序逐事件全量导出。

### 总览

- 事件总数：**47**，类型分布：`{'SystemMessage': 1, 'AIMessageChunk': 46}`
- 事件来源节点：`['call_llm', 'prepare']`
- 其中 HumanMessage（invoke 的输入）0 条；SystemMessage（prepare 节点 return 的）1 条
- 解读：messages 流 = LLM 的 token 分片（逐片转发）+ **节点 return 的消息（完整形态转发，无分片过程）**；invoke 的输入消息不属于任何节点的产出，不进此流（看它请用 values / updates 视图）
- 对照：同一轮执行里 updates 只上报 2 步，messages 却有 47 个事件——分片是「原料」，节点增量是「成品」。

### 先解剖一次 yield：`(message, metadata)` 的完整实例

````text
('messages', (SystemMessage(content='请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系', additional_kwargs={}, response_metadata={}, id='a62ecaa2-dd7d-4283-aab5-56be912485f1'), {'langgraph_step': 1, 'langgraph_node': 'prepare', 'langgraph_triggers': ('branch:to:prepare',), 'langgraph_path': ('__pregel_pull', 'prepare'), 'langgraph_checkpoint_ns': 'prepare:84e3ac2e-4ffe-3404-80c1-bc98bb40ffb2'}))
````

逐层分解：`mode` = `'messages'`；`payload` 是二元组；第 1 项 message 是 `langchain_core.messages.system.SystemMessage`（节点 return 的完整消息（非分片，完整形态直接转发）），第 2 项 metadata 是 `dict`，键：`['langgraph_step', 'langgraph_node', 'langgraph_triggers', 'langgraph_path', 'langgraph_checkpoint_ns']`。

### 逐事件全量导出（按流的原始结构，一个字段不省略）

按 yield 的原始顺序，把全部 47 个事件原样端出。每个事件的第 1 项是消息对象（真实类型全路径 + 原始 repr + 全字段 model_dump），第 2 项是 metadata（真实流中每个事件都重复携带一份，不提取到组外）。

#### 事件 1/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.system.SystemMessage`
- 原始 repr（Python 对对象的原样打印）：

````text
SystemMessage(content='请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系', additional_kwargs={}, response_metadata={}, id='a62ecaa2-dd7d-4283-aab5-56be912485f1')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "请围绕用户问题用中文简短回答：用两三句话介绍一下 LangGraph 是什么、它和 LangChain 是什么关系",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "system",
  "name": null,
  "id": "a62ecaa2-dd7d-4283-aab5-56be912485f1"
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 1,
  "langgraph_node": "prepare",
  "langgraph_triggers": [
    "branch:to:prepare"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "prepare"
  ],
  "langgraph_checkpoint_ns": "prepare:84e3ac2e-4ffe-3404-80c1-bc98bb40ffb2"
}
````

#### 事件 2/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 3/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 4/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 5/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 6/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 7/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 8/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 9/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 10/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 11/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 12/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 13/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='LangGraph ', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "LangGraph ",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 14/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='是一个用于构建有', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "是一个用于构建有",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 15/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='状态、', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "状态、",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 16/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='可编排', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "可编排",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 17/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='的', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "的",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 18/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='智能体（', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "智能体（",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 19/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='Agent）应用的框架，', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "Agent）应用的框架，",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 20/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='它', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "它",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 21/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='通过', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "通过",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 22/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='图结构', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "图结构",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 23/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='来管理复杂', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "来管理复杂",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 24/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='的工作', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "的工作",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 25/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='流、循环', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "流、循环",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 26/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='和分支', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "和分支",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 27/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='，特别', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "，特别",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 28/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='适合需要', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "适合需要",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 29/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='精细', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "精细",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 30/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='控制状态的 LLM ', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "控制状态的 LLM ",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 31/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='应用。它', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "应用。它",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 32/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='基于', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "基于",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 33/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' LangChain 构建', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " LangChain 构建",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 34/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='，可以', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "，可以",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 35/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='视为', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "视为",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 36/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' LangChain 的扩展', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " LangChain 的扩展",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 37/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='，专注于', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "，专注于",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 38/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='把', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "把",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 39/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content=' LangChain 的', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": " LangChain 的",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 40/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='组件（', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "组件（",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 41/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='如工具、', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "如工具、",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 42/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='模型）编排成', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "模型）编排成",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 43/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='多步骤', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "多步骤",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 44/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='的图任务。', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "的图任务。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 45/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'finish_reason': 'stop', 'model_name': 'deepseek-v4-flash-sz', 'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 46/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={'model_provider': 'openai'}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 124, 'output_tokens': 106, 'total_tokens': 230, 'input_token_details': {}, 'output_token_details': {'reasoning': 24}}, tool_call_chunks=[])
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
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 124,
    "output_tokens": 106,
    "total_tokens": 230,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 24
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
````

**【第 2 项】metadata（本事件原样携带）：**

````json
{
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````

#### 事件 47/47

**原始结构 = `(message, metadata)` 二元组，两项如下：**

**【第 1 项】message：**

- 真实类型：`langchain_core.messages.ai.AIMessageChunk`
- 原始 repr（Python 对对象的原样打印）：

````text
AIMessageChunk(content='', additional_kwargs={}, response_metadata={}, id='lc_run--01a134f8-c562-7033-a714-67e2d141ccb1', tool_calls=[], invalid_tool_calls=[], tool_call_chunks=[], chunk_position='last')
````
- 完整字段（model_dump，一个不省略）：

````json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a134f8-c562-7033-a714-67e2d141ccb1",
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
  "langgraph_step": 2,
  "langgraph_node": "call_llm",
  "langgraph_triggers": [
    "branch:to:call_llm"
  ],
  "langgraph_path": [
    "__pregel_pull",
    "call_llm"
  ],
  "langgraph_checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "checkpoint_ns": "call_llm:9af14401-a725-1488-ff54-d616157f5195",
  "ls_provider": "openai",
  "ls_model_name": "deepseek-v4-flash-sz",
  "ls_model_type": "chat",
  "ls_temperature": null
}
````


## 【5】聚合校验：messages 分片用 + 拼回，与 updates 里的完整消息对照

聚合方式即 merge_chunks_demo.py 演示过的 `reduce(operator.add, chunks)`：content 首尾相接、usage 随末块合并。注意 `+` 只对 `AIMessageChunk` 成立（普通消息的 `+` 是「拼进 ChatPromptTemplate」的语义）。

- call_llm 节点共 yield 46 个 token 分片，`reduce(operator.add, ...)` 拼回 1 个 `AIMessageChunk`
- 与 updates 视图里 call_llm 上报的完整 AIMessage 逐项对照：
  - id 一致：**是**（`lc_run--01a134f8-c562-7033-a714-67e2d141ccb1`）
  - content 一致：**是**（157 字）
  - usage_metadata 一致：**是**
  - response_metadata.model_name 一致：**是**

结论：messages 视图的分片就是 updates 视图完整消息的「原料」，两种视图来自同一轮执行，可互相还原。

## 附一：四种视图差异速查

| 调用形态 | yield / 返回的东西 | 粒度 | 典型用途 |
| --- | --- | --- | --- |
| `app.invoke(input)` | 一次性返回**最终状态 dict** | 无流 | 只要最终结果 |
| `app.stream(input)`（values 默认） | 每步一个**完整状态快照** | 超级步 | 观察状态演变、调试 |
| `stream_mode="updates"` | 每步 `{节点名: 增量dict}` | 节点 | 看每个节点贡献了什么 |
| `stream_mode="messages"` | 每事件 `(消息对象, metadata)` | token | 打字机效果、TTFT 观测 |

- 同一次 stream 可传列表组合采集：`stream_mode=["updates", "messages"]`，此时每个 yield 变成 `(mode, payload)` 二元组（本报告【3】【4】即同轮数据）。
- invoke 返回的**不是消息**而是最终状态：拿回答要用 `result["messages"][-1]`。
- `__start__` / `__end__` 只存在于编译后的图结构（get_graph）里；本版本实测 updates 流只上报注册节点，invoke 的输入不单独上报
- 与 simple_agent.py（create_agent）的关系：create_agent 底层就是 LangGraph，本报告的输出结构与那边完全同构，只是图形状更简单（无工具循环）。

## 附二：LangGraph 概念速查（本文件对应代码）

- `StateGraph(State)`：以 State 为 schema 建图（builder）
- `add_node("名字", 函数)`：注册节点；函数签名 `(state) -> dict`，返回值是状态增量
- `add_edge(START, "a")` / `add_edge("a", "b")` / `add_edge("b", END)`：连线
- reducer（`Annotated[list, add_messages]`）：同名键多处写入时的合并规则；没标 reducer 的键就是后写覆盖
- `compile()`：图编译成 Runnable，之后 invoke / stream / astream 与普通 LangChain 组件一致
