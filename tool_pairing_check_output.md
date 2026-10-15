# tool 消息配对校验实测：孤立 ToolMessage / 无应答 tool_calls 会 400 吗

- 采集时间：2026-10-14 14:29:59
- 方式：httpx 裸发 chat/completions，消息手工构造，不传 tools 参数（校验的是消息序列本身），报错即服务端原文

## 结论总览

| 模型 | 用例 | HTTP | 服务端反应 |
| --- | --- | --- | --- |
| `gpt-5.6-terra-ptu` | 1 正确配对（对照组） | 200 | ✅ 正常回答：青岛今天天气晴，26℃，东南风3级。 |
| `gpt-5.6-terra-ptu` | 2 孤立 ToolMessage（前面没有带 tool_calls 的 assistant） | 400 | ❌ 400 拒绝：Invalid parameter: messages with role 'tool' must be a response to a preceeding  |
| `gpt-5.6-terra-ptu` | 3 无应答 tool_calls（assistant 发起调用后没有 tool 回包） | 400 | ❌ 400 拒绝：An assistant message with 'tool_calls' must be followed by tool messages respond |
| `gpt-5.6-terra-ptu` | 4 tool_call_id 不匹配（调用 call_001，回包写 call_999） | 400 | ❌ 400 拒绝：Invalid parameter: 'tool_call_id' of 'call_999' not found in 'tool_calls' of pre |
| `deepseek-v4-flash-sz` | 1 正确配对（对照组） | 200 | ✅ 正常回答：青岛今天天气晴朗，气温26度，东南风3级。 |
| `deepseek-v4-flash-sz` | 2 孤立 ToolMessage（前面没有带 tool_calls 的 assistant） | 200 | ✅ 正常回答：青岛今天天气晴朗，气温26度，东南风3级。 |
| `deepseek-v4-flash-sz` | 3 无应答 tool_calls（assistant 发起调用后没有 tool 回包） | 200 | ✅ 正常回答：抱歉，我无法直接获取青岛今天的实时天气信息。建议打开天气App，或搜索“青岛天气”查看最新预报；也可以告诉我日期，我帮你 |
| `deepseek-v4-flash-sz` | 4 tool_call_id 不匹配（调用 call_001，回包写 call_999） | 200 | ✅ 正常回答：青岛今天天气晴朗，气温 **26 度**，东南风 **3 级**。  请问还需要了解湿度、空气质量等其他信息吗？ |

## `gpt-5.6-terra-ptu` × 1 正确配对（对照组）

HTTP 状态：**200** ｜ 耗时：1.97s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"青岛\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_001",
    "content": "晴，26 度，东南风 3 级"
  }
]
```

响应原文（截断至 4000 字符）：
```json
{"choices":[{"content_filter_results":{},"finish_reason":"stop","index":0,"logprobs":null,"message":{"annotations":[],"content":"青岛今天天气晴，26℃，东南风3级。","refusal":null,"role":"assistant"}}],"created":1791959394,"id":"chatcmpl-EYmmoCX0edY7z54ufYJItXPQ7SY70","model":"gpt-5.6-terra-2026-07-09","object":"chat.completion","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{}}],"routing":{"serving_pipereplica":"d20261013172155-318f323d-prefill-r13-dp0-prefill"},"service_tier":"default","system_fingerprint":null,"usage":{"completion_tokens":19,"completion_tokens_details":{"accepted_prediction_tokens":0,"audio_tokens":0,"reasoning_tokens":0,"rejected_prediction_tokens":0},"latency_checkpoint":{"engine_tbt_ms":6,"engine_ttft_ms":125,"engine_ttlt_ms":251,"pre_inference_ms":102,"service_tbt_ms":6,"service_ttft_ms":856,"service_ttlt_ms":977,"user_visible_ttft_ms":753},"prompt_tokens":55,"prompt_tokens_details":{"audio_tokens":0,"cached_tokens":0},"total_tokens":74}}

```

## `gpt-5.6-terra-ptu` × 2 孤立 ToolMessage（前面没有带 tool_calls 的 assistant）

HTTP 状态：**400** ｜ 耗时：0.25s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "tool",
    "tool_call_id": "call_001",
    "content": "晴，26 度，东南风 3 级"
  }
]
```

响应原文（截断至 4000 字符）：
```json
{
  "error": {
    "message": "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.",
    "type": "invalid_request_error",
    "param": "messages.[1].role",
    "code": null
  }
}
```

## `gpt-5.6-terra-ptu` × 3 无应答 tool_calls（assistant 发起调用后没有 tool 回包）

HTTP 状态：**400** ｜ 耗时：0.19s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"青岛\"}"
        }
      }
    ]
  }
]
```

响应原文（截断至 4000 字符）：
```json
{
  "error": {
    "message": "An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'. The following tool_call_ids did not have response messages: call_001",
    "type": "invalid_request_error",
    "param": "messages",
    "code": null
  }
}
```

## `gpt-5.6-terra-ptu` × 4 tool_call_id 不匹配（调用 call_001，回包写 call_999）

HTTP 状态：**400** ｜ 耗时：0.2s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"青岛\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_999",
    "content": "晴，26 度，东南风 3 级"
  }
]
```

