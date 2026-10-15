# 响应两层对照：服务端原始 JSON vs LangChain AIMessage

- 采集时间：2026-10-13 19:32:21
- 模型：`deepseek-v4-flash-sz`
- 问题：用一句话说明什么是 HTTP 请求头
- 调用方式：一次 `llm.invoke()`，总耗时 0.79s
- 截获方式：httpx **响应**钩子抄下原始响应体（第 1 层）+ `invoke()` 返回值（第 3 层），
  两份是**同一次调用**的数据，可逐字段对上
- 结论先行：你 curl 看到的 JSON 与 invoke 返回值是同一份数据的不同抽象层，映射关系见第四章

## 一、先看结论：同一份数据的三层加工链条

你贴的那种 JSON 与 `llm.invoke()` 返回值不同，不是数据丢了，而是隔着两层加工：

```text
服务端返回的 HTTP 响应体（JSON 文本，chat.completion 对象）
        │
        │  ① openai SDK：json.loads 反序列化 + pydantic 字段校验
        ▼
ChatCompletion 对象（openai SDK 的厂商 DTO：字段与 JSON 一一对应，文本变对象）
        │
        │  ② langchain-openai：字段搬运 + 名称标准化（prompt_tokens→input_tokens、role→type）
        ▼
AIMessage 对象（LangChain 的跨厂商统一消息模型）
        │
        │  ③ llm.invoke() 把它作为返回值交给你
        ▼
代码里拿到的 response（dump_response.md 导出的就是这一层的 model_dump）
```

本文件同时截获链条的首尾两端：第二章 = 第 1 层原始 JSON，第三章 = 第 3 层 AIMessage；
中间的 ChatCompletion（第 2 层）字段与原始 JSON 完全同名同结构，不再单独导出。

## 二、第 1 层：服务端返回的原始响应（HTTP 视角，curl 拿到的就是它）

### 1. 状态行与响应头全量

```text
HTTP 200（HTTP/1.1 协议）
date: Tue, 13 Oct 2026 11:32:22 GMT
content-type: application/json
transfer-encoding: chunked
connection: keep-alive
x-litellm-call-id: 16664532-5c47-41fe-a46c-0d35fb6c5244
x-litellm-model-id: 8904e4c75e2cd020cae33a6049f43512366acdabc05fe205e28c5e08b8a72f9e
x-litellm-model-api-base: https://aix-backup.hismarttv.com/deepseek-v4-flash/v1
x-litellm-version: 1.83.14
x-litellm-response-cost-original: 0.0
x-litellm-response-cost-discount-amount: 0.0
x-litellm-response-cost-margin-amount: 0.0
x-litellm-response-cost-margin-percent: 0.0
x-litellm-key-spend: 0.0
x-litellm-response-duration-ms: 471.666
x-litellm-overhead-duration-ms: 13.676
x-litellm-callback-duration-ms: 0.0
llm_provider-content-type: application/json
llm_provider-req-arrive-time: 1791891141686
llm_provider-resp-start-time: 1791891142116
llm_provider-date: Tue, 13 Oct 2026 11:32:20 GMT
llm_provider-req-cost-time: 430
llm_provider-x-envoy-upstream-service-time: 429
llm_provider-server: istio-envoy
llm_provider-x-request-id: 9fb06089-6311-4327-a851-24fac656b8f4
llm_provider-transfer-encoding: chunked
x-litellm-model-group: deepseek-v4-flash-sz
x-litellm-attempted-retries: 0
x-litellm-attempted-fallbacks: 0
proxytrackid: 5fc93cd0-0c40-44f4-a131-2fa5c30e09f0
proxytrycount: 1
proxyfailovercount: 0
proxyduration: 0.282
set-cookie: BIGipServerPOOL_OCPK8SL7_PRD_80=!prSilNGNBwfWGczVZekhhPIyzDN0VddNva+UQWJhEOjr/QE/JSIJQj24fDI9yFL4kqfh4qLKnDTUaw==; path=/; Secure, BIGipServerPOOL_OCP_JUCLOUD_80=!omZCben7v1W/GcDVZekhhPIyzDN0VTRsDu7zOE4Q3citWtz0mEJzLyYlffOONc6nFCHksK1F0P6E8tw=; path=/; Secure
```

