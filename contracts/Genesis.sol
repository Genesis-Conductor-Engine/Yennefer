// SPDX-License-Identifier: MIT
pragma solidity ^0.8.32;

contract Genesis {
    string public name = 'Genesis Conductor';
    address public owner;
    bool public conductorActive;
    uint256 public epochStartTime;
    
    event CREDIT_PURCHASE(address indexed buyer, uint256 amount);
    event ConductorStarted(address indexed operator, uint256 timestamp);
    event EpochAdvanced(uint256 indexed epoch, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        conductorActive = false;
    }

    function startConductor() external onlyOwner {
        require(!conductorActive, "Already active");
        conductorActive = true;
        epochStartTime = block.timestamp;
        emit ConductorStarted(msg.sender, block.timestamp);
    }

    function emitEvent() public {
        emit CREDIT_PURCHASE(msg.sender, 1);
    }

    function advanceEpoch(uint256 epoch) external onlyOwner {
        require(conductorActive, "Conductor not active");
        emit EpochAdvanced(epoch, block.timestamp);
    }
}
