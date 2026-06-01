# Talk — a minimal 1:1 WebRTC video call

Two people open the **same room link** and instantly see and hear each other — **no install,
no account, no plugins**. A browser tab is the whole product. Video flows **peer-to-peer**;
the server only helps the two browsers find each other.

> Built by **running the GSD eval-first spine** end-to-end. Every phase was specified, given a
> *locked eval contract*, and built **eval-first** (write the test → watch it fail → build →
> watch it pass). See [`docs/EVAL-FIRST-WALKTHROUGH.md`](docs/EVAL-FIRST-WALKTHROUGH.md).

---

## Quick start (about 2 minutes)

You need **Node ≥ 22** (for the built-in WebSocket client used by the tests) and a browser
with a camera + mic.

```bash
cd server
npm install           # installs 'ws' (the only runtime dependency)
npm start             # serves the app on http://localhost:8080
```

Then make a call:

1. Open **http://localhost:8080** in one tab. Allow camera + mic. Type a room name (e.g.
   `hello`) and click **Join** — you should see yourself in the **You** tile.
2. Open **http://localhost:8080/?room=hello** in a *second* tab (or another device on the same
   network, using your machine's LAN IP). Click **Join**.
3. Both tiles go live. Try **Mute mic**, **Camera off**, **Hang up**.

> Two tabs on one machine is the simplest test. For two *devices*, both must reach the server
> (same Wi-Fi, or deploy it) — and note the STUN-only limitation below.

---

## Run the evaluations (the quality gates)

The whole app is gated by **deterministic eval contracts** — no browser needed for the gates:

```bash
cd server
npm run eval          # Phase 01 — signaling server:  EC-1..EC-7   -> "GATE GREEN — 7/7 rows pass"
npm run eval2         # Phase 02 — client logic:       EC-9, EC-11  -> "GATE GREEN"  (EC-10 skips if no Playwright)
npm run eval3         # Phase 03 — hardening:          EC-12..EC-16 -> "GATE GREEN"  (EC-17 TLS smoke skips if no openssl)
npm test              # all phases' deterministic gates in one CI command -> exit 0
```

You can run a single contract row (a task's acceptance check):

```bash
node test/eval-phase1.mjs EC-5     # relay: a signal reaches the other peer, never echoes back
node test/eval-phase2.mjs EC-9     # the full offer/answer/ICE handshake state machine
```

What's *not* auto-tested (because it needs real pixels) is the felt video experience — that's
the **Human/UAT** rows, with exact steps in [`docs/RUN-AND-TEST.md`](docs/RUN-AND-TEST.md).

---

## What's in here

```
webrtc-video-call/
├── README.md                  ← you are here
├── Dockerfile                 containerizes the signaling server (TURN/TLS via env)
├── server/
│   ├── server.js              signaling server: HTTP static + /healthz + /ice-servers + WS /ws
│   │                          (+ ephemeral TURN creds, per-connection rate limit, TLS/wss)
│   ├── test/
│   │   ├── eval-phase1.mjs    Phase 01 gate (EC-1..EC-7), zero deps
│   │   ├── eval-phase2.mjs    Phase 02 gate (EC-9/EC-11 + EC-10 smoke)
│   │   └── eval-phase3.mjs    Phase 03 gate (EC-12..EC-16 + EC-17 TLS smoke)
│   └── package.json           scripts: start, eval, eval2, eval3, test
├── public/
│   ├── index.html             the call UI
│   ├── call-core.js           PURE logic: handshake state machine + signalingUrl + backoffDelay
│   ├── call.js                DOM shell: getUserMedia + RTCPeerConnection, /ice-servers, reconnect
│   └── styles.css
├── docs/
│   ├── ARCHITECTURE.md        how it works: signaling flow + WebRTC handshake + the pure-core design
│   ├── DEPLOY.md              run behind TLS + a coturn TURN server (env reference + UAT)
│   ├── RUN-AND-TEST.md        every command + the manual UAT script, step by step
│   └── EVAL-FIRST-WALKTHROUGH.md   how the GSD spine produced this app (the live red→green proof)
└── .planning/                 the GSD artifacts the spine produced (see the walkthrough)
    ├── PROJECT.md  REQUIREMENTS.md  ROADMAP.md  LEDGER.md
    └── phases/{01-signaling,02-client,03-hardening}/{SPEC, EVAL-CONTRACT, VERIFICATION}
```

---

## Status & honest limitations

| Phase | What | Status |
|-------|------|--------|
| 01 — Signaling | room pairing + handshake relay | ✅ built, **7/7 Code gates green** |
| 02 — Client + media | getUserMedia, peer connection, UI, controls | ✅ built, **Code gates green**; Human UAT pending your run |
| 03 — Production | **TURN** relay, TLS/`wss`, rate limit, reconnect, deploy | ✅ built, **EC-12..EC-16 Code gates green** (+EC-17 TLS smoke); EC-18 real-infra UAT pending |

- **TURN-ready:** `GET /ice-servers` serves STUN by default and **ephemeral coturn TURN
  credentials** when `TURN_URL`+`TURN_SECRET` are set — so symmetric-NAT peers can relay. See
  [`docs/DEPLOY.md`](docs/DEPLOY.md). (Without TURN configured it's STUN-only, which fails on
  symmetric NAT.)
- **TLS / `wss`:** set `TLS_CERT_FILE`+`TLS_KEY_FILE` to serve HTTPS + `wss` (or terminate TLS at
  a proxy). The client derives `wss`/`ws` from the page automatically.
- **Abuse limit:** the signaling server rate-limits each connection (20 msgs/sec); a flooder is
  disconnected (WS code 4029).
- **Reconnect:** the client reconnects dropped signaling sockets with capped exponential backoff.
- **1:1 only:** exactly two peers per room; a third is rejected (`room-full`).
- **No TLS in dev:** browsers allow camera/mic on `http://localhost`. On a real domain serve over
  **HTTPS** (and `wss`) — see the deploy guide.

---

## How this was built
This app is a live demonstration of an **eval-first, spec-driven** workflow: objective →
requirements → spec → **locked eval contract** → plan → eval-gated build → verify, with a
**work ledger** tracking it so any session can resume. Read
[`docs/EVAL-FIRST-WALKTHROUGH.md`](docs/EVAL-FIRST-WALKTHROUGH.md) to see the whole spine.
