/**
 * CODEOWNERS: Igor Holt
 * MODULE: Yennefer Security Layer + Soul Lattice SPA Worker
 * DESCRIPTION: Cloudflare Worker — JWT Validation, Static SPA Hosting, API Proxy
 */

const SETTINGS = {
  AUDIENCE: "bb7516e1db2a1737ae11815f733f99940b82ea42ab46bf3d8cbd23817676a1f9",
  CERTS_URL: "https://iholt.cloudflareaccess.com/cdn-cgi/access/certs",
  ISSUER: "https://iholt.cloudflareaccess.com",
};

const STATIC_EXT = /\.(js|css|png|jpg|jpeg|ico|svg|woff2?|ttf|eot|webp)$/;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (STATIC_EXT.test(url.pathname)) {
      return env.ASSETS.fetch(request);
    }

    if (url.pathname === '/health') {
      return new Response('OK', { status: 200 });
    }

    if (url.pathname === '/api/health') {
      const healthUrl = new URL(url.toString());
      healthUrl.pathname = '/health';
      return proxyToBackend(request, healthUrl, env, 'health-check');
    }

    const authResult = await validateJWT(request);
    if (!authResult.ok) {
      return authResult.response;
    }

    if (url.pathname.startsWith('/api/')) {
      if (url.pathname === '/api/flush') {
        return new Response('Not Found', { status: 404 });
      }
      return proxyToBackend(request, url, env, authResult.email);
    }

    const indexRequest = new Request(new URL('/', url).toString(), {
      method: 'GET',
      headers: request.headers,
    });
    return env.ASSETS.fetch(indexRequest);
  },
};

let _jwksCache = null;
let _jwksCacheAt = 0;
const JWKS_TTL_MS = 10 * 60 * 1000;
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

const decodeB64 = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + "===".slice((s.length + 3) % 4)), c => c.charCodeAt(0));

async function validateJWT(request) {
  const jwt = request.headers.get('Cf-Access-Jwt-Assertion');

  if (!jwt) {
    return { ok: false, response: new Response('Missing Cloudflare Access Token', { status: 401 }) };
  }

  try {
    const parts = jwt.split('.');
    if (parts.length !== 3) throw new Error('Malformed JWT');
    const [headerB64, payloadB64, sigB64] = parts;

    const dec = new TextDecoder();
    const header = JSON.parse(dec.decode(decodeB64(headerB64)));
    const payload = JSON.parse(dec.decode(decodeB64(payloadB64)));

    if (header.alg !== 'RS256') throw new Error(`Unexpected JWT algorithm: ${header.alg}`);
    if (header.typ && header.typ !== 'JWT') throw new Error(`Unexpected JWT type: ${header.typ}`);

    const jwks = await getJWKS();
    const jwk = jwks.keys.find(k => k.kid === header.kid);
    if (!jwk) throw new Error(`No JWKS key for kid=${header.kid}`);

    let cryptoKey = _cryptoKeyCache.get(header.kid);
    if (!cryptoKey) {
      cryptoKey = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
      _cryptoKeyCache.set(header.kid, cryptoKey);
    }

    const message = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
    const valid = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', cryptoKey, decodeB64(sigB64), message);
    if (!valid) throw new Error('Signature verification failed');

    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) throw new Error('Token expired');
    if (payload.iss !== SETTINGS.ISSUER) throw new Error('Unexpected issuer');
    const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
    if (!aud.includes(SETTINGS.AUDIENCE)) throw new Error('Audience mismatch');

    return { ok: true, email: payload.email };
  } catch (error) {
    console.error('[Yennefer] JWT Validation Failed:', error.message);
    return { ok: false, response: new Response('Unauthorized: Invalid Token', { status: 403 }) };
  }
}

async function proxyToBackend(request, url, env, userEmail) {
  const backendUrl = (env.BACKEND_URL || 'http://localhost:8080').replace(/\/$/, '');
  const backendPath = url.pathname.replace(/^\/api/, '') || '/';
  const target = `${backendUrl}${backendPath}${url.search}`;

  const headers = new Headers(request.headers);
  if (userEmail) headers.set('X-User-Email', userEmail);
  headers.set('X-Forwarded-Host', url.host);

  const cf = request.headers.get('CF-Connecting-IP');
  if (cf) {
    const existing = request.headers.get('X-Forwarded-For');
    headers.set('X-Forwarded-For', existing ? `${existing}, ${cf}` : cf);
  }

  headers.delete('Cf-Access-Jwt-Assertion');
  headers.delete('Cf-Access-Client-Id');
  headers.delete('Cf-Access-Client-Secret');
  headers.delete('Cookie');

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
