# REQUIREMENTS — Talk

Functional requirements with stable IDs. Every requirement must be covered by ≥1 eval-contract
row (the **coverage gate** enforces this `REQ ⇄ eval` bijection — that is how we catch
spec-drift-from-intent). The `Eval` column is filled as contracts are authored per phase.

| ID | Requirement | Phase | Eval rows | Measurement |
|----|-------------|-------|-----------|-------------|
| REQ-01 | The server starts and serves the web client (HTML/JS/CSS) over HTTP + exposes a health endpoint. | 01 | EC-1, EC-2 | Code |
| REQ-02 | A client can join a named room over a WebSocket and receive an acknowledgement (with its assigned role: first peer vs second). | 01 | EC-3 | Code |
| REQ-03 | When the second client joins a room, **both** peers are notified to begin the WebRTC handshake (`peer-ready`). | 01 | EC-4 | Code |
| REQ-04 | The server relays an SDP **offer/answer** from one peer to the other peer in the same room (and not back to the sender). | 01 | EC-5 | Code |
| REQ-05 | The server relays **ICE candidates** between the two peers in a room. | 01 | EC-5 | Code |
| REQ-06 | When a peer disconnects, the remaining peer is notified (`peer-left`) so it can reset. | 01 | EC-6 | Code |
| REQ-07 | A room holds **at most 2** peers; a third join is rejected with `room-full` and not admitted. | 01 | EC-7 | Code |
| REQ-08 | The client captures local camera + microphone and displays the **local** video preview. | 02 | EC-8 | Code+Human |
| REQ-09 | The client negotiates an RTCPeerConnection via signaling and displays the **remote** peer's video/audio. | 02 | EC-9, EC-10 | Code+Human |
| REQ-10 | The client provides call controls: **mute mic**, **toggle camera**, **hang up**. | 02 | EC-11 | Code+Human |
| REQ-11 | The server exposes `GET /ice-servers` → JSON `{iceServers:[...]}`: STUN by default, plus a TURN entry when TURN is configured via env. | 03 | EC-12 | Code |
| REQ-12 | When a TURN secret is configured (`TURN_SECRET` + `TURN_URL`), the server issues **ephemeral, time-limited TURN credentials** using the coturn REST scheme: `username = "<expiryUnixTs>:<userid>"`, `credential = base64(HMAC-SHA1(secret, username))`. | 03 | EC-13 | Code |
| REQ-13 | The client connects over **`wss://` when the page is HTTPS** and `ws://` when HTTP (scheme derived, not hardcoded). | 03 | EC-14 | Code |
| REQ-14 | The signaling client **reconnects on drop with capped exponential backoff + jitter**. | 03 | EC-15 | Code |
| REQ-15 | The signaling server applies a **per-connection message rate limit** (flooding is throttled / the socket closed), so one client can't spam the relay. | 03 | EC-16 | Code |
| REQ-16 | The server can run over **TLS (`wss`)** when `TLS_CERT_FILE` / `TLS_KEY_FILE` env are provided. | 03 | EC-17, EC-18 | Code+Human |

## Intent (the thing evals must protect)
"Two strangers click the same link and have a working face-to-face conversation in seconds."
Passing evals must ladder up to *that* — e.g. REQ-09 green means a remote stream actually
renders, not merely that a function was called. The Human rows exist precisely where a Code
eval cannot witness "a conversation actually happened."
