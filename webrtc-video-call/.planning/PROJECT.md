---
gsd_project_version: '1.0'
name: "Talk — minimal 1:1 WebRTC video call"
status: in-progress
---

# PROJECT — Talk

## Core value (the ONE thing)
Two people open the **same room link** and instantly see and hear each other — **no install,
no account, no plugins**. A browser tab is the whole product.

## What it is
A minimal but real 1:1 WebRTC video call:
- a **signaling server** (Node `http` + `ws`) that pairs two peers in a room and relays their
  WebRTC handshake (SDP offer/answer + ICE candidates),
- a **web client** (vanilla JS) that captures camera/mic, negotiates a peer connection, and
  shows local + remote video with mute / camera / hang-up controls.

Media flows **peer-to-peer** (the server never sees video). STUN (Google public) handles most
NATs; TURN relay is an explicit out-of-scope item (see Constraints).

## Why these constraints (they shape the eval contracts)
- **1:1 per room** (exactly 2 peers). A 3rd is rejected. Keeps signaling state trivial and
  deterministically testable.
- **Server is signaling-only.** It relays opaque messages; it never touches media. This is
  what makes the whole signaling layer **deterministically eval-gatable** without a browser.
- **Vanilla JS client, no build step.** The page is served as-is; the signaling/state logic is
  factored to be unit-testable in Node (no DOM) so most of the client is gated by Code evals
  too. The irreducibly visual part (does video actually render) is a Human/UAT eval + an
  optional headless fake-media smoke.

## Out of scope (v1) — honest boundaries
- **TURN relay** (symmetric-NAT traversal) — documented limitation; STUN-only.
- Group calls (>2), recording, chat, auth, persistence, mobile-native.

## Why this is a good spine test
The work splits cleanly along the eval-first **measurement split**: ~80% is deterministic
**Code** evals (signaling correctness, client logic, structure), the rest is **Human** UAT
(the felt video experience). That is exactly the contract the framework prescribes — so this
app exercises the live eval gate end-to-end, which is what we set out to prove.
