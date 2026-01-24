/**
 * Deploy QFLOP Token to Base Mainnet
 * Mints tokens based on GPU quantum compute production
 */

const hre = require("hardhat");
const fs = require("fs");

async function main() {
    console.log("🚀 Deploying QFLOP Token to Base Mainnet...");
    
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deployer:", deployer.address);
    
    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log("Balance:", hre.ethers.formatEther(balance), "ETH");
    
    // Set minter to the legacy wallet (will be updated to conductor)
    const minterAddress = "0x9545e2439c5c75d3aA723AcaC1AA6B0fa1DB6956";
    
    // Deploy
    const QFLOPToken = await hre.ethers.getContractFactory("QFLOPToken");
    
    // Estimate gas
    const deployTx = await QFLOPToken.getDeployTransaction(minterAddress);
    const gasEstimate = await hre.ethers.provider.estimateGas(deployTx);
    const feeData = await hre.ethers.provider.getFeeData();
    const gasCost = gasEstimate * feeData.gasPrice;
    
    console.log("Estimated gas cost:", hre.ethers.formatEther(gasCost), "ETH");
    
    if (balance < gasCost) {
        console.log("❌ Insufficient balance for deployment");
        process.exit(1);
    }
    
    console.log("Deploying...");
    const token = await QFLOPToken.deploy(minterAddress);
    await token.waitForDeployment();
    
    const address = await token.getAddress();
    console.log("✅ QFLOP Token deployed to:", address);
    
    // Save deployment info
    const deploymentInfo = {
        network: "base",
        chainId: 8453,
        contract: "QFLOPToken",
        address: address,
        minter: minterAddress,
        deployer: deployer.address,
        timestamp: new Date().toISOString(),
        txHash: token.deploymentTransaction().hash
    };
    
    fs.writeFileSync(
        "artifacts/qflop_token_deployment.json",
        JSON.stringify(deploymentInfo, null, 2)
    );
    
    console.log("📁 Deployment info saved to artifacts/qflop_token_deployment.json");
    
    // Verify initial state
    const name = await token.name();
    const symbol = await token.symbol();
    const totalSupply = await token.totalSupply();
    
    console.log("");
    console.log("Token Info:");
    console.log("  Name:", name);
    console.log("  Symbol:", symbol);
    console.log("  Total Supply:", hre.ethers.formatEther(totalSupply), symbol);
    console.log("  Minter:", await token.minter());
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
