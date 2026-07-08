// SPDX-License-Identifier: MIT
pragma solidity ^0.8.32;

import {Script, console} from "forge-std/Script.sol";
import {IPoolFactory, IPool, IVoter, IERC20} from "../src/interfaces/IAerodrome.sol";

/// @notice Read-only status of the wQFLOP/WETH Aerodrome pool + optional owner position.
/// Usage: forge script script/Status.s.sol --rpc-url base   (optionally LP_OWNER=0x..)
contract Status is Script {
    address constant FACTORY = 0x420DD381b31aEf6683db6B902084cB0FFECe40Da;
    address constant VOTER   = 0x16613524e02ad97eDfeF371bC883F2F5d6C480A5;
    address constant WETH    = 0x4200000000000000000000000000000000000006;
    address constant WQFLOP  = 0x69262A2D7c92c074729823B654fE7E4Cdb749747;
    uint256 constant MIN_WETH_RESERVE = 1e15; // 0.001 WETH; below => DEGENERATE

    function run() external view {
        address pool = IPoolFactory(FACTORY).getPool(WQFLOP, WETH, false);
        console.log("pool:", pool);
        require(pool != address(0), "pool not found");

        (uint256 r0, uint256 r1,) = IPool(pool).getReserves();
        address t0 = IPool(pool).token0();
        (uint256 wethRes, uint256 wqRes) = t0 == WETH ? (r0, r1) : (r1, r0);
        console.log("WETH reserve (wei):  ", wethRes);
        console.log("wQFLOP reserve (wei):", wqRes);
        if (wqRes > 0) {
            console.log("price wQFLOP->WETH (wei per 1e18 wQFLOP):", (wethRes * 1e18) / wqRes);
        }
        if (wethRes < MIN_WETH_RESERVE) {
            console.log(">>> POOL DEGENERATE: WETH reserve below floor; proportional add would donate value. Default = HOLD.");
        }

        address gauge = IVoter(VOTER).gauges(pool);
        console.log("gauge (0x0 = none):", gauge);
        console.log("pool LP totalSupply:", IPool(pool).totalSupply());

        address owner = vm.envOr("LP_OWNER", address(0));
        if (owner != address(0)) {
            console.log("owner:", owner);
            console.log("  owner LP balance:", IPool(pool).balanceOf(owner));
            console.log("  owner WETH (wei):", IERC20(WETH).balanceOf(owner));
            console.log("  owner wQFLOP    :", IERC20(WQFLOP).balanceOf(owner));
            console.log("  owner ETH (wei) :", owner.balance);
        }
    }
}
