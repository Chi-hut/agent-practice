"""
多模态输入输出全量示例 Demo（图片 base64 / URL / detail / 多图 / 音频 / 流式）

背景：团队模型清单里的 8 组配置已用 agent/multimodal_matrix_check.py 逐一实测，
只有 gpt-5.6-terra-ptu / gpt-5.6-terra-standby 真支持图片理解（其余要么 400 拒图，
要么 200 但把图片悄悄丢掉，详见报告附录 A 的矩阵）。本脚本用 gpt-5.6-terra-ptu
演示 OpenAI 协议下多模态参数的完整形态，请求与响应全部经 httpx event_hooks 原样截获。

用例一览（每例一次真实调用）：
1. 纯文本对照 —— content 是字符串（非多模态形态），模型收不到任何图
2. 图片 base64 —— OpenAI 原生 image_url + data URI（最常用形态）
3. 图片 + detail 参数 —— image_url 里加 detail:"low"，验证参数透传与画质影响
4. LangChain 标准内容块 —— {"type": "image", ...} 写法，看库自动转换成什么
5. 图片 URL —— image_url 传公网 https 地址（由服务端取图）
6. 多图同帧 —— 一条消息里两张图，让模型对比
7. 音频输入 —— input_audio 传 WAV，验证该部署是否支持音频
8. 多模态流式 —— stream=True + 图片，逐块收集并合并

运行方式（在项目根目录下执行）：
    python -m agent.multimodal_demo
    python agent\\multimodal_demo.py

生成文件：
    agent/test_media/           三份测试素材（两张 PNG + 一段 WAV，脚本自动生成）
    multimodal_demo_output.md   主报告（每例：构造代码 + 请求体全量 + 响应全量 + 回答核验）
    multimodal_stream_chunks.md 用例 8 的全部流式分块逐块完整字段
"""

import base64
import json
import math
import operator
import os
import re
import struct
import time
import wave
import zlib
from datetime import datetime
from functools import reduce
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

# ---------------------------------------------------------------------------
# 模型与路由（来自团队模型清单；key 与 agent/llm.py 同一套，走 hr 子路由。
# 矩阵实测该部署支持图片理解，底层模型名见响应的 model 字段）
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
MODEL_NAME = "gpt-5.6-terra-ptu"
API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL_HR")
USER_KEY = os.getenv("LLM_USER_KEY")

ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = Path(__file__).resolve().parent / "test_media"
OUT_MAIN = ROOT / "multimodal_demo_output.md"
OUT_STREAM = ROOT / "multimodal_stream_chunks.md"
MATRIX_JSON = Path(__file__).resolve().parent / "multimodal_matrix_result.json"

# 图 A 的事实（供"回答核验"对照）：红圆 + 蓝方 + 绿圆 + 算式 8+5
# 图 B 的事实：黄方 + 紫圆 + 数字 7
Q_IMAGE_A = ("请仔细看这张图：1) 图中有哪些图形，分别是什么颜色？"
             "2) 图下方写着一个算式，算式是什么、结果等于多少？")
Q_IMAGE_B = "图里画了什么？请用两三句话描述，包括图形、颜色和图中的文字。"
Q_URL = "这张照片拍的是什么场景？请简要描述你看到的。"
Q_MULTI = ("这里有两张图。请分别说明每张图里的图形、颜色和图中写的文字，"
           "再总结两张图的不同点。")
Q_AUDIO = "请听这段音频：它是什么声音？音高是如何变化的？"
PUBLIC_IMG_URL = ("https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/"
                  "Gfp-wisconsin-madison-the-nature-boardwalk.jpg/640px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg")


# ---------------------------------------------------------------------------
# 测试素材：纯 Python 生成（项目未装 Pillow）
# ---------------------------------------------------------------------------

# 5x7 点阵字体（只内置本 demo 用到的字符，需要更多可自行补充）
FONT = {
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
}


def make_png(width: int, height: int, rows: list[bytes]) -> bytes:
    """把 8 位 RGB 像素行打包成 PNG（zlib 压缩 + CRC，无任何第三方依赖）。"""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row for row in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )


def new_canvas(w: int, h: int) -> list[bytearray]:
    """白色画布：每行是 w 个像素的 RGB 字节流。"""
    return [bytearray(bytes((255, 255, 255)) * w) for _ in range(h)]


