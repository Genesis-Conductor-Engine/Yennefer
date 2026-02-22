const hre = require("hardhat");

async function main() {
  // Retrieves the signer based on the private key in your configuration
  const [signer] = await hre.ethers.getSigners();
  const address = await signer.getAddress();
  
  // Fetches the balance from the provider
  const balance = await hre.ethers.provider.getBalance(address);
  
  console.log(`Wallet Address: ${address}`);
  console.log(`Current Balance: ${hre.ethers.formatEther(balance)} ETH`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
