// Eval harness for Phase 03 (production hardening). Implements the LOCKED 03-EVAL-CONTRACT rows.
//
//   node test/eval-phase3.mjs            -> run ALL rows (the phase gate; npm run eval3)
//   node test/eval-phase3.mjs EC-13      -> run one row (a task's acceptance_criteria)
//   node test/eval-phase3.mjs --except EC-17   -> run all rows EXCEPT the listed ones
//
// Exit 0 = all selected GATE rows PASS (warn rows never block). Non-zero = a gate is RED.
//
// THE EVAL-FIRST CRUX (same as Phases 01/02): the deterministic logic is factored into PURE
// exports — makeTurnCredential + makeRateLimiter (server.js), signalingUrl + backoffDelay
// (call-core.js) — so EC-13/14/15 run in Node with no browser and no infra. EC-12 + EC-16 drive
// a REAL server (like Phase 01). EC-17 is an OPTIONAL self-signed TLS smoke that gate-SKIPS when
// openssl/cert is unavailable (mirrors EC-10). EC-18 is Human (real deploy + TURN).

import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import https from 'node:https';
import { execFileSync } from 'node:child_process';
import WebSocket from 'ws';

import { createServer, makeTurnCredential, makeRateLimiter } from '../server.js';
import { signalingUrl, backoffDelay } from '../../public/call-core.js';

