# Gnosis Safe Setup — EOC treasurySink (Option B)

Create a 2-of-3 Gnosis Safe on **Base** to serve as the sweep destination and the
`treasurySink` for `EulersIdentitySynthesis`. This doc is for Igor to execute; no
script here deploys or signs anything.

## 1. Create the Safe (app.safe.global)
1. Open `https://app.safe.global` → connect your **Ledger** → select **Base** network.
2. **Create new Safe** → name it (e.g. `EOC-treasury`).
3. **Signers / threshold** — default **2-of-3**:
   - Signer 1: **Ledger** (primary hardware).
   - Signer 2: **second hardware wallet** (backup — e.g. a second Ledger / Trezor).
   - Signer 3: **social-recovery / cold key** held separately.
   - Threshold: **2** (no single device can move funds).
4. **Fund the deployer** with ≥ **0.005 ETH** on Base for the deployment tx.
5. Review the deployment transaction on the Ledger screen (verify network = Base,
   signers, threshold) → confirm.

## 2. Capture the address
- After deployment, copy the **checksummed** Safe address.
- Export it for the scripts:
  ```bash
  export SAFE_ADDRESS=0xYourChecksummedSafeAddress
  ```
- Do **not** commit it to source; scripts read it from env only.

## 3. Verify the deployed Safe
Run the verifier (fails closed on any mismatch):
```bash
SAFE_ADDRESS=0x... node scripts/verify_safe.cjs
```
Expected JSONL: `{"step":"verify_safe","ok":true,"address":"0x...","threshold":2,"owners":3,...}`

Cross-check manually:
- **Basescan:** `https://basescan.org/address/<SAFE_ADDRESS>#code` — confirm it's a Safe proxy
  (singleton/master copy) and the bytecode is non-empty.
- **Safe API:** `https://safe-transaction-base.safe.global/api/v1/safes/<SAFE_ADDRESS>/`
  — confirm `threshold`, `owners[]`, and that it resolves (HTTP 200).

## 4. Wire it into the rotation
Once verified, `SAFE_ADDRESS` becomes:
- the `--to` destination for `secure_sweep.cjs`,
- the `TO_ADDRESS` for `lp_unwind.cjs`,
- the `treasurySink` constructor arg for `prep_eis_deploy.cjs`.

The orchestrator (`a2a_orchestrate.cjs`) refuses to proceed past step 1 unless the Safe verifies.
