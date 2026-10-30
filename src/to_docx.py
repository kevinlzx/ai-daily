"""Convert daily report into platform-specific .docx files for Yimei batch import.

Usage:
    python -m src.to_docx                 # read output/daily.md, write output/docx/*.docx
    python -m src.to_docx --in file.md    # custom input

Each docx gets a cover image (output/cover/<date>.png) if one exists, then
a per-platform intro line so cross-platform duplicate detection is less likely.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
DOCX_DIR = OUT / "docx"
COVER = OUT / "cover"
COVERS = OUT / "covers"

# per-platform: (subdir name, intro line added after title)
PLATFORMS = [
    ("gongzhonghao", "每天整理海外最新 AI 工具与开发动态，中文解读要点。"),
    ("zhihu", "每日精选海外 AI 工具情报，中文化要点。"),
    ("toutiao", "每日精选海外新工具与开发动态，快速跟上前沿。"),
    ("baijia", "海外 AI 工具情报日报：每日精选，中文化要点。"),
    ("xiaohongshu", "海外 AI 工具情报｜今日精选。"),
]


def parse_daily(md_text):
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


def find_cover(date):
    if not date:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        cand = COVER / (date + ext)
        if cand.exists():
            return cand
    return None


def list_inline_covers():
    """Return sorted list of generic inline cover images under output/covers/."""
    if not COVERS.exists():
        return []
    files = sorted(COVERS.glob("*.png"))
    files += sorted(COVERS.glob("*.jpg"))
    files += sorted(COVERS.glob("*.jpeg"))
    return files


def build_doc(data, intro, inline_covers=None):
    doc = Document()
    doc.add_heading(data["title"], level=0)
    if data["date"]:
        doc.add_paragraph(data["date"] + " 发布")
    cover = find_cover(data["date"])
    if cover:
        doc.add_picture(str(cover), width=Inches(6.0))
        doc.add_paragraph("")
    doc.add_paragraph(intro)
    inline_covers = inline_covers or []
    for idx, it in enumerate(data["items"]):
        doc.add_heading("%d. %s" % (it["n"], it["title"]), level=1)
        if it["blurb"]:
            doc.add_paragraph(it["blurb"])
        if it["url"]:
            pp = doc.add_paragraph()
            pp.add_run("原文链接: ")
            pp.add_run(it["url"])
        if it["source"]:
            doc.add_paragraph("来源: " + it["source"])
        # per-item inline image (cycle through the palette set)
        if inline_covers:
            cover_path = inline_covers[idx % len(inline_covers)]
            pic = doc.add_picture(str(cover_path), width=Inches(5.0))
            cap = doc.add_paragraph("")
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(OUT / "daily.md"))
    args = ap.parse_args()
    md = Path(args.inp).read_text(encoding="utf-8")
    data = parse_daily(md)
    inline = list_inline_covers()
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    for sub, intro in PLATFORMS:
        doc = build_doc(data, intro, inline)
        out = DOCX_DIR / ("%s.docx" % sub)
        doc.save(str(out))
    print("wrote %d docx -> %s" % (len(PLATFORMS), DOCX_DIR))


if __name__ == "__main__":
    main()