| 响应头 | 本次值 | 说明 |
| --- | --- | --- |
| `date` | `Tue, 13 Oct 2026 11:32:22 GMT` | 服务端生成响应的时间 |
| `content-type` | `application/json` | 响应体格式：JSON |
| `transfer-encoding` | `chunked` | 传输编码（分块传输时出现） |
| `connection` | `keep-alive` | 连接策略（keep-alive 复用连接） |
| `x-litellm-call-id` | `16664532-5c47-41fe-a46c-0d35fb6c5244` | 网关 / 服务端附加 |
| `x-litellm-model-id` | `8904e4c75e2cd020cae33a6049f43512366acdabc05fe205e28c5e08b8a72f9e` | 网关 / 服务端附加 |
| `x-litellm-model-api-base` | `https://aix-backup.hismarttv.com/deepseek-v4-flash/v1` | 网关 / 服务端附加 |
| `x-litellm-version` | `1.83.14` | 网关 / 服务端附加 |
| `x-litellm-response-cost-original` | `0.0` | 网关 / 服务端附加 |
| `x-litellm-response-cost-discount-amount` | `0.0` | 网关 / 服务端附加 |
| `x-litellm-response-cost-margin-amount` | `0.0` | 网关 / 服务端附加 |
| `x-litellm-response-cost-margin-percent` | `0.0` | 网关 / 服务端附加 |
| `x-litellm-key-spend` | `0.0` | 网关 / 服务端附加 |
| `x-litellm-response-duration-ms` | `471.666` | 网关 / 服务端附加 |
| `x-litellm-overhead-duration-ms` | `13.676` | 网关 / 服务端附加 |
| `x-litellm-callback-duration-ms` | `0.0` | 网关 / 服务端附加 |
| `llm_provider-content-type` | `application/json` | 网关 / 服务端附加 |
| `llm_provider-req-arrive-time` | `1791891141686` | 网关 / 服务端附加 |
| `llm_provider-resp-start-time` | `1791891142116` | 网关 / 服务端附加 |
| `llm_provider-date` | `Tue, 13 Oct 2026 11:32:20 GMT` | 网关 / 服务端附加 |
| `llm_provider-req-cost-time` | `430` | 网关 / 服务端附加 |
| `llm_provider-x-envoy-upstream-service-time` | `429` | 网关 / 服务端附加 |
| `llm_provider-server` | `istio-envoy` | 网关 / 服务端附加 |
| `llm_provider-x-request-id` | `9fb06089-6311-4327-a851-24fac656b8f4` | 网关 / 服务端附加 |
| `llm_provider-transfer-encoding` | `chunked` | 网关 / 服务端附加 |
| `x-litellm-model-group` | `deepseek-v4-flash-sz` | 网关 / 服务端附加 |
| `x-litellm-attempted-retries` | `0` | 网关 / 服务端附加 |
| `x-litellm-attempted-fallbacks` | `0` | 网关 / 服务端附加 |
| `proxytrackid` | `5fc93cd0-0c40-44f4-a131-2fa5c30e09f0` | 网关 / 服务端附加 |
| `proxytrycount` | `1` | 网关 / 服务端附加 |
| `proxyfailovercount` | `0` | 网关 / 服务端附加 |
| `proxyduration` | `0.282` | 网关 / 服务端附加 |
| `set-cookie` | `BIGipServerPOOL_OCPK8SL7_PRD_80=!prSilNGNBwfWGczVZekhhPIyzDN0VddNva+UQWJhEOjr/QE/JSIJQj24fDI9yFL4kqfh4qLKnDTUaw==; path=/; Secure, BIGipServerPOOL_OCP_JUCLOUD_80=!omZCben7v1W/GcDVZekhhPIyzDN0VTRsDu7zOE4Q3citWtz0mEJzLyYlffOONc6nFCHksK1F0P6E8tw=; path=/; Secure` | 网关（F5 负载均衡）种下的会话粘性标识，httpx 的 cookie jar 存起来、后续请求自动携带 |

### 2. 响应体（JSON 全字段，先原始后美化）

