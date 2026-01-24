// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract GenesisV3 {
    string public name = 'Genesis Conductor V3';
    address public owner;
    bool public conductorActive;
    uint256 public epochStartTime;
    
    event CREDIT_PURCHASE(address indexed buyer, uint256 amount);
    event ConductorStarted(address indexed operator, uint256 timestamp);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event AssetReceived(address indexed from, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _initialOwner) {
        owner = _initialOwner;
        conductorActive = false;
        emit OwnershipTransferred(address(0), _initialOwner);
    }

    function startConductor() external onlyOwner {
        conductorActive = true;
        epochStartTime = block.timestamp;
        emit ConductorStarted(msg.sender, block.timestamp);
    }

    function emitEvent() external onlyOwner {
        emit CREDIT_PURCHASE(msg.sender, block.timestamp);
    }
    
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
    
    receive() external payable {
        emit AssetReceived(msg.sender, msg.value);
    }
    
    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
}
