#!/usr/bin/env python3
"""
Maru MCP Guardian - Anomaly Detection & Reframe Orchestrator
Envelope Version: 0.3.0

Polls Notion telemetry DB, validates hysteresis/VRAM/bus state,
computes Crystalline Score, triggers #!nox reframe on anomalies.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import requests
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/maru_guardian.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "maru_config.yaml"

sys.path.insert(0, str(SCRIPT_DIR))
from hysteresis_validator import HysteresisValidator
from reframe_trigger import ReframeTrigger


class MaruGuardian:
    """MCP Guardian daemon for telemetry validation and anomaly detection."""
    
    def __init__(self, config_path: Path):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.notion_token = os.getenv('NOTION_TOKEN')
        if not self.notion_token:
            raise ValueError("NOTION_TOKEN environment variable required")
        
        self.db_id = self.config['maru_guardian']['notion_db']
        self.poll_interval = self.config['maru_guardian']['poll_interval_minutes'] * 60
        self.lookback_hours = self.config['maru_guardian']['lookback_hours']
        
        self.thresholds = self.config['maru_guardian']['thresholds']
        self.weights = self.config['maru_guardian']['crystalline_weights']
        
        self.hysteresis_validator = HysteresisValidator(self.config)
        self.reframe_trigger = ReframeTrigger(self.config)
        
        self.notion_headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        logger.info("Maru Guardian initialized - Envelope 0.3.0")
    
    def query_telemetry(self):
        """Query Notion DB for recent telemetry entries."""
        cutoff = datetime.utcnow() - timedelta(hours=self.lookback_hours)
        
        query_body = {
            "filter": {
                "property": "Timestamp",
                "date": {
                    "on_or_after": cutoff.isoformat()
                }
            },
            "sorts": [
                {
                    "property": "Timestamp",
                    "direction": "ascending"
                }
            ]
        }
        
        url = f"https://api.notion.com/v1/databases/{self.db_id}/query"
        
        try:
            response = requests.post(url, headers=self.notion_headers, json=query_body, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            logger.info(f"Retrieved {len(results)} telemetry entries")
            return results
        except Exception as e:
            logger.error(f"Failed to query Notion DB: {e}")
            return []
    
    def extract_telemetry_data(self, page):
        """Extract telemetry fields from Notion page."""
        props = page.get('properties', {})
        
        def get_prop(name, prop_type):
            try:
                prop = props.get(name, {})
                if prop_type == 'number':
                    return prop.get('number')
                elif prop_type == 'rich_text':
                    texts = prop.get('rich_text', [])
                    return texts[0]['plain_text'] if texts else None
                elif prop_type == 'date':
                    date_obj = prop.get('date', {})
                    return date_obj.get('start') if date_obj else None
                elif prop_type == 'checkbox':
                    return prop.get('checkbox', False)
            except Exception:
                return None
        
        return {
            'page_id': page['id'],
            'timestamp': get_prop('Timestamp', 'date'),
            'epsilon': get_prop('Epsilon', 'number'),
            'vram_jax': get_prop('VRAM_JAX', 'number'),
            'vram_cuda_q': get_prop('VRAM_CUDA_Q', 'number'),
            'bus_state': get_prop('Bus_State', 'rich_text'),
            'sanitization_success': get_prop('Sanitization_Success', 'checkbox'),
            'crystalline_score': get_prop('Crystalline_Score', 'number'),
            'live_run_verified': get_prop('Live_Run_Verified', 'checkbox')
        }
    
    def validate_hysteresis(self, current_eps, prev_eps, gamma=0.05):
        """Validate epsilon hysteresis compliance."""
        if prev_eps is None:
            return True, "INITIAL_VALUE", 1.0
        
        delta = abs(current_eps - prev_eps)
        
        if delta > gamma:
            return True, "VALID_TRANSITION", 1.0
        
        if current_eps != prev_eps:
            return False, "HYSTERESIS_VIOLATION", 0.0
        
        return True, "HYSTERESIS_HOLD", 1.0
    
    def validate_vram(self, vram_jax, vram_cuda_q):
        """Validate VRAM compliance."""
        violations = []
        alerts = []
        
        if vram_jax is not None:
            if vram_jax > self.thresholds['vram_jax_critical']:
                violations.append(f"JAX VRAM critical: {vram_jax:.2%} > 45%")
            elif vram_jax > self.thresholds['vram_jax_warn']:
                alerts.append(f"JAX VRAM warning: {vram_jax:.2%} > 42%")
        
        if vram_cuda_q is not None:
            if vram_cuda_q > self.thresholds['vram_cuda_q_critical']:
                violations.append(f"CUDA-Q VRAM critical: {vram_cuda_q:.2%} > 55%")
            elif vram_cuda_q > self.thresholds['vram_cuda_q_warn']:
                alerts.append(f"CUDA-Q VRAM warning: {vram_cuda_q:.2%} > 52%")
        
        compliant = len(violations) == 0
        ratio = 1.0 if compliant else 0.5 if len(alerts) > 0 else 0.0
        
        return compliant, violations, alerts, ratio
    
    def validate_bus_state(self, bus_state):
        """Validate bus state."""
        valid_states = ['RUNNING', 'YIELDING', 'BLOCKED']
        
        if bus_state is None:
            return False, "BUS_STATE_MISSING", 0.0
        
        if bus_state in valid_states:
            return True, "BUS_STATE_VALID", 1.0
        
        return False, f"BUS_STATE_ANOMALY: {bus_state}", 0.0
    
    def compute_crystalline_score(self, hysteresis_ratio, vram_ratio, bus_ratio, sanitization_ratio):
        """Compute Crystalline Score with weighted components."""
        score = (
            self.weights['hysteresis'] * hysteresis_ratio +
            self.weights['vram'] * vram_ratio +
            self.weights['bus_health'] * bus_ratio +
            self.weights['sanitization'] * sanitization_ratio
        )
        return round(score, 4)
    
    def update_notion_page(self, page_id, crystalline_score, live_verified, reframe_event=None):
        """Update Notion page with validation results."""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        
        update_body = {
            "properties": {
                "Crystalline_Score": {"number": crystalline_score},
                "Live_Run_Verified": {"checkbox": live_verified}
            }
        }
        
        if reframe_event:
            update_body["properties"]["Maru_Reframe_Event"] = {
                "rich_text": [{"text": {"content": reframe_event}}]
            }
        
        try:
            response = requests.patch(url, headers=self.notion_headers, json=update_body, timeout=30)
            response.raise_for_status()
            logger.info(f"Updated page {page_id[:8]}... with score={crystalline_score}")
        except Exception as e:
            logger.error(f"Failed to update Notion page: {e}")
    
    def process_telemetry_batch(self, telemetry_entries):
        """Process batch of telemetry entries."""
        prev_eps = None
        hysteresis_compliant_count = 0
        total_hysteresis_checks = 0
        
        for entry in telemetry_entries:
            data = self.extract_telemetry_data(entry)
            
            logger.info(f"Processing entry {data['page_id'][:8]}... at {data['timestamp']}")
            
            # Hysteresis validation
            hyst_valid, hyst_status, hyst_ratio = self.validate_hysteresis(
                data['epsilon'], prev_eps
            )
            
            if prev_eps is not None:
                total_hysteresis_checks += 1
                if hyst_valid:
                    hysteresis_compliant_count += 1
            
            # VRAM validation
            vram_valid, vram_violations, vram_alerts, vram_ratio = self.validate_vram(
                data['vram_jax'], data['vram_cuda_q']
            )
            
            # Bus state validation
            bus_valid, bus_status, bus_ratio = self.validate_bus_state(data['bus_state'])
            
            # Sanitization ratio
            san_ratio = 1.0 if data['sanitization_success'] else 0.0
            
            # Compute overall hysteresis compliance ratio
            if total_hysteresis_checks > 0:
                overall_hyst_ratio = hysteresis_compliant_count / total_hysteresis_checks
            else:
                overall_hyst_ratio = 1.0
            
            # Compute Crystalline Score
            crystalline_score = self.compute_crystalline_score(
                overall_hyst_ratio, vram_ratio, bus_ratio, san_ratio
            )
            
            # Check if reframe needed
            anomalies = []
            if not hyst_valid:
                anomalies.append(hyst_status)
            if not vram_valid:
                anomalies.extend(vram_violations)
            if not bus_valid:
                anomalies.append(bus_status)
            
            reframe_event = None
            if anomalies or crystalline_score < self.thresholds['crystalline_min']:
                trigger_reason = "; ".join(anomalies) if anomalies else "CRYSTALLINE_SCORE_LOW"
                
                logger.warning(f"Anomaly detected: {trigger_reason}")
                
                # Trigger reframe
                reframe_result = self.reframe_trigger.trigger_reframe(
                    trigger_reason=trigger_reason,
                    state_snapshot={
                        'epsilon': data['epsilon'],
                        'vram_jax': data['vram_jax'],
                        'vram_cuda_q': data['vram_cuda_q'],
                        'bus_state': data['bus_state'],
                        'crystalline_score': crystalline_score
                    }
                )
                
                reframe_event = f"{datetime.utcnow().isoformat()}Z: {trigger_reason}"
            
            # Update Notion page
            live_verified = (
                hyst_valid and vram_valid and bus_valid and
                crystalline_score >= self.thresholds['crystalline_min']
            )
            
            self.update_notion_page(
                data['page_id'],
                crystalline_score,
                live_verified,
                reframe_event
            )
            
            prev_eps = data['epsilon']
        
        # Generate hysteresis compliance report
        if total_hysteresis_checks > 0:
            compliance_rate = hysteresis_compliant_count / total_hysteresis_checks
            logger.info(f"Hysteresis compliance: {compliance_rate:.2%} ({hysteresis_compliant_count}/{total_hysteresis_checks})")
    
    def run(self):
        """Main guardian loop."""
        logger.info("Starting Maru Guardian main loop")
        
        while True:
            try:
                logger.info("=== Maru Guardian polling cycle ===")
                
                telemetry_entries = self.query_telemetry()
                
                if telemetry_entries:
                    self.process_telemetry_batch(telemetry_entries)
                else:
                    logger.info("No telemetry entries found")
                
                logger.info(f"Sleeping for {self.poll_interval}s")
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Maru Guardian shutdown requested")
                break
            except Exception as e:
                logger.error(f"Error in guardian loop: {e}", exc_info=True)
                time.sleep(60)


if __name__ == "__main__":
    guardian = MaruGuardian(CONFIG_PATH)
    guardian.run()
