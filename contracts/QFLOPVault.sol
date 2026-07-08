// SPDX-License-Identifier: MIT
pragma solidity ^0.8.32;

/**
 * @title QFLOP Vault
 * @notice Simple vault for collecting and distributing ETH
 */
contract QFLOPVault {
    address public owner;
    address public qflopToken;
    
    event Deposit(address indexed from, uint256 amount);
    event Withdraw(address indexed to, uint256 amount);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor(address _qflopToken) {
        owner = msg.sender;
        qflopToken = _qflopToken;
    }
    
    receive() external payable {
        emit Deposit(msg.sender, msg.value);
    }
    
    function withdraw(address payable to, uint256 amount) external onlyOwner {
        uint256 bal = address(this).balance;
        uint256 withdrawAmount = amount == 0 ? bal : amount;
        require(withdrawAmount <= bal, "Insufficient balance");
        (bool success, ) = to.call{value: withdrawAmount}("");
        require(success, "Transfer failed");
        emit Withdraw(to, withdrawAmount);
    }
    
    function balance() external view returns (uint256) {
        return address(this).balance;
    }
}
