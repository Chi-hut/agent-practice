# 流式输出返回值与前后端解析实测报告

## 第 1 层：模型网关原始 SSE 报文 vs LangChain 的 AIMessageChunk（同一次响应）

- 提问：`用三句话介绍你自己`
- HTTP 状态：200，响应 content-type：`text/event-stream; charset=utf-8`
- 原始 body 总行数 58，其中 `data:` 行 29 条（含 `[DONE]`），JSON 事件 28 个
- LangChain `llm.stream()` 产出分块 29 个，类型：['AIMessageChunk']

### 1.1 LangChain 实际发出的请求体

```json
{
  "messages": [
    {
      "content": "用三句话介绍你自己",
      "role": "user"
    }
  ],
  "model": "deepseek-v4-flash-sz",
  "stream": true
}
```

### 1.2 网关返回的原始响应体（逐字，未做任何处理）

```text
data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"","role":"assistant"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning_content":"We"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning_content":" need answer in Chinese. Need"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning_content":" three sentences intro"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning_content":"."}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning_content":" Keep"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"reasoning_content":" concise."}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"我是"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" Deep"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Seek，一个由"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"深度求索公司创造的"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" AI"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" 助手。"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"我"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"擅长回答"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"各种问题、"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"提供信息"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"，"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"并帮助处理"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"学习和"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"工作中的"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"任务。很高兴"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"认识"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"你，有任何"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"需要"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"随时找我！"}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"finish_reason":"stop","index":0,"delta":{}}]}

data: {"id":"810ef23dce174d11b7a5f5bcda1c936c","created":1792587488,"model":"deepseek-v4-flash-sz","object":"chat.completion.chunk","choices":[{"index":0,"delta":{}}],"usage":{"completion_tokens":57,"prompt_tokens":88,"total_tokens":145,"completion_tokens_details":{"reasoning_tokens":15,"text_tokens":42}}}

data: [DONE]


```

### 1.3 对照表：每个 SSE 事件的 delta / finish_reason / usage  ↔  对应分块的非空字段

