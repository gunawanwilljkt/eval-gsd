# 02-VERIFICATION — Web client + media

Verdict produced by the merged eval-verify (framework W5): coverage + weakening + gaming + gate rows.

## Verdict: ✅ PASS (Code gates green; Human rows EC-8 + U-2 pending UAT)

| Check | Result |
|-------|--------|
| **Gate rows (Code)** | EC-9 + EC-11 GREEN via `npm run eval2` (exit 0). Each also passes standalone (`node test/eval-phase2.mjs EC-9`, `… EC-11`). |
| **Warn row (Code)** | EC-10 headless smoke: **PASS** — `node test/eval-phase2.mjs EC-10` → "remote video reached videoWidth>0 across two fake-media contexts", exit 0 (Playwright+Chromium installed 2026-06-01). Visual evidence in `docs/screenshots/peerA.png` + `peerB.png` (both tiles 640×480 live, status "In call.", differing on-screen timestamps prove two independent streams). Reproduce: `npm run capture`. |
| **Human row** | EC-8 (local preview renders) — machine-reported as `HUMAN`, verified at UAT step U-1 below. |
| **Coverage gate (§3)** | REQ-08→EC-8; REQ-09→EC-9 (gate) + EC-10 (warn); REQ-10→EC-11. Every REQ maps to ≥1 row; no orphan rows. Bijection holds. |
| **Weakening detector (§4)** | `locked_hash` recompute (§2.1 command) = `c0aa6452…c914668` — matches the locked value. No row deleted/loosened. |
| **Gaming detector (§4)** | Green commit `dcf89ed` (`public/call-core.js` + `call.js` + `index.html` + `styles.css`) does **not** touch `server/test/eval-phase2.mjs`. Evals committed RED first (`b770d7a`), code second — `git show dcf89ed --stat` is eval-file-clean. |
| **Purity (eval-first crux)** | `grep -vE '^\s*//' public/call-core.js \| grep -nE '\b(document\|navigator\|window\|RTCPeerConnection\|getUserMedia)\b'` → zero hits in non-comment code. The handshake logic is pure → Node-gatable. |
| **No regression** | Phase 01 `npm run eval` still 7/7 GREEN (EC-2 reads the new index.html — `id="app"` preserved). Live server serves `/`, `/call.js`, `/call-core.js`, `/styles.css` (200, correct MIME). |

## Evidence
- **RED run (pre-core):** `node test/eval-phase2.mjs EC-9` → `ERR_MODULE_NOT_FOUND: call-core.js`, exit 1 — proves the gate discriminates (mirrors Phase 01).
- **GREEN run (post-core):** `npm run eval2` → `GATE GREEN — gate rows pass (1 warn/skip, 1 human)`, exit 0.
- **Intent ladder:** EC-9 instantiates TWO cross-wired `call-core` instances (caller+callee), drives a full offer→answer→ICE exchange over fake peer connections, and asserts **both** `onRemoteStream` callbacks fire — i.e. a remote stream is actually delivered to each side, not merely that a function was called. That ladders to REQ-09's intent. The irreducibly visual "real pixels render" is carried by EC-8/U-1 (Human) and the optional EC-10 smoke.

## Human / UAT — run before declaring the phase user-verified

### U-1 — local preview renders (EC-8, REQ-08)
```
cd server && npm start          # http://localhost:8080
```
Open `http://localhost:8080`, allow camera/mic, type a room name, click **Join**.
- PASS: your own camera image appears in the **You** tile within a couple of seconds.
- FAIL: black/empty local tile, or a permission/JS error blocks preview.

### U-2 — remote conversation + controls (EC-9/EC-11 felt counterpart, REQ-09/REQ-10)
Open a **second** tab/window (or use the share link `http://localhost:8080/?room=<name>`) and
**Join the SAME room**.
- PASS: both **You** and **Peer** tiles show live video; **Mute mic** silences your audio to the
  peer; **Camera off** blanks your video to the peer; **Hang up** ends the call and releases your
  camera (light off). A third joiner of the same room sees "Room is full".
- FAIL: remote tile stays black, or any control has no effect.

> Note on testing two peers on ONE machine: browsers gate `getUserMedia` to a single camera, but
> a second tab still gets a (possibly duplicated/blank) stream — the negotiation + remote tile
> still light up. For a fully independent second feed, use a second device or a fake-media flag
> (`chromium --use-fake-device-for-media-stream`), which is exactly what EC-10 automates.

## Conclusion
Phase 02 delivers REQ-08/09/10, gated by a locked contract, verified clean. Code gates (EC-9,
EC-11) green; **EC-10 now GREEN too** (Playwright installed → headless two-peer media path
renders, screenshots captured); EC-8 + U-2 (felt experience on real cameras) await human UAT.
Remaining work = manual UAT + Phase 03 (TURN/deploy, roadmap-only).
