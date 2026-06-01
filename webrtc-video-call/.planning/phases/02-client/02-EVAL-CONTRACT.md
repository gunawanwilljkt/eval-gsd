---
eval_contract_version: '1.0'
phase: '02-client'
status: locked
locked_hash: 'c0aa64526854913ffe44cb459ea9173f6b3bb0ea5c63c7e20bded9112c914668'
locked_at: '2026-06-01'
coverage:
  requirements: [REQ-08, REQ-09, REQ-10]
  rows_total: 4
  uncovered_reqs: []
  orphan_rows: []
---

# Phase 02 — Eval Contract (Web client + media)

Intent: "Two strangers open the same room link and have a working face-to-face conversation in
seconds." The handshake/control *logic* is factored out of the DOM into `public/call-core.js`
(no `document`/`navigator`/`window`/`RTCPeerConnection`) so it is deterministically Code-gatable
in Node with a FAKE peer connection + a capturing transport — no browser. The irreducibly
visual part (real pixels) is a Human/UAT row plus an optional headless fake-media smoke.

Each row's command runs the Phase-02 harness for exactly that check and exits 0 (pass) /
non-zero (fail). Run from the `server/` directory. `npm run eval2` runs them all.

## Rows

| id | objective_ref | req_ref | behavior | measurement | command_or_rubric | sample_rate | severity |
|----|---------------|---------|----------|-------------|-------------------|-------------|----------|
| EC-8 | talk | REQ-08 | local camera + mic captured and the local video preview renders (felt) | Human | UAT step U-1 (see 02-VERIFICATION): join a room → own face appears in the local tile | pre-verify | gate |
| EC-9 | talk | REQ-09 | two cross-wired call-core instances (caller+callee) over fake peer connections drive a full offer→answer→ICE handshake and BOTH receive the remote stream (onRemoteStream fires on each) | Code | node test/eval-phase2.mjs EC-9 | per-task | gate |
| EC-10 | talk | REQ-09 | headless smoke — two Chromium contexts with --use-fake-device-for-media-stream join one room and the remote video reaches videoWidth>0; gate-skips (exit 0) if Playwright/Chromium absent | Code | node test/eval-phase2.mjs EC-10 | pre-verify | warn |
| EC-11 | talk | REQ-10 | control logic — mute toggles audio track.enabled, camera toggles video track.enabled, hang up closes the pc and stops every local track (verified on fake tracks in Node) | Code | node test/eval-phase2.mjs EC-11 | per-task | gate |

Coverage: REQ-08→EC-8; REQ-09→EC-9 (gate) + EC-10 (warn smoke); REQ-10→EC-11. Every REQ maps to
≥1 row; no orphan rows. Bijection holds → lockable.

## Judge Rubrics
None — no subjective-quality rows this phase. Logic is deterministic Code; the felt experience
is Human (EC-8), not Judge.

## Human / UAT rows (measurement: Human)
Carried into `02-VERIFICATION.md` for UAT.

### U-1 — local preview renders (EC-8, REQ-08)
- Steps: `cd server && npm start`; open `http://localhost:8080`, allow camera/mic, type a room
  name, click Join.
- PASS: your own camera image appears in the local video tile within a couple of seconds.
- FAIL: black/empty local tile, or a permission/JS error prevents preview.

### U-2 — remote conversation + controls (EC-9/EC-11 felt counterpart, REQ-09/REQ-10)
- Steps: open a SECOND tab/browser to the same URL, join the SAME room. Both tiles should show
  live video. Test mute mic, toggle camera, hang up.
- PASS: each side sees and hears the other; mute silences your mic to the peer; toggle camera
  blanks your video to the peer; hang up ends the call and stops your camera light.
- FAIL: remote tile stays black, or a control has no effect.
