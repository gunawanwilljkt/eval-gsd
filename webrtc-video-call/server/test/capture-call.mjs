// capture-call.mjs — visual evidence for EC-10.
// Reuses the EC-10 flow (two Chromium contexts, fake camera, same room) but waits until BOTH
// the local AND the remote <video> are rendering pixels on BOTH peers, then saves a screenshot
// of each peer's page. The fake device paints a synthetic moving image, so a working call shows
// video in both the "You" and "Peer" tiles.
//
//   npm run capture        (writes docs/screenshots/peerA.png + peerB.png)

import { chromium } from 'playwright';
import { createServer } from '../server.js';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, '..', '..', 'docs', 'screenshots');
mkdirSync(OUT, { recursive: true });

const bothVideosLive = () => {
  const l = document.querySelector('#localVideo');
  const r = document.querySelector('#remoteVideo');
  return !!(l && r && l.videoWidth > 0 && r.videoWidth > 0);
};

const browser = await chromium.launch({
  args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
         '--autoplay-policy=no-user-gesture-required'],
});

const { httpServer } = createServer();
const srv = await new Promise((res) => httpServer.listen(0, '127.0.0.1', () => res(httpServer)));
const { port } = srv.address();
const url = `http://127.0.0.1:${port}/`;
const room = `shots-${Date.now()}`;

try {
  const mkPeer = async (label) => {
    const ctx = await browser.newContext({
      permissions: ['camera', 'microphone'],
      viewport: { width: 960, height: 720 },
    });
    const page = await ctx.newPage();
    await page.goto(url);
    await page.fill('#room', room);
    await page.click('#join');
    return { label, ctx, page };
  };

  const a = await mkPeer('peerA');
  const b = await mkPeer('peerB');

  // Wait until BOTH peers show both tiles live (local preview + remote stream).
  await a.page.waitForFunction(bothVideosLive, { timeout: 20000 });
  await b.page.waitForFunction(bothVideosLive, { timeout: 20000 });

  // Let a few frames of the synthetic stream actually paint before capturing.
  await a.page.waitForTimeout(1500);

  const fileA = path.join(OUT, 'peerA.png');
  const fileB = path.join(OUT, 'peerB.png');
  await a.page.screenshot({ path: fileA });
  await b.page.screenshot({ path: fileB });

  // Report the dimensions we captured, as proof the videos were live (not blank).
  const dims = (p) => p.evaluate(() => ({
    local: document.querySelector('#localVideo').videoWidth + 'x' + document.querySelector('#localVideo').videoHeight,
    remote: document.querySelector('#remoteVideo').videoWidth + 'x' + document.querySelector('#remoteVideo').videoHeight,
    status: document.querySelector('#status')?.textContent?.trim(),
  }));
  console.log('peerA video dims:', await dims(a.page));
  console.log('peerB video dims:', await dims(b.page));
  console.log('saved:', fileA);
  console.log('saved:', fileB);
} finally {
  try { await browser.close(); } catch {}
  try { await new Promise((r) => srv.close(r)); } catch {}
}