| # | SSE choices[0].delta | SSE finish_reason | SSE usage | chunk.content | chunk 其他非空字段 |
|---|---|---|---|---|---|
| 1 | {"content": "", "role": "assistant"} | null | null | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 2 | {"reasoning_content": "We"} | null | null | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 3 | {"reasoning_content": " need answer in Chinese. Need"} | null | null | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 4 | {"reasoning_content": " three sentences intro"} | null | null | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 5 | {"reasoning_content": "."} | null | null | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 6 | {"reasoning_content": " Keep"} | null | null | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 7 | {"reasoning_content": " concise."} | null | null | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 8 | {"content": "我是"} | null | null | "我是" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 9 | {"content": " Deep"} | null | null | " Deep" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 10 | {"content": "Seek，一个由"} | null | null | "Seek，一个由" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 11 | {"content": "深度求索公司创造的"} | null | null | "深度求索公司创造的" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 12 | {"content": " AI"} | null | null | " AI" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 13 | {"content": " 助手。"} | null | null | " 助手。" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 14 | {"content": "我"} | null | null | "我" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 15 | {"content": "擅长回答"} | null | null | "擅长回答" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 16 | {"content": "各种问题、"} | null | null | "各种问题、" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 17 | {"content": "提供信息"} | null | null | "提供信息" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 18 | {"content": "，"} | null | null | "，" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 19 | {"content": "并帮助处理"} | null | null | "并帮助处理" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 20 | {"content": "学习和"} | null | null | "学习和" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 21 | {"content": "工作中的"} | null | null | "工作中的" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 22 | {"content": "任务。很高兴"} | null | null | "任务。很高兴" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 23 | {"content": "认识"} | null | null | "认识" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 24 | {"content": "你，有任何"} | null | null | "你，有任何" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 25 | {"content": "需要"} | null | null | "需要" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 26 | {"content": "随时找我！"} | null | null | "随时找我！" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 27 | {} | "stop" | null | "" | {"response_metadata": {"finish_reason": "stop", "model_name": "deepseek-v4-flash-sz", "model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8"} |
| 28 | {} | null | {"completion_tokens": 57, "prompt_tokens": 88, "total_tokens": 145, "completion_tokens_details": {"reasoning_tokens": 15, "text_tokens": 42}} | "" | {"response_metadata": {"model_provider": "openai"}, "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8", "usage_metadata": {"input_tokens": 88, "output_tokens": 57, "total_tokens": 145, "input_token_details": {}, "output_token_details": {"reasoning": 15}}} |
| 29 | - | - | - | "" | {"id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8", "chunk_position": "last"} |

### 1.4 每个分块 `chunk.model_dump()` 全字段（逐个）

#### 分块 1（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 2（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 3（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 4（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 5（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 6（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 7（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 8（AIMessageChunk）

```json
{
  "content": "我是",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 9（AIMessageChunk）

```json
{
  "content": " Deep",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 10（AIMessageChunk）

```json
{
  "content": "Seek，一个由",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 11（AIMessageChunk）

```json
{
  "content": "深度求索公司创造的",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 12（AIMessageChunk）

```json
{
  "content": " AI",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 13（AIMessageChunk）

```json
{
  "content": " 助手。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 14（AIMessageChunk）

```json
{
  "content": "我",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 15（AIMessageChunk）

```json
{
  "content": "擅长回答",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 16（AIMessageChunk）

```json
{
  "content": "各种问题、",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 17（AIMessageChunk）

```json
{
  "content": "提供信息",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 18（AIMessageChunk）

```json
{
  "content": "，",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 19（AIMessageChunk）

```json
{
  "content": "并帮助处理",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 20（AIMessageChunk）

```json
{
  "content": "学习和",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 21（AIMessageChunk）

```json
{
  "content": "工作中的",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 22（AIMessageChunk）

```json
{
  "content": "任务。很高兴",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 23（AIMessageChunk）

```json
{
  "content": "认识",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 24（AIMessageChunk）

```json
{
  "content": "你，有任何",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 25（AIMessageChunk）

```json
{
  "content": "需要",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 26（AIMessageChunk）

```json
{
  "content": "随时找我！",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 27（AIMessageChunk）

```json
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
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 28（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 88,
    "output_tokens": 57,
    "total_tokens": 145,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 15
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
```

#### 分块 29（AIMessageChunk）

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": "last"
}
```

### 1.5 所有分块用 `+` 累加后的完整消息 `full.model_dump()`

类型：AIMessageChunk

```json
{
  "content": "我是 DeepSeek，一个由深度求索公司创造的 AI 助手。我擅长回答各种问题、提供信息，并帮助处理学习和工作中的任务。很高兴认识你，有任何需要随时找我！",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai",
    "finish_reason": "stop",
    "model_name": "deepseek-v4-flash-sz"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a15e8a-5b34-7100-aad7-083c18b74fd8",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 88,
    "output_tokens": 57,
    "total_tokens": 145,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 15
    }
  },
  "tool_call_chunks": [],
  "chunk_position": "last"
}
```

## 第 2 层：自己的 FastAPI 后端转发 → Python 客户端解析

- 接口：`POST /chat/stream`，状态 200，content-type：`text/event-stream; charset=utf-8`
- 网络读取次数 18，解析出事件 18 个：delta=17，done=1

### 2.1 客户端每次从网络读到的原始文本（含到达时间，逐字）

| # | 到达 ms | 原始文本 |
|---|---|---|
| 1 | 1121 | "event: delta\ndata: {\"text\": \"我是Deep\"}\n\n" |
| 2 | 1131 | "event: delta\ndata: {\"text\": \"Seek，由\"}\n\n" |
| 3 | 1141 | "event: delta\ndata: {\"text\": \"深度求索公司创造的AI\"}\n\n" |
| 4 | 1154 | "event: delta\ndata: {\"text\": \"助手。我\"}\n\n" |
| 5 | 1161 | "event: delta\ndata: {\"text\": \"擅长解答\"}\n\n" |
| 6 | 1176 | "event: delta\ndata: {\"text\": \"问题、\"}\n\n" |
| 7 | 1183 | "event: delta\ndata: {\"text\": \"处理\"}\n\n" |
| 8 | 1198 | "event: delta\ndata: {\"text\": \"文本\"}\n\n" |
| 9 | 1203 | "event: delta\ndata: {\"text\": \"和提供\"}\n\n" |
| 10 | 1214 | "event: delta\ndata: {\"text\": \"实用\"}\n\n" |
| 11 | 1231 | "event: delta\ndata: {\"text\": \"信息。我会\"}\n\n" |
| 12 | 1241 | "event: delta\ndata: {\"text\": \"用热情细腻\"}\n\n" |
| 13 | 1246 | "event: delta\ndata: {\"text\": \"的方式，陪你\"}\n\n" |
| 14 | 1254 | "event: delta\ndata: {\"text\": \"探索\"}\n\n" |
| 15 | 1268 | "event: delta\ndata: {\"text\": \"各种\"}\n\n" |
| 16 | 1282 | "event: delta\ndata: {\"text\": \"话题\"}\n\n" |
| 17 | 1310 | "event: delta\ndata: {\"text\": \"。\"}\n\n" |
| 18 | 1532 | "event: done\ndata: {\"id\": \"lc_run--01a15e8a-5fe0-7fb2-b512-4f41a3f7bcaf\", \"finish_reason\": \"stop\", \"usage\": {\"input_tokens\": 88, \"output_tokens\": 60, \"total_tokens\": 148, \"input_token_details\": {}, \"output_token_details\": {\"reasoning\": 22}}}\n\n" |

### 2.2 解析后的事件序列

| # | 到达 ms | event | payload |
|---|---|---|---|
| 1 | 1121 | delta | {"text": "我是Deep"} |
| 2 | 1131 | delta | {"text": "Seek，由"} |
| 3 | 1141 | delta | {"text": "深度求索公司创造的AI"} |
| 4 | 1154 | delta | {"text": "助手。我"} |
| 5 | 1161 | delta | {"text": "擅长解答"} |
| 6 | 1176 | delta | {"text": "问题、"} |
| 7 | 1183 | delta | {"text": "处理"} |
| 8 | 1198 | delta | {"text": "文本"} |
| 9 | 1203 | delta | {"text": "和提供"} |
| 10 | 1214 | delta | {"text": "实用"} |
| 11 | 1231 | delta | {"text": "信息。我会"} |
| 12 | 1241 | delta | {"text": "用热情细腻"} |
| 13 | 1246 | delta | {"text": "的方式，陪你"} |
| 14 | 1254 | delta | {"text": "探索"} |
| 15 | 1268 | delta | {"text": "各种"} |
| 16 | 1282 | delta | {"text": "话题"} |
| 17 | 1310 | delta | {"text": "。"} |
| 18 | 1532 | done | {"id": "lc_run--01a15e8a-5fe0-7fb2-b512-4f41a3f7bcaf", "finish_reason": "stop", "usage": {"input_tokens": 88, "output_tokens": 60, "total_tokens": 148, "input_token_details": {}, "output_token_details": {"reasoning": 22}}} |

### 2.3 客户端拼回的完整回答

```text
我是DeepSeek，由深度求索公司创造的AI助手。我擅长解答问题、处理文本和提供实用信息。我会用热情细腻的方式，陪你探索各种话题。
```

## 第 3 层：浏览器前端 fetch + ReadableStream 解析（真实浏览器运行）

- 页面：后端 `GET /` 返回的 HTML，点击发送后调用 `POST /chat/stream`；流结束标记 `__finished=True`
- reader.read() 次数 16，解析事件 16 个

### 3.1 每次 reader.read() 读到的原始文本

| # | 到达 ms | 字节数 | 原始文本 |
|---|---|---|---|
| 1 | 357 | 39 | "event: delta\ndata: {\"text\": \"我是\"}\n\n" |
| 2 | 373 | 44 | "event: delta\ndata: {\"text\": \"DeepSeek，\"}\n\n" |
| 3 | 376 | 36 | "event: delta\ndata: {\"text\": \"由\"}\n\n" |
| 4 | 390 | 62 | "event: delta\ndata: {\"text\": \"深度求索公司创造的AI\"}\n\n" |
| 5 | 404 | 45 | "event: delta\ndata: {\"text\": \"助手。我\"}\n\n" |
| 6 | 406 | 51 | "event: delta\ndata: {\"text\": \"擅长回答问题\"}\n\n" |
| 7 | 419 | 48 | "event: delta\ndata: {\"text\": \"、提供信息\"}\n\n" |
| 8 | 428 | 48 | "event: delta\ndata: {\"text\": \"并协助解决\"}\n\n" |
| 9 | 438 | 39 | "event: delta\ndata: {\"text\": \"各类\"}\n\n" |
| 10 | 447 | 39 | "event: delta\ndata: {\"text\": \"任务\"}\n\n" |
| 11 | 460 | 45 | "event: delta\ndata: {\"text\": \"。我乐于\"}\n\n" |
| 12 | 468 | 36 | "event: delta\ndata: {\"text\": \"用\"}\n\n" |
| 13 | 490 | 39 | "event: delta\ndata: {\"text\": \"清晰\"}\n\n" |
| 14 | 491 | 57 | "event: delta\ndata: {\"text\": \"、友好的方式为你\"}\n\n" |
| 15 | 508 | 42 | "event: delta\ndata: {\"text\": \"服务。\"}\n\n" |
| 16 | 511 | 242 | "event: done\ndata: {\"id\": \"lc_run--01a15e8a-be09-75c0-a38e-03ada8450a9a\", \"finish_reason\": \"stop\", \"usage\": {\"input_tokens\": 88, \"output_tokens\": 55, \"total_tokens\": 143, \"input_token_details\": {}, \"output_token_details\": {\"reasoning\": 18}}}\n\n" |

### 3.2 解析后的事件序列

| # | 到达 ms | event | payload |
|---|---|---|---|
| 1 | 357 | delta | {"text": "我是"} |
| 2 | 373 | delta | {"text": "DeepSeek，"} |
| 3 | 376 | delta | {"text": "由"} |
| 4 | 390 | delta | {"text": "深度求索公司创造的AI"} |
| 5 | 404 | delta | {"text": "助手。我"} |
| 6 | 406 | delta | {"text": "擅长回答问题"} |
| 7 | 420 | delta | {"text": "、提供信息"} |
| 8 | 428 | delta | {"text": "并协助解决"} |
| 9 | 438 | delta | {"text": "各类"} |
| 10 | 447 | delta | {"text": "任务"} |
| 11 | 460 | delta | {"text": "。我乐于"} |
| 12 | 468 | delta | {"text": "用"} |
| 13 | 490 | delta | {"text": "清晰"} |
| 14 | 491 | delta | {"text": "、友好的方式为你"} |
| 15 | 508 | delta | {"text": "服务。"} |
| 16 | 511 | done | {"id": "lc_run--01a15e8a-be09-75c0-a38e-03ada8450a9a", "finish_reason": "stop", "usage": {"input_tokens": 88, "output_tokens": 55, "total_tokens": 143, "input_token_details": {}, "output_token_details": {"reasoning": 18}}} |

### 3.3 页面最终渲染

```text
我是DeepSeek，由深度求索公司创造的AI助手。我擅长回答问题、提供信息并协助解决各类任务。我乐于用清晰、友好的方式为你服务。

finish_reason=stop  usage={"input_tokens":88,"output_tokens":55,"total_tokens":143,"input_token_details":{},"output_token_details":{"reasoning":18}}
```

## 附：本次实验使用的后端 + 前端完整代码（stream_server.py）

```python
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent.llm import llm

app = FastAPI()


class ChatReq(BaseModel):
    question: str


def sse(event: str, data: dict) -> str:
    # data 必须 JSON 编码：模型输出里的换行会被转义成 \n，否则会提前截断一个 SSE 事件
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
async def chat_stream(req: ChatReq):
    async def gen():
        finish_reason, usage, msg_id = None, None, None
        try:
            async for chunk in llm.astream([HumanMessage(req.question)]):
                msg_id = msg_id or chunk.id
                reasoning = chunk.additional_kwargs.get("reasoning_content")
                if reasoning:
                    yield sse("reasoning", {"text": reasoning})
                if chunk.content:
                    yield sse("delta", {"text": chunk.content})
                finish_reason = chunk.response_metadata.get("finish_reason") or finish_reason
                usage = chunk.usage_metadata or usage
            yield sse("done", {"id": msg_id, "finish_reason": finish_reason, "usage": usage})
        except Exception as e:
            yield sse("error", {"message": str(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>stream demo</title>
<style>body{font-family:sans-serif;max-width:860px;margin:24px auto}
#out{white-space:pre-wrap;border:1px solid #ccc;padding:12px;min-height:160px}
#meta{color:#666;font-size:13px;margin-top:8px}</style></head>
<body>
<input id="q" value="用三句话介绍你自己" style="width:70%">
<button id="go" onclick="run()">发送</button>
<div id="out"></div><div id="meta"></div>
<script>
async function run() {
  const out = document.getElementById('out'), meta = document.getElementById('meta');
  out.textContent = ''; meta.textContent = '';
  window.__events = []; window.__rawReads = []; window.__finished = false;
  const t0 = performance.now();
  const resp = await fetch('/chat/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: document.getElementById('q').value})
  });
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    const text = decoder.decode(value, {stream: true});
    window.__rawReads.push({t: Math.round(performance.now() - t0), bytes: value.length, text});
    buf += text;
    let idx;
    while ((idx = buf.indexOf('\\n\\n')) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = 'message', data = '';
      for (const line of block.split('\\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data += line.slice(5).trim();
      }
      const payload = JSON.parse(data);
      window.__events.push({t: Math.round(performance.now() - t0), event, payload});
      if (event === 'delta') out.textContent += payload.text;
      else if (event === 'done') meta.textContent = 'finish_reason=' + payload.finish_reason + '  usage=' + JSON.stringify(payload.usage);
      else if (event === 'error') meta.textContent = '出错: ' + payload.message;
    }
  }
  window.__finished = true;
}
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return PAGE

```
