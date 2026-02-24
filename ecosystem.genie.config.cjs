module.exports = {
  apps: [{
    name: "genesis-project-genie",
    script: "./scripts/genesis.cjs",
    env: {
      GENESIS_LOOP: "true",
      FORCE_MUTATION: "true",
      NODE_ENV: "production"
    }
  }]
}
