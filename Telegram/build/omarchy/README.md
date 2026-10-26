# Native Omarchy prototype

This experimental fork separates translucent window surfaces from solid text,
icons and media. A Python 3.11+ launcher maps Omarchy's published `colors.toml`
and follows theme changes while Telegram runs. Nothing is installed into
Omarchy, and no system daemon or theme hook is needed.

## Run a prepared package

```bash
python3 /path/to/telegram-native/launch.py
```

The launcher uses its own profile under
`${XDG_DATA_HOME:-$HOME/.local/share}/telegram-native`. Your installed Telegram
profile is not imported or changed; expect a separate login. Never pass that
installed profile to `--profile`. Use `--opacity 0.85` to adjust surface opacity
without fading text or media. `--colors`, `--profile`, `--binary` and `--palette`
allow explicit paths. No URL handling or extra Telegram switches are forwarded.

Keep compositor whole-window opacity at **100%**. Native mode uses the separate
Wayland application ID `org.telegram.desktop.native`, avoiding existing rules
that specifically fade `org.telegram.desktop`. A broad opacity rule can still
fade this app. Blur remains the compositor's responsibility.

Run the launcher again after an in-app restart: its watcher follows the process
it started, not Telegram's detached replacement process. This is a prototype,
not a replacement for the installed client.

## Generate only

From the checkout root, with `Telegram/lib_ui` populated:

```bash
preview=$(mktemp -d)
python3 Telegram/build/omarchy/generate_palette.py \
  --colors "$HOME/.local/state/omarchy/current/theme/colors.toml" \
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

## Live changes and process-only rendering

The launcher polls the published theme's color content and adjacent `light.mode`
marker once per second, including through atomic theme-directory replacements.
It regenerates only when these change. Invalid updates retain the last good
palette and produce at most one warning per minute. Missing/invalid initial
inputs stop launch rather than silently choosing another theme.

The fork's two opt-ins are independent:

- `TDESKTOP_THEME=/absolute/file.tdesktop-palette` applies an external palette
  after normal theme initialization and watches the file and parent directory.
  Atomic replacements are supported; reloads are debounced by 150 ms. Invalid
  updates keep the current palette. Keep the parent directory in place.
- `TDESKTOP_TRANSLUCENT=1` enables native transparent surfaces on the all-other
  platform branch (Linux/BSD). Windows and macOS retain normal rendering.
  This startup setting requires a new process. Chat wallpaper is replaced
  visually by the theme tint, without changing the stored wallpaper.

Neither opt-in replaces saved themes or night-mode preferences. The external
palette masks manual theme previews while active. Launch without the variables
to restore normal behavior. The launcher owns a temporary palette and removes
it when its child process exits; it leaves the isolated account profile intact.

## Build and package

Build **Debug**, with `DESKTOP_APP_DISABLE_AUTOUPDATE=ON`, using the fork's
recursive submodules. The native `lib_ui` changes are pinned through
`.gitmodules`; updating Telegram alone without that library will not compile.
Use a personal Telegram API ID for a maintained client; `TDESKTOP_API_TEST=ON`
is a development-build option, not a distribution credential.

The isolated Linux build used Telegram's image:

```text
ghcr.io/telegramdesktop/tdesktop/centos_env@sha256:4f629171eb8b468ce4d8de9208c3a4523f8a91698fa091ba786849452f90c81c
```

With the checkout mounted at `/usr/src/tdesktop`, configure from `Telegram/`:

```bash
./configure.sh -D CMAKE_BUILD_TYPE=Debug -D TDESKTOP_API_TEST=ON \
  -D DESKTOP_APP_DISABLE_AUTOUPDATE=ON \
  -D CMAKE_CXX_FLAGS_DEBUG="-g1 -Og" -D CMAKE_C_FLAGS_DEBUG="-g1 -Og"
```

Build from the checkout root with
`cmake --build out --config Debug --target Telegram --parallel 6`.
The prototype build environment needs more than the sandbox's default RAM;
16 GiB and eight virtual CPUs were used. Do not build or launch against an
owner's desktop/account just to test appearance.

After restoring the disposable test overlay to its no-op version and rebuilding:

```bash
Telegram/build/omarchy/package.sh \
  --binary out/Debug/Telegram \
  --palette Telegram/lib_ui/ui/colors.palette \
  --output /new/telegram-native
```

The output directory must not exist. The package contains the executable,
launcher, generator and palette schema, never accounts or test fixtures. It
neither installs dependencies nor detects the supplied binary's build flags.
Debug symbols may be stripped from the packaged copy; keep the original build
for diagnosis. Automatic updates must stay disabled so an official binary
cannot replace the patched executable.

For upstream updates, rebase the small `lib_ui` patch onto Telegram's newly
pinned library version, publish it, then update the main fork's submodule pin.
Rebuild and repeat actual UI checks; a palette-only check cannot validate alpha.

## Verification and limits

Verified on 2026-10-26 with a Debug build inside an isolated Omarchy VM:

- All 23 installed Omarchy palettes passed generator checks, including light,
  dark, legacy inputs, foreground opacity and preservation of native effects.
- A disposable harness overlay populated real Telegram widgets with 32 local
  chats and an in-memory photo. A separate network namespace had only a down
  loopback interface and no routes. No real account or credentials were used.
- Black/white desktop captures measured a 38/255 background difference in the
  chat, chat list, info panel and main-menu rows: the requested 85% opacity.
  Photo color patches, avatar pixels and fully covered text pixels did not
  change. Native antialiasing and intentional disabled fades remain intact.
- Actual Omarchy light/dark switches updated the running app without restart.
  Invalid color input retained the generated palette; an invalid external
  palette replacement retained displayed colors. Restored updates still worked.
- Chat-list scrolling, changing chats, typing a draft, main menu, Settings,
  and half/quarter/third-size layouts were exercised. Both native and opt-out
  fixture runs completed cleanly. Opt-out backgrounds and photos stayed opaque
  across the same black/white desktop check.
- The disposable overlay was restored to its no-op version before the final
  package rebuild. The launcher was also checked with a fake executable for
  argument handling, atomic theme swaps, process exit and signal cleanup.

This does not validate real login/messaging, calls, wallet operations, every
specialized dialog, custom per-chat themes, or physical-GPU performance. Some
secondary surfaces still layer over their parent rather than replacing it;
full application-wide visual polish is not claimed. Filter-slide alpha handling
was source-reviewed but not exercised with an actual saved filter fixture.
Windows/macOS builds were not run. No upstream PR or automatic-update path is
provided.

Prototype source: https://github.com/Pillumz/tdesktop/tree/feat/omarchy-native
with https://github.com/Pillumz/lib_ui/tree/feat/omarchy-native. Keep the package's
`SOURCE.txt` for the exact revisions and build configuration. Run verification
commands through `herd-test --no-pg`; a green check is not a substitute for
inspecting the real compositor captures.