def fill_rect(rows: list[bytearray], x0: int, y0: int, x1: int, y1: int, rgb: tuple) -> None:
    for y in range(max(0, y0), min(len(rows), y1 + 1)):
        row = rows[y]
        for x in range(max(0, x0), min(len(row) // 3, x1 + 1)):
            row[x * 3:x * 3 + 3] = bytes(rgb)


def fill_circle(rows: list[bytearray], cx: int, cy: int, r: int, rgb: tuple) -> None:
    for y in range(cy - r, cy + r + 1):
        if 0 <= y < len(rows):
            for x in range(cx - r, cx + r + 1):
                if 0 <= x < len(rows[0]) // 3 and (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    rows[y][x * 3:x * 3 + 3] = bytes(rgb)


def draw_text(rows: list[bytearray], text: str, x: int, y: int, scale: int, rgb: tuple) -> None:
    """点阵字体逐字符绘制，scale 为放大倍数。"""
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is not None:
            for gy, pattern in enumerate(glyph):
                for gx, bit in enumerate(pattern):
                    if bit == "1":
                        fill_rect(rows, cx + gx * scale, y + gy * scale,
                                  cx + (gx + 1) * scale - 1, y + (gy + 1) * scale - 1, rgb)
        cx += 6 * scale


def canvas_png(rows: list[bytearray]) -> bytes:
    return make_png(len(rows[0]) // 3, len(rows), [bytes(r) for r in rows])


def build_image_a() -> bytes:
    """图 A：红圆 + 蓝方 + 绿圆 + 算式 8+5（答案 13，可客观核验模型是否真看懂）。"""
    rows = new_canvas(240, 160)
    fill_circle(rows, 40, 42, 18, (220, 30, 30))      # 红色圆形
    fill_rect(rows, 82, 24, 114, 56, (30, 60, 220))   # 蓝色正方形
    fill_circle(rows, 172, 40, 14, (30, 170, 70))     # 绿色圆形
    draw_text(rows, "8+5", 96, 106, 3, (20, 20, 20))  # 黑色算式
    return canvas_png(rows)


def build_image_b() -> bytes:
    """图 B：黄方 + 紫圆 + 数字 7（与图 A 差异明显，适合多图对比）。"""
    rows = new_canvas(240, 160)
    fill_rect(rows, 30, 24, 66, 60, (240, 190, 20))    # 黄色正方形
    fill_circle(rows, 150, 52, 20, (150, 60, 200))     # 紫色圆形
    draw_text(rows, "7", 110, 100, 4, (20, 20, 20))    # 黑色数字
    return canvas_png(rows)


def build_wav(path: Path) -> int:
    """生成三连音 WAV（A4->C5->E5 上行旋律），返回采样点数。"""
    sample_rate = 8000
    notes = [(440.00, 0.25), (523.25, 0.25), (659.25, 0.30)]  # A4 C5 E5
    gap = 0.10
    fade = int(0.02 * sample_rate)
    frames = bytearray()
    for k, (freq, dur) in enumerate(notes):
        n = int(sample_rate * dur)
        for i in range(n):
            env = min(1.0, i / fade, (n - 1 - i) / fade)
            val = int(12000 * env * math.sin(2 * math.pi * freq * i / sample_rate))
            frames += struct.pack("<h", val)
        if k < len(notes) - 1:
            frames += b"\x00\x00" * int(sample_rate * gap)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(bytes(frames))
    return len(frames) // 2


# ---------------------------------------------------------------------------
# HTTP 层捕获：与 dump_request.py / compare_response_layers.py 同一套机制
# ---------------------------------------------------------------------------

captured_requests: list[dict] = []
captured_responses: list[dict] = []


def add_user_key(request: httpx.Request) -> None:
    sep = "&" if "?" in str(request.url) else "?"
    request.url = httpx.URL(f"{request.url}{sep}user_key={USER_KEY}")


def capture_request(request: httpx.Request) -> None:
    """请求钩子：注册在 add_user_key 之后，截到的就是最终发出去的形态。"""
    captured_requests.append({
        "method": request.method,
        "path_query": request.url.raw_path.decode("utf-8"),
        # Request 对象没有 http_version 属性（那是 Response 的），实际版本在 extensions 里
        "http_version": request.extensions.get("http_version", "HTTP/1.1"),
        "url": str(request.url),
        "headers": dict(request.headers),
        "body_text": request.read().decode("utf-8"),
    })


def capture_response(response: httpx.Response) -> None:
    """响应钩子：headers 到达即触发，read() 把响应体抄下来，不影响后续解析。"""
    captured_responses.append({
        "status_code": response.status_code,
        "http_version": response.http_version,
        "headers": dict(response.headers),
        "body_text": response.read().decode("utf-8"),
    })


def build_llm(http_client: httpx.Client) -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        http_client=http_client,
        timeout=180,
    )


# invoke 客户端：请求 + 响应双侧捕获；stream 客户端：只挂请求钩子
# （响应钩子里的 read() 会截走 SSE 流，破坏流式语义，所以流式只在 LangChain 层收集分块）
invoke_client = httpx.Client(timeout=180, event_hooks={
    "request": [add_user_key, capture_request],
    "response": [capture_response],
})
stream_client = httpx.Client(timeout=180, event_hooks={
    "request": [add_user_key, capture_request],
})
invoke_llm = build_llm(invoke_client)
stream_llm = build_llm(stream_client)


# ---------------------------------------------------------------------------
# 脱敏与渲染工具
# ---------------------------------------------------------------------------

def mask_secret(value: str, keep: int = 6) -> str:
    return value[:keep] + "***" if len(value) > keep else "***"


def mask_query(text: str) -> str:
    return re.sub(r"(user_key=)([^&]+)", lambda m: m.group(1) + mask_secret(m.group(2)), text)


def mask_header_value(name: str, value: str) -> str:
    if name == "authorization":
        scheme, _, key = value.partition(" ")
        return f"{scheme} {mask_secret(key)}" if key else mask_secret(value)
    return value


def to_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def dump_message(message) -> str:
    return to_json(message.model_dump())


def answer_text(msg) -> str:
    content = msg.content
    return content if isinstance(content, str) else to_json(content)


# ---------------------------------------------------------------------------
# 用例执行
# ---------------------------------------------------------------------------

CASES: list[dict] = []


def run_invoke(no: int, form: str, title: str, purpose: str, code: str,
               messages: list, expects: list[str]) -> None:
    req_idx = len(captured_requests)
    resp_idx = len(captured_responses)
    print(f">> [{no}/8] {title} ...", flush=True)
    t0 = time.perf_counter()
    err = None
    msg = None
    try:
        msg = invoke_llm.invoke(messages)
    except Exception as e:  # HTTP 4xx/5xx 会在这里以异常出现，但原始响应已被钩子截获
        err = e
    elapsed = time.perf_counter() - t0
    CASES.append({
        "kind": "invoke", "no": no, "form": form, "title": title, "purpose": purpose,
        "code": code, "req_idx": req_idx, "resp_idx": resp_idx,
        "expects": expects, "elapsed": elapsed, "error": err, "msg": msg,
    })
    status = captured_responses[resp_idx]["status_code"] if len(captured_responses) > resp_idx else "ERR"
    print(f"   HTTP {status}，耗时 {elapsed:.2f}s", flush=True)


def run_stream(no: int, form: str, title: str, purpose: str, code: str,
               messages: list, expects: list[str]) -> None:
    req_idx = len(captured_requests)
    print(f">> [{no}/8] {title} ...", flush=True)
    t0 = time.perf_counter()
    timed = []
    for chunk in stream_llm.stream(messages):
        timed.append((time.perf_counter() - t0, chunk))
    elapsed = time.perf_counter() - t0
    merged = reduce(operator.add, [c for _, c in timed])
    CASES.append({
        "kind": "stream", "no": no, "form": form, "title": title, "purpose": purpose,
        "code": code, "req_idx": req_idx, "expects": expects, "elapsed": elapsed,
        "chunks": timed, "merged": merged,
    })
    print(f"   共 {len(timed)} 块，耗时 {elapsed:.2f}s", flush=True)


def run_all_cases() -> None:
    img_a = (MEDIA_DIR / "img_a_shapes.png").read_bytes()
    img_b = (MEDIA_DIR / "img_b_shapes.png").read_bytes()
    wav_b64 = base64.b64encode((MEDIA_DIR / "tone_melody.wav").read_bytes()).decode("ascii")
    b64_a = base64.b64encode(img_a).decode("ascii")
    b64_b = base64.b64encode(img_b).decode("ascii")

    # ---- 用例 1：纯文本对照 ----
    run_invoke(
        1, "纯文本（字符串）", "纯文本对照（content 是字符串）",
        "对照组：content 直接是字符串（此前所有演示的形态）。消息里没有任何图片块，"
        "模型只能靠文字回答——它应该明确说自己没有收到图。与用例 2 对照，"
        "看多模态把 content 从字符串换成了什么样的数组。",
        'message = HumanMessage("请描述我发给你的这张图片")\nresponse = llm.invoke([message])',
        [HumanMessage("请描述我发给你的这张图片")],
        [],
    )

    # ---- 用例 2：图片 base64（原生格式） ----
    run_invoke(
        2, "图 base64（原生 image_url）", "图片 base64 data URI（OpenAI 原生格式）",
        "最常用的多模态形态：本地文件读成字节 -> base64 编码 -> 拼成 data URI 放进 "
        "image_url。图片内嵌在请求体里，服务端无需回源取图。图中事实：红圆 + 蓝方 + "
        "绿圆 + 算式 8+5，可客观核验模型是否真看懂。",
        'b64 = base64.b64encode(IMG_A).decode()\n'
        'message = HumanMessage(content=[\n'
        '    {"type": "text", "text": Q_IMAGE_A},\n'
        '    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},\n'
        '])',
        [HumanMessage(content=[
            {"type": "text", "text": Q_IMAGE_A},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_a}"}},
        ])],
        ["红", "蓝", "绿", "13"],
    )

    # ---- 用例 3：detail 参数 ----
    run_invoke(
        3, "图 base64 + detail=low", "图片 + detail 画质参数（原生格式）",
        "image_url 里唯一常用的附加参数 detail：low 让服务端按低分辨率处理图片"
        "（省 token、更快，但小字可能看不清）。验证两点：① detail 是否被透传进请求体；"
        "② 同一张图在 detail=low 下回答质量是否有变化。",
        'message = HumanMessage(content=[\n'
        '    {"type": "text", "text": Q_IMAGE_A},\n'
        '    {"type": "image_url",\n'
        '     "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"}},\n'
        '])',
        [HumanMessage(content=[
            {"type": "text", "text": Q_IMAGE_A},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_a}", "detail": "low"}},
        ])],
        ["红", "蓝", "绿", "13"],
    )

    # ---- 用例 4：LangChain 标准内容块 ----
    run_invoke(
        4, "图 base64（LangChain 标准块）", "LangChain 标准内容块写法（库自动转换）",
        "LangChain 官方的多模态写法：type 是 image 而不是 image_url，数据放在 "
        "data/mime_type 字段。转换层会把它自动翻译成 OpenAI 的 image_url data URI"
        "（对照用例 2 的请求体）。块上多写一个 detail，实测它能否到达服务端。",
        'message = HumanMessage(content=[\n'
        '    {"type": "text", "text": Q_IMAGE_A},\n'
        '    {"type": "image", "source_type": "base64", "data": b64,\n'
        '     "mime_type": "image/png", "detail": "low"},\n'
        '])',
        [HumanMessage(content=[
            {"type": "text", "text": Q_IMAGE_A},
            {"type": "image", "source_type": "base64", "data": b64_a,
             "mime_type": "image/png", "detail": "low"},
        ])],
        ["红", "蓝", "绿", "13"],
    )

    # ---- 用例 5：图片 URL ----
    run_invoke(
        5, "图 URL（公网地址）", "图片 URL（服务端回源取图）",
        "image_url 也可以不内嵌 base64，而是给一个公网 https 地址，由服务端去下载。"
        "好处是请求体小；前提是服务端能访问外网。能否成功取决于部署环境，实测为准。",
        'message = HumanMessage(content=[\n'
        '    {"type": "text", "text": Q_URL},\n'
        '    {"type": "image_url", "image_url": {"url": PUBLIC_IMG_URL}},\n'
        '])',
        [HumanMessage(content=[
            {"type": "text", "text": Q_URL},
            {"type": "image_url", "image_url": {"url": PUBLIC_IMG_URL}},
        ])],
        [],
    )

    # ---- 用例 6：多图同帧 ----
    run_invoke(
        6, "多图同帧（2 张）", "一条消息里放两张图（多图对比）",
        "content 数组里放两个 image_url 块即为多图输入。让模型分别描述两图再对比差异"
        "（图 A：红圆+蓝方+绿圆+算式 8+5；图 B：黄方+紫圆+数字 7），"
        "同时验证模型对多图的编号/顺序理解。",
        'message = HumanMessage(content=[\n'
        '    {"type": "text", "text": Q_MULTI},\n'
        '    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_a}"}},\n'
        '    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_b}"}},\n'
        '])',
        [HumanMessage(content=[
            {"type": "text", "text": Q_MULTI},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_a}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_b}"}},
        ])],
        ["红", "蓝", "绿", "黄", "紫", "7", "8"],
    )

    # ---- 用例 7：音频 ----
    run_invoke(
        7, "音频 input_audio（WAV）", "音频输入（input_audio + WAV base64）",
        "OpenAI 协议的音频输入形态：content 块类型 input_audio，data 是音频 base64，"
        "format 只支持 wav/mp3。该部署是否真支持音频输入以实测为准——"
        "哪怕返回 400，报错原文也是'这个端点音频能力'的权威答案。",
        'message = HumanMessage(content=[\n'
        '    {"type": "text", "text": Q_AUDIO},\n'
        '    {"type": "input_audio",\n'
        '     "input_audio": {"data": WAV_B64, "format": "wav"}},\n'
        '])',
        [HumanMessage(content=[
            {"type": "text", "text": Q_AUDIO},
            {"type": "input_audio", "input_audio": {"data": wav_b64, "format": "wav"}},
        ])],
        [],
    )

    # ---- 用例 8：多模态流式 ----
    run_stream(
        8, "图 base64 + 流式", "多模态流式（stream=True + 图片）",
        "多模态与流式正交组合：消息构造与用例 2 完全同构，只是调用方式换成 stream()。"
        "看请求体多出的 stream 字段、流式分块的形态，以及分块合并后是否等价于一次 invoke。",
        'for chunk in llm.stream([HumanMessage(content=[\n'
        '    {"type": "text", "text": Q_IMAGE_B},\n'
        '    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_b}"}},\n'
        '])]):\n'
        '    ...  # 逐块收集，块间用 + 合并',
        [HumanMessage(content=[
            {"type": "text", "text": Q_IMAGE_B},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_b}"}},
        ])],
        ["黄", "紫", "7"],
    )


