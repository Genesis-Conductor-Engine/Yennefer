// PM2 Configuration for Project Genie Integration
// Ensures continuous building and evolution of Yennefer

module.exports = {
  apps: [
    {
      name: 'yennefer-genie',
      script: './scripts/genesis.cjs',
      env: {
        NODE_ENV: 'production',
        FORCE_MUTATION: 'false' // Default to false, let the cycle decide or override externally
      },
      autorestart: true,
      restart_delay: 60000, // Run every 60 seconds
      watch: false,
      max_memory_restart: '200M'
    }
  ]
};
