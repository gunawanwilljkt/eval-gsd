# GSD — How it works & how to use it (presentation)

A 58-slide deck explaining the **GSD (Get Shit Done)** spec-driven framework: what it is,
how the lifecycle works, its key capabilities, the command surface, and **two end-to-end
walkthroughs** — a SaaS app (“TaskFlow”) and a payment gateway (“PayLink”: merchant mobile
app + backend + admin dashboard).

## Files

| File | Use |
|------|-----|
| `gsd-presentation-dark.html`  | **Dark theme** — present on screen / projector. |
| `gsd-presentation-light.html` | **Light theme** — present on screen / bright rooms. |
| `gsd-presentation-print.html` | **No background color** — ink-economical, for printing. |
| `gsd-presentation-print.pdf`  | The print version pre-rendered to PDF (one slide per page). |
| `build_deck.py`               | Generator. All three HTML files are built from this one source. |

All HTML files are **self-contained** (inline CSS/JS, system fonts) — open them directly,
no server or internet required.

## Presenting

Open a theme file in any browser and use:

- `→` / `Space` / `PageDown` — next slide
- `←` / `PageUp` — previous slide
- `Home` / `End` — first / last slide
- Click right third = next, left third = previous

The 1280×720 canvas auto-scales to fill the window. Press `F11` for fullscreen.

## Printing

Use `gsd-presentation-print.html` (or the ready-made `.pdf`). To re-print from the browser:
**File → Print → Landscape**, margins **None**. The print version is **zero-fill** — pure
white with all structure carried by borders and type — so it prints faithfully whether or
not "Background graphics" is enabled, and uses minimal ink. Each slide is forced to its own
page — no blank pages.

## Regenerating / editing

Content and styling live in `build_deck.py`. The three themes differ **only** by a palette
(see the `PALETTES` dict); the markup, layout, and print CSS are identical, so any edit stays
consistent across all three.

```bash
python3 build_deck.py        # rewrites all three HTML files
```

### Overflow check (the layout guarantee)

Every slide is a fixed 1280×720 canvas, so the real risk is content silently overflowing.
The deck ships with a built-in checker — open any file and run in the console:

```js
window.__overflow()          // → []  means every slide fits
```

It returns the 1-based index of any slide whose content (or inner body) exceeds the canvas.
This deck was verified to return `[]` in all three themes. If you add content and a slide
starts to overflow, split it across two slides.
