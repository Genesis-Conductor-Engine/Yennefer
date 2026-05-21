# Secret Scanning Audit — Genesis-Conductor-Engine/Yennefer

Walk this after rotating keys (`scripts/rotate_secrets.cjs`) and planning the history
scrub (`scripts/scrub_history.sh`). Rotation comes first: a leaked key is compromised the
moment it hits a public repo, and history rewriting does not un-leak it.

## 1. Enable / confirm secret scanning
- [ ] Repo settings: `https://github.com/Genesis-Conductor-Engine/Yennefer/settings/security_analysis`
- [ ] Confirm **Secret scanning** = Enabled.
- [ ] Confirm **Push protection** = Enabled (blocks future commits containing known secret formats).

## 2. Triage existing alerts
- [ ] Alerts list: `https://github.com/Genesis-Conductor-Engine/Yennefer/security/secret-scanning`
- [ ] For each alert, confirm the credential was **rotated/revoked** before marking resolved.
- [ ] Specifically expect alerts for:
  - [ ] Etherscan API key (previously in `hardhat.config.cjs`)
  - [ ] Alchemy Base RPC key (previously in `hardhat.config.cjs` URL)
- [ ] Mark each `Revoked` only after the provider dashboard confirms the old key is dead.

## 3. Provider-side revocation (do these regardless of GitHub alerts)
- [ ] Etherscan: `https://etherscan.io/myapikey` — delete the old key, confirm new key works.
- [ ] Alchemy: `https://dashboard.alchemy.com/` → app → API Keys → roll/delete old key.

## 4. Verify the working tree is clean
- [ ] `git grep -nE 'F5TARHYEZ|g\.alchemy\.com/v2/[A-Za-z0-9_-]{20,}'` returns nothing on `main`.
- [ ] `hardhat.config.cjs` reads `process.env.ETHERSCAN_API_KEY` / `process.env.BASE_MAINNET_RPC`.
- [ ] `.env`, `.env.local`, `.env.production` are gitignored (confirm in `.gitignore`).

## 5. History scrub (only after rotation)
- [ ] Populate `scripts/leaked_keys.txt` with the literal leaked values.
- [ ] Run `bash scripts/scrub_history.sh` (dry-run) and review the match count.
- [ ] Execute the printed destructive sequence **manually**, back up first.
- [ ] Notify collaborators to re-clone (rewritten history invalidates old clones).

## 6. Close-out
- [ ] All secret-scanning alerts resolved as `Revoked`.
- [ ] New keys live only in `~/.yennefer/.env.local` (0600) and CI secret store — never in source.
