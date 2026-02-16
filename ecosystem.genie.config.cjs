// PM2 Configuration for Yennefer Project Genie Integration
// Live and continuous world building

const path = require('path');

module.exports = {
  apps: [
    {
      name: 'yennefer-genie',
      script: path.join(__dirname, 'scripts/genesis.cjs'),
      cwd: __dirname,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        GENIE_MODE: 'active'
      },
      error_file: path.join(__dirname, 'logs/genie-error.log'),
      out_file: path.join(__dirname, 'logs/genie-out.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
