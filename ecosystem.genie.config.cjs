// PM2 Ecosystem Configuration for Yennefer Genesis Conductor (Project Genie Integration)
// Runs the continuous building cycle

module.exports = {
  apps: [
    {
      name: 'genesis-cycle',
      script: './scripts/genesis.cjs',
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        FORCE_MUTATION: 'false'
      }
    }
  ]
};
