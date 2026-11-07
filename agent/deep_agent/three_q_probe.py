import shutil, tempfile
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from agent.llm import llm

ws = Path(tempfile.mkdtemp()) / "agent_workspace"
shutil.copytree(r"E:\project\code\agent_practice\agent\deep_agent\agent_workspace", ws)
backend = FilesystemBackend(root_dir=ws, virtual_mode=True)

print("########## Q2: 虚拟路径 -> 真实路径映射（不调模型）")
for p in ["/like.txt", "like.txt", "/sub/deep/f.txt", "/../evil.txt"]:
    try:
        print(f"  {p!r:18} -> {backend._resolve_path(p)}")
    except ValueError as e:
        print(f"  {p!r:18} -> ValueError: {e}")
print("  backend.read('/like.txt') =", repr(backend.read("/like.txt")))
print("  backend.read('like.txt')  =", repr(backend.read("like.txt")))


@tool
def big_report(topic: str) -> str:
    """生成一份关于指定主题的超长调研报告，返回大量文本。"""
    return "".join(f"第{i}行：这是关于{topic}的调研内容，编号{i:06d}，用于测试大结果转存。\n" for i in range(1, 4001))


agent = create_deep_agent(model=llm, backend=backend, tools=[big_report])

print("\n########## Q1: 多步任务，观察 AIMessage 是否边干活边说话")
r1 = agent.invoke({"messages": [HumanMessage(
    content="先制定一个 todo 计划，然后分别创建 a.txt、b.txt、c.txt 三个文件，内容依次是 1、2、3，"
            "最后读回三个文件确认内容正确并汇总告诉我")]})
for i, m in enumerate(r1["messages"]):
    tc = [c["name"] for c in getattr(m, "tool_calls", [])]
    if type(m).__name__ == "AIMessage":
        print(f"  msg{i} AIMessage  有文字={bool(m.content)} 文字={m.content!r:.70} 工具调用={tc}")
    else:
        print(f"  msg{i} {type(m).__name__:<12} {m.content!r:.60}")

print("\n########## Q3: 超大工具结果 -> 转存 + 分页读取")
print("  工具原始返回字符数:", len(big_report.invoke({"topic": "测试"})))
r2 = agent.invoke({"messages": [HumanMessage(
    content="调用 big_report 工具生成一份关于'人工智能'的调研报告，"
            "然后只读取该报告的第 2000 行到第 2010 行，把这几行原样告诉我")]})
for i, m in enumerate(r2["messages"]):
    tc = [(c["name"], c["args"]) for c in getattr(m, "tool_calls", [])]
    if tc:
        print(f"  msg{i} AIMessage 工具调用={tc}")
    elif type(m).__name__ == "ToolMessage":
        print(f"  msg{i} ToolMessage name={m.name} 长度={len(m.content)}\n{m.content[:900]}\n    ......")
    else:
        print(f"  msg{i} {type(m).__name__:<12} {m.content!r:.90}")
print("  state files keys:", list(r2.get("files", {})))
for k, v in r2.get("files", {}).items():
    if k.startswith("/large_tool_results"):
        print(f"    {k}: {len(v['content'])} 行, 首行={v['content'][0]!r:.60}")
