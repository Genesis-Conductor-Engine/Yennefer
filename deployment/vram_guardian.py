#!/usr/bin/env python3
"""
MARU VRAM Guardian
Envelope Version: 0.3.0
GTX 1650 4GB VRAM Substrate

Enforces VRAM ceilings with zero OOM tolerance:
- JAX/hyperNEAT: 1800MB ceiling (45% of 4GB)
- CUDA-Q: 2200MB ceiling (55% of 4GB)

Violations trigger:
1. Grace period warning (5s)
2. Process termination
3. NOX engine reframe on repeated violations
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    print("WARNING: pynvml not available, running in mock mode", file=sys.stderr)

ENVELOPE_VERSION = "0.3.0"
VRAM_VIOLATIONS_LOG = "/var/maru/vram_violations.log"
NOX_ENGINE_STATE = os.environ.get('NOX_ENGINE_STATE', '/var/maru/nox_state.json')

POLL_INTERVAL_SEC = 5.0
GRACE_PERIOD_SEC = 5.0

JAX_VRAM_CEILING_MB = int(os.environ.get('JAX_VRAM_CEILING_MB', '1800'))
CUDA_Q_VRAM_CEILING_MB = int(os.environ.get('CUDA_Q_VRAM_CEILING_MB', '2200'))

VIOLATION_THRESHOLD_FOR_REFRAME = 3
VIOLATION_WINDOW_SEC = 300  # 5 minutes

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [GUARDIAN] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(VRAM_VIOLATIONS_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    pid: int
    name: str
    vram_mb: float
    category: str  # 'jax', 'cuda_q', 'unknown'


@dataclass
class Violation:
    timestamp: datetime
    process: ProcessInfo
    ceiling_mb: float
    overage_mb: float


class VRAMGuardian:
    def __init__(self):
        self.gpu_handle = None
        self.violations: List[Violation] = []
        self.reframe_triggered = False
        
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                logger.info("✓ NVML initialized")
            except Exception as e:
                logger.error(f"Failed to initialize NVML: {e}")
                self.gpu_handle = None
    
    def get_gpu_processes(self) -> List[ProcessInfo]:
        """Get all processes using GPU VRAM"""
        processes = []
        
        if not self.gpu_handle:
            return processes
        
        try:
            gpu_processes = pynvml.nvmlDeviceGetComputeRunningProcesses(self.gpu_handle)
            
            for proc in gpu_processes:
                try:
                    vram_mb = proc.usedGpuMemory / (1024 * 1024)
                    
                    name = self._get_process_name(proc.pid)
                    category = self._categorize_process(name, proc.pid)
                    
                    processes.append(ProcessInfo(
                        pid=proc.pid,
                        name=name,
                        vram_mb=vram_mb,
                        category=category
                    ))
                
                except Exception as e:
                    logger.debug(f"Failed to get info for PID {proc.pid}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to enumerate GPU processes: {e}")
        
        return processes
    
    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID"""
        try:
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'comm='],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return f"pid:{pid}"
    
    def _categorize_process(self, name: str, pid: int) -> str:
        """Categorize process as JAX, CUDA-Q, or unknown"""
        name_lower = name.lower()
        
        if any(x in name_lower for x in ['python', 'jax', 'xla', 'hyperneat']):
            cmdline = self._get_process_cmdline(pid)
            if cmdline:
                cmdline_lower = cmdline.lower()
                if any(x in cmdline_lower for x in ['jax', 'hyperneat', 'qmem']):
                    return 'jax'
                elif any(x in cmdline_lower for x in ['cuda-q', 'cudaq', 'cuquantum']):
                    return 'cuda_q'
            return 'jax'  # Default Python processes to JAX
        
        if any(x in name_lower for x in ['cuda', 'cudaq', 'cuquantum']):
            return 'cuda_q'
        
        return 'unknown'
    
    def _get_process_cmdline(self, pid: int) -> Optional[str]:
        """Get full command line for process"""
        try:
            with open(f'/proc/{pid}/cmdline', 'r') as f:
                return f.read().replace('\0', ' ')
        except Exception:
            return None
    
    def check_violations(self) -> List[Violation]:
        """Check for VRAM ceiling violations"""
        violations = []
        processes = self.get_gpu_processes()
        
        for proc in processes:
            ceiling_mb = None
            
            if proc.category == 'jax':
                ceiling_mb = JAX_VRAM_CEILING_MB
            elif proc.category == 'cuda_q':
                ceiling_mb = CUDA_Q_VRAM_CEILING_MB
            else:
                continue  # Don't enforce on unknown processes
            
            if proc.vram_mb > ceiling_mb:
                overage_mb = proc.vram_mb - ceiling_mb
                violation = Violation(
                    timestamp=datetime.utcnow(),
                    process=proc,
                    ceiling_mb=ceiling_mb,
                    overage_mb=overage_mb
                )
                violations.append(violation)
                
                logger.warning(
                    f"⚠ VRAM VIOLATION: {proc.category.upper()} process "
                    f"[PID {proc.pid}] {proc.name} using {proc.vram_mb:.0f}MB "
                    f"(ceiling: {ceiling_mb}MB, overage: {overage_mb:.0f}MB)"
                )
        
        return violations
    
    def handle_violation(self, violation: Violation):
        """Handle a VRAM violation with grace period"""
        logger.warning(
            f"Grace period: {GRACE_PERIOD_SEC}s for PID {violation.process.pid} "
            f"to reduce VRAM usage"
        )
        
        time.sleep(GRACE_PERIOD_SEC)
        
        current_processes = self.get_gpu_processes()
        still_violating = False
        
        for proc in current_processes:
            if proc.pid == violation.process.pid:
                ceiling = (JAX_VRAM_CEILING_MB if proc.category == 'jax' 
                          else CUDA_Q_VRAM_CEILING_MB)
                if proc.vram_mb > ceiling:
                    still_violating = True
                    break
        
        if still_violating:
            self.terminate_process(violation.process.pid, violation.process.name)
            self.violations.append(violation)
            self.check_reframe_threshold()
        else:
            logger.info(f"✓ PID {violation.process.pid} reduced VRAM within grace period")
    
    def terminate_process(self, pid: int, name: str):
        """Terminate a process violating VRAM ceiling"""
        logger.error(f"🔥 TERMINATING process [PID {pid}] {name} for VRAM violation")
        
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            
            logger.info(f"✓ Process {pid} terminated")
        
        except ProcessLookupError:
            logger.info(f"Process {pid} already terminated")
        except Exception as e:
            logger.error(f"Failed to terminate PID {pid}: {e}")
    
    def check_reframe_threshold(self):
        """Check if we need to trigger NOX reframe"""
        if self.reframe_triggered:
            return
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=VIOLATION_WINDOW_SEC)
        recent_violations = [v for v in self.violations if v.timestamp > cutoff_time]
        
        if len(recent_violations) >= VIOLATION_THRESHOLD_FOR_REFRAME:
            logger.critical(
                f"🚨 REFRAME THRESHOLD EXCEEDED: {len(recent_violations)} violations "
                f"in {VIOLATION_WINDOW_SEC}s window"
            )
            self.trigger_nox_reframe()
            self.reframe_triggered = True
    
    def trigger_nox_reframe(self):
        """Trigger NOX engine reframe"""
        logger.critical("⚡ Triggering NOX engine REFRAME")
        
        try:
            if os.path.exists(NOX_ENGINE_STATE):
                with open(NOX_ENGINE_STATE, 'r') as f:
                    state = json.load(f)
                
                if state.get('nox_engine', {}).get('reframe_enabled', True):
                    state.setdefault('reframe_events', [])
                    state['reframe_events'].append({
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'trigger': 'vram_violations',
                        'violation_count': len(self.violations),
                        'envelope_version': ENVELOPE_VERSION
                    })
                    
                    with open(NOX_ENGINE_STATE, 'w') as f:
                        json.dump(state, f, indent=2)
                    
                    logger.info(f"✓ NOX reframe event recorded to {NOX_ENGINE_STATE}")
                else:
                    logger.warning("NOX reframe is disabled in state file")
            else:
                logger.warning(f"NOX state file not found: {NOX_ENGINE_STATE}")
        
        except Exception as e:
            logger.error(f"Failed to trigger NOX reframe: {e}")
    
    def report_status(self):
        """Log current VRAM status"""
        processes = self.get_gpu_processes()
        
        jax_total = sum(p.vram_mb for p in processes if p.category == 'jax')
        cuda_q_total = sum(p.vram_mb for p in processes if p.category == 'cuda_q')
        
        logger.info(
            f"VRAM Status: JAX {jax_total:.0f}MB/{JAX_VRAM_CEILING_MB}MB "
            f"({jax_total/JAX_VRAM_CEILING_MB*100:.1f}%), "
            f"CUDA-Q {cuda_q_total:.0f}MB/{CUDA_Q_VRAM_CEILING_MB}MB "
            f"({cuda_q_total/CUDA_Q_VRAM_CEILING_MB*100:.1f}%)"
        )
    
    def run(self):
        """Main guardian loop"""
        logger.info(f"MARU VRAM Guardian starting (envelope: {ENVELOPE_VERSION})")
        logger.info(f"GTX 1650 4GB VRAM substrate - Zero OOM tolerance")
        logger.info(f"JAX ceiling: {JAX_VRAM_CEILING_MB}MB (45%)")
        logger.info(f"CUDA-Q ceiling: {CUDA_Q_VRAM_CEILING_MB}MB (55%)")
        logger.info(f"Poll interval: {POLL_INTERVAL_SEC}s")
        logger.info(f"Grace period: {GRACE_PERIOD_SEC}s")
        logger.info(f"Reframe threshold: {VIOLATION_THRESHOLD_FOR_REFRAME} violations in {VIOLATION_WINDOW_SEC}s")
        logger.info(f"Violations log: {VRAM_VIOLATIONS_LOG}")
        
        if not PYNVML_AVAILABLE or not self.gpu_handle:
            logger.warning("⚠ Running in degraded mode (NVML unavailable)")
        
        logger.info("✓ VRAM Guardian operational")
        
        cycle = 0
        
        try:
            while True:
                violations = self.check_violations()
                
                for violation in violations:
                    self.handle_violation(violation)
                
                if cycle % 12 == 0:  # Every minute
                    self.report_status()
                
                cycle += 1
                time.sleep(POLL_INTERVAL_SEC)
        
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            if PYNVML_AVAILABLE:
                pynvml.nvmlShutdown()
            sys.exit(0)
        
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            if PYNVML_AVAILABLE:
                pynvml.nvmlShutdown()
            sys.exit(1)


def main():
    guardian = VRAMGuardian()
    guardian.run()


if __name__ == '__main__':
    main()
