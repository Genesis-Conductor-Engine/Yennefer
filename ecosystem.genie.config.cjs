module.exports = {
  apps: [
    {
      name: 'project-genie',
      script: './scripts/genesis.cjs',
      env: {
        GENESIS_LOOP: 'true',
        FORCE_MUTATION: 'true',
      },
    },
  ],
};