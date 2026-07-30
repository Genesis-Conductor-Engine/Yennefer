// PM2 Ecosystem Configuration for Yennefer Genesis Conductor
// All services configured for always-on operation with auto-restart

module.exports = {
  apps: [
    // === CORE SERVICES ===
    {
      name: 'diamond-vault',
      script: '/home/yenn/genesis-q-mem/qmcp_admin_panel.py',
      interpreter: 'python3',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 5000,
      env: {
        COMPUTE_MODE: 'dual',
        ALWAYS_ON: 'true'
      }
    },
    {
      name: 'diamond-watchdog',
      script: '/home/yenn/genesis-q-mem/qmcp_diamond_watchdog.py',
      interpreter: 'python3',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      restart_delay: 5000,
      env: {
        COMPUTE_MODE: 'local',
        ALWAYS_ON: 'true'
      }
    },
    {
      name: 'a2a-handoff',
      script: '/home/yenn/genesis-q-mem/a2a_handoff_server.py',
      interpreter: 'python3',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      restart_delay: 5000,
      env: {
        COMPUTE_MODE: 'dual',
        ALWAYS_ON: 'true'
      }
    },

    // === BLOCKCHAIN SERVICES ===
    {
      name: 'qmcp-bridge',
      script: '/home/yenn/scripts/qmcp_genesis_bridge.cjs',
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      restart_delay: 5000,
      env: {
        COMPUTE_MODE: 'dual',
        ALWAYS_ON: 'true'
      }
    },
    {
      name: 'eth-bridge',
      script: '/home/yenn/scripts/eth_optimism_bridge.cjs',
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      restart_delay: 10000,
      env: {
        COMPUTE_MODE: 'remote',
        ALWAYS_ON: 'true'
      }
    },
    {
      name: 'genesis-deployer',
      script: '/home/yenn/scripts/genesis_deployer.cjs',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      restart_delay: 10000,
      env: {
        COMPUTE_MODE: 'remote',
        ALWAYS_ON: 'true'
      }
    },

    // === MINING & MONITORING ===
    {
      name: 'qflop-miner',
      script: '/home/yenn/genesis-q-mem/qmcp_qflop_miner.py',
      interpreter: 'python3',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 5000,
      env: {
        COMPUTE_MODE: 'local',
        ALWAYS_ON: 'true'
      }
    },
    {
      name: 'process-guardian',
      script: '/home/yenn/scripts/process_guardian.cjs',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      restart_delay: 5000,
      env: {
        COMPUTE_MODE: 'local',
        ALWAYS_ON: 'true'
      }
    }
  ]
};
