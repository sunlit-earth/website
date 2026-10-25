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
| `scripts/fetch-releases.sh` | Writes `data/releases.json`, the stable releases with their files and notes, from the GitHub API |

Prereleases are left out. The script fails if the newest release lacks one of the archives the download section links to.

## Adding a screenshot

Put the WebP in `static/images/` and add an entry with `file` and `caption` to `gallery` in `content/_index.md`, or replace one of the entries under `[extra.app]`.

## After a release

Add the release's highlights to the top of `changes.toml`: a few short entries, one emoji each. Until then, "What's new" shows only the link to its release notes.

## Preview locally

Needs [Zola](https://www.getzola.org/documentation/getting-started/installation/) 0.23.6, the version the workflow pins, plus `gh` (signed in) and `jq`.

```bash
scripts/fetch-releases.sh
zola serve
```

`npx wrangler@4.148.0 dev` serves the output of `zola build` the way Cloudflare does, the 404 page included.

## Repository secrets

| Secret | Value |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | The account ID, shown in the Cloudflare dashboard on the account's overview page |
| `CLOUDFLARE_API_TOKEN` | An API token with Account, Workers Scripts, Edit and Zone `sunlit.earth`, Workers Routes, Edit |
