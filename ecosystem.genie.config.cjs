module.exports = {
  apps: [{
    name: 'project-genie',
    script: './scripts/genesis.cjs',
    env: {
      NODE_ENV: 'production'
    },
    restart_delay: 60000,
    autorestart: true
  }]
}
