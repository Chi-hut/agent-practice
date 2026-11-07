from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.llm import llm

agent = create_deep_agent(
    model=llm,
    checkpointer=InMemorySaver(),
)

# 构造一个配置存一下thread_id

config = {
    "configurable": {
        "thread_id": "user-001",
    }
}
response = agent.invoke(
    {"messages": [HumanMessage(content="你好，我的爱好是唱歌，帮我记录到like.txt文件中")],
     }, config=config)
# 循环打印message中的元素信息
# for message in response["messages"]:
#     print(message)
# print(response["files"])
print(response)
# print("=====================================")
#
# response2 = agent.invoke({"messages": [HumanMessage(content="我的爱好是什么")],
#                           }, config=config)
# for message2 in response2["messages"]:
#     print(message2)
# print(response2["files"])
