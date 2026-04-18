#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BOT_API_BASE = "https://api.telegram.org"
NFT_BASE_URL = "https://t.me/nft/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Telegram gift/NFT media into downloads/."
    )
    parser.add_argument(
        "--bot-token",
        default=os.getenv("BOT_TOKEN", ""),
        help="Telegram bot token. Defaults to BOT_TOKEN env.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="Fetch gifts owned by this Telegram user via getUserGifts.",
    )
    parser.add_argument(
        "--chat-id",
        help="Fetch gifts owned by this chat/channel via getChatGifts.",
    )
    parser.add_argument(
        "--custom-emoji-id",
        action="append",
        default=[],
        help="Download media for this custom emoji id. Can be passed multiple times.",
    )
    parser.add_argument(
        "--custom-emoji-file",
        help="Text file with one custom emoji id per line.",
    )
    parser.add_argument(
        "--output-dir",
        default="downloads",
        help="Where to write manifest JSON and media files.",
    )
    parser.add_argument(
        "--gift-number",
        type=int,
        action="append",
        default=[],
        help="Unique gift number to filter by within fetched user/chat gifts.",
    )
    parser.add_argument(
        "--available-gifts",
        action="store_true",
        help="Download media for gifts returned by getAvailableGifts.",
    )
    parser.add_argument(
        "--nft-url",
        action="append",
        default=[],
        help="Public https://t.me/nft/... URL or slug to download directly. Can be passed multiple times.",
    )
    return parser.parse_args()


def bot_api(method: str, token: str, params: dict[str, Any] | None = None) -> Any:
    query = urllib.parse.urlencode(params or {}, doseq=True)
    url = f"{BOT_API_BASE}/bot{token}/{method}"
    if query:
        url = f"{url}?{query}"

    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not payload.get("ok"):
        description = payload.get("description", f"Telegram API call failed: {method}")
        raise RuntimeError(description)

    return payload["result"]


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def extract_nft_slug(value: str) -> str:
    value = value.strip()
    if value.startswith("https://") or value.startswith("http://"):
        parsed = urllib.parse.urlparse(value)
        return parsed.path.rstrip("/").split("/")[-1]
    return value.strip().split("/")[-1]


