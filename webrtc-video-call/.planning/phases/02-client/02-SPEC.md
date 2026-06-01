# 02-SPEC — Web client + media

WHAT phase 02 delivers, precisely enough that the eval contract can be written against it
before any client code exists. Builds on the Phase 01 signaling protocol (01-SPEC.md): the
client is the peer that *speaks* that protocol and runs the WebRTC handshake on top of it.

## Surfaces (browser)
- **`public/index.html`** — the whole UI. Keeps `id="app"` (so EC-2 still passes). Contains a
  room input + Join button, a local `<video>` (muted, autoplay, playsinline), a remote
  `<video>` (autoplay, playsinline), and a controls bar: **mute mic**, **toggle camera**,
  **hang up**.
- **`public/styles.css`** — layout for the two video tiles + controls.
- **`public/call.js`** — the DOM/browser shell (ES module). Owns `getUserMedia`, a *real*
  `RTCPeerConnection`, the `<video>` elements, and the `WebSocket` to `/ws`. Wires those as
  injected dependencies into `call-core.js`. This is the only client file allowed to touch
  `document` / `navigator` / `window` / `RTCPeerConnection`.
- **`public/call-core.js`** — the **pure** handshake state machine. NO `document` /
  `navigator` / `window` / `RTCPeerConnection` / `getUserMedia` references. Pure logic with
  injected dependencies → deterministically Code-gatable in Node with a fake peer connection
  and a capturing transport (no browser). This factoring is the eval-first crux.

## `call-core.js` contract (the pure module)

```
createCall({ send, createPeerConnection, onRemoteStream, onLocalState })
  → { handleSignal(msg), startAsRole(role, localStream), hangup() }
```

Injected dependencies:
- `send(msg)` — transport. Called with `{ type:'signal', payload:<sdp|ice> }` frames to relay
  to the other peer via the signaling server. (The DOM shell wires this to `ws.send(JSON…)`.)
- `createPeerConnection()` — factory returning a peer-connection-shaped object. In the browser
  this returns a real `new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]})`.
  In Node tests it returns a fake with the same surface (see below).
- `onRemoteStream(stream)` — called once the remote media stream is available (from the pc's
  `track`/`addstream` event). The DOM shell sets `remoteVideo.srcObject = stream`.
- `onLocalState(state)` — optional status callback (`'idle' | 'connecting' | 'in-call' |
  'ended'`) for the UI to reflect call state.

Returned methods:
- `startAsRole(role, localStream)` — called after `getUserMedia` resolves and the server has
  assigned a role. Creates the pc via `createPeerConnection()`, adds each local track to it,
  wires the pc's `onicecandidate` (→ `send({type:'signal',payload:candidate})`) and remote
  track handler (→ `onRemoteStream`). If `role === 'caller'`, it does NOT offer yet — it waits
  for `peer-ready`. (Role is provided so the core knows whether it will be the offerer.)
- `handleSignal(msg)` — the single entry point for every server→client message *after* join:
  - `peer-ready` → if this peer is the `caller`, create an SDP **offer**, `setLocalDescription`,
    and `send({type:'signal', payload:<offer>})`. The `callee` does nothing (waits for offer).
  - `signal` with `payload.type === 'offer'` → `setRemoteDescription(offer)`, create an
    **answer**, `setLocalDescription`, `send({type:'signal', payload:<answer>})`.
  - `signal` with `payload.type === 'answer'` → `setRemoteDescription(answer)`.
  - `signal` with `payload.candidate` (an ICE candidate) → `addIceCandidate(payload)`.
  - `peer-left` → close the pc and reset to a waiting state (ready to renegotiate if a new peer
    joins). Equivalent to a remote-initiated `hangup` of the media path (local stream kept).
- `hangup()` — close the peer connection and stop all local stream tracks; set state `'ended'`.

**Signal discriminator (must match real browsers).** A relayed `signal` payload is routed by
the standard fields a real `RTCPeerConnection` emits: an SDP has `payload.type` of `'offer'` or
`'answer'` (plus `payload.sdp`); an ICE candidate has `payload.candidate`. The core never
inspects SDP text — it only branches on these shapes.

## Fake peer-connection surface (what the Node test injects)
`createPeerConnection()` in tests returns an object exposing exactly what the core calls:
`addTrack(track, stream)`, `createOffer()`, `createAnswer()`, `setLocalDescription(desc)`,
`setRemoteDescription(desc)`, `addIceCandidate(c)`, `close()`, plus assignable event handlers
`onicecandidate` and `ontrack` (and/or `addEventListener('track'|'icecandidate', …)`). The fake
produces offer/answer objects of shape `{type:'offer'|'answer', sdp:'…'}` and ICE objects of
shape `{candidate:'…', sdpMid:'0', sdpMLineIndex:0}` — identical shapes to the browser, so the
core's discriminator is exercised exactly as in production.

## Controls (REQ-10) — factored to be testable on fake tracks in Node
The DOM shell exposes the felt controls; the *logic* is pure, exported from `call-core.js`:
- `setTrackEnabled(stream, kind, enabled)` — sets `enabled` on every `kind` (`'audio'|'video'`)
  track of `stream`; returns the new enabled value. Mute mic = `setTrackEnabled(local,'audio',
  false)`; toggle camera = flip `'video'`.
- Hang up = the core's `hangup()` (closes pc + stops every local track via `track.stop()`).

## Client behavior (the flow the DOM shell drives)
1. User types a room and clicks **Join**. The shell calls `getUserMedia({video,audio})`, shows
   the stream in the local `<video>` (REQ-08), opens the `WebSocket` to `/ws`, sends
   `{type:'join', room}`.
2. On `joined` → store `role`; call `startAsRole(role, localStream)`.
3. Every later server message is forwarded to `handleSignal(msg)` (peer-ready / signal /
   peer-left). The core drives offer/answer/ICE per the contract above.
4. On remote track → `onRemoteStream` → remote `<video>.srcObject = stream` (REQ-09).
5. Controls call the pure helpers / `hangup()`.

## STUN / out of scope
- ICE uses Google public STUN: `stun:stun.l.google.com:19302`. No TURN (Phase 03, roadmap-only)
  → symmetric-NAT peers may fail to connect; documented limitation.
- No reconnection/backoff, no auth, no group calls. Single 1:1 call per tab.

## Non-goals (this phase)
No server changes (Phase 01 is locked). No build step (served as-is). The irreducibly visual
part — "does real video actually render" — is a Human/UAT row (EC-8) plus an optional headless
fake-media smoke (EC-10); everything else (handshake logic, control logic) is deterministic
Code (EC-9, EC-11).
