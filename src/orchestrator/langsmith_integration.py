"""
LangSmith Integration for Diamond Node Unified Inference System

Provides tracing and monitoring for the Claude orchestrator using LangSmith.
Complements AppSignal (system metrics) with LLM-specific observability.
"""

import os
from typing import Optional, Dict, Any
from functools import wraps
import asyncio

try:
    from langsmith import Client, traceable
    from langsmith.run_helpers import get_current_run_tree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Dummy decorator if langsmith not installed
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if not args else decorator(args[0])


class LangSmithTracer:
    """
    LangSmith tracing wrapper for Claude orchestrator.
    
    Provides:
    - LLM call tracing (tokens, latency, cost)
    - Tool execution tracing
    - Chain/agent workflow tracing
    - Error tracking
    - Performance analytics
    """
    
    def __init__(self):
        self.enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
        self.client = None
        
        if self.enabled and LANGSMITH_AVAILABLE:
            try:
                self.client = Client(
                    api_key=os.getenv("LANGSMITH_API_KEY"),
                    api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
                )
                self.project = os.getenv("LANGSMITH_PROJECT", "diamondnode")
                print(f"✓ LangSmith tracing enabled (project: {self.project})")
            except Exception as e:
                print(f"⚠ LangSmith initialization failed: {e}")
                self.enabled = False
        elif self.enabled and not LANGSMITH_AVAILABLE:
            print("⚠ LangSmith tracing requested but langsmith package not installed")
            self.enabled = False
    
    @staticmethod
    def trace_llm_call(name: str = "claude_chat"):
        """
        Decorator to trace LLM calls (Claude API).
        
        Usage:
            @tracer.trace_llm_call("claude_reasoning")
            async def chat(self, message: str):
                ...
        """
        def decorator(func):
            if not LANGSMITH_AVAILABLE:
                return func
            
            @traceable(name=name, run_type="llm")
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            @traceable(name=name, run_type="llm")
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    @staticmethod
    def trace_tool(tool_name: str):
        """
        Decorator to trace tool executions.
        
        Usage:
            @tracer.trace_tool("cuda_q_qaoa")
            async def run_cuda_q_qaoa(self, shots: int):
                ...
        """
        def decorator(func):
            if not LANGSMITH_AVAILABLE:
                return func
            
            @traceable(name=f"tool_{tool_name}", run_type="tool")
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            @traceable(name=f"tool_{tool_name}", run_type="tool")
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    @staticmethod
    def trace_chain(name: str = "orchestrator_chain"):
        """
        Decorator to trace multi-step chains/workflows.
        
        Usage:
            @tracer.trace_chain("blockchain_portfolio_analysis")
            async def analyze_and_rebalance(self, address: str):
                balance = await self.query_wallet_balance(address)
                risk = await self.analyze_portfolio_risk(address)
                rebalancing = await self.simulate_rebalancing(...)
                return {"balance": balance, "risk": risk, "rebalancing": rebalancing}
        """
        def decorator(func):
            if not LANGSMITH_AVAILABLE:
                return func
            
            @traceable(name=name, run_type="chain")
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            @traceable(name=name, run_type="chain")
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def add_metadata(self, metadata: Dict[str, Any]):
        """
        Add metadata to the current trace.
        
        Args:
            metadata: Key-value pairs to attach to the trace
        
        Example:
            tracer.add_metadata({
                "vram_used_mb": 2500,
                "hamiltonian": 6.2,
                "gpu_temp": 72
            })
        """
        if not self.enabled or not LANGSMITH_AVAILABLE:
            return
        
        try:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.extra = {**(run_tree.extra or {}), **metadata}
        except Exception as e:
            print(f"⚠ Failed to add metadata to LangSmith trace: {e}")
    
    def log_feedback(self, run_id: str, score: float, comment: Optional[str] = None):
        """
        Log feedback for a traced run.
        
        Args:
            run_id: Run ID from LangSmith
            score: Numeric score (0.0-1.0 for binary, any range for continuous)
            comment: Optional human-readable feedback
        
        Example:
            tracer.log_feedback(run_id, score=0.95, comment="Excellent rebalancing recommendation")
        """
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.create_feedback(
                run_id=run_id,
                key="user_score",
                score=score,
                comment=comment
            )
        except Exception as e:
            print(f"⚠ Failed to log feedback to LangSmith: {e}")


# Global tracer instance
tracer = LangSmithTracer()


# Convenience decorators for quick usage
trace_llm = tracer.trace_llm_call
trace_tool = tracer.trace_tool
trace_chain = tracer.trace_chain


def get_tracer() -> LangSmithTracer:
    """Get the global LangSmith tracer instance."""
    return tracer


# Example usage functions
async def example_traced_llm_call():
    """Example: Trace a Claude API call"""
    
    @trace_llm("example_claude_call")
    async def call_claude(message: str) -> str:
        # Simulate Claude API call
        tracer.add_metadata({
            "model": "claude-opus-4-7",
            "thinking": "adaptive",
            "effort": "xhigh"
        })
        return f"Response to: {message}"
    
    return await call_claude("What is the meaning of life?")


async def example_traced_tool():
    """Example: Trace a tool execution"""
    
    @trace_tool("vram_query")
    async def query_vram() -> Dict[str, Any]:
        tracer.add_metadata({
            "vram_used_mb": 2500,
            "vram_total_mb": 4096,
            "hamiltonian": 6.1
        })
        return {"vram_used": 2500, "vram_total": 4096}
    
    return await query_vram()


async def example_traced_chain():
    """Example: Trace a multi-step workflow"""
    
    @trace_chain("portfolio_optimization_workflow")
    async def optimize_portfolio(address: str) -> Dict[str, Any]:
        # Step 1: Query balance (would be traced separately if decorated)
        balance = {"eth": 5.6187, "usd_value": 15000}
        
        # Step 2: Analyze risk
        risk = {"volatility": 0.224, "sharpe": -0.229}
        
        # Step 3: QAOA optimization
        rebalancing = {"action": "REBALANCE", "expected_return": 0.0127}
        
        tracer.add_metadata({
            "address": address,
            "balance_usd": balance["usd_value"],
            "risk_score": risk["sharpe"]
        })
        
        return {
            "balance": balance,
            "risk": risk,
            "rebalancing": rebalancing
        }
    
    return await optimize_portfolio("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")


if __name__ == "__main__":
    """Test LangSmith integration"""
    import asyncio
    
    async def test():
        print("Testing LangSmith integration...")
        print(f"Enabled: {tracer.enabled}")
        print(f"Available: {LANGSMITH_AVAILABLE}")
        
        if tracer.enabled:
            print("\n1. Testing LLM call tracing...")
            result = await example_traced_llm_call()
            print(f"Result: {result}")
            
            print("\n2. Testing tool tracing...")
            result = await example_traced_tool()
            print(f"Result: {result}")
            
            print("\n3. Testing chain tracing...")
            result = await example_traced_chain()
            print(f"Result: {result}")
            
            print("\n✓ All tests complete. Check LangSmith dashboard:")
            print(f"  https://smith.langchain.com/o/diamondnode/projects/p/{tracer.project}")
        else:
            print("\n⚠ LangSmith tracing not enabled. Set LANGSMITH_TRACING=true to enable.")
    
    asyncio.run(test())
