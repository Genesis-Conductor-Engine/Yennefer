#!/usr/bin/env python3
"""
Reframe Trigger - #!nox Structural Reframe Orchestrator
Envelope Version: 0.3.0

Applies Kobayashi Maru principle: redefine structure for goal materialism.
Manages structural locks, logs reframe events, creates envelope capsules.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

NOX_STATE_PATH = Path("/var/maru/nox_state.json")
REFRAME_EVENTS_DIR = Path("/var/maru/reframe_events")
AUDIT_LOG_DIR = Path("/var/maru/audit_logs")


class ReframeTrigger:
    """#!nox reframe orchestrator with structural lock management."""
    
    def __init__(self, config: dict):
        self.config = config
        self.reframe_config = config['maru_guardian']['reframe']
        
        self.enabled = self.reframe_config['enabled']
        self.cooldown_minutes = self.reframe_config['cooldown_minutes']
        self.max_reframes_per_hour = self.reframe_config['max_reframes_per_hour']
        self.lock_duration = self.reframe_config['structural_lock_duration_seconds']
        
        self.last_reframe_time = None
        self.reframe_count_hour = 0
        self.reframe_hour_start = None
        
        # Ensure directories exist
        REFRAME_EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    def can_reframe(self) -> tuple[bool, str]:
        """Check if reframe is allowed based on cooldown and rate limits."""
        if not self.enabled:
            return False, "REFRAME_DISABLED"
        
        now = datetime.utcnow()
        
        # Check cooldown
        if self.last_reframe_time:
            elapsed_minutes = (now - self.last_reframe_time).total_seconds() / 60
            if elapsed_minutes < self.cooldown_minutes:
                remaining = self.cooldown_minutes - elapsed_minutes
                return False, f"COOLDOWN_ACTIVE ({remaining:.1f}m remaining)"
        
        # Check hourly rate limit
        if self.reframe_hour_start:
            hour_elapsed = (now - self.reframe_hour_start).total_seconds() / 3600
            if hour_elapsed < 1.0:
                if self.reframe_count_hour >= self.max_reframes_per_hour:
                    return False, f"RATE_LIMIT_EXCEEDED ({self.reframe_count_hour}/{self.max_reframes_per_hour})"
            else:
                # Reset hourly counter
                self.reframe_hour_start = now
                self.reframe_count_hour = 0
        else:
            self.reframe_hour_start = now
        
        return True, "OK"
    
    def load_nox_state(self) -> Dict:
        """Load current #!nox state."""
        if not NOX_STATE_PATH.exists():
            default_state = {
                'structural_lock': False,
                'last_reframe': None,
                'reframe_count': 0,
                'current_epsilon': None,
                'bus_state': 'RUNNING'
            }
            self.save_nox_state(default_state)
            return default_state
        
        try:
            with open(NOX_STATE_PATH) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load nox_state.json: {e}")
            return {}
    
    def save_nox_state(self, state: Dict):
        """Save #!nox state."""
        try:
            NOX_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(NOX_STATE_PATH, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save nox_state.json: {e}")
    
    def apply_structural_lock(self, state: Dict) -> Dict:
        """
        Apply structural lock during reframe.
        
        Kobayashi Maru principle: temporarily lock structure to
        redefine constraints and materialize goal state.
        """
        state['structural_lock'] = True
        state['lock_applied_at'] = datetime.utcnow().isoformat() + 'Z'
        state['lock_duration_seconds'] = self.lock_duration
        
        logger.info(f"Structural lock applied for {self.lock_duration}s")
        
        return state
    
    def release_structural_lock(self, state: Dict) -> Dict:
        """Release structural lock after reframe."""
        state['structural_lock'] = False
        state['lock_released_at'] = datetime.utcnow().isoformat() + 'Z'
        
        logger.info("Structural lock released")
        
        return state
    
    def execute_reframe(self, state_before: Dict, trigger_reason: str) -> Dict:
        """
        Execute #!nox reframe operation.
        
        Applies Kobayashi Maru: redefine structure to achieve goal materialism.
        """
        logger.info(f"Executing #!nox reframe: {trigger_reason}")
        
        # Apply structural lock
        state_after = dict(state_before)
        state_after = self.apply_structural_lock(state_after)
        
        # Reframe logic: adjust epsilon or bus state based on trigger
        if "HYSTERESIS_VIOLATION" in trigger_reason:
            # Force epsilon stabilization
            if state_after.get('current_epsilon'):
                state_after['epsilon_reframed'] = True
                state_after['epsilon_hold_enforced'] = True
                logger.info("Enforced epsilon hold to resolve hysteresis violation")
        
        elif "VRAM_VIOLATION" in trigger_reason:
            # Trigger bus yielding
            state_after['bus_state'] = 'YIELDING'
            state_after['vram_pressure_relief'] = True
            logger.info("Bus state set to YIELDING for VRAM pressure relief")
        
        elif "BUS_ANOMALY" in trigger_reason:
            # Reset bus state
            state_after['bus_state'] = 'RUNNING'
            state_after['bus_reset'] = True
            logger.info("Bus state reset to RUNNING")
        
        # Update reframe metadata
        state_after['last_reframe'] = datetime.utcnow().isoformat() + 'Z'
        state_after['reframe_count'] = state_before.get('reframe_count', 0) + 1
        state_after['last_reframe_trigger'] = trigger_reason
        
        return state_after
    
    def compute_crystalline_impact(self, state_before: Dict, state_after: Dict) -> float:
        """
        Estimate impact of reframe on Crystalline Score.
        
        Returns expected delta in score.
        """
        # Simplified heuristic: each reframe has potential to improve by ~0.05
        # Actual impact depends on anomaly resolution
        return 0.05
    
    def create_envelope_capsule(self, trigger_reason: str, state_before: Dict, 
                                state_after: Dict, crystalline_impact: float) -> Dict:
        """
        Create envelope 0.3.0 capsule for reframe event.
        
        Returns proof schema for audit trail.
        """
        envelope = {
            'envelope_version': '0.3.0',
            'record_type': 'maru_reframe_event',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'trigger': trigger_reason,
            'state_before': {
                'structural_lock': state_before.get('structural_lock', False),
                'bus_state': state_before.get('bus_state'),
                'current_epsilon': state_before.get('current_epsilon'),
                'reframe_count': state_before.get('reframe_count', 0)
            },
            'state_after': {
                'structural_lock': state_after.get('structural_lock', False),
                'bus_state': state_after.get('bus_state'),
                'epsilon_reframed': state_after.get('epsilon_reframed', False),
                'vram_pressure_relief': state_after.get('vram_pressure_relief', False),
                'bus_reset': state_after.get('bus_reset', False),
                'reframe_count': state_after.get('reframe_count', 0)
            },
            'crystalline_impact': crystalline_impact,
            'structural_lock_duration_seconds': self.lock_duration,
            'kobayashi_maru_principle': 'Structure redefined for goal materialism'
        }
        
        return envelope
    
    def save_envelope_capsule(self, envelope: Dict):
        """Save envelope capsule to reframe events directory."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"reframe_event_{timestamp}.json"
        filepath = REFRAME_EVENTS_DIR / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(envelope, f, indent=2)
            logger.info(f"Envelope capsule saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save envelope capsule: {e}")
    
    def log_audit_event(self, event_type: str, details: Dict):
        """Log audit event to audit trail."""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'details': details
        }
        
        date_str = datetime.utcnow().strftime("%Y%m%d")
        audit_file = AUDIT_LOG_DIR / f"maru_audit_{date_str}.jsonl"
        
        try:
            with open(audit_file, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def trigger_reframe(self, trigger_reason: str, state_snapshot: Dict) -> Dict:
        """
        Main reframe trigger orchestration.
        
        Returns reframe result with status and envelope capsule.
        """
        # Check if reframe allowed
        can_reframe, status_msg = self.can_reframe()
        if not can_reframe:
            logger.warning(f"Reframe blocked: {status_msg}")
            self.log_audit_event('REFRAME_BLOCKED', {
                'reason': status_msg,
                'trigger': trigger_reason
            })
            return {
                'success': False,
                'status': status_msg,
                'trigger': trigger_reason
            }
        
        # Load current state
        state_before = self.load_nox_state()
        
        # Merge snapshot into state
        state_before['current_epsilon'] = state_snapshot.get('epsilon')
        state_before['bus_state'] = state_snapshot.get('bus_state', 'RUNNING')
        
        # Execute reframe
        state_after = self.execute_reframe(state_before, trigger_reason)
        
        # Compute impact
        crystalline_impact = self.compute_crystalline_impact(state_before, state_after)
        
        # Create envelope capsule
        envelope = self.create_envelope_capsule(
            trigger_reason, state_before, state_after, crystalline_impact
        )
        
        # Save capsule
        self.save_envelope_capsule(envelope)
        
        # Release structural lock (in production, would be time-delayed)
        state_after = self.release_structural_lock(state_after)
        
        # Save new state
        self.save_nox_state(state_after)
        
        # Update tracking
        self.last_reframe_time = datetime.utcnow()
        self.reframe_count_hour += 1
        
        # Log audit event
        self.log_audit_event('REFRAME_EXECUTED', {
            'trigger': trigger_reason,
            'crystalline_impact': crystalline_impact,
            'state_snapshot': state_snapshot
        })
        
        logger.info(f"Reframe completed: {trigger_reason}")
        
        return {
            'success': True,
            'status': 'REFRAME_EXECUTED',
            'trigger': trigger_reason,
            'crystalline_impact': crystalline_impact,
            'envelope': envelope
        }


if __name__ == "__main__":
    # Example usage
    import yaml
    
    logging.basicConfig(level=logging.INFO)
    
    config_path = Path(__file__).parent.parent / "config" / "maru_config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    trigger = ReframeTrigger(config)
    
    # Test reframe
    result = trigger.trigger_reframe(
        trigger_reason="HYSTERESIS_VIOLATION",
        state_snapshot={
            'epsilon': 0.12,
            'vram_jax': 0.38,
            'vram_cuda_q': 0.47,
            'bus_state': 'RUNNING',
            'crystalline_score': 0.82
        }
    )
    
    print(json.dumps(result, indent=2))