function assert(cond, msg) { if (!cond) throw new Error(msg); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Boot a real server instance (optionally with env overrides) on an ephemeral loopback port.
function startServer(env = {}) {
  const saved = {};
  for (const k of Object.keys(env)) { saved[k] = process.env[k]; process.env[k] = env[k]; }
  const { httpServer } = createServer();
  return new Promise((resolve) => {
    httpServer.listen(0, '127.0.0.1', () => {
      const { port } = httpServer.address();
      resolve({
        port,
        close: () => new Promise((r) => {
          httpServer.close(() => {
            for (const k of Object.keys(env)) {
              if (saved[k] === undefined) delete process.env[k]; else process.env[k] = saved[k];
            }
            r();
          });
        }),
      });
    });
  });
}

// ---------------------------------------------------------------------------
// EC-12 — GET /ice-servers: STUN-only without TURN env; +TURN entry with env.
// ---------------------------------------------------------------------------
async function EC12() {
  // (a) No TURN env -> STUN only, no turn entry.
  const srv1 = await startServer();
  try {
    const r = await fetch(`http://127.0.0.1:${srv1.port}/ice-servers`);
    assert(r.status === 200, `/ice-servers status ${r.status} != 200`);
    assert((r.headers.get('content-type') || '').includes('application/json'),
      '/ice-servers content-type is not application/json');
    const body = await r.json();
    assert(Array.isArray(body.iceServers), 'body.iceServers is not an array');
    const stun = body.iceServers.find((s) => String(s.urls).startsWith('stun:'));
    assert(stun, 'no STUN entry returned by default');
    const turn = body.iceServers.find((s) => String(s.urls).startsWith('turn:'));
    assert(!turn, 'a TURN entry was returned even though no TURN env is set');
  } finally { await srv1.close(); }

  // (b) TURN_URL + TURN_SECRET set -> a turn entry with ephemeral creds.
  const secret = 's3cr3t-turn-key';
  const userid = 'alice';
  const srv2 = await startServer({
    TURN_URL: 'turn:turn.example.com:3478', TURN_SECRET: secret, TURN_USER: userid, TURN_TTL: '3600',
  });
  try {
    const r = await fetch(`http://127.0.0.1:${srv2.port}/ice-servers`);
    const body = await r.json();
    const turn = body.iceServers.find((s) => String(s.urls).startsWith('turn:'));
    assert(turn, 'no TURN entry returned even though TURN_URL+TURN_SECRET are set');
    assert(turn.urls === 'turn:turn.example.com:3478', `turn.urls wrong: ${turn.urls}`);
    assert(/^[0-9]+:/.test(turn.username), `turn.username not "<expiry>:<userid>": ${turn.username}`);
    assert(turn.username.endsWith(`:${userid}`), `turn.username userid mismatch: ${turn.username}`);
    // Consistency: the returned credential must equal the pure helper recomputed from the
    // expiry parsed back out of the returned username (proves the endpoint used the scheme).
    const expiry = Number(turn.username.split(':')[0]);
    const expected = makeTurnCredential(secret, userid, expiry).credential;
    assert(turn.credential === expected,
      `turn.credential ${turn.credential} != makeTurnCredential(...) ${expected}`);
    // Ephemeral: expiry is in the future (within a small window of now+TTL).
    const now = Math.floor(Date.now() / 1000);
    assert(expiry > now && expiry <= now + 3600 + 5, `expiry ${expiry} not ~now+TTL (now ${now})`);
  } finally { await srv2.close(); }
}

// ---------------------------------------------------------------------------
// EC-13 — pure makeTurnCredential against the FROZEN golden literal (coturn REST scheme).
// ---------------------------------------------------------------------------
async function EC13() {
  // Golden values precomputed once (see 03-SPEC §2) and frozen here. Asserting against a literal
  // (not a re-HMAC inside the test) is what makes this a real, non-circular gate.
  const GOLDEN_USERNAME = '4102444800:alice';
  const GOLDEN_CREDENTIAL = 'YxRVVa1+vr70jHjnKQ13MVipWvY=';
  const out = makeTurnCredential('s3cr3t-turn-key', 'alice', 4102444800);
  assert(out.username === GOLDEN_USERNAME, `username ${out.username} != ${GOLDEN_USERNAME}`);
  assert(out.credential === GOLDEN_CREDENTIAL, `credential ${out.credential} != ${GOLDEN_CREDENTIAL}`);
  // Independent cross-check of the FORMULA (base64 HMAC-SHA1 of the username under the secret).
  const recomputed = crypto.createHmac('sha1', 's3cr3t-turn-key').update(GOLDEN_USERNAME).digest('base64');
  assert(recomputed === GOLDEN_CREDENTIAL, `formula sanity: ${recomputed} != golden`);
}

// ---------------------------------------------------------------------------
// EC-14 — pure signalingUrl picks wss for https, ws for http.
// ---------------------------------------------------------------------------
async function EC14() {
  assert(signalingUrl({ protocol: 'https:', host: 'h' }) === 'wss://h/ws',
    'https did not yield wss://h/ws');
  assert(signalingUrl({ protocol: 'http:', host: 'h' }) === 'ws://h/ws',
    'http did not yield ws://h/ws');
  // A realistic host:port is preserved.
  assert(signalingUrl({ protocol: 'https:', host: 'talk.example.com:8443' }) === 'wss://talk.example.com:8443/ws',
    'host:port not preserved for https');
}

// ---------------------------------------------------------------------------
// EC-15 — pure backoffDelay: exponential, capped, bounded jitter (rng injected).
// ---------------------------------------------------------------------------
async function EC15() {
  const opts = { base: 500, factor: 2, cap: 15000, jitter: 0.5 };
  const noJitter = { ...opts, rng: () => 0 };       // rng()=0 -> delay == raw (max of window)
  const fullJitter = { ...opts, rng: () => 1 };     // rng()->1 -> delay == raw*(1-jitter) (min)

  // Exponential growth pre-cap with jitter off.
  assert(backoffDelay(0, noJitter) === 500, `attempt0 ${backoffDelay(0, noJitter)} != 500`);
  assert(backoffDelay(1, noJitter) === 1000, `attempt1 ${backoffDelay(1, noJitter)} != 1000`);
  assert(backoffDelay(2, noJitter) === 2000, `attempt2 ${backoffDelay(2, noJitter)} != 2000`);
  assert(backoffDelay(3, noJitter) === 4000, `attempt3 ${backoffDelay(3, noJitter)} != 4000`);

  // Saturates at cap (attempt 5 -> 500*32=16000 -> capped to 15000) and stays there.
  assert(backoffDelay(5, noJitter) === 15000, `attempt5 ${backoffDelay(5, noJitter)} != 15000 (cap)`);
  assert(backoffDelay(50, noJitter) === 15000, `attempt50 ${backoffDelay(50, noJitter)} != 15000 (cap)`);

  // For ANY attempt and injected rng in {0,1}, delay stays within [raw*(1-jitter), raw] and <= cap.
  for (let a = 0; a <= 12; a++) {
    const raw = Math.min(opts.cap, opts.base * opts.factor ** a);
    const hi = backoffDelay(a, noJitter);    // rng=0 -> upper bound
    const lo = backoffDelay(a, fullJitter);  // rng=1 -> lower bound
    assert(hi === raw, `attempt${a}: rng=0 delay ${hi} != raw ${raw}`);
    assert(Math.abs(lo - raw * (1 - opts.jitter)) < 1e-6, `attempt${a}: rng=1 delay ${lo} != raw*(1-jitter)`);
    assert(hi <= opts.cap + 1e-6, `attempt${a}: delay ${hi} exceeds cap ${opts.cap}`);
    assert(lo >= 0, `attempt${a}: delay ${lo} < 0`);
    // A mid jitter value also stays in the window.
    const mid = backoffDelay(a, { ...opts, rng: () => 0.37 });
    assert(mid <= raw + 1e-6 && mid >= raw * (1 - opts.jitter) - 1e-6,
      `attempt${a}: mid jitter ${mid} outside [${raw * (1 - opts.jitter)}, ${raw}]`);
  }
  // Defaults (no rng/opts beyond attempt) must still produce a finite, capped, non-negative delay.
  const d = backoffDelay(3);
  assert(Number.isFinite(d) && d >= 0 && d <= 15000, `default-opts delay ${d} out of range`);
}

// ---------------------------------------------------------------------------
// EC-16 — real server closes a socket that floods past the per-connection rate limit.
// ---------------------------------------------------------------------------
async function EC16() {
  // First, the pure limiter behaves: allow() true up to max, false once exceeded.
  let t = 0;
  const lim = makeRateLimiter({ max: 20, windowMs: 1000, now: () => t });
  for (let i = 0; i < 20; i++) assert(lim.allow() === true, `limiter rejected msg ${i + 1} within max`);
  assert(lim.allow() === false, 'limiter did not reject the 21st message in the window');
  // After the window slides, it allows again.
  t = 2000;
  assert(lim.allow() === true, 'limiter did not recover after the window slid');

  // Now drive a REAL server: a flooding socket gets closed; a polite socket stays open.
  const srv = await startServer();
  try {
    const flood = new WebSocket(`ws://127.0.0.1:${srv.port}/ws`);
    const polite = new WebSocket(`ws://127.0.0.1:${srv.port}/ws`);
    let floodClose = null;
    let politeClosed = false;
    flood.on('close', (code) => { floodClose = code; });
    polite.on('close', () => { politeClosed = true; });
    await Promise.all([
      new Promise((res) => flood.on('open', res)),
      new Promise((res) => polite.on('open', res)),
    ]);
    // The polite socket joins normally and sends a few legitimate frames — must NOT be throttled.
    polite.send(JSON.stringify({ type: 'join', room: 'ec16-polite' }));
    for (let i = 0; i < 5; i++) polite.send(JSON.stringify({ type: 'signal', payload: { candidate: `c${i}` } }));
    // The flooding socket blasts well past the limit in one tick.
    for (let i = 0; i < 60; i++) flood.send(JSON.stringify({ type: 'signal', payload: { n: i } }));

    // Wait for the server to close the flooder.
    const deadline = Date.now() + 3000;
    while (floodClose === null && Date.now() < deadline) await sleep(20);
    assert(floodClose !== null, 'flooding socket was not closed by the server');
    assert(floodClose === 4029, `flood close code ${floodClose} != 4029 (rate-limit)`);
    // The polite socket must still be open.
    await sleep(200);
    assert(!politeClosed, 'a well-behaved socket was wrongly closed');
    assert(polite.readyState === WebSocket.OPEN, `polite socket not OPEN (state ${polite.readyState})`);
    try { polite.close(); } catch {}
  } finally { await srv.close(); }
}

// ---------------------------------------------------------------------------
// EC-17 — OPTIONAL self-signed TLS smoke. Gate-SKIPS (exit 0) if openssl/cert unavailable.
// Severity is `warn`: it must NEVER block. (Mirrors EC-10.)
// ---------------------------------------------------------------------------
async function EC17() {
  // 1) Generate a throwaway self-signed cert via openssl (skip if absent).
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'talk-tls-'));
  const certFile = path.join(dir, 'cert.pem');
  const keyFile = path.join(dir, 'key.pem');
  try {
    execFileSync('openssl', [
      'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
      '-keyout', keyFile, '-out', certFile,
      '-days', '1', '-subj', '/CN=localhost',
    ], { stdio: 'ignore' });
  } catch (e) {
    console.log(`  SKIP EC-17 — openssl unavailable/failed (${(e.message || '').split('\n')[0]}); warn row, non-blocking`);
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
    return { skipped: true };
  }
  if (!fs.existsSync(certFile) || !fs.existsSync(keyFile)) {
    console.log('  SKIP EC-17 — cert/key not produced; warn row, non-blocking');
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
    return { skipped: true };
  }

  // 2) Start the server in TLS mode and verify https /healthz + a wss handshake.
  const srv = await startServer({ TLS_CERT_FILE: certFile, TLS_KEY_FILE: keyFile });
  try {
    // https GET /healthz with rejectUnauthorized:false -> 200 "ok".
    const status = await new Promise((resolve, reject) => {
      const req = https.request(
        { host: '127.0.0.1', port: srv.port, path: '/healthz', method: 'GET', rejectUnauthorized: false },
        (res) => { let b = ''; res.on('data', (d) => (b += d)); res.on('end', () => resolve({ code: res.statusCode, body: b })); },
      );
      req.on('error', reject); req.end();
    });
    assert(status.code === 200, `https /healthz status ${status.code} != 200`);
    assert(status.body.trim() === 'ok', `https /healthz body "${status.body}" != "ok"`);

    // wss:// handshake succeeds (the WS server attached to the https server).
    await new Promise((resolve, reject) => {
      const ws = new WebSocket(`wss://127.0.0.1:${srv.port}/ws`, { rejectUnauthorized: false });
      const timer = setTimeout(() => reject(new Error('wss connect timeout')), 3000);
      ws.on('open', () => { clearTimeout(timer); try { ws.close(); } catch {} resolve(); });
      ws.on('error', (err) => { clearTimeout(timer); reject(err); });
    });
    console.log('  PASS EC-17 — TLS: https /healthz 200 + wss handshake (self-signed)');
    return { skipped: false };
  } finally {
    await srv.close();
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  }
}

// ---------------------------------------------------------------------------
const CHECKS = {
  'EC-12': EC12,
  'EC-13': EC13,
  'EC-14': EC14,
  'EC-15': EC15,
  'EC-16': EC16,
  'EC-17': EC17,
  'EC-18': async () => {
    // Human/UAT row — a real deploy behind TLS + a forced-relay call through a real coturn TURN
    // server. Not machine-witnessable here (no public domain / TURN infra). Verified at UAT per
    // 03-VERIFICATION U-3 + docs/DEPLOY.md.
    console.log('  HUMAN EC-18 — real TLS deploy + forced-relay TURN call: verified via UAT (03-VERIFICATION U-3)');
    return { human: true };
  },
};

async function main() {
  // Args:  `EC-13`           -> run one row
  //        `--except EC-17`  -> run all rows EXCEPT the listed ones (comma-separated)
  //        (none)            -> run all rows
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
      // EC-17 is `warn` severity — a failure there must NOT fail the gate.
      if (id === 'EC-17') { console.log(`  WARN EC-17 — TLS smoke failed (non-blocking): ${e.message}`); skipped++; continue; }
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
