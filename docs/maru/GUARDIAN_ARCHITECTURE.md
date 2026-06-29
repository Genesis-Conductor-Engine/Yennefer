# Maru Guardian Architecture

**Envelope Version:** 0.3.0  
**Status:** Production-Ready  
**Owner:** diamondnode MCP Infrastructure

## Overview

Maru Guardian is an MCP anomaly detection and structural reframe orchestrator that validates telemetry data from the Yennefer daemon, computes Crystalline Scores, and triggers #!nox reframe operations when anomalies are detected.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Yennefer Telemetry                       │
│              (POSTs to Notion DB hourly)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Notion Database                            │
│    collection://9a32dcb5-00b6-40d7-bd86-43d93965fa82       │
│                                                             │
│  Fields: Epsilon, VRAM_JAX, VRAM_CUDA_Q, Bus_State,       │
│          Crystalline_Score, Live_Run_Verified,             │
│          Maru_Reframe_Event                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Poll every 15 min
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Maru Guardian Daemon                        │
│                 (maru_guardian.py)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Query Telemetry (last 24h)                     │   │
│  │  2. Extract epsilon, VRAM, bus_state                │   │
│  │  3. Validate hysteresis compliance                  │   │
│  │  4. Check VRAM thresholds                          │   │
│  │  5. Validate bus state                             │   │
│  │  6. Compute Crystalline Score                      │   │
│  │  7. Trigger reframe if anomaly detected            │   │
│  │  8. Update Notion fields                           │   │
│  └─────────────────────────────────────────────────────┘   │
└────────┬────────────────────────────────┬───────────────────┘
         │                                │
         │ Anomaly Detected               │ Compliant
         ▼                                ▼
