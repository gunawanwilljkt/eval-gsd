# ROADMAP — Talk

Phases are vertical and eval-gated. A phase is **done** only when its locked eval contract's
`gate` rows are green (Code) and its Human rows pass UAT.

## Phase 01 — Signaling server  ·  REQ-01..07  ·  status: in-progress
The deterministic core. A Node `http`+`ws` server that pairs two peers per room and relays
their handshake. **Entirely Code-eval-gatable** headlessly (no browser): boot, serve, join,
peer-ready, relay, peer-left, room-full.
- Success: EC-1..EC-7 green via `npm run eval` (the live hard gate).

## Phase 02 — Web client + media  ·  REQ-08..10  ·  status: planned
The browser client: `getUserMedia`, `RTCPeerConnection`, local+remote video, controls. The
signaling/handshake **state logic is factored out of the DOM** so it is Code-eval-gatable in
Node (EC-9). The visual media path is a Human UAT row (EC-8/09/11) plus an optional headless
fake-media smoke (EC-10, Playwright `--use-fake-device-for-media-stream`).
- Success: EC-8..EC-9 green (Code) + EC-10 smoke (if Playwright present) + UAT pass.

## Phase 03 — Production hardening  ·  REQ-11..16  ·  status: done (Code)  ·  EC-18 Human/UAT pending
TURN relay (coturn) for symmetric NAT, TLS/`wss`, deploy, reconnection/backoff, basic abuse
limits. Same eval-first discipline as Phases 01/02: the credential/scheme/backoff logic is
factored into **pure** functions (Code-gatable in Node), the rate limit + `/ice-servers` are
driven against a **real** server, and the irreducible "real infra" check (a forced-relay call
through a real TURN server behind real TLS) is a documented **Human** UAT row.
- Success: EC-12..EC-16 green via `npm run eval3` (Code gates) + EC-17 TLS smoke (skips if
  openssl absent, warn) + EC-18 UAT (real deploy + TURN, documented in `docs/DEPLOY.md`).

## Why this ordering
Phase 01 is pure deterministic signaling → it produces the strongest *live* eval-gate
demonstration (real red→green, no browser). Phase 02 builds the experience on top, where the
measurement split (Code logic vs Human feel) is exercised honestly.
