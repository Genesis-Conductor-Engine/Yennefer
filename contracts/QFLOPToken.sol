// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title QFLOP Token
 * @notice ERC-20 token backed by GPU quantum compute production
 * @dev Minting is controlled by the authorized minter (GPU conductor)
 */
contract QFLOPToken {
    string public constant name = "QFLOP Quantum Compute";
    string public constant symbol = "QFLOP";
    uint8 public constant decimals = 18;
    
    uint256 public totalSupply;
    address public owner;
    address public minter;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    // Production tracking
    uint256 public totalQFLOPSMinted;
    uint256 public lastMintTimestamp;
    uint256 public mintRatePerSecond; // tokens per second based on GPU output
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Mint(address indexed to, uint256 amount, uint256 qflopsProduced);
    event MinterUpdated(address indexed oldMinter, address indexed newMinter);
    event ProductionRateUpdated(uint256 oldRate, uint256 newRate);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    modifier onlyMinter() {
        require(msg.sender == minter || msg.sender == owner, "Not authorized to mint");
        _;
    }
    
    constructor(address _minter) {
        owner = msg.sender;
        minter = _minter;
        lastMintTimestamp = block.timestamp;
        // Initial rate: 1 token per 1 billion QFLOPS (1e9)
        // At 3 TFLOPS = 3e12 FLOPS/sec = 3000 tokens/sec
        mintRatePerSecond = 3000 * 1e18; // 3000 tokens per second at 3 TFLOPS
    }
    
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
    
    /**
     * @notice Mint tokens based on GPU production
     * @param to Recipient of minted tokens
     * @param qflopsProduced Amount of QFLOPS produced since last mint
     */
    function mintFromProduction(address to, uint256 qflopsProduced) external onlyMinter {
        // Calculate tokens based on production
        // 1 token per 1e9 QFLOPS
        uint256 tokensToMint = qflopsProduced / 1e9;
        
        require(tokensToMint > 0, "Production too low to mint");
        
        totalSupply += tokensToMint;
        balanceOf[to] += tokensToMint;
        totalQFLOPSMinted += qflopsProduced;
        lastMintTimestamp = block.timestamp;
        
        emit Transfer(address(0), to, tokensToMint);
        emit Mint(to, tokensToMint, qflopsProduced);
    }
    
    /**
     * @notice Mint tokens based on time elapsed (automated)
     * @param to Recipient of minted tokens
     */
    function mintFromTime(address to) external onlyMinter {
        uint256 elapsed = block.timestamp - lastMintTimestamp;
        require(elapsed > 0, "No time elapsed");
        
        uint256 tokensToMint = (mintRatePerSecond * elapsed) / 1e18;
        require(tokensToMint > 0, "Too soon to mint");
        
        totalSupply += tokensToMint * 1e18;
        balanceOf[to] += tokensToMint * 1e18;
        lastMintTimestamp = block.timestamp;
        
        emit Transfer(address(0), to, tokensToMint * 1e18);
        emit Mint(to, tokensToMint * 1e18, tokensToMint * 1e9);
    }
    
    function setMinter(address newMinter) external onlyOwner {
        emit MinterUpdated(minter, newMinter);
        minter = newMinter;
    }
    
    function setMintRate(uint256 newRate) external onlyOwner {
        emit ProductionRateUpdated(mintRatePerSecond, newRate);
        mintRatePerSecond = newRate;
    }
    
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid owner");
        owner = newOwner;
    }
    
    // View functions
    function pendingMint() external view returns (uint256) {
        uint256 elapsed = block.timestamp - lastMintTimestamp;
        return (mintRatePerSecond * elapsed) / 1e18;
    }
}
