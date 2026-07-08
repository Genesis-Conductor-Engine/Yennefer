// SPDX-License-Identifier: MIT
pragma solidity ^0.8.32;

import {Script, console} from "forge-std/Script.sol";
import {IAerodromeRouter, IPool, IPoolFactory, IERC20} from "../src/interfaces/IAerodrome.sol";

/// @notice Add liquidity to the existing wQFLOP/WETH volatile pool, with in-script hard caps.
/// Runs as a fork-simulation by default; pass --broadcast (and a signer via --account/--private-key)
/// to execute live. The signer is provided on the CLI; no key is ever read from source.
///
/// Required env (wei): WETH_AMOUNT, WQFLOP_AMOUNT, LP_OWNER (recipient = signer address)
/// Optional env:       MAX_WETH_PER_TX (wei, default 0.02e18), SLIPPAGE_BPS (default 100)
contract AddLiquidity is Script {
    address constant ROUTER = 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;
    address constant WETH   = 0x4200000000000000000000000000000000000006;
    address constant WQFLOP = 0x69262A2D7c92c074729823B654fE7E4Cdb749747;
    bool    constant STABLE = false;

    function run() external {
        uint256 wethAmount   = vm.envUint("WETH_AMOUNT");
        uint256 wqflopAmount = vm.envUint("WQFLOP_AMOUNT");
        uint256 maxWethTx    = vm.envOr("MAX_WETH_PER_TX", uint256(0.02 ether));
        uint256 slippageBps  = vm.envOr("SLIPPAGE_BPS", uint256(100));
        address to           = vm.envAddress("LP_OWNER");

        // ---- HARD CAPS (revert the whole tx, in sim or live) ----
        require(wethAmount > 0 && wqflopAmount > 0, "amounts must be > 0");
        require(wethAmount <= maxWethTx, "CAP: WETH per tx exceeds max_weth_per_tx");
        require(slippageBps <= 500, "CAP: slippage too high (>5%)");

        uint256 wethMin   = wethAmount   - (wethAmount   * slippageBps / 10_000);
        uint256 wqflopMin = wqflopAmount - (wqflopAmount * slippageBps / 10_000);

        require(IERC20(WETH).balanceOf(to)   >= wethAmount,   "insufficient WETH balance");
        require(IERC20(WQFLOP).balanceOf(to) >= wqflopAmount, "insufficient wQFLOP balance");

        console.log("LP recipient :", to);
        console.log("add wQFLOP    :", wqflopAmount);
        console.log("add WETH      :", wethAmount);
        console.log("min wQFLOP    :", wqflopMin);
        console.log("min WETH      :", wethMin);

        vm.startBroadcast();
        if (IERC20(WETH).allowance(to, ROUTER)   < wethAmount)   IERC20(WETH).approve(ROUTER, type(uint256).max);
        if (IERC20(WQFLOP).allowance(to, ROUTER) < wqflopAmount) IERC20(WQFLOP).approve(ROUTER, type(uint256).max);
        (uint256 aWq, uint256 aWeth, uint256 liq) = IAerodromeRouter(ROUTER).addLiquidity(
            WQFLOP, WETH, STABLE,
            wqflopAmount, wethAmount,
            wqflopMin, wethMin,
            to, block.timestamp + 600
        );
        vm.stopBroadcast();

        console.log("added wQFLOP :", aWq);
        console.log("added WETH   :", aWeth);
        console.log("LP minted    :", liq);
    }
}
