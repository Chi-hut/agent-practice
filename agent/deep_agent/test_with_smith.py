import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

# langsmith 用 lru_cache 缓存环境变量，必须在任何 langchain/deepagents 导入之前加载 .env
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.messages import HumanMessage
from langchain_core.tracers.langchain import wait_for_all_tracers
from agent.llm import llm

if os.getenv("LANGSMITH_TRACING", "").lower() != "true" or not os.getenv("LANGSMITH_API_KEY"):
    print("警告：未配置 LANGSMITH_TRACING=true 或 LANGSMITH_API_KEY，本次运行不会上报 LangSmith")

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

#3. LangSmith 链路追踪配置：run_name/tags/metadata 会显示在 trace 上，便于筛选
run_id = uuid4()
config = {
    "run_name": "deep_agent_with_smith",
    "run_id": run_id,
    "tags": ["deep_agent", "practice"],
    "metadata": {"script": "test_with_smith.py", "workspace": str(workspace_dir)},
}

response = agent.invoke(
    {"messages": [HumanMessage(content="你好，我的爱好是什么")]},
    config=config,
)
print(response["messages"][-1].content)

# trace 由后台线程批量上传，脚本退出前须等待上传完成，否则可能丢失
wait_for_all_tracers()
print(f"LangSmith 项目: {os.getenv('LANGSMITH_PROJECT', 'default')}，根 run_id: {run_id}")
