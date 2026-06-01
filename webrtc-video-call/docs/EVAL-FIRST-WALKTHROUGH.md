# Eval-First Walkthrough — how the GSD spine built this app

This app exists to demonstrate one claim: **AI can generate code, but you still need evals to
confirm it follows the spec and the intent — and those evals should be first-class, authored
early, and *gate* the build.** Here is exactly how that played out, with the real artifacts and
the real red→green evidence.

---

## 1. The spine, applied

```
OBJECTIVE  "two people open the same link and talk, no install"
   │                                            .planning/PROJECT.md
   ▼
REQUIREMENTS  REQ-01..REQ-10, each must map to ≥1 eval
   │                                            .planning/REQUIREMENTS.md
   ▼
ROADMAP  Phase 01 signaling · Phase 02 client · Phase 03 (deferred)
   │                                            .planning/ROADMAP.md
   ▼
per phase:
   SPEC            what the phase delivers      phases/NN/NN-SPEC.md
   EVAL-CONTRACT   how we prove it — LOCKED      phases/NN/NN-EVAL-CONTRACT.md   ← authored BEFORE code
   PLAN            tasks; each carries the         phases/NN/NN-01-PLAN.md
                   contract's rows as <acceptance_criteria>
   EXECUTE         build until the gate is green (eval-first: red → green)
   VERIFY          coverage + weakening + gaming + gate rows  phases/NN/NN-VERIFICATION.md
   │
   ▼
WORK LEDGER  tracks every task + evidence so any session can resume   .planning/LEDGER.md
```

Every box above is a real file in `.planning/`. Open them in order — they read like the story
of the build.

---

## 2. Eval-first in action: the live red→green proof

The git history *is* the proof. Each phase is three commits in a deliberate order:

```
8affe3f  spec+evals(01): signaling spec + LOCKED eval contract + harness   ← evals first (RED)
34e0c84  feat(signaling): phase 01 server — EC-1..EC-7 GREEN               ← code (turns gate GREEN)
3d517f4  chore(ledger): phase 01 flush — signaling complete & verified     ← ledger flush
b770d7a  spec+evals(02): client spec + LOCKED eval contract + harness       ← evals first (RED)
dcf89ed  feat(client): phase 02 web client + media — EC-9/EC-11 GREEN       ← code (turns gate GREEN)
fc4ca1a  chore(ledger): phase 02 flush — web client complete & verified     ← ledger flush
c6475ba  fix(client): register pc handlers via property only                ← later fix, code-only
```

**What "red→green" actually looked like:**

- Phase 01, *before* `server.js` existed, `npm run eval` →
  `ERR_MODULE_NOT_FOUND: server.js` → **GATE RED**. The gate fails when the code is absent —
  proving it's a real discriminator, not a tautology.
- *After* building the server, `npm run eval` → **`GATE GREEN — 7/7 rows pass`**.
- Phase 02, *before* `call-core.js`, `node test/eval-phase2.mjs EC-9` →
  `ERR_MODULE_NOT_FOUND: call-core.js` → **RED**. After building → `PASS EC-9` → **GREEN**.

You can reproduce the green at any time: `cd server && npm run eval && npm run eval2`.

---

## 3. The measurement split (why "evals for all code" is affordable)

Not everything can — or should — be a deterministic test. The contract picks the **cheapest
honest** evaluator per row:

| Row | Requirement | Measurement | How it's checked |
|-----|-------------|-------------|------------------|
| EC-1..EC-7 | signaling (REQ-01..07) | **Code** | `eval-phase1.mjs` drives the real server with WebSocket clients |
| EC-9 | handshake logic (REQ-09) | **Code** | the *pure* `call-core.js` driven in Node with a fake peer connection |
| EC-11 | controls (REQ-10) | **Code** | mute/camera/hangup logic on fake tracks |
| EC-10 | remote video renders | **Code (warn)** | optional headless Chromium fake-media smoke; **skips** if Playwright absent |
| EC-8, U-2 | the felt video call (REQ-08/09/10) | **Human** | manual UAT — a person confirms real pixels + audio (see RUN-AND-TEST §3) |