原始形态（网络上传回来的就是这个单行字节串）：
```text
{"id":"a6a5e64a963148a88a5d7249e40535b8","created":1791891142,"model":"deepseek-v4-flash-sz","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方法、目标、客户端能力、认证信息、内容类型等附加信息。","role":"assistant","reasoning_content":"We need answer in Chinese. User asks \"用一句话说明什么是 HTTP 请求头\" Need one sentence. Define HTTP request header. Keep concise.","provider_specific_fields":{"refusal":null,"reasoning_content":"We need answer in Chinese. User asks \"用一句话说明什么是 HTTP 请求头\" Need one sentence. Define HTTP request header. Keep concise."}},"provider_specific_fields":{"matched_stop":1}}],"usage":{"completion_tokens":73,"prompt_tokens":91,"total_tokens":164,"completion_tokens_details":{"reasoning_tokens":31,"text_tokens":42}},"metadata":{"weight_version":"default"}}
```
美化形态（同一份数据，只加了缩进便于阅读）：
```json
{
  "id": "a6a5e64a963148a88a5d7249e40535b8",
  "created": 1791891142,
  "model": "deepseek-v4-flash-sz",
  "object": "chat.completion",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "content": "HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方法、目标、客户端能力、认证信息、内容类型等附加信息。",
        "role": "assistant",
        "reasoning_content": "We need answer in Chinese. User asks \"用一句话说明什么是 HTTP 请求头\" Need one sentence. Define HTTP request header. Keep concise.",
        "provider_specific_fields": {
          "refusal": null,
          "reasoning_content": "We need answer in Chinese. User asks \"用一句话说明什么是 HTTP 请求头\" Need one sentence. Define HTTP request header. Keep concise."
        }
      },
      "provider_specific_fields": {
        "matched_stop": 1
      }
    }
  ],
  "usage": {
    "completion_tokens": 73,
    "prompt_tokens": 91,
    "total_tokens": 164,
    "completion_tokens_details": {
      "reasoning_tokens": 31,
      "text_tokens": 42
    }
  },
  "metadata": {
    "weight_version": "default"
  }
}
```

### 3. 顶层字段逐项解读

| 字段 | 本次值 | 说明 |
| --- | --- | --- |
| `id` | `"a6a5e64a963148a88a5d7249e40535b8"` | 本次调用的唯一 ID（服务端生成） |
| `created` | `1791891142` | 响应生成的 Unix 时间戳（秒） |
| `model` | `"deepseek-v4-flash-sz"` | 实际服务本次请求的模型名 |
| `object` | `"chat.completion"` | 对象类型标记：chat.completion = 非流式完整结果（流式分块叫 chat.completion.chunk） |
| `choices` | 数组，共 1 个元素（展开见下节） | 候选回复数组：n=1 时永远只有 1 个元素 |
| `usage` | `{"completion_tokens": 73, "prompt_tokens": 91, "total_tokens": 164, "completion_tokens_details": {"reasoning_tokens": 31, "text_tokens": 42}}` | token 用量统计 |
| `metadata` | `{"weight_version": "default"}` | 网关附加的元数据（weight_version=本次命中的权重版本） |

### 4. 嵌套字段展开（choices[0] / message / usage 逐个到叶子）