def search_html(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return html.unescape(match.group(1))


def fetch_public_nft(slug_or_url: str) -> dict[str, Any]:
    slug = extract_nft_slug(slug_or_url)
    url = f"{NFT_BASE_URL}{slug}"
    html_text = fetch_text(url)
    tgs_url = search_html(
        r'<source\s+type="application/x-tgsticker"\s+srcset="([^"]+)"',
        html_text,
    )
    if not tgs_url:
        raise RuntimeError(f"No TGS source found on public NFT page: {slug}")

    return {
        "slug": slug,
        "url": url,
        "title": search_html(
            r'<meta\s+property="og:title"\s+content="([^"]+)"', html_text
        ),
        "description": search_html(
            r'<meta\s+property="og:description"\s+content="([^"]+)"', html_text
        ),
        "image_url": search_html(
            r'<meta\s+property="og:image"\s+content="([^"]+)"', html_text
        ),
        "tgs_url": tgs_url,
    }


def collect_custom_emoji_ids(node: Any) -> set[str]:
    found: set[str] = set()
    stack = [node]

    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key.endswith("custom_emoji_id") and isinstance(value, str) and value:
                    found.add(value)
                elif isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            for value in current:
                if isinstance(value, (dict, list)):
                    stack.append(value)

    return found


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def load_custom_ids_from_file(file_path: str | None) -> list[str]:
    if not file_path:
        return []

    lines = Path(file_path).read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def build_gift_label(owned_gift: dict[str, Any], index: int) -> str:
    gift = owned_gift.get("gift", {})
    base_name = (
        gift.get("base_name") or gift.get("name") or gift.get("gift_id") or "gift"
    )
    unique_name = gift.get("name")
    number = gift.get("number")

    parts = [f"gift_{index:03d}", str(base_name)]
    if unique_name and unique_name != base_name:
        parts.append(str(unique_name))
    if number is not None:
        parts.append(f"#{number}")

    return " ".join(parts)


def fetch_owned_gifts(
    token: str, *, user_id: int | None, chat_id: str | None
) -> list[dict[str, Any]]:
    if user_id is None and chat_id is None:
        return []

    method = "getUserGifts" if user_id is not None else "getChatGifts"
    target_key = "user_id" if user_id is not None else "chat_id"
    target_value = user_id if user_id is not None else chat_id
    gifts: list[dict[str, Any]] = []
    offset = ""

    while True:
        result = bot_api(
            method,
            token,
            {
                target_key: target_value,
                "limit": 100,
                "offset": offset,
                "exclude_unique": "false",
            },
        )
        gifts.extend(result.get("gifts", []))
        offset = result.get("next_offset") or ""
        if not offset:
            return gifts


def fetch_available_gifts(token: str) -> list[dict[str, Any]]:
    result = bot_api("getAvailableGifts", token)
    if isinstance(result, dict):
        gifts = result.get("gifts")
        if isinstance(gifts, list):
            return gifts
    if isinstance(result, list):
        return result
    return []


def filter_owned_gifts_by_number(
    owned_gifts: list[dict[str, Any]], requested_numbers: list[int]
) -> list[dict[str, Any]]:
    if not requested_numbers:
        return owned_gifts

    requested = set(requested_numbers)
    return [
        gift for gift in owned_gifts if gift.get("gift", {}).get("number") in requested
    ]


def collect_sticker_entries(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    stack = [node]

    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            file_id = current.get("file_id")
            if (
                isinstance(file_id, str)
                and isinstance(current.get("width"), int)
                and isinstance(current.get("height"), int)
                and (
                    "type" in current
                    or "is_animated" in current
                    or "is_video" in current
                    or "emoji" in current
                )
            ):
                key = (file_id, str(current.get("custom_emoji_id") or ""))
                if key not in seen:
                    seen.add(key)
                    found.append(current)

            for value in current.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            for value in current:
                if isinstance(value, (dict, list)):
                    stack.append(value)

    return found


def resolve_stickers(token: str, custom_emoji_ids: list[str]) -> list[dict[str, Any]]:
    stickers: list[dict[str, Any]] = []
    for batch in chunked(custom_emoji_ids, 200):
        stickers.extend(
            bot_api(
                "getCustomEmojiStickers",
                token,
                {"custom_emoji_ids": json.dumps(batch, ensure_ascii=False)},
            )
        )
    return stickers


def infer_extension(sticker: dict[str, Any], file_path: str) -> str:
    suffix = Path(file_path).suffix
    if suffix:
        return suffix
    if sticker.get("is_animated"):
        return ".tgs"
    if sticker.get("is_video"):
        return ".webm"
    return ".webp"


def download_file(token: str, file_path: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BOT_API_BASE}/file/bot{token}/{file_path}"
    with urllib.request.urlopen(url, timeout=60) as response:
        destination.write_bytes(response.read())


def download_url(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def download_sticker_file(
    token: str,
    media_dir: Path,
    sticker: dict[str, Any],
    label: str,
) -> dict[str, Any] | None:
    file_id = sticker.get("file_id")
    if not file_id:
        return None

    try:
        file_info = bot_api("getFile", token, {"file_id": file_id})
    except Exception as exc:
        print(f"Skipping {label}: getFile failed: {exc}", file=sys.stderr)
        return None

    file_path = file_info.get("file_path")
    if not file_path:
        print(f"Skipping {label}: Telegram returned no file_path", file=sys.stderr)
        return None

    extension = infer_extension(sticker, file_path)
    custom_id = sticker.get("custom_emoji_id")
    stem = f"custom_emoji_{custom_id}" if custom_id else f"file_{file_id}"
    destination = media_dir / f"{stem}{extension}"

    try:
        download_file(token, file_path, destination)
    except Exception as exc:
        print(f"Skipping {label}: download failed: {exc}", file=sys.stderr)
        return None

    print(f"Saved {destination}")
    return {
        "custom_emoji_id": custom_id,
        "file_id": file_id,
        "file_path": file_path,
        "saved_to": destination.as_posix(),
        "is_animated": bool(sticker.get("is_animated")),
        "is_video": bool(sticker.get("is_video")),
        "sources": [label],
    }


def download_public_nft_file(
    media_dir: Path,
    nft: dict[str, Any],
) -> dict[str, Any] | None:
    slug = nft["slug"]
    destination = media_dir / f"nft_{slug}.tgs"
    try:
        download_url(nft["tgs_url"], destination)
    except Exception as exc:
        print(f"Skipping {slug}: public TGS download failed: {exc}", file=sys.stderr)
        return None

    print(f"Saved {destination}")
    return {
        "custom_emoji_id": None,
        "file_id": None,
        "file_path": nft["tgs_url"],
        "saved_to": destination.as_posix(),
        "is_animated": True,
        "is_video": False,
        "sources": [f"public_nft:{slug}"],
        "slug": slug,
        "title": nft.get("title"),
    }


def write_json(file_path: Path, data: Any) -> None:
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    token = args.bot_token.strip()
    needs_bot_token = bool(
        args.user_id is not None
        or args.chat_id is not None
        or args.custom_emoji_id
        or args.custom_emoji_file
        or args.gift_number
        or args.available_gifts
    )
    if needs_bot_token and (not token or token == "INVALID_TOKEN"):
        print(
            "BOT_TOKEN is required. Pass --bot-token or export BOT_TOKEN.",
            file=sys.stderr,
        )
        return 1

    manual_ids = list(args.custom_emoji_id)
    manual_ids.extend(load_custom_ids_from_file(args.custom_emoji_file))

    output_dir = Path(args.output_dir)
    media_dir = output_dir / "media"
    output_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    if args.gift_number and args.user_id is None and args.chat_id is None:
        print(
            "--gift-number requires --user-id or --chat-id because Telegram can't resolve a gift globally by number alone.",
            file=sys.stderr,
        )
        return 1

    owned_gifts: list[dict[str, Any]] = []
    if args.user_id is not None or args.chat_id is not None:
        try:
            owned_gifts = fetch_owned_gifts(
                token, user_id=args.user_id, chat_id=args.chat_id
            )
        except Exception as exc:
            print(f"Failed to fetch gifts: {exc}", file=sys.stderr)
            return 1

    owned_gifts = filter_owned_gifts_by_number(owned_gifts, args.gift_number)
    if args.gift_number and not owned_gifts:
        print(
            f"No gifts matched requested number(s): {', '.join(str(x) for x in args.gift_number)}",
            file=sys.stderr,
        )
        return 1

    available_gifts: list[dict[str, Any]] = []
    if args.available_gifts:
        try:
            available_gifts = fetch_available_gifts(token)
        except Exception as exc:
            print(f"Failed to fetch available gifts: {exc}", file=sys.stderr)
            return 1

    public_nfts: list[dict[str, Any]] = []
    for item in args.nft_url:
        try:
            public_nfts.append(fetch_public_nft(item))
        except Exception as exc:
            print(f"Failed to fetch public NFT page {item}: {exc}", file=sys.stderr)
            return 1

    sources_by_custom_id: dict[str, list[str]] = {}
    for index, owned_gift in enumerate(owned_gifts, start=1):
        label = build_gift_label(owned_gift, index)
        for custom_id in sorted(collect_custom_emoji_ids(owned_gift.get("gift", {}))):
            sources_by_custom_id.setdefault(custom_id, []).append(label)

    for custom_id in manual_ids:
        sources_by_custom_id.setdefault(custom_id, []).append("manual")

    custom_ids = sorted(sources_by_custom_id)
    if not custom_ids and not available_gifts and not public_nfts:
        print(
            "No assets found. Pass --user-id/--chat-id, --custom-emoji-id, --available-gifts, or --nft-url.",
            file=sys.stderr,
        )
        return 1

    stickers: list[dict[str, Any]] = []
    if custom_ids:
        try:
            stickers = resolve_stickers(token, custom_ids)
        except Exception as exc:
            print(f"Failed to resolve custom emoji stickers: {exc}", file=sys.stderr)
            return 1

    sticker_files: list[dict[str, Any]] = []
    for sticker in stickers:
        custom_id = sticker.get("custom_emoji_id")
        file_id = sticker.get("file_id")
        if not custom_id or not file_id:
            continue

        try:
            file_info = bot_api("getFile", token, {"file_id": file_id})
        except Exception as exc:
            print(f"Skipping {custom_id}: getFile failed: {exc}", file=sys.stderr)
            continue

        file_path = file_info.get("file_path")
        if not file_path:
            print(
                f"Skipping {custom_id}: Telegram returned no file_path", file=sys.stderr
            )
            continue

        extension = infer_extension(sticker, file_path)
        destination = media_dir / f"custom_emoji_{custom_id}{extension}"
        try:
            download_file(token, file_path, destination)
        except Exception as exc:
            print(f"Skipping {custom_id}: download failed: {exc}", file=sys.stderr)
            continue

        sticker_files.append(
            {
                "custom_emoji_id": custom_id,
                "file_id": file_id,
                "file_path": file_path,
                "saved_to": destination.as_posix(),
                "is_animated": bool(sticker.get("is_animated")),
                "is_video": bool(sticker.get("is_video")),
                "sources": sources_by_custom_id.get(custom_id, []),
            }
        )
        print(f"Saved {destination}")

    for index, gift in enumerate(available_gifts, start=1):
        label = f"available_gift_{index:03d}"
        for sticker in collect_sticker_entries(gift):
            record = download_sticker_file(token, media_dir, sticker, label)
            if record is not None:
                sticker_files.append(record)

    for nft in public_nfts:
        record = download_public_nft_file(media_dir, nft)
        if record is not None:
            sticker_files.append(record)

    manifest = {
        "target": {
            "user_id": args.user_id,
            "chat_id": args.chat_id,
            "gift_numbers": args.gift_number,
            "available_gifts": args.available_gifts,
            "nft_urls": args.nft_url,
        },
        "owned_gifts_count": len(owned_gifts),
        "available_gifts_count": len(available_gifts),
        "public_nfts_count": len(public_nfts),
        "custom_emoji_ids": custom_ids,
        "downloaded_files": sticker_files,
    }

    write_json(output_dir / "gift_manifest.json", manifest)
    if owned_gifts:
        write_json(output_dir / "owned_gifts.json", owned_gifts)
    if available_gifts:
        write_json(output_dir / "available_gifts.json", available_gifts)
    if public_nfts:
        write_json(output_dir / "public_nfts.json", public_nfts)
    write_json(output_dir / "resolved_stickers.json", stickers)

    print(f"Downloaded {len(sticker_files)} file(s) into {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
