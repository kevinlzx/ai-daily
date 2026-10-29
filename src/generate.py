"""Generate a Chinese daily report from raw items via Agnes API.

Usage:
    python -m src.generate              # read data/raw.json, write output/daily.md
    python -m src.generate --items 20   # cap how many items to cover

Pipeline is resilient: if the API call fails, it falls back to a
rule-based rendering so a daily report is still produced.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "output"


def load_raw(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_key():
    # AGNES_API_KEY is read from the Hermes env file if not exported already.
    key = os.environ.get("AGNES_API_KEY")
    if key:
        return key
    for cand in (
        Path(os.environ.get("LOCALAPPDATA", "") + r"\hermes\.env"),
        Path.home() / "AppData" / "Local" / "hermes" / ".env",
    ):
        if cand.exists():
            try:
                for line in cand.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("AGNES_API_KEY"):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        return key
            except Exception:
                continue
    return ""


# --------------------------------------------------------------------------
# Agnes completion
# --------------------------------------------------------------------------
BASE = "https://apihub.agnes-ai.com/v1"
MODEL = "agnes-3.0-flash"


def _chat(system, user, temperature=0.6):
    if not requests:
        raise RuntimeError("requests not installed")
    key = _read_key()
    if not key:
        raise RuntimeError("no AGNES_API_KEY")
    last = None
    for attempt in range(3):
        try:
            resp = requests.post(
                BASE + "/chat/completions",
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def summarize_items(items, cap=20):
    """Return a list of dicts: {rank, title, url, source, blurb}."""
    if not items:
        return []
    items = items[:cap]
    # Build a compact English digest for the model.
    lines = []
    for i, it in enumerate(items, 1):
        t = it["title"].replace("|", "/")
        lines.append(
            "%d | %s | score=%d | url=%s"
            % (i, t[:160], it["score"], it["url"])
        )
    digest = "\n".join(lines)
    system = (
        "You write Chinese summaries for a daily AI-tool newsletter. "
        "For each numbered item, output one line in EXACT format:\n"
        "RANK|TITLE(zh)|BLURB(zh,<=120 chars, concrete, why it matters for the reader)"
    )
    user = (
        "Translate and sharpen these items into Chinese. Keep titles short. "
        "Each blurb must say what it does and who it helps. Do not invent facts.\n\n"
        + digest
    )
    try:
        raw = _chat(system, user)
    except Exception as e:
        sys.stderr.write("llm failed, using fallback: %s\n" % e)
        return _fallback(items)
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        try:
            rank = int(parts[0].strip())
        except Exception:
            rank = len(out) + 1
        title = parts[1].strip()
        blurb = "|".join(parts[2:]).strip()
        if rank - 1 < len(items):
            it = items[rank - 1]
            out.append(
                {
                    "rank": rank,
                    "title": title or it["title"],
                    "url": it["url"],
                    "source": it["source"],
                    "blurb": blurb,
                }
            )
    return out


def _fallback(items):
    out = []
    for i, it in enumerate(items[:20], 1):
        out.append(
            {
                "rank": i,
                "title": it["title"],
                "url": it["url"],
                "source": it["source"],
                "blurb": "[源] %s | 热度 %d. 详见原文链接。" % (it["source"], it["score"]),
            }
        )
    return out


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------
def render_markdown(rows, generated_ts):
    date = time.strftime("%Y-%m-%d", time.localtime(generated_ts))
    head = "# 海外 AI 工具情报日报 - " + date + "\n\n"
    head += "每日整理海外最新 AI 工具与开发动态，中文化要点，帮助你快速跟上前沿。\n\n"
    parts = [head]
    for r in rows:
        tag = {"HN": "HN", "ProductHunt": "ProductHunt", "GitHub": "GitHub"}.get(r["source"], r["source"])
        parts.append("## %d. %s\n\n- 来源: %s\n- 链接: %s\n- %s\n" % (r["rank"], r["title"], tag, r["url"], r["blurb"]))
    return "\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(DATA / "raw.json"))
    ap.add_argument("--out", default=str(OUT / "daily.md"))
    ap.add_argument("--items", type=int, default=20)
    args = ap.parse_args()
    data = load_raw(args.raw)
    rows = summarize_items(data.get("items", []), args.items)
    OUT.mkdir(parents=True, exist_ok=True)
    body = render_markdown(rows, data.get("generated_ts", time.time()))
    Path(args.out).write_text(body, encoding="utf-8")
    sys.stderr.write("wrote %d rows -> %s\n" % (len(rows), args.out))
    return rows


if __name__ == "__main__":
    main()
