from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any, Dict, List
ENVELOPE_VERSION = "0.3.0"
REQUIRED_REPORT_FIELDS = ("cycle_id","observed_route","optimal_route","route_scores","inversion_gap","regret_eth","confidence","caveats")
def _score_route(route):
    cost = float(route.get("cost_eth", 0.0)); latency = float(route.get("latency_ms", 0.0)); drag = float(route.get("drag", 0.0))
    raw = cost * 250.0 + (latency / 2000.0) + drag
    return max(0.0, min(1.0, 1.0 / (1.0 + raw)))
def compute_thermodynamic_report(evidence):
    observed = evidence.get("observed_route") or {}
    candidates = list(evidence.get("candidate_routes") or [])
    cycle_id = evidence.get("cycle_id") or "cycle-unspecified"
    policy = evidence.get("policy_gates") or {}
    live_quotes = evidence.get("quote_evidence")
    scored = []
    for route in [observed, *candidates]:
        if not route: continue
        scored.append({"id": route.get("id"), "score": round(_score_route(route), 6), "cost_eth": route.get("cost_eth"), "drag": route.get("drag"), "advisory": route is not observed and live_quotes is None})
    observed_score = _score_route(observed) if observed else 0.0
    optimal, optimal_score = observed, observed_score
    for route in candidates:
        s = _score_route(route)
        if s > optimal_score: optimal, optimal_score = route, s
    inversion_gap = round(max(0.0, optimal_score - observed_score), 6)
    regret_eth = round(max(0.0, float(observed.get("cost_eth", 0.0)) - float(optimal.get("cost_eth", 0.0))), 8)
    caveats = ["simulated_projection is advisory until backed by live quote evidence and policy gates.", "Biological terms in surrounding documentation are analogies only.", "eta_thermo reports wrap envelope_version 0.3.0 and must not activate checkout-sessions without operator gate."]
    if live_quotes is None: caveats.append("No live quote_evidence present; optimal_route is a simulated projection.")
    if not policy.get("checkout_sessions_enabled"): caveats.append("index.yennefer.checkout-sessions remains gated (not enabled).")
    confidence = 0.42 if live_quotes is None else 0.86
    if policy.get("live_quotes_required") and live_quotes is None: confidence = min(confidence, 0.38)
    return {"envelope_version": ENVELOPE_VERSION, "cycle_id": cycle_id, "observed_route": observed, "optimal_route": optimal, "route_scores": scored, "inversion_gap": inversion_gap, "regret_eth": regret_eth, "confidence": confidence, "caveats": caveats, "simulated_projection": live_quotes is None, "checkout_sessions_gated": not bool(policy.get("checkout_sessions_enabled"))}
def serialize_payload(report):
    payload = {k: report[k] for k in REQUIRED_REPORT_FIELDS}; payload["envelope_version"] = report.get("envelope_version", ENVELOPE_VERSION)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
def payload_digest(report):
    return hashlib.sha256(serialize_payload(report).encode("utf-8")).hexdigest()
def main():
    p = argparse.ArgumentParser(); p.add_argument("--input", required=True); p.add_argument("--output", required=True); a = p.parse_args()
    evidence = json.loads(Path(a.input).read_text()); report = compute_thermodynamic_report(evidence); report["payload_digest"] = payload_digest(report)
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"ok": True, "output": str(out), "digest": report["payload_digest"]}))
if __name__ == "__main__": main()
