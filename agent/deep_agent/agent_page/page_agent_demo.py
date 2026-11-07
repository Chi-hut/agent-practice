"""主 agent 调子 agent 查分页数据，用户接着说“下一页”的演示（全部使用模拟数据）。

运行（必须从项目根目录以模块方式执行）：
    .venv/Scripts/python.exe -m agent.deep_agent.agent_page.page_agent_demo

debug 时重点看三处：
1. task 工具：主 agent 把“页码”写进 description，交给 page-agent；
2. query_page 工具：子 agent 根据页码取模拟数据，返回 next_page；
3. 用户说“下一页”：主 agent 从历史消息里找到上一轮的 next_page，再发起一次 task。

关键结论：deepagents 每次用 task 调子 agent 时，都会把子 agent 的 messages 替换成
一条 description（其它 state 字段仍会复制过去），所以子 agent 没有上一轮对话记忆。
见 deepagents/middleware/subagents.py 的 _validate_and_prepare_state。
因此翻页状态必须由主 agent 保存，并在 description 里显式传页码。
"""

import json

from deepagents import create_deep_agent
from langchain.agents.middleware import wrap_tool_call, wrap_model_call
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.llm import llm


# ---------------- 1. 模拟数据：一共 12 条，每页 3 条，共 4 页 ----------------

MOCK_ORDERS = [
    {"id": 1001, "product": "机械键盘", "amount": 399, "status": "已发货"},
    {"id": 1002, "product": "显示器", "amount": 1299, "status": "待付款"},
    {"id": 1003, "product": "鼠标垫", "amount": 39, "status": "已完成"},
    {"id": 1004, "product": "USB-C 扩展坞", "amount": 259, "status": "已发货"},
    {"id": 1005, "product": "降噪耳机", "amount": 899, "status": "待付款"},
    {"id": 1006, "product": "升降桌", "amount": 1599, "status": "已完成"},
    {"id": 1007, "product": "人体工学椅", "amount": 2199, "status": "已发货"},
    {"id": 1008, "product": "笔记本支架", "amount": 129, "status": "已完成"},
    {"id": 1009, "product": "摄像头", "amount": 499, "status": "待付款"},
    {"id": 1010, "product": "麦克风", "amount": 699, "status": "已发货"},
    {"id": 1011, "product": "移动硬盘", "amount": 559, "status": "已完成"},
    {"id": 1012, "product": "路由器", "amount": 349, "status": "已发货"},
]


# ---------------- 2. 子 agent 使用的分页工具 ----------------

@tool
def query_page(page: int = 1, page_size: int = 3) -> str:
    """分页查询订单模拟数据。page 从 1 开始，返回 JSON 字符串，next_page 为 null 表示没有下一页。"""

    total = len(MOCK_ORDERS)
    total_pages = (total + page_size - 1) // page_size

    if page < 1:
        page = 1

    if page > total_pages:
        return json.dumps(
            {"page": page, "total_pages": total_pages, "rows": [], "next_page": None, "message": "没有更多数据"},
            ensure_ascii=False,
        )

    start = (page - 1) * page_size
    result = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "rows": MOCK_ORDERS[start:start + page_size],
        "next_page": page + 1 if page < total_pages else None,
    }

    print(f"[query_page 执行] page={page}，返回 {len(result['rows'])} 条，next_page={result['next_page']}")
    return json.dumps(result, ensure_ascii=False)


# ---------------- 3. 中间件：打印每次工具调用，区分主/子 agent ----------------

@wrap_tool_call
def log_tool_call(request, handler):
    name = request.tool_call["name"]
    args = request.tool_call["args"]
    # 主 agent 调 task 时，这里看到的是主 agent 的完整历史；
    # 子 agent 调 query_page 时，这里只有子 agent 自己的消息（没有主 agent 历史）。
    state_count = len(request.runtime.state.get("messages", []))
    print(f"\n[工具调用] {name} args={args} 当前 state 消息数={state_count}")

    result = handler(request)

    if hasattr(result, "update"):  # task 工具返回 Command，子 agent 的最终回答在 update 里
        content = result.update["messages"][-1].content
    else:
        content = result.content
    print(f"[工具返回] {name}: {str(content)[:300]}")

    return result

@wrap_model_call
def log_model_call(request, handler):
    # print(f"[模型调用] {request.prompt}")
    result = handler(request)
    # print(f"[模型返回] {result.content}")
    return result


# ---------------- 4. 子 agent 和主 agent 的配置 ----------------

page_subagent = {
    "name": "page-agent",
    "description": "分页查询订单数据的子 agent。传入页码 page，返回该页订单和下一页页码 next_page。",
    "system_prompt": (
        "你是分页查询助手。收到查询请求后必须调用 query_page 工具，不要编造数据。"
        "拿到工具结果后，把 JSON 原样作为最终回答，必须保留 page、rows、next_page 字段。"
    ),
    "tools": [query_page],
    "middleware": [log_tool_call,log_model_call],
}

# MAIN_PROMPT = """你是订单查询助手。
# 查询订单数据只允许调用 task 工具，subagent_type 固定填 "page-agent"，不要自己回答数据。
# 调用 task 时，description 里必须写清楚要查询的页码，例如：“查询第 1 页订单”。
# 子 agent 每轮都拿不到上一轮对话，只会在 messages 里看到你写的 description，所以页码一定要写进去。
# 如果用户说“下一页”，先从上一次 page-agent 返回的 JSON 中找到 next_page，
# 再把这个数字作为页码写进新的 task description；next_page 为 null 就告诉用户没有更多数据。"""

MAIN_PROMPT = """你是查询助手。可以借助工具完成用户请求。"""

agent = create_deep_agent(
    model=llm,
    system_prompt=MAIN_PROMPT,
    middleware=[log_model_call,log_tool_call],
    subagents=[page_subagent],
    # 没有 checkpointer 的话，第二次 stream 看不到第一次的对话，主 agent 就找不到 next_page
    checkpointer=InMemorySaver(),
)


# ---------------- 5. 连续多轮请求，模拟用户翻页 ----------------

CONFIG = {"configurable": {"thread_id": "page-demo"}}


def one_line(message) -> str:
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        return "tool_calls=" + str([(call["name"], call["args"]) for call in tool_calls])
    content = message.content if isinstance(message.content, str) else str(message.content)
    return content.replace("\n", " ")[:200]


def chat(user_input: str):
    print(f"\n========== 用户：{user_input} ==========")

    # subgraphs=True：主 agent 和子 agent 内部的事件都会流出来，
    # 每个元素是 (namespace, update)，namespace 为空表示主 agent。
    for namespace, update in agent.stream(
        {"messages": [HumanMessage(user_input)]},
        config=CONFIG,
        stream_mode="updates",
        subgraphs=True,
    ):
        source = "主agent" if not namespace else "子agent"
        for node, data in update.items():
            if not isinstance(data, dict):
                continue
            messages = data.get("messages")
            # deepagents 有些中间件会写入 Overwrite 之类的对象，只打印正常的消息列表
            if not isinstance(messages, list):
                continue
            for message in messages:
                print(f"[{source}/{node}] {one_line(message)}")

    messages = agent.get_state(CONFIG).values["messages"]
    print(f"[主agent历史消息数] {len(messages)}")
    print(f"[最终答复] {messages[-1].content}")


if __name__ == "__main__":
    chat("帮我查一下第 1 页的订单")
    chat("下一页")
    chat("下一页")
