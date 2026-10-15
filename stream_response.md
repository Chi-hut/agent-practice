# stream 流式响应全量信息

- 采集时间：2026-10-13 16:24:12
- 模型：`deepseek-v4-flash-sz`
- 问题：用 300 字左右介绍一下你自己，并说明你能帮我做什么
- 分块数量：**103** 个
- 首块到达：4.05s ｜ 总耗时：5.32s
- 拼接后内容长度：381 字
- 拼接方式：`chunks[0] + chunks[1] + ... + chunks[n]` → `AIMessageChunk`

## 一、全部分块累加后的完整消息（最核心的一份）

类型：`AIMessageChunk`，content 已是完整文本，token 用量随末块回传：

```json
{
  "content": "你好！我是 DeepSeek，一个由深度求索公司开发的 AI 助手。我拥有强大的自然语言理解和生成能力，能够处理各种文本任务，也可以阅读链接和上传的文件（包括图片、PDF、Word、Excel 等），从中提取信息并帮你分析。我支持超长上下文，一次能处理像《三体》三部曲那么大的内容量，适合总结文档、对比观点、梳理知识框架等。\n\n我能帮你做什么呢？比如：写作和润色文章、翻译语言、编写或调试代码、解答学习问题、整理资料、分析数据、提供创意建议，甚至陪你闲聊讨论话题。我还会根据你的需求进行深度思考，用你使用的语言来回复，力求准确、清晰、有条理。\n\n此外，我支持联网搜索（需要你在网页或 App 上手动开启），可以帮你获取最新信息。最关键的是，我是完全免费的，你可以随时向我提问，不用担心次数限制。希望我能成为你学习、工作和生活中的得力助手！有任何需要，随时告诉我。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai",
    "finish_reason": "stop",
    "model_name": "deepseek-v4-flash-sz"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 97,
    "output_tokens": 250,
    "total_tokens": 347,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 37
    }
  },
  "tool_call_chunks": [],
  "chunk_position": "last"
}
```

## 二、全部 103 个分块的完整信息（每块 model_dump 原样导出，无任何简化）

每一小节就是AIMessageChunk对象的全部字段，一个不省略。建议带着这几个问题逐块对比着看：

1. 每一块的 `id` 是否相同？
2. `content`：每块只多几个字？把所有增量按顺序连起来，是不是就得到了第一章的完整文本？
3. `usage_metadata`：前面的块是不是一直是 null？从哪一块开始出现 token 数字？
4. `chunk_position`：取值如何随分块推进（开头 / 中间 / 最后）？
5. `response_metadata`：中间块和最后一块的内容差别？

### 分块 1 ｜ t = 4.055s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 2 ｜ t = 4.055s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 3 ｜ t = 4.056s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 4 ｜ t = 4.059s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 5 ｜ t = 4.102s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 6 ｜ t = 4.102s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 7 ｜ t = 4.102s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 8 ｜ t = 4.113s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 9 ｜ t = 4.125s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 10 ｜ t = 4.158s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 11 ｜ t = 4.158s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 12 ｜ t = 4.162s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 13 ｜ t = 4.175s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 14 ｜ t = 4.213s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 15 ｜ t = 4.354s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 16 ｜ t = 4.425s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 17 ｜ t = 4.425s
增量 content：

```text
你好
```
完整字段：

