# Mobile & Full-Stack Scaffold + Eval Hooks Reference

Patterns for scaffolding **mobile apps** (React Native, Flutter, native iOS/Android) and
**full-stack vertical slices**, and — the part that matters for this framework — the
**per-platform eval hooks**: the concrete, runnable commands that become an eval contract's
`Code` rows so the executor's existing per-task HARD GATE enforces them. Apply when a phase
targets a mobile platform or a full-stack slice.

> Read alongside @.claude/get-shit-done/references/eval-first.md (the contract + gate it feeds)
> and, for iOS project generation specifics, @.claude/get-shit-done/references/ios-scaffold.md.

---

## The principle: mobile is *more* eval-gatable than it looks

A common excuse is "mobile/UI can't really be tested without a device, so evals don't apply."
That is false for ~80% of the surface. The eval-first **measurement split** holds exactly as it
did for the web app this framework was proven on:

- **Code (deterministic, the ~80%):** typecheck, lint, unit tests, the app **builds**, the JS
  **bundles**, the app **boots in a simulator/emulator**, and **e2e flows pass on a simulator
  with injected/fake inputs**. All of these are commands that exit 0/non-zero — i.e. eval
  contract `Code` rows the executor gates on.
- **Code-warn (skips if the toolchain/device is absent):** simulator/emulator e2e and device
  builds — gate-skip when Xcode/Android SDK/emulator isn't available (`warn` severity, like the
  web app's headless-browser and TLS smokes). Never block CI on a missing emulator.
- **Human (the irreducible):** gesture feel, animation smoothness, real-device performance,
  notification/permission UX, and App/Play **Store review** — `Human` rows carried to UAT.

So a mobile phase authors a normal `EVAL-CONTRACT.md` (template + lock + coverage gate, per
eval-first.md). The only thing platform-specific is *which commands* go in the `command_or_rubric`
column — that is what the tables below supply.

---

## Per-platform eval hooks (drop these into the contract's `Code` rows)

### React Native (Expo or bare)

| Eval (behavior) | `command_or_rubric` | severity |
|-----------------|---------------------|----------|
| Types are sound | `npx tsc --noEmit` | gate |
| Lint clean | `npx eslint . --max-warnings=0` | gate |
| Unit/component tests pass | `npm test -- --ci` (Jest + @testing-library/react-native) | gate |
| JS bundles (no import/runtime-graph errors) | `npx expo export --platform ios --output-dir /tmp/exp` (Expo) **or** `npx react-native bundle --entry-file index.js --platform android --dev false --bundle-output /tmp/b.js` (bare) | gate |
| Native app builds (debug) | Expo: `npx expo prebuild && xcodebuild -workspace ios/App.xcworkspace -scheme App -sdk iphonesimulator build` · Android: `cd android && ./gradlew assembleDebug` | warn (skips if SDK absent) |
| E2E on simulator | `maestro test .maestro/` **or** `detox test -c ios.sim.debug` (after `detox build`) | warn (skips if no sim) |
| Feels right on a real device | manual UAT | **Human** |

Scaffold: `npx create-expo-app@latest App` (managed, fastest path) or
`npx @react-native-community/cli init App` (bare). Prefer **Expo** unless the phase needs a
native module Expo doesn't support — say which in the SPEC.

### Flutter

| Eval (behavior) | `command_or_rubric` | severity |
|-----------------|---------------------|----------|
| Static analysis clean | `flutter analyze` | gate |
| Format check | `dart format --set-exit-if-changed .` | gate |
| Unit + widget tests pass | `flutter test` | gate |
| App builds (debug) | `flutter build apk --debug` (Android) · `flutter build ios --debug --no-codesign` (iOS) | warn (skips if SDK absent) |
| Integration/e2e on device | `flutter test integration_test/` (or `patrol test`) on a booted emulator/simulator | warn (skips if no device) |
| Feels right on a real device | manual UAT | **Human** |

