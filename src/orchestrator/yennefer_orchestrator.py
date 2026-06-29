# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Yennefer Orchestrator - Unified Inference Integration

Integrates:
- EnKG Triton kernel (src/kernels/enkg_exchange.py)
- Agent 3 Validator (src/orchestrator/agent3_validator.py)
- aSHARD config (config/ashard_config.yaml)
- Diamond Gateway (localhost:8000)
- Yennefer Telemetry Daemon (workers/yennefer_telemetry_daemon.py)

Orchestration flow:
1. Initialize EnKG kernel with κ, γ parameters
2. Run telemetry cycle (VRAM, temp, Hamiltonian)
3. Apply exchange operator to state vectors
4. Validate output via Agent 3 (NULL/DUCTILE/CRYSTALLINE)
5. Post results to Gateway
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import yaml
import torch
import httpx

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import EnKG kernel
from kernels.enkg_exchange import apply_M_matrix, benchmark_enkg_kernel, TRITON_AVAILABLE

# Import Agent 3 Validator
from orchestrator.agent3_validator import (
    OuroborosAgent3Validator,
    ValidationResult,
    AShardParams,
    InvariantTruth,
    PIScope
)

# Import telemetry daemon components
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from workers.yennefer_telemetry_daemon import YenneferTelemetryDaemon

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TelemetryCycleResult:
    """Result from a single telemetry cycle"""
    timestamp: str
    vram_used_mb: float
    vram_total_mb: float
    vram_percent: float
    gpu_temp_celsius: float
    hamiltonian: float
    gateway_action: str  # CONTINUE or OFFLOAD


@dataclass
class OrchestrationResult:
    """Complete orchestration cycle result"""
    telemetry: TelemetryCycleResult
    enkg_output: torch.Tensor
    validation_state: str  # NULL | DUCTILE | CRYSTALLINE
    validation_details: Dict[str, Any]
    execution_time_ms: float


