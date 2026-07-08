// SPDX-License-Identifier: MIT
pragma solidity ^0.8.32;

/**
 * @title QFLOP Token V2
 * @notice ERC-20 token backed by GPU quantum compute production
 * @dev Includes withdraw functionality for self-funding
 */
contract QFLOPTokenV2 {
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
    uint256 public mintRatePerSecond;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Mint(address indexed to, uint256 amount, uint256 qflopsProduced);
    event MinterUpdated(address indexed oldMinter, address indexed newMinter);
    event ProductionRateUpdated(uint256 oldRate, uint256 newRate);
    event Withdraw(address indexed to, uint256 amount);
    event Received(address indexed from, uint256 amount);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    modifier onlyMinter() {
        require(msg.sender == minter || msg.sender == owner, "Not authorized to mint");
        _;
    }
    
    constructor(address _minter, uint256 _initialSupply) {
        owner = msg.sender;
        minter = _minter;
        lastMintTimestamp = block.timestamp;
        mintRatePerSecond = 3000 * 1e18;
        
        // Mint initial supply to owner
        if (_initialSupply > 0) {
            totalSupply = _initialSupply;
            balanceOf[msg.sender] = _initialSupply;
            emit Transfer(address(0), msg.sender, _initialSupply);
        }
    }
    
    // Allow contract to receive ETH
    receive() external payable {
        emit Received(msg.sender, msg.value);
    }
    
    fallback() external payable {
        emit Received(msg.sender, msg.value);
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
     */
    function mintFromProduction(address to, uint256 qflopsProduced) external onlyMinter {
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
     * @notice Mint tokens based on time elapsed
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
    
    /**
     * @notice Direct mint function for owner
     */
    function mint(address to, uint256 amount) external onlyMinter {
        totalSupply += amount;
        balanceOf[to] += amount;
        lastMintTimestamp = block.timestamp;
        emit Transfer(address(0), to, amount);
    }
    
    /**
     * @notice Withdraw ETH from contract
     * @param to Recipient address
     * @param amount Amount to withdraw (0 = all)
     */
    function withdraw(address payable to, uint256 amount) external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH to withdraw");
        
        uint256 withdrawAmount = amount == 0 ? balance : amount;
        require(withdrawAmount <= balance, "Insufficient contract balance");
        
        (bool success, ) = to.call{value: withdrawAmount}("");
        require(success, "ETH transfer failed");
        
        emit Withdraw(to, withdrawAmount);
    }
    
    /**
     * @notice Withdraw all ETH to owner
     */
    function withdrawAll() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH to withdraw");
        
        (bool success, ) = payable(owner).call{value: balance}("");
        require(success, "ETH transfer failed");
        
        emit Withdraw(owner, balance);
    }
    
    /**
     * @notice Emergency token recovery
     */
    function recoverTokens(address token, uint256 amount) external onlyOwner {
        require(token != address(this), "Cannot recover own tokens");
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSignature("transfer(address,uint256)", owner, amount)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "Token recovery failed");
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
    
    function pendingMint() external view returns (uint256) {
        uint256 elapsed = block.timestamp - lastMintTimestamp;
        return (mintRatePerSecond * elapsed) / 1e18;
    }
    
    function contractBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
