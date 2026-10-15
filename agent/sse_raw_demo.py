"""
底层验证：stream 到底是不是"一次请求、很多次响应"？

绕开 LangChain，直接用 httpx 向网关发一次 stream=true 的原始请求，
亲眼看看 HTTP 层面到底发生了什么：

- 请求：只有 1 次 POST
- 响应：只有 1 个响应（content-type: text/event-stream，即 SSE 事件流）
- 但这 1 个响应的 body 是分很多段陆续到达的：每段是一行 data: 开头的 JSON
  LangChain 把每一段包装成一个 AIMessageChunk，这就是"分段列表"的来源

运行方式（在项目根目录下执行）：
    python -m agent.sse_raw_demo
    python agent\\sse_raw_demo.py
"""

import json
import time

# 兼容两种运行方式（与 llm_stream.py 同样的处理）
try:
    from agent.llm import http_client, llm
except ImportError:
    from llm import http_client, llm

QUESTION = "用一句话介绍你自己"


def main() -> None:
    print("=" * 70)
    print("底层验证：1 次请求 -> 1 个响应 -> body 分 N 段到达")
    print("=" * 70)

    # 不经过 LangChain，按 OpenAI 兼容协议手工组一次最原始的流式请求
    url = llm.openai_api_base.rstrip("/") + "/chat/completions"
    payload = {
        "model": llm.model_name,
        "messages": [{"role": "user", "content": QUESTION}],
        "stream": True,  # 关键：声明要流式，服务端才会用 SSE 一段段推
    }
    headers = {
        "Authorization": f"Bearer {llm.openai_api_key.get_secret_value()}",
        "Content-Type": "application/json",
    }

    print(f">> 即将发出唯一的 1 次 POST 请求 ...")

    start = time.perf_counter()
    with http_client.stream("POST", url, json=payload, headers=headers) as response:
        # with 一进入，响应就建立了：状态码、响应头此刻已拿到
        print(f"\n[响应已建立] 状态码 {response.status_code}，建立耗时 {time.perf_counter() - start:.2f}s")
        print(f"[响应头] content-type = {response.headers.get('content-type')}")
        te = response.headers.get("transfer-encoding")
        if te:
            print(f"[响应头] transfer-encoding = {te}")

        print("\n>> 这同一个响应的 body 开始分多段陆续到达（每行 = 1 个 SSE 事件）:\n")
        n_data = 0        # 普通数据段数（= LangChain 将给出的 chunk 数）
        ids = set()       # 收集所有事件里的响应 id，用于证明它们同属一个响应
        shown = 0
        done_line = None

        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue  # SSE 事件之间的空行等，跳过
            body_text = line[len("data: "):]
            if body_text.strip() == "[DONE]":
                done_line = line  # 结束标记单独记，不计入数据段
                continue

            n_data += 1
            try:
                evt = json.loads(body_text)
                if evt.get("id"):
                    ids.add(evt["id"])
            except json.JSONDecodeError:
                pass

            # 原样打印前 5 段，让大家看到 data: 行的真实长相
            if shown < 5:
                shown += 1
                print(f"  第 {n_data:>3} 段: {line}")

        if done_line:
            print(f"  最后 1 段: {done_line}   <-- 服务端宣告\"说完了\"，连接这才关闭")

        total = time.perf_counter() - start
        print(f"\n[统计] 请求次数: 1 次 ｜ 响应个数: 1 个 ｜ body 分段(SSE 事件)数: {n_data}")
        print(f"[统计] 所有事件携带的响应 id 共 {len(ids)} 种 -> "
              + ("全部来自同一个响应" if len(ids) <= 1 else "存在多个响应(异常)"))
        print(f"[统计] 这 {n_data} 段就是 LangChain stream() 交给你的 {n_data} 个 AIMessageChunk")
        print(f"[统计] 总耗时 {total:.2f}s")


if __name__ == "__main__":
    main()
