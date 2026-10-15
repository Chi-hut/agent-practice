"""
LLM 响应全量信息导出 Demo

依次真实调用一次 stream（流式）和一次 invoke（非流式），把返回消息对象的
完整字段 dump 成 JSON，以 markdown 文件落盘，便于直接查看响应里到底有什么：

- stream_response.md —— 流式响应：分块累加后的完整消息 + 全部 N 个分块的完整字段（无简化）
- invoke_response.md —— 非流式响应：一次性返回的完整 AIMessage

导出内容以 pydantic 的 model_dump() 为准（等价于 model_dump_json() 的结构化版本），
包含 id、content、additional_kwargs、response_metadata、usage_metadata 等全部字段。

运行方式（在项目根目录下执行）：
    python -m agent.dump_response
    python agent\\dump_response.py

生成文件：项目根目录下 stream_response.md 与 invoke_response.md
"""

import json
import time
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage

# 兼容两种运行方式（与 llm_stream.py 同样的处理）：
#   python -m agent.dump_response        -> 能找到 agent 包，走 agent.llm
#   python agent\\dump_response.py       -> sys.path 里只有 agent 目录，直接 import 同级的 llm
try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = "用 300 字左右介绍一下你自己，并说明你能帮我做什么"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_STREAM_MD = ROOT / "stream_response.md"
OUTPUT_INVOKE_MD = ROOT / "invoke_response.md"


def to_json(obj) -> str:
    """dict -> 格式化 JSON 文本；个别字段若不是 JSON 原生类型则退化为字符串，保证一定能导出。"""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def dump_message(message) -> str:
    """把一条消息对象的所有字段转成 JSON 文本（与 model_dump_json() 等价，多了缩进美化）。"""
    return to_json(message.model_dump())


# ---------------------------------------------------------------------------
# stream：采集流式响应全量信息
# ---------------------------------------------------------------------------

