// Eval harness for Phase 02 (web client + media). Implements the LOCKED 02-EVAL-CONTRACT rows.
//
//   node test/eval-phase2.mjs            -> run ALL rows (the phase gate; npm run eval2)
//   node test/eval-phase2.mjs EC-9       -> run one row (a task's acceptance_criteria)
//
// Exit 0 = all selected GATE rows PASS (warn rows never block). Non-zero = a gate is RED.
//
// THE EVAL-FIRST CRUX: the WebRTC handshake state machine lives in public/call-core.js as a
// PURE module (no document/navigator/window/RTCPeerConnection). So we test it here in Node with
// a FAKE peer connection + a capturing transport — no browser needed. EC-9 cross-wires TWO core
// instances (caller + callee) and drives a full offer→answer→ICE handshake, asserting BOTH
// receive the remote stream. EC-11 exercises the control logic on fake tracks. EC-8 is Human
// (UAT). EC-10 is an optional headless smoke that gate-skips when Playwright/Chromium is absent.

import { createCall, setTrackEnabled } from '../../public/call-core.js';

function assert(cond, msg) { if (!cond) throw new Error(msg); }
const deepEq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ---------------------------------------------------------------------------
// Fakes — same SURFACE & message SHAPES a real RTCPeerConnection produces, so
// call-core's SDP/ICE discriminator is exercised exactly as it is in a browser.
// ---------------------------------------------------------------------------

let trackSeq = 0;
function fakeTrack(kind) {
  return { kind, enabled: true, stopped: false, id: `${kind}-${++trackSeq}`,
           stop() { this.stopped = true; } };
}
function fakeStream(kinds = ['audio', 'video']) {
  const tracks = kinds.map(fakeTrack);
  return {
    _tracks: tracks,
    getTracks: () => tracks,
    getAudioTracks: () => tracks.filter((t) => t.kind === 'audio'),
    getVideoTracks: () => tracks.filter((t) => t.kind === 'video'),
  };
}

// A fake peer connection. Mirrors the methods/handlers call-core calls. Offer/answer and ICE
// objects have the EXACT shapes a real RTCPeerConnection emits.
function fakePeerConnection() {
  const pc = {
    closed: false,
    localDescription: null,
    remoteDescription: null,
    added: [],          // tracks added via addTrack
    ice: [],            // ice candidates received via addIceCandidate
    onicecandidate: null,
    ontrack: null,
    _listeners: {},
    addEventListener(ev, fn) { (this._listeners[ev] ||= []).push(fn); },
    _emit(ev, payload) {
      if (ev === 'icecandidate' && typeof this.onicecandidate === 'function') this.onicecandidate(payload);
      if (ev === 'track' && typeof this.ontrack === 'function') this.ontrack(payload);
      for (const fn of (this._listeners[ev] || [])) fn(payload);
    },
    addTrack(track, stream) { this.added.push({ track, stream }); },
    async createOffer() { return { type: 'offer', sdp: 'FAKE-SDP-OFFER' }; },
    async createAnswer() { return { type: 'answer', sdp: 'FAKE-SDP-ANSWER' }; },
    async setLocalDescription(desc) { this.localDescription = desc; },
    async setRemoteDescription(desc) { this.remoteDescription = desc; },
    async addIceCandidate(c) { this.ice.push(c); },
    close() { this.closed = true; },
  };
  return pc;
}

// Emit a remote-track event onto a pc the way a browser does (event carries .streams[]).
function emitRemoteTrack(pc, stream) {
  pc._emit('track', { streams: [stream], track: stream.getTracks()[0] });
}
// Emit a local ICE candidate the browser way (event carries .candidate, or null at end).
function emitLocalIce(pc, candidate) {
  pc._emit('icecandidate', { candidate });
}

// Build one wired core instance with capturing transport + fake pc.
function buildPeer({ onRemoteStream }) {
  const sent = [];                       // every frame the core asked to send
  let pc = null;
  const call = createCall({
    send: (msg) => sent.push(msg),
    createPeerConnection: () => { pc = fakePeerConnection(); return pc; },
    onRemoteStream,
    onLocalState: () => {},
  });
  return { call, sent, getPc: () => pc };
}

