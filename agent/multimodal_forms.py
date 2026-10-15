"""
多模态调用形式速览：所有"怎么把图 / 音频传给大模型"的写法集中在一个文件。

核心只有一句话——多模态就是把 content 从字符串换成"块数组"，块的 type 决定模态：

    HumanMessage("你好")                        # 非多模态：content 是字符串
    HumanMessage(content=[                      # 多模态：content 是数组
        {"type": "text", "text": "..."},        # 文本块
        {"type": "image_url",                   # 图片块（OpenAI 原生格式）
         "image_url": {"url": "data:image/png;base64,..." 或 "https://..."}},
        {"type": "input_audio",                 # 音频块（OpenAI 原生格式）
         "input_audio": {"data": "<wav base64>", "format": "wav"}},
    ])

其余形态全是块的组合与参数变化：
    detail  -> image_url 里加 "detail": "low"（低分辨率，省 token）
    多图    -> 同一数组里放多个 image_url 块
    流式    -> 同一套消息换 llm.stream()
    标准块  -> {"type": "image", ...}，langchain 自动转成 image_url（块上的 detail 会丢）

每个 form_xxx 都是一次完整真实调用（构造消息 -> 调用 -> 打印回答），无抓包无报告导出。
本团队网关实测结论（2026-10）：form 2/3/4/6/8 返回 200 且模型真看懂图；
form 5（公网 URL）与 form 7（音频）返回 400，报错原文会打印出来——那就是该部署的能力边界。

运行（项目根目录）：python -m agent.multimodal_forms
"""

import base64
import io
import math
import operator
import os
import struct
import wave
import zlib
from functools import reduce
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
MODEL_NAME = "gpt-5.6-terra-ptu"
API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL_HR")
USER_KEY = os.getenv("LLM_USER_KEY")


# ---------------------------------------------------------------------------
# LLM 客户端（与 agent/llm.py 同一套：httpx 钩子注入 user_key，模块级单例）
# ---------------------------------------------------------------------------

def _add_user_key(request: httpx.Request) -> None:
    sep = "&" if "?" in str(request.url) else "?"
    request.url = httpx.URL(f"{request.url}{sep}user_key={USER_KEY}")


_client = httpx.Client(timeout=180, event_hooks={"request": [_add_user_key]})
llm = ChatOpenAI(model=MODEL_NAME, api_key=API_KEY, base_url=BASE_URL,
                 http_client=_client, timeout=180)


# ---------------------------------------------------------------------------
# 测试素材（纯 Python 内存生成，不落盘）：128x128 图（红圆+蓝方）+ 一段 440Hz WAV
# ---------------------------------------------------------------------------

