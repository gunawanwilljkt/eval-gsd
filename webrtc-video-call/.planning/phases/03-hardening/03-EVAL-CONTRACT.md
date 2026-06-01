---
eval_contract_version: '1.0'
phase: '03-hardening'
status: locked
locked_hash: '52bedb407a44beb4b4297c417ebe8830c83140f8289a0e5cf0383999a5dfc477'
locked_at: '2026-06-01'
coverage:
  requirements: [REQ-11, REQ-12, REQ-13, REQ-14, REQ-15, REQ-16]
  rows_total: 7
  uncovered_reqs: []
  orphan_rows: []
---

# Phase 03 — Eval Contract (Production hardening)

Intent: "The same in-seconds call works on the real internet — across hard NATs (TURN), over a
secure connection (TLS/`wss`), without one client being able to flood the relay, and surviving a
brief network blip (reconnect)." The logic that *can* be deterministic is factored into PURE
functions (`makeTurnCredential`, `signalingUrl`, `backoffDelay`, `makeRateLimiter`) so the gates
run in Node with no browser and no external infra; the `/ice-servers` endpoint and the rate-limit
close are driven against a REAL server (like Phase 01). The irreducible "real infra" check — a
forced-relay call through a real TURN server behind real TLS — is a Human/UAT row.

Each row's command runs the Phase-03 harness for exactly that check and exits 0 (pass) / non-zero
(fail). Run from the `server/` directory. `npm run eval3` runs them all.

## Rows

| id | objective_ref | req_ref | behavior | measurement | command_or_rubric | sample_rate | severity |
|----|---------------|---------|----------|-------------|-------------------|-------------|----------|
| EC-12 | talk | REQ-11 | GET /ice-servers returns {iceServers:[...]} with the STUN entry and NO turn entry when TURN env is absent; with TURN_URL+TURN_SECRET set it ALSO returns a turn entry whose username matches ^[0-9]+: and whose credential equals makeTurnCredential(secret,userid,expiry-from-username) | Code | node test/eval-phase3.mjs EC-12 | per-task | gate |
| EC-13 | talk | REQ-12 | pure makeTurnCredential('s3cr3t-turn-key','alice',4102444800) returns username "4102444800:alice" and credential "YxRVVa1+vr70jHjnKQ13MVipWvY=" (base64 HMAC-SHA1 of the username under the secret) — asserted against the frozen golden literal | Code | node test/eval-phase3.mjs EC-13 | per-task | gate |
| EC-14 | talk | REQ-13 | pure signalingUrl({protocol:'https:',host:'h'}) === 'wss://h/ws' and signalingUrl({protocol:'http:',host:'h'}) === 'ws://h/ws' | Code | node test/eval-phase3.mjs EC-14 | per-task | gate |
| EC-15 | talk | REQ-14 | pure backoffDelay grows exponentially pre-cap (rng=0 → 500,1000,2000,4000), saturates at cap=15000, and for ANY attempt with injected rng∈{0,1} stays within [raw*(1-jitter), raw] and never exceeds cap | Code | node test/eval-phase3.mjs EC-15 | per-task | gate |
| EC-16 | talk | REQ-15 | flooding a real server's WebSocket with > the per-connection limit (20 msgs/1000ms) within the window causes the server to close that socket (close code 4029); a well-behaved peer is unaffected | Code | node test/eval-phase3.mjs EC-16 | per-task | gate |
| EC-17 | talk | REQ-16 | self-signed TLS smoke — generate a cert via openssl, start the server in TLS mode (TLS_CERT_FILE/TLS_KEY_FILE), connect wss:// and GET https /healthz with rejectUnauthorized:false → 200; gate-SKIPS (exit 0) if openssl/cert unavailable | Code | node test/eval-phase3.mjs EC-17 | pre-verify | warn |
| EC-18 | talk | REQ-16 | real deploy behind TLS with a forced-relay (relay-only ICE) call through a real coturn TURN server connects end-to-end (felt) | Human | UAT step U-3 (see 03-VERIFICATION / docs/DEPLOY.md) | pre-verify | gate |

Coverage: REQ-11→EC-12; REQ-12→EC-13; REQ-13→EC-14; REQ-14→EC-15; REQ-15→EC-16; REQ-16→EC-17
(warn Code smoke) + EC-18 (Human UAT). Every REQ-11..16 maps to ≥1 row; no orphan rows. Bijection
holds → lockable.

## Judge Rubrics
None — no subjective-quality rows this phase. Every deterministic claim is Code; the real-infra
claim is Human (EC-18), not Judge.

## Human / UAT rows (measurement: Human)
Carried into `03-VERIFICATION.md` for UAT. Cannot run in this environment (no public TLS domain,
no coturn server).

### U-3 — forced-relay call through real TURN behind TLS (EC-18, REQ-16)
- Steps: deploy the server behind TLS (real cert) per `docs/DEPLOY.md`; stand up a coturn server
  with `static-auth-secret` == `TURN_SECRET` and point `TURN_URL` at it. Open the HTTPS site in
  two browsers on networks that need relay (or force relay-only ICE). Join the same room.
- PASS: both sides see/hear each other over a `wss://` signaling channel and the media path is
  established via the TURN relay (verifiable in `chrome://webrtc-internals` as `relay`
  candidate-pair); `/ice-servers` returned a fresh `turn:` entry with time-limited creds.
- FAIL: no TURN entry returned, credentials rejected by coturn, or relay never connects.
