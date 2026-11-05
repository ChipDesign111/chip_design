# -*- coding: utf-8 -*-
"""Build the RTL cycle-optimisation deck for the INT8 HAR-MLP SoC.

Numbers come from eda/results/lat_ifetch_20261104/{README.md,results.json}
and the SDF post-simulation package in ./postsim/.
"""
import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---- design tokens -------------------------------------------------------
SURFACE = RGBColor(0xFC, 0xFC, 0xFB)
CARD = RGBColor(0xF4, 0xF3, 0xEF)
INK = RGBColor(0x0B, 0x0B, 0x0B)
INK2 = RGBColor(0x52, 0x51, 0x4E)
MUTED = RGBColor(0x89, 0x87, 0x81)
RULE = RGBColor(0xE1, 0xE0, 0xD9)
BLUE = RGBColor(0x2A, 0x78, 0xD6)
BLUE_D = RGBColor(0x18, 0x4F, 0x95)
ORANGE = RGBColor(0xEB, 0x68, 0x34)
GOOD = RGBColor(0x00, 0x63, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "微软雅黑"
W, H = 13.333, 7.5
HERE = os.path.dirname(os.path.abspath(__file__))

prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]

PAGE = {"n": 0}


# ---- helpers -------------------------------------------------------------
def _ea(run, name=FONT):
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", name)


