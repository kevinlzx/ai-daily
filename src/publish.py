"""Render the daily report into platform-specific versions.

Input : output/daily.md
Output: output/zhihu.md, output/gongzhonghao.md, output/xiaohongshu.md, output/planet.md

Design: each platform has its own tone and formatting rules.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"


def _parse_daily(md):
    """Return {date, items:[{rank,title,source,url,blurb}]} from daily.md."""
    lines = md.splitlines()
    date = ""
    items = []
    cur = None
    for ln in lines:
        m = re.match(r"^# .+ - (\d{4}-\d{2}-\d{2})$", ln)
        if m:
            date = m.group(1)
            continue
        m = re.match(r"^## (\d+)\.\s+(.+)$", ln)
        if m:
            if cur:
                items.append(cur)
            cur = {"rank": int(m.group(1)), "title": m.group(2).strip(), "blurb": ""}
            continue
        m = re.match(r"^- 来源:\s*(\S+)", ln)
        if m and cur:
            cur["source"] = m.group(1)
            continue
        m = re.match(r"^- 链接:\s*(\S+)", ln)
        if m and cur:
            cur["url"] = m.group(1)
            continue
        m = re.match(r"^- (.+)$", ln)
        if m and cur and not cur.get("blurb"):
            cur["blurb"] = m.group(1).strip()
    if cur:
        items.append(cur)
    return {"date": date, "items": items}


def _zhihu(data):
    parts = ["# 海外 AI 工具情报日报 - " + data["date"], ""]
    for it in data["items"]:
        parts.append("## %d. %s" % (it["rank"], it["title"]))
        parts.append("")
        parts.append(it["blurb"])
        parts.append("")
        parts.append("[%s](%s)" % (it["source"], it["url"]))
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def _gongzhonghao(data):
    parts = ["海外 AI 工具情报日报 · " + data["date"], "", "每天精选海外 AI 工具与动态，中文解读，帮助你快速跟上前沿。", ""]
    for it in data["items"]:
        parts.append("### %d. %s" % (it["rank"], it["title"]))
        parts.append("")
        parts.append(it["blurb"])
        parts.append("")
    parts.append("— 本日报由脚本自动整理生成，人工复核 —")
    return "\n".join(parts).strip() + "\n"


def _xiaohongshu(data):
    parts = ["海外 AI 工具情报｜" + data["date"], ""]
    for it in data["items"]:
        parts.append("%d. %s" % (it["rank"], it["title"]))
        parts.append(it["blurb"])
        parts.append("")
    parts.append("#AI工具 #出海 #海外副业 #工具推荐")
    return "\n".join(parts).strip() + "\n"


def _planet(data):
    parts = ["## 今日 AI 工具情报 · " + data["date"], ""]
    for it in data["items"]:
        parts.append("**%d. %s**" % (it["rank"], it["title"]))
        parts.append("")
        parts.append(it["blurb"])
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(OUT / "daily.md"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    md = Path(args.inp).read_text(encoding="utf-8")
    data = _parse_daily(md)
    files = {
        "zhihu.md": _zhihu(data),
        "gongzhonghao.md": _gongzhonghao(data),
        "xiaohongshu.md": _xiaohongshu(data),
        "planet.md": _planet(data),
    }
    for name, body in files.items():
        Path(args.out, name).write_text(body, encoding="utf-8")
    sys.stderr.write("wrote %d platforms -> %s\n" % (len(files), args.out))
    return len(files)


if __name__ == "__main__":
    main()
