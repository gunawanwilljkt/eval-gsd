# 03-SPEC — Production hardening

WHAT phase 03 delivers, precisely enough that the eval contract can be written against it before
any new code exists. Builds on the locked Phases 01 (signaling, `01-SPEC.md`) and 02 (client,
`02-SPEC.md`) — those contracts are unchanged. This phase makes the app deployable on the real
internet: TURN relay for symmetric NAT, scheme-correct + reconnecting signaling, abuse limits,
and TLS. The measurement split is the same as before: pure functions + a real driven server give
deterministic **Code** gates; the irreducible "real infra" check (a forced-relay call through a
real TURN server behind real TLS) is a documented **Human** UAT row.

## New requirements covered
REQ-11 (`/ice-servers` endpoint), REQ-12 (ephemeral TURN credentials), REQ-13 (scheme-correct
signaling URL), REQ-14 (reconnect with capped backoff + jitter), REQ-15 (per-connection rate
limit), REQ-16 (TLS / `wss`).

---

## 1. `GET /ice-servers` (REQ-11) — server endpoint

A new HTTP route on the same server/port.

- **Method/path:** `GET /ice-servers`.
- **Response:** `200`, `content-type: application/json`, body `{"iceServers":[ ... ]}`.
- **STUN default:** always includes the Google public STUN entry
  `{ "urls": "stun:stun.l.google.com:19302" }` (same server the client used to hardcode).
- **TURN when configured:** when **both** `TURN_URL` and `TURN_SECRET` env vars are set, the
  response **additionally** includes a TURN entry with **ephemeral** credentials (§2):
  `{ "urls": "<TURN_URL>", "username": "<expiryTs>:<userid>", "credential": "<base64-hmac>" }`.
  When TURN env is absent → STUN entry only (no TURN entry).
- **Per-request evaluation:** env is read **per request** so credentials are freshly minted each
  call (ephemeral) and so a single running server can serve both STUN-only and TURN states
  depending on env — this is what makes EC-12 testable without restarts.

The endpoint is the single source of ICE config; the client fetches it instead of hardcoding STUN
(REQ-11 + replaces the Phase-02 `STUN_SERVERS` hardcode in the live path).

## 2. Ephemeral TURN credentials (REQ-12) — the coturn REST-API scheme

A **pure** exported helper, deterministic given its inputs (testable with Node `crypto`):

```
makeTurnCredential(secret, userid, expiryTs) -> { username, credential }
```

- `username = "<expiryTs>:<userid>"` — e.g. `"4102444800:alice"` (unix seconds, then a colon,
  then the user id). This is exactly coturn's `static-auth-secret` / "TURN REST API" username form.
- `credential = base64( HMAC_SHA1( key = secret, message = username ) )` — **standard** base64
  (not base64url), i.e. Node `crypto.createHmac('sha1', secret).update(username).digest('base64')`.

**Precomputed golden value (the EC-13 assertion target):** for
`secret = "s3cr3t-turn-key"`, `userid = "alice"`, `expiryTs = 4102444800`:
- `username  === "4102444800:alice"`
- `credential === "YxRVVa1+vr70jHjnKQ13MVipWvY="`

(Generated once via `node -e 'crypto.createHmac("sha1","s3cr3t-turn-key").update("4102444800:alice").digest("base64")'`
and frozen as a literal in the harness — the test asserts the helper reproduces this exact
string. Recomputing inside the test would be circular and prove nothing.)

**TTL / expiry in the live endpoint.** When `/ice-servers` mints a credential it computes
`expiryTs = floor(Date.now()/1000) + TTL`, where `TTL` defaults to **3600** seconds and is
overridable via `TURN_TTL` (seconds). `userid` defaults to `"talk"` and is overridable via
`TURN_USER`. So the live endpoint calls `makeTurnCredential(TURN_SECRET, TURN_USER||'talk',
now+TTL)`. Because expiry is wall-clock, EC-12 asserts the credential's **structure +
consistency** (username matches `^\d+:`, and `credential === makeTurnCredential(secret, userid,
<expiry parsed back from the username>).credential`) rather than a frozen literal; EC-13 asserts
the frozen literal against the pure helper directly.

