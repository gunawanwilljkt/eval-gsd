# Run & Test — step by step

Everything you need to (1) run the app, (2) run the automated eval gates, and (3) do the
manual user-acceptance test (UAT) for the parts a machine can't witness.

---

## 0. Prerequisites
- **Node.js ≥ 22** — check with `node --version`. (The tests use Node's built-in `WebSocket`
  client, added in v22.)
- A browser with a **camera + microphone** (Chrome/Edge/Firefox/Safari).
- One-time: `cd server && npm install` (installs `ws`, the only runtime dependency).

---

## 1. Start the server

```bash
cd server
npm start
```

Expected output:

```
Talk signaling server on http://localhost:8080
```

Sanity check (in another terminal):

```bash
curl -i http://localhost:8080/healthz      # → HTTP/1.1 200 OK,  body: ok
```

Stop the server with **Ctrl-C** when done.

---

## 2. Run the automated eval gates

### `npm test` — the one command that runs everything

```bash
cd server
npm test
```
npm's lifecycle runs two stages automatically:
- **`pretest`** → the **EC-10** headless media smoke (two Chromium peers, fake camera, assert the
  remote video renders). If Playwright/Chromium isn't installed it **skips** (exit 0), so
  `npm test` works with or without browsers.
- **`test`** → the deterministic gates: Phase 01 (`EC-1..EC-7`) + Phase 02 (`EC-8/9/11`,
  excluding EC-10 since `pretest` already ran it).

Exit `0` only if every gate is green. This is the command to wire into CI or a pre-push hook.

---

The pieces individually (the **deterministic** gates start a real server on a throwaway port,
drive it with real WebSocket clients / a fake peer connection, and assert behavior — no browser
needed):

```bash
cd server

npm run eval     # Phase 01 — signaling server
```
Expected (actual harness output):
```
  PASS EC-1
  PASS EC-2
  PASS EC-3
  PASS EC-4
  PASS EC-5
  PASS EC-6
  PASS EC-7

GATE GREEN — 7/7 rows pass
```
What each row checks (from `01-EVAL-CONTRACT.md`): EC-1 server boots + `/healthz` 200 "ok" ·
EC-2 `GET /` serves the client (`id="app"`) · EC-3 join → `joined{role:callee, peers:1}` ·
EC-4 2nd join → both get `peer-ready`, 2nd is `caller` · EC-5 `signal` A→B only, never echoed ·
EC-6 A disconnects → B gets `peer-left` · EC-7 3rd join → `room-full`, not admitted.

```bash
npm run eval2    # Phase 02 — client handshake + control logic
```
Expected (actual harness output):
```
  HUMAN EC-8 — local preview renders: verified via UAT (02-VERIFICATION U-1)
  PASS EC-9
  SKIP EC-10 — playwright absent (warn row, non-blocking)
  PASS EC-11

GATE GREEN — gate rows pass (1 warn/skip, 1 human)
```
Rows: EC-9 = the full offer/answer/ICE handshake state machine (driven in Node with a fake peer
connection); EC-11 = mute / camera / hangup logic on fake tracks; EC-8 = local preview (Human,
see §3); EC-10 = optional headless Chromium fake-media smoke (skips unless Playwright installed).

### Run a single row (a task's acceptance check)
```bash
node test/eval-phase1.mjs EC-5      # just the relay/no-echo behavior
node test/eval-phase2.mjs EC-9      # just the handshake state machine
```
Each prints `PASS`/`FAIL` and exits `0`/non-zero — so it can gate a commit or CI step.

### (Optional) the headless media smoke, EC-10
`EC-10` drives **two real Chromium contexts** with fake camera input and asserts the remote
`<video>` actually reaches `videoWidth > 0`. It's a `warn` row that **skips** unless Playwright
is installed (so it never blocks). To run it for real:
```bash
cd server && npm i -D playwright && npx playwright install chromium
npm run eval2        # EC-10 now runs instead of skipping → "PASS EC-10 — remote video reached videoWidth>0"
```

To also save **screenshots** of a live two-peer call (visual evidence), run:
```bash
cd server && npm run capture       # writes docs/screenshots/peerA.png + peerB.png
```
Each screenshot shows both the local **You** tile and the remote **Peer** tile rendering the
fake camera feed (640×480, status "In call."). The two tiles' on-screen timestamps differ — proof
the remote tile is the *other* peer's stream, not a mirror of the local one.

---

## 3. Manual UAT — the human rows (EC-8, and U-2)

Some things only a person can confirm: *do I actually see myself, see the other person, and
does mute/camera/hangup feel right?* These are the contract's **Human** rows. Do this once:

1. **Start the server** (`cd server && npm start`).
2. **U-1 / EC-8 — local preview.** Open **http://localhost:8080**. The browser asks for camera
   + mic — **Allow**. Type a room name (e.g. `demo`) and click **Join**.
   - ✅ **Pass:** your own face appears in the **You** tile within a second or two.
3. **U-2 — the actual call.** Open a **second** tab at
   **http://localhost:8080/?room=demo** (same room name) and click **Join**.
   - ✅ **Pass:** within a few seconds **both tiles are live** — the *Peer* tile shows the other
     tab's camera, and (if your speakers/mic aren't muted) audio connects. Status shows connected.
4. **Controls (EC-11 felt behavior):**
   - **Mute mic** → the other tab stops hearing you (button toggles to *Unmute*).
   - **Camera off** → your video freezes/blanks for the other tab (toggles to *Camera on*).
   - **Hang up** → the call ends and the camera light turns off.

> **Two devices instead of two tabs:** start the server, find your machine's LAN IP
> (`ipconfig getifaddr en0` on macOS), and open `http://<that-ip>:8080/?room=demo` on the
> second device on the **same Wi-Fi**. See the NAT note below.

---

## 4. Troubleshooting

| Symptom | Cause / fix |
|--------|-------------|
| Browser never asks for camera | Camera/mic only work on `http://localhost` or **HTTPS**. A bare LAN IP over `http://` may be blocked — use localhost (two tabs), or put the app behind HTTPS. |
| "You" tile is black | Another app is using the camera, or permission was denied. Close other apps; re-allow in the site permissions. |
| Both tiles never connect across two *devices* | Likely **symmetric NAT** (common on corporate/cellular). STUN can't traverse it — you need a **TURN** server (Phase 03). On the same home Wi-Fi it usually works. |
| `npm run eval` fails to start | Check `node --version` ≥ 22; run `npm install` in `server/`. |
| Port 8080 in use | `PORT=9000 npm start`, then open `http://localhost:9000`. |

---

## 5. Extending it (add a requirement → add an eval)
The workflow is **eval-first**: never add behavior without first adding the row that proves it.
1. Add the requirement to `.planning/REQUIREMENTS.md` (new `REQ-NN`).
2. Add a row to the phase's `EVAL-CONTRACT.md` (`req_ref: REQ-NN`, a runnable command or a
   Human rubric), re-run the coverage gate, re-lock the hash (see the walkthrough §"locking").
3. Add the check to the harness (`eval-phase*.mjs`), watch it go **red**.
4. Implement until it goes **green**. Commit code separately from the eval file (anti-gaming).
5. Update `.planning/LEDGER.md`.

That is exactly how Phases 01 and 02 were built — see
[`EVAL-FIRST-WALKTHROUGH.md`](EVAL-FIRST-WALKTHROUGH.md).