| 原始响应里的字段路径 | 本次值 | 说明 |
| --- | --- | --- |
| `choices[0].finish_reason` | `stop` | 停止原因：stop=自然讲完；length=被 token 上限截断；tool_calls=要调工具 |
| `choices[0].index` | `0` | 候选序号（n>1 生成多个候选时才有意义） |
| `choices[0].message.content` | `HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方法、目标、客户端能力、认证信息、内容类型等附加信息。` | 回复正文——日常代码里用的就是它 |
| `choices[0].message.role` | `assistant` | 恒为 assistant：表示这条是模型说的 |
| `choices[0].message.reasoning_content` | `We need answer in Chinese. User asks "用一句话说明什么是 HTTP 请求头" Need one sentence. Def…` | 思维链：推理模型先'想'再'答'，这段是它想的过程（DeepSeek 的扩展字段） |
| `choices[0].message.provider_specific_fields.refusal` | `null` | （厂商 / 网关扩展字段） |
| `choices[0].message.provider_specific_fields.reasoning_content` | `We need answer in Chinese. User asks "用一句话说明什么是 HTTP 请求头" Need one sentence. Def…` | 思维链：推理模型先'想'再'答'，这段是它想的过程（DeepSeek 的扩展字段） |
| `choices[0].provider_specific_fields.matched_stop` | `1` | （厂商 / 网关扩展字段） |
| `usage.completion_tokens` | `73` | 输出消耗的 token 数（含思维链） |
| `usage.prompt_tokens` | `91` | 输入消耗的 token 数 |
| `usage.total_tokens` | `164` | 总 token 数 |
| `usage.completion_tokens_details.reasoning_tokens` | `31` | 思维链占的 token 数 |
| `usage.completion_tokens_details.text_tokens` | `42` | （厂商 / 网关扩展字段） |
| `metadata.weight_version` | `default` | （厂商 / 网关扩展字段） |

## 三、第 3 层：llm.invoke() 返回的 AIMessage

同一份响应经过 ①② 两层加工后，你在代码里拿到的对象长这样（`model_dump()` 全字段导出，
与 invoke_response.md 的导出方式一致；content 长度 72 字）：

```json
{
  "content": "HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方法、目标、客户端能力、认证信息、内容类型等附加信息。",
  "additional_kwargs": {
    "refusal": null
  },
  "response_metadata": {
    "token_usage": {
      "completion_tokens": 73,
      "prompt_tokens": 91,
      "total_tokens": 164,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 31,
        "rejected_prediction_tokens": null,
        "text_tokens": 42
      },
      "prompt_tokens_details": null
    },
    "model_provider": "openai",
    "model_name": "deepseek-v4-flash-sz",
    "system_fingerprint": null,
    "id": "a6a5e64a963148a88a5d7249e40535b8",
    "finish_reason": "stop",
    "logprobs": null
  },
  "type": "ai",
  "name": null,
  "id": "lc_run--01a13508-f219-7bb2-8d44-51e2b9582473-0",
  "tool_calls": [],
  "invalid_tool_calls": [],
  "usage_metadata": {
    "input_tokens": 91,
    "output_tokens": 73,
    "total_tokens": 164,
    "input_token_details": {},
    "output_token_details": {
      "reasoning": 31
    }
  }
}
```

| AIMessage 字段 | 说明 |
| --- | --- |
| `content` | 回复正文，搬运自 choices[0].message.content |
| `additional_kwargs` | 厂商扩展字段收纳处（本次只收了 refusal；reasoning_content 并没有被搬进来） |
| `response_metadata` | 厂商响应元数据（token_usage / model_name / finish_reason / 原始 id 等） |
| `type` | 消息类型：'ai' 表示这是模型说的话（表达 role=assistant 这个事实） |
| `name` | 可选的说话者名字（本次未用） |
| `id` | 消息 ID：LangChain 自己生成的运行 ID（lc_run-- 前缀）——不是响应 JSON 里那个 id（那个在 response_metadata.id） |
| `tool_calls` | 模型发起的工具调用列表（绑定工具后才有内容，本次为空） |
| `invalid_tool_calls` | 解析失败的工具调用（本次为空） |
| `usage_metadata` | LangChain 标准化的 token 用量（input/output/total_tokens + output_token_details.reasoning 细分） |

## 四、字段映射对照表（核心：两边实测值并排，逐行对照看）

