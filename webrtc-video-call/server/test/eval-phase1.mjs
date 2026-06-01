// Eval harness for Phase 01 (signaling). Implements the LOCKED eval contract's rows EC-1..EC-7.
//
//   node test/eval-phase1.mjs            -> run ALL rows (the phase gate; npm run eval)
//   node test/eval-phase1.mjs EC-3       -> run one row (a task's acceptance_criteria)
//
// Exit 0 = all selected rows PASS (gate clears). Non-zero = a gate is RED.
// Zero external deps: built-in WebSocket client + global fetch (Node >=22). Drives a real
// server instance on an ephemeral port — these are behavioral evals, not mocks.

import { createServer } from '../server.js';

const TIMEOUT = 3000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function startServer() {
  const { httpServer } = createServer();
  return new Promise((resolve) => {
    httpServer.listen(0, '127.0.0.1', () => {
      const { port } = httpServer.address();
      resolve({ port, close: () => new Promise((r) => httpServer.close(r)) });
    });
  });
}

function client(port) {
  const ws = new WebSocket(`ws://127.0.0.1:${port}/ws`);
  const msgs = [];
  ws.addEventListener('message', (e) => { try { msgs.push(JSON.parse(e.data)); } catch {} });
  return {
    ws, msgs,
    open: () => new Promise((res, rej) => {
      if (ws.readyState === 1) return res();
      ws.addEventListener('open', () => res(), { once: true });
      ws.addEventListener('error', () => rej(new Error('ws connect error')), { once: true });
    }),
    send: (o) => ws.send(JSON.stringify(o)),
    waitFor: async (pred, ms = TIMEOUT) => {
      const deadline = Date.now() + ms;
      while (Date.now() < deadline) {
        const m = msgs.find(pred);
        if (m) return m;
        await sleep(15);
      }
      throw new Error('timeout waiting for a matching message');
    },
    sawAny: (pred) => msgs.some(pred),
    close: () => { try { ws.close(); } catch {} },
  };
}

function assert(cond, msg) { if (!cond) throw new Error(msg); }
const deepEq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// Pair two clients in a fresh room; returns {a,b} both joined + peer-ready.
async function pair(port, room) {
  const a = client(port); await a.open(); a.send({ type: 'join', room });
  await a.waitFor((m) => m.type === 'joined');
  const b = client(port); await b.open(); b.send({ type: 'join', room });
  await b.waitFor((m) => m.type === 'joined');
  await a.waitFor((m) => m.type === 'peer-ready');
  await b.waitFor((m) => m.type === 'peer-ready');
  return { a, b };
}

// ---- the rows ----
const CHECKS = {
  'EC-1': async ({ port }) => {
    const r = await fetch(`http://127.0.0.1:${port}/healthz`);
    assert(r.status === 200, `healthz status ${r.status} != 200`);
    assert((await r.text()).trim() === 'ok', 'healthz body != "ok"');
  },
  'EC-2': async ({ port }) => {
    const r = await fetch(`http://127.0.0.1:${port}/`);
    assert(r.status === 200, `GET / status ${r.status} != 200`);
    assert((await r.text()).includes('id="app"'), 'index.html missing marker id="app"');
  },
  'EC-3': async ({ port }) => {
    const a = client(port); await a.open(); a.send({ type: 'join', room: 'ec3' });
    const j = await a.waitFor((m) => m.type === 'joined');
    assert(j.role === 'callee', `first joiner role ${j.role} != callee`);
    assert(j.peers === 1, `peers ${j.peers} != 1`);
    a.close();
  },
  'EC-4': async ({ port }) => {
    const a = client(port); await a.open(); a.send({ type: 'join', room: 'ec4' });
    await a.waitFor((m) => m.type === 'joined');
    const b = client(port); await b.open(); b.send({ type: 'join', room: 'ec4' });
    const jb = await b.waitFor((m) => m.type === 'joined');
    assert(jb.role === 'caller', `second joiner role ${jb.role} != caller`);
    await a.waitFor((m) => m.type === 'peer-ready');   // both notified
    await b.waitFor((m) => m.type === 'peer-ready');
    a.close(); b.close();
  },
  'EC-5': async ({ port }) => {
    const { a, b } = await pair(port, 'ec5');
    a.send({ type: 'signal', payload: { sdp: 'OFFER-XYZ' } });
    const s = await b.waitFor((m) => m.type === 'signal');
    assert(deepEq(s.payload, { sdp: 'OFFER-XYZ' }), 'relayed payload mismatch');
    await sleep(300);
    assert(!a.sawAny((m) => m.type === 'signal'), 'signal was echoed back to sender');
    a.close(); b.close();
  },
  'EC-6': async ({ port }) => {
    const { a, b } = await pair(port, 'ec6');
    a.close();
    await b.waitFor((m) => m.type === 'peer-left');
    b.close();
  },
  'EC-7': async ({ port }) => {
    const { a, b } = await pair(port, 'ec7');
    const c = client(port); await c.open(); c.send({ type: 'join', room: 'ec7' });
    await c.waitFor((m) => m.type === 'room-full');
    await sleep(200);
    assert(!c.sawAny((m) => m.type === 'joined'), 'rejected client was still admitted (got joined)');
    a.close(); b.close(); c.close();
  },
};

async function main() {
  const want = process.argv[2];
  const ids = want ? [want] : Object.keys(CHECKS);
  if (want && !CHECKS[want]) { console.error(`unknown row ${want}`); process.exit(2); }

  const srv = await startServer();
  let failed = 0;
  for (const id of ids) {
    try {
      await CHECKS[id]({ port: srv.port });
      console.log(`  PASS ${id}`);
    } catch (e) {
      failed++;
      console.log(`  FAIL ${id} — ${e.message}`);
    }
  }
  await srv.close();
  console.log(failed === 0 ? `\nGATE GREEN — ${ids.length}/${ids.length} rows pass`
                           : `\nGATE RED — ${failed}/${ids.length} rows failing`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((e) => { console.error('harness error:', e); process.exit(1); });
