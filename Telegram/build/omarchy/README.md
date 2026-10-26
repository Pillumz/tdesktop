# Omarchy palette prototype

Standalone Python 3.11+ stdlib generator for this Telegram fork. It reads an
explicit Omarchy `colors.toml` and Telegram's actual palette definitions, then
writes a `.tdesktop-palette`. No C++ changes, installation, daemon, hooks,
network/cloud calls, secrets, or account access. It does not change the host's
active theme or apply anything to Telegram.

## Generate only

From the checkout root, with `Telegram/lib_ui` populated:

```bash
preview=$(mktemp -d)
python3 Telegram/build/omarchy/generate_palette.py \
  --colors /home/explify/omarchy/themes/tokyo-night/colors.toml \
  --output "$preview/omarchy.tdesktop-palette"
```

The output parent must already exist. `--surface-alpha 0.85` is the default;
use `--surface-alpha 1` for opaque surfaces (native effect alpha is unchanged). `--palette /path/to/colors.palette`
selects a different populated checkout's schema/defaults without changing a
submodule. Remove the temporary preview directory when finished.

Both inputs are parsed and validated before replacement. Output uses a private
same-directory temporary file, flush/fsync, and atomic rename; failures before
rename leave an existing output intact and remove the temporary file. Output
symlinks and paths/hardlinks to either input are rejected. Replacement files
are owner-readable/writable (0600); this is not a privileged/shared-file writer.

## Mapping and boundaries

- Canonical keys win over legacy names: `background/bg/color0`,
  `foreground/fg/color7`, `lighter_background/lighter_bg`,
  `bright_foreground/bright_fg/color15`, `muted/color8/dark_foreground/dark_fg`,
  `selection/selection_background/color8`, `accent/blue/color4`,
  `red/color1`, and `green/color2`. Only background and foreground are required.
  Missing roles use neutral/accent mixes or semantic red/green defaults.
  Consumed colors must be `#RRGGBB`; unrelated keys (including border gradients)
  are ignored. This is a focused subset, not Omarchy's entire template resolver.
- Mode precedence: `--mode`, `mode`, legacy `theme_type`, adjacent `light.mode`,
  then the same RGB-sum light/dark heuristic as `omarchy-theme-color`.
  Mode selects fallback colors; no unsupported Telegram mode key is emitted.
- Explicit roles cover main windows, chat lists, sidebars, compose areas,
  menus/boxes, message bubbles, notification/toast surfaces, media menus,
  call panels, wallet panels, text/icons, selection, links, errors and success.
  Outgoing bubbles get a subtle accent tint. Destructive and success roles stay
  separate from the accent. Text/link contrast is adjusted toward black/white
  to at least 4.5:1 against nominal mapped backgrounds; muted roles target 3:1.
  This cannot guarantee contrast over an arbitrary translucent wallpaper/media.
- Every palette entry is a concrete color. RGB mapping and original Telegram
  alpha are resolved independently, including through aliases. Native shadow,
  fade, ripple, media-selection and intentional foreground fades retain their
  original alpha even when their RGB is remapped. Only `SURFACES` receives the
  configured surface opacity; this new alpha never propagates through aliases.
  Ordinary text/icons, file-download icons and selected-chat badge/check
  foregrounds stay solid. Photo/video pixels are not processed; controls over
  media retain white RGB and any native fade rather than being tinted.
- Unmapped entries retain Telegram's default RGB, including many identity/file
  colors, premium gradients, charts and specialized effects. This is **not**
  complete every-UI coverage. The exact role groups and translucent surfaces
  are visible in `ROLE_KEYS` and `SURFACES` in `generate_palette.py`.
- A palette cannot by itself make native windows translucent or remove chat
  wallpaper; hardcoded/custom-rendered UI and actual stacking need GUI proof.

## Live changes: deferred

Omarchy stages templates under `current/next-theme`, publishes
`~/.local/state/omarchy/current/theme`, then invokes the `theme-set` hook with
the theme slug. Regeneration should consume the published theme, not staging.
Rapid switches can produce stale hook invocations, so a future integration
should read the current palette rather than trust the hook's slug alone.

The coordinator must choose the fork's launch/apply/reload contract, output
ownership, stale-switch handling, and renderer alpha policy first. This CLI
only regenerates a file when invoked; no hook is provided or installed, and
live updates are not implemented or claimed.

## Verification scope

Use `herd-test --no-pg -- python3 ...` for focused CLI runs into temporary
directories with installed dark/light palettes. Verify deterministic replacement,
concrete keys, native effect-alpha preservation, foreground opacity, invalid-input
preservation and legacy inputs.
No default unit suite or app build is added. Coordinator-owned build/GUI checks
must establish actual appearance, media opacity and live application separately.
