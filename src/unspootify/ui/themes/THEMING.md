# Looks (themes)

Every look is one CSS file in this folder. `../base.css` owns the layout; a look only
restyles it. Today: `phosphor.css`, `jukebox.css`.

## Contract

A look file must:

- Scope every rule under `body[data-theme="<name>"]` (or `[data-theme="<name>"] …`).
- Define a swatch for the Settings picker: `.sw-<name> { … }` (unscoped, so it always shows in its own style).
- Work offline: no web fonts, no remote images. Use system fonts and CSS only.
- Not change layout: no edits to `grid-template-*`, `display` of regions, or element order.
  Spacing, borders, colors, fonts, shadows, and hiding decoration (`.logo`, `.wordmark`) are fine.
- Keep text readable (contrast) and keep the status colors distinct.

### What to style

| Area | Classes |
|---|---|
| Window | `body`, `.app` (`--gap` sets spacing) |
| Top bar | `.masthead`, `.logo` (ASCII), `.wordmark` (text logo, hidden by default), `.lcd`, `.lcd-line1`, `.lcd-line2`, `.lcd-bar span`, `.icon-btn` |
| Boxes | `.panel`, `.panel > h2`, `.sidebar`, `.tracks`, `.terminal` |
| Inputs | `input[type=text]`, `input[type=password]`, `.field > span`, `.hint` |
| Buttons | `.btn`, `.btn.small`, `.btn.tiny`, `.btn.primary-soft`, `.btn.go` (+ `.running`), `.btn.default`, `.advanced-btn` |
| Choices | `.seg button` (+ `.on`), `.toggle .box` (checked: `.toggle input:checked + .box`) |
| Playlists | `.playlist-list li` (+ `.sel`), `.pl-name`, `.pl-count`, `.pl-meter span` |
| Songs | `.track-row`, `.track-row.header`, `.track-rows .track-row.active`, `.c-num`, `.c-fmt`, `.bar i`, `.asciibar` |
| Status | `.st-queued`, `.st-searching`, `.st-downloading`, `.st-done`, `.st-skipped`, `.st-failed` |
| Details | `.log`, `.log b`, `.splitter span` |
| Dialogs | `.sheet-backdrop`, `.sheet`, `.sheet-title`, `.group`, `.group legend`, `.look-card` (+ `.on`) |

## Make your own look (future feature)

Planned: drop a `.css` file into the app's "Looks" folder and it appears in Settings.
The prompt below is what the app will offer to copy into any AI chat:

```
Write a CSS theme file for the unSpootify app.
Theme name: <one word, lowercase>
The look I want: <describe it: colors, era, mood, references>

Rules:
- Scope every rule under body[data-theme="<name>"].
- Add an unscoped .sw-<name> swatch (a small preview tile).
- Only restyle: don't change grid layout, display of regions, or element order.
- No web fonts or remote images; system fonts and pure CSS only.
- Keep text readable and keep the status colors (.st-done, .st-failed, .st-searching) distinct.

Here is the class contract and an example theme:
<paste THEMING.md and jukebox.css>
```
