#!/usr/bin/env python3
"""Writes data/releases.json and static/releases/v1.json from the published releases of Sunlit Earth.

data/releases.json holds every stable release, newest first, for the download section and "What's
new". static/releases/v1.json is the update feed the app reads to learn that a newer version exists.
Refuses to write either when the releases would give the app something it must not trust.
"""
import argparse
import json
import math
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_URL = "https://api.github.com/repos/sunlit-earth/sunlit-earth/releases?per_page=100"
REPO_URL = "https://github.com/sunlit-earth/sunlit-earth/releases/"
NOTES_PREFIX = REPO_URL
ASSET_PREFIX = REPO_URL + "download/"
MAX_FEED_RELEASES = 20
ARCHIVES = [
    "windows-x86_64",
    "linux-x86_64",
    "linux-aarch64",
    "macos-aarch64-app",
    "macos-x86_64-app",
    "macos-aarch64-terminal",
    "macos-x86_64-terminal",
]
MONTHS = [
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
]
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
ARCHIVE_SUFFIX = re.compile(r"\.(zip|tar\.gz)$")


class Refusal(Exception):
    pass


def fetch_api_releases():
    token = os.environ.get("GH_TOKEN", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sunlit-earth-website",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(API_URL, headers=headers), timeout=60) as response:
        return json.load(response)


def size_text(size):
    tenths = size / 1e5
    rounded = math.floor(tenths)
    if tenths - rounded >= 0.5:
        rounded += 1
    return f"{rounded // 10}.{rounded % 10} MB"


def site_release(api_release):
    version = api_release["tag_name"].removeprefix("v")
    date = api_release["published_at"][:10]
    year, month, day = (int(part) for part in date.split("-"))
    prefix = f"sunlit-earth-{version}-"
    files = {}
    for asset in api_release["assets"]:
        name = asset["name"]
        if not name.startswith(prefix):
            continue
        key = ARCHIVE_SUFFIX.sub("", name.removeprefix(prefix), count=1)
        size = asset.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise Refusal(f"{version}: {key} has no size in bytes")
        files[key] = {"name": name, "url": asset["browser_download_url"], "size": size_text(size), "bytes": size}
    return {
        "version": version,
        "date": date,
        "date_text": f"{MONTHS[month - 1]} {day}, {year}",
        "url": api_release["html_url"],
        "files": files,
    }


def site_releases(api_releases):
    stable = [r for r in api_releases if not (r["draft"] or r["prerelease"])]
    newest_first = reversed(sorted(stable, key=lambda r: r["published_at"]))
    return [site_release(r) for r in newest_first]


def highlights_by_version(changes):
    found = {}
    for entry in changes.get("release", []):
        texts = [c["text"].strip() for c in entry.get("changes", []) if c.get("text", "").strip()]
        found[entry["version"]] = texts
    return found


def feed_entry(release, highlights):
    version = release["version"]
    if not VERSION.fullmatch(version):
        raise Refusal(f"version {version!r} is not X.Y.Z")
    date = release["date"]
    if not DATE.fullmatch(date):
        raise Refusal(f"{version}: date {date!r} is not YYYY-MM-DD")
    notes = release["url"]
    if not notes.startswith(NOTES_PREFIX):
        raise Refusal(f"{version}: release page {notes!r} does not start with {NOTES_PREFIX}")

    assets = {}
    for key, file in sorted(release["files"].items()):
        url = file["url"]
        if not url.startswith(ASSET_PREFIX):
            raise Refusal(f"{version}: {key} URL {url!r} does not start with {ASSET_PREFIX}")
        assets[key] = {"url": url, "size": file["bytes"]}

    entry = {"version": version, "date": date, "notes": notes}
    texts = highlights.get(version)
    if texts:
        entry["highlights"] = texts
    entry["assets"] = assets
    return entry


def update_feed(releases, changes):
    if not releases:
        raise Refusal("there are no stable releases")
    newest = releases[0]
    missing = [key for key in ARCHIVES if key not in newest["files"]]
    if missing:
        raise Refusal(f"the newest release {newest['version']} lacks: {', '.join(missing)}")
    highlights = highlights_by_version(changes)
    return {"releases": [feed_entry(r, highlights) for r in releases[:MAX_FEED_RELEASES]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--api-response",
        type=Path,
        help="read the GitHub API's list of releases from this file instead of fetching it",
    )
    parser.add_argument("--changes", type=Path, default=ROOT / "changes.toml")
    parser.add_argument("--releases", type=Path, default=ROOT / "data" / "releases.json")
    parser.add_argument("--feed", type=Path, default=ROOT / "static" / "releases" / "v1.json")
    args = parser.parse_args()

    try:
        if args.api_response:
            api_releases = json.loads(args.api_response.read_text(encoding="utf-8"))
        else:
            api_releases = fetch_api_releases()
        changes = tomllib.loads(args.changes.read_text(encoding="utf-8"))
        releases = site_releases(api_releases)
        feed = update_feed(releases, changes)
    except Refusal as error:
        sys.exit(f"write-release-data: refusing to write: {error}")
    except (OSError, ValueError) as error:
        sys.exit(f"write-release-data: {error}")
    except KeyError as error:
        sys.exit(f"write-release-data: a release in the API response lacks {error}")

    args.releases.parent.mkdir(parents=True, exist_ok=True)
    site_data = {"latest": releases[0], "releases": releases}
    args.releases.write_text(json.dumps(site_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="")
    print(f"Wrote {args.releases.name}: latest release {releases[0]['version']}, {len(releases)} releases")

    args.feed.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(feed, separators=(",", ":"), ensure_ascii=False)
    args.feed.write_text(body, encoding="utf-8", newline="")
    print(f"Wrote {args.feed.name}: {len(feed['releases'])} releases, {len(body.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