// ---------------------------------------------------------------------------
// EC-9 — full cross-wired handshake over fakes; BOTH peers get the remote stream.
// ---------------------------------------------------------------------------
async function EC9() {
  let calleeRemote = null, callerRemote = null;
  const callee = buildPeer({ onRemoteStream: (s) => { calleeRemote = s; } }); // role: callee
  const caller = buildPeer({ onRemoteStream: (s) => { callerRemote = s; } }); // role: caller

  const calleeStream = fakeStream();
  const callerStream = fakeStream();

  // Each peer starts with its assigned role + local stream (post-getUserMedia, post-joined).
  await callee.call.startAsRole('callee', calleeStream);
  await caller.call.startAsRole('caller', callerStream);

  // Local tracks must be added to each pc (so the remote will receive them).
  assert(callee.getPc().added.length === calleeStream.getTracks().length, 'callee did not add its local tracks');
  assert(caller.getPc().added.length === callerStream.getTracks().length, 'caller did not add its local tracks');

  // Cross-wire: a frame the core sends is delivered to the OTHER core as a relayed `signal`
  // (this is exactly what the Phase-01 server does — relay payload to the other peer only).
  const relay = async (fromSent, toCall) => {
    while (fromSent.length) {
      const frame = fromSent.shift();
      assert(frame.type === 'signal', `expected a {type:'signal'} frame, got ${JSON.stringify(frame)}`);
      await toCall.handleSignal({ type: 'signal', payload: frame.payload });
    }
  };

  // peer-ready fires on BOTH when the room reaches 2 peers (Phase-01 REQ-03).
  await callee.call.handleSignal({ type: 'peer-ready' });
  await caller.call.handleSignal({ type: 'peer-ready' });

  // The caller must have produced an OFFER and sent it.
  const offerFrame = caller.sent.find((m) => m.payload && m.payload.type === 'offer');
  assert(offerFrame, 'caller did not create/send an SDP offer on peer-ready');
  // The callee must NOT offer (it answers).
  assert(!callee.sent.some((m) => m.payload && m.payload.type === 'offer'), 'callee wrongly created an offer');

  // Drive the relay to completion (offer → callee answers → caller setsRemote; ICE both ways).
  await relay(caller.sent, callee.call);   // offer (+any caller ICE) to callee
  await relay(callee.sent, caller.call);   // answer (+any callee ICE) to caller
  await relay(caller.sent, callee.call);   // any further caller ICE
  await relay(callee.sent, caller.call);   // any further callee ICE

  // Both peers must have applied the remote SDP of the right type.
  assert(deepEq(callee.getPc().remoteDescription, { type: 'offer', sdp: 'FAKE-SDP-OFFER' }),
    'callee did not setRemoteDescription(offer)');
  assert(deepEq(caller.getPc().remoteDescription, { type: 'answer', sdp: 'FAKE-SDP-ANSWER' }),
    'caller did not setRemoteDescription(answer)');

  // ICE: simulate each pc gathering a local candidate; the core must relay it as a signal.
  emitLocalIce(caller.getPc(), { candidate: 'CALLER-ICE-1', sdpMid: '0', sdpMLineIndex: 0 });
  emitLocalIce(callee.getPc(), { candidate: 'CALLEE-ICE-1', sdpMid: '0', sdpMLineIndex: 0 });
  await relay(caller.sent, callee.call);
  await relay(callee.sent, caller.call);
  assert(callee.getPc().ice.some((c) => c.candidate === 'CALLER-ICE-1'), 'callee never received caller ICE');
  assert(caller.getPc().ice.some((c) => c.candidate === 'CALLEE-ICE-1'), 'caller never received callee ICE');

  // The remote MEDIA arrives: each pc fires its track event → core must surface it.
  emitRemoteTrack(callee.getPc(), callerStream); // callee receives caller's media
  emitRemoteTrack(caller.getPc(), calleeStream); // caller receives callee's media
  assert(calleeRemote === callerStream, 'callee never received the remote stream (onRemoteStream not fired)');
  assert(callerRemote === calleeStream, 'caller never received the remote stream (onRemoteStream not fired)');
}

// ---------------------------------------------------------------------------
// EC-11 — control logic on fake tracks: mute, camera toggle, hangup.
// ---------------------------------------------------------------------------
async function EC11() {
  // setTrackEnabled is a pure exported helper.
  const s = fakeStream(['audio', 'video']);
  assert(s.getAudioTracks()[0].enabled === true, 'precondition: audio enabled');
  // Mute mic.
  setTrackEnabled(s, 'audio', false);
  assert(s.getAudioTracks().every((t) => t.enabled === false), 'mute did not disable audio track.enabled');
  assert(s.getVideoTracks().every((t) => t.enabled === true), 'mute wrongly touched video tracks');
  // Toggle camera off then on.
  setTrackEnabled(s, 'video', false);
  assert(s.getVideoTracks().every((t) => t.enabled === false), 'camera toggle did not disable video track.enabled');
  setTrackEnabled(s, 'video', true);
  assert(s.getVideoTracks().every((t) => t.enabled === true), 'camera toggle did not re-enable video track.enabled');

  // hangup() closes the pc AND stops every local track.
  let pcRef = null;
  const local = fakeStream(['audio', 'video']);
  const call = createCall({
    send: () => {},
    createPeerConnection: () => { pcRef = fakePeerConnection(); return pcRef; },
    onRemoteStream: () => {},
    onLocalState: () => {},
  });
  await call.startAsRole('caller', local);
  call.hangup();
  assert(pcRef && pcRef.closed === true, 'hangup did not close the peer connection');
  assert(local.getTracks().every((t) => t.stopped === true), 'hangup did not stop every local track');
}

