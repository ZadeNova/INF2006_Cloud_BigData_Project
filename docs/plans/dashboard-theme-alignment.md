# Dashboard theme alignment (option A)

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step. Follow-up to [batch-06c-dashboard.md](batch-06c-dashboard.md).

## Context

The operator dashboard (`/analytics/`, built on `CL/Analytics`) was written and reviewed against the pre-redesign palette. Branch `erfan/analytics` merges it with the three UIUX commits on `main`, which replaced that palette with the black/white/red VoiceBox theme (square corners, dark mode). The merge is conflict-free and the suite passes (438), but the dashboard's own CSS block (`site.css`, "Analytics dashboard" section, appended after the redesign) still references nine colour tokens the redesign deleted (`--color-spruce`, `--color-mint`, `--color-pine`, `--color-ink-soft`, `--color-accent`, `--color-border`, `--color-ceramic`, `--color-white`, `--color-white-soft`), and `analytics.js` hard-codes the old green chart palette. Unresolved `var()` references make the declaration invalid at computed time, so for example the active range link renders white text on no background.

**The UIUX commits take precedence** (user decision, 24 September 2026). This change edits only the dashboard's own rules and script; it does not touch the redesign's tokens, components, `base.html` or the presentation-only statistics comp.

## Scope (option A)

Make the existing dashboard correct and dark-mode-safe in the new theme. Not a redesign: markup, tests and behaviour are unchanged.

Option B (rebuild the panel around the designer's comp `foundation/statistics.html`) is **not** in scope; it depends on the UIUX owner confirming the comp is meant to replace the dashboard markup, and on whether the backend supplies the comp's "Orders" and "Average order" tiles (unchecked).

## Changes

1. **`src/static/css/site.css`, dashboard block only.** Token mapping, chosen to mirror how the designer's own comp uses each token (`.chip`/`.chip--on`, `.stat-tile`, `.chart__*`):

| Old | New |
|---|---|
| `--color-ink-soft` | `--color-text-secondary` |
| `--color-spruce` as text | `--color-text-primary` |
| `--color-spruce` as fill (hero mark, flagged card) | `--band-fill` with `--band-ink` text |
| active range link | `--action-fill` / `--on-action` (as `.chip--on`) |
| `--color-white`, `--color-white-soft` | `--band-ink` (`--band-ink-soft` is not used here; it was undefined in light mode when this was written and was defined on 24 September) |
| `--color-mint` chips, badges | `--color-surface-raised` |
| `--color-pine` | `--color-success` (fill `--color-success-tint`) |
| `--color-accent` | `--color-secondary-ink` for emphasis, `--color-text-primary` for comparison deltas, `--color-border-strong` for focus outlines |
| `--color-border`, `--color-ceramic` | `--color-border-subtle` |
| `#fff0d1` | `--color-warning-tint` |

   Also: `border-radius: 50%` circles (hero mark, empty icon, note icon, rank badge) become square and the hero mark's rotation is dropped, matching `--card-radius: 0`; the duplicate `.visually-hidden` (already defined earlier in the file) is removed.

2. **`src/static/js/analytics.js`.** Chart colours are read from the CSS custom properties with `getComputedStyle` each time a chart is drawn, replacing the hard-coded green object. Series follow the comp: current line `--color-text-primary`, previous period `--color-text-secondary` dashed, grid `--color-border-subtle`, no smoothing, no rounded bars. A `MutationObserver` on `<html data-theme>` and a `prefers-color-scheme` listener redraw the charts so a theme toggle recolours them.

## Verification

- `docker compose build web` (CSS/JS are copied into the image and `collectstatic` runs at build), then `tests/test_analytics_dashboard.py` and the full suite: markup is unchanged, so no test should change.
- A grep proves no undefined custom property remains in `site.css`, and `collectstatic` accepts the edited files.
- Visual check by the user in light and dark mode at `/analytics/` (JavaScript and appearance are not unit-testable; stated as a limit).

## Not done

Independent review of this change; not claimed. The dashboard's earlier review gate (`reviews/analytics-dashboard.md`) covered the old theme and does not cover appearance under the new one.
