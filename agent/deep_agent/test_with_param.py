from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.messages import HumanMessage
from agent.deep_agent.util.response_dump import response_to_dict, response_to_json, save_response, print_response
from agent.llm import llm
from agent.deep_agent.http_trace import trace_http
#1. 准备本地工作目录 (用 Path 改写)
workspace_dir = Path("./agent_workspace").resolve()
if not workspace_dir.exists ():
    workspace_dir.mkdir (parents=True, exist_ok=True)
print (f"Agent 的工作目录已设置为:{workspace_dir}")
#2. 配置本地文件系统后端
#virtual_mode=True 开启安全沙箱模式，限制 Agent! 只能访问 workspace_dir
backend = FilesystemBackend(root_dir=workspace_dir, virtual_mode=True)


agent = create_deep_agent(
    model=llm,
    backend=backend,
)

# response = agent.invoke(
#     {"messages": [HumanMessage(content="你好，我的爱好是唱歌，帮我记录到like.txt文件中")],
#      }, config=config)

with trace_http():                                     # 用 with 包住 invoke
    response = agent.invoke(
        {"messages": [HumanMessage(content="你好，我的爱好是什么")],
         })


# data = response_to_json(response)
# print(data)



