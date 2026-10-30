"""Generate a daily cover image via Agnes image model.

Usage:
    python -m src.cover                 # read output/daily.md date, save output/cover/<date>.png
    python -m src.cover --prompt "..."  # custom prompt

Skips if today's cover already exists (avoids re-billing on daily runs).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
COVER = OUT / "cover"
BASE = "https://apihub.agnes-ai.com/v1"
MODEL = "agnes-image-2.1-flash"
UA = "ai-daily"


def _read_key():
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
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                continue
    return ""


def default_prompt():
    return (
        "Wide 16:9 tech banner, glowing cyan and blue neural network nodes "
        "connected by thin lines over a deep navy gradient, subtle abstract "
        "grid, clean flat vector style, no text, high contrast, modern AI feel"
    )


def get_date():
    md = OUT / "daily.md"
    if md.exists():
        import re
        m = re.search(r"(\d{4}-\d{2}-\d{2})", md.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return time.strftime("%Y-%m-%d")


def generate(prompt, out_path):
    if not requests:
        raise RuntimeError("requests not installed")
    key = _read_key()
    if not key:
        raise RuntimeError("no AGNES_API_KEY")
    body = {
        "model": MODEL,
        "prompt": prompt,
        "n": 1,
    }
    resp = requests.post(
        BASE + "/images/generations",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": UA},
        json=body,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    d = data["data"][0]
    if d.get("b64_json"):
        img = base64.b64decode(d["b64_json"])
        out_path.write_bytes(img)
    elif d.get("url"):
        r = requests.get(d["url"], timeout=120)
        r.raise_for_status()
        out_path.write_bytes(r.content)
    else:
        raise RuntimeError("no image in response")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    d = get_date()
    COVER.mkdir(parents=True, exist_ok=True)
    target = Path(args.out) if args.out else COVER / ("%s.png" % d)
    if target.exists():
        sys.stderr.write("cover exists, skip: %s\n" % target)
        return target
    prompt = args.prompt or default_prompt()
    try:
        generate(prompt, target)
        sys.stderr.write("cover saved: %s\n" % target)
        return target
    except Exception as e:
        sys.stderr.write("cover FAILED (proceed without): %s\n" % e)
        return None


if __name__ == "__main__":
    main()