| 原始响应里的字段 | AIMessage 里去哪了 | 第 1 层实测值 | 第 3 层实测值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `response_metadata.id` | `a6a5e64a963148a88a5d7249e40535b8` | `a6a5e64a963148a88a5d7249e40535b8` | 服务端调用 ID 存进 response_metadata；注意 AIMessage 顶层的 id 是 LangChain 另生成的运行 ID（lc_run-- 前缀），两者不是一回事 |
| `choices[0].message.content` | `content` | `HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方…` | `HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方…` | 回复正文，一字不差搬过来 |
| `choices[0].message.role` | `type` | `assistant` | `ai` | assistant 这个事实改用 type='ai' 表达（LangChain 自己的命名） |
| `choices[0].message.reasoning_content` | （消失，不再往下传） | `We need answer in Chinese. User asks "用一句话说明什么…` | — | 思维链：本次实测被丢弃——langchain-openai 1.x 的转换没搬运它，只在原始层可见（排查思维链丢失要记住这点） |
| `choices[0].finish_reason` | `response_metadata.finish_reason` | `stop` | `stop` | 停止原因 |
| `model` | `response_metadata.model_name` | `deepseek-v4-flash-sz` | `deepseek-v4-flash-sz` | 模型名 |
| `usage.prompt_tokens` | `usage_metadata.input_tokens` | `91` | `91` | 输入 token：字段名被标准化为 input_tokens |
| `usage.completion_tokens` | `usage_metadata.output_tokens` | `73` | `73` | 输出 token：字段名被标准化为 output_tokens |
| `usage.total_tokens` | `usage_metadata.total_tokens` | `164` | `164` | 总 token |
| `usage.completion_tokens_details.reasoning_tokens` | `usage_metadata.output_token_details.reasoning` | `31` | `31` | 思维链 token：注意 LangChain 的键名是 output_token_details.reasoning（没有 s、词尾也不同） |
| `usage` | `response_metadata.token_usage` | `{"completion_tokens": 73, "prompt_tokens": 91,…` | `{"completion_tokens": 73, "prompt_tokens": 91,…` | openai 的 usage 原始结构整包也保留一份（双份并存：标准化版 + 原始版） |
| `choices[0].message.provider_specific_fields` | `additional_kwargs` | `{"refusal": null, "reasoning_content": "We nee…` | `{"refusal": null}` | 厂商扩展收纳：本次只有 refusal 进了 additional_kwargs，里面的 reasoning_content 同样没被搬运 |
| `object` | （消失，不再往下传） | `chat.completion` | — | 类型标记：openai SDK 反序列化时就消费掉了，用完即弃 |
| `created` | （消失，不再往下传） | `1791891142` | — | Unix 时间戳：LangChain 不保留 |
| `choices[0].index` | （消失，不再往下传） | `0` | — | 候选序号：n=1 时无意义 |
| `metadata` | （消失，不再往下传） | `{"weight_version": "default"}` | — | 网关元数据（weight_version）：LangChain 不认识的字段直接丢弃 |

> 表里只列主要的映射关系；两边**全部**字段的完整清单见第五章（一个叶子字段都不漏）。

## 五、两层完整字段清单（全量，无省略）

### 1. 第 1 层（原始 JSON）的全部叶子字段

| # | 字段路径 | 本次值 |
| --- | --- | --- |
| 1 | `id` | `a6a5e64a963148a88a5d7249e40535b8` |
| 2 | `created` | `1791891142` |
| 3 | `model` | `deepseek-v4-flash-sz` |
| 4 | `object` | `chat.completion` |
| 5 | `choices[0].finish_reason` | `stop` |
| 6 | `choices[0].index` | `0` |
| 7 | `choices[0].message.content` | `HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方法、目标、客户端能力、认证信息、内容类型等附加信…` |
| 8 | `choices[0].message.role` | `assistant` |
| 9 | `choices[0].message.reasoning_content` | `We need answer in Chinese. User asks "用一句话说明什么是 HTTP 请求头" Need one sen…` |
| 10 | `choices[0].message.provider_specific_fields.refusal` | `null` |
| 11 | `choices[0].message.provider_specific_fields.reasoning_content` | `We need answer in Chinese. User asks "用一句话说明什么是 HTTP 请求头" Need one sen…` |
| 12 | `choices[0].provider_specific_fields.matched_stop` | `1` |
| 13 | `usage.completion_tokens` | `73` |
| 14 | `usage.prompt_tokens` | `91` |
| 15 | `usage.total_tokens` | `164` |
| 16 | `usage.completion_tokens_details.reasoning_tokens` | `31` |
| 17 | `usage.completion_tokens_details.text_tokens` | `42` |
| 18 | `metadata.weight_version` | `default` |

### 2. 第 3 层（AIMessage model_dump）的全部顶层字段

