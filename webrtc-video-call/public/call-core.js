// call-core.js — the PURE WebRTC handshake state machine.
//
// EVAL-FIRST CRUX: this module has NO document / navigator / window / RTCPeerConnection /
// getUserMedia references. All browser capability is INJECTED, so the whole negotiation logic
// is deterministically testable in Node with a fake peer connection + a capturing transport
// (see server/test/eval-phase2.mjs). The DOM shell (call.js) wires the real dependencies in.
//
// Contract (02-SPEC.md):
//   createCall({ send, createPeerConnection, onRemoteStream, onLocalState })
//     -> { handleSignal(msg), startAsRole(role, localStream), hangup() }
//
// Signal discriminator matches what a real RTCPeerConnection emits:
//   SDP    -> payload.type === 'offer' | 'answer'  (plus payload.sdp)
//   ICE    -> payload.candidate present
// The core never parses SDP text; it only branches on these standard shapes.

export const STUN_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }];

export function createCall({ send, createPeerConnection, onRemoteStream, onLocalState }) {
  const emitState = (s) => { if (typeof onLocalState === 'function') onLocalState(s); };

  let pc = null;          // the active peer connection (from createPeerConnection)
  let role = null;        // 'caller' | 'callee'
  let localStream = null; // the local MediaStream whose tracks we publish
  let state = 'idle';

  function setState(s) { state = s; emitState(s); }

  // Attach the pc's outbound-ICE and inbound-track handlers (browser + fake both supported).
  function wirePeerConnection(connection) {
    const onIce = (event) => {
      // Real browsers fire icecandidate with a null candidate at end-of-gathering; skip those.
      const candidate = event && event.candidate;
      if (candidate) send({ type: 'signal', payload: candidate });
    };
    const onTrack = (event) => {
      const stream = event && event.streams && event.streams[0];
      if (stream && typeof onRemoteStream === 'function') onRemoteStream(stream);
    };
    // Use the on* property ONLY. On a real RTCPeerConnection the IDL attribute and an
    // addEventListener listener are SEPARATE registrations that both fire — registering both
    // would send each ICE candidate twice and surface each remote track twice. The real pc and
    // our fake both expose these properties, so property-only assignment is universally correct.
    connection.onicecandidate = onIce;
    connection.ontrack = onTrack;
  }

  // Build the pc and publish local tracks. Called once a role is assigned and media is ready.
  async function startAsRole(assignedRole, stream) {
    role = assignedRole;
    localStream = stream;
    pc = createPeerConnection();
    wirePeerConnection(pc);
    if (stream && typeof stream.getTracks === 'function') {
      for (const track of stream.getTracks()) pc.addTrack(track, stream);
    }
    // The caller does NOT offer yet — it waits for `peer-ready` (the 2nd peer has joined).
    setState('connecting');
  }

  async function makeOffer() {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    send({ type: 'signal', payload: offer });
  }

  async function makeAnswer(offer) {
    await pc.setRemoteDescription(offer);
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    send({ type: 'signal', payload: answer });
  }

  // The single entry point for every server->client message after `joined`.
  async function handleSignal(msg) {
    if (!msg || !msg.type) return;

    if (msg.type === 'peer-ready') {
      // The 2nd peer has joined; the caller initiates the SDP offer. The callee waits.
      if (role === 'caller' && pc) await makeOffer();
      return;
    }

    if (msg.type === 'peer-left') {
      // The other peer dropped: tear down the media path but keep our local stream so we can
      // renegotiate if a new 2nd peer joins.
      if (pc) { try { pc.close(); } catch {} pc = null; }
      setState('idle');
      return;
    }

    if (msg.type === 'signal') {
      const p = msg.payload;
      if (!p || !pc) return;
      if (p.type === 'offer') { await makeAnswer(p); return; }
      if (p.type === 'answer') { await pc.setRemoteDescription(p); return; }
      if (p.candidate) { try { await pc.addIceCandidate(p); } catch {} return; }
      return;
    }
  }

  // End the call: close the pc and stop every local track (releases camera/mic).
  function hangup() {
    if (pc) { try { pc.close(); } catch {} pc = null; }
    if (localStream && typeof localStream.getTracks === 'function') {
      for (const track of localStream.getTracks()) { try { track.stop(); } catch {} }
    }
    setState('ended');
  }

  return { handleSignal, startAsRole, hangup };
}

// ---- Pure control helpers (REQ-10), testable on fake tracks in Node ----

// Set `enabled` on every track of the given `kind` ('audio' | 'video') in a MediaStream.
// Returns the new enabled value. Mute mic = setTrackEnabled(local, 'audio', false);
// toggle camera = flip 'video'.
export function setTrackEnabled(stream, kind, enabled) {
  if (!stream || typeof stream.getTracks !== 'function') return enabled;
  for (const track of stream.getTracks()) {
    if (track.kind === kind) track.enabled = enabled;
  }
  return enabled;
}

// ---- Phase 03 pure helpers (REQ-13, REQ-14) — still DOM-free ----

// Derive the signaling WebSocket URL from a location-shaped object (REQ-13). Uses `wss://` when
// the page is HTTPS and `ws://` when HTTP — NOT hardcoded. Reads only `protocol`/`host` so it
// stays pure (no `window`); the DOM shell calls signalingUrl(window.location).
export function signalingUrl(location) {
  const proto = location && location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/ws`;
}

// Capped exponential backoff with bounded jitter (REQ-14), deterministic via injected rng.
//   raw   = min(cap, base * factor ** attempt)
//   delay = raw * (1 - jitter * rng())   in  [raw*(1-jitter), raw],  always <= cap
// `attempt` is 0-based. rng() returns a value in [0,1). With rng()=0 -> delay == raw (the upper
// bound of the window); as rng()->1 -> delay -> raw*(1-jitter). Jitter only ever REDUCES the
// delay, so it never exceeds the cap and never goes negative.
export function backoffDelay(attempt, opts = {}) {
  const { base = 500, factor = 2, cap = 15000, jitter = 0.5, rng = Math.random } = opts;
  const raw = Math.min(cap, base * factor ** attempt);
  return raw * (1 - jitter * rng());
}
