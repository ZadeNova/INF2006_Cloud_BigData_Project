# VoiceBox

Bold, opinionated, magazine-style.

## Overview

VoiceBox is a high-contrast editorial design system for opinion blogs and cultural commentary sites. It channels the energy of print magazines — massive headlines, stark black-and-white foundations, and a single aggressive red accent that punctuates like an exclamation mark. The density is intentionally mixed: bold, oversized headers create dramatic entries while compact body text maintains readability for long-form argument. Every element is flat and sharp, with borders doing all the structural work.

## Colors

### Brand Palette

| Token     | Hex       | Role                                         |
|-----------|-----------|-----------------------------------------------|
| Primary   | `#0A0A0A` | Black — headings, primary UI, dominant tone    |
| Secondary | `#EF4444` | Red — accent, emphasis, editorial highlights   |
| Tertiary  | `#FAFAFA` | White — backgrounds, inverse text              |

### Surface Palette

| Token          | Hex       | Role                                    |
|----------------|-----------|------------------------------------------|
| Background     | `#FAFAFA` | Pure white page background               |
| Surface        | `#F5F5F5` | Card backgrounds, aside blocks           |
| Surface Raised | `#E5E5E5` | Hover backgrounds, pull-quote blocks     |

### Content Palette

| Token          | Hex       | Role                                  |
|----------------|-----------|---------------------------------------|
| Text Primary   | `#0A0A0A` | Headlines, body copy                  |
| Text Secondary | `#525252` | Bylines, datelines, secondary prose   |
| Text Tertiary  | `#A3A3A3` | Placeholders, disabled text           |

### Border Palette

| Token         | Hex       |
|---------------|-----------|
| Border Subtle | `#E5E5E5` |
| Border Medium | `#D4D4D4` |
| Border Strong | `#0A0A0A` |

### Semantic Colors

| Token   | Hex       |
|---------|-----------|
| Success | `#16A34A` |
| Warning | `#CA8A04` |
| Error   | `#EF4444` |
| Info    | `#0A0A0A` |

## Typography

### Font Stack

| Role             | Font                                                        |
|------------------|-------------------------------------------------------------|
| Display/Headings | Archivo Black, Impact, 'Arial Black', sans-serif            |
| UI/Body          | Work Sans, -apple-system, 'Segoe UI', Helvetica, sans-serif |
| Mono/Code        | Space Mono, 'Courier New', Consolas, monospace              |

### Type Scale

| Level        | Font          | Size   | Weight | Line Height | Letter Spacing | Usage                         |
|--------------|---------------|--------|--------|-------------|----------------|-------------------------------|
| Display      | Archivo Black | 56px   | 400    | 1.05        | -0.03em        | Hero opinion headlines        |
| Headline     | Archivo Black | 38px   | 400    | 1.1         | -0.02em        | Article titles                |
| Subhead      | Archivo Black | 24px   | 400    | 1.2         | -0.01em        | Section breaks                |
| Body Large   | Work Sans     | 20px   | 400    | 1.65        | 0              | Lede paragraphs, pull quotes  |
| Body         | Work Sans     | 16px   | 400    | 1.7         | 0              | Default article text          |
| Body Small   | Work Sans     | 14px   | 400    | 1.6         | 0              | Sidebar, related links        |
| Caption      | Work Sans     | 12px   | 500    | 1.5         | 0.01em         | Photo credits, timestamps     |
| Overline     | Work Sans     | 11px   | 700    | 1.4         | 0.12em         | Section labels, rubrics       |
| Code         | Space Mono    | 14px   | 400    | 1.6         | 0              | Inline code, embeds           |

## Spacing

| Property                    | Value   |
|-----------------------------|---------|
| Base unit                   | 8px     |
| Scale                       | 4, 8, 16, 24, 32, 48, 64, 96 |
| Component padding — small   | 8px     |
| Component padding — medium  | 16px    |
| Component padding — large   | 32px    |
| Section spacing — mobile    | 48px    |
| Section spacing — tablet    | 64px    |
| Section spacing — desktop   | 96px    |

