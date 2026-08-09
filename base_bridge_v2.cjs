const { ethers } = require('ethers');
require('dotenv').config();

// Base L1 Bridge addresses - there are two interfaces:
// 1. L1StandardBridge (old): 0x3154Cf16ccdb4C6d922629664174b904d80F2C35
// 2. OptimismPortal (new): 0x49048044D57e1C92A77f79988d21Fa8fAF74E97e
const OPTIMISM_PORTAL = '0x49048044D57e1C92A77f79988d21Fa8fAF74E97e';

async function bridgeToBase() {
    console.log('🔷 ETH → Base (OptimismPortal Direct Deposit)');
    console.log('═══════════════════════════════════════════════════════════════');
    
    const ethRpc = process.env.GETBLOCK_ETH_RPC || process.env.ETH_MAINNET_RPC || 'https://eth.llamarpc.com';
    const provider = new ethers.JsonRpcProvider(ethRpc);
    const pk = process.env.ETH_PRIVATE_KEY;
    
    if (!pk) {
        console.log('❌ ETH_PRIVATE_KEY not found');
        return;
    }
    
    const wallet = new ethers.Wallet(pk, provider);
    console.log('Wallet:', wallet.address);
    
    const balance = await provider.getBalance(wallet.address);
    console.log('ETH Balance:', ethers.formatEther(balance), 'ETH');
    
    // Keep 0.0005 ETH for gas
    const gasReserve = ethers.parseEther('0.0005');
    const bridgeAmount = balance - gasReserve;
    
    if (bridgeAmount <= 0n) {
        console.log('❌ Insufficient balance');
        return;
    }
    
    console.log('Bridge Amount:', ethers.formatEther(bridgeAmount), 'ETH');
    
    // OptimismPortal depositTransaction function
    const portalABI = [
        'function depositTransaction(address _to, uint256 _value, uint64 _gasLimit, bool _isCreation, bytes _data) payable'
    ];
    
    const portal = new ethers.Contract(OPTIMISM_PORTAL, portalABI, wallet);
    
    console.log('\n🚀 Bridging via OptimismPortal...');
    
    try {
        const feeData = await provider.getFeeData();
        console.log('   Gas Price:', ethers.formatUnits(feeData.gasPrice, 'gwei'), 'gwei');
        
        // depositTransaction - send ETH to ourselves on L2
        const tx = await portal.depositTransaction(
            wallet.address,  // recipient on L2
            bridgeAmount,    // amount to send
            100000n,         // L2 gas limit
            false,           // not a contract creation
            '0x',            // no calldata
            { 
                value: bridgeAmount, 
                gasLimit: 200000,
                maxFeePerGas: feeData.maxFeePerGas,
                maxPriorityFeePerGas: feeData.maxPriorityFeePerGas
            }
        );
        
        console.log('\n✅ Bridge TX Submitted!');
        console.log('   TX Hash:', tx.hash);
        console.log('   Etherscan: https://etherscan.io/tx/' + tx.hash);
        
        const receipt = await tx.wait();
        console.log('   ✅ Confirmed in block:', receipt.blockNumber);
        console.log('   Gas Used:', receipt.gasUsed.toString());
        console.log('\n💰 ETH will arrive on Base in ~10-15 minutes');
        
    } catch (err) {
        console.log('❌ Bridge error:', err.reason || err.message);
    }
}

bridgeToBase().catch(console.error);