# ---------------------------------------------------------------------------
# markdown 渲染
# ---------------------------------------------------------------------------

def render_blocks_table(body: dict) -> list[str]:
    """把请求体里的 messages 逐条逐块展开成表（base64 只报长度，完整值在上方请求体里）。"""
    lines = ["| # | role | 块 type | 内容 |", "| --- | --- | --- | --- |"]
    i = 0
    for m in body.get("messages", []):
        content = m.get("content")
        if isinstance(content, str):
            i += 1
            lines.append(f"| {i} | {m.get('role')} | （纯字符串 content） | {table_cell(content)} |")
            continue
        for b in content or []:
            i += 1
            t = b.get("type", "?")
            if t == "text":
                desc = table_cell(b.get("text", ""))
            elif t == "image_url":
                iu = b.get("image_url", {})
                u = iu.get("url", "")
                if u.startswith("data:"):
                    head, _, b64 = u.partition(";base64,")
                    desc = f"data URI（`{head};base64,`），base64 共 {len(b64)} 字符（完整值见上方请求体）"
                else:
                    desc = f"URL：{table_cell(u)}"
                if iu.get("detail"):
                    desc += f"，**detail={iu.get('detail')}**（已透传到请求体）"
            elif t == "input_audio":
                ia = b.get("input_audio", {})
                desc = (f"format=`{ia.get('format')}`，base64 共 {len(ia.get('data', ''))} 字符"
                        "（完整值见上方请求体）")
            elif t == "image":
                desc = (f"source_type=`{b.get('source_type')}`，mime_type=`{b.get('mime_type')}`，"
                        f"data 共 {len(b.get('data', ''))} 字符"
                        + (f"，块上写了 detail={b.get('detail')}" if b.get("detail") else ""))
            else:
                desc = table_cell(json.dumps(b, ensure_ascii=False, default=str))
            lines.append(f"| {i} | {m.get('role')} | `{t}` | {desc} |")
    return lines


