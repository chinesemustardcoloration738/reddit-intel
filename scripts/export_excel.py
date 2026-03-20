#!/usr/bin/env python3
"""
export_excel.py — reddit-intel skill Excel 导出脚本

用法：
  python3 export_excel.py --input posts_processed.json --keyword "关键词"

输出：
  reddit_intel_[关键词]_[YYYYMMDD].xlsx
"""

import sys
import json
import argparse
import re
from datetime import datetime
from pathlib import Path
from collections import Counter

try:
    import openpyxl
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side
    )
    from openpyxl.utils import get_column_letter
    from openpyxl.styles.numbers import FORMAT_TEXT
except ImportError:
    print("错误：需要安装 openpyxl\n运行：pip install openpyxl")
    sys.exit(1)


# ── 样式常量 ──────────────────────────────────────────────────────────

HEADER_BG = "1a1a2e"
HEADER_FG = "ffffff"

SENTIMENT_STYLE = {
    "正面": ("d4edda", "155724"),
    "负面": ("f8d7da", "721c24"),
    "中性": ("e2e3e5", "383d41"),
    "混合": ("fff3cd", "856404"),
}

CONFIDENCE_STYLE = {
    "高": ("d4edda", "155724"),
    "中": ("fff3cd", "856404"),
    "低": ("f8d7da", "721c24"),
}

ROW_ODD_BG  = "ffffff"
ROW_EVEN_BG = "f8f9fa"
ACTION_BG   = "fefce8"


# ── 列定义 ────────────────────────────────────────────────────────────

COLUMNS = [
    ("标题（原文）",   "title_original",          50, "left",   False),
    ("标题（中文）",   "title_zh",                50, "left",   False),
    ("内容摘要（中文）","summary_zh",              70, "left",   False),
    ("核心意图",       "core_intent",             14, "center", False),
    ("主分类",         "main_category",           16, "center", False),
    ("子标签",         "sub_tags",                24, "left",   False),
    ("情绪",           "sentiment",               10, "center", True),   # 带颜色
    ("提及竞品",       "competitors_mentioned",   24, "left",   False),
    ("使用场景",       "use_case",                28, "left",   False),
    ("热评精华",       "top_comments_summary",    60, "left",   False),
    ("行动点",         "action_item",             50, "left",   True),   # 加粗+黄底
    ("置信度",         "confidence",              10, "center", True),   # 带颜色
    ("点赞数",         "upvotes",                  8, "center", False),
    ("评论数",         "num_comments",             8, "center", False),
    ("来源版块",       "subreddit",               18, "center", False),
    ("发帖时间",       "created_date",            12, "center", False),
    ("原帖链接",       "url",                     40, "left",   False),
]


def make_fill(hex_color):
    return PatternFill(fill_type="solid", fgColor=hex_color)


def make_font(bold=False, color="000000", size=10, underline=None):
    kwargs = dict(bold=bold, color=color, size=size)
    if underline:
        kwargs["underline"] = underline
    return Font(**kwargs)


def make_align(horizontal="left", wrap_text=True):
    return Alignment(horizontal=horizontal, vertical="top", wrap_text=wrap_text)


def get_cell_value(post, field):
    val = post.get(field, "")
    if isinstance(val, list):
        return ", ".join(str(v) for v in val) if val else ""
    if val is None:
        return ""
    return val


def safe_filename(keyword):
    """生成安全的文件名片段。"""
    return re.sub(r'[^\w\u4e00-\u9fff\-]', '_', keyword)[:30]


# ── 主数据 Sheet ──────────────────────────────────────────────────────

