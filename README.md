# sunlit.earth

The website of [Sunlit Earth](https://github.com/sunlit-earth/sunlit-earth): a single page built with [Zola](https://www.getzola.org/) and served by Cloudflare as a Worker with static assets and no script.

A push to `main` deploys it, and so does a `repository_dispatch` of type `release-published`, which the app repository sends when a release is published so the download links follow. Pull requests build the site and run a dry run of the deploy. `workflow_dispatch` redeploys by hand.

## Layout

| Path | What it holds |
|---|---|
| `templates/index.html` | The page |
| `templates/shot.html`, `templates/release.html` | A screenshot with its responsive sizes, a release's notes |
| `templates/icons/` | The OS icons. Apple and Linux are from [Simple Icons](https://simpleicons.org/) 15.0.0, CC0 1.0 |
| `content/_index.md` | The screenshots in the carousel, the app screenshot for each OS, and their captions |
| `changes.toml` | The highlights of each release for "What's new", written by hand |
| `static/images/` | The full-size screenshots. Zola writes the smaller versions to `static/processed_images/` at build time |
| `static/site.css`, `static/site.js` | Styles, OS detection, the copy buttons and the image viewer |
| `scripts/write-release-data.py` | Fetches the releases from the GitHub API and writes `data/releases.json`, the stable releases with their files (size as text and in bytes) for the download section and "What's new", and `static/releases/v1.json`, the update feed, with the highlights from `changes.toml` |

Prereleases and drafts are left out. The script fails if the newest release lacks one of the seven archives, which include every archive the download section links to.

## The update feed

The app checks `https://sunlit.earth/releases/v1.json` for newer versions. It is written at build time by `scripts/write-release-data.py`, which needs Python 3.11 or newer and nothing else, and Zola copies it to the site from `static/releases/`, which git ignores like `data/`. The file holds the 20 newest stable releases, newest first, each with its date, its release page, its highlights as plain text (the emoji of `changes.toml` stay on the page) and its archives with their URL and size in bytes, keyed as in `data/releases.json`, without whitespace between tokens. The `v1` is the format's version: a format an older app could not read gets a new file beside this one, and this one stays served. The format and the rules the app reads it by are in the app repository's `docs/plans/2026-11-22-update-check-plan.md`.

The script checks every release it writes, not only the newest, and refuses to write, failing the build, when a version is not `X.Y.Z`, when a date is not `YYYY-MM-DD`, when a release page does not start with `https://github.com/sunlit-earth/sunlit-earth/releases/` or an archive URL with `https://github.com/sunlit-earth/sunlit-earth/releases/download/`, when an archive has no size in bytes, or when the newest release lacks one of the seven archives. An entry in `changes.toml` for a version that is not published yet is ignored, so the highlights can be added before the release is published.

## Adding a screenshot

Put the WebP in `static/images/` and add an entry with `file` and `caption` to `gallery` in `content/_index.md`, or replace one of the entries under `[extra.app]`.

## After a release

Add the release's highlights to the top of `changes.toml`: a few short entries, one emoji each. Until then, "What's new" shows only the link to its release notes. The same text goes into the update feed, so add them before publishing the draft release: the app lists a release without highlights as a heading alone.

## Preview locally

Needs [Zola](https://www.getzola.org/documentation/getting-started/installation/) 0.23.6, the version the workflow pins, and Python 3.11 or newer (`uv run` finds one). The script asks the GitHub API without a token unless `GH_TOKEN` or `GITHUB_TOKEN` is set, which GitHub allows for a public repository up to 60 times an hour.

```bash
uv run scripts/write-release-data.py
zola serve
```

`npx wrangler@4.148.0 dev` serves the output of `zola build` the way Cloudflare does, the 404 page included.

## Repository secrets

| Secret | Value |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | The account ID, shown in the Cloudflare dashboard on the account's overview page |
| `CLOUDFLARE_API_TOKEN` | An API token with Account, Workers Scripts, Edit and Zone `sunlit.earth`, Workers Routes, Edit |