| # | 字段 | 本次值 |
| --- | --- | --- |
| 1 | `content` | `HTTP 请求头是客户端在发送 HTTP 请求时附带的键值对元数据，用来向服务器说明请求的方法、目标、客户端能力、认证信息、内容类型等附加信…` |
| 2 | `additional_kwargs` | `{"refusal": null}` |
| 3 | `response_metadata` | `{"token_usage": {"completion_tokens": 73, "prompt_tokens": 91, "total_…` |
| 4 | `type` | `ai` |
| 5 | `name` | `null` |
| 6 | `id` | `lc_run--01a13508-f219-7bb2-8d44-51e2b9582473-0` |
| 7 | `tool_calls` | `[]` |
| 8 | `invalid_tool_calls` | `[]` |
| 9 | `usage_metadata` | `{"input_tokens": 91, "output_tokens": 73, "total_tokens": 164, "input_…` |

### 3. 哪些是搬运、哪些是消失、哪些是新增（以本次实测为准）

- **搬运**：`content`、`finish_reason`、`model`、`usage` 全家、原始 `id`（进 response_metadata.id）
- **消失**：`object`、`created`（SDK 层消费掉）、`choices[0].index`（单候选无意义）、`metadata.weight_version`（网关扩展不认识）、
  **`reasoning_content`（思维链！langchain-openai 1.x 的转换没搬运它，要看思维链只能去原始层）**
- **新增（LangChain 自有）**：`type: 'ai'`（表达 role=assistant）、`id`（lc_run-- 前缀的运行 ID）、`name`、`tool_calls` / `invalid_tool_calls`（工具调用槽位，本次为空）
- **双份保留**：token 用量既有标准化版 `usage_metadata`，又有原始版 `response_metadata.token_usage`；
  `response_metadata` 里的 `model_provider` / `system_fingerprint` / `logprobs` 则是转换层补齐的元数据槽位

## 六、为什么要隔这一层：LangChain 的设计动机

类比 Java：外部第三方 API 的响应 DTO 一般不会直接渗透进业务层，而是转成自己的
domain model（适配器模式）。LangChain 做的就是这件事，收益有三：

1. **跨厂商统一**：LangChain / LangGraph 的上层组件（agent、memory、graph）只认
   AIMessage 这套模型。哪天把 OpenAI 换成 Anthropic、Ollama，响应 JSON 的字段名
   各不相同（比如 token 用量各家叫法都不一样），但 `invoke()` 的返回值结构不变，
   上层代码一行不用改。
2. **字段名标准化**：`prompt_tokens`→`input_tokens`、`role: assistant`→`type: 'ai'`，
   把各家的方言翻译成一套统一词汇。
3. **厂商扩展尽量不丢（但不保证全搬）**：统一的同时开了两个"杂物抽屉"——`additional_kwargs`
   （消息级扩展，本次收了 `refusal`）和 `response_metadata`（响应级元数据，原始 `id`、`token_usage` 都在）。
   但注意本次实测：**`reasoning_content` 没有被搬运**——想拿思维链得自己去原始层截（第二章那种），
   这是用统一模型要留意的代价。

另外注意：流式调用时第 1 层的形态不是单个 JSON，而是 SSE 分块文本流
（`chat.completion.chunk` 序列，见 stream_response.md 与 sse_raw_demo.py）；
分块累加（merge_chunks_demo.py 的 `+`）后与 invoke 的 AIMessage 同构——
统一模型让"流式 / 非流式"在上层看起来也是一套东西。

## 七、想自己拿到原始 JSON 的三种办法

1. **curl 直接调**：request_payload.md 每一章第 7 节都有现成的等价 curl 命令，
   把脱敏值换成 agent/llm.py 里的完整密钥即可，拿到的就是本文件第二章这种 JSON。
2. **httpx 响应钩子**：本脚本的做法，与请求钩子（dump_request.py）互为镜像，
   适合想在 LangChain 体系里顺手截一份的场景。
3. **绕过 LangChain 直用 openai SDK**：`OpenAI(...).chat.completions.create(...)`
   返回 `ChatCompletion` 对象（链条第 2 层），`model_dump_json()` 一下就是与原始 JSON
   同构的文本——LangChain 底下用的正是它。
