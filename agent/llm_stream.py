"""
流式 vs 非流式 调用对比 Demo

复用 agent/llm.py 里的同一个 llm 对象，对比三种典型调用方式：

1. invoke  —— 同步非流式：等模型把全部内容生成完，一次性返回 AIMessage
              （类似 Java 里 RestTemplate / Feign 的同步阻塞调用）
2. stream  —— 同步流式：返回一个生成器，服务端每生成一小段就 yield 一个 AIMessageChunk
              （类似 Java 8 的 Stream 惰性迭代，边拿边处理）
3. astream —— 异步流式：async for 逐块接收，等待网络数据时不阻塞线程
              （类似 Java 里 WebClient 返回 Flux<String> 的响应式流）

运行方式（在项目根目录下执行）：
    python -m agent.llm_stream            # 依次跑完 invoke / stream / astream
    python -m agent.llm_stream stream     # 只跑指定的某一种
"""

import asyncio
import sys
import time

from langchain_core.messages import HumanMessage

# 兼容两种运行方式：
#   python -m agent.llm_stream   -> 能找到 agent 这个包，走 agent.llm
#   python agent\\llm_stream.py  -> sys.path 里只有 agent 目录，直接 import 同级的 llm
try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = "用 300 字左右介绍一下你自己，并说明你能帮我做什么"


def _print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def run_invoke() -> None:
    """【对比组】非流式调用：阻塞到完整结果生成完毕才返回。"""
    _print_header("【1】invoke 非流式：等待全部生成完，一次性返回")

    start = time.perf_counter()
    response = llm.invoke([HumanMessage(QUESTION)])
    total = time.perf_counter() - start

    print(response.content)

    print(f"\n[统计] 总耗时 {total:.2f}s —— 这段时间里终端一直空着，什么内容都看不到")
    print(f"[统计] 返回类型: {type(response).__name__}，完整消息一次性拿全")
    print(f"[统计] token 用量 usage_metadata: {response.usage_metadata}")


def run_stream() -> None:
    """【实验组 A】同步流式调用：生成器逐块 yield 增量内容。"""
    _print_header("【2】stream 同步流式：边生成边打印")

    start = time.perf_counter()
    first_chunk_at = None
    chunks = []

    for chunk in llm.stream([HumanMessage(QUESTION)]):
        if first_chunk_at is None:
            # 第一个块到达的时刻，即用户"看到字"的时间（TTFT, time to first token）
            first_chunk_at = time.perf_counter() - start
        # end="" 不换行拼接；flush=True 立即刷出缓冲区，
        # 否则 print 会攒着缓冲，流式效果会变成"一顿一顿"地出字
        print(chunk.content, end="", flush=True)
        chunks.append(chunk)

    total = time.perf_counter() - start

    print(f"\n\n[统计] 首块到达 {first_chunk_at:.2f}s，总耗时 {total:.2f}s，共收到 {len(chunks)} 个块")
    print(f"[统计] 单块类型: {type(chunk).__name__}，可理解为 AIMessage 的'增量切片'")

    # 块与块之间支持用 + 累加，拼回来就等价于一次 invoke 的完整返回
    merged = chunks[0]
    for c in chunks[1:]:
        merged = merged + c
    print(f"[统计] 用 + 拼接后: {type(merged).__name__}，内容长度 {len(merged.content)}")
    print(f"[统计] 末块 usage_metadata: {merged.usage_metadata}（token 用量一般随最后一个块才回传）")



async def run_astream() -> None:
    """【实验组 B】异步流式调用：等待期间不占用线程。"""
    _print_header("【3】astream 异步流式：async for 逐块接收")

    start = time.perf_counter()
    first_chunk_at = None
    n_chunks = 0

    async for chunk in llm.astream([HumanMessage(QUESTION)]):
        if first_chunk_at is None:
            first_chunk_at = time.perf_counter() - start
        print(chunk.content, end="", flush=True)
        n_chunks += 1

    total = time.perf_counter() - start

    print(f"\n\n[统计] 首块到达 {first_chunk_at:.2f}s，总耗时 {total:.2f}s，共收到 {n_chunks} 个块")
    print("[统计] 输出内容与 stream 一致，区别在 IO 模型：异步等待时当前线程可以去处理其它任务")


if __name__ == "__main__":
    demos = {
        "invoke": run_invoke,
        "stream": run_stream,
        "astream": lambda: asyncio.run(run_astream()),
    }
    # python -m agent.llm_stream [invoke|stream|astream]，不带参数则全部执行
    choice = sys.argv[1] if len(sys.argv) > 1 else "all"
    if choice == "all":
        for fn in demos.values():
            fn()
    else:
        demos[choice]()
