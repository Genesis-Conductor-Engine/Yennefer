const ENVELOPE_VERSION = "0.3.0";
function discovery() {
  return {
    envelope_version: ENVELOPE_VERSION,
    advertised: ["thermodynamic_report"],
    endpoints: {
      candidate: { advertises: "thermodynamic_report", gated: false },
      report: { advertises: "thermodynamic_report", gated: false },
      intelligence: { advertises: "thermodynamic_report", gated: false },
      "checkout-sessions": { advertises: "thermodynamic_report", gated: true }
    },
    sku: "GENESIS-YENNEFER-THERMO-REPORT",
    status: "draft-ready"
  };
}
function health() {
  return { ok: true, service: "x402-cycle-intelligence", envelope_version: ENVELOPE_VERSION };
}
module.exports = { discovery, health, ENVELOPE_VERSION };
