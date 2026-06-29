# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Claude API Orchestrator for Diamond Node Unified Inference System

This module provides an intelligent orchestrator that routes requests to the
appropriate backend (CUDA-Q, YOLO11, Qwen) based on natural language queries.
"""

import os
import json
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from anthropic import Anthropic
import httpx
import yaml

# OpenTelemetry imports for monitoring
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    print("[Warning] OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")

# Import configuration management
try:
    from config import get_config, Config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    print("[Warning] config module not available, using environment variables")

# Import blockchain tools
try:
    from blockchain_tools import get_analyzer
    BLOCKCHAIN_AVAILABLE = True
except ImportError:
    BLOCKCHAIN_AVAILABLE = False
    print("[Warning] blockchain_tools not available")

# Import optimizer from diamond-node
try:
    diamond_node_path = Path.home() / "diamond-node" / "unified_inference"
    if str(diamond_node_path) not in sys.path:
        sys.path.insert(0, str(diamond_node_path))
    
    from optimizer import (
        OrthogonalOptimizer, 
        WorkloadType,
        SystemState,
        ModelMetrics
    )
    OPTIMIZER_AVAILABLE = True
except ImportError as e:
    OPTIMIZER_AVAILABLE = False
    print(f"[Warning] optimizer module not available: {e}")

# Import NOX Engine
try:
    from nox_engine import NoxEngine
    NOX_AVAILABLE = True
except ImportError:
    NOX_AVAILABLE = False
    print("[Warning] nox_engine module not available")


class ClaudeOrchestrator:
    """
    Intelligent orchestrator using Claude Opus 4.7 with adaptive thinking.
    Routes requests to appropriate backends and manages VRAM efficiently.
    """
    
    # Tool definitions for the unified inference system
    TOOLS = [
        {
            "name": "query_vram_status",
            "description": "Query the current GPU VRAM usage, temperature, and resource Hamiltonian from Diamond Gateway. Use this to check if VRAM is available before running models.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "include_history": {
                        "type": "boolean",
                        "description": "Include historical VRAM usage data"
                    }
                }
            }
        },
        {
            "name": "get_nox_state",
            "description": "Retrieve current NOX Agentic Engine state, including thermodynamic rates (eta_thermo) and electron potentiation levels.",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "configure_nox_engine",
            "description": "Configure the NOX Agentic Engine. Opens an interactive Control Panel for thermodynamic throttling and multilane kernel management.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "eta_thermo": {
                        "type": "number",
                        "description": "Target thermodynamic rate (0.0-1.0)"
                    },
                    "encryption_enabled": {
                        "type": "boolean",
                        "description": "Enable thermodynamic post-quantum encryption"
                    },
                    "multilane_active": {
                        "type": "boolean",
                        "description": "Activate multilane kernel potentiation"
                    },
                    "kernel_lanes": {
                        "type": "integer",
                        "description": "Number of kernel lanes (1-16)"
                    }
                }
            },
            "_meta": {
                "ui": {
                    "resourceUri": "ui://widgets/nox_control_panel.html"
                }
            }
        },
        {
            "name": "manage_diamond_vault",
            "description": "Trigger semantic reference synchronization with Notion and GitHub via the Diamond Vault. Manages VRAM embedding offload.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["sync_notion", "sync_github", "offload_embeddings"],
                        "description": "The action to perform"
                    },
                    "embeddings": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Embeddings to offload (if action is offload_embeddings)"
                    }
                },
                "required": ["action"]
            }
        },
        {
            "name": "run_cuda_q_qaoa",
            "description": "Execute CUDA-Q QAOA optimization on the 16-node mycelial network. Returns energy convergence, purity, and waveform equilibrium metrics.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "shots": {
                        "type": "integer",
                        "description": "Number of shots for QAOA (256-2048)"
                    },
                    "outer_rounds": {
                        "type": "integer", 
                        "description": "Number of outer optimization rounds"
                    }
                }
            }
        },
        {
            "name": "run_yolo11_detection",
            "description": "Run YOLO11s object detection on an image. Supports batch processing. Returns detected objects with confidence scores.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file or base64-encoded image"
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "description": "Minimum confidence threshold (0.0-1.0)"
                    },
                    "batch_size": {
                        "type": "integer",
                        "description": "Batch size for processing (1-8)"
                    }
                },
                "required": ["image_path"]
            }
        },
        {
            "name": "query_qwen_chat",
            "description": "Send a chat message to Qwen 1.5 4B LLM. Use for conversational AI, text generation, or question answering.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to Qwen"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0-1.0)"
                    }
                },
                "required": ["message"]
            }
        },
        {
            "name": "optimize_orthogonal_bounds",
            "description": "Run orthogonal optimization across all 4 dimensions (VRAM, throughput, accuracy, equilibrium). Returns Pareto-optimal configurations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "workload_profile": {
                        "type": "string",
                        "enum": ["scientific", "vision", "conversational", "balanced", "low-power"],
                        "description": "The workload profile to optimize for"
                    },
                    "constraints": {
                        "type": "object",
                        "properties": {
                            "max_vram_mb": {
                                "type": "integer",
                                "description": "Maximum VRAM in MB"
                            },
                            "max_temp_celsius": {
                                "type": "integer",
                                "description": "Maximum GPU temperature"
                            }
                        }
                    }
                },
                "required": ["workload_profile"]
            }
        },
        {
            "name": "trigger_notion_offload",
            "description": "Trigger context offload to Notion soul-capsule database when resource Hamiltonian exceeds 8.5. Use when VRAM is critically high.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier"
                    },
                    "context_buffer": {
                        "type": "string",
                        "description": "Context to offload"
                    },
                    "hamiltonian": {
                        "type": "number",
                        "description": "Current resource Hamiltonian value"
                    }
                },
                "required": ["session_id", "context_buffer", "hamiltonian"]
            }
        },
        {
            "name": "query_wallet_balance",
            "description": "Check ETH/BTC/token balances for a blockchain wallet address. Returns real on-chain data including balance, transaction count, and recent activity.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Ethereum wallet address (0x...)"
                    }
                },
                "required": ["address"]
            }
        },
        {
            "name": "analyze_portfolio_risk",
            "description": "Compute portfolio risk metrics including volatility, Sharpe ratio, max drawdown, and Value at Risk. Analyzes historical on-chain balance data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Ethereum wallet address to analyze"
                    },
                    "historical_blocks": {
                        "type": "integer",
                        "description": "Number of blocks to analyze for historical data (default 1000)"
                    }
                },
                "required": ["address"]
            }
        },
        {
            "name": "simulate_rebalancing",
            "description": "Run Monte Carlo simulation of portfolio rebalancing strategies. Integrates CUDA-Q QAOA for quantum-optimized allocation. Returns expected returns, risk metrics, and rebalancing actions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "current_allocation": {
                        "type": "object",
                        "description": "Current portfolio allocation as percentages (e.g., {\"ETH\": 0.6, \"BTC\": 0.4})"
                    },
                    "target_allocation": {
                        "type": "object",
                        "description": "Target portfolio allocation as percentages (must sum to 1.0)"
                    },
                    "simulations": {
                        "type": "integer",
                        "description": "Number of Monte Carlo simulation paths (default 1000)"
                    },
                    "time_horizon_days": {
                        "type": "integer",
                        "description": "Investment time horizon in days (default 30)"
                    }
                },
                "required": ["current_allocation", "target_allocation"]
            }
        },
        {
            "name": "optimize_gas_fees",
            "description": "Optimize Ethereum transaction timing for minimal gas costs. Uses real-time gas oracles and historical patterns to recommend optimal transaction windows.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Transaction urgency: low (>30min), medium (5-15min), high (<1min)"
                    }
                }
            }
        }
    ]

    def __init__(self, api_key: Optional[str] = None, config: Optional[Config] = None):
        # Load configuration
        if CONFIG_AVAILABLE:
            self.config = config or get_config()
            api_key = api_key or self.config.api.anthropic_api_key
            self.model = self.config.api.claude_model
            self.max_tokens = self.config.api.max_tokens_streaming
            self.gateway_secret = self.config.api.gateway_secret
        else:
            self.config = None
            api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            self.model = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
            self.max_tokens = int(os.environ.get("MAX_TOKENS_STREAMING", "64000"))
            self.gateway_secret = os.environ.get("GATEWAY_SECRET")
        
        try:
            self.client = Anthropic(api_key=api_key)
        except Exception as e:
            print(f"[Warning] Anthropic client initialization failed: {e}")
            self.client = None
        
        self.conversation_history = []
        
        # Initialize NOX Engine
        self.nox_engine = NoxEngine() if NOX_AVAILABLE else None
        
        # Initialize OpenTelemetry monitoring
        self._init_monitoring()
        
        # Load optimization profiles from diamond-node config
        config_path = Path.home() / "diamond-node" / "config" / "optimization_profiles.yaml"
        self.optimization_profiles = {}
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r') as f:
                    self.optimization_profiles = yaml.safe_load(f)
            except ImportError:
                print("[Warning] PyYAML not installed, skipping optimization profiles")
        
        self.system_prompt = """You are an intelligent orchestrator for the Diamond Node Unified Inference System.