## Border Radius

| Token  | Value | Usage                               |
|--------|-------|-------------------------------------|
| None   | 0px   | All elements — default              |
| Small  | 0px   | Not used                            |
| Medium | 0px   | Not used                            |
| Large  | 0px   | Not used                            |
| XL     | 0px   | Not used                            |
| Full   | 9999px| Author avatar thumbnails only       |

Sharp, square edges are mandatory across every component. The magazine aesthetic demands geometric precision.

## Shadows

**Philosophy:** VoiceBox is completely flat with borders. Hierarchy comes from weight, scale, and black-white contrast — never from elevation.

| Level   | CSS Value | Usage                            |
|---------|-----------|----------------------------------|
| Subtle  | `none`    | —                                |
| Medium  | `none`    | —                                |
| Large   | `none`    | —                                |
| Overlay | `none`    | —                                |

**Special — Focus Ring:** `0 0 0 2px #FAFAFA, 0 0 0 4px #0A0A0A` — stark black focus indicator.

**Special — Red Underline:** A 3px bottom border in `#EF4444` used as a highlight accent on featured articles and active nav items.

## Components

### Buttons

**Primary**
- Background: `#0A0A0A`
- Text: `#FAFAFA`
- Border: `2px solid #0A0A0A`
- Padding: 10px 24px
- Font: Work Sans, 14px, weight 700, uppercase
- Letter spacing: 0.06em
- Radius: 0px
- Hover: Background `#EF4444`, border `#EF4444`
- Active: Background `#DC2626`, border `#DC2626`

**Secondary**
- Background: transparent
- Text: `#0A0A0A`
- Border: `2px solid #0A0A0A`
- Padding: 10px 24px
- Font: Work Sans, 14px, weight 700, uppercase
- Letter spacing: 0.06em
- Radius: 0px
- Hover: Background `#0A0A0A`, text `#FAFAFA`
- Active: Background `#262626`

**Ghost**
- Background: transparent
- Text: `#0A0A0A`
- Border: none
- Padding: 10px 24px
- Font: Work Sans, 14px, weight 700, uppercase
- Letter spacing: 0.06em
- Radius: 0px
- Hover: text `#EF4444`
- Active: text `#DC2626`

**Destructive**
- Background: `#EF4444`
- Text: `#FAFAFA`
- Border: `2px solid #EF4444`
- Padding: 10px 24px
- Font: Work Sans, 14px, weight 700, uppercase
- Letter spacing: 0.06em
- Radius: 0px
- Hover: Background `#DC2626`, border `#DC2626`
- Active: Background `#B91C1C`, border `#B91C1C`

**Sizes:** Small 6px 16px / 12px, Medium 10px 24px / 14px, Large 14px 32px / 16px

**Disabled:** Opacity 0.35, cursor not-allowed, no hover transition.

### Cards

**Default**
- Background: `#FAFAFA`
- Border: `2px solid #E5E5E5`
- Radius: 0px
- Padding: 24px
- Shadow: none
- Hover: Border `#0A0A0A`

**Elevated**
- Background: `#FAFAFA`
- Border-top: `4px solid #EF4444`
- Border-left/right/bottom: `2px solid #E5E5E5`
- Radius: 0px
- Padding: 24px
- Shadow: none

### Inputs

**Text Input**
- Height: 44px
- Background: `#FAFAFA`
- Border: `2px solid #D4D4D4`
- Radius: 0px
- Padding: 8px 14px
- Font: Work Sans, 14px, weight 400
- Text color: `#0A0A0A`
- Placeholder color: `#A3A3A3`
- Focus: Border `#0A0A0A`, ring `0 0 0 2px #FAFAFA, 0 0 0 4px #0A0A0A`
- Error: Border `#EF4444`
- Disabled: Background `#F5F5F5`, opacity 0.5

**Label:** Work Sans, 12px, weight 700, color `#0A0A0A`, uppercase, letter-spacing 0.06em, margin-bottom 6px.

**Helper Text:** Work Sans, 12px, weight 400, color `#525252`, margin-top 4px. Error helper color `#EF4444`.

