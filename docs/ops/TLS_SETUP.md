# TLS / HTTPS setup (proposal, nothing applied)

Today the app is plain HTTP on the home server (192.168.4.4): API on :8010, nginx web on :8011. Public launch needs HTTPS (browser PWA service worker, secure transport for tokens, Apple sign-in, Play Store). Plan: Caddy as the single public entry point with automatic certificates.

Note: the app uses bearer tokens, not cookies (no `Set-Cookie` in backend or frontend), so there are no secure-cookie flags to flip. What matters is the origin names (CORS, CSP, link in reset email).

## Decisions and inputs needed from the owner
1. A domain name (for example `app.<domain>`), and where its DNS is managed (Cloudflare is easiest for either option).
2. How the home server is exposed: Option A (port-forward) or Option B (Cloudflare Tunnel), below.
3. Is the ISP IP public and stable (not CGNAT)? Does the router allow forwarding 80/443? Is :80/:443 already used on the box (the box also runs keyboard-sensei behind Caddy; reuse that Caddy or give LingoSquared its own)?
4. Approval to open ports, change DNS, and install/run Caddy on the server. A one-off agreement on the contact email for certificate notices.
5. The public origin for password-reset links (`PASSWORD_RESET_BASE_URL`) once email is set up.

## Option A: router port-forward 80/443 + DNS A record
Forward TCP 80 and 443 to the server, point an A (and AAAA if used) record at the home IP, and let Caddy obtain Let's Encrypt certificates over HTTP-01.
Pros: free, no third party in the data path, full control, simplest Caddy config.
Cons: exposes the home IP and the box directly to the internet; needs a static IP or dynamic DNS; fails behind CGNAT; ISP may block 80/443; no DDoS buffer; the home LAN depends on firewall hygiene (only forward 80/443, nothing else).

## Option B: Cloudflare Tunnel (cloudflared)
`cloudflared` makes an outbound connection to Cloudflare, which terminates TLS and routes the hostname to the server. No inbound ports, works behind CGNAT, hides the home IP, includes basic DDoS/WAF.
Pros: no port-forward, no certificate handling, works with dynamic IPs.
Cons: DNS must be on Cloudflare; Cloudflare can see the traffic (they terminate TLS); an extra dependency and a possible outage point; large uploads and WebSocket limits on the free tier; audio/media bandwidth terms apply. Caddy is optional here (the tunnel can target :8011 and :8010 directly), but keeping Caddy gives one place for path routing and headers.

Recommendation: Option B if the ISP uses CGNAT or the owner does not want ports open; otherwise A is fine and simpler to reason about. Either way the Caddy config below is the same.

## Routing: one origin, API under `/api`
Serving the API under the same origin avoids CORS and keeps the existing CSP (`'self'`) working. The frontend is currently built with `VITE_API_BASE_URL=http://192.168.4.4:8010` and nginx's CSP only allows `http(s)://*:8010` for API calls, so a separate `https://api.<domain>` host would also need a CSP change in `backend/nginx.web.conf`. With `/api` on the same origin no CSP change is needed.

`Caddyfile` (new file, for example `/home/ramin/lingosquared-caddy/Caddyfile`):
```
app.example.com {
    encode zstd gzip
    handle_path /api/* {
        reverse_proxy host.docker.internal:8010
    }
    handle {
        reverse_proxy host.docker.internal:8011
    }
}
```
`handle_path` strips `/api`, so `/api/health` reaches the API as `/health`. Confirm the API has no routes that rely on the original path prefix (it has none today). Caddy adds HSTS automatically only if configured; add `header Strict-Transport-Security "max-age=31536000"` after the first successful HTTPS test.

## docker-compose snippet (separate file, for example `docker-compose.caddy.yml`)
```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data        # certificates; keep this volume
      - caddy_config:/config
volumes:
  caddy_data:
  caddy_config:
```
For Option B, drop the `ports` and run `cloudflared` instead, with ingress `app.example.com -> http://caddy:80` (and set Caddy's site address to `http://app.example.com`).
Once HTTPS works, bind the raw ports to localhost so the plain-HTTP endpoints are not public: `API_PORT=127.0.0.1:8010` and `WEB_PORT=127.0.0.1:8011` in `backend/.env` (the compose files expand them as `"${API_PORT}:8000"` and `"${WEB_PORT}:80"`, so the prefix works). If Caddy runs in a container it reaches them through `host.docker.internal`, which still works with a localhost-published port only when Caddy uses host networking; simplest is to attach Caddy to the app's compose network and proxy to `api:8000` and `web:80` instead. LAN phone testing then goes through the hostname.

## Environment changes (server `backend/.env` and frontend build)
- `CORS_ORIGINS=https://app.example.com` (add `http://192.168.4.4:8011` only if LAN testing continues). Same-origin `/api` makes CORS mostly moot, but keep it correct.
- `PASSWORD_RESET_BASE_URL=https://app.example.com` (with `EMAIL_PROVIDER` set; see `backend/app/core/config.py`).
- `APP_ENV=production` already required.
- Frontend: rebuild with `VITE_API_BASE_URL=https://app.example.com/api` (build-time, so redeploy `web_dist`) and `VITE_PASSWORD_RESET_ENABLED` only when email works.
- Sentry stays on `https://*.ingest.de.sentry.io` (already in CSP).
- Social sign-in (if enabled): add the https origin to the Google client's authorised origins; Apple needs the real domain (`docs/SOCIAL_SIGN_IN.md`).

## Verify
`curl -I https://app.example.com/` returns 200 with a valid certificate, `curl https://app.example.com/api/health` returns ok, the app logs in, audio plays, the browser console shows no CSP or mixed-content errors, and the PWA install prompt appears. Rollback: stop `caddy`; the old `:8011` URL still works while ports are published.
