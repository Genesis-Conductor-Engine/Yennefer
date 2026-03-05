// PM2 Ecosystem Configuration for Yennefer Genesis Conductor - Project Genie Integration
// Configured to run the continuous building loop

module.exports = {
  apps: [
    {
      name: 'project-genie',
      script: './scripts/genesis.cjs',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 5000,
      env: {
        GENESIS_LOOP: 'true',
        FORCE_MUTATION: 'true'
      }
    }
  ]
};
