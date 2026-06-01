// Talk — signaling server (Phase 01).
// HTTP serves the web client + /healthz; WebSocket (/ws) pairs two peers per room and relays
// their opaque WebRTC handshake (SDP offer/answer + ICE). The server NEVER parses media.
// Protocol is specified in .planning/phases/01-signaling/01-SPEC.md and gated by 01-EVAL-CONTRACT.md.

import http from 'node:http';
import https from 'node:https';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(__dirname, '..', 'public');

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
                '.css': 'text/css; charset=utf-8', '.ico': 'image/x-icon' };

const STUN_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }];
const RATE_LIMIT = { max: 20, windowMs: 1000 }; // per-connection inbound message rate (REQ-15)
const RATE_LIMIT_CLOSE_CODE = 4029;             // private-use WS close code: "rate limit exceeded"

function send(ws, obj) {
  if (ws.readyState === ws.OPEN) ws.send(JSON.stringify(obj));
}

// ---- Phase 03 pure helpers (exported so they're independently Code-gatable) ----

// Ephemeral coturn "TURN REST API" credential (REQ-12). The username embeds the expiry so coturn
// can verify it statelessly against its shared `static-auth-secret`:
//   username   = "<expiryUnixTs>:<userid>"
//   credential = base64( HMAC-SHA1( key = secret, message = username ) )   // standard base64
export function makeTurnCredential(secret, userid, expiryTs) {
  const username = `${expiryTs}:${userid}`;
  const credential = crypto.createHmac('sha1', secret).update(username).digest('base64');
  return { username, credential };
}

// Build the ICE server list (REQ-11). Always STUN; adds a TURN entry with FRESH ephemeral creds
// when both TURN_URL and TURN_SECRET are configured. Reads `env` (defaults to process.env) per
// call so credentials are minted at request time and stay time-limited.
export function buildIceServers(env = process.env, now = Date.now) {
  const iceServers = [...STUN_SERVERS];
  const { TURN_URL, TURN_SECRET } = env;
  if (TURN_URL && TURN_SECRET) {
    const ttl = Number(env.TURN_TTL) > 0 ? Number(env.TURN_TTL) : 3600;
    const userid = env.TURN_USER || 'talk';
    const expiryTs = Math.floor(now() / 1000) + ttl;
    const { username, credential } = makeTurnCredential(TURN_SECRET, userid, expiryTs);
    iceServers.push({ urls: TURN_URL, username, credential });
  }
  return iceServers;
}

// Per-connection sliding-window rate limiter (REQ-15). Timestamp-based — NO timer is created, so
// it never keeps the event loop alive. allow() records `now()` and returns true while the count in
// the trailing windowMs is <= max, false once it exceeds max.
export function makeRateLimiter({ max = RATE_LIMIT.max, windowMs = RATE_LIMIT.windowMs, now = Date.now } = {}) {
  const hits = [];
  return {
    allow() {
      const t = now();
      const cutoff = t - windowMs;
      while (hits.length && hits[0] <= cutoff) hits.shift();
      hits.push(t);
      return hits.length <= max;
    },
  };
}

export function createServer() {
  // room id -> array of peer sockets (max 2)
  const rooms = new Map();

  const handler = (req, res) => {
    if (req.method === 'GET' && req.url === '/healthz') {
      res.writeHead(200, { 'content-type': 'text/plain' });
      return res.end('ok');
    }
    if (req.method === 'GET' && req.url.split('?')[0] === '/ice-servers') {     // REQ-11
      // env read per request -> ephemeral TURN creds (REQ-12), STUN-only otherwise.
      res.writeHead(200, { 'content-type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ iceServers: buildIceServers() }));
    }
    // static: map / -> index.html, prevent path traversal
    const urlPath = req.url.split('?')[0];
    const rel = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
    const filePath = path.join(PUBLIC_DIR, rel);
    if (!filePath.startsWith(PUBLIC_DIR)) { res.writeHead(403); return res.end('forbidden'); }
    fs.readFile(filePath, (err, buf) => {
      if (err) { res.writeHead(404, { 'content-type': 'text/plain' }); return res.end('not found'); }
      res.writeHead(200, { 'content-type': TYPES[path.extname(filePath)] || 'application/octet-stream' });
      res.end(buf);
    });
  };

  // TLS (REQ-16): serve HTTPS (-> wss for the attached WS server) when cert+key env are provided
  // and readable; otherwise plain HTTP (unchanged dev behavior). The returned `httpServer` key is
  // preserved either way so the Phase 01/02 harnesses keep working.
  let httpServer;
  const { TLS_CERT_FILE, TLS_KEY_FILE } = process.env;
  if (TLS_CERT_FILE && TLS_KEY_FILE) {
    const cert = fs.readFileSync(TLS_CERT_FILE);
    const key = fs.readFileSync(TLS_KEY_FILE);
    httpServer = https.createServer({ cert, key }, handler);
  } else {
    httpServer = http.createServer(handler);
  }

  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });

  wss.on('connection', (ws) => {
    ws.room = null;
    ws.role = null;
    const limiter = makeRateLimiter(RATE_LIMIT); // REQ-15: per-connection inbound rate limit

    ws.on('message', (raw) => {
      // Count EVERY inbound frame (before parsing). One flooding client can't spam the relay:
      // past the limit we close this socket; `close` below frees its room slot + notifies the peer.
      if (!limiter.allow()) { try { ws.close(RATE_LIMIT_CLOSE_CODE, 'rate limit exceeded'); } catch {} return; }

      let msg;
      try { msg = JSON.parse(raw.toString()); } catch { return; }

      if (msg.type === 'join') {
        const room = String(msg.room || '');
        if (!room) return;
        const peers = rooms.get(room) || [];
        if (peers.length >= 2) { send(ws, { type: 'room-full', room }); return; } // REQ-07: not admitted
        const role = peers.length === 0 ? 'callee' : 'caller';                    // REQ-02: deterministic by order
        peers.push(ws);
        rooms.set(room, peers);
        ws.room = room;
        ws.role = role;
        send(ws, { type: 'joined', room, role, peers: peers.length });
        if (peers.length === 2) {                                                 // REQ-03: pair both
          for (const p of peers) send(p, { type: 'peer-ready' });
        }
        return;
      }

      if (msg.type === 'signal') {                                                // REQ-04/05: relay to OTHER only
        if (!ws.room) return;
        const peers = rooms.get(ws.room) || [];
        for (const p of peers) if (p !== ws) send(p, { type: 'signal', payload: msg.payload });
        return;
      }
    });

    ws.on('close', () => {                                                        // REQ-06: notify + free slot
      if (!ws.room) return;
      const peers = rooms.get(ws.room) || [];
      const remaining = peers.filter((p) => p !== ws);
      for (const p of remaining) send(p, { type: 'peer-left' });
      if (remaining.length === 0) rooms.delete(ws.room);
      else rooms.set(ws.room, remaining);
    });
  });

  return { httpServer, wss, rooms };
}

// Standalone: `node server.js`
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const PORT = process.env.PORT || 8080;
  const tls = !!(process.env.TLS_CERT_FILE && process.env.TLS_KEY_FILE);
  const { httpServer } = createServer();
  const scheme = tls ? 'https' : 'http';
  httpServer.listen(PORT, () => console.log(`Talk signaling server on ${scheme}://localhost:${PORT}`));
}
