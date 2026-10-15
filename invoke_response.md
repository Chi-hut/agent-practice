# invoke 非流式响应全量信息

- 采集时间：2026-10-13 16:24:13
- 模型：`deepseek-v4-flash-sz`
- 问题：用 300 字左右介绍一下你自己，并说明你能帮我做什么
- 总耗时：1.44s（期间阻塞等待，返回即完整）
- 返回类型：`AIMessage`
- 内容长度：418 字

## 一、完整消息对象（最核心的一份）

一次性返回的完整消息，content 即全部文本，token 用量随响应直接给出：

```json
{
  "content": "你好！我是 DeepSeek，一个由深度求索公司开发的 AI 助手。我拥有强大的自然语言理解和生成能力，知识截止于 2025 年 5 月，善于处理各类文本任务。\n\n我可以帮你做什么呢？主要包括这几方面：\n\n- **学习与知识答疑**：无论是数学、物理、历史、编程，还是日常百科，我都能用清晰易懂的方式为你讲解。\n- **写作与创意**：帮你写文章、改文案、润色简历、构思故事，也能生成诗歌、对联等创意内容。\n- **数据处理与分析**：我支持上传 Excel、PDF、Word 等文件，能快速提取信息、整理表格、总结要点。\n- **编程助手**：帮你调试代码、解释逻辑、设计算法，甚至完成一个小项目的开发。\n- **翻译与语言**：支持多语言互译，也能帮你练习外语、纠正语法。\n\n我完全免费，还支持联网搜索（需你手动开启）。无论你是学习、工作还是娱乐，随时都能来找我。我会用认真、耐心、细致的风格，陪你解决问题。有什么想聊的，直接说吧！",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 291,
      "prompt_tokens": 97,
      "total_tokens": 388,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 56,
        "rejected_prediction_tokens": null,
        "text_tokens": 235
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "739cf4efa9234e51a9023355759cd202",
    "finish_reason": "stop",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a1345c-b0f7-7c82-993d-301929e10a7a-0",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 97,
    "output_tokens": 291,
    "total_tokens": 388,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 56
    }
  }
}
```

## 二、回复正文（即 content 字段）

```text
你好！我是 DeepSeek，一个由深度求索公司开发的 AI 助手。我拥有强大的自然语言理解和生成能力，知识截止于 2025 年 5 月，善于处理各类文本任务。

我可以帮你做什么呢？主要包括这几方面：

- **学习与知识答疑**：无论是数学、物理、历史、编程，还是日常百科，我都能用清晰易懂的方式为你讲解。
- **写作与创意**：帮你写文章、改文案、润色简历、构思故事，也能生成诗歌、对联等创意内容。
- **数据处理与分析**：我支持上传 Excel、PDF、Word 等文件，能快速提取信息、整理表格、总结要点。
- **编程助手**：帮你调试代码、解释逻辑、设计算法，甚至完成一个小项目的开发。
- **翻译与语言**：支持多语言互译，也能帮你练习外语、纠正语法。

我完全免费，还支持联网搜索（需你手动开启）。无论你是学习、工作还是娱乐，随时都能来找我。我会用认真、耐心、细致的风格，陪你解决问题。有什么想聊的，直接说吧！
```

## 三、与 stream 响应的结构差异

| 维度 | invoke（本文件） | stream（stream_response.md） |
| --- | --- | --- |
| 返回类型 | `AIMessage` | `AIMessageChunk`（增量切片） |
| content | 完整文本，一次给全 | 每块只有增量，需 `+` 累加 |
| 调用次数 | 1 个对象 | N 个对象（本次 N 见 stream 文件） |
| token 用量 | 响应直接带全 | 随最后一个分块才回传 |
| 字段结构 | 二者字段完全一致，仅 content 到达方式不同 ||