def collect_stream() -> str:
    print(">> [1/2] 正在执行 stream（流式）调用，请稍等 ...")
    start = time.perf_counter()
    chunks = []
    for chunk in llm.stream([HumanMessage(QUESTION)]):
        chunks.append((round(time.perf_counter() - start, 3), chunk))
    total = time.perf_counter() - start
    ttft = chunks[0][0] if chunks else 0.0

    # 块与块之间用 + 累加，拼回来就等价于一次 invoke 的完整返回
    merged = chunks[0][1]
    for _, c in chunks[1:]:
        merged = merged + c

    md = []
    md.append("# stream 流式响应全量信息\n")
    md.append(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- 模型：`{llm.model_name}`")
    md.append(f"- 问题：{QUESTION}")
    md.append(f"- 分块数量：**{len(chunks)}** 个")
    md.append(f"- 首块到达：{ttft:.2f}s ｜ 总耗时：{total:.2f}s")
    md.append(f"- 拼接后内容长度：{len(merged.content)} 字")
    md.append(f"- 拼接方式：`chunks[0] + chunks[1] + ... + chunks[n]` → `{type(merged).__name__}`\n")

    md.append("## 一、全部分块累加后的完整消息（最核心的一份）\n")
    md.append(f"类型：`{type(merged).__name__}`，content 已是完整文本，token 用量随末块回传：\n")
    md.append("```json")
    md.append(dump_message(merged))
    md.append("```\n")

    md.append(f"## 二、全部 {len(chunks)} 个分块的完整信息（每块 model_dump 原样导出，无任何简化）\n")
    md.append(f"每一小节就是{type(chunks[0][1]).__name__}对象的全部字段，一个不省略。"
              "建议带着这几个问题逐块对比着看：\n")
    md.append("1. 每一块的 `id` 是否相同？")
    md.append("2. `content`：每块只多几个字？把所有增量按顺序连起来，是不是就得到了第一章的完整文本？")
    md.append("3. `usage_metadata`：前面的块是不是一直是 null？从哪一块开始出现 token 数字？")
    md.append("4. `chunk_position`：取值如何随分块推进（开头 / 中间 / 最后）？")
    md.append("5. `response_metadata`：中间块和最后一块的内容差别？\n")

    # 逐块完整导出：标题带到达时刻，正文是本块增量 content + 全部字段的 JSON
    for i, (t, c) in enumerate(chunks, 1):
        md.append(f"### 分块 {i} ｜ t = {t:.3f}s")
        md.append("增量 content：\n")
        md.append("```text")
        md.append(c.content if c.content else "（空字符串：本块只携带元数据，不带文字）")
        md.append("```")
        md.append("完整字段：\n")
        md.append("```json")
        md.append(dump_message(c))
        md.append("```\n")

    md.append("## 三、字段速查\n")
    md.append("- `id`：本次调用的消息 ID（LangChain 生成，同一次会话的各分块共享同一 id）")
    md.append("- `content`：消息文本；分块里只有增量，累加后才是完整内容")
    md.append("- `additional_kwargs`：厂商扩展字段（如 DeepSeek 的 reasoning_content 会出现在这里）")
    md.append("- `response_metadata`：厂商原始响应元数据（model_name / finish_reason / token_usage 等）")
    md.append("- `usage_metadata`：LangChain 标准化的 token 用量（input_tokens / output_tokens / total_tokens）")
    md.append("- `type`：消息类型标识，`AIMessageChunk` 为流式分块，`AIMessage` 为完整消息")

    text = "\n".join(md)
    OUTPUT_STREAM_MD.write_text(text, encoding="utf-8")
    print(f"   完成，首块 {ttft:.2f}s，总耗时 {total:.2f}s，共 {len(chunks)} 块")
    print(f"   已生成: {OUTPUT_STREAM_MD}")
    return text


# ---------------------------------------------------------------------------
# invoke：采集非流式响应全量信息
# ---------------------------------------------------------------------------

def collect_invoke() -> str:
    print(">> [2/2] 正在执行 invoke（非流式）调用，请稍等 ...")
    start = time.perf_counter()
    response = llm.invoke([HumanMessage(QUESTION)])
    total = time.perf_counter() - start

    md = []
    md.append("# invoke 非流式响应全量信息\n")
    md.append(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- 模型：`{llm.model_name}`")
    md.append(f"- 问题：{QUESTION}")
    md.append(f"- 总耗时：{total:.2f}s（期间阻塞等待，返回即完整）")
    md.append(f"- 返回类型：`{type(response).__name__}`")
    md.append(f"- 内容长度：{len(response.content)} 字\n")

    md.append("## 一、完整消息对象（最核心的一份）\n")
    md.append("一次性返回的完整消息，content 即全部文本，token 用量随响应直接给出：\n")
    md.append("```json")
    md.append(dump_message(response))
    md.append("```\n")

    md.append("## 二、回复正文（即 content 字段）\n")
    md.append("```text")
    md.append(response.content)
    md.append("```\n")

    md.append("## 三、与 stream 响应的结构差异\n")
    md.append("| 维度 | invoke（本文件） | stream（stream_response.md） |")
    md.append("| --- | --- | --- |")
    md.append("| 返回类型 | `AIMessage` | `AIMessageChunk`（增量切片） |")
    md.append("| content | 完整文本，一次给全 | 每块只有增量，需 `+` 累加 |")
    md.append("| 调用次数 | 1 个对象 | N 个对象（本次 N 见 stream 文件） |")
    md.append("| token 用量 | 响应直接带全 | 随最后一个分块才回传 |")
    md.append("| 字段结构 | 二者字段完全一致，仅 content 到达方式不同 ||")

    text = "\n".join(md)
    OUTPUT_INVOKE_MD.write_text(text, encoding="utf-8")
    print(f"   完成，总耗时 {total:.2f}s，内容 {len(response.content)} 字")
    print(f"   已生成: {OUTPUT_INVOKE_MD}")
    return text


if __name__ == "__main__":
    print("=" * 70)
    print("LLM 响应全量信息导出（stream / invoke 各一次真实调用）")
    print("=" * 70)
    collect_stream()
    collect_invoke()
    print("\n" + "=" * 70)
    print("两份 markdown 均已生成完毕，用编辑器或 Markdown 预览打开即可查看")
