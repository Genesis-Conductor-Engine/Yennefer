/**
 * x402-cycle-intelligence — Yennefer Thermodynamic Daemon publication surface
 * envelope_version: 0.3.0
 * Gates checkout-sessions unless live evidence + confidence policy pass.
 * simulated_projection is advisory only.
 */
const ENVELOPE = "0.3.0";
const HANDOFF = "genesis-yennefer-thermodynamic-daemon-2026-05-03";
const THRESHOLDS = { route: 0.7, defer: 0.3 };

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "x-yennefer-envelope": ENVELOPE,
      "access-control-allow-origin": "*",
    },
  });
}

function digest(payload) {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(payload)).then((buf) =>
    [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("")
  );
}

function canonicalReport(input) {
  const observed = input.observed_route || {};
  const candidates = Array.isArray(input.candidates) ? input.candidates : [];
  const liveQuotes = Array.isArray(input.live_quotes) ? input.live_quotes : [];
  const hasLive = liveQuotes.length > 0;

  const observedCost = Number(observed.cost_eth);
  let best = null;
  for (const q of liveQuotes.concat(candidates)) {
    const c = Number(q.cost_eth);
    if (!Number.isFinite(c)) continue;
    if (!best || c < Number(best.cost_eth)) best = q;
  }

  const observedScore = Number.isFinite(observedCost) ? 1 / (1 + Math.max(0, observedCost)) : 0;
  const optimalScore = best && Number.isFinite(Number(best.cost_eth))
    ? 1 / (1 + Math.max(0, Number(best.cost_eth)))
    : 0;
  const inversionGap = Math.max(0, optimalScore - observedScore);
  const regret = Number.isFinite(observedCost) && best
    ? Math.max(0, observedCost - Number(best.cost_eth))
    : 0;
  const eta = hasLive ? Math.max(0, Math.min(1, optimalScore)) : 0;
  const confidence = hasLive ? Math.min(0.85, 0.4 + 0.1 * liveQuotes.length) : 0;

  let action = "defer";
  if (hasLive && eta >= THRESHOLDS.route && confidence >= 0.5) action = "route";
  else if (hasLive && eta >= THRESHOLDS.defer) action = "advisory";

  return {
    envelope_version: ENVELOPE,
    handoff_id: HANDOFF,
    cycle_id: input.cycle_id || `yenn.eta.${Date.now()}`,
    observed_route: observed,
    optimal_route: best
      ? { ...best, source: hasLive ? "live_quote" : "simulated_projection" }
      : { id: "none", source: "simulated_projection" },
    route_scores: {
      observed: Number(observedScore.toFixed(6)),
      optimal: Number(optimalScore.toFixed(6)),
      eta_thermo: Number(eta.toFixed(6)),
    },
    inversion_gap: Number(inversionGap.toFixed(6)),
    regret_eth: Number(regret.toFixed(8)),
    confidence: Number(confidence.toFixed(4)),
    checkout_sessions_gate: action === "route" ? "allow" : "deny",
    action,
    caveats: [
      "simulated_projection is advisory until backed by live quote evidence and policy gates",
      hasLive
        ? "Live quotes present; gate still requires eta_thermo >= 0.7 and confidence >= 0.5 for checkout-sessions"
        : "No live quotes supplied; checkout-sessions remain denied",
      "Biological terms in doctrine pages are analogies only",
    ],
  };
}

const DISCOVERY = {
  envelope_version: ENVELOPE,
  service: "x402-cycle-intelligence",
  handoff_id: HANDOFF,
  advertised: ["thermodynamic_report"],
  endpoints: {
    health: { method: "GET", path: "/health" },
    discovery: { method: "GET", path: "/.well-known/x402" },
    candidate: { method: "POST", path: "/candidate", returns: "thermodynamic_report" },
    report: { method: "POST", path: "/report", returns: "thermodynamic_report" },
    intelligence: { method: "POST", path: "/intelligence", returns: "thermodynamic_report" },
  },
  proof_contract: {
    thermodynamic_report_in_serialized_payload: true,
    recompute_before_payload_digest: true,
    required_fields: [
      "cycle_id",
      "observed_route",
      "optimal_route",
      "route_scores",
      "inversion_gap",
      "regret_eth",
      "confidence",
      "caveats",
    ],
  },
  thresholds: THRESHOLDS,
  shopify: {
    sku: "GENESIS-YENNEFER-THERMO-REPORT",
    status: "DRAFT_PENDING_OPERATOR",
    price_usd: 0.1,
  },
};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET,POST,OPTIONS",
          "access-control-allow-headers": "content-type,authorization,x-analyzer-token",
        },
      });
    }
    if (url.pathname === "/health" || url.pathname === "/") {
      return json({
        status: "ok",
        service: "x402-cycle-intelligence",
        envelope_version: ENVELOPE,
        advertised: ["thermodynamic_report"],
        timestamp: new Date().toISOString(),
      });
    }
    if (url.pathname === "/.well-known/x402" || url.pathname === "/discovery") {
      return json(DISCOVERY);
    }
    if (
      request.method === "POST" &&
      (url.pathname === "/report" ||
        url.pathname === "/candidate" ||
        url.pathname === "/intelligence")
    ) {
      let body = {};
      try {
        body = await request.json();
      } catch {
        body = {};
      }
      const report = canonicalReport(body);
      const serialized = JSON.stringify(report);
      const payload_digest = await digest(serialized);
      return json({
        thermodynamic_report: report,
        serialized_payload: serialized,
        payload_digest,
        verification: "recomputed_before_digest",
      });
    }
    return json({ error: "not_found", advertised: ["thermodynamic_report"] }, 404);
  },
};