def build_data_sheet(ws, posts):
    # 冻结表头
    ws.freeze_panes = "A2"

    # 写表头
    header_font  = make_font(bold=True, color=HEADER_FG)
    header_fill  = make_fill(HEADER_BG)
    header_align = make_align(horizontal="center", wrap_text=False)

    for col_idx, (col_name, _, col_width, _, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width

    ws.row_dimensions[1].height = 22

    # 写数据行
    for row_idx, post in enumerate(posts, start=2):
        is_even = (row_idx % 2 == 0)
        default_bg = ROW_EVEN_BG if is_even else ROW_ODD_BG

        for col_idx, (_, field, _, align, special) in enumerate(COLUMNS, start=1):
            value = get_cell_value(post, field)
            cell  = ws.cell(row=row_idx, column=col_idx, value=value)

            # 情绪列
            if field == "sentiment" and value in SENTIMENT_STYLE:
                bg, fg = SENTIMENT_STYLE[value]
                cell.fill = make_fill(bg)
                cell.font = make_font(bold=True, color=fg)
            # 置信度列
            elif field == "confidence" and value in CONFIDENCE_STYLE:
                bg, fg = CONFIDENCE_STYLE[value]
                cell.fill = make_fill(bg)
                cell.font = make_font(bold=True, color=fg)
            # 行动点列
            elif field == "action_item":
                cell.fill = make_fill(ACTION_BG)
                cell.font = make_font(bold=True)
            # URL 列
            elif field == "url" and value:
                cell.font = make_font(color="0563C1", underline="single")
            else:
                cell.fill = make_fill(default_bg)
                cell.font = make_font()

            cell.alignment = make_align(horizontal=align)

        ws.row_dimensions[row_idx].height = 60


# ── 概览 Sheet ────────────────────────────────────────────────────────

def build_summary_sheet(ws, posts, keyword):
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 20

    title_font   = make_font(bold=True, size=14)
    section_font = make_font(bold=True, size=11)
    normal_font  = make_font(size=10)

    def write_row(row, label, value="", bold_label=False):
        a = ws.cell(row=row, column=1, value=label)
        b = ws.cell(row=row, column=2, value=value)
        a.font = section_font if bold_label else normal_font
        b.font = normal_font
        a.alignment = make_align(wrap_text=False)
        b.alignment = make_align(wrap_text=False)

    r = 1
    ws.cell(row=r, column=1, value=f"Reddit Intel 概览 — {keyword}").font = title_font
    r += 2

    # 基础信息
    write_row(r, "总帖数", len(posts), bold_label=True); r += 1
    dates = [p.get("created_date", "") for p in posts if p.get("created_date")]
    date_range = f"{min(dates)} 至 {max(dates)}" if dates else "—"
    write_row(r, "时间跨度", date_range); r += 1
    subreddits = [p.get("subreddit", "") for p in posts if p.get("subreddit")]
    write_row(r, "来源版块数", len(set(subreddits))); r += 2

    # 情绪分布
    write_row(r, "情绪分布", bold_label=True); r += 1
    sentiment_counter = Counter(p.get("sentiment", "未知") for p in posts)
    for s, count in sentiment_counter.most_common():
        pct = f"{count/len(posts)*100:.1f}%" if posts else "—"
        write_row(r, f"  {s}", f"{count} 条 ({pct})"); r += 1
    r += 1

    # 核心意图分布
    write_row(r, "核心意图分布", bold_label=True); r += 1
    intent_counter = Counter(p.get("core_intent", "未知") for p in posts)
    for intent, count in intent_counter.most_common():
        write_row(r, f"  {intent}", f"{count} 条"); r += 1
    r += 1

    # 置信度分布
    write_row(r, "置信度分布", bold_label=True); r += 1
    conf_counter = Counter(p.get("confidence", "未知") for p in posts)
    for conf in ["高", "中", "低"]:
        count = conf_counter.get(conf, 0)
        write_row(r, f"  {conf}", f"{count} 条"); r += 1
    r += 1

    # 提及最多的竞品 Top 5
    all_competitors = []
    for p in posts:
        comps = p.get("competitors_mentioned", [])
        if isinstance(comps, list):
            all_competitors.extend(comps)
        elif isinstance(comps, str) and comps:
            all_competitors.extend([c.strip() for c in comps.split(",") if c.strip()])
    if all_competitors:
        write_row(r, "提及最多竞品 Top 5", bold_label=True); r += 1
        comp_counter = Counter(all_competitors)
        for comp, count in comp_counter.most_common(5):
            write_row(r, f"  {comp}", f"{count} 次提及"); r += 1
        r += 1

    # 点赞最高 Top 5
    write_row(r, "点赞最高的帖子 Top 5", bold_label=True); r += 1
    top_posts = sorted(posts, key=lambda p: int(p.get("upvotes", 0) or 0), reverse=True)[:5]
    for p in top_posts:
        title = (p.get("title_zh") or p.get("title_original") or "")[:40]
        upvotes = p.get("upvotes", 0)
        write_row(r, f"  {title}", f"👍 {upvotes}"); r += 1


# ── 主程序 ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Reddit Intel Excel 导出')
    parser.add_argument('--input',   required=True, help='posts_processed.json 路径')
    parser.add_argument('--keyword', default='reddit', help='关键词（用于文件名）')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：找不到文件 {input_path}")
        sys.exit(1)

    with open(input_path, encoding='utf-8') as f:
        posts = json.load(f)

    if not posts:
        print("错误：posts_processed.json 为空")
        sys.exit(1)

    print(f"\n生成 Excel：{len(posts)} 条帖子...")

    wb = openpyxl.Workbook()

    # Sheet 1：主数据
    ws_data = wb.active
    ws_data.title = "舆情数据"
    build_data_sheet(ws_data, posts)

    # Sheet 2：概览
    ws_summary = wb.create_sheet("概览")
    build_summary_sheet(ws_summary, posts, args.keyword)

    # 文件命名
    safe_kw   = safe_filename(args.keyword)
    date_str  = datetime.now().strftime('%Y%m%d')
    filename  = f"reddit_intel_{safe_kw}_{date_str}.xlsx"
    out_path  = Path.cwd() / filename

    wb.save(out_path)

    print(f"\n✅ 完成")
    print(f"  文件：{out_path}")
    print(f"  帖子数：{len(posts)} 条")
    print(f"  列数：{len(COLUMNS)} 列（舆情数据 Sheet）+ 概览 Sheet")


if __name__ == '__main__':
    main()