响应原文（截断至 4000 字符）：
```json
{
  "error": {
    "message": "Invalid parameter: 'tool_call_id' of 'call_999' not found in 'tool_calls' of previous message.",
    "type": "invalid_request_error",
    "param": "messages.[2].tool_call_id",
    "code": null
  }
}
```

## `deepseek-v4-flash-sz` × 1 正确配对（对照组）

HTTP 状态：**200** ｜ 耗时：0.93s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"青岛\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_001",
    "content": "晴，26 度，东南风 3 级"
  }
]
```

响应原文（截断至 4000 字符）：
```json
{"id":"788784470cef4246b6226dbc0a435acf","created":1791959397,"model":"deepseek-v4-flash-sz","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"青岛今天天气晴朗，气温26度，东南风3级。","role":"assistant","reasoning_content":"好的，我通过工具查询到了青岛今天的天气情况。现在需要把这个信息直接、清晰地告诉用户。用户的问题很简洁，所以回答也应该简洁明了。我核实一下查询结果：天气是晴天，温度26摄氏度，风力是东南风3级。信息很完整，直接回复就可以了。","provider_specific_fields":{"refusal":null,"reasoning_content":"好的，我通过工具查询到了青岛今天的天气情况。现在需要把这个信息直接、清晰地告诉用户。用户的问题很简洁，所以回答也应该简洁明了。我核实一下查询结果：天气是晴天，温度26摄氏度，风力是东南风3级。信息很完整，直接回复就可以了。"}},"provider_specific_fields":{"matched_stop":1}}],"usage":{"completion_tokens":78,"prompt_tokens":156,"total_tokens":234,"completion_tokens_details":{"reasoning_tokens":63,"text_tokens":15}},"metadata":{"weight_version":"default"}}
```

## `deepseek-v4-flash-sz` × 2 孤立 ToolMessage（前面没有带 tool_calls 的 assistant）

HTTP 状态：**200** ｜ 耗时：0.42s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "tool",
    "tool_call_id": "call_001",
    "content": "晴，26 度，东南风 3 级"
  }
]
```

响应原文（截断至 4000 字符）：
```json
{"id":"e41bb41874404501b32db558e5a44cb3","created":1791959397,"model":"deepseek-v4-flash-sz","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"青岛今天天气晴朗，气温26度，东南风3级。","role":"assistant","reasoning_content":"我们需要根据提供的tool result回答青岛今天天气。用户问青岛今天天气怎么样，工具给出了晴，26度，东南风3级。我们直接回答即可。注意语言自然。","provider_specific_fields":{"refusal":null,"reasoning_content":"我们需要根据提供的tool result回答青岛今天天气。用户问青岛今天天气怎么样，工具给出了晴，26度，东南风3级。我们直接回答即可。注意语言自然。"}},"provider_specific_fields":{"matched_stop":1}}],"usage":{"completion_tokens":54,"prompt_tokens":108,"total_tokens":162,"completion_tokens_details":{"reasoning_tokens":39,"text_tokens":15}},"metadata":{"weight_version":"default"}}
```

## `deepseek-v4-flash-sz` × 3 无应答 tool_calls（assistant 发起调用后没有 tool 回包）

HTTP 状态：**200** ｜ 耗时：1.12s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"青岛\"}"
        }
      }
    ]
  }
]
```

响应原文（截断至 4000 字符）：
```json
{"id":"9d5048b1407d46be9bb01cd808f4aac4","created":1791959398,"model":"deepseek-v4-flash-sz","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"抱歉，我无法直接获取青岛今天的实时天气信息。建议打开天气App，或搜索“青岛天气”查看最新预报；也可以告诉我日期，我帮你查一般的气候参考。","role":"assistant","reasoning_content":"We need answer in Chinese. Need know weather Qingdao today? Need current date? System current date 2026-06-05. We need provide weather? We have no live internet. Need be honest: cannot query real-time. But maybe ask geolocation? Need say as AI no real-time weather, suggest check app. But maybe can give general seasonal clue. Need answer: \"抱歉，我无法获取实时天气数据。请打开天气App或搜索'青岛天气'查看今日详情。\" Could mention June typical mild/sea breeze. But if request \"青岛今天天气怎么样\" maybe we can respond with \"需联网查询，当前无实时数据\". Need be accurate.","provider_specific_fields":{"refusal":null,"reasoning_content":"We need answer in Chinese. Need know weather Qingdao today? Need current date? System current date 2026-06-05. We need provide weather? We have no live internet. Need be honest: cannot query real-time. But maybe ask geolocation? Need say as AI no real-time weather, suggest check app. But maybe can give general seasonal clue. Need answer: \"抱歉，我无法获取实时天气数据。请打开天气App或搜索'青岛天气'查看今日详情。\" Could mention June typical mild/sea breeze. But if request \"青岛今天天气怎么样\" maybe we can respond with \"需联网查询，当前无实时数据\". Need be accurate."}},"provider_specific_fields":{"matched_stop":1}}],"usage":{"completion_tokens":180,"prompt_tokens":88,"total_tokens":268,"completion_tokens_details":{"reasoning_tokens":141,"text_tokens":39}},"metadata":{"weight_version":"default"}}
```

## `deepseek-v4-flash-sz` × 4 tool_call_id 不匹配（调用 call_001，回包写 call_999）

HTTP 状态：**200** ｜ 耗时：0.62s

请求 messages：
```json
[
  {
    "role": "user",
    "content": "青岛今天天气怎么样？"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"青岛\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_999",
    "content": "晴，26 度，东南风 3 级"
  }
]
```

响应原文（截断至 4000 字符）：
```json
{"id":"eac15a36c65b4218ac24c5fd35316f99","created":1791959399,"model":"deepseek-v4-flash-sz","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"青岛今天天气晴朗，气温 **26 度**，东南风 **3 级**。\n\n请问还需要了解湿度、空气质量等其他信息吗？","role":"assistant","reasoning_content":"好的，用户想知道青岛今天的天气。这是一个简单的天气查询问题。\n\n我需要提供青岛今天的天气信息，包括天气状况、温度和风力。这些数据我已经通过工具获取到了，可以直接回答用户。\n\n考虑到用户可能还想知道更多细节，比如湿度或空气质量，我可以在回答后补充一句，询问用户是否需要更多信息，这样显得更贴心。","provider_specific_fields":{"refusal":null,"reasoning_content":"好的，用户想知道青岛今天的天气。这是一个简单的天气查询问题。\n\n我需要提供青岛今天的天气信息，包括天气状况、温度和风力。这些数据我已经通过工具获取到了，可以直接回答用户。\n\n考虑到用户可能还想知道更多细节，比如湿度或空气质量，我可以在回答后补充一句，询问用户是否需要更多信息，这样显得更贴心。"}},"provider_specific_fields":{"matched_stop":1}}],"usage":{"completion_tokens":103,"prompt_tokens":156,"total_tokens":259,"completion_tokens_details":{"reasoning_tokens":72,"text_tokens":31}},"metadata":{"weight_version":"default"}}
```
