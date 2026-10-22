# sunlit.earth

The website of [Sunlit Earth](https://github.com/sunlit-earth/sunlit-earth), served from `public/` as a Cloudflare Worker with static assets and no script.

A push to `main` deploys it. Pull requests run a dry run, which validates the configuration and deploys nothing.

## Preview locally

```bash
npx wrangler@4.148.0 dev
```

## Repository secrets

| Secret | Value |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | The account ID, shown in the Cloudflare dashboard on the account's overview page |
| `CLOUDFLARE_API_TOKEN` | An API token with Account, Workers Scripts, Edit and Zone `sunlit.earth`, Workers Routes, Edit |
