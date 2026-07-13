#!/usr/bin/env python3
"""Extract the real backdrop palette (centre, edge, pattern colours) and the Backdrop/
Symbol names from public Telegram NFT gift pages (t.me/nft/<slug>).

The gift page renders its backdrop as an SVG radialGradient with two stops plus a
`giftGradienPatternColor` flood-colour for the tiled symbol. We only read those colours;
no proprietary art is copied. Output is JSON on stdout for pasting into the app catalogue.

Usage:
  python scripts/extract_gift_backdrops.py Ghosted-1 CrystalBall-9406 ...
  python scripts/extract_gift_backdrops.py --from-downloads   # every slug in downloads/media
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

NFT_BASE = "https://t.me/nft/"
UA = {"User-Agent": "Mozilla/5.0"}


def fetch(slug: str) -> str:
    req = urllib.request.Request(NFT_BASE + slug, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def extract(slug: str) -> dict | None:
    html = fetch(slug)
    stops = re.findall(r'<stop\s+stop-color="(#[0-9a-fA-F]{6})"', html)
    pattern = re.search(r'giftGradienPatternColor"\s+flood-color="(#[0-9a-fA-F]{6})"', html)
    desc = re.search(r'og:description"\s+content="([^"]+)"', html)
    names = {}
    if desc:
        for line in desc.group(1).split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                names[key.strip().lower()] = value.strip()
    if len(stops) < 2:
        return None
    return {
        "slug": slug,
        "backdrop": names.get("backdrop"),
        "symbol": names.get("symbol"),
        "model": names.get("model"),
        "center": stops[0],
        "edge": stops[1],
        "pattern": pattern.group(1) if pattern else stops[1],
    }


def slugs_from_downloads() -> list[str]:
    media = Path("downloads/media")
    return sorted(
        p.stem.removeprefix("nft_") for p in media.glob("nft_*.tgs")
    )


def main() -> None:
    args = sys.argv[1:]
    slugs = slugs_from_downloads() if (not args or args == ["--from-downloads"]) else args
    out = []
    for slug in slugs:
        try:
            data = extract(slug)
        except Exception as exc:  # noqa: BLE001
            print(f"[-] {slug}: {exc}", file=sys.stderr)
            continue
        if data:
            out.append(data)
            print(f"[+] {slug}: {data['backdrop']} / {data['symbol']} "
                  f"{data['center']}->{data['edge']} pat {data['pattern']}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
