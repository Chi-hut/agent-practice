from deepagents import create_deep_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolRuntime

from agent.llm import llm
from rich import print as rprint


@tool
def my_tool(location: str, runtime: ToolRuntime):
    """
    用于查询天气的一个工具，输入是城市名，输出是天气情况
    """

    # stream_writer = get_stream_writer()
    # stream_writer({f"type": "调用天气工具", "message": f"调用天气工具的输出{runtime.state.keys()}"})
    return f"{location}的天气是晴天"

@wrap_tool_call
def my_middleware(request,handler):
    print(request, flush=True)
    result = handler(request)
    print(result, flush=True)
    return result



subagent_config = {
    "name": "subagent",
    "description":"天气查询助手",
    "tools": [my_tool],
    "system_prompt": "你是一个 helpful的助手，请根据用户输入给出相应的输出。",
    "middleware": [my_middleware],
}

agent = create_deep_agent(
    model=llm,
    system_prompt="你是人工助手，请根据用户输入调用相应的工具给出相应的输出。",
    middleware=[my_middleware],
    subagents=[subagent_config],
)



if __name__ == "__main__":
    response = agent.stream({"messages": [HumanMessage("查询一下北京的天气")]}, stream_mode="updates")
    # 打印流式输出
    for chunk in response:
        rprint(chunk)
        # print(chunk)
        # print(chunk.content, end="", flush=True)