┌──────────────────────────┐    ┌────────────────────────┐
│  Reframe Trigger         │    │  Update Notion:        │
│  (reframe_trigger.py)    │    │  - Crystalline_Score   │
│                          │    │  - Live_Run_Verified   │
│  1. Check cooldown       │    └────────────────────────┘
│  2. Load nox_state.json  │
│  3. Apply structural lock│
│  4. Execute reframe      │
│  5. Create envelope      │
│  6. Save capsule         │
│  7. Release lock         │
│  8. Log audit event      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  /var/maru/reframe_events/               │
│  reframe_event_20260513_224800.json      │
│                                          │
│  Envelope 0.3.0 capsule with:           │
│  - Trigger reason                        │
│  - State before/after                    │
│  - Crystalline impact                    │
│  - Kobayashi Maru principle              │
└──────────────────────────────────────────┘
```

## Component Details

### 1. Maru Guardian Daemon (`maru_guardian.py`)

**Purpose:** Main orchestration daemon for telemetry validation and anomaly detection.

**Polling Cycle:**
- Interval: 15 minutes (configurable)
- Lookback: 24 hours of telemetry data
- Action: Query Notion DB → Validate → Update → Reframe if needed

**Validation Pipeline:**

1. **Hysteresis Validation** (40% weight)
   ```python
   def validate_hysteresis(current_eps, prev_eps, gamma=0.05):
       delta = abs(current_eps - prev_eps)
       if delta > gamma:
           return True, "VALID_TRANSITION"
       if current_eps != prev_eps:
           return False, "HYSTERESIS_VIOLATION"
       return True, "HYSTERESIS_HOLD"
   ```
   - γ threshold: 0.05
   - Detects oscillations and invalid transitions
   - Computes compliance rate across batch

2. **VRAM Compliance** (30% weight)
   - JAX threshold: ≤ 45% (alert at 42%)
   - CUDA-Q threshold: ≤ 55% (alert at 52%)
   - Binary compliance: pass/fail

3. **Bus State Validation** (20% weight)
   - Valid states: `RUNNING`, `YIELDING`, `BLOCKED`
   - Any other state = anomaly
   - Triggers bus reset reframe

4. **Sanitization Success** (10% weight)
   - Boolean field from Yennefer telemetry
   - 1.0 if true, 0.0 if false

**Crystalline Score Computation:**

```python
score = (
    0.4 * hysteresis_compliance_ratio +
    0.3 * vram_compliance_ratio +
    0.2 * bus_health_ratio +
    0.1 * sanitization_success_ratio
)
```

**Target:** ≥ 0.85

**Notion Updates:**
- `Crystalline_Score`: Computed weighted score
- `Live_Run_Verified`: True if all checks pass and score ≥ 0.85
- `Maru_Reframe_Event`: Appended timestamp and trigger reason on anomaly

### 2. Hysteresis Validator (`hysteresis_validator.py`)

**Purpose:** Dedicated epsilon transition analysis and compliance reporting.

**Key Functions:**

- `validate_transition()`: Single transition validation with γ buffer
- `analyze_sequence()`: Batch analysis with compliance metrics
- `detect_oscillations()`: Pattern detection for rapid alternation
- `generate_compliance_report()`: Envelope 0.3.0 proof schema

**Oscillation Detection:**
- Window size: 5 transitions
- Criteria: Only 2 unique epsilon values with ≥3 alternations
- Severity: HIGH (4+ changes) or MEDIUM (3 changes)

**Compliance Report Schema:**
```json
{
  "envelope_version": "0.3.0",
  "record_type": "hysteresis_compliance_report",
  "timestamp": "2026-05-13T22:48:00Z",
  "gamma_threshold": 0.05,
  "analysis": {
    "total_transitions": 120,
    "compliant_transitions": 108,
    "compliance_rate": 0.90,
    "status": "COMPLIANT"
  },
  "violations": [...],
  "oscillations": [...]
}
```

### 3. Reframe Trigger (`reframe_trigger.py`)

**Purpose:** #!nox structural reframe orchestrator applying Kobayashi Maru principle.

**Kobayashi Maru Principle:**
> "When constraints prevent goal achievement, redefine the structure."

**Reframe Conditions:**
1. Hysteresis violation detected
2. VRAM threshold exceeded (critical level)
3. Bus state anomaly
4. Crystalline Score < 0.85

**Reframe Logic by Trigger:**

| Trigger | Action |
|---------|--------|
| HYSTERESIS_VIOLATION | Enforce epsilon hold, prevent further transitions |
| VRAM_VIOLATION | Set bus_state to YIELDING for pressure relief |
| BUS_ANOMALY | Reset bus_state to RUNNING |
| CRYSTALLINE_SCORE_LOW | Composite remediation |

**Structural Lock:**
- Duration: 30 seconds (configurable)
- Purpose: Freeze system state during reframe
- Ensures atomic state transition

**Rate Limiting:**
- Cooldown: 60 minutes between reframes
- Max per hour: 3 reframes
- Prevents reframe storms

**Envelope Capsule Schema:**
```json
{
  "envelope_version": "0.3.0",
  "record_type": "maru_reframe_event",
  "timestamp": "2026-05-13T22:48:00Z",
  "trigger": "HYSTERESIS_VIOLATION",
  "state_before": {
    "structural_lock": false,
    "bus_state": "RUNNING",
    "current_epsilon": 0.12,
    "reframe_count": 5
  },
  "state_after": {
    "structural_lock": false,
    "bus_state": "RUNNING",
    "epsilon_reframed": true,
    "reframe_count": 6
  },
  "crystalline_impact": 0.05,
  "structural_lock_duration_seconds": 30,
  "kobayashi_maru_principle": "Structure redefined for goal materialism"
}
```

**Audit Trail:**
- Location: `/var/maru/audit_logs/maru_audit_YYYYMMDD.jsonl`
- Format: JSONL (one event per line)
- Events: REFRAME_EXECUTED, REFRAME_BLOCKED, ANOMALY_DETECTED

### 4. Configuration (`maru_config.yaml`)

**Structure:**
```yaml
envelope_version: "0.3.0"
maru_guardian:
  poll_interval_minutes: 15
  notion_db: "9a32dcb5-00b6-40d7-bd86-43d93965fa82"
  lookback_hours: 24
  thresholds:
    crystalline_min: 0.85
    hysteresis_compliance_min: 0.90
    vram_jax_warn: 0.42
    vram_jax_critical: 0.45
    vram_cuda_q_warn: 0.52
    vram_cuda_q_critical: 0.55
  reframe:
    enabled: true
    cooldown_minutes: 60
    max_reframes_per_hour: 3
    structural_lock_duration_seconds: 30
  crystalline_weights:
    hysteresis: 0.4
    vram: 0.3
    bus_health: 0.2
    sanitization: 0.1
