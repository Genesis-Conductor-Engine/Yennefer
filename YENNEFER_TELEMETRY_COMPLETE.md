# Yennefer Thermodynamic Telemetry Emitter

**Status:** ✅ Complete - Ready for Deployment  
**Envelope Version:** 0.3.0  
**Notion DB:** `9a32dcb5-00b6-40d7-bd86-43d93965fa82`

## 🎯 Overview

Hourly daemon that computes thermodynamic metrics (η_thermo, ε, γ, Δq) and posts telemetry to Notion with ε hysteresis and payload sanitization.

## 📁 Files Created

```
diamondnode-unified-inference/
├── config/
│   └── yennefer_config.yaml          # Configuration
├── workers/
│   ├── thermodynamic_simulator.py    # Electron movement simulator
│   ├── notion_sanitizer.py           # Payload validation
│   ├── yennefer_telemetry_daemon.py  # Main daemon
│   └── test_yennefer.sh              # Test runner
└── deployment/
    ├── yennefer-telemetry.service    # Systemd service
    └── yennefer-telemetry.env.template  # Environment template
```

## 🔬 Components

### 1. Thermodynamic Simulator (`thermodynamic_simulator.py`)
- Simulates electron trajectories in quantum potentiation field
- Computes **η_thermo** (0.0-1.0): rate of state transitions
- Computes **ε** (energy state): normalized field strength
- Computes **Δq** (0.01-0.15): quantum differentiation delta
- Includes **ε hysteresis**: `|ε_curr - ε_prev| < γ` → hold previous state
- CUDA-Q multilane integration for parallel quantum processing
- Crystalline score computation: `base + η*bonus - vram*penalty`

### 2. Notion Sanitizer (`notion_sanitizer.py`)
- Pre-annealment validation: NaN, inf, out-of-range checks
- Status: `CLEAN` | `SANITIZED` | `REJECTED`
- Rejected payloads → envelope capsule + #!nox reframe log
- Validation summary statistics

### 3. Telemetry Daemon (`yennefer_telemetry_daemon.py`)
- **Hourly cadence** (configurable in YAML)
- Reads VRAM: JAX via `jax.devices()[0].memory_stats()`
- Reads CUDA-Q status: process monitoring (`pgrep -f cuda-q`)
- Computes metrics → sanitizes → POSTs to Notion
- Logs: `/home/diamondnode/diamondnode-unified-inference/logs/yennefer_telemetry.log`
- Notion properties: Timestamp, η_thermo, ε, γ, Δq, VRAM_JAX_Pct, CUDA_Q_Kernel_Status, Crystalline_Score, Notes, Live_Run_Verified

## ⚙️ Configuration

`config/yennefer_config.yaml`:
```yaml
envelope_version: "0.3.0"
yennefer:
  cadence_hours: 1
  notion_db: "9a32dcb5-00b6-40d7-bd86-43d93965fa82"
  hysteresis:
    gamma_buffer: 0.05
    min_hold_cycles: 3
  thermodynamic:
    eta_thermo_max: 1.0
    electron_sim_steps: 1000
  vram_thresholds:
    jax_warn: 0.42
    jax_critical: 0.45
    cuda_q_warn: 0.52
    cuda_q_critical: 0.55
```

## 🚀 Deployment

### 1. Install Dependencies
```bash
cd ~/diamondnode-unified-inference
pip install notion-client pyyaml numpy
```

### 2. Test Components
```bash
./workers/test_yennefer.sh
```

### 3. Configure Environment
```bash
# Copy template
sudo cp deployment/yennefer-telemetry.env.template /etc/default/yennefer-telemetry

# Edit with real NOTION_TOKEN
sudo nano /etc/default/yennefer-telemetry
```

### 4. Install Systemd Service
```bash
sudo cp deployment/yennefer-telemetry.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yennefer-telemetry
sudo systemctl start yennefer-telemetry
```

### 5. Monitor
```bash
# Check status
sudo systemctl status yennefer-telemetry

# View logs
sudo journalctl -u yennefer-telemetry -f

# Check log file
tail -f logs/yennefer_telemetry.log
```

## 🧪 Testing

### Run All Tests
```bash
cd ~/diamondnode-unified-inference
./workers/test_yennefer.sh
```

### Test Individual Components
```bash
# Thermodynamic simulator
python3 workers/thermodynamic_simulator.py

# Sanitizer
python3 workers/notion_sanitizer.py

# Single cycle (no POST)
python3 -c "
from workers.yennefer_telemetry_daemon import YenneferTelemetryDaemon
daemon = YenneferTelemetryDaemon()
metrics = daemon.compute_metrics()
print(metrics)
"
```

## 📊 Notion Database Schema

| Property | Type | Description |
|----------|------|-------------|
| Timestamp | Title | UTC timestamp |
| η_thermo | Number | Thermodynamic rate (0.0-1.0) |
| ε | Number | Energy state with hysteresis |
| γ | Number | Gamma buffer (default 0.05) |
| Δq | Number | Quantum differentiation delta |
| VRAM_JAX_Pct | Number | JAX VRAM percentage |
| CUDA_Q_Kernel_Status | Select | ACTIVE / IDLE / UNKNOWN |
| Maru_Reframe_Event | Select | NONE / VRAM_CRITICAL |
| Crystalline_Score | Number | Coherence score (0.0-1.0) |
| Notes | Rich Text | Run info + sanitization status |
| Live_Run_Verified | Checkbox | Manual verification flag |

## ✅ Success Criteria

- ✅ Hourly Notion API POST
- ✅ ε hysteresis prevents oscillation (γ=0.05 buffer)
- ✅ Thermodynamic simulation computes η_thermo
- ✅ Sanitization wrapper validates payloads (CLEAN/SANITIZED/REJECTED)
- ✅ Systemd service for production
- ✅ Envelope 0.3.0 throughout
- ✅ CUDA-Q multilane integration
- ✅ JAX VRAM monitoring
- ✅ Crystalline score computation
- ✅ Rejected payload envelope capsules

## 🔧 Troubleshooting

### Daemon won't start
```bash
# Check service status
sudo systemctl status yennefer-telemetry

# Check logs
sudo journalctl -u yennefer-telemetry -xe

# Verify config
python3 -c "import yaml; print(yaml.safe_load(open('config/yennefer_config.yaml')))"
```

### Notion POST failing
```bash
# Verify NOTION_TOKEN
sudo cat /etc/default/yennefer-telemetry

# Test Notion connection
python3 -c "
import os
os.environ['NOTION_TOKEN'] = 'YOUR_TOKEN_HERE'
from notion_client import Client
client = Client(auth=os.environ['NOTION_TOKEN'])
print(client.databases.retrieve('9a32dcb5-00b6-40d7-bd86-43d93965fa82'))
"
```

### JAX not available
Daemon gracefully falls back to mock VRAM values based on time.

## 📝 Notes

- Daemon runs as user `diamondnode`
- Logs to both file and journald
- Graceful degradation: no JAX/CUDA-Q → uses mock values
- Hysteresis state persists across cycles within daemon lifetime
- Rejected payloads logged to `logs/rejected_capsules_YYYYMMDD.log`
- Hold cycles tracked to detect state stability

---

**Delivery:** Single-pass implementation complete. All 5 files + service created and tested.
