# 03-VERIFICATION — Production hardening

Verdict produced by the merged eval-verify (framework W5): coverage + weakening + gaming + gate rows.

## Verdict: ✅ PASS (Code gates green; Human row EC-18 pending real-infra UAT)

| Check | Result |
|-------|--------|
| **Gate rows (Code)** | EC-12, EC-13, EC-14, EC-15, EC-16 all GREEN via `npm run eval3` (exit 0). Each also passes standalone (`node test/eval-phase3.mjs EC-12`, `… EC-13`, …). |
| **Warn row (Code)** | EC-17 self-signed TLS smoke: **PASS** — `node test/eval-phase3.mjs EC-17` → "TLS: https /healthz 200 + wss handshake (self-signed)", exit 0 (openssl 3.6.2 present; generates a throwaway cert, boots the server with `TLS_CERT_FILE`/`TLS_KEY_FILE`, connects `wss://` + `https /healthz` with `rejectUnauthorized:false`). **Gate-SKIPs cleanly** (exit 0) where openssl/cert is unavailable — mirrors EC-10, never blocks. |
| **Human row** | EC-18 (forced-relay TURN call behind real TLS) — machine-reported as `HUMAN`; verified at UAT step U-3 below + `docs/DEPLOY.md §5`. Cannot run here (no public TLS domain, no coturn). |
| **Coverage gate (§3)** | REQ-11→EC-12; REQ-12→EC-13; REQ-13→EC-14; REQ-14→EC-15; REQ-15→EC-16; REQ-16→EC-17 (warn Code smoke) + EC-18 (Human UAT). Every REQ-11..16 maps to ≥1 row; no orphan rows (7 rows total). Bijection holds. |
| **Weakening detector (§4)** | `locked_hash` recompute (§2.1 command) = `52bedb40…a5dfc477` — matches the locked value. No row deleted/loosened. |
| **Gaming detector (§4)** | Green commit `e57d86a` (`server.js` + `call-core.js` + `call.js` + `Dockerfile` + `docs/DEPLOY.md`, 5 files) does **not** touch `server/test/eval-phase3.mjs`. Evals committed RED first (`f2188bd`), code second — `git show e57d86a --stat` is eval-file-clean. |
| **Purity (eval-first crux)** | `grep -vE '^\s*//' public/call-core.js \| grep -nE '\b(document\|navigator\|window\|RTCPeerConnection\|getUserMedia)\b'` → zero hits in non-comment code. `signalingUrl` + `backoffDelay` are pure (reads only `location.protocol/host`; injected `rng`) → Node-gatable. |
| **No regression** | `npm test` (Phases 01+02+03 deterministic rows) → exit 0. Phase 01 still 7/7 GREEN; Phase 02 EC-9/EC-11 + EC-10 smoke GREEN. Phase 01/02 contract hashes unchanged (`4dce1263…`, `c0aa6452…`). `createServer()` still returns the `httpServer` key (the rate limiter is timestamp-windowed — no timer — so the harness still exits cleanly). The 20 msgs/1000ms limit does not trip on the Phase-01/02 eval traffic or EC-10's localhost handshake (witnessed by the green run). **Honest caveat (not witnessed here):** a real multi-homed peer / TURN burst can emit 20–30+ ICE candidates and approach the limit — `RATE_LIMIT.max` is a per-deployment knob (see 03-SPEC §5). EC-16 only proves "flooding past the limit closes the socket," which is tested. |

## Evidence
- **RED run (pre-impl):** `node test/eval-phase3.mjs` → `SyntaxError: … does not provide an export named 'backoffDelay'`, exit 1 — link-time discriminator across all rows (mirrors Phases 01/02).
- **GREEN run (post-impl):** `npm run eval3` → `GATE GREEN — gate rows pass (1 human)`, exit 0. Rows: EC-12 PASS, EC-13 PASS, EC-14 PASS, EC-15 PASS, EC-16 PASS, EC-17 PASS (TLS smoke), EC-18 HUMAN.
- **Intent ladder:**
  - EC-13 asserts the **exact** coturn-REST credential (`makeTurnCredential('s3cr3t-turn-key','alice',4102444800)` → username `"4102444800:alice"`, credential `"YxRVVa1+vr70jHjnKQ13MVipWvY="`) against a **frozen golden literal** — so a real coturn (sharing the secret) will accept what the server mints (REQ-12). EC-12 proves the live `/ice-servers` uses that scheme with ephemeral, future-dated expiry (REQ-11).
  - EC-16 drives a **real** server with a real `ws` client: a socket that floods past 20 msgs/1000ms is closed with code 4029 while a polite peer stays OPEN — one client can't spam the relay (REQ-15).
  - EC-15 proves the reconnect delay grows exponentially (500→1000→2000→4000), saturates at the 15000 cap, and for any attempt with injected `rng∈{0,1}` stays within `[raw·(1-jitter), raw]` and never exceeds the cap (REQ-14). EC-14 proves scheme-correct `wss`/`ws` selection (REQ-13).
  - The irreducible "real relay actually carries media behind real TLS" is carried by EC-17 (self-signed TLS smoke, automatable) + EC-18 (Human, real coturn) — honest measurement split.

## Human / UAT — run before declaring the phase fully user-verified

### U-3 — forced-relay call through real TURN behind TLS (EC-18, REQ-16)
Deploy per `docs/DEPLOY.md` (TLS cert + a coturn server whose `static-auth-secret` == `TURN_SECRET`,
`TURN_URL` pointed at it). Open the **HTTPS** site in two browsers that require relay (or force
`iceTransportPolicy:'relay'`), join the same room.
- PASS: both sides see/hear each other over `wss://`; the selected ICE candidate pair is type
  **`relay`** in `chrome://webrtc-internals` (media went through TURN); `/ice-servers` returned a
  fresh `turn:` entry with a future-dated `username`.
- FAIL: no TURN entry, coturn rejects the credential (check secret match + clock), or relay never connects.

## Conclusion
Phase 03 delivers REQ-11..16, gated by a locked contract, verified clean. Code gates (EC-12..EC-16)
green; EC-17 TLS smoke green (and skip-safe); no regression (P01 7/7, P02 gates green, all three
contract hashes match). The one remaining item — EC-18, a forced-relay call through a real coturn
TURN server behind real public TLS — is a documented **Human UAT** requiring infrastructure that
can't exist in this environment (no public domain, no TURN server). It is fully specified in
`docs/DEPLOY.md §5` + U-3 above so it can be run on a real deploy.
