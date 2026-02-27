module.exports = {
  apps: [{
    name: 'project-genie',
    script: './scripts/genesis.cjs',
    env: {
      NODE_ENV: 'production',
      GENESIS_LOOP: 'true',
      FORCE_MUTATION: 'true', // Simulate rapid evolution for the "live building" effect
      REFLECTION_INTERVAL: 10000 // 10 seconds for rapid generation demo
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G'
  }]
};