~80% of the surface is deterministic Code (cheap, fast, objective). The browser handshake —
normally un-testable without a browser — was made Code-gatable by **factoring the state machine
out of the DOM** (`call-core.js`). Only the irreducibly visual experience stays Human. That's
the whole point: deterministic where possible, judge/human only where genuinely necessary.

---

## 4. The honesty mechanisms (why a green gate means something)

A gate that the builder can quietly weaken is theatre. The spine prevents that:

- **Locked contracts.** Each `EVAL-CONTRACT.md` is `status: locked` with a `locked_hash` (a
  sha256 of its rows). Phase 01 = `4dce1263…`, Phase 02 = `c0aa6452…`. Verify-time recomputes
  the hash with the *same* command; a drifted hash without an explicit re-lock = a flagged
  weakening. (Recompute now: see `.planning/phases/*/*-VERIFICATION.md`.)
- **Coverage gate (intent ⇄ eval).** Every `REQ-NN` must map to ≥1 row, and every row to a real
  REQ. This catches *intent with no eval* — e.g. REQ-05 (ICE relay) is explicitly covered by
  EC-5 alongside REQ-04, so nothing in the spec is left unproven.
- **Anti-gaming, two-commit.** The commit that turns a gate green must **not** touch the eval
  file (otherwise the test was bent to the output). Proof:
  `git show 34e0c84 --stat` (Phase 01 green) and `git show dcf89ed --stat` (Phase 02 green)
  list only product code — **no `eval-phase*.mjs`**. Evals were committed *red, first*, in a
  separate commit.

---

## 5. The work ledger + a live handoff

`.planning/LEDGER.md` is the always-warm, sub-task-granular record: per task `status`,
`evidence` (commit SHA + passing eval ids), and a HEAD that always says what to do next. It is
the single thing a fresh session reads to resume.

This was not hypothetical here: **Phase 02 was built by a different session that started with no
prior context** — it read `LEDGER.md` (which said "Phase 01 done; next: Phase 02"), authored and
locked the Phase 02 contract, built the client eval-first, and flushed the ledger. The handoff
was the ledger, and it worked. (See the Decision Log at the bottom of `LEDGER.md`.)

That property — *state lives in the durable ledger, not in any one session's context* — is what
lets this scale past a single AI context window.

---

## 6. Where the framework concepts live (quick map)

| Spine concept | In this app |
|---------------|-------------|
| Eval contract (locked, spec-time) | `.planning/phases/*/*-EVAL-CONTRACT.md` |
| Planner emits rows as acceptance_criteria | `.planning/phases/*/*-01-PLAN.md` (tasks carry `<eval_rows>` + the row commands) |
| Executor's hard gate (red→green) | `npm run eval` / `npm run eval2`; per-row `node test/eval-*.mjs EC-N` |
| Coverage + weakening + gaming verdict | `.planning/phases/*/*-VERIFICATION.md` |
| Always-warm work ledger | `.planning/LEDGER.md` |
| Measurement split (Code/Judge/Human) | the contract `measurement` column |
| Deferred-but-documented scope | Phase 03 in `ROADMAP.md` (TURN/TLS/deploy) |

---

## 7. Continue the build (Phase 03)
The roadmap's next phase is production hardening: a **TURN** relay (coturn) for symmetric NAT,
**TLS/`wss`**, deployment, reconnection/backoff, and basic abuse limits. To do it the same way:
author `03-SPEC.md` + a locked `03-EVAL-CONTRACT.md` (e.g. a Code row that the server negotiates
`wss`, a row that a forced-relay call still connects via a test TURN server), then build
eval-first. `LEDGER.md`'s `next_action` already points here.
