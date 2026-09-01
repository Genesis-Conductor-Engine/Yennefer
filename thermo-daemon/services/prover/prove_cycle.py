from services.yennefer.thermodynamic_daemon import compute_thermodynamic_report, payload_digest, serialize_payload
from services.common.validation import validate_thermodynamic_report
def prove_cycle(evidence):
    report = compute_thermodynamic_report(evidence); validate_thermodynamic_report(report)
    return {"cycle_id": report["cycle_id"], "envelope_version": report["envelope_version"], "thermodynamic_report": report, "serialized_payload": serialize_payload(report), "payload_digest": payload_digest(report)}
def verify_cycle(evidence, claimed_digest):
    return prove_cycle(evidence)["payload_digest"] == claimed_digest
