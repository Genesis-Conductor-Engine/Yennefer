/**
 * CODEOWNERS: Igor Holt
 * MODULE: Yennefer Security Layer + Soul Lattice SPA Worker
 * DESCRIPTION: Cloudflare Worker — JWT Validation, Static SPA Hosting, API Proxy
 *
 * JWT validation uses the native Web Crypto API (no external npm deps).
 * Cloudflare Access issues RS256 JWTs; public keys are fetched from the JWKS
 * endpoint and cached in module-scope for the lifetime of the V8 isolate.
 */

const SETTINGS = {
  AUDIENCE: "bb7516e1db2a1737ae11815f733f99940b82ea42ab46bf3d8cbd23817676a1f9",
  CERTS_URL: "https://iholt.cloudflareaccess.com/cdn-cgi/access/certs",
  ISSUER: "https://iholt.cloudflareaccess.com",
};

// Static asset extensions — served without JWT auth so the React bundle loads.
// Source maps (.map) are intentionally excluded: they expose readable source and
// must either require auth or not be uploaded (GENERATE_SOURCEMAP=false at build).
const STATIC_EXT = /\.(js|css|png|jpg|jpeg|ico|svg|woff2?|ttf|eot|webp)$/;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1. Static assets (JS/CSS/fonts/images) bypass JWT validation.
    //    These are fetched by the browser after Cloudflare Access has already
    //    authenticated the user at the edge and set the JWT cookie.  Skipping
    //    JWKS validation on every asset avoids unnecessary crypto overhead on a
    //    hot path.
    //
    //    HTML entry-points (/, /index.html) are NOT matched here and ARE gated
    //    by validateJWT() below.  This is intentional: Cloudflare Access injects
    //    a valid Cf-Access-Jwt-Assertion header before the Worker sees any
    //    request, so authenticated users always arrive with a token.
    //    Unauthenticated users are redirected to the Access login page by
    //    Cloudflare before reaching this Worker.
    if (STATIC_EXT.test(url.pathname)) {
      return env.ASSETS.fetch(request);
    }

    // 2. Worker-only health check — unauthenticated, used by uptime monitors
    if (url.pathname === '/health') {
      return new Response('OK', { status: 200 });
    }

    // 3. Backend health passthrough — unauthenticated; verifies BACKEND_URL is
    //    reachable AND exercises proxyToBackend() so the same code path used by
    //    authenticated /api/* routes is covered by post-deploy smoke tests.
    //    Rewrites /api/health → /health to match the Go server's Heartbeat route.
    if (url.pathname === '/api/health') {
      const healthUrl = new URL(url.toString());
      healthUrl.pathname = '/health';
      return proxyToBackend(request, healthUrl, env, 'health-check');
    }

    // 4. All other traffic requires a valid Cloudflare Access JWT
    const authResult = await validateJWT(request);
    if (!authResult.ok) {
      return authResult.response;
    }

    // 5. API proxy — forward /api/* to the Go backend.
    //    /api/flush is intentionally blocked here; state resets are admin-only
    //    and should only be performed via direct backend access.
    //    proxyToBackend strips the /api prefix before forwarding so backend
    //    routes (/state, /events, /health) are matched exactly as registered.
    if (url.pathname.startsWith('/api/')) {
      if (url.pathname === '/api/flush') {
        return new Response('Not Found', { status: 404 });
      }
      return proxyToBackend(request, url, env, authResult.email);
    }

    // 6. SPA fallback — all remaining routes get index.html so React Router works
    const indexRequest = new Request(new URL('/', url).toString(), {
      method: 'GET',
      headers: request.headers,
    });
    return env.ASSETS.fetch(indexRequest);
  },
};

// ─── JWKS cache ───────────────────────────────────────────────────────────────
// Module-scope variables persist for the lifetime of the V8 isolate (~minutes).

let _jwksCache = null;
let _jwksCacheAt = 0;
const JWKS_TTL_MS = 10 * 60 * 1000; // 10 minutes

// CryptoKey cache: kid → CryptoKey.  importKey() is relatively expensive;
// caching avoids re-importing the same public key on every authenticated request.
const _cryptoKeyCache = new Map();

async function getJWKS() {
  const now = Date.now();
  if (_jwksCache && now - _jwksCacheAt < JWKS_TTL_MS) return _jwksCache;
  const res = await fetch(SETTINGS.CERTS_URL);
  if (!res.ok) throw new Error(`JWKS fetch failed with status ${res.status}`);
  _jwksCache = await res.json();
  _jwksCacheAt = now;
  return _jwksCache;
}

// ─── JWT Validation (native Web Crypto) ──────────────────────────────────────

