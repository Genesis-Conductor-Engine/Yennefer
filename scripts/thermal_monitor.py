#!/usr/bin/env python3
"""
aSHARD Thermal Monitor
Continuously monitors GPU temperature and integrates with Diamond Gateway
Implements thermal throttling protection
"""
import sys
import time
import yaml
import signal
from pathlib import Path
from typing import Optional

class ThermalMonitor:
    def __init__(self, config_path: Path):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.ashard = self.config["ashard"]
        self.thermal_config = self.ashard["thermal"]
        self.running = True
        
        # Initialize pynvml
        try:
            import pynvml
            pynvml.nvmlInit()
            device_idx = int(self.ashard["device"].split(":")[1])
            self.handle = pynvml.nvmlDeviceGetHandleByIndex(device_idx)
            self.pynvml = pynvml
        except Exception as e:
            print(f"Failed to initialize NVML: {e}")
            sys.exit(1)
    
    def get_temperature(self) -> float:
        """Get current GPU temperature in °C"""
        return self.pynvml.nvmlDeviceGetTemperature(
            self.handle, 
            self.pynvml.NVML_TEMPERATURE_GPU
        )
    
    def get_vram_usage(self) -> dict:
        """Get current VRAM usage"""
        mem_info = self.pynvml.nvmlDeviceGetMemoryInfo(self.handle)
        return {
            "used": mem_info.used,
            "total": mem_info.total,
            "free": mem_info.free,
            "utilization": mem_info.used / mem_info.total
        }
    
    def check_thermal_status(self, temp: float) -> str:
        """Check thermal status against thresholds"""
        if temp >= self.thermal_config["critical_threshold"]:
            return "CRITICAL"
        elif temp >= self.thermal_config["warn_threshold"]:
            return "WARNING"
        else:
            return "OK"
    
    def send_gateway_metrics(self, temp: float, vram: dict) -> Optional[dict]:
        """Send metrics to Diamond Gateway"""
        import requests
        import os
        
        gateway_config = self.ashard.get("gateway", {})
        metrics_url = gateway_config.get("metrics_url")
        auth_var = gateway_config.get("auth_env_var")
        
        if not metrics_url or not auth_var:
            return None
        
        token = os.getenv(auth_var)
        if not token:
            return None
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(metrics_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        
        return None
    
    def handle_thermal_event(self, temp: float, status: str):
        """Handle thermal events"""
        if status == "CRITICAL":
            print(f"🔥 CRITICAL: Temperature {temp:.1f}°C - EMERGENCY STOP")
            print("Recommendation: Stop all GPU workloads immediately")
            # Could send emergency signal to orchestrator here
        
        elif status == "WARNING":
            print(f"⚠️  WARNING: Temperature {temp:.1f}°C - Throttling recommended")
            throttle = self.thermal_config["throttle_factor"]
            print(f"Recommendation: Reduce workload to {throttle*100:.0f}% capacity")
            # Could send throttle signal to orchestrator here
    
    def run(self):
        """Main monitoring loop"""
        check_interval = self.thermal_config["check_interval"]
        
        print("=== aSHARD Thermal Monitor ===")
        print(f"Device: {self.ashard['device']}")
        print(f"Warning threshold: {self.thermal_config['warn_threshold']}°C")
        print(f"Critical threshold: {self.thermal_config['critical_threshold']}°C")
        print(f"Check interval: {check_interval}s")
        print("\nPress Ctrl+C to stop\n")
        
        # Register signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        last_status = "OK"
        
        try:
            while self.running:
                temp = self.get_temperature()
                vram = self.get_vram_usage()
                status = self.check_thermal_status(temp)
                
                # Print current stats
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Temp: {temp:.1f}°C | "
                      f"VRAM: {vram['used']/1024**3:.2f}/{vram['total']/1024**3:.2f}GB "
                      f"({vram['utilization']*100:.1f}%) | Status: {status}")
                
                # Handle status changes
                if status != last_status:
                    self.handle_thermal_event(temp, status)
                    last_status = status
                
                # Try to send to gateway (optional, don't fail if unavailable)
                gateway_metrics = self.send_gateway_metrics(temp, vram)
                if gateway_metrics:
                    # Gateway might have additional info
                    pass
                
                time.sleep(check_interval)
        
        finally:
            self.cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nShutdown signal received...")
        self.running = False
    
    def cleanup(self):
        """Cleanup resources"""
        print("Shutting down thermal monitor...")
        self.pynvml.nvmlShutdown()

def main():
    config_path = Path(__file__).parent.parent / "config" / "ashard_config.yaml"
    
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    
    monitor = ThermalMonitor(config_path)
    monitor.run()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
