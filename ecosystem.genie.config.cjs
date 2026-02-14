// PM2 Configuration for Yennefer Project Genie Integration
// Ensures live and continuous building of the world

module.exports = {
  apps: [
    {
      name: 'yennefer-genie',
      script: './scripts/genesis.cjs',
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        GENIE_MODE: 'true'
      },
      error_file: './logs/genie-error.log',
      out_file: './logs/genie-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
