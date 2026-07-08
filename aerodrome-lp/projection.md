# wQFLOP/WETH Liquidity — Plans & Projections (2026-07-08)

- Pool: `0x4aBC6D796cd036b6f1E433A97F9784a00f90C53e` (Aerodrome volatile)
- Reserves: WETH=3904437556426949 wei, wQFLOP=313667413886288907520718572531 wei
- Decision: **ADD** (within_caps); daily spent 0 / 100000000000000000
- **1 ETH goal:** accrued **0.003895621937509833 ETH** (0.3896%) — components wallet_eth=0.00000166202660499, wallet_weth=0.000000064335880247, lp_weth_share=0.003893895575024596
- Compiler: solc **0.8.32** (clears LostStorageArrayWriteOnSlotOverflow + prior low-sev bugs)
- Workflow: see `docs/1ETH-RECOVERY-WORKFLOW.md` · pm2 lp-autoscale dry-run online
- Blocker: fund LP_OWNER ≥ 0.01 ETH for live execution

_Subagent: push this to Notion via notion-cli (page: 'wQFLOP Liquidity — Plans & Projections'). Handoff vibe agent `/loop n=n` until 1 ETH._
