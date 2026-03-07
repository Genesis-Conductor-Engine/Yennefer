/**
 * CODEOWNERS: Igor Holt
 * MODULE: Yennefer Security Layer + Soul Lattice SPA Worker
 * DESCRIPTION: Cloudflare Worker — JWT Validation, Static SPA Hosting, API Proxy
 */
import { jwtVerify, createRemoteJWKSet } from 'jose';

const SETTINGS = {
  AUDIENCE: "bb7516e1db2a1737ae11815f733f99940b82ea42ab46bf3d8cbd23817676a1f9",
  CERTS_URL: "https://iholt.cloudflareaccess.com/cdn-cgi/access/certs",
  ISSUER: "https://iholt.cloudflareaccess.com",
};

// JWKS with built-in caching from jose
const JWKS = createRemoteJWKSet(new URL(SETTINGS.CERTS_URL));

// Static asset extensions — served without JWT auth so the React bundle loads
const STATIC_EXT = /\.(js|css|png|jpg|jpeg|ico|svg|woff2?|ttf|eot|map|webp)$/;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1. Static assets bypass auth — browser fetches these before the JWT cookie is set
    if (STATIC_EXT.test(url.pathname)) {
      return env.ASSETS.fetch(request);
    }

    // 2. Health check — unauthenticated, used by uptime monitors
    if (url.pathname === '/health') {
      return new Response('OK', { status: 200 });
    }

    // 3. All other traffic requires a valid Cloudflare Access JWT
    const authResult = await validateJWT(request);
    if (!authResult.ok) {
      return authResult.response;
    }

    // 4. API proxy — forward /api/* to the Go backend (Cloud Run or env.BACKEND_URL)
    if (url.pathname.startsWith('/api/')) {
      return proxyToBackend(request, url, env, authResult.email);
    }

    // 5. SPA fallback — all remaining routes get index.html so React Router works
    const indexRequest = new Request(new URL('/', url).toString(), {
      method: 'GET',
      headers: request.headers,
    });
    return env.ASSETS.fetch(indexRequest);
  },
};

// ─── JWT Validation ───────────────────────────────────────────────────────────

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
    const { payload } = await jwtVerify(jwt, JWKS, {
      issuer: SETTINGS.ISSUER,
      audience: SETTINGS.AUDIENCE,
    });

    console.log(`[Yennefer] Authenticated: ${payload.email} at ${new Date().toISOString()}`);
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
  const target = `${backendUrl}${url.pathname}${url.search}`;

  const headers = new Headers(request.headers);
  headers.set('X-User-Email', userEmail);
  headers.set('X-Forwarded-Host', url.host);

  const cf = request.headers.get('CF-Connecting-IP');
  if (cf) headers.set('X-Forwarded-For', cf);

  // Strip Cloudflare Access headers before forwarding to the origin
  headers.delete('Cf-Access-Jwt-Assertion');
  headers.delete('Cf-Access-Client-Id');
  headers.delete('Cf-Access-Client-Secret');

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
