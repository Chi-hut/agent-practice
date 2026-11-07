from deepagents import create_deep_agent
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolRuntime

from agent.llm import llm
from rich import print as rprint


@tool
def my_tool(location: str,runtime:ToolRuntime):

    """
    用于查询天气的一个工具，输入是城市名，输出是天气情况
    """



    stream_writer = get_stream_writer()
    stream_writer({f"type" : "调用天气工具","message":f"调用天气工具的输出{runtime.state.keys()}"})
    return f"{location}的天气是晴天"


agent = create_deep_agent(
    model=llm,
    tools=[my_tool],
    system_prompt="你是一个 helpful的助手，请根据用户输入给出相应的输出。",
)

response = agent.stream({"messages": [HumanMessage("查询一下北京的天气")]},stream_mode="custom")
print(type(response))
# 打印流式输出
for chunk in response:
    rprint(chunk)
    # print(chunk)
    # print(chunk.content, end="", flush=True)
