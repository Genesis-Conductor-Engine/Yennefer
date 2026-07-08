// Load secrets from qflop-backfill + aerodrome .env (never commit)
require('dotenv').config({ path: '/home/diamondnode/Yennefer/qflop-backfill/.env' });
require('dotenv').config({ path: '/home/diamondnode/Yennefer/aerodrome-lp/.env' });
require('dotenv').config({ path: '/home/diamondnode/.env' });

const PK = process.env.PRIVATE_KEY || '';

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
        DOTENV_CONFIG_PATH: '/home/diamondnode/Yennefer/qflop-backfill/.env',
        RPC_URL: 'https://base-rpc.publicnode.com',
        PRIVATE_KEY: PK,
        // Live when key present; gas_keeper maintains floor
        LP_DRY_RUN: process.env.LP_DRY_RUN || (PK ? '0' : '1'),
        LP_CYCLE_INTERVAL_MS: '1800000',  // 30 min
      },
      error_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/autoscale-err.log',
      out_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/autoscale-out.log',
      merge_logs: true,
      time: true,
    },
    {
      name: 'gas-keeper',
      script: 'scripts/gas_keeper.mjs',
      args: '--live --loop',
      cwd: '/home/diamondnode/Yennefer/aerodrome-lp',
      interpreter: 'node',
      interpreter_args: '--experimental-vm-modules',
      autorestart: true,
      restart_delay: 60000,
      max_restarts: 1000,
      max_memory_restart: '256M',
      env: {
        NODE_PATH: '/home/diamondnode/Yennefer/qflop-backfill/node_modules',
        RPC_URL: 'https://base-rpc.publicnode.com',
        PRIVATE_KEY: PK,
        BACKFILL_MASTER_MNEMONIC: process.env.BACKFILL_MASTER_MNEMONIC || '',
        GAS_MIN_ETH: process.env.GAS_MIN_ETH || '0.0005',
        GAS_TARGET_ETH: process.env.GAS_TARGET_ETH || '0.01',
        GAS_MAX_ETH: process.env.GAS_MAX_ETH || '0.05',
        MAX_REMOVE_PCT: process.env.MAX_REMOVE_PCT || '5',
        MIN_LP_SHARE_BPS: process.env.MIN_LP_SHARE_BPS || '7000',
        GAS_KEEPER_INTERVAL_MS: process.env.GAS_KEEPER_INTERVAL_MS || '900000',
      },
      error_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/gas-keeper-err.log',
      out_file: '/home/diamondnode/Yennefer/aerodrome-lp/logs/gas-keeper-out.log',
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