### Env contract (TURN)
| Env | Meaning | Default |
|-----|---------|---------|
| `TURN_URL` | TURN server URL, e.g. `turn:turn.example.com:3478` | (none → no TURN entry) |
| `TURN_SECRET` | coturn `static-auth-secret` (shared HMAC key) | (none → no TURN entry) |
| `TURN_USER` | userid embedded in the credential username | `talk` |
| `TURN_TTL` | credential lifetime, seconds | `3600` |

TURN is emitted **only when both** `TURN_URL` and `TURN_SECRET` are present.

## 3. Scheme-correct signaling URL (REQ-13) — pure client helper

A **pure**, DOM-free exported helper in `public/call-core.js` (so it imports in Node):

```
signalingUrl(location) -> string
```

- Given `{ protocol: 'https:', host: 'h' }` → returns `"wss://h/ws"`.
- Given `{ protocol: 'http:',  host: 'h' }` → returns `"ws://h/ws"`.
- It reads only `location.protocol` and `location.host` — no `window`, so it stays pure. The DOM
  shell (`call.js`) calls `signalingUrl(window.location)`. This replaces the inline `wsUrl()` in
  `call.js`, removing the hardcode and making the choice unit-testable.

## 4. Reconnect with capped exponential backoff + jitter (REQ-14) — pure client helper

A **pure**, deterministic (rng-injected) exported helper in `public/call-core.js`:

```
backoffDelay(attempt, opts) -> milliseconds
```

- `attempt` is 0-based (0 = first retry).
- `opts = { base = 500, factor = 2, cap = 15000, jitter = 0.5, rng = Math.random }`.
- **Exponential, capped:** `raw = min(cap, base * factor ** attempt)`.
- **Bounded jitter:** the returned delay is `raw` scaled into the window
  `[ raw*(1-jitter) , raw ]` using `rng()` (a value in `[0,1)`):
  `delay = raw * (1 - jitter * rng())`. So with `rng()=0 → delay = raw`; with `rng()→1 →
  delay → raw*(1-jitter)`. **The delay never exceeds `cap`** (jitter only ever reduces `raw`,
  and `raw ≤ cap`), and never drops below `raw*(1-jitter) ≥ 0`. `rng` is injected so the test is
  deterministic.
- **Growth:** with `rng()=0` (jitter off), `backoffDelay(0)=500`, `backoffDelay(1)=1000`,
  `backoffDelay(2)=2000`, … doubling until it saturates at `cap=15000` (attempt ≥ 5 →
  `min(15000, 500*32)=15000`).

**Wiring in the DOM shell.** When the signaling `WebSocket` closes *unexpectedly while a call is
active* (not on an explicit hang-up / `room-full` teardown), `call.js` schedules a reconnect after
`backoffDelay(attempt++, ...)` ms, re-opens the socket, and re-sends `{type:'join', room}`. A
successful `joined` resets `attempt` to 0. Reconnection is best-effort and capped — it does not
change the Phase-01 protocol.

## 5. Per-connection message rate limit (REQ-15) — server

The signaling server throttles a single socket that floods it, so one client can't spam the relay
or exhaust the server.

- **Policy:** a **sliding window** of **20 inbound messages per 1000 ms**, per connection. Every
  inbound WebSocket message (any type, counted at the very top of the message handler, before
  parsing) records `Date.now()` in a per-socket ring; messages whose timestamp is older than the
  window are dropped from the count.
- **Action on breach:** when a socket's count within the trailing 1000 ms window exceeds 20, the
  server **closes that socket** with WebSocket close code **`4029`** (a private-use code meaning
  "rate limit exceeded") and stops relaying for it. The offending socket is treated like a normal
  disconnect (its room peer gets `peer-left`).
- **Timestamp-based, not timer-based.** The window is evaluated from stored timestamps on each
  message — **no `setInterval`/`setTimeout` timer is created**, so the limiter never keeps the
  Node event loop alive (the eval harness must still exit cleanly).
