from langchain_core.messages import HumanMessage

from agent.llm import llm


response = llm.stream([HumanMessage("介绍一下你自己")])

# 打印流式输出
for chunk in response:
    print(type(chunk))
    print(chunk)
    # print(chunk.content, end="", flush=True)


