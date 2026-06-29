# Notion Telemetry Seed Setup Guide

## Quick Start

### 1. Get Notion Integration Token

The telemetry seed scripts require a Notion integration token with access to the DiamondNode Telemetry database.

**Option A: From Cloudflare Worker Secrets (Recommended)**

If you've already configured the notion-bridge worker:

```bash
cd ~/genesis/notion-bridge
npx wrangler secret list
# Note: The actual token value is not displayed for security
```

To retrieve the token, check your Notion integration settings:
1. Go to https://www.notion.so/my-integrations
2. Find "DiamondNode Telemetry Integration"
3. Copy the "Internal Integration Token"

**Option B: Create New Integration**

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name: "DiamondNode Telemetry Seed"
4. Select workspace
5. Copy the token (starts with `secret_`)

6. Share database with integration:
   - Open database: https://notion.so/9a32dcb5-00b6-40d7-bd86-43d93965fa82
   - Click "..." → "Add connections"
   - Select "DiamondNode Telemetry Seed"

### 2. Run Seed Script

**Method 1: Environment Variable (Recommended)**

```bash
cd ~/diamondnode-unified-inference
source yennefer_venv/bin/activate
export NOTION_TOKEN="secret_your_token_here"
python3 scripts/seed_notion_telemetry.py
```

**Method 2: Direct Argument**

```bash
cd ~/diamondnode-unified-inference
source yennefer_venv/bin/activate
python3 scripts/seed_notion_telemetry.py --token "secret_your_token_here"
```

**Method 3: Use load-env.sh (if configured)**

```bash
cd ~/diamondnode-unified-inference
source ../load-env.sh  # Loads from ~/.env if NOTION_TOKEN is set
source yennefer_venv/bin/activate
python3 scripts/seed_notion_telemetry.py
```

### 3. Verify Seed Data

```bash
cd ~/diamondnode-unified-inference
source yennefer_venv/bin/activate
export NOTION_TOKEN="secret_your_token_here"
python3 scripts/verify_notion_seed.py
```

## Expected Output

### Seed Script Success

```
🌟 DiamondNode Notion Telemetry Seed
==================================================
Database ID: 9a32dcb5-00b6-40d7-bd86-43d93965fa82
Envelope Version: 0.3.0
Samples to create: 3

Creating Row 1: η=0.42, ε=0.68, status=RUNNING... ✓ a1b2c3d4...
Creating Row 2: η=0.78, ε=0.68, status=YIELDING... ✓ e5f6g7h8...
Creating Row 3: η=0.61, ε=0.73, status=YIELDING... ✓ i9j0k1l2...

==================================================
✅ 3 telemetry rows seeded successfully
Envelope version: 0.3.0
Live run verified: 3 rows

Key demonstrations:
  • Dynamic η_thermo: 0.42 → 0.78 → 0.61
  • Hysteresis hold: Row 2 (ε=0.68 held despite η spike)
  • YIELDING status: Rows 2 & 3 (CUDA-Q bus coordination)
  • Sanitization: CLEAN (2 rows), SANITIZED (1 row)
  • Crystalline scores: 0.89, 0.91, 0.87 (all ≥ 0.85)
```

### Verification Script Success

```
🔍 Notion Telemetry Seed Verification
================================================================================
Found 3 rows in database

┌─────────────────────┬──────────┬──────┬──────────┬────────┬──────────┬───────┬──────────┐
│ Timestamp           │ η_thermo │ ε    │ Status   │ VRAM%  │ Crystal  │ Live✓ │ Sanit    │
├─────────────────────┼──────────┼──────┼──────────┼────────┼──────────┼───────┼──────────┤
│ 2026-05-13T20:00:00 │ 0.42     │ 0.68 │ RUNNING  │ 0.38   │ 0.89     │ ✓     │ CLEAN    │
│ 2026-05-13T21:00:00 │ 0.78     │ 0.68 │ YIELDING │ 0.43   │ 0.91     │ ✓     │ CLEAN    │
│ 2026-05-13T22:00:00 │ 0.61     │ 0.73 │ YIELDING │ 0.44   │ 0.87     │ ✓     │ SANITIZED│
└─────────────────────┴──────────┴──────┴──────────┴────────┴──────────┴───────┴──────────┘

Validation Results:
────────────────────────────────────────────────────────────────────────────────
  ✅ Database accessible: True
  ✅ Minimum 3 rows exist: True
  ✅ All rows have Live_Run_Verified: True
  ✅ Envelope version: 0.3.0

Key Demonstrations Found:
────────────────────────────────────────────────────────────────────────────────
  • Dynamic η_thermo progression: 0.42 → 0.78 → 0.61
  • Hysteresis hold detected: ε=0.68 maintained across η spike
  • YIELDING kernel status: 2 instances (bus coordination active)
  • Sanitization: CLEAN (2), SANITIZED (1)

================================================================================
✅ All validation checks passed - seed data ready for Maru guardian polling
```

## Troubleshooting

### Error: "NOTION_TOKEN environment variable not set"

Set the token using one of the methods above.

### Error: "Failed to query database"

1. Check that the integration has access to the database
2. Verify the database ID: `9a32dcb5-00b6-40d7-bd86-43d93965fa82`
3. Confirm the token is valid (not expired)

### Error: "ModuleNotFoundError: No module named 'notion_client'"

Install dependencies:

```bash
cd ~/diamondnode-unified-inference
source yennefer_venv/bin/activate
pip install notion-client tabulate
```

## Next Steps

After successful seeding:

1. **Deploy Yennefer Daemon:**
   ```bash
   cd ~/diamondnode-unified-inference/deployment
   ./deploy_yennefer.sh
   ```

2. **View Data in Notion:**
   - https://notion.so/9a32dcb5-00b6-40d7-bd86-43d93965fa82

3. **Monitor Live Telemetry:**
   ```bash
   sudo journalctl -u yennefer-telemetry -f
   ```

4. **Maru Guardian Integration:**
   - Sample data demonstrates hysteresis hold (Row 2)
   - VRAM warning scenario (Row 3)
   - All crystalline scores ≥ 0.85 target

## Files Created

```
~/diamondnode-unified-inference/
├── scripts/
│   ├── seed_notion_telemetry.py      # Creates 3 sample rows
│   ├── verify_notion_seed.py          # Validates seed data
│   └── SETUP_NOTION_SEED.md           # This file
└── artifacts/diamondnode_maru_integration/
    └── telemetry_schemas/
        └── SAMPLE_DATA_DOCUMENTATION.md  # Physics rationale
```

## Documentation

See `SAMPLE_DATA_DOCUMENTATION.md` for detailed physics rationale:
- Hysteresis hold demonstration
- Crystalline score computation
- VRAM warning scenarios
- Sanitization wrapper behavior
