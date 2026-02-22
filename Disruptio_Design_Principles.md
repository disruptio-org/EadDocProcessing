# Disruptio — Design Principles & Requirements (derived from disruptio.org)

> Goal: reproduce the *feel* and operating principles of the Disruptio website across sites, presentations, and apps: pragmatic, execution-driven, clear, and premium-with-restraint.

## 1) Brand vibe (what it should feel like)
- **Pragmatic tech/consulting**: “menos buzzwords, mais execução”.
- **Operational clarity** over marketing fluff.
- **Confident + minimal**: strong statements, very little decoration.
- **Systematic**: everything aligned to a grid; repeatable components.

## 2) Layout system
- **Whitespace-first**: generous margins/padding; content never feels cramped.
- **Clear sectioning**: distinct horizontal bands/sections with consistent spacing.
- **Two-column hero** pattern:
  - Left: headline + short subcopy + CTAs
  - Right: simple diagram/illustration
- **Card grids** for services/process/audience:
  - 3-up cards on desktop
  - consistent card height, internal padding, and alignment
- **Consistent vertical rhythm**:
  - Section title → short lead → content (cards/list/quote)
  - spacing is predictable (think 8pt grid).

## 3) Typography principles
- **Hierarchy is the primary design tool** (more than color).
- **Headlines are bold and condensed in meaning**:
  - short, punchy, stacked lines
  - frequent use of **periods** to create cadence (e.g., “MENOS X. MAIS Y.”)
- **Body text is secondary**:
  - lighter color/weight than headings
  - short paragraphs, easy scan
- **Uppercase section headers** used as anchors (e.g., “COMO TRABALHAMOS”).

### Practical type scale (recommended)
- H1 (hero): 56–80px, bold/extra-bold, tight line-height
- H2 (section): 32–40px, bold
- H3 (card titles): 18–22px, bold
- Body: 14–16px, regular
- Caption/meta: 12–13px

## 4) Color & contrast
- **Mostly neutral**: light background with dark text.
- **Single accent color (red)** used for:
  - Primary CTA buttons
  - Key emphasis words inside a headline
  - Small UI highlights (step numbers, subtle dividers)
- **Black/dark band** used for strong CTA section near the bottom.
- Avoid multi-color palettes. Keep it **one accent** + neutrals.

### Palette guidance (approximate, to recreate the feel)
- Background: warm white / off-white
- Text: near-black
- Secondary text: mid-gray
- Surfaces/cards: very light gray
- Accent: strong red
- Dividers/borders: light gray

## 5) Visual language / graphics
- **Simple line icons** (thin stroke, minimal fill) inside service/audience cards.
- **Process steps** shown as a sequence with:
  - small numbered squares (accent red)
  - large faint background numerals (01/02/03/04) as subtle texture
- Hero illustration is **diagrammatic**, not “artsy”:
  - before/after concept (e.g., messy → structured)
  - thin lines, minimal shapes

## 6) Components (design requirements)

### Navigation / header
- Minimal top nav with a clear brand mark.
- One dominant CTA in the header (red button): **“Marcar Diagnóstico”**.

### Buttons
- Primary CTA:
  - solid red background
  - uppercase or strong label
  - arrow/chevron optional
- Secondary CTA:
  - neutral/outline style
  - less visual weight than primary

### Cards
- Light-gray surface
- subtle border or no border; rely on spacing
- icon → title → short description → small list or link (“SABER MAIS”)

### Quote/testimonial block
- Dark card on light section
- Large quote marks not needed; keep it simple
- Name/role small and subdued

### Section CTA band
- Dark full-width band
- Big headline in white
- Single prominent red button

### Footer
- Minimal columns: services, company, contact
- very light hierarchy; nothing flashy

## 7) Copy/UX patterns (this matters for “same look”)
- Headlines are **outcome-driven**:
  - “Menos trabalho manual. Mais controlo. Mais crescimento.”
- Subcopy avoids hype; focuses on operational benefits.
- Sections answer:
  - what we do → how we work → expected results → who it’s for → CTA.
- Lists are short and scannable.

## 8) Motion/interaction (optional)
- Subtle hover states on buttons/cards.
- No heavy animations. If used, keep to:
  - fade/translate 8–16px
  - 150–250ms