def verdict_of(rec: dict) -> str:
    if rec["kind"] == "stream":
        n_ok = sum(1 for k in rec["expects"] if k in answer_text(rec["merged"]))
        if rec["expects"] and n_ok == len(rec["expects"]):
            return "✅ 全对"
        return f"⚠ {n_ok}/{len(rec['expects'])} 项命中" if rec["expects"] else "✅ 正常返回"
    if len(captured_responses) > rec["resp_idx"]:
        status = captured_responses[rec["resp_idx"]]["status_code"]
        if status != 200:
            # 4xx/5xx 会被 langchain 包装成异常，但响应本体已被钩子截获——
            # 这是服务端的明确答复（如 400 拒绝），不是连接层失败
            return f"❌ HTTP {status}（服务端拒绝，响应原文见本用例）"
    elif rec["error"] is not None:
        return "❌ 连接失败（未收到 HTTP 响应）"
    ans = answer_text(rec["msg"]) if rec["msg"] is not None else ""
    if rec["expects"]:
        n_ok = sum(1 for k in rec["expects"] if k in ans)
        return "✅ 全对" if n_ok == len(rec["expects"]) else f"⚠ {n_ok}/{len(rec['expects'])} 项命中"
    return "✅ 正常返回"


def render_case(rec: dict) -> list[str]:
    md = []
    md.append(f"## 用例 {rec['no']}：{rec['title']}\n")
    md.append(f"**这一步在干什么**：{rec['purpose']}\n")

    # 1. 构造代码
    md.append("### 1. 我们构造的消息（Python 原文）\n")
    md.append("```python")
    md.append(rec["code"])
    md.append("```\n")

    # 2. 请求体
    req = captured_requests[rec["req_idx"]]
    body = json.loads(req["body_text"])
    md.append("### 2. 实际发出的请求体（httpx 钩子截获，完整 JSON，无省略）\n")
    md.append("```text")
    md.append(f"{req['method']} {mask_query(req['path_query'])} {req['http_version']}")
    md.append("```")
    md.append("```json")
    md.append(to_json(body))
    md.append("```\n")

    # 3. 内容块展开
    md.append("### 3. messages 内容块逐块展开（多模态参数就在这里）\n")
    md += render_blocks_table(body)
    md.append("")

    # 4. 输入素材
    if rec["no"] in (2, 3, 4):
        md.append("### 4. 输入图片长这样（与模型看到的是同一份字节）\n")
        md.append("![图 A：红圆 + 蓝方 + 绿圆 + 算式 8+5](agent/test_media/img_a_shapes.png)")
        md.append(f"（240×160 PNG，{len((MEDIA_DIR / 'img_a_shapes.png').read_bytes())} 字节，"
                  "base64 后约 "
                  f"{len(base64.b64encode((MEDIA_DIR / 'img_a_shapes.png').read_bytes()))} 字符）\n")
    elif rec["no"] == 5:
        md.append("### 4. 输入图片\n")
        md.append(f"公网图片：{PUBLIC_IMG_URL}（服务端回源下载）\n")
    elif rec["no"] == 6:
        md.append("### 4. 输入的两张图\n")
        md.append("第一张（图 A）：")
        md.append("![图 A](agent/test_media/img_a_shapes.png)")
        md.append("第二张（图 B）：")
        md.append("![图 B：黄方 + 紫圆 + 数字 7](agent/test_media/img_b_shapes.png)")
        b64_a_len = len(base64.b64encode((MEDIA_DIR / "img_a_shapes.png").read_bytes()))
        b64_b_len = len(base64.b64encode((MEDIA_DIR / "img_b_shapes.png").read_bytes()))
        md.append(f"（本用例请求体同时含图 A、图 B 两份 base64，共 {b64_a_len + b64_b_len} 字符）\n")
    elif rec["no"] == 7:
        wav_path = MEDIA_DIR / "tone_melody.wav"
        md.append("### 4. 输入音频\n")
        md.append(f"脚本生成的三连音 WAV：`{wav_path.relative_to(ROOT)}`"
                  f"（A4→C5→E5 上行旋律，8000Hz 16bit 单声道，{wav_path.stat().st_size} 字节）\n")
    elif rec["no"] == 8:
        md.append("### 4. 输入图片\n")
        md.append("![图 B](agent/test_media/img_b_shapes.png)\n")

    # 5. 响应
    md.append("### 5. 服务端响应（原始 JSON，全量）\n")
    if rec["kind"] == "invoke":
        if len(captured_responses) > rec["resp_idx"]:
            resp = captured_responses[rec["resp_idx"]]
            md.append(f"HTTP 状态：**{resp['status_code']}** ｜ 耗时：{rec['elapsed']:.2f}s\n")
            md.append("```json")
            md.append(resp["body_text"].strip())
            md.append("```\n")
        else:
            md.append(f"未收到 HTTP 响应（连接层失败），异常：`{rec['error']!r}`\n")
    else:
        md.append(f"流式响应（SSE）：共 **{len(rec['chunks'])}** 个分块 ｜ 耗时：{rec['elapsed']:.2f}s ｜ "
                  "逐块完整字段见 multimodal_stream_chunks.md\n")

    # 6. 回答
    if rec["kind"] == "invoke" and rec["msg"] is not None:
        md.append("### 6. 模型回答（message.content）\n")
        md.append("```text")
        md.append(answer_text(rec["msg"]))
        md.append("```\n")
        if rec["expects"]:
            marks = " ｜ ".join(
                f"{k} {'✓' if k in answer_text(rec['msg']) else '✗'}" for k in rec["expects"])
            md.append(f"### 7. 回答核验（与图中事实对照）\n\n{marks}\n")
    elif rec["kind"] == "stream":
        merged = rec["merged"]
        md.append("### 6. 分块合并后的完整回答\n")
        md.append("```text")
        md.append(answer_text(merged))
        md.append("```\n")
        if rec["expects"]:
            marks = " ｜ ".join(
                f"{k} {'✓' if k in answer_text(merged) else '✗'}" for k in rec["expects"])
            md.append(f"### 7. 回答核验（与图中事实对照）\n\n{marks}\n")
    return md