```

**Tuning Guidelines:**
- Increase `poll_interval_minutes` to reduce API calls
- Adjust `crystalline_min` to change sensitivity
- Modify weights to prioritize different validation aspects
- Increase `cooldown_minutes` to reduce reframe frequency

## Deployment

### Prerequisites
- Python 3.8+
- `pyyaml`, `requests` packages
- NOTION_TOKEN environment variable
- Yennefer telemetry daemon running
- Systemd (for service management)

### Installation

```bash
cd ~/diamondnode-unified-inference/deployment
chmod +x deploy_maru_guardian.sh
./deploy_maru_guardian.sh
```

The script will:
1. Create `/var/maru/` directories
2. Install systemd service
3. Create environment file template
4. Enable and start service

### Post-Installation

1. **Set NOTION_TOKEN:**
   ```bash
   sudo nano /etc/default/maru-guardian
   # Add: NOTION_TOKEN=your_actual_token_here
   sudo systemctl restart maru-guardian
   ```

2. **Verify service:**
   ```bash
   sudo systemctl status maru-guardian
   sudo journalctl -u maru-guardian -f
   ```

3. **Check state files:**
   ```bash
   ls -lah /var/maru/reframe_events/
   cat /var/maru/nox_state.json
   ```

## Monitoring

### Service Health
```bash
# Check service status
sudo systemctl status maru-guardian

# View recent logs
sudo journalctl -u maru-guardian -n 100

# Follow logs in real-time
sudo journalctl -u maru-guardian -f
```

### Telemetry Validation

```bash
# Check latest Crystalline Scores in Notion DB
# (via Notion API or web interface)

# Review reframe events
ls -lth /var/maru/reframe_events/ | head -10
cat /var/maru/reframe_events/reframe_event_*.json | jq
```

### Audit Trail
```bash
# View today's audit log
cat /var/maru/audit_logs/maru_audit_$(date +%Y%m%d).jsonl | jq

# Count reframes today
grep REFRAME_EXECUTED /var/maru/audit_logs/maru_audit_$(date +%Y%m%d).jsonl | wc -l
```

## Troubleshooting

### Issue: Service fails to start

**Symptoms:** `systemctl status maru-guardian` shows "failed" state

**Check:**
1. NOTION_TOKEN set in `/etc/default/maru-guardian`
2. Python dependencies installed: `python3 -c "import yaml, requests"`
3. Config file exists: `ls ~/diamondnode-unified-inference/config/maru_config.yaml`
4. Log for errors: `sudo journalctl -u maru-guardian -n 50`

### Issue: No telemetry entries found

**Symptoms:** Logs show "No telemetry entries found" every poll cycle

**Check:**
1. Yennefer telemetry daemon running: `systemctl status yennefer-telemetry`
2. Notion DB ID correct in config: `9a32dcb5-00b6-40d7-bd86-43d93965fa82`
3. NOTION_TOKEN has read access to database
4. Lookback hours not too restrictive (default: 24h)

### Issue: Reframes not triggering on anomalies

**Symptoms:** Anomalies detected but no reframe capsules created

**Check:**
1. Reframe enabled in config: `reframe.enabled: true`
2. Not in cooldown: Check `/var/maru/nox_state.json` for `last_reframe`
3. Rate limit not exceeded: Check `reframe_count` in state
4. Permissions on `/var/maru/`: `sudo chown -R diamondnode:diamondnode /var/maru`

### Issue: Crystalline Score always low

**Symptoms:** All entries have score < 0.85

**Possible Causes:**
1. Hysteresis violations common → Check epsilon transitions in Yennefer
2. VRAM thresholds too strict → Adjust `vram_*_critical` in config
3. Bus state anomalies → Investigate bus_state values in telemetry
4. Weights misconfigured → Verify `crystalline_weights` sum to 1.0

**Remediation:**
```bash
# Temporarily lower threshold for testing
nano ~/diamondnode-unified-inference/config/maru_config.yaml
# Set crystalline_min: 0.75
sudo systemctl restart maru-guardian
```

### Issue: Too many reframes

**Symptoms:** Hitting rate limit frequently, logs show "RATE_LIMIT_EXCEEDED"

**Check:**
1. Underlying telemetry issues → Review Yennefer configuration
2. Thresholds too sensitive → Increase `vram_*_warn` values
3. Hysteresis γ too strict → Consider γ=0.08 instead of 0.05

**Remediation:**
```bash
# Increase cooldown and reduce max reframes
nano ~/diamondnode-unified-inference/config/maru_config.yaml
# Set cooldown_minutes: 120, max_reframes_per_hour: 2
sudo systemctl restart maru-guardian
```

## API Integration

### Programmatic Access to Reframe Events

```python
import json
from pathlib import Path

