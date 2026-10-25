#!/usr/bin/env bash
# Writes data/releases.json, the published stable releases of Sunlit Earth, newest first.
set -euo pipefail

repo=sunlit-earth/sunlit-earth
cd "$(dirname "$0")/.."
mkdir -p data

gh api "repos/$repo/releases?per_page=100" | jq '
  ["January", "February", "March", "April", "May", "June", "July",
   "August", "September", "October", "November", "December"] as $months
  | map(select((.draft or .prerelease) | not))
  | sort_by(.published_at) | reverse
  | map(
      (.tag_name | ltrimstr("v")) as $version
      | (.published_at[0:10] | split("-") | map(tonumber)) as [$y, $m, $d]
      | {
          version: $version,
          date: .published_at[0:10],
          date_text: "\($months[$m - 1]) \($d), \($y)",
          url: .html_url,
          files: ([.assets[]
            | select(.name | startswith("sunlit-earth-\($version)-"))
            | {
                key: (.name | ltrimstr("sunlit-earth-\($version)-") | sub("\\.(zip|tar\\.gz)$"; "")),
                value: {name, url: .browser_download_url, size: (.size / 1e5 | round | "\(. / 10 | floor).\(. % 10) MB")}
              }] | from_entries)
        })
  | {latest: .[0], releases: .}
' > data/releases.json

expected='["windows-x86_64","macos-aarch64-app","macos-x86_64-app","macos-aarch64-terminal","macos-x86_64-terminal","linux-x86_64","linux-aarch64"]'
missing=$(jq -r --argjson e "$expected" '$e - (.latest.files | keys) | join(", ")' data/releases.json)
if [[ -n $missing ]]; then
  echo "The latest release lacks: $missing" >&2
  exit 1
fi
jq -r '"Latest release: \(.latest.version), \(.releases | length) releases"' data/releases.json
