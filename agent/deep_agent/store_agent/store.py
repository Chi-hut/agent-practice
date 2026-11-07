import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# 本机专用容器：docker run -p 5433:5432 postgres:16
DB_URI = os.getenv("STORE_DB_URI", "postgresql://postgres:postgres@localhost:5433/agent_store")

# StoreBackend 保存文件的命名空间：key 是文件路径，value 是 {"content": [...], "created_at": ..., "modified_at": ...}
FILES_NAMESPACE = ("filesystem",)


def dump(store, title):
    """直接读 store（不经过 agent），把当前所有文件打印出来。"""
    items = store.search(FILES_NAMESPACE, limit=100)
    print(f"\n[{title}] 共 {len(items)} 个文件")
    for item in items:
        print(f"  {item.namespace}/{item.key}  ({item.value['modified_at']})")
        for line in item.value["content"]:
            print(f"    {line}")
