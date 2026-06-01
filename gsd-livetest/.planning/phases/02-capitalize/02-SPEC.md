# 02-SPEC — capitalize

WHAT phase 02 delivers: an ESM module `src/capitalize.mjs` exporting `capitalize(text)`.

## Behavior
- `capitalize(s)` returns `s` with the **first character upper-cased and the rest lower-cased**.
- Empty-safe: `capitalize("")` returns `""` (no crash).

## Requirements
- REQ-03: `capitalize("hELLO") === "Hello"`
- REQ-04: `capitalize("") === ""`

## Non-goals
No Unicode-locale casing, no word-by-word title case. ASCII, single token.
