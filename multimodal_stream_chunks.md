# 多模态流式分块全量信息（用例 8：多模态流式（stream=True + 图片））

- 采集时间：2026-10-14 13:46:03
- 模型：`gpt-5.6-terra-ptu`（与主报告同一次实验，图片为图 B）
- 分块数量：**44** 个 ｜ 首块到达：1.99s ｜ 总耗时：2.42s
- 合并方式：`chunks[0] + chunks[1] + ...`（AIMessageChunk 重载了 + 运算符）

## 一、实际发出的请求体（完整 JSON，与普通请求只差 stream 字段）

```json
{
  "messages": [
    {
      "content": [
        {
          "type": "text",
          "text": "图里画了什么？请用两三句话描述，包括图形、颜色和图中的文字。"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAPAAAACgCAIAAAC9uXYyAAACvUlEQVR4nO3dwY1UMRBF0QliwiFOwmFNOGQwsEdCTdvlKr9/jiqAZ+nu/fEFQT66B8BOgiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJUhj0rx+fJ6/uIVxE0EQRNFEETRRBE0XQRBE0UQRNFEFf7/u3n90TBhH0Zf7k+8p1z2wj6Gu8mPLDsxb0Bd5I+bFZC3q0xZQfmLWg59pY83OaFvRQ22t+SNOCnqio5ic0LehxSmuOb1rQ4wh6haBnOVBzdtOCnkXQiwQ9yLGag5sW9CCCXifoKQ7XnNq0oKcQ9BaCnkLQWwh6CkFvIegpBL2FoKcQ9BaCHqGl5simBT2FmrcQ9BSC3kLQUwh6C0FPIegtBD2FoLcQ9BSC3kLQg6h5naAHEfQ6v2DNouZFgp5F0IsEPY6aVwh6HEGvEPREan6boIdS83sEPZea3yDo0dT8vwR9ASm/TtDXkPIrBH0ZKf+boK/35Hz/JmiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoLf5XNC9PYegtxH0BILeRtATCHobQU8g6DaCriDoNoKuIOg2gq4g6DaCriDoo0RcTdBHCbqaoI8SdDVBHyXoaoIuJ+KTBF1O0CcJupygTxJ0OUGfJOgSIu4i6BKC7iLoEoLuIugSgu4i6BKC7iLoEoLuIugSgu4i6BKC7iLoEoLuIugSgu4i6BKC7iLoEoLuImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgifIbHFwPEpVm894AAAAASUVORK5CYII="
          }
        }
      ],
      "role": "user"
    }
  ],
  "model": "gpt-5.6-terra-ptu",
  "stream": true
}
```

## 二、全部分块累加后的完整消息

```json
{
  "content": "图中白色背景上方左侧有一个黄色正方形，上方偏中间有一个紫色圆形。下方中央位置有一个黑色数字“7”。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai",
    "finish_reason": "stop",
    "model_name": "gpt-5.6-terra-2026-07-09",
    "service_tier": "default"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 77,
    "output_tokens": 83,
    "total_tokens": 160,
    "input_token_details": {
      "audio": 0,
      "cache_read": 0
    },
    "output_token_details": {
      "audio": 0,
      "reasoning": 35
    }
  },
  "tool_call_chunks": [],
  "chunk_position": "last"
}
```

## 三、全部 44 个分块的完整信息（逐块 model_dump，无省略）

### 分块 1 ｜ t = 1.993s
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
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 2 ｜ t = 1.994s
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
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 3 ｜ t = 1.995s
增量 content：

```text
图
```
完整字段：

