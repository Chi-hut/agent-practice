import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# 创建带 user_key 注入的 http 客户端
def add_user_key(request: httpx.Request):
    sep = "&" if "?" in str(request.url) else "?"
    request.url = httpx.URL(f"{request.url}{sep}user_key={os.getenv('LLM_USER_KEY')}")


# 异步客户端内部执行 hook 的方式是 await hook(request)，
# 所以同一个逻辑必须包装成 async 函数注册，否则 await 同步函数的返回值 None 会报 TypeError
async def add_user_key_async(request: httpx.Request):
    add_user_key(request)


# trust_env=False：内网网关必须直连，不能被系统代理（如访问 LangSmith 开的代理）接管
http_client = httpx.Client(event_hooks={"request": [add_user_key]}, trust_env=False)
async_http_client = httpx.AsyncClient(event_hooks={"request": [add_user_key_async]}, trust_env=False)

llm = ChatOpenAI(
    model="deepseek-v4-flash-sz",
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL_V1"),
    http_client=http_client,
    http_async_client=async_http_client,
)

# 只有直接运行本文件时才发起调用（类似 Java 的 public static void main）。
# 这样其它文件可以安全地 from agent.llm import llm，不会在 import 时就触发一次真实请求。
if __name__ == "__main__":
    response = llm.invoke([HumanMessage("介绍一下你自己")])
    print(response.content)
    print(response.model_dump_json())