def render_matrix_appendix() -> list[str]:
    md = ["## 附录 A：8 组模型多模态支持矩阵（实测）\n"]
    md.append("数据来自 `agent/multimodal_matrix_check.py` 的真实调用"
              "（每模型：一次文本 ping + 一次同图提问），原始 JSON 见 "
              "`agent/multimodal_matrix_result.json`。核心结论：**HTTP 200 不代表看得见图**，"
              "必须用图中事实可核验的问题实测。\n")
    if not MATRIX_JSON.exists():
        md.append("（未找到矩阵数据文件，跳过）\n")
        return md
    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    md.append("| 模型 | 文本 ping | 图片请求 | 图片耗时 | 判定 |")
    md.append("| --- | --- | --- | --- | --- |")
    for row in data["rows"]:
        ts = row.get("text_status", row.get("text_error", "?"))
        is_ = row.get("image_status", row.get("image_error", "?"))
        ie = row.get("image_elapsed", "-")
        check = row.get("vision_check", {})
        if any(check.values()):
            verdict = "✅ 真多模态（回答对得上图）"
        elif row.get("image_status") == 200:
            verdict = "❌ 200 但丢图（实际纯文本）"
        elif row.get("image_status") == 400:
            verdict = "❌ 400 拒绝（模型声明仅文本）"
        elif row.get("image_status") == 403:
            verdict = "❌ 403 无该模型权限"
        elif row.get("image_status") == 429:
            verdict = "❌ 429 无可用部署"
        elif row.get("image_status") == 404:
            verdict = "❌ 404 模型组/路由不存在"
        else:
            verdict = f"❌ {str(row.get('image_error', is_))[:60]}"
        md.append(f"| `{row['model']}` | {ts} | {is_} | {ie}s | {verdict} |")
    md.append("")
    for i, row in enumerate(data["rows"], 1):
        md.append(f"### A.{i} `{row['model']}`（{row['base_url']}）\n")
        md.append(f"- 文本 ping：HTTP {row.get('text_status', row.get('text_error'))}，"
                  f"耗时 {row.get('text_elapsed', '-')}s")
        md.append(f"- 图片请求：HTTP {row.get('image_status', row.get('image_error'))}，"
                  f"耗时 {row.get('image_elapsed', '-')}s")
        if "image_answer" in row:
            md.append(f"- 回答核验：{row.get('vision_check')}")
            md.append("- 模型回答原文：")
            md.append("  ```text")
            for ln in row["image_answer"].splitlines() or ["（空）"]:
                md.append(f"  {ln}")
            md.append("  ```")
        body = row.get("image_body") or row.get("image_error", "")
        md.append("- 图片请求响应原文（抓取时截断至 6000 字符）：")
        md.append("  ```json")
        for ln in body.splitlines() or ["（空）"]:
            md.append(f"  {ln}")
        md.append("  ```\n")
    return md


