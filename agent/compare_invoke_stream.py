"""
invoke vs stream 差异可视化 Demo

依次真实调用一次 invoke（非流式）和一次 stream（同步流式），采集两种方式的
时间与分块数据，生成 compare_invoke_stream.html。用浏览器打开该文件即可
直观看到差异：

- invoke：整段时间都在"干等"，最后一个时刻一次性拿到完整 AIMessage
- stream：首块很快到达（TTFT），之后小块按时间陆续到达，边生成边可见

运行方式（在项目根目录下执行）：
    python -m agent.compare_invoke_stream
    python agent\\compare_invoke_stream.py

生成文件：项目根目录下 compare_invoke_stream.html（纯静态，无外部依赖）
"""

import json
import time
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage

# 兼容两种运行方式（与 llm_stream.py 同样的处理）：
#   python -m agent.compare_invoke_stream -> 能找到 agent 包，走 agent.llm
#   python agent\\compare_invoke_stream.py -> sys.path 里只有 agent 目录，直接 import 同级的 llm
try:
    from agent.llm import llm
except ImportError:
    from llm import llm

QUESTION = "用 300 字左右介绍一下你自己，并说明你能帮我做什么"

# 报告输出到项目根目录
OUTPUT_HTML = Path(__file__).resolve().parent.parent / "compare_invoke_stream.html"


# ---------------------------------------------------------------------------
# 第一步：真实调用并采集数据
# ---------------------------------------------------------------------------

def collect_invoke() -> dict:
    """非流式调用：阻塞到完整结果生成完毕才返回，只产生 1 个"块"。"""
    print(">> [1/2] 正在执行 invoke（非流式）调用，请稍等 ...")
    start = time.perf_counter()
    response = llm.invoke([HumanMessage(QUESTION)])
    total = time.perf_counter() - start
    print(f"   完成，总耗时 {total:.2f}s，内容 {len(response.content)} 字")

    return {
        "mode": "invoke",
        "label": "invoke 非流式",
        "type": type(response).__name__,
        # 非流式要等全部生成完才能看到第一个字，所以"首字时间"就是总耗时
        "ttft": round(total, 3),
        "total": round(total, 3),
        "chunks": [{"t": round(total, 3), "text": response.content}],
        "content": response.content,
        "usage": response.usage_metadata or {},
    }


def collect_stream() -> dict:
    """流式调用：逐块记录每个 chunk 的到达时刻与内容。"""
    print(">> [2/2] 正在执行 stream（流式）调用，请稍等 ...")
    start = time.perf_counter()
    chunk_objs = []
    chunks = []
    for chunk in llm.stream([HumanMessage(QUESTION)]):
        t = time.perf_counter() - start
        chunk_objs.append(chunk)
        chunks.append({"t": round(t, 4), "text": chunk.content})
    total = time.perf_counter() - start

    ttft = next((c["t"] for c in chunks if c["text"]), total)
    content = "".join(c["text"] for c in chunks)

    # 块累加回来等价于一次 invoke 的完整返回，token 用量一般在末块才回传
    usage = {}
    if chunk_objs:
        merged = chunk_objs[0]
        for c in chunk_objs[1:]:
            merged = merged + c
        usage = merged.usage_metadata or {}

    print(f"   完成，首块 {ttft:.2f}s，总耗时 {total:.2f}s，共 {len(chunks)} 块，内容 {len(content)} 字")

    return {
        "mode": "stream",
        "label": "stream 同步流式",
        "type": type(chunk_objs[-1]).__name__ if chunk_objs else "-",
        "ttft": round(ttft, 3),
        "total": round(total, 3),
        "chunks": chunks,
        "content": content,
        "usage": usage,
    }


