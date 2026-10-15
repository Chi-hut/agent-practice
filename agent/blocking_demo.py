"""
阻塞等待验证 Demo：for chunk in llm.stream(...) 到底卡不卡线程？

结论：llm.stream() 是同步 API，for 循环每轮拿不到下一段时，
当前线程就阻塞在网络 read 上等待（内核挂起线程，不耗 CPU），
下一段到达才醒来继续——这就是"同步流式"里"同步"的含义。

实验一：逐轮测量循环之间的时间差（gap ≈ 阻塞等待时长），
        直观看"阻塞 -> 醒来拿一段 -> 处理 -> 再阻塞"的节奏。
实验二：单个线程里用 astream 同时跑两个流式调用 + 一个心跳协程，
        证明异步流式等待期间不阻塞线程，多路任务交错推进。

运行方式（在项目根目录下执行）：
    python -m agent.blocking_demo
    python agent\\blocking_demo.py
"""

import asyncio
import time

from langchain_core.messages import HumanMessage

# 兼容两种运行方式（与 llm_stream.py 同样的处理）
try:
    from agent.llm import llm
except ImportError:
    from llm import llm


def experiment_sync_block() -> None:
    print("=" * 70)
    print("实验一：同步 stream —— 每轮循环之间的 gap 就是阻塞等待的时长")
    print("=" * 70)

    start = time.perf_counter()
    prev = start
    gaps = []
    shown = 0

    for chunk in llm.stream([HumanMessage("用 100 字介绍 Python 的优势")]):
        now = time.perf_counter()
        gap_ms = (now - prev) * 1000  # 与上一块的时间差 ≈ 本轮阻塞等待了多久
        gaps.append(gap_ms)
        # 循环体只有一个 print（微秒级），所以 gap 几乎全是"等数据"的时间
        if shown < 10:
            shown += 1
            preview = chunk.content if chunk.content else "(本块无 content，如思考段)"
            print(f"  阻塞 {gap_ms:6.0f} ms 后醒来，拿到: {preview}")
        elif shown == 10:
            shown += 1
            print("  ...（后面每一轮都是同样的\"阻塞-醒来\"节奏，略）...")
        prev = now

    total = time.perf_counter() - start
    wait = sum(gaps) / 1000
    print(f"\n[统计] 共 {len(gaps)} 轮循环，全程 {total:.2f}s")
    print(f"[统计] 其中阻塞等待合计约 {wait:.2f}s（占全程 {wait / total * 100:.0f}%）")
    print(f"[统计] 最长一次阻塞 {max(gaps):.0f} ms，平均 {sum(gaps) / len(gaps):.0f} ms/段")
    print("[结论] 同步 stream：线程大部分时间卡在\"等下一段\"上；但每醒一次就能立刻处理一段")


async def heartbeat(times: int) -> None:
    for i in range(1, times + 1):
        await asyncio.sleep(0.3)
        print(f"      [心跳 {i}] 事件循环没有被卡住：等数据的间隙线程在跑别的协程")


async def consume(name: str, question: str) -> None:
    async for chunk in llm.astream([HumanMessage(question)]):
        if chunk.content:
            print(f"  [{name}] 收到 {len(chunk.content)} 字: {chunk.content[:14]}")


async def experiment_async_nonblock() -> None:
    print("\n" + "=" * 70)
    print("实验二：astream —— 同一个线程，两个流 + 一个心跳交错推进")
    print("=" * 70)
    await asyncio.gather(
        consume("流A", "用一句话写春天的诗"),
        consume("流B", "用一句话写秋天的诗"),
        heartbeat(8),
    )
    print("[结论] astream 在等数据的间隙把线程还给事件循环：单线程同时养活多个流+心跳")
    print("       （对照 Java：stream ≈ OkHttp 同步调用逐块读；astream ≈ WebClient 返回 Flux）")


if __name__ == "__main__":
    experiment_sync_block()
    asyncio.run(experiment_async_nonblock())