def render_cheatsheet_appendix() -> list[str]:
    md = ["## 附录 B：多模态 content 块写法速查（本项目实测）\n"]
    md.append("| 你在 Python 里写的 content 块 | 实际发到请求体里的样子 |")
    md.append("| --- | --- |")
    md.append('| `{"type": "text", "text": "..."}` | 原样透传 |')
    md.append('| `{"type": "image_url", "image_url": {"url": "https://..."}}` | 原样透传（服务端回源取图） |')
    md.append('| `{"type": "image_url", "image_url": {"url": "data:image/png;base64,...", "detail": "low"}}` '
              '| 原样透传，**detail 保留**（用例 3 请求体可查） |')
    md.append('| `{"type": "image", "source_type": "base64", "data": "...", "mime_type": "image/png"}` '
              '| langchain-openai 自动转换成 `{"type": "image_url", "image_url": {"url": "data:...;base64,..."}}`；'
              '**块上多写的 detail 会被 langchain-core 1.2.18 丢弃**（用例 4 请求体无 detail，实测） |')
    md.append('| `{"type": "input_audio", "input_audio": {"data": "...", "format": "wav"}}` '
              '| 原样透传（OpenAI 音频格式，仅 wav/mp3） |')
    md.append('| `{"type": "audio", "base64": "...", "mime_type": "audio/wav"}`（LangChain 标准块） '
              '| 自动转换成 `{"type": "input_audio", "input_audio": {...}}` |')
    md.append("| 多图 | 同一 content 数组里放多个 image_url 块即可（用例 6） |")
    md.append("| 流式 | 消息构造不变，请求体多出 `\"stream\": true`（用例 8） |")
    md.append("")
    return md


