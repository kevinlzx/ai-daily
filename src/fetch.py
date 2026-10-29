"""Overseas AI tools intel - data fetcher.

Usage:
    python -m src.fetch              fetch and write data/raw.json
    python -m src.fetch --days 2     lookback window in days (default 2)

Each source is isolated in try/except so one failure never blocks the run.
Unified item shape: {title, url, source, ts, score, summary}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT = 20


def _get(url, **kw):
    kw.setdefault("timeout", TIMEOUT)
    kw.setdefault("headers", {"User-Agent": UA})
    kw.setdefault("allow_redirects", True)
    last = None
    for attempt in range(3):
        try:
            return requests.get(url, **kw)
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def _item(title, url, source, score=0, summary="", ts=None):
    return {
        "title": (title or "").strip(),
        "url": (url or "").strip(),
        "source": source,
        "ts": int(ts or time.time()),
        "score": int(score or 0),
        "summary": (summary or "").strip(),
    }


# --------------------------------------------------------------------------
# Source 1: Hacker News front page (Algolia, stable public API)
# --------------------------------------------------------------------------
def fetch_hn(days=2):
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    url = (
        "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=80"
        "&numericFilters=created_at_i>" + str(since)
    )
    r = _get(url)
    r.raise_for_status()
    out = []
    for h in r.json().get("hits", []):
        pts = h.get("points") or 0
        if pts < 40:
            continue
        link = h.get("url") or ("https://news.ycombinator.com/item?id=" + str(h.get("objectID")))
        out.append(_item(h.get("title"), link, "HN", pts))
    return out


# --------------------------------------------------------------------------
# Source 2: Product Hunt daily RSS feed
# --------------------------------------------------------------------------
def fetch_producthunt(days=2):
    r = _get("https://www.producthunt.com/feed")
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall("a:entry", ns) or list(root)
    cutoff = time.time() - days * 86400
    out = []
    for e in entries:
        title = (e.findtext("a:title", default="", namespaces=ns)).strip()
        link_el = e.find("a:link", ns)
        link = link_el.get("href") if link_el is not None else ""
        content = e.findtext("a:content", default="", namespaces=ns) or ""
        summary = re.sub("<[^>]+>", " ", content)
        summary = re.sub("\\s+", " ", summary).strip()[:280]
        pub = e.findtext("a:updated", default="", namespaces=ns) or e.findtext(
            "a:published", default="", namespaces=ns
        )
        ts = time.time()
        if pub:
            try:
                ts = datetime.fromisoformat(pub.replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
        if ts < cutoff:
            continue
        out.append(_item(title, link, "PH", 200, summary, ts))
    return out


# --------------------------------------------------------------------------
# Source 3: GitHub trending (HTML fallback; ok on many networks, else skipped)
# --------------------------------------------------------------------------
def fetch_github(days=2):
    try:
        r = _get("https://github.com/trending?since=daily")
        r.raise_for_status()
    except Exception:
        return []
    html = r.text
    # Repo rows carry the href inside an <h2 class="h3 lh-condensed"> block.
    # Anchor on the class, then pull owner/name within that block only.
    seen, out = set(), []
    for m in re.finditer(r'<h2 class="[^"]*lh-condensed[^"]*">.*?href="/([^"/]+/[^"/]+)"', html, re.S):
        nm = m.group(1)
        if nm in seen or " " in nm or nm.count("/") != 1:
            continue
        seen.add(nm)
        out.append(_item(nm, "https://github.com/" + nm, "GH", 300))
        if len(out) >= 25:
            break
    return out


# --------------------------------------------------------------------------
# Source 4: Reddit /r/SideProject top-of-day (JSON; skipped when blocked)
# --------------------------------------------------------------------------
def fetch_reddit(days=2):
    try:
        r = _get(
            "https://www.reddit.com/r/SideProject/top.json?t=day&limit=30",
            headers={"User-Agent": "ai-daily/1.0 by hermes"},
        )
        r.raise_for_status()
        posts = r.json()["data"]["children"]
    except Exception:
        return []
    out = []
    for c in posts:
        d = c.get("data", {})
        if d.get("stickied"):
            continue
        out.append(
            _item(
                d.get("title"),
                "https://www.reddit.com" + d.get("permalink", ""),
                "Reddit",
                d.get("score") or 0,
            )
        )
    return out


# --------------------------------------------------------------------------
# Orchestrator + entrypoint
# --------------------------------------------------------------------------
def gather(days=2):
    results = []
    jobs = [("HN", fetch_hn), ("ProductHunt", fetch_producthunt), ("GitHub", fetch_github), ("Reddit", fetch_reddit)]
    for name, fn in jobs:
        try:
            items = fn(days)
            for it in items:
                it["source"] = name
            results.extend(items)
        except Exception as e:
            sys.stderr.write("source %s failed: %s\n" % (name, e))
    # dedupe by url
    seen = set()
    uniq = []
    for it in sorted(results, key=lambda x: -x["score"]):
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        uniq.append(it)
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--out", default=str(DATA / "raw.json"))
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    items = gather(args.days)
    out = {
        "generated_ts": int(time.time()),
        "days": args.days,
        "count": len(items),
        "items": items,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stderr.write("wrote %d items -> %s\n" % (len(items), args.out))
    return items


if __name__ == "__main__":
    main()
