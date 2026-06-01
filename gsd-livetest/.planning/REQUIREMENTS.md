# Requirements: slugify-lib

**Defined:** 2026-06-01
**Core Value:** Predictable, dependency-free slug generation.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Slugify

- [ ] **REQ-01**: `slugify("Hello World")` returns `"hello-world"` (lowercase + single hyphen between words).
- [ ] **REQ-02**: `slugify("  A__B--C!  ")` returns `"a-b-c"` (collapse runs of non-alphanumerics to one hyphen, trim whitespace, strip leading/trailing hyphens, strip punctuation).

### Capitalize (Phase 2)

- [x] **REQ-03**: `capitalize("hELLO")` returns `"Hello"` (first character upper, the rest lower).
- [x] **REQ-04**: `capitalize("")` returns `""` (empty-safe; no crash on empty input).

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Unicode transliteration | Trivial target — ASCII only |
| Configurable separator | Single fixed `-` separator |
| CLI / packaging | Library function only |
