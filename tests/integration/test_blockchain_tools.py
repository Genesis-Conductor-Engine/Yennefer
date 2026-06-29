#!/usr/bin/env python3
"""
Test script for blockchain wallet analysis tools.
Tests all 4 tools with Vitalik Buterin's Ethereum address.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from blockchain.blockchain_tools import get_analyzer

# Vitalik's famous Ethereum address
VITALIK_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

async def test_query_wallet_balance():
    """Test 1: Query wallet balance"""
    print("\n" + "="*80)
    print("TEST 1: Query Wallet Balance")
    print("="*80)
    
    analyzer = get_analyzer()
    result = await analyzer.query_wallet_balance(VITALIK_ADDRESS)
    
    print(f"\nAddress: {result.get('address', 'N/A')}")
    print(f"Balance: {result.get('balance_eth', 0):.4f} ETH")
    print(f"Transaction Count: {result.get('transaction_count', 0):,}")
    print(f"Current Block: {result.get('current_block', 0):,}")
    print(f"Gas Price: {result.get('current_gas_price_gwei', 0):.2f} Gwei")
    print(f"Is Contract: {result.get('is_contract', False)}")
    
    if result.get('recent_transactions'):
        print(f"\nRecent Transactions: {len(result['recent_transactions'])}")
        for i, tx in enumerate(result['recent_transactions'][:3], 1):
            print(f"  {i}. Block {tx['block']}: {tx['value_eth']:.4f} ETH")
    
    print(f"\nStatus: {'✅ SUCCESS' if result.get('status') == 'success' else '❌ FAILED'}")
    return result

async def test_analyze_portfolio_risk():
    """Test 2: Analyze portfolio risk metrics"""
    print("\n" + "="*80)
    print("TEST 2: Analyze Portfolio Risk")
    print("="*80)
    
    analyzer = get_analyzer()
    result = await analyzer.analyze_portfolio_risk(VITALIK_ADDRESS, historical_blocks=500)
    
    print(f"\nAddress: {result.get('address', 'N/A')}")
    print(f"Samples Analyzed: {result.get('samples_analyzed', 0)}")
    print(f"Blocks Analyzed: {result.get('blocks_analyzed', 0)}")
    print(f"Time Range: {result.get('time_range_hours', 0):.1f} hours")
    
    if result.get('status') == 'success':
        print(f"\nRisk Metrics:")
        print(f"  Volatility: {result.get('volatility', 0):.6f}")
        print(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0):.4f}")
        print(f"  Max Drawdown: {result.get('max_drawdown', 0)*100:.2f}%")
        print(f"  Value at Risk (95%): {result.get('value_at_risk_95', 0)*100:.2f}%")
        print(f"  Risk Level: {result.get('risk_level', 'UNKNOWN')}")
        
        balance_range = result.get('balance_range', {})
        print(f"\nBalance Range:")
        print(f"  Min: {balance_range.get('min', 0):.4f} ETH")
        print(f"  Max: {balance_range.get('max', 0):.4f} ETH")
        print(f"  Current: {balance_range.get('current', 0):.4f} ETH")
    
    print(f"\nStatus: {'✅ SUCCESS' if result.get('status') == 'success' else '❌ FAILED'}")
    return result

async def test_simulate_rebalancing():
    """Test 3: Monte Carlo portfolio rebalancing simulation"""
    print("\n" + "="*80)
    print("TEST 3: Simulate Portfolio Rebalancing")
    print("="*80)
    
    analyzer = get_analyzer()
    
    current_allocation = {"ETH": 0.7, "BTC": 0.3}
    target_allocation = {"ETH": 0.5, "BTC": 0.3, "USDC": 0.2}
    
    print(f"\nCurrent Allocation: {current_allocation}")
    print(f"Target Allocation: {target_allocation}")
    print(f"Simulations: 1000")
    print(f"Time Horizon: 30 days")
    
    result = await analyzer.simulate_rebalancing(
        current_allocation,
        target_allocation,
        simulations=1000,
        time_horizon_days=30
    )
    
    if result.get('status') == 'success':
        current = result.get('current_portfolio', {})
        rebalanced = result.get('rebalanced_portfolio', {})
        
        print(f"\nCurrent Portfolio:")
        print(f"  Expected Value: {current.get('expected_value', 0):.4f}")
        print(f"  Std Dev: {current.get('std_dev', 0):.4f}")
        print(f"  Sharpe Ratio: {current.get('sharpe_ratio', 0):.4f}")
        print(f"  VaR 95%: {current.get('value_at_risk_95', 0):.4f}")
        
        print(f"\nRebalanced Portfolio:")
        print(f"  Expected Value: {rebalanced.get('expected_value', 0):.4f}")
        print(f"  Std Dev: {rebalanced.get('std_dev', 0):.4f}")
        print(f"  Sharpe Ratio: {rebalanced.get('sharpe_ratio', 0):.4f}")
        print(f"  VaR 95%: {rebalanced.get('value_at_risk_95', 0):.4f}")
        
        improvement = result.get('improvement', {})
        print(f"\nImprovement:")
        print(f"  Expected Return Delta: {improvement.get('expected_return_delta', 0):.4f}")
        print(f"  Sharpe Delta: {improvement.get('sharpe_delta', 0):.4f}")
        print(f"  Recommendation: {improvement.get('recommendation', 'N/A')}")
        
        qaoa = result.get('qaoa_quantum_optimization', {})
        print(f"\nQAOA Quantum Optimization:")
        print(f"  Energy: {qaoa.get('qaoa_energy', 0):.2f}")
        print(f"  Purity: {qaoa.get('purity', 0):.2f}")
        print(f"  Quantum Advantage: {qaoa.get('quantum_advantage', 'N/A')}")
        
        actions = result.get('rebalancing_actions', [])
        if actions:
            print(f"\nRebalancing Actions ({len(actions)}):")
            for action in actions:
                print(f"  {action['action']} {action['amount_percent']:.1f}% of {action['asset']}")
    
    print(f"\nStatus: {'✅ SUCCESS' if result.get('status') == 'success' else '❌ FAILED'}")
    return result

async def test_optimize_gas_fees():
    """Test 4: Optimize gas fees"""
    print("\n" + "="*80)
    print("TEST 4: Optimize Gas Fees")
    print("="*80)
    
    analyzer = get_analyzer()
    
    for urgency in ["low", "medium", "high"]:
        print(f"\n--- Urgency: {urgency.upper()} ---")
        result = await analyzer.optimize_gas_fees(urgency)
        
        if result.get('status') == 'success':
            prices = result.get('current_gas_prices_gwei', {})
            print(f"Current Gas Prices:")
            print(f"  Safe: {prices.get('safe', 0):.2f} Gwei")
            print(f"  Standard: {prices.get('standard', 0):.2f} Gwei")
            print(f"  Fast: {prices.get('fast', 0):.2f} Gwei")
            
            recommended = result.get('recommended', {})
            print(f"\nRecommended ({urgency}):")
            print(f"  Gas Price: {recommended.get('gas_price_gwei', 0):.2f} Gwei")
            print(f"  Confirmation Time: {recommended.get('expected_confirmation_time', 'N/A')}")
            
            cost = result.get('cost_estimate', {})
            print(f"\nCost Estimate (Standard Transfer):")
            print(f"  ETH: {cost.get('standard_transfer_eth', 0):.6f}")
            print(f"  USD: ${cost.get('standard_transfer_usd', 0):.2f}")
            
            timing = result.get('optimal_timing', {})
            print(f"\nOptimal Timing:")
            print(f"  Window: {timing.get('window', 'N/A')}")
            print(f"  Hour UTC: {timing.get('current_hour_utc', 0)}")
            print(f"  Is Weekend: {timing.get('is_weekend', False)}")
            
            savings = result.get('savings_opportunity', {})
            print(f"\nSavings Opportunity:")
            print(f"  Potential Savings: {savings.get('current_vs_optimal_percent', 0):.1f}%")
            print(f"  Recommendation: {savings.get('recommendation', 'N/A')}")
    
    print(f"\nStatus: ✅ SUCCESS")
    return result

async def main():
    """Run all blockchain tool tests"""
    print("\n" + "🚀"*40)
    print("BLOCKCHAIN WALLET ANALYSIS TOOLS TEST SUITE")
    print("Testing with Vitalik Buterin's Address")
    print("🚀"*40)
    
    try:
        # Test 1: Query Wallet Balance
        balance_result = await test_query_wallet_balance()
        
        # Test 2: Analyze Portfolio Risk
        risk_result = await test_analyze_portfolio_risk()
        
        # Test 3: Simulate Rebalancing
        rebalancing_result = await test_simulate_rebalancing()
        
        # Test 4: Optimize Gas Fees
        gas_result = await test_optimize_gas_fees()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        tests = [
            ("Query Wallet Balance", balance_result.get('status') == 'success'),
            ("Analyze Portfolio Risk", risk_result.get('status') == 'success'),
            ("Simulate Rebalancing", rebalancing_result.get('status') == 'success'),
            ("Optimize Gas Fees", gas_result.get('status') == 'success')
        ]
        
        passed = sum(1 for _, success in tests if success)
        total = len(tests)
        
        for test_name, success in tests:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
        
        if passed == total:
            print("\n🎉 All blockchain tools working successfully!")
            return 0
        else:
            print("\n⚠️  Some tests failed. Check errors above.")
            return 1
    
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