def render_findings_appendix() -> list[str]:
    # 从捕获数据推导事实句
    body3 = json.loads(captured_requests[2]["body_text"])
    body4 = json.loads(captured_requests[3]["body_text"])
    detail_kept = any(b.get("image_url", {}).get("detail")
                      for m in body3["messages"] if isinstance(m.get("content"), list)
                      for b in m["content"])
    detail_dropped = not any(b.get("image_url", {}).get("detail")
                             for m in body4["messages"] if isinstance(m.get("content"), list)
                             for b in m["content"])
    status7 = captured_responses[6]["status_code"] if len(captured_responses) > 6 else "?"
    status5 = captured_responses[4]["status_code"] if len(captured_responses) > 4 else "?"
    underlying = "?"
    try:
        underlying = json.loads(captured_responses[1]["body_text"])["model"]
    except Exception:
        pass

    md = ["## 附录 C：实测要点汇总\n"]
    md.append(f"1. **HTTP 200 ≠ 看得见图**：矩阵里 xinghai-ultra、qwen-flash、qwen-plus 图片请求都返回 200，"
              "但模型回答\"看不到图片\"——服务端把 image_url 静默丢弃了。判定多模态能力必须用"
              "图中事实可核验的问题实测（本报告所有图片用例都带核验标记）。")
    md.append("2. **deepseek-v4-flash-sz 是纯文本模型**：发图直接 400，报错原文是 litellm 的模型能力声明"
              "（only supports text input），完整报错见矩阵附录 A.6。")
    md.append(f"3. **路由组名 ≠ 底层模型名**：请求里写 `{MODEL_NAME}`，响应 `model` 字段返回 `{underlying}`"
              "——网关把路由组映射到了具体部署版本。")
    md.append(f"4. **detail 参数的坑**：原生 image_url 格式下 detail 透传（实测：{'是' if detail_kept else '否'}）；"
              f"LangChain 标准块写法下 detail 被转换层丢弃（实测：{'是' if detail_dropped else '否'}）。"
              "要用 detail 就写原生格式。")
    md.append(f"5. **图片 URL 用例**：HTTP {status5}——能否成功取决于服务端是否可回源访问公网，响应原文见用例 5。")
    md.append(f"6. **音频用例**：HTTP {status7}——该部署对 input_audio 的真实态度见用例 7 响应原文。")
    md.append("7. **流式与多模态正交**：同一套消息 + stream()，请求体只多 `\"stream\": true`，"
              "分块仍是纯文本增量，`+` 合并后等价一次 invoke（逐块全量数据见 multimodal_stream_chunks.md）。")
    md.append("")
    return md