class YenneferOrchestrator:
    """
    Main Yennefer orchestration framework for unified inference.
    
    Coordinates:
    - GPU telemetry via Diamond Gateway
    - EnKG exchange operator (Triton kernel)
    - Agent 3 validation (Seismic Tree-of-Thoughts)
    - Yennefer telemetry daemon
    """
    
    def __init__(
        self,
        ashard_config_path: Optional[Path] = None,
        agent3_config_path: Optional[Path] = None,
        yennefer_config_path: Optional[Path] = None
    ):
        """
        Initialize Yennefer Orchestrator
        
        Args:
            ashard_config_path: Path to ashard_config.yaml (defaults to config/ashard_config.yaml)
            agent3_config_path: Path to agent3_system_prompt.yaml
            yennefer_config_path: Path to yennefer_config.yaml
        """
        # Load aSHARD config
        if ashard_config_path is None:
            ashard_config_path = Path(__file__).parent.parent.parent / "config" / "ashard_config.yaml"
        
        with open(ashard_config_path, 'r') as f:
            self.ashard_config = yaml.safe_load(f)
        
        logger.info(f"Loaded aSHARD config from {ashard_config_path}")
        
        # Load agent3 config if provided
        if agent3_config_path is None:
            agent3_config_path = Path(__file__).parent.parent.parent / "config" / "agent3_system_prompt.yaml"
        
        # Load yennefer config
        if yennefer_config_path is None:
            yennefer_config_path = Path(__file__).parent.parent.parent / "config" / "yennefer_config.yaml"
        
        with open(yennefer_config_path, 'r') as f:
            self.yennefer_config = yaml.safe_load(f)
        
        # Gateway configuration
        gateway_config = self.ashard_config['ashard']['gateway']
        self.gateway_metrics_url = gateway_config['metrics_url']
        self.gateway_orchestrate_url = gateway_config['orchestrate_url']
        self.gateway_auth_env_var = gateway_config['auth_env_var']
        self.gateway_poll_interval = gateway_config['poll_interval']
        
        # Get auth token
        self.gateway_secret = os.getenv(self.gateway_auth_env_var)
        if not self.gateway_secret:
            logger.warning(f"Gateway auth token not found in env var: {self.gateway_auth_env_var}")

        # Device setup. Keep the effective device on self so non-GPU hosts
        # actually use the advertised CPU fallback path.
        requested_device = torch.device(self.ashard_config['ashard']['device'])
        if requested_device.type == 'cuda' and torch.cuda.is_available():
            self.device = requested_device
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA Version: {torch.version.cuda}")
            logger.info(f"Triton Available: {TRITON_AVAILABLE}")
        elif requested_device.type == 'cuda':
            self.device = torch.device('cpu')
            logger.warning("CUDA not available, using CPU fallback")
        else:
            self.device = requested_device
            logger.info(f"Using device: {self.device}")
        
        # Initialize EnKG kernel parameters (default values, can be overridden)
        self.kappa = 0.7  # Identity component
        self.gamma = 0.3  # Pauli-X exchange component
        
        # Initialize Agent 3 Validator
        invariant_truth = {
            "conservation_laws": [
                "energy_conservation",
                "momentum_conservation",
                "charge_conservation"
            ],
            "symmetries": ["time_reversal", "parity", "gauge_invariance"],
            "dimensional_constraints": {
                "vram_bytes": self.ashard_config['ashard']['vram_total'],
                "temperature_celsius": self.ashard_config['ashard']['max_temperature']
            },
            "boundary_conditions": {
                "thermal_warn": self.ashard_config['ashard']['thermal']['warn_threshold'],
                "thermal_critical": self.ashard_config['ashard']['thermal']['critical_threshold']
            }
        }
        
        ashard_params = {
            "vram_total_bytes": self.ashard_config['ashard']['vram_total'],
            "thermal_max_celsius": self.ashard_config['ashard']['max_temperature'],
            "vram_allocation_buffer": 0.9
        }
        
        pi_scope = {
            "allowed_operations": ["inference", "training", "validation"],
            "resource_limits": {
                "max_batch_size": self.ashard_config['ashard']['safety']['max_batch_size'],
                "max_sequence_length": self.ashard_config['ashard']['safety']['max_sequence_length']
            },
            "state_transitions": {
                "NULL": ["DUCTILE"],
                "DUCTILE": ["CRYSTALLINE", "NULL"],
                "CRYSTALLINE": ["NULL"]
            },
            "execution_context": {
                "device": str(self.device),
                "enable_cudnn_benchmark": self.ashard_config['ashard']['performance']['enable_cudnn_benchmark']
            }
        }
        
        try:
            self.agent3_validator = OuroborosAgent3Validator(
                invariant_truth=invariant_truth,
                ashard_params=ashard_params,
                pi_scope=pi_scope,
                system_prompt_path=agent3_config_path,
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                use_local_llm=False
            )
            logger.info("Agent 3 Validator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Agent 3 Validator: {e}")
            self.agent3_validator = None
        
        # Initialize telemetry daemon
        try:
            self.telemetry_daemon = YenneferTelemetryDaemon(
                config_path=str(yennefer_config_path)
            )
            logger.info("Yennefer Telemetry Daemon initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Telemetry Daemon: {e}")
            self.telemetry_daemon = None
        
        logger.info("Yennefer Orchestrator initialized successfully")

    @staticmethod
    def _metric_value(metrics: Dict[str, Any], *names: str, default: float = 0.0) -> float:
        for name in names:
            value = metrics.get(name)
            if value is not None:
                return float(value)
        return float(default)
    
    def initialize_enkg_kernel(self, kappa: float, gamma: float) -> None:
        """
        Initialize EnKG kernel with specified parameters
        
        Args:
            kappa: Identity component coefficient (0-1)
            gamma: Pauli-X exchange component coefficient (0-1)
        """
        self.kappa = kappa
        self.gamma = gamma
        logger.info(f"EnKG kernel initialized: κ={kappa:.3f}, γ={gamma:.3f}")
    
    async def run_telemetry_cycle(self) -> TelemetryCycleResult:
        """
        Execute a single telemetry cycle
        
        Queries Diamond Gateway for:
        - VRAM usage (used/total/percent)
        - GPU temperature
        - Resource Hamiltonian H(s)
        - Orchestration action (CONTINUE/OFFLOAD)
        
        Returns:
            TelemetryCycleResult with current system state
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {}
                if self.gateway_secret:
                    headers['Authorization'] = f'Bearer {self.gateway_secret}'
                
                # Query metrics endpoint
                response = await client.get(
                    self.gateway_metrics_url,
                    headers=headers
                )
                response.raise_for_status()
                metrics = response.json()
                
                # Query orchestrate endpoint
                orchestrate_payload = {
                    "session_id": f"yennefer-{int(time.time())}",
                    "context_buffer": "[Yennefer telemetry cycle]"
                }
                
                orchestrate_response = await client.post(
                    self.gateway_orchestrate_url,
                    headers={**headers, 'Content-Type': 'application/json'},
                    json=orchestrate_payload
                )
                orchestrate_response.raise_for_status()
                orchestrate_data = orchestrate_response.json()
                
                # Extract telemetry. Gateway /metrics may report VRAM as MiB
                # fields or legacy byte fields; keep telemetry in MB/MiB units.
                if 'vram_used_mib' in metrics or 'vram_total_mib' in metrics:
                    vram_used_mb = self._metric_value(metrics, 'vram_used_mib')
                    vram_total_mb = self._metric_value(metrics, 'vram_total_mib', default=4096.0)
                else:
                    vram_used_mb = self._metric_value(metrics, 'vram_used') / (1024 * 1024)
                    vram_total_mb = self._metric_value(metrics, 'vram_total', default=4096.0 * 1024 * 1024) / (1024 * 1024)
                vram_percent = (vram_used_mb / vram_total_mb * 100) if vram_total_mb > 0 else 0
                
                result = TelemetryCycleResult(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    vram_used_mb=vram_used_mb,
                    vram_total_mb=vram_total_mb,
                    vram_percent=vram_percent,
                    gpu_temp_celsius=self._metric_value(metrics, 'temperature_c', 'temperature', default=0.0),
                    hamiltonian=orchestrate_data.get('hamiltonian', 0.0),
                    gateway_action=orchestrate_data.get('action', 'CONTINUE')
                )
                
                logger.info(
                    f"Telemetry: VRAM {vram_used_mb:.1f}/{vram_total_mb:.1f}MB "
                    f"({vram_percent:.1f}%), Temp {result.gpu_temp_celsius:.1f}°C, "
                    f"H(s)={result.hamiltonian:.2f}, Action={result.gateway_action}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Telemetry cycle failed: {e}")
            # Return mock data on failure
            return TelemetryCycleResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                vram_used_mb=0.0,
                vram_total_mb=4096.0,
                vram_percent=0.0,
                gpu_temp_celsius=0.0,
                hamiltonian=0.0,
                gateway_action='CONTINUE'
            )
    
    def apply_exchange_operator(self, state_vector: torch.Tensor) -> torch.Tensor:
        """
        Apply EnKG exchange operator M = κI + γσ_x to state vector
        
        Args:
            state_vector: Input tensor (must be contiguous, even final dimension)
        
        Returns:
            Transformed tensor via Triton kernel (or CPU fallback)
        """
        if not state_vector.is_contiguous():
            state_vector = state_vector.contiguous()
        
        if state_vector.shape[-1] % 2 != 0:
            # Pad to even dimension
            pad_size = 1
            state_vector = torch.nn.functional.pad(state_vector, (0, pad_size))
            logger.warning(f"Padded state vector to even dimension: {state_vector.shape}")
        
        # Apply EnKG operator
        output = apply_M_matrix(state_vector, kappa=self.kappa, gamma=self.gamma)
        
        logger.info(f"Applied EnKG operator: input shape {state_vector.shape} -> output shape {output.shape}")
        
        return output
    
    def validate_output(self, payload: Dict[str, Any]) -> str:
        """
        Validate orchestration output via Agent 3 (Seismic Tree-of-Thoughts)
        
        Args:
            payload: Output payload to validate (includes telemetry, state, etc.)
        
        Returns:
            Validation state: NULL | DUCTILE | CRYSTALLINE
        """
        if self.agent3_validator is None:
            logger.warning("Agent 3 Validator not available, returning NULL")
            return "NULL"
        
        try:
            # Run validation
            validation_result = self.agent3_validator.validate(payload)
            
            logger.info(f"Validation state: {validation_result.state}")
            logger.debug(f"Validation details: {validation_result.evaluation_summary}")
            
            return validation_result.state
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return "NULL"
    
    async def run_full_cycle(
        self,
        state_vector: Optional[torch.Tensor] = None,
        kappa: Optional[float] = None,
        gamma: Optional[float] = None
    ) -> OrchestrationResult:
        """
        Execute a complete Yennefer orchestration cycle
        
        Workflow:
        1. Run telemetry cycle (Gateway query)
        2. Apply EnKG exchange operator to state vector
        3. Validate output via Agent 3
        4. Return orchestration result
        
        Args:
            state_vector: Input state vector (generates random if None)
            kappa: Identity coefficient (uses default if None)
            gamma: Exchange coefficient (uses default if None)
        
        Returns:
            OrchestrationResult with telemetry, output, and validation
        """
        start_time = time.perf_counter()
        
        # Update kernel parameters if provided
        if kappa is not None and gamma is not None:
            self.initialize_enkg_kernel(kappa, gamma)
        
        # Step 1: Run telemetry cycle
        logger.info("Step 1: Running telemetry cycle...")
        telemetry = await self.run_telemetry_cycle()
        
        # Step 2: Generate or use provided state vector
        if state_vector is None:
            # Generate random state vector (even dimension)
            vector_size = 1024  # Default size
            state_vector = torch.randn(vector_size, device=self.device)
            logger.info(f"Generated random state vector: shape {state_vector.shape}")
        
        # Step 3: Apply EnKG exchange operator
        logger.info("Step 2: Applying EnKG exchange operator...")
        enkg_output = self.apply_exchange_operator(state_vector)
        
        # Step 4: Prepare validation payload
        validation_payload = {
            "telemetry": asdict(telemetry),
            "enkg_output": {
                "shape": list(enkg_output.shape),
                "dtype": str(enkg_output.dtype),
                "device": str(enkg_output.device),
                "mean": float(enkg_output.mean().item()),
                "std": float(enkg_output.std().item()),
                "min": float(enkg_output.min().item()),
                "max": float(enkg_output.max().item())
            },
            "kernel_params": {
                "kappa": self.kappa,
                "gamma": self.gamma
            },
            "ashard_compliance": {
                "vram_within_limit": telemetry.vram_percent < 90.0,
                "temperature_safe": telemetry.gpu_temp_celsius < self.ashard_config['ashard']['thermal']['warn_threshold']
            }
        }
        
        # Step 5: Validate via Agent 3
        logger.info("Step 3: Validating output via Agent 3...")
        validation_state = self.validate_output(validation_payload)
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        result = OrchestrationResult(
            telemetry=telemetry,
            enkg_output=enkg_output,
            validation_state=validation_state,
            validation_details=validation_payload,
            execution_time_ms=execution_time_ms
        )
        
        logger.info(
            f"Orchestration cycle complete: {execution_time_ms:.2f}ms, "
            f"State={validation_state}, Action={telemetry.gateway_action}"
        )
        
        return result


# FastAPI endpoint integration (optional, can be added to web_ui.py)
def create_yennefer_endpoint(app):
    """
    Add /v1/yennefer endpoint to FastAPI app
    
    Usage:
        from orchestrator.yennefer_orchestrator import create_yennefer_endpoint
        create_yennefer_endpoint(app)
    """
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    
    class YenneferRequest(BaseModel):
        kappa: Optional[float] = 0.7
        gamma: Optional[float] = 0.3
        vector_size: Optional[int] = 1024
    
    router = APIRouter(prefix="/v1", tags=["yennefer"])
    
    orchestrator = YenneferOrchestrator()
    
    @router.post("/yennefer")
    async def run_yennefer_orchestration(request: YenneferRequest):
        """
        Run a complete Yennefer orchestration cycle
        
        Returns telemetry, EnKG output stats, and Agent 3 validation state
        """
        try:
            # Generate state vector
            state_vector = torch.randn(request.vector_size, device=orchestrator.device)
            
            # Run cycle
            result = await orchestrator.run_full_cycle(
                state_vector=state_vector,
                kappa=request.kappa,
                gamma=request.gamma
            )
            
            # Return JSON-serializable result
            return {
                "status": "success",
                "telemetry": asdict(result.telemetry),
                "enkg_output_stats": result.validation_details["enkg_output"],
                "validation_state": result.validation_state,
                "execution_time_ms": result.execution_time_ms,
                "kernel_params": {
                    "kappa": request.kappa,
                    "gamma": request.gamma
                }
            }
            
        except Exception as e:
            logger.error(f"Yennefer orchestration failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    app.include_router(router)
    logger.info("Yennefer endpoint registered at /v1/yennefer")


if __name__ == '__main__':
    # Test orchestrator
    import argparse
    
    parser = argparse.ArgumentParser(description="Yennefer Orchestrator Test")
    parser.add_argument('--kappa', type=float, default=0.7, help='Identity coefficient')
    parser.add_argument('--gamma', type=float, default=0.3, help='Exchange coefficient')
    parser.add_argument('--size', type=int, default=1024, help='State vector size')
    args = parser.parse_args()
    
    async def main():
        orchestrator = YenneferOrchestrator()
        
        # Run single cycle
        result = await orchestrator.run_full_cycle(
            kappa=args.kappa,
            gamma=args.gamma
        )
        
        print("\n" + "="*60)
        print("YENNEFER ORCHESTRATION RESULT")
        print("="*60)
        print(f"Execution Time: {result.execution_time_ms:.2f}ms")
        print(f"\nTelemetry:")
        print(f"  VRAM: {result.telemetry.vram_used_mb:.1f}/{result.telemetry.vram_total_mb:.1f}MB ({result.telemetry.vram_percent:.1f}%)")
        print(f"  Temp: {result.telemetry.gpu_temp_celsius:.1f}°C")
        print(f"  Hamiltonian: {result.telemetry.hamiltonian:.3f}")
        print(f"  Gateway Action: {result.telemetry.gateway_action}")
        print(f"\nEnKG Output:")
        print(f"  Shape: {result.enkg_output.shape}")
        print(f"  Mean: {result.enkg_output.mean().item():.4f}")
        print(f"  Std: {result.enkg_output.std().item():.4f}")
        print(f"\nValidation State: {result.validation_state}")
        print("="*60)
    
    asyncio.run(main())
