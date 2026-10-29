"""Convert daily report into platform-specific .docx files for Yimei batch import.

Usage:
    python -m src.to_docx                 # read output/daily.md, write output/docx/*
    python -m src.to_docx --in file.md    # custom input

Produces one .docx per platform with a per-platform intro line so cross-platform
duplicate detection is less likely to fire.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
DOCX_DIR = OUT / "docx"

# per-platform: (subdir name, intro line added at top)
PLATFORMS = [
    ("gongzhonghao", "【海外 AI 工具情报日报】每天整理海外最新 AI 工具与开发动态。"),
    ("zhihu", "海外 AI 工具情报日报 · 每日精选"),
    ("toutiao", "海外 AI 工具日报｜每日精选海外新工具与开发动态"),
    ("baijia", "海外 AI 工具情报日报：每日精选，中文化要点"),
    ("xiaohongshu", "海外 AI 工具情报｜今日精选"),
]


def parse_daily(md_text):
    """Return dict: {date, title, items:[{n,title,source,url,blurb}]}"""
    lines = md_text.splitlines()
    date = ""
    title = ""
    items = []
    cur = None
    for ln in lines:
        m = re.match(r"^#\s+(.+)\s*-\s*(\d{4}-\d{2}-\d{2})$", ln)
        if m:
            title = m.group(1).strip()
            date = m.group(2)
            continue
        m = re.match(r"^##\s+(\d+)\.\s*(.+)$", ln)
        if m:
            if cur:
                items.append(cur)
            cur = {"n": int(m.group(1)), "title": m.group(2).strip(), "blurb": "", "url": "", "source": ""}
            continue
        m = re.match(r"^- 来源:\s*(.+)$", ln)
        if m and cur:
            cur["source"] = m.group(1).strip()
            continue
        m = re.match(r"^- 链接:\s*(.+)$", ln)
        if m and cur:
            cur["url"] = m.group(1).strip()
            continue
        m = re.match(r"^- (.+)$", ln)
        if m and cur and not cur.get("blurb"):
            cur["blurb"] = m.group(1).strip()
    if cur:
        items.append(cur)
    return {"date": date, "title": title, "items": items}


def build_doc(data, intro):
    doc = Document()
    # title
    h = doc.add_heading(data["title"], level=0)
    if data["date"]:
        doc.add_paragraph(data["date"] + " 发布")
    doc.add_paragraph(intro)
    for it in data["items"]:
        doc.add_heading("%d. %s" % (it["n"], it["title"]), level=1)
        if it["blurb"]:
            doc.add_paragraph(it["blurb"])
        if it["url"]:
            p = doc.add_paragraph()
            run = p.add_run("原文链接: ")
            run = p.add_run(it["url"])
        if it["source"]:
            doc.add_paragraph("来源: " + it["source"])
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(OUT / "daily.md"))
    args = ap.parse_args()
    md = Path(args.inp).read_text(encoding="utf-8")
    data = parse_daily(md)
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    for sub, intro in PLATFORMS:
        doc = build_doc(data, intro)
        out = DOCX_DIR / ("%s.docx" % sub)
        doc.save(str(out))
    print("wrote %d docx -> %s" % (len(PLATFORMS), DOCX_DIR))


if __name__ == "__main__":
    main()