def build_main_md() -> str:
    underlying = "?"
    try:
        underlying = json.loads(captured_responses[1]["body_text"])["model"]
    except Exception:
        pass

    md = []
    md.append("# 多模态参数调用模型：输入输出全量实例\n")
    md.append(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- 模型：`{MODEL_NAME}`（网关路由组名；响应 `model` 字段显示底层为 `{underlying}`）")
    md.append(f"- base_url：`{BASE_URL}`（hr 子路由；key 与 `agent/llm.py` 同一套，`user_key` 已脱敏）")
    md.append("- 捕获方式：httpx event_hooks 请求/响应双侧钩子，与 `dump_request.py` / "
              "`compare_response_layers.py` 同机制，截到的与真实收发的字节一致")
    md.append("- 测试素材：脚本用纯 Python 生成的两张 PNG 与一段 WAV（项目未装 Pillow），"
              "存于 `agent/test_media/`，报告中内嵌显示，模型看到的与你看到的完全同源")
    md.append("- 结构：用例 1-8 每例 = 构造代码 + 请求体全量 + 内容块展开 + 响应全量 + 回答核验；"
              "附录 A 是 8 组模型的多模态支持矩阵，附录 B/C 是写法速查与要点\n")

    md.append("## 用例总览\n")
    md.append("| 用例 | 输入形式 | HTTP | 耗时 | 结果核验 |")
    md.append("| --- | --- | --- | --- | --- |")
    for rec in CASES:
        status = "SSE" if rec["kind"] == "stream" else (
            captured_responses[rec["resp_idx"]]["status_code"]
            if len(captured_responses) > rec["resp_idx"] else "ERR")
        md.append(f"| {rec['no']} | {rec['form']} | {status} | {rec['elapsed']:.2f}s | {verdict_of(rec)} |")
    md.append("")

    for rec in CASES:
        md += render_case(rec)

    md += render_matrix_appendix()
    md += render_cheatsheet_appendix()
    md += render_findings_appendix()
    return "\n".join(md)


def build_stream_md(rec: dict) -> str:
    req = captured_requests[rec["req_idx"]]
    chunks = rec["chunks"]
    merged = rec["merged"]
    ttft = chunks[0][0] if chunks else 0.0

    md = []
    md.append(f"# 多模态流式分块全量信息（用例 {rec['no']}：{rec['title']}）\n")
    md.append(f"- 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- 模型：`{MODEL_NAME}`（与主报告同一次实验，图片为图 B）")
    md.append(f"- 分块数量：**{len(chunks)}** 个 ｜ 首块到达：{ttft:.2f}s ｜ 总耗时：{rec['elapsed']:.2f}s")
    md.append("- 合并方式：`chunks[0] + chunks[1] + ...`（AIMessageChunk 重载了 + 运算符）\n")

    md.append("## 一、实际发出的请求体（完整 JSON，与普通请求只差 stream 字段）\n")
    md.append("```json")
    md.append(to_json(json.loads(req["body_text"])))
    md.append("```\n")

    md.append("## 二、全部分块累加后的完整消息\n")
    md.append("```json")
    md.append(dump_message(merged))
    md.append("```\n")

    md.append(f"## 三、全部 {len(chunks)} 个分块的完整信息（逐块 model_dump，无省略）\n")
    for i, (t, c) in enumerate(chunks, 1):
        md.append(f"### 分块 {i} ｜ t = {t:.3f}s")
        md.append("增量 content：\n")
        md.append("```text")
        md.append(c.content if c.content else "（空字符串：本块只携带元数据，不带文字）")
        md.append("```")
        md.append("完整字段：\n")
        md.append("```json")
        md.append(dump_message(c))
        md.append("```\n")

    md.append("## 四、字段速查\n")
    md.append("- `content`：每块只有增量文字，累加后等于完整回答")
    md.append("- `id`：同一次调用的所有分块共享同一 id")
    md.append("- `usage_metadata`：随最后一个分块回传 token 用量")
    md.append("- `chunk_position` / `response_metadata`：中间块与末块差异可逐块对比")
    return "\n".join(md)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print(f"多模态输入输出全量示例（8 次真实调用，模型 {MODEL_NAME}）")
    print("=" * 70)

    MEDIA_DIR.mkdir(exist_ok=True)
    img_a = build_image_a()
    img_b = build_image_b()
    (MEDIA_DIR / "img_a_shapes.png").write_bytes(img_a)
    (MEDIA_DIR / "img_b_shapes.png").write_bytes(img_b)
    samples = build_wav(MEDIA_DIR / "tone_melody.wav")
    print(f"测试素材已生成：图 A {len(img_a)}B，图 B {len(img_b)}B，WAV {samples} 采样\n")

    run_all_cases()

    invoke_client.close()
    stream_client.close()

    stream_rec = next(c for c in CASES if c["kind"] == "stream")
    OUT_STREAM.write_text(build_stream_md(stream_rec), encoding="utf-8")
    OUT_MAIN.write_text(build_main_md(), encoding="utf-8")
    print(f"\n已生成: {OUT_MAIN}")
    print(f"已生成: {OUT_STREAM}")
    print("用编辑器或 Markdown 预览打开即可查看（请求与响应均为全量导出）")


if __name__ == "__main__":
    main()
