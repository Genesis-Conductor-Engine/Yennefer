REQUIRED = ("cycle_id","observed_route","optimal_route","route_scores","inversion_gap","regret_eth","confidence","caveats")
def validate_thermodynamic_report(report):
    missing = [k for k in REQUIRED if k not in report]
    if missing: raise ValueError(f"missing: {missing}")
