// ecosystem.genie.config.cjs
// PM2 Ecosystem Configuration for Project Genie Integration (Continuous Building)

module.exports = {
  apps: [
    {
      name: 'genesis-genie',
      script: './scripts/genesis.cjs',
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        GENESIS_LOOP: 'true',
        GENESIS_INTERVAL: '60000', // 1 minute interval for "live" building
        FORCE_MUTATION: 'false', // Set to 'true' to force visual updates every cycle
      }
    }
  ]
};