- **Headroom for real traffic.** The Phase-01/02 eval traffic and a minimal localhost handshake
  (a few host candidates) stay well under 20 msgs/sec/socket — confirmed by the no-regression run,
  which exercises EC-1..7 (a handful of frames each) and EC-10's localhost fake-media handshake
  (1–3 host candidates, no srflx/relay). **Caveat (not witnessed here):** a real multi-homed peer
  — especially with TURN configured — can emit 20–30+ ICE candidates in the initial gathering
  burst, each a separate `signal`, and could approach or exceed 20 msgs/1000ms. The limit is a
  per-deployment knob: tune `RATE_LIMIT.max`/`windowMs` for your expected candidate volume. The
  limiter is exported as a pure helper too (§contract) so the policy is independently checkable.

### Pure helper (testable)
```
makeRateLimiter({ max = 20, windowMs = 1000, now = Date.now }) -> { allow() -> boolean }
```
`allow()` records the current time and returns `true` while the count in the trailing window is
`<= max`, `false` once it exceeds `max`. The server creates one limiter per connection and closes
the socket the first time `allow()` returns `false`. EC-16 drives a **real** server with a real
`ws` client and asserts that flooding past the limit closes the socket (close code observed).

## 6. TLS / `wss` (REQ-16) — server

The server can serve HTTPS (and therefore `wss`, since the WebSocket server is attached to the
same HTTP(S) server) when TLS material is provided.

### Env contract (TLS)
| Env | Meaning |
|-----|---------|
| `TLS_CERT_FILE` | path to a PEM certificate (fullchain) |
| `TLS_KEY_FILE`  | path to the matching PEM private key |

- When **both** `TLS_CERT_FILE` and `TLS_KEY_FILE` are set and readable, `createServer()` builds
  an `https.createServer({ cert, key }, handler)` instead of `http.createServer(handler)`; the
  `WebSocketServer` attaches to it exactly as before (so the WS endpoint is now `wss://…/ws`).
- When TLS env is absent → plain `http` (unchanged dev behavior; browsers still allow camera/mic
  on `http://localhost`).
- **`createServer()` still returns `{ httpServer, wss, rooms, ... }`** — the `httpServer` key is
  preserved (now possibly an `https.Server`) so the Phase 01/02 harnesses that destructure it are
  unaffected. The endpoint and limiter additions are also backward compatible with EC-1..EC-11.

### Deploy artifacts
- **`Dockerfile`** — containerizes the server (Node base, installs `ws`, copies `server/` +
  `public/`, exposes the port, `CMD node server.js`). TURN/TLS are supplied via env + mounted
  cert files at deploy time.
- **`docs/DEPLOY.md`** — how to run behind TLS (cert/key env, or a TLS-terminating proxy) and how
  to stand up a coturn TURN server with a matching `static-auth-secret` = `TURN_SECRET`; the full
  env-var reference; the forced-relay UAT (EC-18).

## 7. Eval-first measurement split
- **Code (deterministic gates):** EC-12 `/ice-servers` STUN-only vs TURN (real driven server);
  EC-13 the pure `makeTurnCredential` golden literal; EC-14 the pure `signalingUrl`; EC-15 the
  pure `backoffDelay` (exponential + cap + bounded jitter, rng injected); EC-16 the real
  rate-limit close (real server + `ws` client).
- **Code (warn, skippable):** EC-17 optional self-signed TLS smoke — generate a cert via
  `openssl` if present, boot the server in TLS mode, connect `wss://` + `https` `/healthz` with
  `rejectUnauthorized:false`, assert `200`; **gate-SKIPs (exit 0)** if openssl/cert is
  unavailable (mirrors EC-10). Never blocks.
- **Human (UAT):** EC-18 — a real deploy behind TLS with a forced-relay call through a real TURN
  server. Documented in `docs/DEPLOY.md` + `03-VERIFICATION.md`; cannot run in this environment.

## Non-goals (this phase)
No group calls, recording, chat, auth, or persistence. No change to the Phase-01 signaling
protocol or the Phase-02 client logic beyond the additive items above. TURN bandwidth/cost
management and coturn operations are deployment concerns, documented but not automated.