```json
{
  "content": "你好",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 18 ｜ t = 4.425s
增量 content：

```text
！我是 DeepSeek，
```
完整字段：

```json
{
  "content": "！我是 DeepSeek，",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 19 ｜ t = 4.425s
增量 content：

```text
一个由深度求索公司
```
完整字段：

```json
{
  "content": "一个由深度求索公司",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 20 ｜ t = 4.425s
增量 content：

```text
开发的 AI 助手。
```
完整字段：

```json
{
  "content": "开发的 AI 助手。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 21 ｜ t = 4.425s
增量 content：

```text
我拥有
```
完整字段：

```json
{
  "content": "我拥有",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 22 ｜ t = 4.425s
增量 content：

```text
强大的自然
```
完整字段：

```json
{
  "content": "强大的自然",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 23 ｜ t = 4.425s
增量 content：

```text
语言理解和生成
```
完整字段：

```json
{
  "content": "语言理解和生成",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 24 ｜ t = 4.426s
增量 content：

```text
能力，能够处理各种文本
```
完整字段：

```json
{
  "content": "能力，能够处理各种文本",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 25 ｜ t = 4.426s
增量 content：

```text
任务，也可以
```
完整字段：

```json
{
  "content": "任务，也可以",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 26 ｜ t = 4.426s
增量 content：

```text
阅读
```
完整字段：

```json
{
  "content": "阅读",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 27 ｜ t = 4.426s
增量 content：

```text
链接
```
完整字段：

```json
{
  "content": "链接",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 28 ｜ t = 4.461s
增量 content：

```text
和
```
完整字段：

```json
{
  "content": "和",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 29 ｜ t = 4.461s
增量 content：

```text
上传的文件（
```
完整字段：

```json
{
  "content": "上传的文件（",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 30 ｜ t = 4.461s
增量 content：

```text
包括
```
完整字段：

```json
{
  "content": "包括",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 31 ｜ t = 4.462s
增量 content：

```text
图片、PDF、Word、
```
完整字段：

```json
{
  "content": "图片、PDF、Word、",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 32 ｜ t = 4.462s
增量 content：

```text
Excel 等），从中
```
完整字段：

```json
{
  "content": "Excel 等），从中",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 33 ｜ t = 4.489s
增量 content：

```text
提取信息
```
完整字段：

```json
{
  "content": "提取信息",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 34 ｜ t = 4.489s
增量 content：

```text
并帮你分析
```
完整字段：

```json
{
  "content": "并帮你分析",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 35 ｜ t = 4.489s
增量 content：

```text
。我支持
```
完整字段：

```json
{
  "content": "。我支持",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 36 ｜ t = 4.536s
增量 content：

```text
超长上下文，一次
```
完整字段：

```json
{
  "content": "超长上下文，一次",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 37 ｜ t = 4.536s
增量 content：

```text
能
```
完整字段：

```json
{
  "content": "能",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 38 ｜ t = 4.536s
增量 content：

```text
处理像
```
完整字段：

```json
{
  "content": "处理像",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 39 ｜ t = 4.566s
增量 content：

```text
《三体》三部曲
```
完整字段：

```json
{
  "content": "《三体》三部曲",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 40 ｜ t = 4.566s
增量 content：

```text
那么大的内容量
```
完整字段：

```json
{
  "content": "那么大的内容量",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 41 ｜ t = 4.566s
增量 content：

```text
，适合
```
完整字段：

```json
{
  "content": "，适合",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 42 ｜ t = 4.618s
增量 content：

```text
总结
```
完整字段：

```json
{
  "content": "总结",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 43 ｜ t = 4.618s
增量 content：

```text
文档
```
完整字段：

```json
{
  "content": "文档",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 44 ｜ t = 4.618s
增量 content：

```text
、对比
```
完整字段：

```json
{
  "content": "、对比",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 45 ｜ t = 4.618s
增量 content：

```text
观点
```
完整字段：

```json
{
  "content": "观点",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 46 ｜ t = 4.618s
增量 content：

```text
、梳理知识框架
```
完整字段：

```json
{
  "content": "、梳理知识框架",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 47 ｜ t = 4.720s
增量 content：

```text
等
```
完整字段：

```json
{
  "content": "等",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 48 ｜ t = 4.739s
增量 content：

```text
。

我能
```
完整字段：

```json
{
  "content": "。\n\n我能",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 49 ｜ t = 4.739s
增量 content：

```text
帮你做什么呢？比如
```
完整字段：

```json
{
  "content": "帮你做什么呢？比如",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 50 ｜ t = 4.739s
增量 content：

```text
：
```
完整字段：

```json
{
  "content": "：",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 51 ｜ t = 4.739s
增量 content：

```text
写作和
```
完整字段：

```json
{
  "content": "写作和",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 52 ｜ t = 4.739s
增量 content：

```text
润色文章
```
完整字段：

```json
{
  "content": "润色文章",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 53 ｜ t = 4.739s
增量 content：

```text
、翻译
```
完整字段：

```json
{
  "content": "、翻译",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 54 ｜ t = 4.754s
增量 content：

```text
语言
```
完整字段：

```json
{
  "content": "语言",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 55 ｜ t = 4.754s
增量 content：

```text
、编写
```
完整字段：

```json
{
  "content": "、编写",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 56 ｜ t = 4.754s
增量 content：

```text
或
```
完整字段：

```json
{
  "content": "或",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 57 ｜ t = 4.789s
增量 content：

```text
调试代码、解答
```
完整字段：

```json
{
  "content": "调试代码、解答",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 58 ｜ t = 4.789s
增量 content：

```text
学习
```
完整字段：

```json
{
  "content": "学习",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 59 ｜ t = 4.789s
增量 content：

```text
问题、整理资料
```
完整字段：

```json
{
  "content": "问题、整理资料",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 60 ｜ t = 4.794s
增量 content：

```text
、分析数据
```
完整字段：

```json
{
  "content": "、分析数据",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 61 ｜ t = 4.801s
增量 content：

```text
、提供
```
完整字段：

```json
{
  "content": "、提供",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 62 ｜ t = 4.821s
增量 content：

```text
创意
```
完整字段：

```json
{
  "content": "创意",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 63 ｜ t = 4.852s
增量 content：

```text
建议
```
完整字段：

```json
{
  "content": "建议",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 64 ｜ t = 4.852s
增量 content：

```text
，甚至陪你
```
完整字段：

```json
{
  "content": "，甚至陪你",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 65 ｜ t = 4.852s
增量 content：

```text
闲聊
```
完整字段：

```json
{
  "content": "闲聊",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 66 ｜ t = 4.862s
增量 content：

```text
讨论
```
完整字段：

```json
{
  "content": "讨论",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 67 ｜ t = 4.875s
增量 content：

```text
话题
```
完整字段：

```json
{
  "content": "话题",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 68 ｜ t = 4.886s
增量 content：

```text
。我还会
```
完整字段：

```json
{
  "content": "。我还会",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 69 ｜ t = 4.901s
增量 content：

```text
根据
```
完整字段：

```json
{
  "content": "根据",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 70 ｜ t = 4.910s
增量 content：

```text
你的需求进行
```
完整字段：

```json
{
  "content": "你的需求进行",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 71 ｜ t = 4.941s
增量 content：

```text
深度思考
```
完整字段：

```json
{
  "content": "深度思考",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 72 ｜ t = 4.942s
增量 content：

```text
，用
```
完整字段：

```json
{
  "content": "，用",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 73 ｜ t = 4.962s
增量 content：

```text
你
```
完整字段：

```json
{
  "content": "你",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 74 ｜ t = 4.968s
增量 content：

```text
使用的
```
完整字段：

```json
{
  "content": "使用的",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 75 ｜ t = 4.978s
增量 content：

```text
语言来
```
完整字段：

```json
{
  "content": "语言来",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 76 ｜ t = 4.989s
增量 content：

```text
回复，
```
完整字段：

```json
{
  "content": "回复，",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 77 ｜ t = 5.003s
增量 content：

```text
力求
```
完整字段：

```json
{
  "content": "力求",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 78 ｜ t = 5.017s
增量 content：

```text
准确
```
完整字段：

```json
{
  "content": "准确",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 79 ｜ t = 5.029s
增量 content：

```text
、清晰
```
完整字段：

```json
{
  "content": "、清晰",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 80 ｜ t = 5.044s
增量 content：

```text
、有条理。

此外
```
完整字段：

```json
{
  "content": "、有条理。\n\n此外",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 81 ｜ t = 5.070s
增量 content：

```text
，我支持
```
完整字段：

```json
{
  "content": "，我支持",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 82 ｜ t = 5.085s
增量 content：

```text
联网搜索（
```
完整字段：

```json
{
  "content": "联网搜索（",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 83 ｜ t = 5.090s
增量 content：

```text
需要你在
```
完整字段：

```json
{
  "content": "需要你在",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 84 ｜ t = 5.095s
增量 content：

```text
网页或
```
完整字段：

```json
{
  "content": "网页或",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 85 ｜ t = 5.110s
增量 content：

```text
 App 上
```
完整字段：

```json
{
  "content": " App 上",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 86 ｜ t = 5.125s
增量 content：

```text
手动开启），可以帮你
```
完整字段：

```json
{
  "content": "手动开启），可以帮你",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 87 ｜ t = 5.136s
增量 content：

```text
获取最新信息。
```
完整字段：

```json
{
  "content": "获取最新信息。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 88 ｜ t = 5.151s
增量 content：

```text
最关键
```
完整字段：

```json
{
  "content": "最关键",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 89 ｜ t = 5.159s
增量 content：

```text
的是，我是
```
完整字段：

```json
{
  "content": "的是，我是",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 90 ｜ t = 5.177s
增量 content：

```text
完全
```
完整字段：

```json
{
  "content": "完全",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 91 ｜ t = 5.190s
增量 content：

```text
免费的，你可以随时
```
完整字段：

```json
{
  "content": "免费的，你可以随时",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 92 ｜ t = 5.202s
增量 content：

```text
向我
```
完整字段：

```json
{
  "content": "向我",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 93 ｜ t = 5.223s
增量 content：

```text
提问，不用担心
```
完整字段：

```json
{
  "content": "提问，不用担心",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 94 ｜ t = 5.236s
增量 content：

```text
次数限制。
```
完整字段：

```json
{
  "content": "次数限制。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 95 ｜ t = 5.258s
增量 content：

```text
希望
```
完整字段：

```json
{
  "content": "希望",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 96 ｜ t = 5.258s
增量 content：

```text
我能成为
```
完整字段：

```json
{
  "content": "我能成为",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 97 ｜ t = 5.269s
增量 content：

```text
你学习
```
完整字段：

```json
{
  "content": "你学习",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 98 ｜ t = 5.276s
增量 content：

```text
、工作和
```
完整字段：

```json
{
  "content": "、工作和",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 99 ｜ t = 5.289s
增量 content：

```text
生活中的得力助手！有任何需要
```
完整字段：

```json
{
  "content": "生活中的得力助手！有任何需要",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 100 ｜ t = 5.321s
增量 content：

```text
，随时告诉我。
```
完整字段：

```json
{
  "content": "，随时告诉我。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 101 ｜ t = 5.321s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

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
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 102 ｜ t = 5.322s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 97,
    "output_tokens": 250,
    "total_tokens": 347,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 37
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 103 ｜ t = 5.322s
增量 content：

```text
（空字符串：本块只携带元数据，不带文字）
```
完整字段：

```json
{
  "content": "",
  "additional_kwargs": {},
  "response_metadata": {},
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a1345c-9c2d-7553-80ac-b290e934390e",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": "last"
}
```

## 三、字段速查

- `id`：本次调用的消息 ID（LangChain 生成，同一次会话的各分块共享同一 id）
- `content`：消息文本；分块里只有增量，累加后才是完整内容
- `additional_kwargs`：厂商扩展字段（如 DeepSeek 的 reasoning_content 会出现在这里）
- `response_metadata`：厂商原始响应元数据（model_name / finish_reason / token_usage 等）
- `usage_metadata`：LangChain 标准化的 token 用量（input_tokens / output_tokens / total_tokens）
- `type`：消息类型标识，`AIMessageChunk` 为流式分块，`AIMessage` 为完整消息