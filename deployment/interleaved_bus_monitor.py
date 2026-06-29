#!/usr/bin/env python3
"""
MARU Interleaved Bus Monitor
Envelope Version: 0.3.0
GTX 1650 4GB VRAM Substrate

Monitors JAX and CUDA-Q kernel execution states and enforces
interleaved bus protocol to prevent VRAM conflicts.

Yield Logic:
- If hyperNEAT pulsing OR qmem active → CUDA-Q yields
- If CUDA-Q active AND JAX memory > 42% → JAX throttles
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Dict, Optional

ENVELOPE_VERSION = "0.3.0"
BUS_STATE_LOG = "/var/maru/bus_state.log"
METRICS_PORT = 9090
POLL_INTERVAL_SEC = 1.0

JAX_MEMORY_THROTTLE_THRESHOLD = 0.42
JAX_MEMORY_WARNING_THRESHOLD = 0.40

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [BUS] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(BUS_STATE_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BusState:
    """Global bus state tracker"""
    def __init__(self):
        self.jax_memory_fraction = 0.0
        self.jax_memory_mb = 0.0
        self.jax_active = False
        self.hyperneat_pulsing = False
        self.qmem_active = False
        
        self.cuda_q_active = False
        self.cuda_q_kernel_state = "IDLE"  # IDLE | RUNNING | YIELDING | BLOCKED
        self.cuda_q_lanes = [False] * 4
        
        self.yield_count = 0
        self.throttle_count = 0
        self.conflict_count = 0
        
        self.last_update = datetime.utcnow()
        
    def to_dict(self) -> Dict:
        return {
            "envelope_version": ENVELOPE_VERSION,
            "timestamp": self.last_update.isoformat() + "Z",
            "jax": {
                "memory_fraction": round(self.jax_memory_fraction, 4),
                "memory_mb": round(self.jax_memory_mb, 2),
                "active": self.jax_active,
                "hyperneat_pulsing": self.hyperneat_pulsing,
                "qmem_active": self.qmem_active
            },
            "cuda_q": {
                "active": self.cuda_q_active,
                "kernel_state": self.cuda_q_kernel_state,
                "lanes": self.cuda_q_lanes
            },
            "bus_stats": {
                "yield_count": self.yield_count,
                "throttle_count": self.throttle_count,
                "conflict_count": self.conflict_count
            }
        }


bus_state = BusState()


def check_jax_memory() -> tuple[float, float]:
    """
    Check JAX memory usage via jax.devices()[0].memory_stats()
    Returns: (fraction_used, mb_used)
    """
    try:
        import jax
        device = jax.devices()[0]
        stats = device.memory_stats()
        
        if stats and 'bytes_in_use' in stats and 'bytes_limit' in stats:
            bytes_in_use = stats['bytes_in_use']
            bytes_limit = stats['bytes_limit']
            
            if bytes_limit > 0:
                fraction = bytes_in_use / bytes_limit
                mb_used = bytes_in_use / (1024 * 1024)
                return (fraction, mb_used)
        
        return (0.0, 0.0)
    except (ImportError, IndexError, KeyError, Exception) as e:
        logger.debug(f"JAX memory check unavailable: {e}")
        return (0.0, 0.0)


def detect_hyperneat_pulsing() -> bool:
    """
    Detect hyperNEAT pulsing state
    In production, this would check actual hyperNEAT state
    """
    state_file = os.environ.get('NOX_ENGINE_STATE', '/var/maru/nox_state.json')
    try:
        if os.path.exists(state_file):
            with open(state_file) as f:
                data = json.load(f)
                return data.get('hyperneat', {}).get('pulsing', False)
    except (json.JSONDecodeError, IOError):
        pass
    return False


def detect_qmem_active() -> bool:
    """
    Detect quantum memory (qmem) active state
    In production, this would check actual qmem state
    """
    return os.path.exists('/var/maru/qmem.lock')


def detect_cuda_q_kernel_state() -> tuple[bool, str]:
    """
    Detect CUDA-Q kernel execution state
    Returns: (active, state)
    """
    kernel_state_file = '/var/maru/cuda_q_kernel.state'
    try:
        if os.path.exists(kernel_state_file):
            with open(kernel_state_file) as f:
                state = f.read().strip().upper()
                active = state in ['RUNNING', 'YIELDING']
                return (active, state)
    except IOError:
        pass
    return (False, 'IDLE')


def enforce_interleaved_bus_protocol():
    """
    Core interleaved bus protocol enforcement
    
    Rules:
    1. If hyperNEAT pulsing OR qmem active → CUDA-Q yields
    2. If CUDA-Q active AND JAX memory > 42% → JAX throttles
    """
    global bus_state
    
    jax_frac, jax_mb = check_jax_memory()
    bus_state.jax_memory_fraction = jax_frac
    bus_state.jax_memory_mb = jax_mb
    bus_state.jax_active = jax_frac > 0.01
    
    bus_state.hyperneat_pulsing = detect_hyperneat_pulsing()
    bus_state.qmem_active = detect_qmem_active()
    
    cuda_q_active, cuda_q_state = detect_cuda_q_kernel_state()
    bus_state.cuda_q_active = cuda_q_active
    bus_state.cuda_q_kernel_state = cuda_q_state
    
    actions_taken = []
    
    # Rule 1: CUDA-Q yields to JAX priority workloads
    if bus_state.hyperneat_pulsing or bus_state.qmem_active:
        if bus_state.cuda_q_active and bus_state.cuda_q_kernel_state == 'RUNNING':
            yield_cuda_q()
            bus_state.yield_count += 1
            actions_taken.append('CUDA-Q_YIELD')
            logger.info(f"✓ CUDA-Q yielded (hyperNEAT: {bus_state.hyperneat_pulsing}, qmem: {bus_state.qmem_active})")
    
    # Rule 2: JAX throttles if consuming too much during CUDA-Q work
    if bus_state.cuda_q_active and bus_state.jax_memory_fraction > JAX_MEMORY_THROTTLE_THRESHOLD:
        throttle_jax()
        bus_state.throttle_count += 1
        actions_taken.append('JAX_THROTTLE')
        logger.warning(f"⚠ JAX throttled (memory: {bus_state.jax_memory_fraction:.2%}, threshold: {JAX_MEMORY_THROTTLE_THRESHOLD:.2%})")
    
    # Detect conflicts (both trying to run simultaneously at high load)
    if bus_state.jax_active and bus_state.cuda_q_active:
        if bus_state.jax_memory_fraction > JAX_MEMORY_WARNING_THRESHOLD:
            bus_state.conflict_count += 1
            logger.warning(f"⚠ Potential bus conflict (JAX: {bus_state.jax_memory_fraction:.2%}, CUDA-Q: {bus_state.cuda_q_kernel_state})")
    
    bus_state.last_update = datetime.utcnow()
    
    if actions_taken:
        logger.info(f"Bus actions: {', '.join(actions_taken)}")


def yield_cuda_q():
    """Signal CUDA-Q kernel to yield execution"""
    yield_signal_file = '/var/maru/cuda_q_yield.signal'
    try:
        with open(yield_signal_file, 'w') as f:
            f.write(f"{datetime.utcnow().isoformat()}Z\n")
    except IOError as e:
        logger.error(f"Failed to signal CUDA-Q yield: {e}")


def throttle_jax():
    """Signal JAX to throttle execution"""
    throttle_signal_file = '/var/maru/jax_throttle.signal'
    try:
        with open(throttle_signal_file, 'w') as f:
            f.write(f"{datetime.utcnow().isoformat()}Z\n")
    except IOError as e:
        logger.error(f"Failed to signal JAX throttle: {e}")


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint"""
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            metrics = bus_state.to_dict()
            self.wfile.write(json.dumps(metrics, indent=2).encode())
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            health = {
                "status": "healthy",
                "envelope_version": ENVELOPE_VERSION,
                "service": "interleaved_bus_monitor"
            }
            self.wfile.write(json.dumps(health).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default HTTP logs"""
        pass


def run_metrics_server():
    """Run HTTP metrics server in background thread"""
    server = HTTPServer(('0.0.0.0', METRICS_PORT), MetricsHandler)
    logger.info(f"Metrics server listening on :{METRICS_PORT}/metrics")
    server.serve_forever()


def main():
    logger.info(f"MARU Interleaved Bus Monitor starting (envelope: {ENVELOPE_VERSION})")
    logger.info(f"GTX 1650 4GB VRAM substrate")
    logger.info(f"Partitioning: JAX 45% | CUDA-Q 55%")
    logger.info(f"Poll interval: {POLL_INTERVAL_SEC}s")
    logger.info(f"Bus state log: {BUS_STATE_LOG}")
    
    metrics_thread = Thread(target=run_metrics_server, daemon=True)
    metrics_thread.start()
    
    logger.info("✓ Interleaved bus monitor operational")
    
    try:
        while True:
            enforce_interleaved_bus_protocol()
            time.sleep(POLL_INTERVAL_SEC)
    
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
