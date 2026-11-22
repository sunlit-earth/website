#!/usr/bin/env python3
"""Writes static/releases/v1.json, the feed the app reads to learn that a newer version exists.

Reads data/releases.json (scripts/fetch-releases.sh) and changes.toml. Refuses to write when the
data would give the app something it must not trust.
"""
import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/sunlit-earth/sunlit-earth/releases/"
NOTES_PREFIX = REPO_URL
ASSET_PREFIX = REPO_URL + "download/"
MAX_RELEASES = 20
ARCHIVES = [
    "windows-x86_64",
    "linux-x86_64",
    "linux-aarch64",
    "macos-aarch64-app",
    "macos-x86_64-app",
    "macos-aarch64-terminal",
    "macos-x86_64-terminal",
]
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class Refusal(Exception):
    pass


def highlights_by_version(changes):
    found = {}
    for entry in changes.get("release", []):
        texts = [c["text"].strip() for c in entry.get("changes", []) if c.get("text", "").strip()]
        found[entry["version"]] = texts
    return found


def build_entry(release, highlights):
    version = release.get("version", "")
    if not VERSION.fullmatch(version):
        raise Refusal(f"version {version!r} is not X.Y.Z")
    date = release.get("date", "")
    if not DATE.fullmatch(date):
        raise Refusal(f"{version}: date {date!r} is not YYYY-MM-DD")
    notes = release.get("url", "")
    if not notes.startswith(NOTES_PREFIX):
        raise Refusal(f"{version}: release page {notes!r} does not start with {NOTES_PREFIX}")

    assets = {}
    for key, file in sorted(release.get("files", {}).items()):
        url = file.get("url", "")
        if not url.startswith(ASSET_PREFIX):
            raise Refusal(f"{version}: {key} URL {url!r} does not start with {ASSET_PREFIX}")
        size = file.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise Refusal(f"{version}: {key} has no size in bytes; run scripts/fetch-releases.sh again")
        assets[key] = {"url": url, "size": size}

    entry = {"version": version, "date": date, "notes": notes}
    texts = highlights.get(version)
    if texts:
        entry["highlights"] = texts
    entry["assets"] = assets
    return entry


def build_feed(data, changes):
    releases = data.get("releases", [])
    if not releases:
        raise Refusal("data has no releases")
    newest = releases[0]
    missing = [key for key in ARCHIVES if key not in newest.get("files", {})]
    if missing:
        raise Refusal(f"the newest release {newest.get('version')} lacks: {', '.join(missing)}")
    highlights = highlights_by_version(changes)
    return {"releases": [build_entry(r, highlights) for r in releases[:MAX_RELEASES]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--releases", type=Path, default=ROOT / "data" / "releases.json")
    parser.add_argument("--changes", type=Path, default=ROOT / "changes.toml")
    parser.add_argument("--out", type=Path, default=ROOT / "static" / "releases" / "v1.json")
    args = parser.parse_args()

    try:
        data = json.loads(args.releases.read_text(encoding="utf-8"))
        changes = tomllib.loads(args.changes.read_text(encoding="utf-8"))
        feed = build_feed(data, changes)
    except Refusal as error:
        sys.exit(f"write-update-feed: refusing to write {args.out}: {error}")
    except (OSError, ValueError) as error:
        sys.exit(f"write-update-feed: {error}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(feed, separators=(",", ":"), ensure_ascii=False)
    args.out.write_text(body, encoding="utf-8", newline="")
    print(f"Wrote {args.out.name}: {len(feed['releases'])} releases, {len(body.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
