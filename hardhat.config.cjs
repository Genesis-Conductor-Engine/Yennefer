require('@nomicfoundation/hardhat-toolbox');
require('dotenv').config();

// SAFETY CHECK: If PRIVATE_KEY is not in .env, use a placeholder that forces a prompt
const PRIVATE_KEY = process.env.ETH_PRIVATE_KEY || 'YOUR_PRIVATE_KEY_HERE';

module.exports = {
  etherscan: {
    apiKey: process.env.BASESCAN_API_KEY || '',
  },
  sourcify: {
    enabled: false,
  },
  solidity: {
    compilers: [
      { version: '0.8.24' },
      { version: '0.8.28' },
    ],
  },
  networks: {
    baseSepolia: {
      url: 'https://sepolia.base.org',
      accounts: [PRIVATE_KEY],
      chainId: 84532,
    },
    baseMainnet: {
      url: process.env.GETBLOCK_BASE_RPC || process.env.BASE_MAINNET_RPC || 'https://mainnet.base.org',
      accounts: [PRIVATE_KEY],
      chainId: 8453,
    },
  },
};
