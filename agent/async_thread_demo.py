"""
"让出线程"到底是什么意思？—— 单线程多协程实验

先回顾 Java 的模型：
  一个任务独占一个线程（线程池里每个 worker 服务一个任务）。
  IO 阻塞时，OS 把这个线程挂起（它退出可运行队列，不占 CPU），
  CPU 转去跑其他就绪线程。但线程资源本身还被这个任务占着，
  别的任务用不了它 —— 所以 Java 里不存在"让出线程"，线程是任务私有的。

asyncio 的模型完全不同：
  成千上万个协程共享同一个线程，线程是所有任务共用的公共资源。
  协程在 await 处暂停自己（执行状态存到堆上的协程对象里，不占线程），
  线程立刻转身去跑"下一个就绪的协程" —— 这就是"让出线程"的准确含义：
  让出的是"线程的执行机会"（控制权还给事件循环），而不是 CPU 切片。

本实验证明两件事：
  1. 两个任务自始至终跑在同一个线程上（它们打印的线程名相同）；
  2. 收 LLM 数据的任务在等待网络时，同一个线程在跑定时打点任务（输出交错）。

运行方式（项目根目录下）：
    .venv\\Scripts\\python.exe -m agent.async_thread_demo
"""

import asyncio
import threading
import time

from langchain_core.messages import HumanMessage

try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = "用 150 字左右介绍一下你自己"


async def ticker(start: float) -> None:
    """背景任务：每隔 0.4s 打一次点，用来证明"等待 LLM 数据时线程没闲着"。"""
    i = 0
    while True:
        i += 1
        elapsed = time.perf_counter() - start
        print(f"\n[ticker] 第 {i} 次打点 t={elapsed:.2f}s 线程={threading.current_thread().name}")
        # asyncio.sleep 本身也是一个让出点：这条语句会暂停本协程，把线程还给事件循环
        await asyncio.sleep(0.4)


async def llm_task(start: float) -> None:
    """主任务：异步流式接收 LLM 输出。"""
    n_chunks = 0
    first_at = None

    async for chunk in llm.astream([HumanMessage(QUESTION)]):
        if first_at is None:
            first_at = time.perf_counter() - start
        print(chunk.content, end="", flush=True)
        n_chunks += 1

    total = time.perf_counter() - start
    print(f"\n[llm] 首块 {first_at:.2f}s，共 {n_chunks} 块，线程={threading.current_thread().name}")


async def main() -> None:
    start = time.perf_counter()
    print(f"[main] 主线程: {threading.current_thread().name}（下面两个任务共用这一个线程）")

    # create_task：把协程注册进事件循环开始调度，类似把任务丢进线程池
    ticker_task = asyncio.create_task(ticker(start))

    # 等 LLM 收完。这期间事件循环在 ticker 和 llm_task 之间轮流跑：
    # 谁到了 await 让出点，另一个就上线程执行
    await llm_task(start)

    # LLM 收完了，打点任务没用了，取消它（相当于 Java 的 interrupt）
    ticker_task.cancel()
    try:
        await ticker_task
    except asyncio.CancelledError:
        pass

    print(f"[main] 总耗时 {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
