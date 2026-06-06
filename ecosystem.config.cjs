module.exports = {
  apps: [
    // === CORE SERVICES ===
    { name: 'diamond-vault', script: '/home/diamondnode/Yennefer/genesis-q-mem/qmcp_admin_panel.py', interpreter: 'python3', autorestart: true, watch: false, max_memory_restart: '500M', restart_delay: 5000, env: { COMPUTE_MODE: 'dual', ALWAYS_ON: 'true' } },
    { name: 'diamond-watchdog', script: '/home/diamondnode/Yennefer/genesis-q-mem/qmcp_diamond_watchdog.py', interpreter: 'python3', autorestart: true, watch: false, max_memory_restart: '200M', restart_delay: 5000, env: { COMPUTE_MODE: 'local', ALWAYS_ON: 'true' } },
    { name: 'a2a-handoff', script: '/home/diamondnode/Yennefer/genesis-q-mem/a2a_handoff_server.py', interpreter: 'python3', autorestart: true, watch: false, max_memory_restart: '200M', restart_delay: 5000, env: { COMPUTE_MODE: 'dual', ALWAYS_ON: 'true' } },

    // === BLOCKCHAIN SERVICES ===
    { name: 'qmcp-bridge', script: '/home/diamondnode/Yennefer/scripts/qmcp_genesis_bridge.cjs', autorestart: true, watch: false, max_memory_restart: '300M', restart_delay: 5000, env: { COMPUTE_MODE: 'dual', ALWAYS_ON: 'true' } },
    { name: 'eth-bridge', script: '/home/diamondnode/Yennefer/scripts/eth_optimism_bridge.cjs', autorestart: true, watch: false, max_memory_restart: '300M', restart_delay: 10000, env: { COMPUTE_MODE: 'remote', ALWAYS_ON: 'true' } },
    { name: 'genesis-deployer', script: '/home/diamondnode/Yennefer/scripts/genesis_deployer.cjs', autorestart: true, watch: false, max_memory_restart: '200M', restart_delay: 10000, env: { COMPUTE_MODE: 'remote', ALWAYS_ON: 'true' } },

    // === QFLOP BACKFILL (INTEGRATED - finishes the QFLOP loop on diamondnode) ===
    {
      name: 'qflop-backfill',
      script: '/home/diamondnode/Yennefer/qflop-backfill/orchestrator/backfill_orchestrator.mjs',
      interpreter: 'node',
      interpreter_args: '--experimental-vm-modules',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      restart_delay: 5000,
      min_uptime: '10s',
      out_file: '/home/diamondnode/Yennefer/qflop-backfill/logs/orchestrator-out.log',
      error_file: '/home/diamondnode/Yennefer/qflop-backfill/logs/orchestrator-err.log',
      merge_logs: false,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        NODE_ENV: 'production',
        NODE_OPTIONS: '--experimental-vm-modules',
        BACKFILL_MASTER_MNEMONIC: process.env.BACKFILL_MASTER_MNEMONIC || '',
        STRIPE_SECRET_KEY: process.env.STRIPE_SECRET_KEY || '',
        STRIPE_CUSTOMER_ID: process.env.STRIPE_CUSTOMER_ID || 'cus_UE77PXj6fhQCen',
        WORKER_AUTH_TOKEN: process.env.WORKER_AUTH_TOKEN || '',
        BILLING_WORKER_URL: process.env.BILLING_WORKER_URL || 'https://genesis-billing-worker.iholt.workers.dev',
        RPC_URL: process.env.RPC_URL || 'https://mainnet.base.org',
        WQFLOP_CONTRACT: process.env.WQFLOP_CONTRACT || '0x69262A2D7c92c074729823B654fE7E4Cdb749747',
        ETH_PRICE_USD: process.env.ETH_PRICE_USD || '2500',
        ETHERSCAN_API_KEY: process.env.ETHERSCAN_API_KEY || ''
      }
    },

    // === MINING & MONITORING ===
    { name: 'qflop-miner', script: '/home/diamondnode/Yennefer/genesis-q-mem/qmcp_qflop_miner.py', interpreter: 'python3', autorestart: true, watch: false, max_memory_restart: '500M', restart_delay: 5000, env: { COMPUTE_MODE: 'local', ALWAYS_ON: 'true' } },
    { name: 'process-guardian', script: '/home/diamondnode/Yennefer/scripts/process_guardian.cjs', autorestart: true, watch: false, max_memory_restart: '200M', restart_delay: 5000, env: { COMPUTE_MODE: 'local', ALWAYS_ON: 'true' } },

    // === MANAGEMENT / SECURE SURFACES (Auth0 JWT Bearer protected) ===
    // Secures botid-dashboard (Vite React config/monitoring + hook exec) with stateless JWT.
    // - Requires prior `cd ~/botid-dashboard && npm run build` (dist/ served; see server.mjs)
    // - Uses checkJwt + requiredScopes from express-oauth2-jwt-bearer (^1.9.0)
    // - Protected: /api/* (incl. POST /api/exec-hook | /api/qflop -> safe ~/bin/qflop_manage allowlist)
    // - Public: static dashboard UI + /health + /api/public
    // - Env: AUTH0_DOMAIN + AUTH0_AUDIENCE (or ISSUER_BASE_URL/AUDIENCE) from ~/.env or local .env
    // - Telegram diamondnodebot / kimi-claw (18789) + direct ~/bin/qflop_manage calls remain fully functional (hook-direct path untouched).
    // - Start after edit: pm2 start ~/Yennefer/ecosystem.config.cjs --only botid-dashboard-secure ; pm2 save
    {
      name: 'botid-dashboard-secure',
      script: '/home/diamondnode/botid-dashboard/server.mjs',
      cwd: '/home/diamondnode/botid-dashboard',
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      restart_delay: 5000,
      min_uptime: '5s',
      out_file: '/home/diamondnode/logs/botid-dashboard-secure-out.log',
      error_file: '/home/diamondnode/logs/botid-dashboard-secure-err.log',
      merge_logs: false,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        NODE_ENV: 'production',
        PORT: '3100'
        // AUTH0_* and other secrets pulled via dotenv in server.mjs from ~/.env (preferred for shared) + local .env
      }
    }
  ]
};