## 9) Presentation/app translation rules (how to reuse the style)

### For presentations
- Use the same cadence headlines with period breaks.
- Mostly white slides with one accent red.
- Use cards for “services / pillars / steps”.
- Use a single dark “CTA/closing” slide near the end.
- For process slides: step tiles + faint big background numerals.

### For apps/dashboards
- Neutral UI with one accent.
- Card-based layout, strong typography hierarchy.
- Data tables: minimal borders, lots of spacing, clear headers.

## 10) “Do / Don’t” checklist
**Do**
- Use grid + consistent spacing
- Use one accent color sparingly
- Make headings carry the message
- Keep copy short and operational

**Don’t**
- Add gradients, multiple accents, or decorative shapes
- Use long paragraphs
- Use too many icon styles
- Over-animate

---

## Quick build spec (starter tokens)
- Spacing system: 8 / 16 / 24 / 32 / 48 / 64
- Corner radius: 6–10 (cards/buttons)
- Stroke: 1px light gray for dividers
- Icon stroke: 1.5–2px outline icons

## Figma-ready design tokens (copy/paste)

> These are intentionally approximate to match the *Disruptio feel*. Adjust exact hex values after sampling from the live site if needed.

### Color styles
```yaml
color:
  bg:
    base: "#F7F7F5"        # warm off-white
    surface: "#EFEFEC"     # cards
    surface2: "#FFFFFF"    # elevated/clean areas
    darkBand: "#111111"    # closing CTA band
  text:
    primary: "#111111"     # near-black
    secondary: "#6B6F76"   # mid gray
    muted: "#9AA0A6"       # captions
    onDark: "#F5F5F5"      # text on dark
  accent:
    red: "#D73A3A"         # primary action / emphasis
    redDark: "#B92F2F"     # hover/pressed
  stroke:
    subtle: "#D8DBDF"      # hairline dividers
  state:
    success: "#1F9D55"     # optional (tiny checkmarks)
```

### Typography styles
```yaml
type:
  fontFamily: "Inter"  # or any clean grotesk sans
  h1:
    size: 72
    weight: 800
    lineHeight: 0.95
    letterSpacing: -0.02
  h2:
    size: 40
    weight: 800
    lineHeight: 1.05
    letterSpacing: -0.01
  h3:
    size: 22
    weight: 700
    lineHeight: 1.15
  body:
    size: 16
    weight: 400
    lineHeight: 1.5
  small:
    size: 14
    weight: 400
    lineHeight: 1.45
  caption:
    size: 12
    weight: 500
    lineHeight: 1.35
  sectionLabel:
    size: 12
    weight: 700
    uppercase: true
    letterSpacing: 0.08
```

### Spacing & grid
```yaml
layout:
  grid:
    baseUnit: 8
    containerMaxWidth: 1120
    columnsDesktop: 12
    gutter: 24
    margin: 32
  spacing:
    xs: 8
    sm: 16
    md: 24
    lg: 32
    xl: 48
    xxl: 64
```

### Radius, shadows, strokes
```yaml
shape:
  radius:
    button: 8
    card: 10
    pill: 999
  stroke:
    hairline: 1
  shadow:
    card: "0 8 24 0 rgba(17,17,17,0.06)"   # keep very subtle
```

### Buttons (component spec)
```yaml
components:
  buttonPrimary:
    bg: "{color.accent.red}"
    text: "#FFFFFF"
    radius: "{shape.radius.button}"
    paddingX: 20
    paddingY: 12
    hoverBg: "{color.accent.redDark}"
  buttonSecondary:
    bg: "transparent"
    text: "{color.text.primary}"
    stroke: "{color.stroke.subtle}"
    radius: "{shape.radius.button}"
```

### Cards (component spec)
```yaml
components:
  card:
    bg: "{color.bg.surface}"
    radius: "{shape.radius.card}"
    padding: 24
    stroke: "transparent"  # rely on spacing; optional subtle stroke
    iconStrokeWidth: 1.5
```

### Presentation defaults (if using this style for decks)
```yaml
presentation:
  slide:
    size: "1920x1080"
    padding: 80
    bg: "{color.bg.base}"
  sectionSlide:
    bg: "{color.bg.darkBand}"
    titleColor: "{color.text.onDark}"
    accent: "{color.accent.red}"
```
