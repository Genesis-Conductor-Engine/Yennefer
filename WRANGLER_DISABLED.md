# Cloudflare Worker Build Disabled

The Cloudflare Worker build was consistently failing due to environment incompatibilities with the root-level dependencies (specifically `node-gyp-build` for native modules).

As per the user's instructions to prioritize GitHub Pages if Cloudflare Workers are not working, we have:

1. Renamed `wrangler.toml` to `wrangler.disabled.toml` to stop the automatic Cloudflare build checks.
2. Enabled GitHub Pages deployment for the `yennefer-observatory` frontend via `.github/workflows/deploy-pages.yml`.

## Re-enabling the Worker

If you need to restore the Cloudflare Worker functionality:

1. Rename `wrangler.disabled.toml` back to `wrangler.toml`.
2. Ensure the build environment can handle the native module compilation or move the worker code to a separate directory with its own minimal `package.json`.
