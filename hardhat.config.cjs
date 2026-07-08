require('@nomicfoundation/hardhat-toolbox');
require('@nomicfoundation/hardhat-ledger');
require('dotenv').config();

// Hot key (legacy signer). Only used while sweeping assets out during rotation.
// Provided at runtime via env; never inlined. Invalid/placeholder -> no account
// (prevents hardhat load errors and accidental use of a junk key).
const RAW_KEY = process.env.ETH_PRIVATE_KEY || process.env.BASE_PRIVATE_KEY || '';
const HOT_ACCOUNTS = /^0x[0-9a-fA-F]{64}$/.test(RAW_KEY) ? [RAW_KEY] : [];

// Rotation target: the Ledger hardware account that replaces the hot key.
// Set LEDGER_ACCOUNT=0x... to enable hardware signing for that address.
const LEDGER_ACCOUNTS = /^0x[0-9a-fA-F]{40}$/.test(process.env.LEDGER_ACCOUNT || '')
  ? [process.env.LEDGER_ACCOUNT]
  : [];

// Secrets moved out of source. Rotate the previously-committed keys.
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY || '';
const BASE_MAINNET_RPC = process.env.BASE_MAINNET_RPC || process.env.BASE_RPC_URL || 'https://mainnet.base.org';

module.exports = {
  etherscan: {
    apiKey: ETHERSCAN_API_KEY,
    customChains: [
      {
        network: "baseMainnet",
        chainId: 8453,
        urls: {
          apiURL: "https://api.basescan.org/api",
          browserURL: "https://basescan.org"
        }
      },
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia.basescan.org"
        }
      }
    ]
  },
  sourcify: {
    enabled: false,
  },
  solidity: {
    // 0.8.32 clears explorer warnings for:
    // LostStorageArrayWriteOnSlotOverflow, VerbatimInvalidDeduplication,
    // FullInlinerNonExpressionSplitArgumentEvaluationOrder, MissingSideEffectsOnSelectorAccess
    compilers: [
      { version: '0.8.32', settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: 'cancun' } },
      { version: '0.8.28' },
      { version: '0.8.24' },
    ],
  },
  networks: {
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_RPC || 'https://sepolia.base.org',
      accounts: HOT_ACCOUNTS,
      ledgerAccounts: LEDGER_ACCOUNTS,
      chainId: 84532,
    },
    baseMainnet: {
      url: BASE_MAINNET_RPC,
      accounts: HOT_ACCOUNTS,
      ledgerAccounts: LEDGER_ACCOUNTS,
      chainId: 8453,
    },
  },
};
