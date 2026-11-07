import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

# LangSmith 开关在 import langchain 时读取并缓存，必须先加载 .env
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from langchain_core.messages import HumanMessage
from langchain_core.tracers.langchain import wait_for_all_tracers
from langgraph.store.postgres import PostgresStore

from agent.deep_agent.store_agent.store import DB_URI, FILES_NAMESPACE, dump
from agent.llm import llm


def main():
    with PostgresStore.from_conn_string(DB_URI) as store:
        store.setup()  # 首次运行建表，重复执行安全

        # 不传 tools：文件读写全靠 FilesystemMiddleware 自动挂载的
        # ls / read_file / write_file / edit_file / glob / grep，最终落到下面的 store
        agent = create_deep_agent(
            model=llm,
            store=store,
            backend=lambda runtime: StoreBackend(
                runtime, namespace=lambda ctx: FILES_NAMESPACE
            ),
            system_prompt="你是一个助手。需要记录信息时，用 write_file 写到 /notes/ 目录下。",
        )

        config = {
            "run_name": "store_backend_agent",
            "run_id": uuid4(),
            "tags": ["deep_agent", "store", "postgres", "store_backend"],
            "metadata": {"script": "store_agent/main.py"},
        }

        # 第 1 轮：模型调 write_file，把内容写进 store
        print("=== 用户：把我的爱好打羽毛球写到 /notes/hobby.md ===")
        result = agent.invoke(
            {"messages": [HumanMessage("把我的爱好是打羽毛球这件事写到 /notes/hobby.md")]},
            config=config,
        )
        print("agent：", result["messages"][-1].content)

        # 第 2 轮：全新一次调用（相当于新会话），模型调 ls + read_file 从 store 读
        print("\n=== 用户：看看 /notes 下有什么，读出 /notes/hobby.md 的内容 ===")
        result = agent.invoke(
            {"messages": [HumanMessage("看看 /notes 目录下有哪些文件，然后读出 /notes/hobby.md 的内容")]},
            config=config,
        )
        print("agent：", result["messages"][-1].content)

        # 直接读 PG，验证文件确实存在 store 里，而不是 agent 的内存里
        dump(store, "agent 运行后，直接读 store")

        # 也可以按文件路径精确 get，和 write_file 的路径一一对应
        item = store.get(FILES_NAMESPACE, "/notes/hobby.md")
        print(f"\nstore.get(('filesystem',), '/notes/hobby.md') -> {item.value}")

    wait_for_all_tracers()
    print(f"\nLangSmith 项目：{os.getenv('LANGSMITH_PROJECT')}（https://smith.langchain.com）")


if __name__ == "__main__":
    main()
