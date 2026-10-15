import sys
import importlib

print("Python", sys.version.split()[0])
mods = [
    "langchain", "langgraph", "mcp", "fastapi", "ollama", "openai",
    "langchain_mcp_adapters", "langchain_ollama", "fastmcp", "psycopg",
    "langchain_openai", "langchain_deepseek", "langchain_anthropic",
]
for m in mods:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", "ok")
        print(f"{m:28s} -> {ver}")
    except Exception as e:
        print(f"{m:28s} -> FAIL: {e}")
