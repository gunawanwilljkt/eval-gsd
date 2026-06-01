# Milestone Summary — Talk v1

A complete, honest account of what shipped: the features, the **full eval ledger** (every gate
and what it proves), requirements coverage, the eval-first evidence, and exactly what remains
for human acceptance. This is the onboarding/review doc — read it and you know the whole state.

---

## 1. What Talk is
A minimal **1:1 WebRTC video call**: two people open the same room link and see/hear each other,
no install/account. Media is peer-to-peer (the server never sees it); a small Node server only
relays the signaling handshake. Built end-to-end by **running the GSD eval-first spine** — every
phase specified, given a *locked eval contract*, and built test-first (red → green).

## 2. What shipped (3 phases, whole roadmap)

| Phase | Delivered | Code gates |
|-------|-----------|-----------|
| **01 — Signaling** | Node `http`+`ws` server: room pairing (1st=callee, 2nd=caller), `peer-ready`, opaque relay of offer/answer/ICE, `peer-left`, `room-full` capacity. Fully headless-testable. | EC-1..EC-7 ✅ |
| **02 — Client + media** | Browser client: `getUserMedia`, `RTCPeerConnection`, local+remote video, mute/camera/hangup. Handshake state machine factored into a **pure, DOM-free** `call-core.js` so the negotiation logic is Node-gatable. | EC-9, EC-11 ✅ (+EC-10 headless smoke ✅) |
| **03 — Hardening** | `GET /ice-servers`, **ephemeral coturn TURN credentials** (HMAC), `wss`/`ws` auto-select, reconnect backoff, per-connection rate limit, TLS server, `Dockerfile` + `DEPLOY.md`. | EC-12..EC-16 ✅ (+EC-17 TLS smoke ✅) |

## 3. The full eval ledger

18 rows. **Measurement split:** Code (deterministic, ~80%) · Code-warn (env-dependent smoke,
non-blocking) · Human (the felt experience a machine can't witness).

| Row | Req | What it proves | Measurement | Status |
|-----|-----|----------------|-------------|--------|
| EC-1 | REQ-01 | server boots + `/healthz` 200 "ok" | Code | ✅ green |
| EC-2 | REQ-01 | `GET /` serves the client (`id="app"`) | Code | ✅ green |
| EC-3 | REQ-02 | join → `joined{role:callee, peers:1}` | Code | ✅ green |
| EC-4 | REQ-03 | 2nd join → both `peer-ready`, 2nd is `caller` | Code | ✅ green |
| EC-5 | REQ-04,05 | `signal` A→B only, never echoed to A | Code | ✅ green |
| EC-6 | REQ-06 | A disconnects → B gets `peer-left` | Code | ✅ green |
| EC-7 | REQ-07 | 3rd join → `room-full`, not admitted | Code | ✅ green |
| EC-8 | REQ-08 | local camera preview renders | **Human** | ⏳ UAT (U-1) |
| EC-9 | REQ-09 | full offer/answer/ICE handshake state machine | Code | ✅ green |
| EC-10 | REQ-09 | headless two-peer fake-media: remote `videoWidth>0` | Code-warn | ✅ green (Playwright) |
| EC-11 | REQ-10 | mute / camera / hangup logic on fake tracks | Code | ✅ green |
| EC-12 | REQ-11 | `/ice-servers` STUN default; TURN when configured | Code | ✅ green |
| EC-13 | REQ-12 | ephemeral TURN credential = real coturn HMAC | Code | ✅ green |
| EC-14 | REQ-13 | `wss` on HTTPS, `ws` on HTTP (derived) | Code | ✅ green |
| EC-15 | REQ-14 | reconnect backoff: exponential + cap + jitter | Code | ✅ green |
| EC-16 | REQ-15 | flooding the socket → rate-limited / closed | Code | ✅ green |
| EC-17 | REQ-16 | self-signed TLS: `https` healthz 200 + `wss` handshake | Code-warn | ✅ green (openssl) |
| EC-18 | REQ-16 | real deploy behind TLS + forced-relay TURN call | **Human** | ⏳ UAT (U-3) |

**Tally:** 14 Code gates green · 2 Code-warn smokes green (EC-10, EC-17) · 2 Human rows pending.
`npm test` runs all deterministic gates in one command → **exit 0**.

## 4. Requirements coverage (intent ⇄ eval bijection)
All **REQ-01..REQ-16** map to ≥1 eval row, and every row maps to a real REQ (the coverage gate
that catches "intent with no eval"). REQ-05 shares EC-5 with REQ-04 (the relay path is
payload-opaque, so one eval proves both). No orphan rows; no uncovered requirements.

## 5. Eval-first evidence (why a green gate means something)
- **Red→green, every phase.** Each phase's harness was committed **red first** (e.g.
  `ERR_MODULE_NOT_FOUND` before the code), then the code turned it green. The git history shows
  the order: `spec+evals (RED)` → `feat (GREEN)` → `chore(ledger) flush`, ×3.
- **Locked contracts, verified.** Phase hashes — 01 `4dce1263…`, 02 `c0aa6452…`,
  03 `52bedb40…` — all **recompute-match** at verify time (no weakening).
- **Anti-gaming.** Each green commit (`34e0c84`, `dcf89ed`, `e57d86a`) was confirmed to **not
  touch its eval harness** (`git show <sha> --stat`) — the test wasn't bent to the output.
- **Independent re-verification.** The orchestrator re-ran every gate; the TURN credential was
  checked against an independent HMAC-SHA1/base64 computation (it's a real coturn credential,
  not an invented string).

## 6. What remains — human UAT only
The build is complete at the Code-gate level. The two open items are the felt/real-infra checks
no machine can witness here (full steps in `docs/RUN-AND-TEST.md §3` and `docs/DEPLOY.md`):
- **U-1 / EC-8 + U-2** — a real two-person call on real cameras (local preview + remote
  conversation + controls feel right).
- **U-3 / EC-18** — a real deployment behind TLS with a real coturn TURN server, and a
  forced-relay call across symmetric NAT.

## 7. Honest limitations (carried forward)
- Reconnect: only the pure `backoffDelay` schedule is gated; the reconnect **wiring** in
  `call.js` is exercised by hand, not a Code gate.
- Rate limit: the 20 msg/s ceiling is a per-deployment knob; headroom against a real
  high-candidate TURN ICE burst hasn't been witnessed (flagged in `03-VERIFICATION.md`).
- STUN-only unless TURN is configured; no auth/persistence/group calls (out of scope by design).

## 8. Metrics
- **Phases:** 3 (all built) · **Requirements:** 16 (all covered) · **Eval rows:** 18 (16 green, 2 human-pending).
- **Build commits:** 13, in the deliberate eval-first order (RED → GREEN → flush per phase).
- **Runtime deps:** 1 (`ws`); Playwright is dev-only for the smokes.
- **Sessions:** built across multiple fresh AI contexts, each resuming from `.planning/LEDGER.md`
  alone — the handoff worked at real-app scale (Phases 02 and 03 were built by sessions that
  started with no prior context).

## 9. Pointers
- Run it / test it: `README.md`, `docs/RUN-AND-TEST.md`
- How it works: `docs/ARCHITECTURE.md`
- Deploy (TLS + TURN): `docs/DEPLOY.md`
- How the spine produced it: `docs/EVAL-FIRST-WALKTHROUGH.md`
- The live state / task ledger: `.planning/LEDGER.md`