events_dir = Path("/var/maru/reframe_events")

# Load latest reframe event
events = sorted(events_dir.glob("reframe_event_*.json"), reverse=True)
if events:
    with open(events[0]) as f:
        latest_event = json.load(f)
    
    print(f"Trigger: {latest_event['trigger']}")
    print(f"Impact: {latest_event['crystalline_impact']}")
```

### Query Crystalline Scores from Notion

```python
import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_ID = "9a32dcb5-00b6-40d7-bd86-43d93965fa82"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

url = f"https://api.notion.com/v1/databases/{DB_ID}/query"

response = requests.post(url, headers=headers, json={
    "sorts": [{"property": "Timestamp", "direction": "descending"}],
    "page_size": 10
})

for page in response.json()["results"]:
    score = page["properties"]["Crystalline_Score"]["number"]
    verified = page["properties"]["Live_Run_Verified"]["checkbox"]
    print(f"Score: {score}, Verified: {verified}")
```

## Performance Characteristics

- **CPU Usage:** < 5% during poll cycle, negligible between polls
- **Memory:** ~50 MB resident set size
- **Network:** ~2-5 KB per Notion API call (query + updates)
- **Disk I/O:** Minimal (envelope capsules ~2 KB each)
- **Latency:** Poll cycle completes in < 10 seconds for 100 entries

## Security Considerations

1. **NOTION_TOKEN Protection:**
   - Stored in `/etc/default/maru-guardian` (mode 600, root-owned)
   - Never logged or exposed in output
   - Rotated quarterly

2. **State File Integrity:**
   - `/var/maru/nox_state.json` owned by diamondnode user
   - Validated on load (JSON schema check)
   - Backed up before each reframe

3. **Audit Trail:**
   - Immutable append-only JSONL format
   - Rotation after 30 days (configurable)
   - No sensitive data in audit logs

## Future Enhancements

1. **Predictive Reframing:**
   - ML model to predict anomalies before they occur
   - Proactive epsilon adjustments

2. **Multi-DB Support:**
   - Monitor multiple Notion databases
   - Aggregate Crystalline Scores across environments

3. **Slack/Discord Notifications:**
   - Alert on critical anomalies
   - Daily compliance summary reports

4. **Grafana Dashboard:**
   - Real-time Crystalline Score visualization
   - Reframe event timeline
   - Hysteresis compliance trends

## References

- Yennefer Telemetry: See `~/diamondnode-unified-inference/docs/yennefer/`
- Notion API: https://developers.notion.com/
- Envelope 0.3.0 Spec: `~/diamondnode-unified-inference/docs/envelope_spec.md`
- Kobayashi Maru Principle: Original Star Trek II (1982)

## Support

For issues or questions:
- Logs: `sudo journalctl -u maru-guardian -f`
- State: `cat /var/maru/nox_state.json`
- Config: `~/diamondnode-unified-inference/config/maru_config.yaml`

**Last Updated:** 2026-05-13  
**Maintainer:** diamondnode MCP Infrastructure Team
