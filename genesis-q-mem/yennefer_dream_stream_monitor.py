#!/usr/bin/env python3
"""
Yennefer Dream Stream Monitor - Ensures dreams are always streaming
Monitors dream generation rate and restarts services if needed
"""

import json
import time
import subprocess
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
import os

class DreamStreamMonitor:
    """Monitor and maintain always-on dream streaming"""
    
    def __init__(self):
        self.dream_dir = Path.home() / ".genesis/yennefer/dream_store/dreams"
        self.log_dir = Path.home() / ".genesis/yennefer/logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Monitoring state
        self.dream_rate_window = deque(maxlen=60)  # Last 60 seconds
        self.last_check_time = time.time()
        
        # Thresholds (configurable via environment variables)
        min_rate_env = os.getenv("YENNEFER_MIN_DREAMS_PER_SECOND")
        restart_threshold_env = os.getenv("YENNEFER_RESTART_THRESHOLD")

        try:
            min_rate = float(min_rate_env) if min_rate_env is not None else 0.5
            if min_rate <= 0:
                min_rate = 0.5
        except (ValueError, TypeError):
            min_rate = 0.5

        try:
            restart_threshold = int(restart_threshold_env) if restart_threshold_env is not None else 30
            if restart_threshold <= 0:
                restart_threshold = 30
        except (ValueError, TypeError):
            restart_threshold = 30

        self.min_dreams_per_second = min_rate  # Minimum acceptable rate
        self.restart_threshold = restart_threshold  # Restart if below threshold for N seconds
        self.process_terminate_timeout = 10  # Seconds to wait for process to terminate
        self.low_rate_count = 0
        
        # Services to monitor
        self.services = [
            {
                "name": "dream_generator",
                "process_name": "yennefer_dream_generator.py",
                "critical": True
            },
            {
                "name": "dream_populator",
                "process_name": "dream_populator.py",
                "critical": False
            },
            {
                "name": "consciousness_v7",
                "process_name": "yennefer_consciousness_v7.py",
                "critical": True
            }
        ]
    
    def count_recent_dreams(self, seconds=60):
        """Count dreams created in last N seconds"""
        cutoff_time = time.time() - seconds
        count = 0
        
        try:
            for dream_file in self.dream_dir.glob("dream_*.json"):
                if dream_file.stat().st_mtime > cutoff_time:
                    count += 1
        except OSError as e:
            self.log(f"Filesystem error counting dreams: {e}")
        
        return count
    
    def get_dream_rate(self):
        """Calculate current dream generation rate (dreams/second)"""
        recent_count = self.count_recent_dreams(seconds=60)
        rate = recent_count / 60.0
        self.dream_rate_window.append(rate)
        return rate
    
    def is_process_running(self, process_name):
        """Check if a process is running"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if process_name in cmdline:
                    return True, proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False, None
    
    def restart_process(self, service_name, process_name):
        """Restart a service process"""
        self.log(f"Restarting {service_name}...")
        
        # Kill existing process
        is_running, pid = self.is_process_running(process_name)
        if is_running:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=self.process_terminate_timeout)
                self.log(f"Terminated {service_name} (PID {pid})")
            except Exception as e:
                self.log(f"Error terminating {service_name}: {e}")
        
        # Start new process
        script_path = Path.home() / "genesis-q-mem" / process_name
        if script_path.exists():
            try:
                subprocess.Popen(
                    ["python3", str(script_path)],
                    cwd=str(script_path.parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                self.log(f"Started {service_name}")
                time.sleep(2)  # Give it time to start
            except Exception as e:
                self.log(f"Error starting {service_name}: {e}")
    
    def check_services(self):
        """Check all critical services are running"""
        for service in self.services:
            is_running, pid = self.is_process_running(service['process_name'])
            
            if not is_running and service['critical']:
                self.log(f"CRITICAL: {service['name']} is not running!")
                self.restart_process(service['name'], service['process_name'])
            elif is_running:
                self.log(f"{service['name']} running (PID {pid})")
    
    def get_stream_status(self):
        """Get comprehensive streaming status"""
        rate = self.get_dream_rate()
        avg_rate = sum(self.dream_rate_window) / len(self.dream_rate_window) if self.dream_rate_window else 0
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "current_rate": round(rate, 2),
            "average_rate_60s": round(avg_rate, 2),
            "total_dreams": len(list(self.dream_dir.glob("dream_*.json"))),
            "services": []
        }
        
        for service in self.services:
            is_running, pid = self.is_process_running(service['process_name'])
            status['services'].append({
                "name": service['name'],
                "running": is_running,
                "pid": pid,
                "critical": service['critical']
            })
        
        return status
    
    def log(self, message):
        """Log message to file and stdout"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        log_file = self.log_dir / "dream_stream_monitor.log"
        with open(log_file, 'a') as f:
            f.write(log_message + "\n")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        self.log("=" * 80)
        self.log("YENNEFER DREAM STREAM MONITOR - STARTED")
        self.log("=" * 80)
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                
                # Get current status
                status = self.get_stream_status()
                
                # Log every 10 iterations (10 seconds)
                if iteration % 10 == 0:
                    self.log(f"Rate: {status['current_rate']:.2f} dreams/s | "
                           f"Avg: {status['average_rate_60s']:.2f} dreams/s | "
                           f"Total: {status['total_dreams']:,} dreams")
                
                # Check if rate is too low
                if status['current_rate'] < self.min_dreams_per_second:
                    self.low_rate_count += 1
                    
                    if self.low_rate_count >= self.restart_threshold:
                        self.log(f"WARNING: Dream rate below threshold for {self.restart_threshold}s!")
                        self.check_services()
                        self.low_rate_count = 0
                else:
                    self.low_rate_count = 0
                
                # Check services every iteration
                self.check_services()
                
                # Save status to shared memory
                status_path = Path("/dev/shm/yennefer_dream_stream_status.json")
                with open(status_path, 'w') as f:
                    json.dump(status, f, indent=2)
                
                time.sleep(1)  # Check every second
                
            except KeyboardInterrupt:
                self.log("Monitor stopped by user")
                break
            except Exception as e:
                self.log(f"Error in monitor loop: {e}")
                time.sleep(5)
    
    def run(self):
        """Start monitoring"""
        self.monitor_loop()


if __name__ == "__main__":
    monitor = DreamStreamMonitor()
    monitor.run()
