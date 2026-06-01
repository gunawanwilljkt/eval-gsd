# Architecture — how Talk works

A 1:1 WebRTC call has two jobs: (1) the two browsers must **find each other and exchange a
tiny bit of setup info** (that's *signaling*, and it needs a server), and (2) once connected,
**audio/video flows directly browser-to-browser** (that's the *media*, and the server is not
involved). Talk keeps these cleanly separated.

```
        ┌─────────────┐         WebSocket /ws          ┌─────────────┐
        │  Browser A  │◄──────── signaling ───────────►│  Browser B  │
        │ (caller)    │      (via the server)          │ (callee)    │
        └─────┬───────┘                                └──────┬──────┘
              │                                               │
              │            ░░░ media flows PEER-TO-PEER ░░░   │
              └───────────────── audio/video ─────────────────┘
                        (server never sees this)

                          ┌──────────────────┐
                          │  signaling server │  HTTP: serves the page + /healthz
                          │  (server.js)      │  WS  : relays join / offer / answer / ICE
                          └──────────────────┘
```

---

## 1. The signaling server (`server/server.js`)

A tiny Node server using only `http` (built-in) + `ws`. Two surfaces:

- **HTTP** — serves `public/` (the web client) and `GET /healthz → 200 "ok"`.
- **WebSocket** (`/ws`) — the signaling protocol. The server keeps one in-memory map:
  `room id → [peerSocket, peerSocket]` (max 2). It **never parses SDP or media** — `signal`
  payloads are opaque; it just forwards them to the other peer.

### Signaling protocol (JSON frames)

| Direction | Message | Meaning |
|-----------|---------|---------|
| C→S | `{type:"join", room}` | join a room |
| S→C | `{type:"joined", room, role, peers}` | accepted; `role` = `"callee"` (1st) or `"caller"` (2nd) |
| S→C | `{type:"room-full", room}` | rejected — room already has 2 (not admitted) |
| S→C | `{type:"peer-ready"}` | the 2nd peer joined — start the handshake |
| C→S | `{type:"signal", payload}` | relay this opaque blob to the other peer |
| S→C | `{type:"signal", payload}` | a blob relayed *from* the other peer |
| S→C | `{type:"peer-left"}` | the other peer disconnected |

**Role decides who offers:** the *second* peer to join (`caller`) creates the SDP offer; the
first (`callee`) waits. This makes the handshake deterministic — no glare/both-offer races.

---

## 2. The WebRTC handshake (who says what, when)

```
 Browser A (caller, joins 2nd)        Server              Browser B (callee, joins 1st)
        │                                │                          │
        │                                │   join "room"            │
        │                                │◄─────────────────────────│
        │                                │   joined{role:callee}    │
        │                                │─────────────────────────►│
        │   join "room"                  │                          │
        │───────────────────────────────►│                          │
        │   joined{role:caller}          │                          │
        │◄───────────────────────────────│                          │
        │   peer-ready  (to BOTH)        │   peer-ready             │
        │◄───────────────────────────────│─────────────────────────►│
        │                                │                          │
   createOffer + setLocalDescription     │                          │
        │   signal{ offer }              │   signal{ offer }        │
        │───────────────────────────────►│─────────────────────────►│
        │                                │            setRemoteDescription(offer)
        │                                │            createAnswer + setLocalDescription
        │   signal{ answer }             │   signal{ answer }       │
        │◄───────────────────────────────│◄─────────────────────────│
   setRemoteDescription(answer)          │                          │
        │                                │                          │
        │  ◄── signal{ ICE candidate } ──┼── signal{ ICE } ──►  (both directions, repeatedly)
        │                                │                          │
        │░░░░░░░░░░  audio + video now flow directly A ↔ B  ░░░░░░░░░│
```

STUN (`stun:stun.l.google.com:19302`) is used during ICE so each browser discovers its
public address. If both peers are behind **symmetric NAT**, STUN isn't enough and a **TURN**
relay would be required (Phase 03, not built).

---

## 3. The client, split for testability (`public/`)

The most important design decision: the **handshake state machine is pure** — it lives in
`call-core.js` and has **no `document` / `window` / `navigator` / `RTCPeerConnection` /
`getUserMedia`**. Every browser capability is *injected*. That is what makes the negotiation
logic — normally trapped in the browser — **deterministically testable in plain Node**.

```
   public/index.html          the UI: room input, two <video> tiles, mute/camera/hangup
        │  loads
        ▼
   public/call.js   ── the DOM SHELL (impure, browser-only) ──────────────┐
        │  • navigator.mediaDevices.getUserMedia() → local MediaStream     │ injects real
        │  • new WebSocket('/ws')                  → send()                 │ dependencies
        │  • () => new RTCPeerConnection({iceServers})                      │ into…
        ▼                                                                   ▼
   public/call-core.js  ── the PURE state machine ──────────────────────────
        createCall({ send, createPeerConnection, onRemoteStream, onLocalState })
          → { startAsRole(role, localStream), handleSignal(msg), hangup() }
        + setTrackEnabled(stream, kind, enabled)   // mute mic / toggle camera
```

- `startAsRole(role, stream)` builds the peer connection, wires `onicecandidate → send(signal)`
  and `ontrack → onRemoteStream`, and publishes the local tracks. The caller does **not** offer
  yet — it waits for `peer-ready`.
- `handleSignal(msg)` is the single entry point for every server message: `peer-ready` →
  caller offers; `signal{offer}` → answer; `signal{answer}` → set remote; `signal{candidate}`
  → add ICE; `peer-left` → tear down the media path (keep local stream to renegotiate).
- `hangup()` closes the connection and stops the local tracks (releases camera/mic).

### Why this matters for evals
Because `call-core.js` only talks to injected interfaces, the test
(`server/test/eval-phase2.mjs`) hands it a **fake `RTCPeerConnection`** and a **capturing
`send`**, then drives two cores against each other and asserts the *exact* offer/answer/ICE
sequence — **no browser, no camera, fully deterministic**. The irreducibly visual part ("do
real pixels appear") stays a Human/UAT row. See
[`EVAL-FIRST-WALKTHROUGH.md`](EVAL-FIRST-WALKTHROUGH.md).

---

## 4. Data & trust boundaries
- The server sees: room names + opaque signaling blobs. It does **not** see or relay media.
- Media (audio/video) is peer-to-peer and DTLS-encrypted by WebRTC itself.
- No persistence, no accounts, no logging of payloads. Rooms are ephemeral in memory and freed
  when peers leave.
