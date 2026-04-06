#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";
import { ethers } from "ethers";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const configPath = path.join(rootDir, "ops", "wallet_status.config.yml");
const docsDir = path.join(rootDir, "docs");

const erc20Abi = [
  "function balanceOf(address owner) view returns (uint256)",
  "function decimals() view returns (uint8)",
  "function symbol() view returns (string)",
];

function mustEnv(key) {
  const value = process.env[key];
  if (!value) throw new Error(`Missing required env var: ${key}`);
  return value;
}

function fmt(n, maxDecimals = 6) {
  const x = Number(n);
  if (!Number.isFinite(x)) return String(n);
  if (x === 0) return "0";
  if (x < 0.000001) return x.toExponential(3);
  return x.toLocaleString(undefined, {
    maximumFractionDigits: maxDecimals,
    minimumFractionDigits: x < 1 ? 4 : 2,
  });
}

function toFloat(value) {
  const x = Number(value);
  return Number.isFinite(x) ? x : 0;
}

function loadPrices() {
  try {
    return JSON.parse(process.env.WALLET_STATUS_PRICES_JSON || "{}");
  } catch {
    return {};
  }
}

function calcTotalUSD(networkResults, prices = {}) {
  let total = 0;
  for (const network of networkResults) {
    const nativePrice = toFloat(prices[network.nativeSymbol]);
    for (const wallet of network.wallets) {
      total += toFloat(wallet.nativeBalance.formatted) * nativePrice;
      for (const token of wallet.tokens) {
        total += toFloat(token.formatted) * toFloat(prices[token.symbol]);
      }
    }
  }
  return total;
}

async function getTokenBalance(provider, tokenAddress, walletAddress, fallbackSymbol, fallbackDecimals) {
  const contract = new ethers.Contract(tokenAddress, erc20Abi, provider);
  const [balance, decimals, symbol] = await Promise.all([
    contract.balanceOf(walletAddress),
    fallbackDecimals != null ? Promise.resolve(fallbackDecimals) : contract.decimals(),
    contract.symbol().catch(() => fallbackSymbol || "UNKNOWN"),
  ]);

  return {
    raw: balance.toString(),
    formatted: ethers.formatUnits(balance, decimals),
    decimals,
    symbol,
    address: tokenAddress,
  };
}

function evaluateAlerts(report, alerting) {
  const alerts = [];
  for (const network of report.networks) {
    const minNative = network.nativeSymbol === "MATIC"
      ? alerting?.min_native_balance_matic
      : alerting?.min_native_balance_eth;

    for (const wallet of network.wallets) {
      if (minNative != null && toFloat(wallet.nativeBalance.formatted) < toFloat(minNative)) {
        alerts.push({
          severity: "critical",
          type: "native_balance_low",
          network: network.name,
          wallet: wallet.name,
          symbol: network.nativeSymbol,
          actual: wallet.nativeBalance.formatted,
          threshold: String(minNative),
        });
      }
    }
  }

  if (
    alerting?.critical_threshold_usd != null
    && toFloat(report.summary.totalUsdEstimate) < toFloat(alerting.critical_threshold_usd)
  ) {
    alerts.push({
      severity: "critical",
      type: "portfolio_value_low",
      actual: String(report.summary.totalUsdEstimate),
      threshold: String(alerting.critical_threshold_usd),
    });
  }

  return alerts;
}

function writeDocs(report) {
  fs.mkdirSync(docsDir, { recursive: true });

  fs.writeFileSync(path.join(docsDir, "wallet_status.json"), `${JSON.stringify(report, null, 2)}\n`);

  const banner = `**Wallet Vital Signs:** ${report.summary.totalWallets} wallets | ${report.summary.networkCount} networks | Estimated Total: $${fmt(report.summary.totalUsdEstimate, 2)} | Alerts: ${report.alerts.length}`;
  fs.writeFileSync(path.join(docsDir, "WALLET_BANNER.md"), `${banner}\n`);

  const lines = [
    "# Genesis Conductor Wallet Status",
    "",
    `Last Updated (UTC): ${report.generatedAt}`,
    "",
    `Estimated Total Value: **$${fmt(report.summary.totalUsdEstimate, 2)}**`,
    `Active Alerts: **${report.alerts.length}**`,
    "",
    "## Networks",
  ];

  for (const network of report.networks) {
    lines.push("", `### ${network.name} (${network.nativeSymbol})`);
    for (const wallet of network.wallets) {
      lines.push(`- **${wallet.name}** (${wallet.address})`);
      lines.push(`  - Native: ${fmt(wallet.nativeBalance.formatted)} ${network.nativeSymbol}`);
      for (const token of wallet.tokens) {
        lines.push(`  - ${token.symbol}: ${fmt(token.formatted)}`);
      }
    }
  }

  if (report.alerts.length) {
    lines.push("", "## Alerts", "");
    for (const alert of report.alerts) {
      lines.push(`- [${alert.severity}] ${alert.type} :: ${JSON.stringify(alert)}`);
    }
  }

  if (report.warnings?.length) {
    lines.push("", "## Warnings", "");
    for (const warning of report.warnings) lines.push(`- ${warning}`);
  }

  fs.writeFileSync(path.join(docsDir, "WALLET_STATUS.md"), `${lines.join("\n")}\n`);
}

async function collect() {
  const config = yaml.load(fs.readFileSync(configPath, "utf8"));
  const prices = loadPrices();
  const networks = [];
  const warnings = [];

  for (const network of config.networks || []) {
    const provider = new ethers.JsonRpcProvider(mustEnv(network.rpcEnv), network.chainId);
    const wallets = [];

    for (const wallet of config.wallets || []) {
      if (!ethers.isAddress(wallet.address)) {
        warnings.push(`Skipped invalid wallet address for ${wallet.name}: ${wallet.address}`);
        continue;
      }

      const nativeRaw = await provider.getBalance(wallet.address);
      const nativeBalance = {
        raw: nativeRaw.toString(),
        formatted: ethers.formatEther(nativeRaw),
      };

      const tokens = [];
      for (const token of network.tokens || []) {
        try {
          const balance = await getTokenBalance(provider, token.address, wallet.address, token.symbol, token.decimals);
          tokens.push(balance);
        } catch (error) {
          tokens.push({
            symbol: token.symbol || "UNKNOWN",
            address: token.address,
            error: error.message,
            formatted: "0",
          });
        }
      }

      wallets.push({
        name: wallet.name,
        address: wallet.address,
        tags: wallet.tags || [],
        nativeBalance,
        tokens,
      });
    }

    networks.push({
      name: network.name,
      chainId: network.chainId,
      nativeSymbol: network.nativeSymbol,
      wallets,
    });
  }

  const totalUsdEstimate = calcTotalUSD(networks, prices);
  const report = {
    generatedAt: new Date().toISOString(),
    summary: {
      networkCount: networks.length,
      totalWallets: (config.wallets || []).length,
      processedWallets: networks.reduce((acc, n) => acc + n.wallets.length, 0),
      totalUsdEstimate,
      priceSymbols: Object.keys(prices),
    },
    prices,
    networks,
  };

  report.alerts = evaluateAlerts(report, config.alerting || {});
  report.warnings = warnings;
  writeDocs(report);

  console.log("wallet-status: wrote docs/wallet_status.json, docs/WALLET_STATUS.md, docs/WALLET_BANNER.md");
}

collect().catch((error) => {
  console.error(`wallet-status: ${error.message}`);
  process.exitCode = 1;
});
