# 01-SPEC — Signaling server

WHAT phase 01 delivers, precisely enough that the eval contract can be written against it
before any code exists.

## Surfaces
- **HTTP** (`http` built-in): serves `/` → `public/index.html`, static assets under `/`, and
  `GET /healthz` → `200` with body `ok`.
- **WebSocket** (`ws`): one endpoint (same host/port, path `/ws`). Carries the signaling
  protocol below. JSON text frames.

## Signaling protocol (JSON over WebSocket)

**Client → Server**
| type | fields | meaning |
|------|--------|---------|
| `join` | `room` (string) | request to join a room |
| `signal` | `payload` (opaque object) | relay this to the other peer in my room (SDP offer/answer or ICE candidate) |

**Server → Client**
| type | fields | meaning |
|------|--------|---------|
| `joined` | `room`, `role` (`"callee"` \| `"caller"`), `peers` (int) | join accepted; `role` decides who makes the WebRTC offer |
| `room-full` | `room` | join rejected — room already has 2 peers; socket is NOT admitted |
| `peer-ready` | — | the 2nd peer has joined; both should start the handshake |
| `signal` | `payload` | a `signal` relayed from the OTHER peer (never echoed to sender) |
| `peer-left` | — | the other peer disconnected; reset and wait |

## Rules (the behaviors evals will check)
1. **Roles.** First peer to join a room → `role: "callee"` (waits). Second → `role: "caller"`
   (creates the SDP offer on `peer-ready`). Deterministic by join order.
2. **Pairing.** When the room reaches 2 peers, the server sends `peer-ready` to **both**.
3. **Relay.** A `signal` from peer A is delivered to peer B **only** (not echoed to A). Payload
   is opaque — the server never parses SDP/ICE.
4. **Capacity.** A 3rd `join` for a full room → `room-full`, and that socket is not added to the
   room (it receives no further room traffic).
5. **Departure.** On any peer's disconnect, the remaining peer (if any) gets `peer-left`, and the
   room frees the slot (a new 2nd peer may then join).
6. **Isolation.** Rooms are independent; a signal in room X never reaches room Y.

## Non-goals (this phase)
No media, no browser code (that is Phase 02), no TURN, no auth. The server is pure signaling so
it is fully deterministic and headlessly eval-gatable.