function parseB64(s){return Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/').padEnd(s.length+(4-s.length%4)%4,'=')),c=>c.charCodeAt(0))}

async function validateJWT(request) {
  const jwt = request.headers.get('Cf-Access-Jwt-Assertion');

  if (!jwt) {
    return {
      ok: false,
      response: new Response('Missing Cloudflare Access Token', {
        status: 401,
        headers: { 'Content-Type': 'text/plain' },
      }),
    };
  }

  try {
    const parts = jwt.split('.');
    if (parts.length !== 3) throw new Error('Malformed JWT');
    const [headerB64, payloadB64, sigB64] = parts;

    const dec = new TextDecoder();
    const header = JSON.parse(dec.decode(parseB64(headerB64)));
    const payload = JSON.parse(dec.decode(parseB64(payloadB64)));

    // Reject unexpected algorithm/type before touching the crypto path to
    // prevent algorithm-confusion attacks and fail fast for auditing.
    if (header.alg !== 'RS256') throw new Error(`Unexpected JWT algorithm: ${header.alg}`);
    if (header.typ && header.typ !== 'JWT') throw new Error(`Unexpected JWT type: ${header.typ}`);

    // Find the matching public key by kid
    const jwks = await getJWKS();
    const jwk = jwks.keys.find(k => k.kid === header.kid);
    if (!jwk) throw new Error(`No JWKS key for kid=${header.kid}`);

    // Cloudflare Access uses RS256 (RSASSA-PKCS1-v1_5 + SHA-256).
    // Cache the imported CryptoKey by kid so we pay the importKey cost only
    // once per key rotation rather than on every authenticated request.
    let cryptoKey = _cryptoKeyCache.get(header.kid);
    if (!cryptoKey) {
      cryptoKey = await crypto.subtle.importKey(
        'jwk', jwk,
        { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
        false, ['verify'],
      );
      _cryptoKeyCache.set(header.kid, cryptoKey);
    }

    const message = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
    const valid = await crypto.subtle.verify(
      'RSASSA-PKCS1-v1_5', cryptoKey, parseB64(sigB64), message,
    );
    if (!valid) throw new Error('Signature verification failed');

    // Validate standard claims
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) throw new Error('Token expired');
    if (payload.iss !== SETTINGS.ISSUER) throw new Error('Unexpected issuer');
    const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
    if (!aud.includes(SETTINGS.AUDIENCE)) throw new Error('Audience mismatch');

    return { ok: true, email: payload.email };
  } catch (error) {
    console.error('[Yennefer] JWT Validation Failed:', error.message);
    return {
      ok: false,
      response: new Response('Unauthorized: Invalid or Expired Token', {
        status: 403,
        headers: { 'Content-Type': 'text/plain' },
      }),
    };
  }
}

// ─── API Proxy ────────────────────────────────────────────────────────────────

async function proxyToBackend(request, url, env, userEmail) {
  const backendUrl = (env.BACKEND_URL || 'http://localhost:8080').replace(/\/$/, '');
  // Strip the /api prefix: Worker routes are /api/*, but the Go backend
  // registers routes at /state, /events, /flush, /health (no /api prefix).
  const backendPath = url.pathname.replace(/^\/api/, '') || '/';
  const target = `${backendUrl}${backendPath}${url.search}`;

  const headers = new Headers(request.headers);
  // Only propagate the email when the JWT actually contained the claim —
  // absent claims produce undefined, which would stringify to "undefined".
  if (userEmail) headers.set('X-User-Email', userEmail);
  headers.set('X-Forwarded-Host', url.host);

  // Append to existing X-Forwarded-For chain instead of overwriting, so
  // upstream proxies can see the full client IP chain.
  const cf = request.headers.get('CF-Connecting-IP');
  if (cf) {
    const existing = request.headers.get('X-Forwarded-For');
    headers.set('X-Forwarded-For', existing ? `${existing}, ${cf}` : cf);
  }

  // Strip headers that must not reach the backend: Cloudflare Access tokens
  // (already validated) and Cookie (the Go backend uses no session cookies;
  // forwarding them would leak user session data to the origin unnecessarily).
  headers.delete('Cf-Access-Jwt-Assertion');
  headers.delete('Cf-Access-Client-Id');
  headers.delete('Cf-Access-Client-Secret');
  headers.delete('Cookie');

  // Forward the shared secret so the backend can verify requests originate
  // from this Worker rather than direct Cloud Run access.
  if (env.BACKEND_TOKEN) headers.set('X-Backend-Token', env.BACKEND_TOKEN);

  try {
    return await fetch(new Request(target, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? null : request.body,
    }));
  } catch (err) {
    console.error('[Yennefer] Backend proxy error:', err.message);
    return new Response('Backend Unavailable', { status: 502 });
  }
}
