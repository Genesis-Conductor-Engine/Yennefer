module.exports = {
  apps: [
    {
      name: 'project-genie',
      script: './scripts/genesis.cjs',
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      restart_delay: 5000,
      env: {
        GENESIS_LOOP: 'true',
        FORCE_MUTATION: 'true',
        ALWAYS_ON: 'true'
      }
    }
  ]
};
