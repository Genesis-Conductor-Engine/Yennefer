// PM2 Configuration for Yennefer Genesis Cycle (Project Genie Integration)
// Manages the continuous building loop

module.exports = {
  apps: [
    {
      name: 'yennefer-genesis',
      script: './scripts/genesis.cjs',
      watch: ['./scripts/genesis.cjs', './scripts/lib/genie.cjs'],
      ignore_watch: ['node_modules', 'logs'],
      env: {
        NODE_ENV: 'production',
        FORCE_MUTATION: 'false'
      },
      // Restart if memory exceeds 200MB (prevent leaks)
      max_memory_restart: '200M',
      // Delay between restarts if script crashes
      restart_delay: 5000,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    }
  ]
};
