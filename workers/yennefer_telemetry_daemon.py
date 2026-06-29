#!/usr/bin/env python3
"""
Yennefer Thermodynamic Telemetry Daemon
Hourly emitter to Notion API with ε hysteresis and payload sanitization
Envelope Version: 0.3.0
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from workers.thermodynamic_simulator import ThermodynamicSimulator, epsilon_with_hysteresis
from workers.notion_sanitizer import NotionSanitizer

try:
    from notion_client import Client as NotionClient
except ImportError:
    NotionClient = None
    print("WARNING: notion-client not installed. Install with: pip install notion-client")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/diamondnode/diamondnode-unified-inference/logs/yennefer_telemetry.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class YenneferTelemetryDaemon:
    """
    Hourly thermodynamic telemetry daemon.
    Computes metrics, sanitizes, and posts to Notion.
    """
    
    def __init__(self, config_path: str = None):
        self.envelope_version = "0.3.0"
        
        # Load config
        if config_path is None:
            config_path = "/home/diamondnode/diamondnode-unified-inference/config/yennefer_config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize components
        sim_steps = self.config['yennefer']['thermodynamic']['electron_sim_steps']
        self.simulator = ThermodynamicSimulator(self.envelope_version, sim_steps)
        self.sanitizer = NotionSanitizer(self.envelope_version)
        
        # Initialize Notion client
        notion_token = os.getenv('NOTION_TOKEN')
        if notion_token and NotionClient:
            self.notion_client = NotionClient(auth=notion_token)
            logger.info("Notion client initialized")
        else:
            self.notion_client = None
            logger.warning("Notion client not available")
        
        # State tracking
        self.prev_epsilon = 0.5
        self.hold_cycles = 0
        self.run_count = 0
        
    def read_vram_jax(self) -> float:
        """
        Read GPU VRAM percentage. Prefers cupy (real CUDA driver query),
        falls back to JAX device stats, then mock.
        Returns percentage (0-100).
        """
        try:
            import cupy
            free, total = cupy.cuda.runtime.memGetInfo()
            if total > 0:
                used = total - free
                pct = (used / total) * 100.0
                return min(100.0, pct)
        except Exception as e:
            logger.warning(f"cupy VRAM read failed: {e}")

        try:
            import jax
            devices = jax.devices()
            if len(devices) > 0:
                stats = devices[0].memory_stats()
                if stats:
                    used = stats.get('bytes_in_use', 0)
                    limit = stats.get('bytes_limit', 1)
                    pct = (used / limit) * 100.0 if limit > 0 else 0.0
                    return min(100.0, pct)
        except Exception as e:
            logger.warning(f"jax VRAM read failed: {e}")

        # Fallback: mock value (signals "no real reader available")
        mock_pct = 35.0 + (time.time() % 100) / 10.0
        return mock_pct
    
    def check_cuda_q_status(self) -> str:
        """
        Check CUDA-Q kernel status via process monitoring.
        Returns: "ACTIVE" | "IDLE" | "UNKNOWN"
        """
        try:
            import subprocess
            result = subprocess.run(
                ['pgrep', '-f', 'cuda-q'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return "ACTIVE"
            return "IDLE"
        except Exception as e:
            logger.warning(f"Failed to check CUDA-Q status: {e}")
            return "UNKNOWN"
    
    def compute_metrics(self) -> dict:
        """
        Compute all thermodynamic metrics.
        """
        # Read system state
        vram_jax_pct = self.read_vram_jax()
        vram_jax_ratio = vram_jax_pct / 100.0
        cuda_q_status = self.check_cuda_q_status()
        cuda_q_active = (cuda_q_status == "ACTIVE")
        
        # Run thermodynamic simulation
        sim_result = self.simulator.simulate_electron_movement(
            vram_jax_ratio,
            cuda_q_active
        )
        
        eta_thermo = sim_result["eta_thermo"]
        current_epsilon = sim_result["epsilon"]
        delta_q = sim_result["delta_q"]
        
        # Apply hysteresis to ε
        gamma = self.config['yennefer']['hysteresis']['gamma_buffer']
        epsilon = epsilon_with_hysteresis(current_epsilon, self.prev_epsilon, gamma)
        
        # Track hold cycles
        if epsilon == self.prev_epsilon:
            self.hold_cycles += 1
        else:
            self.hold_cycles = 0
            self.prev_epsilon = epsilon
        
        # Compute crystalline score
        crystalline_cfg = self.config['yennefer']['crystalline']
        crystalline_score = self.simulator.compute_crystalline_score(
            eta_thermo,
            vram_jax_ratio,
            crystalline_cfg['base_score'],
            crystalline_cfg['vram_penalty_factor'],
            crystalline_cfg['eta_bonus_factor']
        )
        
        # Check for Maru reframe events (placeholder)
        maru_reframe_event = "NONE"
        if vram_jax_pct > self.config['yennefer']['vram_thresholds']['jax_critical'] * 100:
            maru_reframe_event = "VRAM_CRITICAL"
        
        return {
            "eta_thermo": eta_thermo,
            "epsilon": epsilon,
            "gamma": gamma,
            "delta_q": delta_q,
            "vram_jax_pct": vram_jax_pct,
            "cuda_q_kernel_status": cuda_q_status,
            "maru_reframe_event": maru_reframe_event,
            "crystalline_score": crystalline_score,
            "hold_cycles": self.hold_cycles
        }
    
    def post_to_notion(self, metrics: dict) -> bool:
        """
        Post metrics to Notion database.
        Returns True on success.
        """
        if not self.notion_client:
            logger.warning("Notion client not available, skipping POST")
            return False
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Prepare payload
        payload = {
            "eta_thermo": metrics["eta_thermo"],
            "epsilon": metrics["epsilon"],
            "gamma": metrics["gamma"],
            "delta_q": metrics["delta_q"],
            "vram_jax_pct": metrics["vram_jax_pct"],
            "crystalline_score": metrics["crystalline_score"]
        }
        
        # Sanitize payload
        status, sanitized = self.sanitizer.validate_payload(payload)
        
        if status == "REJECTED":
            logger.error("Payload rejected by sanitizer, aborting POST")
            return False
        
        # Build Notion properties
        notes = f"Run #{self.run_count} | Hold cycles: {metrics['hold_cycles']} | Envelope: {self.envelope_version}"
        if status == "SANITIZED":
            notes += f" | Sanitized: {sanitized.get('sanitization_notes', 'modified')}"
        
        properties = {
            "Timestamp": {
                "title": [{"text": {"content": timestamp}}]
            },
            "η_thermo": {
                "number": sanitized["eta_thermo"]
            },
            "ε": {
                "number": sanitized["epsilon"]
            },
            "γ": {
                "number": sanitized["gamma"]
            },
            "Δq": {
                "number": sanitized["delta_q"]
            },
            "VRAM_JAX_Pct": {
                "number": sanitized["vram_jax_pct"]
            },
            "CUDA_Q_Kernel_Status": {
                "select": {"name": metrics["cuda_q_kernel_status"]}
            },
            "Crystalline_Score": {
                "number": sanitized["crystalline_score"]
            },
            "Notes": {
                "rich_text": [{"text": {"content": notes}}]
            },
            "Live_Run_Verified": {
                "checkbox": False
            }
        }
        
        # Add Maru reframe event if present
        if "Maru_Reframe_Event" in metrics:
            properties["Maru_Reframe_Event"] = {
                "select": {"name": metrics["maru_reframe_event"]}
            }
        
        try:
            self.notion_client.pages.create(
                parent={"database_id": self.config['yennefer']['notion_db']},
                properties=properties
            )
            logger.info(f"Posted to Notion: η={metrics['eta_thermo']:.4f}, ε={metrics['epsilon']:.4f}, VRAM={metrics['vram_jax_pct']:.2f}%")
            return True
        except Exception as e:
            logger.error(f"Failed to post to Notion: {e}")
            return False
    
    def run_cycle(self):
        """Run single telemetry cycle."""
        logger.info(f"=== Yennefer Telemetry Cycle #{self.run_count} ===")
        
        try:
            # Compute metrics
            metrics = self.compute_metrics()
            logger.info(f"Metrics computed: η={metrics['eta_thermo']:.4f}, ε={metrics['epsilon']:.4f}")
            
            # Post to Notion
            success = self.post_to_notion(metrics)
            
            if success:
                logger.info("Cycle completed successfully")
            else:
                logger.warning("Cycle completed with warnings")
            
            self.run_count += 1
            
        except Exception as e:
            logger.error(f"Cycle failed: {e}", exc_info=True)
    
    def run_daemon(self, oneshot=False):
        """Run daemon with hourly cadence or oneshot."""
        if oneshot:
            logger.info(f"Yennefer Telemetry Daemon v{self.envelope_version} starting (ONESHOT)")
            self.run_cycle()
            return

        cadence_hours = self.config['yennefer']['cadence_hours']
        cadence_seconds = cadence_hours * 3600
        
        logger.info(f"Yennefer Telemetry Daemon v{self.envelope_version} starting")
        logger.info(f"Cadence: {cadence_hours}h ({cadence_seconds}s)")
        logger.info(f"Notion DB: {self.config['yennefer']['notion_db']}")
        
        while True:
            try:
                self.run_cycle()
                logger.info(f"Sleeping for {cadence_hours}h until next cycle...")
                time.sleep(cadence_seconds)
            except KeyboardInterrupt:
                logger.info("Daemon interrupted by user")
                break
            except Exception as e:
                logger.error(f"Daemon error: {e}", exc_info=True)
                logger.info("Retrying in 5 minutes...")
                time.sleep(300)


def main():
    """Entry point for daemon."""
    import sys
    oneshot = "--oneshot" in sys.argv

    # Ensure logs directory exists
    log_dir = Path("/home/diamondnode/diamondnode-unified-inference/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create daemon
    daemon = YenneferTelemetryDaemon()
    
    # Run daemon
    daemon.run_daemon(oneshot=oneshot)


if __name__ == "__main__":
    main()