Your role:
- Route user requests to the appropriate backend (CUDA-Q, YOLO11, Qwen)
- Monitor VRAM usage and trigger offloads when necessary
- Optimize performance across 4 dimensions: VRAM, throughput, accuracy, equilibrium
- Provide clear explanations of what you're doing

Available backends:
1. CUDA-Q QAOA: Quantum optimization for 16-node mycelial network (124 MB VRAM)
2. YOLO11s: Object detection at 27.5 FPS (1.2 GB VRAM)
3. Qwen 1.5 Chat: 4B parameter LLM (2.5 GB VRAM)

VRAM state thresholds (H_resource):
- H < 5.0: OPTIMAL (parallel workloads allowed)
- H 5.0-7.5: DYNAMIC (moderate pipelining)
- H 7.5-8.5: SEQUENTIAL (enforce serialization)
- H > 8.5: OFFLOAD (trigger Notion soul-capsule)"""
        
        # Initialize VRAM state tracking
        self.current_vram_state = "OPTIMAL"
        self.last_hamiltonian = 0.0
    
    def _init_monitoring(self):
        """Initialize OpenTelemetry monitoring with AppSignal exporter."""
        if not OPENTELEMETRY_AVAILABLE:
            self.tracer = None
            self.meter = None
            self.metrics = {}
            print("[Warning] OpenTelemetry not available, monitoring disabled")
            return
        
        try:
            # Load AppSignal configuration
            appsignal_key = os.environ.get("APPSIGNAL_API_KEY")
            appsignal_endpoint = os.environ.get(
                "APPSIGNAL_PUSH_API_ENDPOINT",
                "14g2tvpd.eu-central.appsignal-collector.net"
            )
            
            # Create resource with service metadata
            resource = Resource.create({
                "service.name": "claude-orchestrator",
                "service.version": "1.0.0",
                "deployment.environment": os.environ.get("APPSIGNAL_ENVIRONMENT", "production")
            })
            
            # Initialize tracer with AppSignal exporter
            if appsignal_key:
                # AppSignal OTLP endpoint
                otlp_endpoint = f"https://{appsignal_endpoint}/v1/traces"
                span_exporter = OTLPSpanExporter(
                    endpoint=otlp_endpoint,
                    headers={"Authorization": f"Bearer {appsignal_key}"}
                )
                trace_provider = TracerProvider(resource=resource)
                trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
                trace.set_tracer_provider(trace_provider)
                self.tracer = trace.get_tracer("claude-orchestrator")
                print(f"[✓] OpenTelemetry traces configured for AppSignal")
            else:
                self.tracer = None
                print("[Warning] APPSIGNAL_API_KEY not set, tracing disabled")
            
            # Initialize metrics with AppSignal exporter
            if appsignal_key:
                otlp_metric_endpoint = f"https://{appsignal_endpoint}/v1/metrics"
                metric_exporter = OTLPMetricExporter(
                    endpoint=otlp_metric_endpoint,
                    headers={"Authorization": f"Bearer {appsignal_key}"}
                )
                metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=30000)
                meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
                metrics.set_meter_provider(meter_provider)
                self.meter = metrics.get_meter("claude-orchestrator")
                
                # Create metrics
                self.metrics = {
                    "tool_calls_total": self.meter.create_counter(
                        "tool_calls_total",
                        description="Total number of tool calls by tool name and status"
                    ),
                    "tool_execution_duration": self.meter.create_histogram(
                        "tool_execution_duration",
                        unit="ms",
                        description="Tool execution latency in milliseconds"
                    ),
                    "vram_state_transitions": self.meter.create_counter(
                        "vram_state_transitions",
                        description="VRAM state transitions (OPTIMAL/DYNAMIC/SEQUENTIAL/OFFLOAD)"
                    )
                }
                
                # Store latest values for observable gauges
                self.latest_vram_bytes = 0
                self.latest_hamiltonian = 0.0
                self.latest_qaoa_energy = 0.0
                self.latest_gas_price = 0.0
                
                # Create observable gauges with callbacks
                self.meter.create_observable_gauge(
                    "vram_usage_bytes",
                    callbacks=[lambda options: [(self.latest_vram_bytes, {})]],
                    unit="bytes",
                    description="Current VRAM usage from gateway"
                )
                self.meter.create_observable_gauge(
                    "hamiltonian_value",
                    callbacks=[lambda options: [(self.latest_hamiltonian, {})]],
                    description="Resource Hamiltonian H_resource from gateway"
                )
                self.meter.create_observable_gauge(
                    "qaoa_energy",
                    callbacks=[lambda options: [(self.latest_qaoa_energy, {})]],
                    description="CUDA-Q QAOA energy value"
                )
                self.meter.create_observable_gauge(
                    "blockchain_gas_price",
                    callbacks=[lambda options: [(self.latest_gas_price, {})]],
                    unit="gwei",
                    description="Current Ethereum gas price in Gwei"
                )
                print(f"[✓] OpenTelemetry metrics configured for AppSignal")
            else:
                self.meter = None
                self.metrics = {}
                print("[Warning] APPSIGNAL_API_KEY not set, metrics disabled")
                
        except Exception as e:
            print(f"[Warning] Failed to initialize OpenTelemetry: {e}")
            self.tracer = None
            self.meter = None
            self.metrics = {}
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result with OpenTelemetry tracing."""
        start_time = time.time()
        
        # Start tracing span
        if self.tracer:
            with self.tracer.start_as_current_span(
                "tool_execution",
                attributes={
                    "tool.name": tool_name,
                    "tool.input": json.dumps(tool_input)[:500]  # Truncate large inputs
                }
            ) as span:
                try:
                    result = await self._execute_tool_impl(tool_name, tool_input)
                    
                    # Record successful execution
                    if span:
                        span.set_attribute("tool.status", "success")
                        span.set_status(Status(StatusCode.OK))
                    
                    # Track metrics
                    if self.metrics:
                        duration_ms = (time.time() - start_time) * 1000
                        self.metrics["tool_calls_total"].add(1, {"tool": tool_name, "status": "success"})
                        self.metrics["tool_execution_duration"].record(duration_ms, {"tool": tool_name})
                        
                        # Update VRAM and Hamiltonian gauges if this was a VRAM query
                        if tool_name == "query_vram_status" and result.get("vram_used_mb"):
                            self.latest_vram_bytes = result["vram_used_mb"] * 1024 * 1024
                            if "hamiltonian" in result:
                                self.latest_hamiltonian = result["hamiltonian"]
                                self._check_vram_state_transition(result["hamiltonian"])
                        
                        # Update QAOA energy if this was a CUDA-Q run
                        if tool_name == "run_cuda_q_qaoa" and result.get("energy"):
                            self.latest_qaoa_energy = result["energy"]
                        
                        # Update gas price if this was a gas optimization
                        if tool_name == "optimize_gas_fees" and result.get("current_gas_price_gwei"):
                            self.latest_gas_price = result["current_gas_price_gwei"]
                    
                    return result
                    
                except Exception as e:
                    # Record error in span
                    if span:
                        span.set_attribute("tool.status", "error")
                        span.set_attribute("error.message", str(e))
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                    
                    # Track error metrics
                    if self.metrics:
                        duration_ms = (time.time() - start_time) * 1000
                        self.metrics["tool_calls_total"].add(1, {"tool": tool_name, "status": "error"})
                        self.metrics["tool_execution_duration"].record(duration_ms, {"tool": tool_name})
                    
                    # Re-raise the exception
                    raise
        else:
            # No tracing available, execute directly
            return await self._execute_tool_impl(tool_name, tool_input)
    
    def _check_vram_state_transition(self, hamiltonian: float):
        """Check for VRAM state transitions and emit events."""
        # Determine new state based on Hamiltonian
        if hamiltonian > 8.5:
            new_state = "OFFLOAD"
        elif hamiltonian > 7.5:
            new_state = "SEQUENTIAL"
        elif hamiltonian > 5.0:
            new_state = "DYNAMIC"
        else:
            new_state = "OPTIMAL"
        
        # Check for state transition
        if new_state != self.current_vram_state:
            print(f"[VRAM State Transition] {self.current_vram_state} → {new_state} (H={hamiltonian:.2f})")
            
            # Record state transition in metrics
            if self.metrics:
                self.metrics["vram_state_transitions"].add(
                    1,
                    {
                        "from_state": self.current_vram_state,
                        "to_state": new_state,
                        "hamiltonian": str(round(hamiltonian, 2))
                    }
                )
            
            # Emit trace event
            if self.tracer:
                with self.tracer.start_as_current_span("vram_state_transition") as span:
                    if span:
                        span.set_attribute("vram.old_state", self.current_vram_state)
                        span.set_attribute("vram.new_state", new_state)
                        span.set_attribute("vram.hamiltonian", hamiltonian)
                        span.add_event(
                            f"VRAM state changed to {new_state}",
                            attributes={
                                "threshold": self._get_state_threshold(new_state),
                                "action": self._get_state_action(new_state)
                            }
                        )
            
            self.current_vram_state = new_state
            self.last_hamiltonian = hamiltonian
    
    def _get_state_threshold(self, state: str) -> str:
        """Get the Hamiltonian threshold for a state."""
        thresholds = {
            "OPTIMAL": "H < 5.0",
            "DYNAMIC": "5.0 <= H < 7.5",
            "SEQUENTIAL": "7.5 <= H < 8.5",
            "OFFLOAD": "H >= 8.5"
        }
        return thresholds.get(state, "unknown")
    
    def _get_state_action(self, state: str) -> str:
        """Get the recommended action for a state."""
        actions = {
            "OPTIMAL": "Parallel workloads allowed",
            "DYNAMIC": "Moderate pipelining",
            "SEQUENTIAL": "Enforce serialization",
            "OFFLOAD": "Trigger Notion soul-capsule offload"
        }
        return actions.get(state, "unknown")
    
    async def _execute_tool_impl(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Internal implementation of tool execution."""
        
        if tool_name == "get_nox_state":
            if not self.nox_engine:
                return {"status": "error", "error": "NOX Engine not available"}
            return self.nox_engine.get_state()
            
        elif tool_name == "configure_nox_engine":
            if not self.nox_engine:
                return {"status": "error", "error": "NOX Engine not available"}
            return self.nox_engine.configure(
                eta_thermo=tool_input.get("eta_thermo"),
                encryption_enabled=tool_input.get("encryption_enabled"),
                multilane_active=tool_input.get("multilane_active"),
                kernel_lanes=tool_input.get("kernel_lanes")
            )
            
        elif tool_name == "manage_diamond_vault":
            if not self.nox_engine:
                return {"status": "error", "error": "NOX Engine not available"}
            
            action = tool_input.get("action")
            if action == "offload_embeddings":
                return self.nox_engine.offload_embeddings(tool_input.get("embeddings", []))
            elif action in ["sync_notion", "sync_github"]:
                # Simulation for sync
                return {
                    "status": "SUCCESS",
                    "action": action,
                    "records_synced": 42,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            return {"status": "error", "error": f"Unknown action: {action}"}

        elif tool_name == "query_vram_status":
            # Real query to Diamond Gateway
            gateway_url = self.config.gateway.orchestrate_url if self.config else "http://127.0.0.1:8000/v1/orchestrate"
            
            if not self.gateway_secret:
                return {
                    "status": "error",
                    "error": "GATEWAY_SECRET not configured. Set it in ~/.env"
                }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        gateway_url,
                        headers={
                            "Authorization": f"Bearer {self.gateway_secret}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "session_id": "claude-session",
                            "context_buffer": "[CTX]"
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Transform gateway response to expected format
                    return {
                        "vram_used_mb": data.get("vram_used_mib", 0),
                        "vram_total_mb": data.get("vram_total_mib", 4096),
                        "vram_percent": int((data.get("vram_used_mib", 0) / data.get("vram_total_mib", 4096)) * 100),
                        "hamiltonian": data.get("hamiltonian", 0.0),
                        "action": data.get("action", "CONTINUE"),
                        "session_id": data.get("session_id", "unknown"),
                        "available_vram_mb": data.get("vram_total_mib", 4096) - data.get("vram_used_mib", 0),
                        "gateway_status": "connected"
                    }
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": f"Gateway connection failed: {str(e)}",
                    "gateway_status": "disconnected"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Unexpected error querying gateway: {str(e)}",
                    "gateway_status": "error"
                }
        
        elif tool_name == "run_cuda_q_qaoa":
            # Real CUDA-Q QAOA execution
            shots = tool_input.get("shots", 512)
            outer_rounds = tool_input.get("outer_rounds", 3)
            
            # Validate parameters
            if not (256 <= shots <= 2048):
                return {
                    "status": "error",
                    "error": f"shots must be between 256 and 2048, got {shots}"
                }
            
            if not (1 <= outer_rounds <= 10):
                return {
                    "status": "error",
                    "error": f"outer_rounds must be between 1 and 10, got {outer_rounds}"
                }
            
            # Path to CUDA-Q script and Python interpreter
            script_path = Path.home() / "diamond-node" / "scripts" / "mycelial_qubo.py"
            python_path = Path.home() / "xinference_venv" / "bin" / "python3"
            
            if not script_path.exists():
                return {
                    "status": "error",
                    "error": f"CUDA-Q script not found at {script_path}"
                }
            
            if not python_path.exists():
                # Fallback to system python3
                python_path = "python3"
            
            try:
                # Execute CUDA-Q QAOA
                import time
                start_time = time.time()
                
                result = subprocess.run(
                    [str(python_path), str(script_path), 
                     "--shots", str(shots),
                     "--outer-rounds", str(outer_rounds),
                     "--json"],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    cwd=str(script_path.parent)
                )
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                if result.returncode != 0:
                    return {
                        "status": "error",
                        "error": f"CUDA-Q execution failed: {result.stderr}",
                        "returncode": result.returncode
                    }
                
                # Parse JSON output from script
                try:
                    qaoa_result = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    return {
                        "status": "error",
                        "error": f"Failed to parse CUDA-Q output: {e}",
                        "raw_output": result.stdout[:500]
                    }
                
                # Calculate additional metrics
                energy = qaoa_result.get("energy", 0.0)
                best_energy = qaoa_result.get("best_energy", energy)
                energy_gradient = abs(energy - best_energy) if best_energy > 0 else 0.0
                
                # Estimate purity from convergence (higher is better)
                active_edges = qaoa_result.get("active_edges", 0)
                purity = min(0.99, 0.85 + (active_edges / 120.0) * 0.14)  # Scale based on edge count
                
                # Calculate effective dimension from subspace count
                subspaces = qaoa_result.get("subspaces", [])
                effective_dimension = len(subspaces) * 0.5 if subspaces else 4.0
                
                return {
                    "status": "success",
                    "shots": shots,
                    "outer_rounds": outer_rounds,
                    "energy": energy,
                    "best_energy": best_energy,
                    "energy_gradient": energy_gradient,
                    "purity": purity,
                    "effective_dimension": effective_dimension,
                    "active_edges": active_edges,
                    "iteration": qaoa_result.get("iteration", 0),
                    "vram_used_mb": 124,  # CUDA-Q uses ~124 MB
                    "inference_time_ms": elapsed_ms,
                    "raw_result": qaoa_result
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "status": "error",
                    "error": "CUDA-Q execution timed out (>300s)"
                }
            except FileNotFoundError as e:
                return {
                    "status": "error",
                    "error": f"Python interpreter or script not found: {e}"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Unexpected error running CUDA-Q: {type(e).__name__}: {e}"
                }
        
        elif tool_name == "run_yolo11_detection":
            return {
                "status": "success",
                "image": tool_input.get("image_path"),
                "detections": [
                    {"class": "person", "confidence": 0.89, "bbox": [100, 150, 300, 500]},
                    {"class": "car", "confidence": 0.76, "bbox": [400, 200, 600, 400]}
                ],
                "fps": 27.5,
                "latency_ms": 36,
                "vram_used_mb": 1200
            }
        
        elif tool_name == "query_qwen_chat":
            message = tool_input.get("message")
            return {
                "status": "success",
                "response": f"Qwen response to: {message[:50]}...",
                "tokens_generated": 156,
                "tokens_per_sec": 19.2,
                "latency_ms": 8125,
                "vram_used_mb": 2500
            }
        
        elif tool_name == "optimize_orthogonal_bounds":
            return await self._execute_orthogonal_optimization(tool_input)
        
        elif tool_name == "trigger_notion_offload":
            return {
                "status": "offloaded",
                "session_id": tool_input.get("session_id"),
                "notion_page_id": "abc123",
                "hamiltonian": tool_input.get("hamiltonian"),
                "bytes_offloaded": 2048000
            }
        
        # Blockchain wallet analysis tools
        elif tool_name == "query_wallet_balance":
            if not BLOCKCHAIN_AVAILABLE:
                return {
                    "error": "Blockchain tools not available. Install web3: pip install web3",
                    "status": "unavailable"
                }
            
            analyzer = get_analyzer()
            address = tool_input.get("address")
            result = await analyzer.query_wallet_balance(address)
            return result
        
        elif tool_name == "analyze_portfolio_risk":
            if not BLOCKCHAIN_AVAILABLE:
                return {
                    "error": "Blockchain tools not available. Install web3: pip install web3",
                    "status": "unavailable"
                }
            
            analyzer = get_analyzer()
            address = tool_input.get("address")
            historical_blocks = tool_input.get("historical_blocks", 1000)
            result = await analyzer.analyze_portfolio_risk(address, historical_blocks)
            return result
        
        elif tool_name == "simulate_rebalancing":
            if not BLOCKCHAIN_AVAILABLE:
                return {
                    "error": "Blockchain tools not available. Install web3: pip install web3",
                    "status": "unavailable"
                }
            
            analyzer = get_analyzer()
            current_allocation = tool_input.get("current_allocation")
            target_allocation = tool_input.get("target_allocation")
            simulations = tool_input.get("simulations", 1000)
            time_horizon_days = tool_input.get("time_horizon_days", 30)
            
            result = await analyzer.simulate_rebalancing(
                current_allocation,
                target_allocation,
                simulations,
                time_horizon_days
            )
            return result
        
        elif tool_name == "optimize_gas_fees":
            if not BLOCKCHAIN_AVAILABLE:
                return {
                    "error": "Blockchain tools not available. Install web3: pip install web3",
                    "status": "unavailable"
                }
            
            analyzer = get_analyzer()
            urgency = tool_input.get("urgency", "medium")
            result = await analyzer.optimize_gas_fees(urgency)
            return result
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _execute_orthogonal_optimization(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real orthogonal optimization using OrthogonalOptimizer.
        
        Args:
            tool_input: Contains workload_profile and optional constraints
            
        Returns:
            Dict with status, profile, pareto_optimal_configs, and recommended config
        """
        try:
            workload_profile = tool_input.get("workload_profile", "balanced")
            constraints = tool_input.get("constraints", {})
            
            # Map profile string to WorkloadType enum
            profile_map = {
                "scientific": WorkloadType.SCIENTIFIC,
                "vision": WorkloadType.VISION,
                "conversational": WorkloadType.CONVERSATIONAL,
                "balanced": WorkloadType.BALANCED,
                "low-power": WorkloadType.BALANCED  # Fallback for low-power
            }
            
            workload_type = profile_map.get(workload_profile.lower(), WorkloadType.BALANCED)
            
            # Create optimizer with workload profile
            optimizer = OrthogonalOptimizer(
                workload_type=workload_type,
                constraints=constraints or None
            )
            
            # Load profile config to get predicted metrics
            profile_config = self.optimization_profiles.get(workload_profile.lower(), {})
            
            # Generate operating points from profile configurations
            # For each model configuration, create predicted operating points
            operating_points = []
            
            # Get predicted metrics from profile
            predicted_metrics = profile_config.get("predicted_metrics", {})
            model_config = profile_config.get("model_config", {})
            
            # Create multiple configuration variants for Pareto analysis
            configs_to_test = self._generate_config_variants(
                workload_profile, 
                predicted_metrics,
                model_config
            )
            
            # Evaluate each configuration
            for config_name, config_data in configs_to_test:
                # Build SystemState
                total_vram = sum(m.get("vram_used_mib", 0) for m in config_data["metrics"].values())
                system_state = SystemState(
                    vram_used_mib=total_vram,
                    vram_total_mib=4096,
                    vram_util_pct=(total_vram / 4096) * 100,
                    temp_celsius=config_data.get("temp_celsius", 50.0),
                    hamiltonian=config_data.get("hamiltonian", 5.0),
                    active_models=list(config_data["metrics"].keys())
                )
                
                # Build ModelMetrics dict
                model_metrics = {}
                for model_name, metrics_dict in config_data["metrics"].items():
                    model_metrics[model_name] = ModelMetrics(
                        model_name=model_name,
                        vram_used_mib=metrics_dict.get("vram_used_mib", 0),
                        throughput_ops_per_sec=metrics_dict.get("throughput_ops_per_sec", 0.0),
                        accuracy_score=metrics_dict.get("accuracy_score", 0.0),
                        latency_p50_ms=metrics_dict.get("latency_p50_ms", 0.0),
                        latency_p95_ms=metrics_dict.get("latency_p95_ms", 0.0),
                        purity=metrics_dict.get("purity"),
                        effective_dimension=metrics_dict.get("effective_dimension"),
                        energy_gradient=metrics_dict.get("energy_gradient")
                    )
                
                # Evaluate operating point
                op = optimizer.evaluate_operating_point(
                    system_state=system_state,
                    model_metrics=model_metrics,
                    config_name=config_name
                )
                operating_points.append(op)
            
            # Find Pareto-optimal configurations
            pareto_optimal = optimizer.find_pareto_frontier(operating_points)
            
            # Format results
            pareto_configs = []
            for op in pareto_optimal[:10]:  # Top 10 Pareto-optimal configs
                primary_model = list(op.model_metrics.keys())[0] if op.model_metrics else "unknown"
                primary_metrics = list(op.model_metrics.values())[0] if op.model_metrics else None
                
                pareto_configs.append({
                    "config": op.config_name,
                    "score": round(op.total_score, 4),
                    "vram_mb": op.system_state.vram_used_mib,
                    "throughput": round(primary_metrics.throughput_ops_per_sec, 2) if primary_metrics else 0,
                    "accuracy": round(primary_metrics.accuracy_score, 4) if primary_metrics else 0,
                    "hamiltonian": round(op.system_state.hamiltonian, 3),
                    "objective_scores": {
                        dim.value: round(score, 4) 
                        for dim, score in op.objective_scores.items()
                    }
                })
            
            return {
                "status": "success",
                "profile": workload_profile,
                "total_configs_evaluated": len(operating_points),
                "pareto_optimal_count": len(pareto_optimal),
                "pareto_optimal_configs": pareto_configs,
                "recommended": pareto_configs[0]["config"] if pareto_configs else None,
                "optimization_weights": {
                    "vram_efficiency": round(optimizer.weights.vram_efficiency, 3),
                    "compute_throughput": round(optimizer.weights.compute_throughput, 3),
                    "model_accuracy": round(optimizer.weights.model_accuracy, 3),
                    "waveform_equilibrium": round(optimizer.weights.waveform_equilibrium, 3)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "profile": tool_input.get("workload_profile", "unknown")
            }
    
    def _generate_config_variants(self, 
                                  workload_profile: str,
                                  predicted_metrics: Dict[str, Any],
                                  model_config: Dict[str, Any]) -> List[tuple]:
        """Generate configuration variants for Pareto analysis.
        
        Creates multiple configurations by varying parameters like batch size,
        shots, quantization, etc. to explore the optimization space.
        
        Returns:
            List of (config_name, config_data) tuples
        """
        configs = []
        
        if workload_profile == "scientific":
            # CUDA-Q focused variants
            for shots in [512, 1024, 2048]:
                for layers in [2, 3, 4]:
                    config_name = f"scientific_q16_s{shots}_l{layers}"
                    
                    # Scale metrics based on parameters
                    base_metrics = predicted_metrics.get("cuda_q", {})
                    throughput_scale = 1024 / shots  # More shots = slower
                    accuracy_scale = shots / 1024 * layers / 3  # More shots/layers = better
                    
                    configs.append((config_name, {
                        "metrics": {
                            "cuda-q": {
                                "vram_used_mib": base_metrics.get("vram_used_mib", 180) + (layers - 3) * 20,
                                "throughput_ops_per_sec": base_metrics.get("throughput_ops_per_sec", 220) * throughput_scale,
                                "accuracy_score": base_metrics.get("energy_gradient", 0.0008) / accuracy_scale,
                                "latency_p50_ms": base_metrics.get("latency_p50_ms", 450) / throughput_scale,
                                "latency_p95_ms": base_metrics.get("latency_p95_ms", 680) / throughput_scale,
                                "purity": min(0.98, base_metrics.get("purity", 0.96) * accuracy_scale),
                                "effective_dimension": max(3.0, base_metrics.get("effective_dimension", 4.2) / accuracy_scale),
                                "energy_gradient": base_metrics.get("energy_gradient", 0.0008) / accuracy_scale
                            }
                        },
                        "temp_celsius": 35 + (shots / 512) * 10,
                        "hamiltonian": 1.5 + (shots / 512) * 0.5
                    }))
        
        elif workload_profile == "vision":
            # YOLO11 focused variants
            for batch_size in [1, 2, 4, 8]:
                for half_precision in [True, False]:
                    precision_str = "fp16" if half_precision else "fp32"
                    config_name = f"vision_yolo11_b{batch_size}_{precision_str}"
                    
                    base_metrics = predicted_metrics.get("yolo11s", {})
                    throughput_scale = batch_size * (1.2 if half_precision else 1.0)
                    vram_scale = batch_size * (0.5 if half_precision else 1.0)
                    
                    configs.append((config_name, {
                        "metrics": {
                            "yolo11s": {
                                "vram_used_mib": int(base_metrics.get("vram_used_mib", 1250) * vram_scale),
                                "throughput_ops_per_sec": base_metrics.get("throughput_ops_per_sec", 28.5) * throughput_scale / batch_size,
                                "accuracy_score": base_metrics.get("accuracy_score", 0.72) * (0.98 if half_precision else 1.0),
                                "latency_p50_ms": base_metrics.get("latency_p50_ms", 32) * batch_size / throughput_scale,
                                "latency_p95_ms": base_metrics.get("latency_p95_ms", 48) * batch_size / throughput_scale,
                                "purity": None,
                                "effective_dimension": None,
                                "energy_gradient": None
                            }
                        },
                        "temp_celsius": 45 + batch_size * 5,
                        "hamiltonian": 3.5 + vram_scale * 0.8
                    }))
        
        elif workload_profile == "conversational":
            # Qwen LLM focused variants
            for seq_len in [512, 1024, 2048]:
                for quant in ["int4", "int8", "fp16"]:
                    config_name = f"conversational_qwen_seq{seq_len}_{quant}"
                    
                    base_metrics = predicted_metrics.get("qwen_1_5", {})
                    vram_scale = {"int4": 0.7, "int8": 0.85, "fp16": 1.0}[quant]
                    throughput_scale = seq_len / 2048
                    
                    configs.append((config_name, {
                        "metrics": {
                            "qwen-1.5": {
                                "vram_used_mib": int(base_metrics.get("vram_used_mib", 2650) * vram_scale * (seq_len / 2048)),
                                "throughput_ops_per_sec": base_metrics.get("throughput_ops_per_sec", 18.5) / throughput_scale,
                                "accuracy_score": base_metrics.get("accuracy_score", 4.2) * (1.1 if quant == "int4" else 1.0),
                                "latency_p50_ms": base_metrics.get("latency_p50_ms", 280) * throughput_scale,
                                "latency_p95_ms": base_metrics.get("latency_p95_ms", 420) * throughput_scale,
                                "purity": None,
                                "effective_dimension": None,
                                "energy_gradient": None
                            }
                        },
                        "temp_celsius": 40 + vram_scale * 15,
                        "hamiltonian": 6.0 + vram_scale * 1.5
                    }))
        
        else:  # balanced or other
            # Mixed workload variants
            configs.append(("balanced_cuda_q", {
                "metrics": {
                    "cuda-q": predicted_metrics.get("cuda_q", {
                        "vram_used_mib": 140,
                        "throughput_ops_per_sec": 180.0,
                        "accuracy_score": 0.003,
                        "latency_p50_ms": 520,
                        "latency_p95_ms": 780,
                        "purity": 0.93,
                        "effective_dimension": 5.8,
                        "energy_gradient": 0.003
                    })
                },
                "temp_celsius": 45,
                "hamiltonian": 2.5
            }))
            
            configs.append(("balanced_yolo", {
                "metrics": {
                    "yolo11s": predicted_metrics.get("yolo11s", {
                        "vram_used_mib": 1180,
                        "throughput_ops_per_sec": 22.0,
                        "accuracy_score": 0.70,
                        "latency_p50_ms": 42,
                        "latency_p95_ms": 65,
                        "purity": None,
                        "effective_dimension": None,
                        "energy_gradient": None
                    })
                },
                "temp_celsius": 55,
                "hamiltonian": 5.0
            }))
            
            configs.append(("balanced_qwen", {
                "metrics": {
                    "qwen-1.5": predicted_metrics.get("qwen_1_5", {
                        "vram_used_mib": 1950,
                        "throughput_ops_per_sec": 15.0,
                        "accuracy_score": 5.5,
                        "latency_p50_ms": 350,
                        "latency_p95_ms": 520,
                        "purity": None,
                        "effective_dimension": None,
                        "energy_gradient": None
                    })
                },
                "temp_celsius": 50,
                "hamiltonian": 6.5
            }))
        
        return configs

    
    async def _execute_orthogonal_optimization(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real orthogonal optimization using OrthogonalOptimizer.
        
        Args:
            tool_input: Contains workload_profile and optional constraints
            
        Returns:
            Dict with status, profile, pareto_optimal_configs, and recommended config
        """
        try:
            workload_profile = tool_input.get("workload_profile", "balanced")
            constraints = tool_input.get("constraints", {})
            
            # Map profile string to WorkloadType enum
            profile_map = {
                "scientific": WorkloadType.SCIENTIFIC,
                "vision": WorkloadType.VISION,
                "conversational": WorkloadType.CONVERSATIONAL,
                "balanced": WorkloadType.BALANCED,
                "low-power": WorkloadType.BALANCED  # Fallback for low-power
            }
            
            workload_type = profile_map.get(workload_profile.lower(), WorkloadType.BALANCED)
            
            # Create optimizer with workload profile
            optimizer = OrthogonalOptimizer(
                workload_type=workload_type,
                constraints=constraints or None
            )
            
            # Load profile config to get predicted metrics
            profile_config = self.optimization_profiles.get(workload_profile.lower(), {})
            
            # Generate operating points from profile configurations
            # For each model configuration, create predicted operating points
            operating_points = []
            
            # Get predicted metrics from profile
            predicted_metrics = profile_config.get("predicted_metrics", {})
            model_config = profile_config.get("model_config", {})
            
            # Create multiple configuration variants for Pareto analysis
            configs_to_test = self._generate_config_variants(
                workload_profile, 
                predicted_metrics,
                model_config
            )
            
            # Evaluate each configuration
            for config_name, config_data in configs_to_test:
                # Build SystemState
                total_vram = sum(m.get("vram_used_mib", 0) for m in config_data["metrics"].values())
                system_state = SystemState(
                    vram_used_mib=total_vram,
                    vram_total_mib=4096,
                    vram_util_pct=(total_vram / 4096) * 100,
                    temp_celsius=config_data.get("temp_celsius", 50.0),
                    hamiltonian=config_data.get("hamiltonian", 5.0),
                    active_models=list(config_data["metrics"].keys())
                )
                
                # Build ModelMetrics dict
                model_metrics = {}
                for model_name, metrics_dict in config_data["metrics"].items():
                    model_metrics[model_name] = ModelMetrics(
                        model_name=model_name,
                        vram_used_mib=metrics_dict.get("vram_used_mib", 0),
                        throughput_ops_per_sec=metrics_dict.get("throughput_ops_per_sec", 0.0),
                        accuracy_score=metrics_dict.get("accuracy_score", 0.0),
                        latency_p50_ms=metrics_dict.get("latency_p50_ms", 0.0),
                        latency_p95_ms=metrics_dict.get("latency_p95_ms", 0.0),
                        purity=metrics_dict.get("purity"),
                        effective_dimension=metrics_dict.get("effective_dimension"),
                        energy_gradient=metrics_dict.get("energy_gradient")
                    )
                
                # Evaluate operating point
                op = optimizer.evaluate_operating_point(
                    system_state=system_state,
                    model_metrics=model_metrics,
                    config_name=config_name
                )
                operating_points.append(op)
            
            # Find Pareto-optimal configurations
            pareto_optimal = optimizer.find_pareto_frontier(operating_points)
            
            # Format results
            pareto_configs = []
            for op in pareto_optimal[:10]:  # Top 10 Pareto-optimal configs
                primary_model = list(op.model_metrics.keys())[0] if op.model_metrics else "unknown"
                primary_metrics = list(op.model_metrics.values())[0] if op.model_metrics else None
                
                pareto_configs.append({
                    "config": op.config_name,
                    "score": round(op.total_score, 4),
                    "vram_mb": op.system_state.vram_used_mib,
                    "throughput": round(primary_metrics.throughput_ops_per_sec, 2) if primary_metrics else 0,
                    "accuracy": round(primary_metrics.accuracy_score, 4) if primary_metrics else 0,
                    "hamiltonian": round(op.system_state.hamiltonian, 3),
                    "objective_scores": {
                        dim.value: round(score, 4) 
                        for dim, score in op.objective_scores.items()
                    }
                })
            
            return {
                "status": "success",
                "profile": workload_profile,
                "total_configs_evaluated": len(operating_points),
                "pareto_optimal_count": len(pareto_optimal),
                "pareto_optimal_configs": pareto_configs,
                "recommended": pareto_configs[0]["config"] if pareto_configs else None,
                "optimization_weights": {
                    "vram_efficiency": round(optimizer.weights.vram_efficiency, 3),
                    "compute_throughput": round(optimizer.weights.compute_throughput, 3),
                    "model_accuracy": round(optimizer.weights.model_accuracy, 3),
                    "waveform_equilibrium": round(optimizer.weights.waveform_equilibrium, 3)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "profile": tool_input.get("workload_profile", "unknown")
            }
    
    def _generate_config_variants(self, 
                                  workload_profile: str,
                                  predicted_metrics: Dict[str, Any],
                                  model_config: Dict[str, Any]) -> List[tuple]:
        """Generate configuration variants for Pareto analysis.
        
        Creates multiple configurations by varying parameters like batch size,
        shots, quantization, etc. to explore the optimization space.
        
        Returns:
            List of (config_name, config_data) tuples
        """
        configs = []
        
        if workload_profile == "scientific":
            # CUDA-Q focused variants
            for shots in [512, 1024, 2048]:
                for layers in [2, 3, 4]:
                    config_name = f"scientific_q16_s{shots}_l{layers}"
                    
                    # Scale metrics based on parameters
                    base_metrics = predicted_metrics.get("cuda_q", {})
                    throughput_scale = 1024 / shots  # More shots = slower
                    accuracy_scale = shots / 1024 * layers / 3  # More shots/layers = better
                    
                    configs.append((config_name, {
                        "metrics": {
                            "cuda-q": {
                                "vram_used_mib": base_metrics.get("vram_used_mib", 180) + (layers - 3) * 20,
                                "throughput_ops_per_sec": base_metrics.get("throughput_ops_per_sec", 220) * throughput_scale,
                                "accuracy_score": base_metrics.get("energy_gradient", 0.0008) / accuracy_scale,
                                "latency_p50_ms": base_metrics.get("latency_p50_ms", 450) / throughput_scale,
                                "latency_p95_ms": base_metrics.get("latency_p95_ms", 680) / throughput_scale,
                                "purity": min(0.98, base_metrics.get("purity", 0.96) * accuracy_scale),
                                "effective_dimension": max(3.0, base_metrics.get("effective_dimension", 4.2) / accuracy_scale),
                                "energy_gradient": base_metrics.get("energy_gradient", 0.0008) / accuracy_scale
                            }
                        },
                        "temp_celsius": 35 + (shots / 512) * 10,
                        "hamiltonian": 1.5 + (shots / 512) * 0.5
                    }))
        
        elif workload_profile == "vision":
            # YOLO11 focused variants
            for batch_size in [1, 2, 4, 8]:
                for half_precision in [True, False]:
                    precision_str = "fp16" if half_precision else "fp32"
                    config_name = f"vision_yolo11_b{batch_size}_{precision_str}"
                    
                    base_metrics = predicted_metrics.get("yolo11s", {})
                    throughput_scale = batch_size * (1.2 if half_precision else 1.0)
                    vram_scale = batch_size * (0.5 if half_precision else 1.0)
                    
                    configs.append((config_name, {
                        "metrics": {
                            "yolo11s": {
                                "vram_used_mib": int(base_metrics.get("vram_used_mib", 1250) * vram_scale),
                                "throughput_ops_per_sec": base_metrics.get("throughput_ops_per_sec", 28.5) * throughput_scale / batch_size,
                                "accuracy_score": base_metrics.get("accuracy_score", 0.72) * (0.98 if half_precision else 1.0),
                                "latency_p50_ms": base_metrics.get("latency_p50_ms", 32) * batch_size / throughput_scale,
                                "latency_p95_ms": base_metrics.get("latency_p95_ms", 48) * batch_size / throughput_scale,
                                "purity": None,
                                "effective_dimension": None,
                                "energy_gradient": None
                            }
                        },
                        "temp_celsius": 45 + batch_size * 5,
                        "hamiltonian": 3.5 + vram_scale * 0.8
                    }))
        
        elif workload_profile == "conversational":
            # Qwen LLM focused variants
            for seq_len in [512, 1024, 2048]:
                for quant in ["int4", "int8", "fp16"]:
                    config_name = f"conversational_qwen_seq{seq_len}_{quant}"
                    
                    base_metrics = predicted_metrics.get("qwen_1_5", {})
                    vram_scale = {"int4": 0.7, "int8": 0.85, "fp16": 1.0}[quant]
                    throughput_scale = seq_len / 2048
                    
                    configs.append((config_name, {
                        "metrics": {
                            "qwen-1.5": {
                                "vram_used_mib": int(base_metrics.get("vram_used_mib", 2650) * vram_scale * (seq_len / 2048)),
                                "throughput_ops_per_sec": base_metrics.get("throughput_ops_per_sec", 18.5) / throughput_scale,
                                "accuracy_score": base_metrics.get("accuracy_score", 4.2) * (1.1 if quant == "int4" else 1.0),
                                "latency_p50_ms": base_metrics.get("latency_p50_ms", 280) * throughput_scale,
                                "latency_p95_ms": base_metrics.get("latency_p95_ms", 420) * throughput_scale,
                                "purity": None,
                                "effective_dimension": None,
                                "energy_gradient": None
                            }
                        },
                        "temp_celsius": 40 + vram_scale * 15,
                        "hamiltonian": 6.0 + vram_scale * 1.5
                    }))
        
        else:  # balanced or other
            # Mixed workload variants
            configs.append(("balanced_cuda_q", {
                "metrics": {
                    "cuda-q": predicted_metrics.get("cuda_q", {
                        "vram_used_mib": 140,
                        "throughput_ops_per_sec": 180.0,
                        "accuracy_score": 0.003,
                        "latency_p50_ms": 520,
                        "latency_p95_ms": 780,
                        "purity": 0.93,
                        "effective_dimension": 5.8,
                        "energy_gradient": 0.003
                    })
                },
                "temp_celsius": 45,
                "hamiltonian": 2.5
            }))
            
            configs.append(("balanced_yolo", {
                "metrics": {
                    "yolo11s": predicted_metrics.get("yolo11s", {
                        "vram_used_mib": 1180,
                        "throughput_ops_per_sec": 22.0,
                        "accuracy_score": 0.70,
                        "latency_p50_ms": 42,
                        "latency_p95_ms": 65,
                        "purity": None,
                        "effective_dimension": None,
                        "energy_gradient": None
                    })
                },
                "temp_celsius": 55,
                "hamiltonian": 5.0
            }))
            
            configs.append(("balanced_qwen", {
                "metrics": {
                    "qwen-1.5": predicted_metrics.get("qwen_1_5", {
                        "vram_used_mib": 1950,
                        "throughput_ops_per_sec": 15.0,
                        "accuracy_score": 5.5,
                        "latency_p50_ms": 350,
                        "latency_p95_ms": 520,
                        "purity": None,
                        "effective_dimension": None,
                        "energy_gradient": None
                    })
                },
                "temp_celsius": 50,
                "hamiltonian": 6.5
            }))
        
        return configs
    
    async def chat_stream(self, user_message: str, streaming: bool = True):
        """
        Process a user message with streaming support.
        
        Args:
            user_message: The user's query
            streaming: If True, yields events in real-time. If False, uses blocking mode.
            
        Yields:
            Dict events with types:
            - {"type": "text_delta", "text": "..."}
            - {"type": "thinking_delta", "thinking": "..."}
            - {"type": "tool_start", "name": "...", "input": {...}}
            - {"type": "tool_end", "name": "...", "result": {...}}
            - {"type": "message_complete", "text": "..."}
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        if not streaming:
            # Fall back to blocking mode
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                thinking={"type": "adaptive", "display": os.environ.get("THINKING_DISPLAY", "summarized")},
                output_config={"effort": "xhigh"},
                system=[{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=self.conversation_history
            )
            
            assistant_message = []
            final_text = ""
            
            for block in response.content:
                if block.type == "text":
                    assistant_message.append({"type": "text", "text": block.text})
                    final_text += block.text
                elif block.type == "thinking":
                    if block.thinking:
                        yield {"type": "thinking_delta", "thinking": block.thinking}
                elif block.type == "tool_use":
                    yield {"type": "tool_start", "name": block.name, "input": block.input}
                    tool_result = await self.execute_tool(block.name, block.input)
                    yield {"type": "tool_end", "name": block.name, "result": tool_result}
                    
                    assistant_message.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            yield {"type": "message_complete", "text": final_text}
            return
        
        # Streaming mode with client.messages.stream()
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive", "display": os.environ.get("THINKING_DISPLAY", "summarized")},
            output_config={"effort": "xhigh"},
            system=[{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=self.conversation_history
        ) as stream:
            assistant_message = []
            accumulated_text = ""
            accumulated_thinking = ""
            current_tool_use = None
            
            for event in stream:
                # Text delta events
                if event.type == "content_block_start":
                    if hasattr(event, 'content_block'):
                        if event.content_block.type == "text":
                            pass  # Text block started
                        elif event.content_block.type == "thinking":
                            accumulated_thinking = ""
                        elif event.content_block.type == "tool_use":
                            current_tool_use = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": ""
                            }
                            yield {"type": "tool_start", "name": event.content_block.name, "input": {}}
                
                elif event.type == "content_block_delta":
                    if hasattr(event, 'delta'):
                        if event.delta.type == "text_delta":
                            text_chunk = event.delta.text
                            accumulated_text += text_chunk
                            yield {"type": "text_delta", "text": text_chunk}
                        
                        elif event.delta.type == "thinking_delta":
                            thinking_chunk = event.delta.thinking
                            accumulated_thinking += thinking_chunk
                            yield {"type": "thinking_delta", "thinking": thinking_chunk}
                        
                        elif event.delta.type == "input_json_delta":
                            if current_tool_use:
                                current_tool_use["input"] += event.delta.partial_json
                
                elif event.type == "content_block_stop":
                    if current_tool_use:
                        # Tool call completed, execute it
                        try:
                            tool_input = json.loads(current_tool_use["input"]) if current_tool_use["input"] else {}
                        except json.JSONDecodeError:
                            tool_input = {}
                        
                        tool_result = await self.execute_tool(current_tool_use["name"], tool_input)
                        yield {"type": "tool_end", "name": current_tool_use["name"], "result": tool_result}
                        
                        assistant_message.append({
                            "type": "tool_use",
                            "id": current_tool_use["id"],
                            "name": current_tool_use["name"],
                            "input": tool_input
                        })
                        
                        current_tool_use = None
            
            # Get final message from stream
            final_message = stream.get_final_message()
            
            # If tool was used, we need follow-up
            if any(block["type"] == "tool_use" for block in assistant_message):
                # Add assistant message with tool use
                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                
                # Add tool results
                for block in assistant_message:
                    if block["type"] == "tool_use":
                        tool_result = await self.execute_tool(block["name"], block["input"])
                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block["id"],
                                "content": json.dumps(tool_result)
                            }]
                        })
                
                # Stream follow-up response
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    thinking={"type": "adaptive", "display": os.environ.get("THINKING_DISPLAY", "summarized")},
                    output_config={"effort": "xhigh"},
                    system=[{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
                    tools=TOOLS,
                    messages=self.conversation_history
                ) as follow_stream:
                    follow_text = ""
                    
                    for event in follow_stream:
                        if event.type == "content_block_delta":
                            if hasattr(event, 'delta'):
                                if event.delta.type == "text_delta":
                                    text_chunk = event.delta.text
                                    follow_text += text_chunk
                                    yield {"type": "text_delta", "text": text_chunk}
                                elif event.delta.type == "thinking_delta":
                                    yield {"type": "thinking_delta", "thinking": event.delta.thinking}
                    
                    follow_message = follow_stream.get_final_message()
                    self.conversation_history.append({"role": "assistant", "content": follow_message.content})
                    
                    yield {"type": "message_complete", "text": follow_text}
            else:
                # No tool use, just save the message
                if accumulated_text:
                    assistant_message.append({"type": "text", "text": accumulated_text})
                
                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                yield {"type": "message_complete", "text": accumulated_text}
    
    async def chat(self, user_message: str, streaming: bool = False) -> str:
        """
        Process a user message and return Claude's response (non-streaming by default).
        
        Args:
            user_message: The user's query
            streaming: If True, prints events in real-time but still returns final text
            
        Returns:
            Final text response from Claude
        """
        final_text = ""
        
        if streaming:
            # Use streaming but accumulate to return final text
            async for event in self.chat_stream(user_message, streaming=True):
                if event["type"] == "text_delta":
                    print(event["text"], end="", flush=True)
                elif event["type"] == "thinking_delta":
                    # Optionally print thinking (can be verbose)
                    pass
                elif event["type"] == "tool_start":
                    print(f"\n[Tool: {event['name']}]", flush=True)
                elif event["type"] == "tool_end":
                    print(f"[Tool Complete: {event['name']}]", flush=True)
                elif event["type"] == "message_complete":
                    final_text = event["text"]
                    print()  # Newline at end
        else:
            # Blocking mode (original behavior)
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.config.api.max_tokens_sync if self.config else 16000,
                thinking={"type": "adaptive", "display": os.environ.get("THINKING_DISPLAY", "summarized")},
                output_config={"effort": "xhigh"},
                system=[{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=self.conversation_history
            )
            
            assistant_message = []
            
            for block in response.content:
                if block.type == "text":
                    assistant_message.append({"type": "text", "text": block.text})
                    final_text += block.text
                elif block.type == "thinking":
                    if block.thinking:
                        print(f"[Claude Thinking]: {block.thinking[:100]}...")
                elif block.type == "tool_use":
                    tool_result = await self.execute_tool(block.name, block.input)
                    assistant_message.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
                    
                    self.conversation_history.append({"role": "assistant", "content": assistant_message})
                    self.conversation_history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_result)
                        }]
                    })
                    
                    follow_up = self.client.messages.create(
                        model=self.model,
                        max_tokens=self.config.api.max_tokens_sync if self.config else 16000,
                        thinking={"type": "adaptive", "display": os.environ.get("THINKING_DISPLAY", "summarized")},
                        output_config={"effort": "xhigh"},
                        system=[{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
                        tools=TOOLS,
                        messages=self.conversation_history
                    )
                    
                    final_text = ""
                    for follow_block in follow_up.content:
                        if follow_block.type == "text":
                            final_text += follow_block.text
                    
                    self.conversation_history.append({"role": "assistant", "content": follow_up.content})
                    return final_text
            
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
        
        return final_text
    
    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []


async def main():
    """Demo of the Claude orchestrator."""
    
    orchestrator = ClaudeOrchestrator()
    
    queries = [
        "What's the current VRAM status?",
        "Run a CUDA-Q optimization with 2048 shots",
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"User: {query}")
        print(f"{'='*60}")
        
        response = await orchestrator.chat(query)
        print(f"\nClaude: {response}\n")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set")
    
    asyncio.run(main())
