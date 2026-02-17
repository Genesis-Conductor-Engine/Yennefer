// PM2 Ecosystem Configuration for Project Genie (Continuous Building)
// Runs the Genesis Cycle continuously to evolve the Yennefer world.
// Inspired by Google Labs Project Genie: https://labs.google/projectgenie

module.exports = {
  apps: [
    {
      name: 'project-genie-builder',
      script: './scripts/genesis.cjs',
      interpreter: 'node',
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      // Run every 60 seconds (60000ms) to simulate continuous evolution
      // This creates a "live" building effect as new components are generated over time
      restart_delay: 60000,
      env: {
        NODE_ENV: 'production',
        // FORCE_MUTATION: 'true' // Set to true for rapid demo mode
      }
    }
  ]
};
