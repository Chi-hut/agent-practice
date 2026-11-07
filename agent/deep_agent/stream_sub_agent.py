from deepagents import create_deep_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer

from agent.llm import llm
from rich import print as rprint


@tool
def my_tool(location: str):
    """
    用于查询天气的一个工具，输入是城市名，输出是天气情况
    """

    stream_writer = get_stream_writer()
    stream_writer({"type" : "调用天气工具","message":"调用天气工具的输出"})
    return f"{location}的天气是晴天"


weather_subagent = {
    "name": "weather-agent",
    "description": "专门负责查询城市天气的子agent，传入要查询的城市即可",
    "system_prompt": "你是天气查询助手，必须调用 my_tool 查询天气，然后简洁地返回结果。",
    "tools": [my_tool],
}

agent = create_deep_agent(
    model=llm,
    # system_prompt="你是一个 helpful的助手。涉及天气的问题必须通过 task 工具交给 weather-agent 子agent 处理，不要自己回答。",
    subagents=[weather_subagent],
)

# subgraphs=True 时每个分块是 (namespace, mode, chunk)：namespace 为空元组表示主 agent，非空表示子图内部
response = agent.stream(
    {"messages": [HumanMessage("查询一下北京的天气")]},
    stream_mode=["updates", "custom"],
    subgraphs=True,
)

print(type(response))
for namespace, mode, chunk in response:
    source = "主agent" if not namespace else f"子图 {namespace}"
    rprint(f"[bold cyan]===== {source} | {mode} =====[/bold cyan]")
    rprint(chunk)
