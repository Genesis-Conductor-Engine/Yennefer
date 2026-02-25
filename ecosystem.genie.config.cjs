// ecosystem.genie.config.cjs
// PM2 Configuration for Project Genie Integration (Yennefer Genesis)

module.exports = {
  apps: [
    {
      name: 'yennefer-genie',
      script: './scripts/genesis.cjs',
      cwd: './',
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        GENESIS_LOOP: 'true',
        GENESIS_INTERVAL: '60000', // Check every 60 seconds
        // GEMINI_API_KEY should be set in the system environment
      }
    }
  ]
};
