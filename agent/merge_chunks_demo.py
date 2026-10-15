"""
流式分块拼回完整内容 Demo

stream 返回的是一串 AIMessageChunk（生成器，逐块产出），本文件演示三种
拿到最终完整 content 的方式，并用真实调用验证三者结果完全一致：

1. 字符串拼接：只要文本时最朴素，循环里往一个 str 上累加
2. chunk 对象 + 累加：得到一个完整的 AIMessageChunk，token 用量等元数据一并合并
3. functools.reduce 一行写法：方式 2 的函数式等价形式

运行方式（在项目根目录下执行）：
    python -m agent.merge_chunks_demo
    python agent\\merge_chunks_demo.py
"""

import operator
import time
from functools import reduce

from langchain_core.messages import HumanMessage

# 兼容两种运行方式（与 llm_stream.py 同样的处理）
try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = "用 300 字左右介绍一下你自己，并说明你能帮我做什么"


def main() -> None:
    print(">> 正在执行 stream（流式）调用 ...")
    start = time.perf_counter()
    # 关键点：stream() 返回的是生成器，只能从头到尾消费一次（和 Java 的 Stream 一样）。
    # 后面三种方式都要反复遍历，所以先用 list() 把所有分块收下来。
    chunks = list(llm.stream([HumanMessage(QUESTION)]))
    total = time.perf_counter() - start
    print(f"   共收到 {len(chunks)} 个分块，总耗时 {total:.2f}s\n")

    # ---------- 方式一：字符串拼接（只需要文本时，推荐这个） ----------
    text1 = ""
    for c in chunks:
        text1 += c.content  # 每块只有增量文字，往字符串后面接就行

    # ---------- 方式二：chunk 对象用 + 累加（还需要 token 用量等元数据时用） ----------
    # AIMessageChunk 重载了 + 运算符：content 拼接、usage 数字累加、元数据取更全的一方
    merged = chunks[0]
    for c in chunks[1:]:
        merged = merged + c

    # ---------- 方式三：reduce 一行写法（方式二的函数式等价形式） ----------
    merged2 = reduce(operator.add, chunks)

    print(f"【方式一】str 拼接        -> {len(text1)} 字")
    print(f"【方式二】chunk 逐块 +    -> {type(merged).__name__}，content {len(merged.content)} 字")
    print(f"【方式三】reduce 一行写法 -> content {len(merged2.content)} 字")

    print("\n三种方式得到的 content 完全一致：", text1 == merged.content == merged2.content)

    print("\n拼接后完整对象的 token 用量（随末块合并而来）:")
    print(f"  {merged.usage_metadata}")

    print("\n拼接出的完整文本:")
    print(text1)


if __name__ == "__main__":
    main()
