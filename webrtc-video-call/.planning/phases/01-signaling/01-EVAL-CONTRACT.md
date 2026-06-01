---
eval_contract_version: '1.0'
phase: '01-signaling'
status: locked
locked_hash: '4dce12635d95414e250770e3497f78afd501d05f0644fda0a07aa0a1c9f11279'
locked_at: '2026-06-01'
coverage:
  requirements: [REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-06, REQ-07]
  rows_total: 7
  uncovered_reqs: []
  orphan_rows: []
---

# Phase 01 — Eval Contract (Signaling server)

Intent: "Two peers reliably find each other in a room and exchange a WebRTC handshake through
the server, which never sees their media." Every row below is a deterministic, runnable Code
gate — authored here BEFORE the server exists, so red→green on these rows IS the build.

Each row's command runs the harness for exactly that check and exits 0 (pass) / non-zero
(fail). Run from the `server/` directory. `npm run eval` runs them all.

## Rows

| id | objective_ref | req_ref | behavior | measurement | command_or_rubric | sample_rate | severity |
|----|---------------|---------|----------|-------------|-------------------|-------------|----------|
| EC-1 | talk | REQ-01 | server boots and GET /healthz returns 200 body "ok" | Code | node test/eval-phase1.mjs EC-1 | per-task | gate |
| EC-2 | talk | REQ-01 | GET / returns 200 and serves the web client (contains marker id="app") | Code | node test/eval-phase1.mjs EC-2 | per-task | gate |
| EC-3 | talk | REQ-02 | a client that joins room r1 receives joined with role "callee" and peers=1 | Code | node test/eval-phase1.mjs EC-3 | per-task | gate |
| EC-4 | talk | REQ-03 | when a 2nd client joins r1, BOTH receive peer-ready and the 2nd's role is "caller" | Code | node test/eval-phase1.mjs EC-4 | per-task | gate |
| EC-5 | talk | REQ-04, REQ-05 | a signal (SDP or ICE) from peer A is delivered to peer B only and never echoed back to A | Code | node test/eval-phase1.mjs EC-5 | per-task | gate |
| EC-6 | talk | REQ-06 | when peer A disconnects, peer B receives peer-left | Code | node test/eval-phase1.mjs EC-6 | per-task | gate |
| EC-7 | talk | REQ-07 | a 3rd client joining a full room receives room-full and gets no room traffic | Code | node test/eval-phase1.mjs EC-7 | per-task | gate |

Note: REQ-05 (ICE relay) shares EC-5 with REQ-04 — the relay path is payload-opaque, so one
relay eval proves both offer/answer and ICE forwarding. Coverage gate: every REQ-01..07 maps
to ≥1 row; no orphan rows. Bijection holds → lockable.

## Human / UAT rows
None this phase — signaling is fully deterministic. (The felt experience is gated in Phase 02.)