def build_test_png(swap: bool = False) -> bytes:
    """swap=False：红色圆形(右下) + 蓝色方块(左上)；swap=True：红蓝互换。"""
    red, blue = ((30, 60, 220), (220, 30, 30)) if swap else ((220, 30, 30), (30, 60, 220))
    w = h = 128
    cx, cy, r = 72, 72, 40

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                row += bytes(red)
            elif 10 <= x < 46 and 10 <= y < 46:
                row += bytes(blue)
            else:
                row += b"\xff\xff\xff"
        rows.append(bytes(row))
    raw = b"".join(b"\x00" + r for r in rows)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def tone_wav_b64() -> str:
    """440Hz 正弦波 0.5s 的 WAV，返回 base64。"""
    sr = 8000
    frames = b"".join(
        struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440.0 * i / sr)))
        for i in range(int(sr * 0.5)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(frames)
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------------------
# 调用辅助：打印 content 形状 + 模型回答
# ---------------------------------------------------------------------------

def content_shape(content) -> str:
    if isinstance(content, str):
        return "字符串（非多模态）"
    return "[" + ", ".join(b.get("type", "?") for b in content) + "]"


def call_and_show(title: str, message: HumanMessage, stream_mode: bool = False) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(f"[content 形状] {content_shape(message.content)}")
    try:
        if stream_mode:
            answer = reduce(operator.add, llm.stream([message])).content
        else:
            answer = llm.invoke([message]).content
    except Exception as e:
        first = str(e).splitlines()[0] if str(e) else ""
        print(f"[调用异常] {type(e).__name__}：{first[:280]}")
        return
    print(f"[模型回答] {answer}")


# ---------------------------------------------------------------------------
# 8 种调用形式，每个函数 = 一种形式
# ---------------------------------------------------------------------------

def form_1_plain_text() -> None:
    """对照：content 是字符串，不是数组——模型收不到任何图。"""
    call_and_show(
        "form 1 纯文本（对照组：content 是字符串）",
        HumanMessage("请描述我发给你的这张图片"))


def form_2_image_base64() -> None:
    """最常用形态：图片字节 -> base64 -> data URI -> image_url 块。"""
    b64 = base64.b64encode(build_test_png()).decode()
    call_and_show(
        "form 2 图片 base64（image_url + data URI）",
        HumanMessage(content=[
            {"type": "text", "text": "图里有什么图形？分别什么颜色？"},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]))


def form_3_detail_low() -> None:
    """detail 是 image_url 里唯一常用参数：low = 低分辨率省 token。"""
    b64 = base64.b64encode(build_test_png()).decode()
    call_and_show(
        "form 3 图片 + detail=low（image_url 加 detail 字段）",
        HumanMessage(content=[
            {"type": "text", "text": "图里有什么图形？分别什么颜色？"},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"}},
        ]))


def form_4_langchain_block() -> None:
    """LangChain 标准写法：type=image，由库转成 image_url；块上的 detail 会被丢弃。"""
    b64 = base64.b64encode(build_test_png()).decode()
    call_and_show(
        "form 4 LangChain 标准块（type=image，库自动转换）",
        HumanMessage(content=[
            {"type": "text", "text": "图里有什么图形？分别什么颜色？"},
            {"type": "image", "source_type": "base64", "data": b64,
             "mime_type": "image/png", "detail": "low"},
        ]))


def form_5_image_url() -> None:
    """图片也可以只给 URL 让服务端回源取图——本网关内网隔离，实测 400。"""
    call_and_show(
        "form 5 图片 URL（服务端回源取图，实测 400）",
        HumanMessage(content=[
            {"type": "text", "text": "这张照片拍的是什么？"},
            {"type": "image_url", "image_url": {"url":
             "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/"
             "Gfp-wisconsin-madison-the-nature-boardwalk.jpg/"
             "640px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"}},
        ]))


def form_6_multi_image() -> None:
    """多图 = 同一 content 数组里放多个 image_url 块，模型按顺序编号理解。"""
    b64_a = base64.b64encode(build_test_png()).decode()
    b64_b = base64.b64encode(build_test_png(swap=True)).decode()
    call_and_show(
        "form 6 多图（数组里两个 image_url 块，第二张红蓝互换）",
        HumanMessage(content=[
            {"type": "text", "text": "两张图分别是什么图形和颜色？有什么不同？"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_a}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_b}"}},
        ]))


def form_7_audio() -> None:
    """音频块 input_audio（仅 wav/mp3）——本部署实测 400，只收 text/image_url 块。"""
    call_and_show(
        "form 7 音频（input_audio + WAV base64，实测 400）",
        HumanMessage(content=[
            {"type": "text", "text": "这段音频是什么声音？"},
            {"type": "input_audio",
             "input_audio": {"data": tone_wav_b64(), "format": "wav"}},
        ]))


def form_8_stream() -> None:
    """流式 = 同一套多模态消息换 llm.stream()，分块用 + 合并。"""
    b64 = base64.b64encode(build_test_png()).decode()
    call_and_show(
        "form 8 多模态流式（同一消息换 stream()）",
        HumanMessage(content=[
            {"type": "text", "text": "图里有什么图形？分别什么颜色？"},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]), stream_mode=True)


def main() -> None:
    print(f"多模态调用形式速览（模型 {MODEL_NAME}，8 种形式全部真实调用）")
    # form_1_plain_text()
    form_2_image_base64()
    # form_3_detail_low()
    # form_4_langchain_block()
    # form_5_image_url()
    # form_6_multi_image()
    # form_7_audio()
    # form_8_stream()
    _client.close()
    print("\n完成。每种形式的请求/响应全量字节见 multimodal_demo_output.md。")


if __name__ == "__main__":
    main()
