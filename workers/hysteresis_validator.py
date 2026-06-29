#!/usr/bin/env python3
"""
Hysteresis Validator - Epsilon Compliance Analysis
Envelope Version: 0.3.0

Analyzes epsilon transitions for hysteresis compliance,
detects oscillation patterns, generates compliance reports.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


class HysteresisValidator:
    """Dedicated hysteresis analysis module."""
    
    def __init__(self, config: dict):
        self.config = config
        self.gamma = 0.05  # Hysteresis threshold
        self.min_compliance = config['maru_guardian']['thresholds']['hysteresis_compliance_min']
    
    def validate_transition(self, current_eps: float, prev_eps: float) -> Tuple[bool, str, float]:
        """
        Validate a single epsilon transition.
        
        Returns:
            (valid, status, compliance_score)
        """
        if prev_eps is None:
            return True, "INITIAL_VALUE", 1.0
        
        delta = abs(current_eps - prev_eps)
        
        # Valid transition: delta exceeds hysteresis threshold
        if delta > self.gamma:
            return True, "VALID_TRANSITION", 1.0
        
        # Hysteresis violation: changed without exceeding threshold
        if current_eps != prev_eps:
            return False, "HYSTERESIS_VIOLATION", 0.0
        
        # Valid hold: stayed same within threshold
        return True, "HYSTERESIS_HOLD", 1.0
    
    def analyze_sequence(self, epsilon_sequence: List[float]) -> Dict:
        """
        Analyze sequence of epsilon values for compliance patterns.
        
        Returns:
            Analysis report with compliance metrics and violations.
        """
        if len(epsilon_sequence) < 2:
            return {
                'total_transitions': 0,
                'compliant_transitions': 0,
                'violations': [],
                'compliance_rate': 1.0,
                'status': 'INSUFFICIENT_DATA'
            }
        
        transitions = []
        violations = []
        compliant_count = 0
        
        for i in range(1, len(epsilon_sequence)):
            prev_eps = epsilon_sequence[i-1]
            curr_eps = epsilon_sequence[i]
            
            valid, status, score = self.validate_transition(curr_eps, prev_eps)
            
            transition = {
                'index': i,
                'prev': prev_eps,
                'current': curr_eps,
                'delta': abs(curr_eps - prev_eps),
                'valid': valid,
                'status': status,
                'score': score
            }
            
            transitions.append(transition)
            
            if valid:
                compliant_count += 1
            else:
                violations.append(transition)
        
        total_transitions = len(transitions)
        compliance_rate = compliant_count / total_transitions if total_transitions > 0 else 0.0
        
        # Detect oscillation patterns
        oscillations = self.detect_oscillations(epsilon_sequence)
        
        report = {
            'total_transitions': total_transitions,
            'compliant_transitions': compliant_count,
            'violations': violations,
            'compliance_rate': compliance_rate,
            'meets_threshold': compliance_rate >= self.min_compliance,
            'oscillations': oscillations,
            'status': 'COMPLIANT' if compliance_rate >= self.min_compliance else 'NON_COMPLIANT'
        }
        
        return report
    
    def detect_oscillations(self, epsilon_sequence: List[float], window_size: int = 5) -> List[Dict]:
        """
        Detect oscillation patterns in epsilon sequence.
        
        Oscillation: repeated back-and-forth changes between two values.
        """
        if len(epsilon_sequence) < window_size:
            return []
        
        oscillations = []
        
        for i in range(len(epsilon_sequence) - window_size + 1):
            window = epsilon_sequence[i:i+window_size]
            unique_values = set(window)
            
            # Oscillation: only 2 unique values with alternating pattern
            if len(unique_values) == 2:
                changes = sum(1 for j in range(len(window)-1) if window[j] != window[j+1])
                
                if changes >= window_size - 2:  # Mostly alternating
                    oscillations.append({
                        'start_index': i,
                        'end_index': i + window_size - 1,
                        'values': list(unique_values),
                        'changes': changes,
                        'severity': 'HIGH' if changes == window_size - 1 else 'MEDIUM'
                    })
        
        return oscillations
    
    def generate_compliance_report(self, analysis: Dict) -> Dict:
        """
        Generate envelope 0.3.0 compliance report.
        
        Returns proof schema for audit trail.
        """
        report = {
            'envelope_version': '0.3.0',
            'record_type': 'hysteresis_compliance_report',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'gamma_threshold': self.gamma,
            'min_compliance_threshold': self.min_compliance,
            'analysis': {
                'total_transitions': analysis['total_transitions'],
                'compliant_transitions': analysis['compliant_transitions'],
                'compliance_rate': analysis['compliance_rate'],
                'status': analysis['status'],
                'meets_threshold': analysis['meets_threshold']
            },
            'violations': [
                {
                    'index': v['index'],
                    'prev_epsilon': v['prev'],
                    'current_epsilon': v['current'],
                    'delta': v['delta'],
                    'status': v['status']
                }
                for v in analysis['violations']
            ],
            'oscillations': analysis['oscillations']
        }
        
        return report
    
    def save_report(self, report: Dict, output_path: Path):
        """Save compliance report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
    
    def load_telemetry_sequence(self, telemetry_entries: List[Dict]) -> List[float]:
        """Extract epsilon sequence from telemetry entries."""
        epsilon_values = []
        
        for entry in telemetry_entries:
            eps = entry.get('epsilon')
            if eps is not None:
                epsilon_values.append(eps)
        
        return epsilon_values


if __name__ == "__main__":
    # Example usage
    import yaml
    
    config_path = Path(__file__).parent.parent / "config" / "maru_config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    validator = HysteresisValidator(config)
    
    # Test sequence with violations
    test_sequence = [0.10, 0.11, 0.12, 0.11, 0.12, 0.16, 0.16, 0.16]
    
    analysis = validator.analyze_sequence(test_sequence)
    report = validator.generate_compliance_report(analysis)
    
    print(json.dumps(report, indent=2))
    print(f"\nCompliance Rate: {analysis['compliance_rate']:.2%}")
    print(f"Status: {analysis['status']}")
