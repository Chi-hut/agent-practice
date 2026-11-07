"""file_agent 测试用的确定性文件与输出目录。"""

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE / "_workspace"
OUT = HERE / "_out"


def _log_text(n: int) -> str:
    lines = []
    for i in range(1, n + 1):
        lines.append(
            f"第{i:04d}行 2026-10-25 08:{i % 60:02d}:{i % 60:02d}.000 INFO order-service "
            f"trace={i * 2654435761 & 0xFFFFFFFF:08x} 订单 #{100000 + i} 创建成功 "
            f"耗时 {i % 4000}ms 备注=这是用于测试 read_file 大文件截断行为的填充文本\n"
        )
    return "".join(lines)


def build_workspace() -> Path:
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    WORKSPACE.mkdir(parents=True)
    (WORKSPACE / "huge.log").write_text(_log_text(3000), encoding="utf-8")
    (WORKSPACE / "medium.txt").write_text(_log_text(120), encoding="utf-8")
    return WORKSPACE


def file_stats(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "path": path.name,
        "lines": len(text.splitlines()),
        "chars": len(text),
        "bytes": path.stat().st_size,
    }