// ---------------------------------------------------------------------------
// EC-10 — OPTIONAL headless fake-media smoke. Gate-SKIPS (exit 0) if Playwright/Chromium absent.
// Severity is `warn`: it must NEVER block. We do not install heavy browsers.
// ---------------------------------------------------------------------------
async function EC10() {
  let chromium;
  try {
    ({ chromium } = await import('playwright'));
  } catch {
    console.log('  SKIP EC-10 — playwright absent (warn row, non-blocking)');
    return { skipped: true };
  }
  const { createServer } = await import('../server.js');
  let browser, srv;
  try {
    const flags = ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
                   '--autoplay-policy=no-user-gesture-required'];
    browser = await chromium.launch({ args: flags });
  } catch (e) {
    console.log(`  SKIP EC-10 — chromium not launchable (${e.message.split('\n')[0]}); warn row, non-blocking`);
    return { skipped: true };
  }
  try {
    const { httpServer } = createServer();
    srv = await new Promise((res) => httpServer.listen(0, '127.0.0.1', () => res(httpServer)));
    const { port } = srv.address();
    const url = `http://127.0.0.1:${port}/?room=smoke`;

    const ctxA = await browser.newContext({ permissions: ['camera', 'microphone'] });
    const ctxB = await browser.newContext({ permissions: ['camera', 'microphone'] });
    const pageA = await ctxA.newPage();
    const pageB = await ctxB.newPage();
    const room = `smoke-${Date.now()}`;
    const join = async (page) => {
      await page.goto(url);
      await page.fill('#room', room);
      await page.click('#join');
    };
    await join(pageA);
    await join(pageB);
    // Wait for the remote video on page A to carry real pixels.
    await pageA.waitForFunction(() => {
      const v = document.querySelector('#remoteVideo');
      return v && v.videoWidth > 0;
    }, { timeout: 20000 });
    console.log('  PASS EC-10 — remote video reached videoWidth>0 across two fake-media contexts');
    return { skipped: false };
  } finally {
    try { await browser.close(); } catch {}
    try { if (srv) await new Promise((r) => srv.close(r)); } catch {}
  }
}

// ---------------------------------------------------------------------------
const CHECKS = {
  'EC-8': async () => {
    // Human/UAT row — not machine-witnessable. Reported as a pass for gate accounting; the felt
    // check (local preview renders) is performed at UAT per 02-VERIFICATION U-1.
    console.log('  HUMAN EC-8 — local preview renders: verified via UAT (02-VERIFICATION U-1)');
    return { human: true };
  },
  'EC-9': EC9,
  'EC-10': EC10,
  'EC-11': EC11,
};

async function main() {
  // Args:  `EC-9`            -> run one row (a task's acceptance check)
  //        `--except EC-10`  -> run all rows EXCEPT the listed ones (comma-separated)
  //        (none)            -> run all rows
  // `npm test` uses `--except EC-10` so the browser smoke runs once, in `pretest`.
  const args = process.argv.slice(2);
  const exceptIdx = args.indexOf('--except');
  const except = exceptIdx >= 0
    ? (args[exceptIdx + 1] || '').split(',').map((s) => s.trim()).filter(Boolean)
    : [];
  const want = args.find((a, i) => !a.startsWith('--') && i !== exceptIdx + 1);
  if (want && !CHECKS[want]) { console.error(`unknown row ${want}`); process.exit(2); }
  const ids = (want ? [want] : Object.keys(CHECKS)).filter((id) => !except.includes(id));

  let failed = 0, skipped = 0, human = 0;
  for (const id of ids) {
    try {
      const r = await CHECKS[id]();
      if (r && r.skipped) { skipped++; continue; }
      if (r && r.human) { human++; continue; }
      console.log(`  PASS ${id}`);
    } catch (e) {
      // EC-10 is `warn` severity — a failure there must NOT fail the gate.
      if (id === 'EC-10') { console.log(`  WARN EC-10 — smoke failed (non-blocking): ${e.message}`); skipped++; continue; }
      failed++;
      console.log(`  FAIL ${id} — ${e.message}`);
    }
  }
  const note = [skipped ? `${skipped} warn/skip` : '', human ? `${human} human` : '']
    .filter(Boolean).join(', ');
  console.log(failed === 0 ? `\nGATE GREEN — gate rows pass${note ? ` (${note})` : ''}`
                           : `\nGATE RED — ${failed} gate row(s) failing`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((e) => { console.error('harness error:', e); process.exit(1); });