# ---------------------------------------------------------------------------
# 第二步：生成自包含的可视化 HTML（内联 CSS/JS，不依赖任何外部资源）
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>invoke vs stream 调用差异可视化</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0b1220;
    color: #e2e8f0;
    font-family: system-ui, "Segoe UI", "Microsoft YaHei", sans-serif;
    line-height: 1.6;
  }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 36px 20px 60px; }
  h1 { font-size: 26px; margin-bottom: 6px; }
  h1 .vs { color: #38bdf8; font-size: 18px; margin: 0 6px; }
  h2 { font-size: 17px; margin-bottom: 14px; color: #93c5fd; }
  .sub { color: #64748b; font-size: 13px; margin-bottom: 28px; }
  .sub code { color: #94a3b8; }
  code { font-family: Consolas, monospace; }
  .card {
    background: #111a2e;
    border: 1px solid #1e2a44;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 22px;
  }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 860px) { .grid2 { grid-template-columns: 1fr; } }

  /* ---- ① 指标卡片 ---- */
  .stat {
    border: 1px solid #1e2a44;
    border-radius: 12px;
    padding: 14px 18px;
    background: #0d1526;
  }
  .stat.inv { border-top: 3px solid #fbbf24; }
  .stat.stm { border-top: 3px solid #34d399; }
  .stat-title { font-weight: 700; margin-bottom: 8px; }
  .stat.inv .stat-title { color: #fbbf24; }
  .stat.stm .stat-title { color: #34d399; }
  .stat-row { display: flex; justify-content: space-between; font-size: 13.5px; padding: 3px 0; }
  .stat-row span { color: #94a3b8; }
  .stat-row b { font-variant-numeric: tabular-nums; }
  .callout {
    margin-top: 16px;
    background: #0c2233;
    border: 1px solid #155e75;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px;
    color: #a5f3fc;
  }
  .callout b { color: #fde68a; }

  /* ---- ② 时间轴 ---- */
  .tl-legend { font-size: 12.5px; color: #94a3b8; margin-bottom: 12px; }
  .lg { display: inline-block; width: 22px; height: 8px; border-radius: 4px; margin: 0 6px 0 14px; vertical-align: middle; }
  .lg:first-child { margin-left: 0; }
  .tl-label { font-size: 13px; font-weight: 700; margin: 14px 0 4px; }
  .color-inv { color: #fbbf24; }
  .color-stm { color: #34d399; }
  .tl-row {
    position: relative;
    height: 58px;
    background: #0d1526;
    border: 1px solid #1e2a44;
    border-radius: 8px;
    overflow: visible;
  }
  .tl-wait {
    position: absolute; left: 0; top: 13px; height: 32px;
    background: repeating-linear-gradient(45deg, #3a2f14 0 10px, #2a2210 10px 20px);
    background-size: 28px 28px;
    animation: crawl 1.2s linear infinite;
    border-radius: 6px;
    display: flex; align-items: center;
    padding-left: 10px;
    color: #fbbf24; font-size: 12px;
    white-space: nowrap; overflow: hidden;
  }
  @keyframes crawl { to { background-position: 28px 0; } }
  .tl-block {
    position: absolute; top: 13px; height: 32px;
    border-radius: 4px; min-width: 3px;
  }
  .tl-block.inv { background: #fbbf24; width: 10px; box-shadow: 0 0 12px #fbbf2455; }
  .tl-block.stm { background: linear-gradient(180deg, #34d399, #059669); }
  .tl-flag {
    position: absolute; top: -16px;
    transform: translateX(-50%);
    font-size: 11px; color: #34d399; white-space: nowrap;
  }
  .tl-cursor {
    position: absolute; top: -4px; bottom: -4px; width: 2px;
    background: #38bdf8; box-shadow: 0 0 8px #38bdf8;
    display: none; z-index: 5;
  }
  .tl-axis { position: relative; height: 22px; margin-top: 4px; }
  .tl-tick {
    position: absolute; transform: translateX(-50%);
    font-size: 11px; color: #64748b;
  }
  .hint { font-size: 12.5px; color: #64748b; margin-top: 10px; }
  .hint b { color: #cbd5e1; }

  /* ---- ③ 曲线 ---- */
  #curve { width: 100%; height: auto; display: block; }

  /* ---- ④ 回放 ---- */
  .controls {
    display: flex; flex-wrap: wrap; align-items: center; gap: 12px;
    margin-bottom: 14px; font-size: 13.5px; color: #94a3b8;
  }
  .btn {
    background: #1e293b; color: #e2e8f0;
    border: 1px solid #334155; border-radius: 8px;
    padding: 6px 16px; cursor: pointer; font-size: 13.5px;
  }
  .btn:hover { background: #273549; }
  .btn.primary { background: #0369a1; border-color: #0284c7; }
  .btn.primary:hover { background: #075985; }
  .btn.spd.active { background: #155e75; border-color: #0e7490; color: #a5f3fc; }
  #clock { color: #38bdf8; font-weight: 700; font-variant-numeric: tabular-nums; min-width: 78px; }
  .progress-outer {
    flex: 1; min-width: 140px; height: 8px;
    background: #0d1526; border-radius: 4px; overflow: hidden;
  }
  .progress-inner { height: 100%; width: 0; background: linear-gradient(90deg, #fbbf24, #34d399); }
  .pane-title { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
  .terminal {
    background: #05080f;
    border: 1px solid #1e2a44;
    border-radius: 10px;
    padding: 14px 16px;
    height: 250px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    font-family: Consolas, "Courier New", monospace;
    font-size: 13px;
    line-height: 1.75;
  }
  .caret { animation: blink 0.9s steps(1) infinite; color: #34d399; }
  @keyframes blink { 50% { opacity: 0; } }
  .waiting {
    height: 100%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 12px; color: #94a3b8; text-align: center; font-size: 13px;
  }
  .spinner {
    width: 26px; height: 26px;
    border: 3px solid #334155; border-top-color: #fbbf24;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .pane-status { font-size: 12px; color: #64748b; margin-top: 6px; min-height: 18px; }
  .pane-status .ok { color: #34d399; }
  .pane-status .dim { color: #fbbf24; }

  /* ---- ⑤ 内容对比 / ⑥ 明细表 ---- */
  .content-box {
    background: #05080f;
    border: 1px solid #1e2a44;
    border-radius: 10px;
    padding: 14px 16px;
    height: 240px; overflow-y: auto;
    white-space: pre-wrap; word-break: break-all;
    font-size: 13px; line-height: 1.75;
  }
  .table-box {
    max-height: 420px; overflow-y: auto;
    border: 1px solid #1e2a44; border-radius: 10px;
  }
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  th, td { padding: 7px 12px; text-align: left; border-bottom: 1px solid #1e2a44; }
  th {
    position: sticky; top: 0;
    background: #16233d; color: #93c5fd;
    font-weight: 600; z-index: 2;
  }
  td { vertical-align: top; }
  td.wrap, th.wrap { white-space: pre-wrap; word-break: break-all; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  tr:hover td { background: #16203a; }
  .dim { color: #475569; font-style: italic; }
  footer { text-align: center; color: #475569; font-size: 12px; margin-top: 8px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>invoke <span class="vs">vs</span> stream 调用差异可视化</h1>
    <p class="sub">问题：<code id="q"></code><br>真实调用采集于 <code id="ts"></code> · 模型 <code id="model"></code> · 数据来自 <code>agent/compare_invoke_stream.py</code></p>
  </header>

  <section class="card">
    <h2>① 关键指标对比</h2>
    <div class="grid2" id="stat-cards"></div>
    <div class="callout" id="callout"></div>
  </section>

  <section class="card">
    <h2>② 时间轴对比：内容什么时候到达</h2>
    <div id="timeline"></div>
    <p class="hint">黄色条纹 = invoke 的<b>等待期</b>（连接一直挂着，屏幕空白）；右端黄点 = 完整消息<b>一次性</b>到达。绿色小块 = stream 的<b>每个分块</b>按真实到达时刻摆放（悬停可看内容与时刻）。<b>点第 ④ 区的播放按钮</b>，蓝色游标会在两条时间轴上同步移动。</p>
  </section>

  <section class="card">
    <h2>③ "已看到的字数" 随时间变化</h2>
    <div class="tl-legend"><span class="lg" style="background:#fbbf24"></span>invoke<span class="lg" style="background:#34d399"></span>stream</div>
    <div class="svg-box"><svg id="curve"></svg></div>
    <p class="hint">纵轴是<b>用户已经能看到的内容占比</b>。invoke 全程贴地 0%，直到最后时刻垂直跳到 100%；stream 从首块开始阶梯式爬升 —— 这就是两者体感差异的本质。</p>
  </section>

  <section class="card">
    <h2>④ 动画回放：同一时刻两边的"屏幕"长什么样</h2>
    <div class="controls">
      <button class="btn primary" id="btn-play">▶ 播放</button>
      <button class="btn" id="btn-reset">↺ 重置</button>
      <span>速度：</span>
      <button class="btn spd" data-s="1">1x</button>
      <button class="btn spd active" data-s="2">2x</button>
      <button class="btn spd" data-s="4">4x</button>
      <span id="clock">t = 0.00s</span>
      <div class="progress-outer"><div class="progress-inner" id="progress"></div></div>
    </div>
    <div class="grid2">
      <div>
        <div class="pane-title color-inv">invoke（非流式）终端</div>
        <div class="terminal" id="term-invoke"></div>
        <div class="pane-status" id="status-invoke"></div>
      </div>
      <div>
        <div class="pane-title color-stm">stream（流式）终端</div>
        <div class="terminal" id="term-stream"></div>
        <div class="pane-status" id="status-stream"></div>
      </div>
    </div>
  </section>

  <section class="card">
    <h2>⑤ 完整回复内容对比</h2>
    <div class="grid2">
      <div>
        <div class="pane-title color-inv">invoke 返回的 AIMessage.content</div>
        <div class="content-box" id="content-invoke"></div>
      </div>
      <div>
        <div class="pane-title color-stm">stream 分块拼接后的文本</div>
        <div class="content-box" id="content-stream"></div>
      </div>
    </div>
    <p class="hint">两边文字内容一致（流式的分块用 <b>+</b> 累加后等价于一次 invoke 的返回），差异只在<b>到达方式</b>。</p>
  </section>

  <section class="card">
    <h2>⑥ stream 分块明细</h2>
    <div class="table-box">
      <table>
        <thead><tr><th class="num">#</th><th class="num">到达时刻 (s)</th><th class="num">与上一块间隔</th><th class="wrap">本块内容</th></tr></thead>
        <tbody id="chunk-rows"></tbody>
      </table>
    </div>
  </section>

  <footer>由 agent/compare_invoke_stream.py 生成 · 重新运行该脚本可采集新数据覆盖本报告</footer>
</div>

<script id="perf-data" type="application/json">__PERF_DATA__</script>
<script>
"use strict";
var D = JSON.parse(document.getElementById("perf-data").textContent);
var inv = D.invoke, stm = D.stream;
var maxT = Math.max(inv.total, stm.total);
var stmParts = stm.chunks.filter(function (c) { return c.text; });
var maxChunkLen = Math.max.apply(null, stmParts.map(function (c) { return c.text.length; }));

function $(id) { return document.getElementById(id); }
function fmt(t) { return t.toFixed(2); }
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function pct(t) { return (t / maxT * 100); }
function usageStr(u) {
  if (!u || u.input_tokens == null) return "—";
  return "输入 " + u.input_tokens + " · 输出 " + u.output_tokens;
}

/* ---------- 顶部信息 ---------- */
$("q").textContent = D.question;
$("ts").textContent = D.generated_at;
$("model").textContent = D.model;

/* ---------- ① 指标卡片 ---------- */
function statCard(m, cls) {
  return '<div class="stat ' + cls + '">'
    + '<div class="stat-title">' + esc(m.label) + '</div>'
    + '<div class="stat-row"><span>响应类型</span><b>' + esc(m.type) + '</b></div>'
    + '<div class="stat-row"><span>看到第一个字（TTFT）</span><b>' + fmt(m.ttft) + 's</b></div>'
    + '<div class="stat-row"><span>内容块数</span><b>' + m.chunks.length + '</b></div>'
    + '<div class="stat-row"><span>总耗时</span><b>' + fmt(m.total) + 's</b></div>'
    + '<div class="stat-row"><span>token 用量</span><b>' + usageStr(m.usage) + '</b></div>'
    + '</div>';
}
$("stat-cards").innerHTML = statCard(inv, "inv") + statCard(stm, "stm");

var gain = inv.total > 0 ? Math.round((inv.total - stm.ttft) / inv.total * 100) : 0;
$("callout").innerHTML =
  "两种方式的<b>总耗时接近</b>（" + fmt(inv.total) + "s vs " + fmt(stm.total) + "s，模型生成量相同），"
  + "差别在于<b>内容什么时候可见</b>：invoke 要干等 " + fmt(inv.total) + "s 才能见到第一个字；"
  + "stream 在 <b>" + fmt(stm.ttft) + "s</b> 就开始出字（首块到达），"
  + "比 invoke 提前约 <b>" + gain + "%</b> 的时间看到内容，之后内容逐步补齐。";

/* ---------- ② 时间轴 ---------- */
(function buildTimeline() {
  var html = "";
  html += '<div class="tl-legend"><span class="lg" style="background:#fbbf24"></span>invoke 非流式'
    + '<span class="lg" style="background:#34d399"></span>stream 流式（每格=一个分块）</div>';

  // invoke 行
  html += '<div class="tl-label color-inv">invoke</div><div class="tl-row">';
  html += '<div class="tl-wait" style="width:' + pct(inv.total) + '%">'
    + '<span>⏳ 等待中，什么内容都看不到 …（' + fmt(inv.total) + 's）</span></div>';
  html += '<div class="tl-block inv" style="left:calc(' + pct(inv.total) + '% - 5px)" '
    + 'title="t=' + fmt(inv.total) + 's 完整消息（' + inv.content.length + ' 字）一次性到达"></div>';
  html += '<div class="tl-cursor"></div></div>';

  // stream 行
  html += '<div class="tl-label color-stm">stream</div><div class="tl-row">';
  stmParts.forEach(function (c) {
    var w = Math.max(0.25, c.text.length / maxChunkLen * 3.5);
    var tip = "t=" + fmt(c.t) + "s（" + esc(c.text.slice(0, 24)) + "）";
    html += '<div class="tl-block stm" style="left:' + pct(c.t) + '%;width:' + w + '%" title="' + tip + '"></div>';
  });
  html += '<div class="tl-flag" style="left:' + pct(stm.ttft) + '%">首块 ' + fmt(stm.ttft) + 's</div>';
  html += '<div class="tl-cursor"></div></div>';

  // x 轴刻度
  html += '<div class="tl-axis">';
  var NT = 5;
  for (var i = 0; i <= NT; i++) {
    var t = maxT * i / NT;
    html += '<div class="tl-tick" style="left:' + (i / NT * 100) + '%">' + t.toFixed(1) + 's</div>';
  }
  html += "</div>";
  $("timeline").innerHTML = html;
})();

/* ---------- ③ 已见字数曲线（SVG 阶梯图） ---------- */
(function buildCurve() {
  var W = 880, H = 250, padL = 46, padR = 18, padT = 18, padB = 34;
  var X = function (t) { return padL + (t / maxT) * (W - padL - padR); };
  var Y = function (p) { return padT + (1 - p) * (H - padT - padB); };
  var svg = $("curve");
  svg.setAttribute("viewBox", "0 0 " + W + " " + H);
  var NS = "http://www.w3.org/2000/svg";
  function el(name, attrs, text) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    svg.appendChild(n);
    return n;
  }

  // 网格与 y 轴标签
  [0, 0.25, 0.5, 0.75, 1].forEach(function (p) {
    el("line", { x1: padL, y1: Y(p), x2: W - padR, y2: Y(p), stroke: "#1e2a44", "stroke-width": 1 });
    el("text", { x: padL - 8, y: Y(p) + 4, fill: "#64748b", "font-size": 11, "text-anchor": "end" }, Math.round(p * 100) + "%");
  });
  // x 轴刻度
  var NT = 5;
  for (var i = 0; i <= NT; i++) {
    var t = maxT * i / NT;
    el("text", { x: X(t), y: H - 10, fill: "#64748b", "font-size": 11, "text-anchor": "middle" }, t.toFixed(1) + "s");
  }

  // invoke：全程 0%，最后垂直跳 100%
  var pathInv = "M " + X(0) + " " + Y(0) + " L " + X(inv.total) + " " + Y(0)
    + " L " + X(inv.total) + " " + Y(1);
  el("path", { d: pathInv, fill: "none", stroke: "#fbbf24", "stroke-width": 2.5 });
  el("circle", { cx: X(inv.total), cy: Y(1), r: 4, fill: "#fbbf24" });
  el("text", { x: X(inv.total) - 8, y: Y(1) - 10, fill: "#fbbf24", "font-size": 12, "text-anchor": "end" },
    "invoke 到这里才一次性给全");

  // stream：阶梯式爬升
  var pathStm = "M " + X(0) + " " + Y(0);
  var acc = 0, prevP = 0;
  stmParts.forEach(function (c) {
    acc += c.text.length;
    var p = stm.content.length ? acc / stm.content.length : 0;
    pathStm += " L " + X(c.t) + " " + Y(prevP) + " L " + X(c.t) + " " + Y(p);
    prevP = p;
  });
  pathStm += " L " + X(maxT) + " " + Y(prevP);
  el("path", { d: pathStm, fill: "none", stroke: "#34d399", "stroke-width": 2.5 });
  el("circle", { cx: X(stm.ttft), cy: Y(0), r: 4, fill: "#34d399" });
  el("text", { x: X(stm.ttft) + 8, y: Y(0) - 10, fill: "#34d399", "font-size": 12 },
    "stream 首字 " + fmt(stm.ttft) + "s");

  el("text", { x: padL - 8, y: padT - 6, fill: "#94a3b8", "font-size": 11, "text-anchor": "end" }, "已见内容");
})();

/* ---------- ④ 回放动画 ---------- */
var vt = 0, timer = null, speed = 2, TICK = 40;

function drawReplay() {
  $("clock").textContent = "t = " + fmt(vt) + "s";
  $("progress").style.width = (vt / maxT * 100) + "%";

  // invoke 终端
  var ti = $("term-invoke");
  if (vt >= inv.total) {
    ti.innerHTML = esc(inv.content);
    $("status-invoke").innerHTML = '<span class="ok">✔ t=' + fmt(inv.total) + 's：连接返回，' + inv.content.length + ' 字一次性显示</span>';
  } else {
    ti.innerHTML = '<div class="waiting"><span class="spinner"></span><div>模型生成中 …<br>屏幕保持空白</div></div>';
    $("status-invoke").innerHTML = '<span class="dim">已等待 ' + fmt(vt) + 's，一个字都看不到</span>';
  }

  // stream 终端
  var s = "";
  for (var i = 0; i < stm.chunks.length; i++) {
    if (stm.chunks[i].t <= vt) s += stm.chunks[i].text; else break;
  }
  $("term-stream").innerHTML = esc(s) + '<span class="caret">▊</span>';
  $("status-stream").innerHTML = '<span class="ok">已见 ' + s.length + " / " + stm.content.length + " 字（分块持续到达中）</span>";

  // 时间轴游标
  var cursor = document.querySelectorAll(".tl-cursor");
  for (var j = 0; j < cursor.length; j++) {
    cursor[j].style.display = vt > 0 ? "block" : "none";
    cursor[j].style.left = "calc(" + pct(vt) + "% - 1px)";
  }
}

function stopPlay() {
  if (timer) { clearInterval(timer); timer = null; }
  $("btn-play").textContent = "▶ 播放";
}
function playPause() {
  if (timer) { stopPlay(); return; }
  if (vt >= maxT) vt = 0;
  $("btn-play").textContent = "⏸ 暂停";
  timer = setInterval(function () {
    vt = Math.min(vt + TICK / 1000 * speed, maxT);
    drawReplay();
    if (vt >= maxT) stopPlay();
  }, TICK);
}
$("btn-play").addEventListener("click", playPause);
$("btn-reset").addEventListener("click", function () { stopPlay(); vt = 0; drawReplay(); });
var spdBtns = document.querySelectorAll(".spd");
for (var k = 0; k < spdBtns.length; k++) {
  spdBtns[k].addEventListener("click", function () {
    speed = Number(this.dataset.s);
    for (var m = 0; m < spdBtns.length; m++) spdBtns[m].classList.remove("active");
    this.classList.add("active");
  });
}

/* ---------- ⑤ 内容对比 ---------- */
$("content-invoke").textContent = inv.content;
$("content-stream").textContent = stm.content;

/* ---------- ⑥ 分块明细表 ---------- */
(function buildTable() {
  var prev = 0, rows = "";
  stm.chunks.forEach(function (c, i) {
    var gap = i === 0 ? "—" : Math.round((c.t - prev) * 1000) + " ms";
    prev = c.t;
    var text = c.text ? esc(c.text) : '<span class="dim">(空块)</span>';
    rows += "<tr><td class='num'>" + (i + 1) + "</td><td class='num'>" + c.t.toFixed(3)
      + "</td><td class='num'>" + gap + "</td><td class='wrap'>" + text + "</td></tr>";
  });
  $("chunk-rows").innerHTML = rows;
})();

drawReplay();
</script>
</body>
</html>
"""


def build_html(data: dict) -> str:
    """把采集到的数据嵌入 HTML 模板。< 替换为 \\u003c，防止内容里出现 </script> 破坏页面。"""
    safe_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return HTML_TEMPLATE.replace("__PERF_DATA__", safe_json)


def main() -> None:
    print("=" * 70)
    print("invoke vs stream 真实调用采集 + 可视化报告生成")
    print("=" * 70)

    inv = collect_invoke()
    stm = collect_stream()

    data = {
        "question": QUESTION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": llm.model_name,
        "invoke": inv,
        "stream": stm,
    }
    OUTPUT_HTML.write_text(build_html(data), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"报告已生成: {OUTPUT_HTML}")
    print("用浏览器打开即可对比两种调用方式的差异（含时间轴 / 曲线 / 动画回放）")


if __name__ == "__main__":
    main()