### Chips

**Filter Chip**
- Background: transparent
- Border: `2px solid #D4D4D4`
- Radius: 0px
- Padding: 4px 14px
- Font: Work Sans, 12px, weight 700, uppercase
- Letter spacing: 0.04em
- Text: `#525252`
- Selected: Background `#0A0A0A`, text `#FAFAFA`, border `#0A0A0A`

**Status Chip**
- Padding: 4px 12px
- Font: Work Sans, 11px, weight 700, uppercase
- Letter spacing: 0.06em
- Radius: 0px
- Success: Background `#F0FDF4`, text `#16A34A`, border `2px solid #16A34A`
- Warning: Background `#FEFCE8`, text `#CA8A04`, border `2px solid #CA8A04`
- Error: Background `#FEF2F2`, text `#EF4444`, border `2px solid #EF4444`

### Lists

**Default List Item**
- Padding: 14px 0
- Border bottom: `1px solid #E5E5E5`
- Font: Work Sans, 16px, weight 400
- Text: `#0A0A0A`
- Secondary text: `#A3A3A3`, 12px
- Hover: Background `#F5F5F5`
- Active: Background `#E5E5E5`
- Leading element: 20px icon, color `#0A0A0A`

### Checkboxes

- Size: 18px
- Border: `2px solid #0A0A0A`
- Radius: 0px
- Background: `#FAFAFA`
- Checked: Background `#0A0A0A`, border `#0A0A0A`, checkmark `#FAFAFA`
- Indeterminate: Background `#0A0A0A`, dash `#FAFAFA`
- Hover: Background `#F5F5F5`
- Focus: Ring `0 0 0 2px #FAFAFA, 0 0 0 4px #0A0A0A`
- Disabled: Opacity 0.35
- Label: Work Sans, 14px, weight 400, margin-left 10px

### Radio Buttons

- Size: 18px
- Border: `2px solid #0A0A0A`
- Radius: 9999px
- Background: `#FAFAFA`
- Selected: Border `#0A0A0A`, inner dot `#0A0A0A` (8px)
- Hover: Background `#F5F5F5`
- Focus: Ring `0 0 0 2px #FAFAFA, 0 0 0 4px #0A0A0A`
- Disabled: Opacity 0.35
- Label: Work Sans, 14px, weight 400, margin-left 10px

### Tooltips

- Background: `#0A0A0A`
- Text: `#FAFAFA`
- Font: Work Sans, 12px, weight 600
- Padding: 8px 14px
- Radius: 0px
- Max width: 220px
- Arrow: 6px, same background
- Delay: 250ms enter, 0ms leave
- Shadow: none

## Do's and Don'ts

1. **Do** make headlines massive and unapologetic — Archivo Black at 38px+ demands attention.
2. **Don't** use red (`#EF4444`) for more than one element per viewport — it is a scalpel, not a paintbrush.
3. **Do** use thick 2px borders for interactive elements to maintain the editorial weight.
4. **Don't** introduce rounded corners or soft shadows — VoiceBox is angular and assertive.
5. **Do** use pull quotes styled with a left `4px solid #EF4444` border and Body Large italic.
6. **Don't** use more than three type sizes on a single page — headline, body, caption is the standard.
7. **Do** set overline category labels in uppercase Work Sans to establish section identity.
8. **Do** maintain stark black-on-white contrast — the palette is intentionally limited.
9. **Don't** add decorative imagery, gradients, or background textures that dilute the typographic focus.
10. **Do** use the red accent on hover states for primary buttons to create a visceral interaction cue.

---

## As built in this project

The sections above are the design system as supplied. This section records where
the 42Factors implementation deviates from it, so this file describes the
delivered system rather than an intention. Implementation lives in
`src/static/css/site.css`, whose `:root` block carries the reasoning inline.

### 1. Status chip labels are one shade darker

| Token | Specified above | As built | Why |
|-------|-----------------|----------|-----|
| Success text | `#16A34A` | `#15803D` | 3.1:1 on its tint fails AA at 11px; 4.79:1 passes |
| Warning text | `#CA8A04` | `#A16207` | 3.0:1 fails; 4.76:1 passes |
| Error text | `#EF4444` | `#B91C1C` | 3.5:1 fails; 5.91:1 passes |

