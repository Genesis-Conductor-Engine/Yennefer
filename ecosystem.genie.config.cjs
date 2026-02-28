module.exports = {
  apps: [
    {
      name: 'genie-genesis-loop',
      script: './scripts/genesis.cjs',
      env: {
        GENESIS_LOOP: 'true',
        FORCE_MUTATION: 'true'
      }
    }
  ]
};