```json
{
  "content": "图",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 4 ｜ t = 1.995s
增量 content：

```text
中
```
完整字段：

```json
{
  "content": "中",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 5 ｜ t = 1.995s
增量 content：

```text
白
```
完整字段：

```json
{
  "content": "白",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 6 ｜ t = 1.995s
增量 content：

```text
色
```
完整字段：

```json
{
  "content": "色",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 7 ｜ t = 1.995s
增量 content：

```text
背景
```
完整字段：

```json
{
  "content": "背景",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 8 ｜ t = 1.995s
增量 content：

```text
上
```
完整字段：

```json
{
  "content": "上",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 9 ｜ t = 1.995s
增量 content：

```text
方
```
完整字段：

```json
{
  "content": "方",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 10 ｜ t = 1.995s
增量 content：

```text
左
```
完整字段：

```json
{
  "content": "左",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 11 ｜ t = 1.995s
增量 content：

```text
侧
```
完整字段：

```json
{
  "content": "侧",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 12 ｜ t = 1.995s
增量 content：

```text
有
```
完整字段：

```json
{
  "content": "有",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 13 ｜ t = 1.995s
增量 content：

```text
一个
```
完整字段：

```json
{
  "content": "一个",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 14 ｜ t = 1.996s
增量 content：

```text
黄色
```
完整字段：

```json
{
  "content": "黄色",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 15 ｜ t = 1.996s
增量 content：

```text
正
```
完整字段：

```json
{
  "content": "正",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 16 ｜ t = 1.996s
增量 content：

```text
方
```
完整字段：

```json
{
  "content": "方",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 17 ｜ t = 1.996s
增量 content：

```text
形
```
完整字段：

```json
{
  "content": "形",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 18 ｜ t = 1.996s
增量 content：

```text
，上
```
完整字段：

```json
{
  "content": "，上",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 19 ｜ t = 1.996s
增量 content：

```text
方
```
完整字段：

```json
{
  "content": "方",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 20 ｜ t = 1.996s
增量 content：

```text
偏
```
完整字段：

```json
{
  "content": "偏",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 21 ｜ t = 1.996s
增量 content：

```text
中
```
完整字段：

```json
{
  "content": "中",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 22 ｜ t = 1.996s
增量 content：

```text
间
```
完整字段：

```json
{
  "content": "间",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 23 ｜ t = 1.996s
增量 content：

```text
有
```
完整字段：

```json
{
  "content": "有",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 24 ｜ t = 1.996s
增量 content：

```text
一个
```
完整字段：

```json
{
  "content": "一个",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 25 ｜ t = 1.997s
增量 content：

```text
紫
```
完整字段：

```json
{
  "content": "紫",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 26 ｜ t = 1.997s
增量 content：

```text
色
```
完整字段：

```json
{
  "content": "色",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 27 ｜ t = 1.997s
增量 content：

```text
圆
```
完整字段：

```json
{
  "content": "圆",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 28 ｜ t = 1.997s
增量 content：

```text
形
```
完整字段：

```json
{
  "content": "形",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 29 ｜ t = 1.997s
增量 content：

```text
。
```
完整字段：

```json
{
  "content": "。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 30 ｜ t = 1.997s
增量 content：

```text
下
```
完整字段：

```json
{
  "content": "下",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 31 ｜ t = 1.997s
增量 content：

```text
方
```
完整字段：

```json
{
  "content": "方",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 32 ｜ t = 1.997s
增量 content：

```text
中央
```
完整字段：

```json
{
  "content": "中央",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 33 ｜ t = 1.998s
增量 content：

```text
位置
```
完整字段：

```json
{
  "content": "位置",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 34 ｜ t = 2.404s
增量 content：

```text
有
```
完整字段：

```json
{
  "content": "有",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 35 ｜ t = 2.405s
增量 content：

```text
一个
```
完整字段：

```json
{
  "content": "一个",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 36 ｜ t = 2.405s
增量 content：

```text
黑
```
完整字段：

```json
{
  "content": "黑",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 37 ｜ t = 2.405s
增量 content：

```text
色
```
完整字段：

```json
{
  "content": "色",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 38 ｜ t = 2.405s
增量 content：

```text
数字
```
完整字段：

```json
{
  "content": "数字",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 39 ｜ t = 2.405s
增量 content：

```text
“
```
完整字段：

```json
{
  "content": "“",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 40 ｜ t = 2.406s
增量 content：

```text
7
```
完整字段：

```json
{
  "content": "7",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 41 ｜ t = 2.406s
增量 content：

```text
”。
```
完整字段：

```json
{
  "content": "”。",
  "additional_kwargs": {},
  "response_metadata": {
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 42 ｜ t = 2.406s
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
    "model_name": "gpt-5.6-terra-2026-07-09",
    "service_tier": "default",
    "model_provider": "openai"
  },
  "type": "AIMessageChunk",
  "name": null,
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 43 ｜ t = 2.416s
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
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 77,
    "output_tokens": 83,
    "total_tokens": 160,
    "input_token_details": {
      "audio": 0,
      "cache_read": 0
    },
    "output_token_details": {
      "audio": 0,
      "reasoning": 35
    }
  },
  "tool_call_chunks": [],
  "chunk_position": null
}
```

### 分块 44 ｜ t = 2.416s
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
  "id": "lc_run--01a138f2-395c-7a63-bcb7-abd67f5c8bc1",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": null,
  "tool_call_chunks": [],
  "chunk_position": "last"
}
```

## 四、字段速查

- `content`：每块只有增量文字，累加后等于完整回答
- `id`：同一次调用的所有分块共享同一 id
- `usage_metadata`：随最后一个分块回传 token 用量
- `chunk_position` / `response_metadata`：中间块与末块差异可逐块对比