The 2px borders and tinted backgrounds keep the specified values. Only the label
text moved, and only because the specified pairs fail WCAG AA.

### 2. Red is a fill, a rule and a mark, never small text

`#EF4444` reaches only **3.61:1** on `#FAFAFA`. That is enough for a border, a
rule, a fill or large text, and not enough for a word. Red that has to be read
steps down to `#B91C1C` (6.20:1), held as `--color-red-ink`.

### 3. Dark mode is derived, not specified

This system defines no dark palette, but the build ships a theme toggle. Dark
mode is the straight inversion a black-and-white system inverts to: ink and
ground swap, the red keeps its hue. On `#0A0A0A` the red reaches 5.26:1, so
there it may be text as well as a rule. Always-dark bands stay dark rather than
inverting to paper, one step below the page ground.

### 4. Red placement was extended past one element per viewport

Rule 2 of the Do's and Don'ts caps red at one element per viewport. At the
project owner's request the accent was extended to eleven placements, each a
rule, a mark or a state and never a decorative wash: primary-button hover (rule
10 above), brand mark, cart badge, section overlines, active-nav underline,
order-summary top rule, callout and error left rules, current checkout step,
footer wordmark rule, destructive hover, and text selection.

Still not red: focus rings (rule above: stark black), success and completed
states, low stock, and product category overlines.

### 5. Motion

Not covered above, so this is the specification. Motion matches the surfaces:
flat and square means **crisp and mechanical, never organic**. No springs, no
bounce, no blur-softened crossfades, no stagger.

#### Easing and duration

| Token | Value | Use |
|-------|-------|-----|
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | anything entering or leaving |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | anything moving on screen |
| `--dur-press` | `120ms` | press feedback; must feel instant |
| `--dur-fast` | `160ms` | hover, state marks, icon swaps |
| `--dur-enter` | `220ms` | something arriving on screen |

`ease-in` is never used. It delays the first movement, which is the moment the
viewer is watching, so it reads as sluggish at any duration. The browser
defaults (`ease`, `ease-out`) are too weak to read as intentional; use the
tokens above.

Nothing animates from `scale(0)`. Things that shrink to nothing read as
appearing out of nowhere; press states go to `0.95`–`0.97`.

#### What does not animate

Anything seen tens or hundreds of times a day should lose its animation. Four
standing refusals:

1. **Page transitions.** Every navigation is a full document load, so an enter
   animation would delay content on the highest-frequency interaction there is.
2. **The product grid.** Stagger is decorative and the catalogue is the most
   visited page.
3. **Stat tile count-ups.** An operator opens the statistics page repeatedly;
   counting up delays the number they came for.
4. **Theme toggle spin.** A toggle is a state switch, not an event. The icons
   cross-fade only because a `display` swap is jarring.

#### What animates, and the purpose it serves

Every animation names a purpose: feedback, state indication, spatial
consistency, or preventing a jarring change. If none applies, it does not ship.

| What | Purpose | Spec |
|------|---------|------|
| Button press | feedback | `scale(0.97)`, `--dur-press` |
| Stepper and icon-button press | feedback | `scale(0.95)`, `--dur-press` |
| Nav underline | state indication | `scaleX` from the left edge, `--dur-fast` |
| Card and row hover | feedback | border colour only, `--dur-fast` |
| Work in flight | preventing a jarring change | opacity to `0.55`, `--dur-fast` |
| Fragment arriving | preventing a jarring change | `@starting-style`, opacity + 4px rise, `--dur-enter` |
| A figure that just changed | state indication | inverts instantly, releases over `420ms` |
| Messages and alerts | preventing a jarring change | `@starting-style`, opacity + rise |
| Theme icon swap | preventing a jarring change | cross-fade, `--dur-fast` |
| Skip link | spatial consistency | `translateY`, `--dur-fast` |

