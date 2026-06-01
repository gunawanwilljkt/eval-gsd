# Deploying Talk in production (TLS + TURN)

In development, two tabs on `http://localhost:8080` are enough — browsers allow camera/mic on
`localhost`, and Google's public STUN traverses most home/office NATs. To run on the **real
internet** you need two more things, both added in Phase 03:

1. **TLS / `wss`** — outside `localhost`, browsers refuse `getUserMedia` unless the page is HTTPS,
   and the signaling socket must then be `wss://`. (REQ-13, REQ-16)
2. **A TURN server** — STUN alone fails on **symmetric NAT** (some corporate/cellular networks).
   A TURN relay carries the media when a direct path can't be found. (REQ-11, REQ-12)

This document covers both, plus the full env-var reference and the forced-relay UAT (EC-18).

---

## 1. Environment variables

| Env | Purpose | Default |
|-----|---------|---------|
| `PORT` | listen port | `8080` |
| `TLS_CERT_FILE` | path to a PEM certificate (fullchain) — enables HTTPS + `wss` | (none → HTTP) |
| `TLS_KEY_FILE` | path to the matching PEM private key | (none → HTTP) |
| `TURN_URL` | TURN server URL, e.g. `turn:turn.example.com:3478` | (none → no TURN entry) |
| `TURN_SECRET` | coturn `static-auth-secret` (shared HMAC key) | (none → no TURN entry) |
| `TURN_USER` | userid embedded in the ephemeral credential username | `talk` |
| `TURN_TTL` | credential lifetime, seconds | `3600` |

- **TLS** turns on only when **both** `TLS_CERT_FILE` and `TLS_KEY_FILE` are set and readable.
- **TURN** is advertised by `GET /ice-servers` only when **both** `TURN_URL` and `TURN_SECRET`
  are set; otherwise the endpoint returns STUN only.

---

## 2. TLS — two options

### Option A: terminate TLS at the Node server
Mount a real cert (e.g. from Let's Encrypt / `certbot`) and point the env at it:

```bash
docker run -p 443:8443 \
  -e PORT=8443 \
  -e TLS_CERT_FILE=/certs/fullchain.pem \
  -e TLS_KEY_FILE=/certs/privkey.pem \
  -v /etc/letsencrypt/live/talk.example.com:/certs:ro \
  talk
```

The same port now serves `https://…` and `wss://…/ws`. The client picks `wss` automatically
because it derives the scheme from `window.location` (`signalingUrl()` — REQ-13).

### Option B: terminate TLS at a reverse proxy
Run Talk as plain HTTP behind nginx/Caddy/an ELB that terminates TLS and forwards (including the
WebSocket `Upgrade` headers) to the container. Leave `TLS_*` unset on the container. Example
nginx location:

```nginx
location / {
  proxy_pass http://talk:8080;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;       # WebSocket upgrade
  proxy_set_header Connection "upgrade";
  proxy_set_header Host $host;
}
```

> Local self-signed smoke: the test `node test/eval-phase3.mjs EC-17` generates a throwaway cert
> via `openssl`, boots the server with `TLS_*`, and asserts `https /healthz` 200 + a `wss`
> handshake (skips cleanly if openssl is absent). Use the same pattern to sanity-check a host:
> `openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 1 -subj /CN=localhost`.

---

## 3. TURN — stand up coturn

Install [coturn](https://github.com/coturn/coturn). The key line is a **shared secret** that
matches `TURN_SECRET` — the app and coturn never exchange per-user passwords; instead the app
mints **time-limited** credentials that coturn verifies statelessly (the coturn "TURN REST API",
a.k.a. `use-auth-secret`).

`/etc/turnserver.conf`:
```ini
listening-port=3478
fingerprint
use-auth-secret
static-auth-secret=<SAME VALUE AS TURN_SECRET>
realm=turn.example.com
# TLS for turns:// (optional but recommended)
# cert=/certs/fullchain.pem
# pkey=/certs/privkey.pem
```

Run the app pointing at it:
```bash
docker run -p 443:8443 \
  -e PORT=8443 \
  -e TLS_CERT_FILE=/certs/fullchain.pem -e TLS_KEY_FILE=/certs/privkey.pem \
  -e TURN_URL=turn:turn.example.com:3478 \
  -e TURN_SECRET=<SAME VALUE AS static-auth-secret> \
  -e TURN_USER=talk -e TURN_TTL=3600 \
  -v /certs:/certs:ro \
  talk
```

### How the credential works (REQ-12)
On each `GET /ice-servers` the server computes, fresh:
```
expiry     = floor(now/1000) + TURN_TTL
username   = "<expiry>:<TURN_USER>"
credential = base64( HMAC-SHA1( key = TURN_SECRET, message = username ) )
```
coturn recomputes the same HMAC from its `static-auth-secret` and accepts the credential until
`expiry`. Because the credential is minted per request and expires, a leaked credential is only
briefly useful. Verify the formula with `node test/eval-phase3.mjs EC-13` (frozen golden value).

Example response when TURN is configured:
```json
{
  "iceServers": [
    { "urls": "stun:stun.l.google.com:19302" },
    { "urls": "turn:turn.example.com:3478", "username": "1717200000:talk", "credential": "…base64…" }
  ]
}
```

---

## 4. Build & run the container

```bash
# from the repo root
docker build -t talk .
docker run -p 8080:8080 talk          # dev: HTTP, STUN-only
# production: add the -e TLS_* and -e TURN_* flags from above
```

Health check: `GET /healthz` → `200 ok`. ICE config: `GET /ice-servers`.

---

## 5. UAT — EC-18 (forced-relay call through real TURN behind TLS)

This is the one check that needs real infrastructure (it can't run in CI). After deploying with
both TLS and TURN:

1. Open the **HTTPS** site in two browsers on networks that require relay (or force relay-only ICE
   in `chrome://webrtc-internals`, or with a browser flag / test page that sets
   `iceTransportPolicy: 'relay'`).
2. Join the same room in both.
3. **PASS:** both sides see and hear each other; in `chrome://webrtc-internals` the selected
   candidate pair is of type **`relay`** (proving media went through TURN, not a direct/STUN
   path); `GET /ice-servers` returned a fresh `turn:` entry with a future-dated `username`.
4. **FAIL:** no TURN entry returned, coturn rejects the credential (check that `TURN_SECRET` ==
   `static-auth-secret` and the server clock is correct), or the relay never connects.

---

## 6. Operational notes
- **TURN bandwidth costs money** — relayed media flows through your server. Scope `TURN_TTL` and
  monitor coturn usage. (Out of scope to automate here.)
- **Clock skew** breaks the credential check — keep the app and coturn on NTP.
- The signaling server is **stateless beyond the in-memory room map**; scale-out needs sticky
  sessions or a shared room registry (future milestone).
