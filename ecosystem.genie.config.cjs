// PM2 Configuration for Yennefer Project Genie Integration
// Ensures live and continuous building of the world.

module.exports = {
  apps: [
    {
      name: 'yennefer-genie',
      script: './scripts/genesis.cjs',
      cwd: __dirname,
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      restart_delay: 10000, // 10 seconds delay if it crashes
      env: {
        NODE_ENV: 'production',
        PROJECT_GENIE_ENABLED: 'true'
      },
      error_file: '/home/yenn/.yennefer/logs/genie-error.log',
      out_file: '/home/yenn/.yennefer/logs/genie-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
