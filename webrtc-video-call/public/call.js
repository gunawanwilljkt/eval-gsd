// call.js — the DOM/browser shell. The ONLY client file that touches document / navigator /
// window / RTCPeerConnection / getUserMedia. It captures local media, opens the signaling
// WebSocket, and wires REAL browser dependencies into the pure state machine in call-core.js.

import { createCall, setTrackEnabled, STUN_SERVERS, signalingUrl, backoffDelay } from './call-core.js';

const $ = (id) => document.getElementById(id);
const roomInput = $('room');
const joinBtn = $('join');
const localVideo = $('localVideo');
const remoteVideo = $('remoteVideo');
const muteBtn = $('mute');
const cameraBtn = $('camera');
const hangupBtn = $('hangup');
const statusEl = $('status');
const controls = $('controls');

let ws = null;
let localStream = null;
let call = null;
let micOn = true;
let camOn = true;
let iceServers = STUN_SERVERS;   // replaced by GET /ice-servers once fetched (REQ-11)
let currentRoom = null;          // the room we're in (for reconnect re-join)
let reconnectAttempt = 0;        // capped-backoff counter (REQ-14)
let reconnectTimer = null;
let active = false;              // true between Join and an explicit teardown

function setStatus(text) { if (statusEl) statusEl.textContent = text; }

// Prefill the room from ?room= so two tabs can be pointed at the same call quickly (and so the
// headless smoke can drive it).
const params = new URLSearchParams(window.location.search);
if (params.get('room')) roomInput.value = params.get('room');

// Fetch ICE config from the server (STUN by default, +TURN when configured). Falls back to the
// bundled STUN list if the endpoint is unreachable. (REQ-11)
async function loadIceServers() {
  try {
    const r = await fetch('/ice-servers');
    if (r.ok) {
      const body = await r.json();
      if (Array.isArray(body.iceServers) && body.iceServers.length) iceServers = body.iceServers;
    }
  } catch { /* keep the STUN fallback */ }
}

async function join() {
  const room = (roomInput.value || '').trim();
  if (!room) { setStatus('Enter a room name first.'); return; }
  joinBtn.disabled = true;
  roomInput.disabled = true;
  currentRoom = room;
  active = true;

  // 1) Capture local camera + mic and show the local preview (REQ-08).
  try {
    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  } catch (err) {
    setStatus(`Could not access camera/mic: ${err.message}`);
    joinBtn.disabled = false; roomInput.disabled = false; active = false;
    return;
  }
  localVideo.srcObject = localStream;

  // 1b) Pull ICE config (STUN + maybe TURN) before building the peer connection.
  await loadIceServers();

  // 2) Build the pure call core with REAL injected dependencies.
  call = createCall({
    send: (msg) => { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg)); },
    createPeerConnection: () => new RTCPeerConnection({ iceServers }),
    onRemoteStream: (stream) => { remoteVideo.srcObject = stream; setStatus('In call.'); },
    onLocalState: (state) => {
      if (state === 'idle') { remoteVideo.srcObject = null; setStatus('Waiting for a peer…'); }
      if (state === 'connecting') setStatus('Waiting for a peer…');
      if (state === 'ended') setStatus('Call ended.');
    },
  });

  // 3) Open the signaling socket and speak the Phase-01 protocol.
  controls.hidden = false;
  openSocket();
}

// Open (or re-open) the signaling socket and speak the Phase-01 protocol. On an UNEXPECTED drop
// while a call is active, reconnect with capped exponential backoff + jitter (REQ-14).
function openSocket() {
  ws = new WebSocket(signalingUrl(window.location));   // wss when HTTPS, ws when HTTP (REQ-13)
  ws.addEventListener('open', () => ws.send(JSON.stringify({ type: 'join', room: currentRoom })));
  ws.addEventListener('message', async (e) => {
    let msg; try { msg = JSON.parse(e.data); } catch { return; }
    if (msg.type === 'joined') {
      reconnectAttempt = 0;   // a clean join resets the backoff
      setStatus(`Joined "${currentRoom}" as ${msg.role}. Waiting for a peer…`);
      await call.startAsRole(msg.role, localStream);
      return;
    }
    if (msg.type === 'room-full') {
      setStatus(`Room "${currentRoom}" is full (2 peers max).`);
      teardown();
      return;
    }
    // peer-ready / signal / peer-left all flow to the pure core.
    await call.handleSignal(msg);
  });
  ws.addEventListener('close', () => {
    if (!active) { setStatus('Disconnected from server.'); return; }
    // Unexpected drop during a live call -> schedule a reconnect.
    const delay = backoffDelay(reconnectAttempt++);
    setStatus(`Connection lost — reconnecting in ${Math.round(delay / 1000)}s…`);
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => { if (active) openSocket(); }, delay);
  });
}

function teardown() {
  active = false;
  reconnectAttempt = 0;
  clearTimeout(reconnectTimer);
  try { if (call) call.hangup(); } catch {}
  try { if (ws) ws.close(); } catch {}
  ws = null;
  localVideo.srcObject = null;
  remoteVideo.srcObject = null;
  controls.hidden = true;
  joinBtn.disabled = false;
  roomInput.disabled = false;
}

// ---- Controls (REQ-10) ----
muteBtn.addEventListener('click', () => {
  micOn = !micOn;
  setTrackEnabled(localStream, 'audio', micOn);
  muteBtn.textContent = micOn ? 'Mute mic' : 'Unmute mic';
  muteBtn.classList.toggle('off', !micOn);
});

cameraBtn.addEventListener('click', () => {
  camOn = !camOn;
  setTrackEnabled(localStream, 'video', camOn);
  cameraBtn.textContent = camOn ? 'Camera off' : 'Camera on';
  cameraBtn.classList.toggle('off', !camOn);
});

hangupBtn.addEventListener('click', () => { teardown(); setStatus('Call ended.'); });

joinBtn.addEventListener('click', join);
roomInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') join(); });
setStatus('Enter a room name and click Join.');
