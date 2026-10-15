"""
多模态支持矩阵实测工具：对团队模型清单里的每组配置逐一真实调用，判定谁真正支持图片输入。

每个模型两次调用：
1. 文本 ping —— 验证网络可达 / 鉴权 / 模型名是否正确（与多模态无关的基线）
2. 图片理解 —— 一张纯 Python 生成的小 PNG（红圆 + 蓝方块），问"有什么图形、什么颜色"，
   回答里能对上"红色圆形 + 蓝色方块"才算真的看得懂

判定口径（以服务端真实响应为准，HTTP 200 不代表看得见图！）：
- 200 且回答对得上图 -> 真支持多模态
- 200 但回答"看不到图" -> 服务端把图片丢掉了，实际纯文本
- 400 且报错 only supports text input -> 可达但模型声明纯文本
- 403 -> 网关无该模型权限；404 -> 模型组/路由不存在；连接错误 -> 服务不可达

运行方式（在项目根目录下执行）：
    python -m agent.multimodal_matrix_check

结果写入 agent/multimodal_matrix_result.json（UTF-8），供 multimodal_demo 报告附录引用。
"""

import base64
import json
import os
import struct
import time
import zlib
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 团队模型清单（model, api_key, base_url, user_key；user_key 为 None 表示无）
_KEY_MAIN = os.getenv("LLM_API_KEY")
_KEY_OPEN = os.getenv("LLM_API_KEY_OPEN")
_USER_KEY_MAIN = os.getenv("LLM_USER_KEY")
_USER_KEY_OPEN = os.getenv("LLM_USER_KEY_OPEN")
ROWS = [
    ("xinghai-ultra", _KEY_MAIN,
     os.getenv("LLM_BASE_URL_HR"), _USER_KEY_MAIN),
    ("qwen3-5-397b-vip", _KEY_MAIN,
     os.getenv("LLM_BASE_URL_V1"), _USER_KEY_MAIN),
    ("qwen3.5-397b-subagents", os.getenv("LLM_API_KEY_SUB"),
     os.getenv("LLM_BASE_URL_SUB"), None),
    ("gpt-5.6-terra-ptu", _KEY_MAIN,
     os.getenv("LLM_BASE_URL_HR"), _USER_KEY_MAIN),
    ("gpt-5.6-terra-standby", _KEY_MAIN,
     os.getenv("LLM_BASE_URL_HR"), _USER_KEY_MAIN),
    ("deepseek-v4-flash-sz", _KEY_MAIN,
     os.getenv("LLM_BASE_URL_V1"), _USER_KEY_MAIN),
    ("qwen-flash", _KEY_OPEN,
     os.getenv("LLM_BASE_URL_OPEN"), _USER_KEY_OPEN),
    ("qwen-plus", _KEY_OPEN,
     os.getenv("LLM_BASE_URL_OPEN"), _USER_KEY_OPEN),
]

QUESTION = "这张图里有什么图形？分别是什么颜色？只描述你真正看到的，不要猜测。"


# ---------------------------------------------------------------------------
# 纯 Python 生成测试 PNG（不依赖 Pillow）：128x128 白底 + 红色圆形 + 左上蓝方块
# ---------------------------------------------------------------------------

def make_png(width: int, height: int, rows: list[bytes]) -> bytes:
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


def test_image_png() -> bytes:
    w = h = 128
    cx, cy, r = 72, 72, 40
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            in_circle = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
            in_square = 10 <= x < 46 and 10 <= y < 46
            if in_circle:
                row += bytes((220, 30, 30))
            elif in_square:
                row += bytes((30, 60, 220))
            else:
                row += bytes((255, 255, 255))
        rows.append(bytes(row))
    return make_png(w, h, rows)


def looks_like_seen(text: str) -> dict:
    """对模型回答做关键词核验：是否真说出了 红色圆 与 蓝色方块。"""
    t = text.replace(" ", "")
    return {
        "提到红": ("红" in t) or ("red" in t.lower()),
        "提到圆": ("圆" in t) or ("circle" in t.lower()),
        "提到蓝": ("蓝" in t) or ("blue" in t.lower()),
        "提到方": ("方" in t or "矩形" in t or "正方" in t) or ("square" in t.lower() or "rectangle" in t.lower()),
    }


def main() -> None:
    png = test_image_png()
    data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    results = []
    for i, (name, api_key, base, user_key) in enumerate(ROWS, 1):
        url = base.rstrip("/") + "/chat/completions"
        if user_key:
            url += ("&" if "?" in url else "?") + "user_key=" + user_key
        headers = {"Authorization": f"Bearer {api_key}"}
        entry = {"model": name, "base_url": base, "has_user_key": bool(user_key)}

        with httpx.Client(timeout=120) as client:
            # ---- 1. 文本 ping ----
            try:
                t0 = time.perf_counter()
                r = client.post(url, headers=headers, json={
                    "model": name,
                    "messages": [{"role": "user", "content": "只回复两个字：收到"}],
                })
                entry["text_status"] = r.status_code
                entry["text_elapsed"] = round(time.perf_counter() - t0, 2)
                entry["text_body"] = r.text[:2500]
            except Exception as e:
                entry["text_error"] = repr(e)

            # ---- 2. 图片理解 ----
            try:
                t0 = time.perf_counter()
                r = client.post(url, headers=headers, json={
                    "model": name,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": QUESTION},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }],
                })
                entry["image_status"] = r.status_code
                entry["image_elapsed"] = round(time.perf_counter() - t0, 2)
                entry["image_body"] = r.text[:6000]
                try:
                    msg = r.json()["choices"][0]["message"]
                    answer = msg.get("content") or ""
                    if not answer:
                        answer = "(content 为空) reasoning: " + str(msg.get("reasoning_content"))[:800]
                    entry["image_answer"] = answer[:1500]
                    entry["vision_check"] = looks_like_seen(answer)
                except Exception:
                    pass
            except Exception as e:
                entry["image_error"] = repr(e)

        results.append(entry)
        ts = entry.get("text_status", entry.get("text_error", "?"))
        is_ = entry.get("image_status", entry.get("image_error", "?"))
        print(f"[{i}/{len(ROWS)}] {name}: text={ts} image={is_} ({entry.get('image_elapsed', '-')}s)", flush=True)

    out = Path(__file__).resolve().parent / "multimodal_matrix_result.json"
    out.write_text(json.dumps({"png_bytes": len(png), "rows": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("matrix done ->", out)


if __name__ == "__main__":
    main()
