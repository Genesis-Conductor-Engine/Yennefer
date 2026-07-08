// SPDX-License-Identifier: MIT
pragma solidity ^0.8.32;

// Minimal interfaces for Aerodrome (Velodrome V2 fork) on Base.
// Signatures validated against live contracts on 2026-06-09:
//   Router  0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43  (poolFor/getReserves confirmed)
//   Factory 0x420DD381b31aEf6683db6B902084cB0FFECe40Da
//   Voter   0x16613524e02ad97eDfeF371bC883F2F5d6C480A5  (gauges() confirmed)

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function decimals() external view returns (uint8);
    function symbol() external view returns (string memory);
    function totalSupply() external view returns (uint256);
}

interface IAerodromeRouter {
    function defaultFactory() external view returns (address);
    function poolFor(address tokenA, address tokenB, bool stable, address _factory)
        external view returns (address);
    function getReserves(address tokenA, address tokenB, bool stable, address _factory)
        external view returns (uint256 reserveA, uint256 reserveB);
    function quoteAddLiquidity(
        address tokenA, address tokenB, bool stable, address _factory,
        uint256 amountADesired, uint256 amountBDesired
    ) external view returns (uint256 amountA, uint256 amountB, uint256 liquidity);
    function addLiquidity(
        address tokenA, address tokenB, bool stable,
        uint256 amountADesired, uint256 amountBDesired,
        uint256 amountAMin, uint256 amountBMin,
        address to, uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB, uint256 liquidity);
    function removeLiquidity(
        address tokenA, address tokenB, bool stable,
        uint256 liquidity, uint256 amountAMin, uint256 amountBMin,
        address to, uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB);
}

interface IPoolFactory {
    function getPool(address tokenA, address tokenB, bool stable) external view returns (address);
    function createPool(address tokenA, address tokenB, bool stable) external returns (address);
}

interface IPool {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function stable() external view returns (bool);
    function getReserves() external view returns (uint256 reserve0, uint256 reserve1, uint256 blockTimestampLast);
    function totalSupply() external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
}

interface IVoter {
    function gauges(address pool) external view returns (address);
}

interface IGauge {
    function deposit(uint256 amount) external;
    function withdraw(uint256 amount) external;
    function getReward(address account) external;
    function earned(address account) external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
    function stakingToken() external view returns (address);
}
