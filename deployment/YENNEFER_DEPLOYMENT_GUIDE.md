# Yennefer Telemetry Deployment Guide

## Quick Start

```bash
cd ~/diamondnode-unified-inference
./deployment/deploy_yennefer.sh
```

## Manual Deployment

### 1. Install Dependencies
```bash
cd ~/diamondnode-unified-inference
python3 -m venv yennefer_venv
source yennefer_venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure NOTION_TOKEN
```bash
sudo cp deployment/yennefer-telemetry.env.template /etc/default/yennefer-telemetry
sudo nano /etc/default/yennefer-telemetry
# Add: NOTION_TOKEN=secret_xxxxx
```

### 3. Install Service
```bash
sudo cp deployment/yennefer-telemetry.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yennefer-telemetry
sudo systemctl start yennefer-telemetry
```

### 4. Verify
```bash
sudo systemctl status yennefer-telemetry
sudo journalctl -u yennefer-telemetry -f
```

## Service Management

```bash
# Start
sudo systemctl start yennefer-telemetry

# Stop
sudo systemctl stop yennefer-telemetry

# Restart
sudo systemctl restart yennefer-telemetry

# Status
sudo systemctl status yennefer-telemetry

# Logs (live)
sudo journalctl -u yennefer-telemetry -f

# Logs (last 100 lines)
sudo journalctl -u yennefer-telemetry -n 100
```

## Testing Before Deployment

```bash
cd ~/diamondnode-unified-inference
./workers/test_yennefer.sh
```

## Configuration

Edit `config/yennefer_config.yaml` to customize:
- Cadence (default: 1 hour)
- Hysteresis gamma buffer (default: 0.05)
- VRAM thresholds
- Crystalline score factors

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u yennefer-telemetry -xe
```

### Notion POST failing
Check NOTION_TOKEN:
```bash
sudo cat /etc/default/yennefer-telemetry
```

### Python dependencies missing
```bash
cd ~/diamondnode-unified-inference
source yennefer_venv/bin/activate
pip install -r requirements.txt
```

## Files

- **workers/yennefer_telemetry_daemon.py** - Main daemon
- **workers/thermodynamic_simulator.py** - η_thermo computation
- **workers/notion_sanitizer.py** - Payload validation
- **config/yennefer_config.yaml** - Configuration
- **deployment/yennefer-telemetry.service** - Systemd unit
- **deployment/yennefer-telemetry.env.template** - Environment template
