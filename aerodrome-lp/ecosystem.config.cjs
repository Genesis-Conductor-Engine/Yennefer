require('dotenv').config({ path: '/home/diamondnode/.env' });

module.exports = {
  apps: [
    {
      name: 'lp-autoscale',
      script: 'scripts/lp_autoscale.mjs',
      cwd: '/home/diamondnode/Yennefer/aerodrome-lp',
      interpreter: 'node',
      interpreter_args: '--experimental-vm-modules -r dotenv/config',
      // Run continuously with internal loop (30 min sleep between cycles)
      autorestart: true,
      restart_delay: 1800000,  // 30 min between restarts if it exits
      max_restarts: 1000,
      max_memory_restart: '512M',
      env: {
        NODE_PATH: '/home/diamondnode/Yennefer/qflop-backfill/node_modules',
        DOTENV_CONFIG_PATH: '/home/diamondnode/Yennefer/aerodrome-lp/.env',
        RPC_URL: 'https://base-rpc.publicnode.com',
        // Live txs need PRIVATE_KEY in process env or foundry keystore via workflow.sh.
        // Without PRIVATE_KEY the loop stays online in dry-run + dashboard mode.
        PRIVATE_KEY: process.env.PRIVATE_KEY || '',
        LP_DRY_RUN: process.env.LP_DRY_RUN || (process.env.PRIVATE_KEY ? '0' : '1'),
        LP_CYCLE_INTERVAL_MS: '1800000',  // 30 min
      },
      error_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/autoscale-err.log',
      out_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/autoscale-out.log',
      merge_logs: true,
      time: true,
    },
    {
      name: 'lp-dashboard',
      script: 'scripts/lp_dashboard_propagate.mjs',
      args: '--propagate --loop',
      cwd: '/home/diamondnode/Yennefer/aerodrome-lp',
      interpreter: 'node',
      interpreter_args: '--experimental-vm-modules -r dotenv/config',
      autorestart: true,
      restart_delay: 900000,  // 15 min between restarts if it exits
      max_restarts: 1000,
      max_memory_restart: '256M',
      env: {
        NODE_PATH: '/home/diamondnode/Yennefer/qflop-backfill/node_modules',
        DOTENV_CONFIG_PATH: '/home/diamondnode/.env',
        RPC_URL: 'https://base-rpc.publicnode.com',
        PRIVATE_KEY: process.env.PRIVATE_KEY || '',
        DASHBOARD_INTERVAL_MS: '900000',  // 15 min
      },
      error_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/dashboard-err.log',
      out_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/dashboard-out.log',
      merge_logs: true,
      time: true,
    },
    {
      // here.now async realtime publisher for live QFLOP LP dashboard
      // consumes /dev/shm lp_dashboard + accumulated + backfill_state + registry
      // regenerates site + publishes updates so sunny-lantern-pmcn.here.now stays current
      name: 'qflop-here-realtime',
      script: '/home/diamondnode/qflop-lp-here/realtime-sync.mjs',
      cwd: '/home/diamondnode/qflop-lp-here',
      interpreter: 'node',
      autorestart: true,
      restart_delay: 10000,
      max_restarts: 100,
      max_memory_restart: '128M',
      env: {
        QFLOP_HERE_SLUG: 'sunny-lantern-pmcn',
        PUBLISH_INTERVAL: '28000'
      },
      error_file: '/home/diamondnode/qflop-lp-here/logs/realtime-err.log',
      out_file: '/home/diamondnode/qflop-lp-here/logs/realtime-out.log',
      merge_logs: true,
      time: true,
    },
  ],
};