def style(run, size, bold=False, color=INK, name=FONT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = name
    _ea(run, name)


def textbox(slide, x, y, w, h, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.paragraphs[0].alignment = align
    return tf


def para(tf, first=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = PP_ALIGN.LEFT
    return p


def line(tf, text, size=18, bold=False, color=INK2, space_before=0,
         space_after=0, first=False, align=PP_ALIGN.LEFT, line_spacing=None):
    p = para(tf, first)
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    if line_spacing:
        p.line_spacing = line_spacing
    r = p.add_run()
    r.text = text
    style(r, size, bold, color)
    return p


def rect(slide, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE, line_color=None,
         line_w=1.0, radius=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.shadow.inherit = False
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line_color is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line_color
        s.line.width = Pt(line_w)
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.text_frame.word_wrap = True
    return s


def shape_text(s, text, size=13, bold=False, color=INK, align=PP_ALIGN.CENTER):
    tf = s.text_frame
    tf.margin_left = Inches(0.06)
    tf.margin_right = Inches(0.06)
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    style(r, size, bold, color)


def slide_base(kicker="", title="", subtitle=""):
    s = prs.slides.add_slide(BLANK)
    rect(s, 0, 0, W, H, SURFACE)
    PAGE["n"] += 1
    tf = textbox(s, 0.75, 7.02, 9.5, 0.3)
    line(tf, "取指行缓冲 · INT8 HAR-MLP SoC · 2026-11-05", 9, False, MUTED, first=True)
    tf = textbox(s, 11.9, 7.02, 0.7, 0.3, align=PP_ALIGN.RIGHT)
    line(tf, "%02d" % PAGE["n"], 9, False, MUTED, first=True, align=PP_ALIGN.RIGHT)
    if title:
        if kicker:
            tf = textbox(s, 0.75, 0.46, 11.8, 0.3)
            line(tf, kicker, 11, True, BLUE, first=True)
            y = 0.80
        else:
            y = 0.62
        tf = textbox(s, 0.75, y, 11.8, 0.75)
        line(tf, title, 30 if len(title) < 24 else 26, True, INK, first=True)
        ty = y + 0.78
        if subtitle:
            tf = textbox(s, 0.75, ty, 11.6, 0.4)
            line(tf, subtitle, 13, False, MUTED, first=True)
            ty += 0.42
        rect(s, 0.75, ty, 11.83, 0.014, RULE)
        s._content_top = ty + 0.34
    return s


def table(slide, x, y, w, rows, col_w, row_h=0.42, head_h=0.46,
          size=12, head_size=12, align=None):
    """Rows: list of lists; the first is the header."""
    n_rows, n_cols = len(rows), len(rows[0])
    total_h = head_h + row_h * (n_rows - 1)
    gt = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y),
                                Inches(w), Inches(total_h)).table
    gt.first_row = True
    gt.horz_banding = False
    for j, cw in enumerate(col_w):
        gt.columns[j].width = Inches(cw)
    gt.rows[0].height = Inches(head_h)
    for i in range(1, n_rows):
        gt.rows[i].height = Inches(row_h)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = gt.cell(i, j)
            cell.margin_left = Inches(0.10)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = BLUE_D if i == 0 else (
                WHITE if i % 2 else CARD)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = (PP_ALIGN.LEFT if j == 0 else
                           (align[j] if align else PP_ALIGN.CENTER))
            r = p.add_run()
            r.text = str(val)
            style(r, head_size if i == 0 else size, i == 0,
                  WHITE if i == 0 else INK)
    return gt


# ---- 1. cover ------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, W, H, SURFACE)
rect(s, 0, 0, 0.22, H, BLUE)
PAGE["n"] += 1
tf = textbox(s, 1.15, 1.55, 10.6, 0.35)
line(tf, "TSMC 180 nm · INT8 HAR-MLP SoC · 流片课程", 13, True, BLUE, first=True)
tf = textbox(s, 1.15, 2.05, 10.9, 1.9)
line(tf, "取指行缓冲：", 44, True, INK, first=True, line_spacing=1.12)
line(tf, "CPU 自检段砍掉三分之一", 44, True, INK, line_spacing=1.12)
tf = textbox(s, 1.15, 4.05, 10.4, 0.9)
line(tf, "只改 RTL、不改测试台：3,650 → 2,337 拍（−36.0%），"
         "并在 20 ns SDF 门级后仿 17/17 通过", 15, False, INK2, first=True,
     line_spacing=1.45)
rect(s, 1.15, 5.15, 2.2, 0.02, BLUE)
tf = textbox(s, 1.15, 5.40, 10.4, 0.9)
line(tf, "整片面积 3.7956 mm²（限 3.8） · Setup WNS +0.445 ns · Hold WNS +0.019 ns",
     13, False, MUTED, first=True, line_spacing=1.5)
line(tf, "2026-11-05 · commit 2714f61", 13, False, MUTED, line_spacing=1.5)

# ---- 2. headline ---------------------------------------------------------
s = slide_base("结论先行", "四个数字",
               "所有数据来自同一版本：RTL 行为级 + 布局布线 + SDF 门级后仿")
kpis = [
    ("2,337", "拍", "CPU 自检段", "3,650 → 2,337（−36.0%）", GOOD),
    ("2,338", "拍", "门级后仿", "17/17 用例通过，统计值无偏移", GOOD),
    ("8,536", "拍", "端到端", "9,832 → 8,536（−13.2%）", GOOD),
    ("3.7956", "mm²", "整片面积", "限 3.8 mm²，WNS +0.445 ns", INK),
]
x0, gap = 0.75, 0.28
card_w = (11.83 - gap * 3) / 4
for i, (num, unit, label, note, col) in enumerate(kpis):
    x = x0 + i * (card_w + gap)
    rect(s, x, 2.02, card_w, 2.30, CARD, MSO_SHAPE.ROUNDED_RECTANGLE,
         radius=0.06)
    tf = textbox(s, x + 0.26, 2.24, card_w - 0.5, 0.4)
    line(tf, label, 11.5, True, MUTED, first=True)
    tf = textbox(s, x + 0.26, 2.66, card_w - 0.5, 0.75)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = num
    style(r, 34, True, INK)
    r2 = p.add_run()
    r2.text = " " + unit
    style(r2, 13, True, INK2)
    tf = textbox(s, x + 0.26, 3.52, card_w - 0.5, 0.62)
    line(tf, note, 10.5, False, col, first=True, line_spacing=1.35)

tf = textbox(s, 0.75, 4.72, 11.83, 1.6)
line(tf, "改的是取指通路。", 18, True, INK, first=True, space_after=6)
line(tf, "原来每条指令走一次单拍 AXI 事务、3 拍往返且不能重叠；换成 8 字行缓冲 + "
         "INCR burst 预取后，顺序代码 1 指令/拍，取指代价从 1,543 拍降到 230 拍。",
     14.5, False, INK2, line_spacing=1.6)
line(tf, "NPU、DMA、存储器接口、装载协议都没有改动。", 14.5, False, MUTED,
     space_before=6)

# ---- 3. end-to-end budget ------------------------------------------------
s = slide_base("端到端", "8,536 拍花在哪",
               "橙色是测试台协议下限，蓝色是本轮动过的部分")
budget = [
    ("装载窗口（SBA 逐字写）", 6182, 72.4, ORANGE),
    ("CPU 自检", 2337, 27.4, BLUE),
    ("收尾", 17, 0.2, MUTED),
]
bx, by, bw = 0.75, 2.30, 11.83
total = sum(b[1] for b in budget)
acc = 0.0
for name, cyc, pct, col in budget:
    w = bw * cyc / total
    rect(s, bx + acc, by, w, 0.62, col)
    if w > 0.9:
        shape_text(s.shapes[-1], f"{cyc:,} 拍 · {pct}%", 12, True, WHITE)
    acc += w
rect(s, bx, by, bw, 0.62, None, MSO_SHAPE.RECTANGLE, SURFACE, 0.5)

# legend
lx = 0.75
for name, cyc, pct, col in budget:
    rect(s, lx, 3.18, 0.16, 0.16, col)
    tf = textbox(s, lx + 0.24, 3.12, 3.4, 0.3)
    line(tf, name, 11.5, False, INK2, first=True)
    lx += 3.9

tf = textbox(s, 0.75, 3.80, 5.6, 2.4)
line(tf, "装载窗口 6,182 拍（72.4%）", 15, True, INK, first=True, space_after=8)
line(tf, "测试台自身协议下限：驱动 → 判 gnt → 撤 req → 判 r_valid，"
         "共 3 个下降沿/字。", 12.5, False, INK2, line_spacing=1.55)
line(tf, "RTL 侧写响应已经只要 1 拍，不改 TB 无法再省。", 12.5, False, INK2,
     line_spacing=1.55, space_before=6)

tf = textbox(s, 6.85, 3.80, 5.6, 2.4)
line(tf, "CPU 自检 2,337 拍（27.4%）", 15, True, INK, first=True, space_after=8)
line(tf, "NPU 本身 1,038 拍 + CPU 复制/比较约 1,070 拍 + 取指残余 230 拍。",
     12.5, False, INK2, line_spacing=1.55)
line(tf, "本轮动的就是最后这一项。", 12.5, True, BLUE, line_spacing=1.55,
     space_before=6)

rect(s, 0.75, 5.95, 11.83, 0.02, RULE)
tf = textbox(s, 0.75, 6.12, 11.83, 0.5)
line(tf, "结论：端到端剩下的 72% 是测试台装载协议，本轮改完 CPU 段后，再往下压只能从 TB 或架构入手。",
     11.5, False, MUTED, first=True)

# ---- 4. problem ----------------------------------------------------------
s = slide_base("问题定位", "取指是唯一的冗余",
               "用“理想取指探针”把取指口压成零代价，测出真实下限")
tf = textbox(s, 0.75, 1.95, 11.8, 1.0)
line(tf, "保留真实 SoC，只把 CPU 取指口强制成“同拍给 gnt、下一拍给数据、数据取自镜像”，"
         "并把 xbar 取指从端口压住：", 14, False, INK2, first=True, line_spacing=1.5)
tf = textbox(s, 0.75, 2.55, 11.8, 0.5)
line(tf, "IDEAL   cycles = 2,107      npu_cycles = 1,035", 15, True, INK,
     first=True)

cards = [
    ("2,107 拍", "零取指代价时的自检段下限", BLUE),
    ("3,650 拍", "实测（每指令 3 拍往返、事务不能重叠）", ORANGE),
    ("1,543 拍", "纯取指开销 = 42% 的自检段", INK),
]
for i, (num, note, col) in enumerate(cards):
    x = 0.75 + i * 3.98
    rect(s, x, 3.30, 3.70, 1.45, CARD, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.07)
    rect(s, x, 3.30, 0.05, 1.45, col)
    tf = textbox(s, x + 0.28, 3.50, 3.2, 0.55)
    line(tf, num, 26, True, INK, first=True)
    tf = textbox(s, x + 0.28, 4.12, 3.2, 0.55)
    line(tf, note, 11, False, INK2, first=True, line_spacing=1.3)

tf = textbox(s, 0.75, 5.05, 11.8, 1.7)
line(tf, "为什么这么贵", 14, True, INK, first=True, space_after=6)
for t in ["每条指令 = 一次独立的单拍 AXI 事务：AR 握手 → 次拍 r 有效 → COMPLETE_READ，共 3 拍；",
          "axi_xbar 配置为 MaxSlvTrans=1，事务之间无法重叠，流水被完全串行化；",
          "而同一段代码反复执行，指令本来就有极强的空间局部性——这正是缓存/行缓冲能吃下的部分。"]:
    line(tf, "·  " + t, 12.5, False, INK2, line_spacing=1.5, space_before=3)

# ---- 5. the change -------------------------------------------------------
s = slide_base("改动", "my_ifetch：8 字行缓冲 + 顺序预取",
               "新增 rtl/soc/my_ifetch.sv，替换 i_axi_adapter_instr；只读通道")
boxes = [
    ("CPU\nIF 口", BLUE_D, 1.5),
    ("my_ifetch\n4 × 8 字 · LRU", BLUE, 2.4),
    ("axi_xbar", INK2, 1.5),
    ("axi2mem", INK2, 1.5),
    ("SRAM / BootROM", INK2, 1.7),
]
x = 0.75
bx_y, bx_h = 2.05, 0.78
for i, (name, col, wid) in enumerate(boxes):
    b = rect(s, x, bx_y, wid, bx_h, col, MSO_SHAPE.ROUNDED_RECTANGLE,
             radius=0.12)
    shape_text(b, name, 10.5, True, WHITE)
    x += wid
    if i < len(boxes) - 1:
        rect(s, x + 0.03, bx_y + bx_h / 2 - 0.045, 0.22, 0.09, MUTED,
             MSO_SHAPE.RIGHT_ARROW)
        x += 0.30
rect(s, 2.30, 3.00, 2.35, 0.05, BLUE)
tf = textbox(s, 2.30, 3.12, 3.2, 0.3)
line(tf, "命中当拍给 gnt，数据下一拍到", 10, False, INK2, first=True)

tf = textbox(s, 0.75, 3.62, 5.75, 3.0)
line(tf, "四个要点", 14, True, INK, first=True, space_after=8)
for t, d in [("一笔 burst 取一整行", "8 字对齐行用 INCR burst 取回，25 次填充代替上千次单拍事务"),
             ("边填边可用", "每到一个 beat 就放开对应字，miss 落在第 k 字只等 k 拍"),
             ("一行提前预取", "命中行之后的那一行在后台取，循环体常驻时不产生额外流量"),
             ("4 路全相联 + LRU", "1,024 个触发器，与 4 字×8 行同面积，但只有 4 路 tag 比较")]:
    line(tf, t, 12, True, INK, space_before=8)
    line(tf, d, 11, False, INK2, line_spacing=1.45)

tf = textbox(s, 6.95, 3.62, 5.6, 3.0)
line(tf, "边界条件", 14, True, INK, first=True, space_after=8)
for t in ["burst 只发给 boot ROM 与 SRAM 两个区间（都由 axi2mem 服务，支持 INCR）；",
          "其余地址——尤其 DM 停机区——退回单字取指，避免从端口收到它服务不了的 burst；",
          "只读通道，不碰数据通路，因此 DMA 重叠计数、NPU 周期数全部不变。"]:
    line(tf, "·  " + t, 11.5, False, INK2, line_spacing=1.5, space_before=4)

# ---- 6. design choices ---------------------------------------------------
s = slide_base("设计选择", "为什么是 8 字 × 4 行", "同一探针台、同一固件，全部 PASS")
table(s, 0.75, 1.98, 11.83, [
    ["配置", "自检段拍数", "填充次数 (miss / 预取)", "停顿拍"],
    ["4 字 × 8 行", "2,662", "159 (77 / 82)", "568"],
    ["4 字 × 8 行 ＋ 边填边可用", "2,448", "122 (53 / 69)", "278"],
    ["8 字 × 3 行 ＋ 边填边可用", "2,217", "27 (3 / 24)", "24"],
    ["8 字 × 4 行 ＋ 边填边可用", "2,199", "25 (2 / 23)", "10"],
    ["8 字 × 8 行 ＋ 边填边可用", "2,199", "25 (2 / 23)", "10"],
], [4.63, 2.4, 3.0, 1.8], row_h=0.46, head_h=0.48, size=12, head_size=12)
tf = textbox(s, 0.75, 4.90, 11.83, 0.35)
line(tf, "表中绝对拍数是在“单拍读旁路”仍在时测的（该旁路已回退，见后页），整列偏低约 138 拍；"
         "行间差值与排序不受影响。", 10, False, MUTED, first=True, line_spacing=1.3)

tf = textbox(s, 0.75, 5.42, 5.7, 1.4)
line(tf, "2 行方案反而更慢", 12, True, INK, first=True, space_after=2)
line(tf, "3,496 拍——向后跳转回到的正是刚被换出的上一行，每轮迭代都重取。",
     11.5, False, INK2, line_spacing=1.45)

tf = textbox(s, 6.75, 5.42, 5.85, 1.4)
line(tf, "采用 8 × 4 的理由", 12, True, INK, first=True, space_after=2)
line(tf, "与 8 × 8 完全同速，但行存储只用一半，且命中通路只有 4 路比较，对 20 ns 时序最友好。",
     11.5, False, INK2, line_spacing=1.45)

# ---- 7. result chart -----------------------------------------------------
s = slide_base("效果", "取指开销被吃掉 85%", "")
s.shapes.add_picture(os.path.join(HERE, "chart_breakdown.png"),
                     Inches(0.75), Inches(1.62), width=Inches(11.4))
tf = textbox(s, 0.75, 5.55, 11.83, 1.3)
line(tf, "门级后仿同样成立：sdf_max 3,651 → 2,338 拍（−36.0%），统计值 "
         "npu=1,038 / DMA 读 62 / 写 93 与 RTL 完全一致。", 12.5, False, INK2,
     first=True, line_spacing=1.5)
line(tf, "剩下的 230 拍全部是每次 load 的 3 拍往返，受 SRAM 时序约束，RTL 侧已无空间。",
     12.5, False, MUTED, line_spacing=1.5, space_before=4)

# ---- 8. the revert -------------------------------------------------------
s = slide_base("反面教材", "一次“更快”的改动被后仿打回",
               "单拍读省 COMPLETE_READ：RTL 省 138 拍，门级全错")
steps = [
    ("做法", "WAIT_R_VALID 收到 r.last 当拍就给出 valid_o / rdata_o，不绕 COMPLETE_READ，"
             "取指往返 3 拍 → 2 拍"),
    ("症状", "后仿统计区整体右移一格：[0xc0dec0de, 1038, 93, 62]；gate_zero 里 CPU 对 NPU 状态口"
             " 0x70000004 的 bne 读到旧值，跳进 fail:"),
    ("根因", "读数据直接来自 SRAM 宏的 Q 输出；my_mainmem 用 sram_clk = ~clk_i 驱动宏，"
             "Q 要到系统时钟下降沿才有效，而不是 r 握手那个上升沿"),
    ("证据", "连续读 [11111111, 22222222, 33333333, 44444444] → 读回 [xxxx, 11111111, 22222222, 33333333]"),
    ("结论", "已完整回退。这 138 拍是买正确性的代价：自检段 2,199 → 2,337 拍，仍比起点 3,650 拍少 36%"),
]
y = 1.95
for i, (k, v) in enumerate(steps):
    col = ORANGE if k != "结论" else BLUE
    rect(s, 0.75, y, 0.06, 0.72, col)
    tf = textbox(s, 1.02, y, 1.3, 0.35)
    line(tf, k, 13, True, col, first=True)
    tf = textbox(s, 2.30, y - 0.02, 10.2, 0.8)
    line(tf, v, 12, k == "结论", INK if k == "结论" else INK2, first=True,
         line_spacing=1.4)
    y += 0.86

tf = textbox(s, 0.75, 6.30, 11.83, 0.5)
line(tf, "教训：RTL 行为级仿真给不出存储宏的边沿时序，凡是“数据比握手早一拍”的优化，"
         "必须用 SDF 门级后仿裁决。", 12, True, BLUE, first=True, line_spacing=1.4)

# ---- 9. physical ---------------------------------------------------------
s = slide_base("物理实现", "面积、时序、DRC 全绿",
               "Genus 19.1 + Innovus 21.16，34 个步骤全部完成")
table(s, 0.75, 2.52, 7.35, [
    ["项目", "结果"],
    ["整片面积", "3.7956 mm²（限 3.8）"],
    ["Setup WNS / TNS", "+0.445 ns / 0"],
    ["Setup 违例路径", "0"],
    ["Hold WNS / TNS", "+0.019 ns / 0"],
    ["Hold 违例路径", "0"],
    ["default DRC", "0"],
    ["full-core PG", "0"],
    ["Antenna", "0 条违例网络"],
], [3.35, 4.0], row_h=0.46, head_h=0.46, size=12,
    align=[PP_ALIGN.LEFT, PP_ALIGN.LEFT])

tf = textbox(s, 8.55, 2.52, 4.0, 2.6)
line(tf, "整片尺寸没动", 14, True, INK, first=True, space_after=8)
line(tf, "die 边框由 floorplan 固定，两版都是 3.7956390976 mm²，"
         "不变的是这个框，不是单元面积。", 11.5, False, INK2, line_spacing=1.5)
line(tf, "标准单元 58,652 → 61,591 个。", 11.5, False, MUTED,
     line_spacing=1.5, space_before=6)

tf = textbox(s, 8.55, 4.62, 4.0, 1.9)
line(tf, "真实代价在利用率里", 13, True, INK, first=True, space_after=6)
line(tf, "单元面积 1.896 → 1.980 mm²，+0.083 mm²（+4.4%），占整片 2.2%，"
         "被布线空隙吸收；整片仍在 3.8 mm² 以内。", 11.5, False, INK2,
     line_spacing=1.5)

# ---- 10. post-sim --------------------------------------------------------
s = slide_base("门级验证", "SDF 后仿 17/17 全通过",
               "20 ns 系统时钟，SDF 反标，含真实 SRAM 宏模型")
table(s, 0.75, 2.52, 7.35, [
    ["用例组", "数量", "结果"],
    ["sdf_max（SDF）", "1", "PASS · 2,338 拍"],
    ["gate_zero（无 SDF）", "1", "PASS · 2,337 拍"],
    ["复位相位扫描", "15", "全部 PASS · 2,338 拍"],
    ["SDF 回标", "—", "error 0 / 缺失实例 0"],
    ["工作窗口检查", "—", "通过"],
], [3.0, 1.35, 3.0], row_h=0.5, head_h=0.48, size=12,
    align=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER])

tf = textbox(s, 8.55, 2.52, 4.05, 3.6)
line(tf, "每个用例读回的固件计数器完全一致", 13, True, INK, first=True,
     space_after=8)
line(tf, "cycles 2,337~2,338", 12, False, INK2, line_spacing=1.5)
line(tf, "npu_cycles 1,038", 12, False, INK2, line_spacing=1.5)
line(tf, "DMA 与 MAC 重叠 93", 12, False, INK2, line_spacing=1.5)
line(tf, "读重叠 62 / 写重叠 93", 12, False, INK2, line_spacing=1.5)
line(tf, "与 RTL 完全一致，没有右移。", 12, True, GOOD, space_before=8,
     line_spacing=1.5)
line(tf, "计时检查信息 15 条，全部是时钟门控单元使能端的 $setuphold，"
         "上一轮同类 12 条，非本轮引入。", 10.5, False, MUTED, space_before=10,
     line_spacing=1.45)

tf = textbox(s, 0.75, 5.55, 11.83, 1.1)
line(tf, "对比上一轮：3,651 → 2,338 拍（−36.0%）。本轮未跑独立 DRC/LVS，不宣称独立签核。",
     12, False, MUTED, first=True, line_spacing=1.5)

# ---- 11. closing ---------------------------------------------------------
s = slide_base("下一步", "还剩多少、往哪走", "")
tf = textbox(s, 0.75, 1.95, 5.7, 4.2)
line(tf, "已经接近下限", 14, True, INK, first=True, space_after=8)
line(tf, "自检段 2,337 拍 vs 理想取指下限 2,107 拍，只剩 230 拍（占端到端 2.7%），"
         "且全部落在每次 load 的 3 拍往返上。", 12, False, INK2, line_spacing=1.55)
line(tf, "继续压 RTL 的收益已低于风险。", 12, True, BLUE, space_before=8,
     line_spacing=1.5)

tf = textbox(s, 6.75, 1.95, 5.85, 4.2)
line(tf, "真正的大头在别处", 14, True, INK, first=True, space_after=8)
for t in ["装载窗口 6,182 拍（72.4%）——测试台协议，不改 TB 动不了；",
          "若允许改 TB：流水装载可把 3 拍/字降到 2 拍/字；",
          "若允许改架构：提高 SRAM 端口带宽 / NPU 并行度，才能动 1,038 拍的 NPU 段。"]:
    line(tf, "·  " + t, 12, False, INK2, line_spacing=1.55, space_before=6)

rect(s, 0.75, 5.95, 11.83, 0.02, RULE)
tf = textbox(s, 0.75, 6.12, 11.83, 0.6)
line(tf, "交付物：rtl/soc/my_ifetch.sv、17 用例后仿结果包、完整实验记录 "
         "eda/results/lat_ifetch_20261104/", 11.5, False, MUTED, first=True)

out = os.path.join(HERE, "取指行缓冲_周期优化_20261105.pptx")
prs.save(out)
print("wrote", out)
