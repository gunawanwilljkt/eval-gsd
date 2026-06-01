---
ledger_version: '1.0'
status: in-progress
generation: 1
forward_progress: 15
continuation_policy: warm-ledger
updated: 2026-06-01 06:55
position:
  phase: '03-hardening'
  plan: '03'
  task: 'T4'
sole_writer: orchestrator
---

# Work Ledger — read me first

## Next Action
**All three phases COMPLETE & VERIFIED (Code).** Phase 03 (production hardening) built eval-first:
EC-12..EC-16 green via `npm run eval3` (exit 0), EC-17 TLS smoke green (openssl present; skip-safe),
EC-18 Human; locked contract hash `52bedb40…a5dfc477` matches; no gaming (green commit `e57d86a`
is eval-file-clean — 5 files, no harness). `npm test` (P01+P02+P03 deterministic rows) exits 0 —
no regression (P01 7/7, P02 gates green, all three contract hashes unchanged). **Remaining = manual
UAT only:** Phase 02 EC-8/U-2 (local preview + remote conversation, two tabs at localhost:8080),
and Phase 03 EC-18/U-3 (a forced-relay call through a real coturn TURN server behind real public
TLS — needs infra that can't exist here; fully documented in `docs/DEPLOY.md §5`).

## Current Position
- Phase: 03-hardening · Plan: 03 · all tasks done — PHASE COMPLETE (Code gates green; EC-18 Human/UAT pending)
- Status: Phases 01, 02 & 03 verified (Code); Human rows P02 EC-8/U-2 + P03 EC-18/U-3 await UAT
- Active task marker: none · Last clean commit: e57d86a (code, EC-12..EC-16 green)

## Open Escalations
None.

## Health (loop-control at a glance)
- Phase 01: Tasks 5/5 done · 0 blocked
- Phase 02: Tasks 5/5 done · 0 blocked (Code gates green; 2 Human rows pending UAT, non-blocking for build)
- Phase 03: Tasks 4/4 done · 0 blocked (Code gates green; EC-18 Human row pending real-infra UAT, non-blocking)
- Last task outcomes (P03): [T0 red-first, T1 pass, T2 pass, T3 pass]
- Stuck watch: none

<!-- ===================== TIER 2: HISTORY ===================== -->

## Task Records

### T0 — eval harness (Wave 0)
- status: done — `test/eval-phase1.mjs` written; RED run confirmed (ERR_MODULE_NOT_FOUND) before server
- eval_rows: []
- evidence: { commit_sha: 8affe3f, note: "evals committed RED first (eval-first)" }

### T1 — HTTP serve + health
- status: done
- req_ids: [REQ-01]
- eval_rows: [EC-1, EC-2]
- evidence: { commit_sha: 34e0c84, passing_eval_ids: [EC-1, EC-2] }

### T2 — join / rooms / roles / capacity
- status: done
- req_ids: [REQ-02, REQ-07]
- eval_rows: [EC-3, EC-7]
- evidence: { commit_sha: 34e0c84, passing_eval_ids: [EC-3, EC-7] }

### T3 — pairing + relay
- status: done
- req_ids: [REQ-03, REQ-04, REQ-05]
- eval_rows: [EC-4, EC-5]
- evidence: { commit_sha: 34e0c84, passing_eval_ids: [EC-4, EC-5] }

### T4 — departure
- status: done
- req_ids: [REQ-06]
- eval_rows: [EC-6]
- evidence: { commit_sha: 34e0c84, passing_eval_ids: [EC-6] }

## Phase 02 Task Records (02-client)

### T0 — spec + LOCKED contract + eval harness (Wave 0)
- status: done — `02-SPEC.md`, `02-EVAL-CONTRACT.md` (locked, hash c0aa6452…c914668), `test/eval-phase2.mjs`; RED run confirmed (ERR_MODULE_NOT_FOUND: call-core.js) before client built
- eval_rows: []
- evidence: { commit_sha: b770d7a, note: "evals committed RED first (eval-first); public/package.json {type:module} added so the pure module imports in Node" }

### T1 — pure handshake state machine (call-core.js)
- status: done
- req_ids: [REQ-09]
- eval_rows: [EC-9]
- evidence: { commit_sha: dcf89ed, passing_eval_ids: [EC-9], note: "two cross-wired cores drive full offer/answer/ICE over fake pcs; both onRemoteStream fire; purity grep clean (no DOM globals)" }

### T2 — control logic (mute / camera / hangup)
- status: done
- req_ids: [REQ-10]
- eval_rows: [EC-11]
- evidence: { commit_sha: dcf89ed, passing_eval_ids: [EC-11], note: "setTrackEnabled + hangup (close pc + stop tracks) verified on fake tracks in Node" }

### T3 — DOM shell + UI (call.js, index.html, styles.css)
- status: done
- req_ids: [REQ-08, REQ-09, REQ-10]
- eval_rows: [EC-8, EC-10]
- evidence: { commit_sha: dcf89ed, passing_eval_ids: [EC-10 SKIP (warn, playwright absent)], note: "EC-8 Human/UAT (U-1) pending; live server serves /,/call.js,/call-core.js,/styles.css 200; id=app kept (EC-2 still green)" }

### T4 — verify + flush
- status: done
- eval_rows: []
- evidence: { commit_sha: fc4ca1a, note: "02-VERIFICATION.md written; coverage clean, weakening hash matches, gaming clean; Phase 01 eval still 7/7 (no regression)" }

## Phase 03 Task Records (03-hardening)

### T0 — spec + LOCKED contract + eval harness (Wave 0)
- status: done — `03-SPEC.md`, `03-EVAL-CONTRACT.md` (locked, hash 52bedb40…a5dfc477), `test/eval-phase3.mjs`; added REQ-11..REQ-16 to REQUIREMENTS.md; ROADMAP Phase 03 → in-progress; RED run confirmed (SyntaxError: no export named backoffDelay) before impl
- eval_rows: []
- evidence: { commit_sha: f2188bd, note: "evals committed RED first (eval-first); package.json gains eval3 + extends `test` to run EC-12..16 (--except EC-17). Coverage gate clean (REQ-11..16 each ≥1 row, no orphans)." }

### T1 — server hardening (/ice-servers + TURN creds + rate limit + TLS)
- status: done
- req_ids: [REQ-11, REQ-12, REQ-15, REQ-16]
- eval_rows: [EC-12, EC-13, EC-16, EC-17]
- evidence: { commit_sha: e57d86a, passing_eval_ids: [EC-12, EC-13, EC-16, EC-17], note: "pure makeTurnCredential (golden literal YxRVVa1+vr70jHjnKQ13MVipWvY=) + buildIceServers + makeRateLimiter exported; /ice-servers STUN-only vs +TURN; flooder closed code 4029, polite peer unaffected; https/wss when TLS_* set; createServer still returns httpServer (P01/P02 intact)" }

### T2 — client hardening (signalingUrl + backoff + /ice-servers fetch + reconnect)
- status: done
- req_ids: [REQ-13, REQ-14, REQ-11]
- eval_rows: [EC-14, EC-15]
- evidence: { commit_sha: e57d86a, passing_eval_ids: [EC-14, EC-15], note: "pure signalingUrl (wss/ws) + backoffDelay (capped exp + bounded jitter, rng injected) in DOM-free call-core.js; call.js fetches /ice-servers, derives scheme, reconnects drops with backoff. Purity grep clean." }

### T3 — deploy artifacts (Dockerfile + DEPLOY.md)
- status: done
- req_ids: [REQ-16, REQ-12]
- eval_rows: [EC-18]
- evidence: { commit_sha: e57d86a, passing_eval_ids: [EC-18 HUMAN (UAT, real coturn+TLS)], note: "Dockerfile (node:22-alpine, ws-only, CMD node server.js) + docs/DEPLOY.md (TLS two ways, coturn use-auth-secret matching TURN_SECRET, full env ref, forced-relay UAT U-3)" }

### T4 — verify + flush
- status: done
- eval_rows: []
- evidence: { commit_sha: pending-this-commit, note: "03-VERIFICATION.md written; coverage clean, weakening hash 52bedb40… matches, gaming clean (green e57d86a eval-file-clean); npm test exit 0 across P01+P02+P03; ROADMAP P03→done(Code); README status table updated" }

## Decision Log (append-only)
- 2026-06-01 01-signaling: eval contract locked (hash 4dce1263…); 7 deterministic Code gates; no Human rows.
- 2026-06-01 01-signaling: eval-first executed — harness RED before server (ERR_MODULE_NOT_FOUND) → server built → `npm run eval` GREEN 7/7. Two-commit anti-gaming: green commit 34e0c84 does not touch the eval file. Verified clean (01-VERIFICATION.md).
- 2026-06-01 02-client: eval contract locked (hash c0aa6452…c914668); 4 rows — EC-8 Human (local preview), EC-9 Code gate (handshake state machine), EC-10 Code warn (headless fake-media smoke, gate-skips if Playwright absent), EC-11 Code gate (control logic).
- 2026-06-01 02-client: central eval-first move — WebRTC handshake factored out of the DOM into PURE `public/call-core.js` (no document/navigator/window/RTCPeerConnection/getUserMedia), so negotiation is Code-gatable in Node with a fake pc + capturing transport. `public/package.json {type:module}` added so the module imports cleanly (clean ERR_MODULE_NOT_FOUND RED, not a SyntaxError).
- 2026-06-01 02-client: eval-first executed — harness RED before core (ERR_MODULE_NOT_FOUND: call-core.js) → client built → `npm run eval2` GREEN (EC-9+EC-11, exit 0; EC-10 skip; EC-8 human). Two-commit anti-gaming: green commit dcf89ed does not touch test/eval-phase2.mjs. Verified clean (02-VERIFICATION.md). EC-8 + U-2 await manual UAT.
- 2026-06-01 02-client: EC-10 promoted SKIP→GREEN — Playwright+Chromium installed; headless two-peer fake-media smoke passes (remote videoWidth>0). Screenshots captured (docs/screenshots/peerA.png,peerB.png; both 640x480 live, status "In call."). Contract unchanged (hash still c0aa6452…), no weakening; `npm run capture` reproduces.
- 2026-06-01 02-client: wired EC-10 into npm `pretest` — `npm test` now runs pretest (EC-10 browser smoke; skips gracefully if Playwright absent) → test (EC-1..7 + EC-8/9/11, EC-10 excluded via new `--except` flag to avoid double-run). `npm test` exit 0, all gates green. CI-ready single command.
- 2026-06-01 03-hardening: added REQ-11..REQ-16 (ice-servers, ephemeral coturn TURN creds, scheme-correct wss URL, reconnect backoff, per-connection rate limit, TLS/wss); ROADMAP Phase 03 → in-progress. Eval contract locked (hash 52bedb40…a5dfc477); 7 rows — EC-12..EC-16 Code gates, EC-17 warn TLS smoke (openssl skip), EC-18 Human UAT. Coverage clean (REQ-11..16 each ≥1 row, no orphans).
- 2026-06-01 03-hardening: measurement split — deterministic logic factored into PURE functions: `makeTurnCredential`+`makeRateLimiter`+`buildIceServers` exported from server.js; `signalingUrl`+`backoffDelay` exported from DOM-free call-core.js (rng injected → deterministic). EC-13 asserts a FROZEN golden credential literal (not a re-HMAC) so a real coturn sharing the secret will accept what the server mints. EC-16 drives a real server (flooder closed code 4029, polite peer unaffected). Rate limiter is timestamp-windowed (no timer) so the harness still exits cleanly.
- 2026-06-01 03-hardening: eval-first executed — harness RED before impl (SyntaxError: no export named backoffDelay) → server+client built → `npm run eval3` GREEN (EC-12..16 + EC-17 TLS smoke, exit 0; EC-18 human). Two-commit anti-gaming: green commit e57d86a (5 files) does not touch test/eval-phase3.mjs. No regression: `npm test` exit 0 across P01+P02+P03, all three contract hashes match. Verified clean (03-VERIFICATION.md). EC-18/U-3 (real coturn+TLS forced-relay) await real-infra UAT — documented in docs/DEPLOY.md.
- 2026-06-01 MILESTONE: Talk v1 complete (Code) — all 3 phases (01 signaling, 02 client, 03 hardening) built eval-first; 16/18 eval rows green (EC-1..7,9,10,11,12..17), 2 Human rows pending UAT (EC-8 real call, EC-18 real TLS+TURN deploy). `npm test` exit 0; all 3 contract hashes match; anti-gaming clean. Full account: docs/MILESTONE-SUMMARY.md.