The changed-figure mark is the one asymmetric case, and the pattern generalises:
**slow where the viewer is deciding, fast where the system is responding.** It
snaps to inverted with `transition-duration: 0ms`, then releases over 420ms, so
the answer is immediate and the explanation lingers. It is a transition rather
than a keyframe, so repeated rapid changes retarget smoothly instead of
restarting from zero. Use transitions, not keyframes, for anything that can be
triggered in bursts.

#### Reduced motion

`prefers-reduced-motion: reduce` means fewer and gentler animations, not none.
Opacity and colour changes carry meaning — what is in flight, what just changed
— and are kept at `--dur-fast`. Everything that **moves** is removed:
`transition-property` is restricted to `opacity, background-color, color,
border-color, fill, stroke`, and transforms are set to `none`.

#### Touch

Hover effects are neutralised under `(hover: none)`. A tap triggers hover on a
touch device and the state then sticks, which is worse than no hover at all.

### 6. Where each value lives in the CSS

Token names follow the palette tables above, so a name here can be found in
`src/static/css/site.css`. Change a token in its `:root` block and the whole
site follows; the rules underneath hold no literal colours.

| Table above | CSS token | Light | Dark |
|---|---|---|---|
| Primary | `--color-primary` | `#0A0A0A` | `#FAFAFA` |
| Secondary | `--color-secondary` | `#EF4444` | `#EF4444` |
| Tertiary | `--color-tertiary` | `#FAFAFA` | `#0A0A0A` |
| Background | `--color-background` | `#FAFAFA` | `#0A0A0A` |
| Surface | `--color-surface` | `#FAFAFA` | `#141414` |
| Surface Raised | `--color-surface-raised` | `#F5F5F5` | `#1C1C1C` |
| Text Primary | `--color-text-primary` | `#0A0A0A` | `#FAFAFA` |
| Text Secondary | `--color-text-secondary` | `#525252` | `#A3A3A3` |
| Border Subtle | `--color-border-subtle` | `#E5E5E5` | `#2E2E2E` |
| Border Medium | `--color-border-medium` | `#D4D4D4` | `#3D3D3D` |
| Border Strong | `--color-border-strong` | `#0A0A0A` | `#FAFAFA` |
| Success / Warning / Error | `--color-success` / `--color-warning` / `--color-error` | see section 1 | lifted for the dark ground |

Light `Surface` equals `Background` on purpose: this system separates a card
from the page with a 2px border, not a fill. They diverge in dark mode.

Two extra tokens exist because the palette collapses so far that one name
cannot serve two jobs:

- `--color-secondary-ink` (`#B91C1C`) - red where it has to be read, per
  section 2 above.
- `--on-action` - ink on the primary button. It is not `--band-ink`, because
  the button and an always-dark band invert in opposite directions.

Role tokens (`--band-fill`, `--action-fill`, `--focus-inner`, and so on) sit
below the palette in the same block and are built from these values.

### 7. Attribution

- **Typefaces**: Archivo Black, Work Sans and Space Mono, all SIL Open Font
  License, loaded from Google Fonts. Pixelify Sans (SIL Open Font License) sets
  only the "67" brand mark, loaded from Google Fonts as a two-glyph subset.
- **Icons**: Phosphor Icons regular weight, MIT, vendored as one SVG sprite at
  `src/static/img/icons.svg` with the licence in the file header.
- **This design system**: added to the repository as a Starbucks-inspired
  reference by Lim Chee Long on 11 September 2026 (commit `c7ed9d1`) and replaced
  by this VoiceBox version by Jun Keat Lim on 23 September 2026 (commit
  `d147c9d`). The VoiceBox source was recovered on 11 October 2026:
  [VoiceBox v1 by Chef (@chef)](https://designmd.ai/chef/voicebox), published
  under the MIT License. All 287 lines of the supplied reference above match
  the upstream download after normalising line endings and surrounding
  whitespace. The "As built in this project" section records our adaptations.
  See [licence text and verification details](docs/licenses/voicebox-MIT.txt)
  and [AI_USE_DECLARATION.md](AI_USE_DECLARATION.md).