Scaffold: `flutter create app`. Factor business logic out of widgets (the same DOM-free
discipline the web app used for `call-core.js`) so it's unit-gatable without a render surface.

### Native iOS (Swift)

Generate the project with **XcodeGen** per `ios-scaffold.md` (never `Package.swift` executable
targets). Then:

| Eval (behavior) | `command_or_rubric` | severity |
|-----------------|---------------------|----------|
| Project generates | `xcodegen generate` (exit 0, `.xcodeproj` exists) | gate |
| Builds for simulator | `xcodebuild -project App.xcodeproj -scheme App -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' build` | gate (if Xcode present; else warn) |
| Unit + UI tests pass | `xcodebuild test -project App.xcodeproj -scheme App -destination 'platform=iOS Simulator,name=iPhone 15'` (pipe to `xcbeautify`) | warn (skips if no Xcode/sim) |
| Feels right / store review | manual UAT | **Human** |

### Native Android (Kotlin)

| Eval (behavior) | `command_or_rubric` | severity |
|-----------------|---------------------|----------|
| Compiles + lint | `./gradlew lintDebug` | gate |
| Unit tests pass | `./gradlew testDebugUnitTest` | gate |
| App assembles (debug) | `./gradlew assembleDebug` | gate (if SDK present; else warn) |
| Instrumented e2e | `./gradlew connectedDebugAndroidTest` (booted emulator) | warn (skips if no emulator) |
| Feels right / store review | manual UAT | **Human** |

---

## Full-stack vertical slices

For a full-stack phase (the walking-skeleton style — see `skeleton-template.md`), the eval
contract's `Code` rows span the whole stack so "the slice works end-to-end" is gated, not
assumed:

- **Backend:** `<server> test` + a real endpoint contract row (`curl … | assert status+schema`)
  + `migration applies on a clean DB` — exactly the Phase-01 signaling pattern from the proven
  web app.
- **Frontend:** typecheck + build + the client logic factored into pure, Node-testable modules
  (the `call-core.js` pattern) so negotiation/state logic is `Code`-gated.
- **Cross-stack e2e:** one `warn` smoke that boots both and drives the slice (Playwright for web,
  Maestro/Detox/`integration_test` for mobile) — skips if the runner/device is absent.
- **The felt experience:** one `Human` row.

This makes a full-stack slice's contract read like: *N deterministic Code gates + 1–2 skip-able
e2e smokes + 1 Human UAT* — the same shape, and the same `npm test`-style single gate command,
that the framework was dogfooded on.

---

## Pitfalls (so the gates stay honest)
- **Don't fake a simulator gate green when no simulator ran.** Gate-skip (exit 0, `warn`) when
  the toolchain/device is absent — and `log()`/print the skip so "covered" never silently means
  "skipped." (This is the EC-10/EC-17 discipline from the web app.)
- **Device signing / store submission is `Human`**, never a `Code` gate (it needs real
  credentials + human review). Put it in the contract as a Human/UAT row.
- **Factor logic out of the view layer** (RN component / Flutter widget / SwiftUI View) so the
  ~80% deterministic gates don't need a render surface — mirrors `call-core.js`.
- **Pin the simulator/emulator + SDK versions** in the SPEC so the build/e2e commands are
  reproducible across sessions (a fresh session resuming from the ledger must run the same gate).

---

## How a planner/spec-phase uses this
1. SPEC names the platform + the simulator/SDK versions.
2. The eval contract (eval-first.md §2.1) is authored with `Code` rows drawn from the table
   above for that platform (+ the coverage gate, + lock).
3. `gsd-planner` emits each `gate`/`Code` row as a task `<acceptance_criteria>` (W1) → the
   executor's existing HARD GATE runs the build/test commands → red→green is progress.
4. `warn` simulator/device smokes skip gracefully off-CI; `Human` rows go to `{NN}-UAT.md`.
