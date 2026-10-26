#!/usr/bin/env python3
"""Generate a prototype Telegram palette from an explicit Omarchy colors.toml."""

import argparse
import math
import os
from pathlib import Path
import re
import tempfile
import tomllib


DEFAULT_PALETTE = Path(__file__).resolve().parents[2] / "lib_ui/ui/colors.palette"
HEX = re.compile(r"#[0-9a-fA-F]{6}")
PALETTE_LINE = re.compile(
    r"(\w+):\s*(#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?|\w+)(?:\s*\|\s*\w+)?;"
)
LEGACY = {
    "background": ("bg", "color0"),
    "foreground": ("fg", "color7"),
    "lighter_background": ("lighter_bg",),
    "bright_foreground": ("bright_fg", "color15"),
    "muted": ("color8", "dark_foreground", "dark_fg"),
    "selection": ("selection_background", "color8"),
    "accent": ("blue", "color4"),
    "red": ("color1",),
    "green": ("color2",),
}
SURFACES = frozenset("""
windowBg dialogsBg dialogsBgOver dialogsBgActive topBarBg sideBarBg sideBarBgActive
mainMenuBg mainMenuCoverBg menuBg menuBgOver boxBg boxSearchBg contactsBg introBg titleBg
titleBgActive emojiPanBg emojiPanCategories emojiPanHeaderBg stickerPreviewBg
historyComposeAreaBg historyPinnedBg historyReplyBg historyComposeButtonBg
historyUnreadBarBg mediaPlayerBg notificationBg tooltipBg toastBg
msgInBg msgOutBg msgInBgSelected msgOutBgSelected msgServiceBg msgServiceBgSelected
mediaviewBg mediaviewMenuBg mediaviewCaptionBg callBg groupCallBg
groupCallMembersBg groupCallMenuBg walletTitleBg walletTitleBgActive walletTopBg
""".split())
ROLE_KEYS = {
    "background": """
windowBg dialogsBg topBarBg mainMenuBg menuBg boxBg boxSearchBg contactsBg introBg
emojiPanBg emojiPanCategories emojiPanHeaderBg stickerPreviewBg historyComposeAreaBg
historyPinnedBg historyReplyBg historyComposeButtonBg mediaPlayerBg notificationBg
mediaviewFileBg mediaviewMenuBg callBg callBgOpaque groupCallBg groupCallMenuBg
walletTitleBg walletTitleBgActive
""",
    "panel": """
windowBgOver titleBg titleBgActive sideBarBg walletTopBg tooltipBg toastBg
mediaviewBg mediaviewCaptionBg groupCallMembersBg historyUnreadBarBg
boxDividerBg searchedBarBg filterInputInactiveBg botKbBg callBgButton
""",
    "hover": """
windowBgRipple dialogsBgOver menuBgOver menuBgRipple lightButtonBgOver
lightButtonBgRipple contactsBgOver filterInputActiveBg sideBarBgRipple
mediaviewMenuBgOver mediaviewMenuBgRipple groupCallMembersBgOver
groupCallMembersBgRipple groupCallMenuBgOver groupCallMenuBgRipple
callIconBg callIconActiveRipple callMuteRipple msgBotKbOverBgAdd msgBotKbRippleBg
titleButtonBgOver walletTitleButtonBgOver
""",
    "muted": """
windowSubTextFg windowSubTextFgOver menuIconFg smallCloseIconFg placeholderFg
placeholderFgActive checkboxFg menuFgDisabled titleFg titleButtonFg
walletTitleButtonFg walletTitleButtonFgOver walletTopLabelFg sideBarTextFg
sideBarIconFg dialogsSendingIconFg dialogsUnreadBgMuted trayCounterBgMute
callStatusFg groupCallMemberInactiveIcon groupCallMemberNotJoinedStatus
mediaPlayerDisabledFg profileStatusFgOver sideBarBadgeBgMuted callBarBgMuted
boxTitleAdditionalFg emojiIconFg dialogsArchiveFg dialogsArchiveFgOver
notificationSampleCloseFg
notificationSampleTextFg notificationSampleNameFg msgInDateFg msgOutDateFg
historySendingInIconFg historySendingOutIconFg msgWaveformInInactive
msgWaveformOutInactive mediaviewPlaybackInactive mediaviewPlaybackInactiveOver
""",
    "foreground": """
windowFg windowFgOver windowBoldFg windowBoldFgOver boxTitleFg tooltipFg toastFg
mediaviewMenuFg mediaviewCaptionFg callNameFg groupCallMembersFg groupCallIconFg
callIconFg walletBalanceFg walletSubBalanceFg botKbColor menuIconFgOver
smallCloseIconFgOver titleFgActive titleButtonFgOver menuSubmenuArrowFg
emojiSubIconFgActive
""",
    "border": """
inputBorderFg menuSeparatorFg tooltipBorderFg sliderBgInactive scrollBg scrollBgOver
historyScrollBg historyScrollBgOver msgInShadow msgOutShadow msgInShadowSelected
msgOutShadowSelected windowShadowFgFallback titleShadow
""",
    "accent": """
windowBgActive activeButtonBg activeButtonBgOver activeButtonBgRipple activeLineFg
filterInputBorderFg botKbPrimaryBg botKbInlinePrimaryBg mainMenuCloudBg sideBarBadgeBg
sideBarBadgeBgActive sideBarBadgeBgMutedActive msgFileInBg msgFileInBgOver
msgFileInBgSelected msgFileOutBg msgFileOutBgSelected callIconBgActive
""",
    "link": """
windowActiveTextFg lightButtonFg historySendIconFg historySendIconFgOver
historyReplyIconFg sideBarTextFgActive sideBarIconFgActive mediaPlayerActiveFg
historyUnreadBarFg
msgOutServiceFg msgInMonoFg msgOutMonoFg
msgFileThumbLinkOutFg msgInReplyBarColor
msgInReplyBarSelColor msgOutReplyBarColor msgOutReplyBarSelColor
msgWaveformInActive msgWaveformInActiveSelected msgWaveformOutActive
msgWaveformOutActiveSelected groupCallActiveFg groupCallMemberInactiveStatus
mediaviewTextLinkFg currencyFg photoEditorItemBaseHandleFg
""",
    "on_accent": """
windowFgActive activeButtonFg activeButtonSecondaryFg sideBarBadgeFg
historyFileInIconFg historyFileInIconFgSelected historyFileInRadialFg
historyFileInRadialFgSelected historyFileOutIconFg historyFileOutIconFgSelected
historyFileOutRadialFg historyFileOutRadialFgSelected overviewCheckFgActive
callIconFgActive
""",
    "on_selection": """
dialogsNameFgActive dialogsDateFgActive dialogsTextFgActive dialogsTextFgServiceActive
dialogsDraftFgActive dialogsSendingIconFgActive dialogsSentIconFgActive
historyTextInFgSelected historyTextOutFgSelected msgInDateFgSelected
msgOutDateFgSelected msgInServiceFgSelected msgOutServiceFgSelected
historyLinkInFgSelected historyLinkOutFgSelected msgInMonoFgSelected
msgOutMonoFgSelected msgFileThumbLinkInFgSelected msgFileThumbLinkOutFgSelected
searchedTextMatchFg
searchedTextCurrentMatchFg mainMenuCloudFg
""",
    "selected_badge": """
dialogsVerifiedIconBgActive dialogsUnreadBgActive dialogsUnreadBgMutedActive
""",
    "selection": """
dialogsBgActive sideBarBgActive mainMenuCoverBg msgInBgSelected msgOutBgSelected
msgServiceBgSelected searchedTextMatchBg searchedTextCurrentMatchBg
dialogsVerifiedIconFgActive dialogsUnreadFgActive
""",
    "selected_muted": "msgWaveformInInactiveSelected msgWaveformOutInactiveSelected",
    "incoming": "msgInBg",
    "outgoing": "msgOutBg",
    "service": "msgServiceBg",
    "service_text": "msgServiceFg",
    "red": """
attentionButtonFg attentionButtonFgOver activeLineFgError boxTextFgError
callArrowMissedFg dialogsDraftFg dialogsDraftFgOver dialogsScamFg
callHangupBg callHangupRipple groupCallMemberMutedIcon groupCallLeaveBg
groupCallLeaveBgRipple spellUnderline trayCounterBg
""",
    "red_fill": """
attentionButtonBgOver attentionButtonBgRipple titleButtonCloseBgOver
botKbDangerBg botKbInlineDangerBg
""",
    "green": """
boxTextFgGood paymentsTipActive callArrowFg historyCallArrowInFg
historyCallArrowInFgSelected historyOutIconFg historyOutIconFgSelected
dialogsSentIconFg dialogsSentIconFgOver dialogsOnlineBadgeFg
callAnswerBg callAnswerRipple callAnswerBgOuter groupCallMemberActiveIcon
groupCallMemberActiveStatus botKbSuccessBg botKbInlineSuccessBg rankAdminFg
""",
    "on_red": "titleButtonCloseFgOver trayCounterFg",
    "media_white": """
historyFileThumbIconFg historyFileThumbIconFgSelected historyFileThumbRadialFg
historyFileThumbRadialFgSelected historyVideoMessageProgressFg
historyIconFgInverted historySendingInvertedIconFg msgDateImgFg
mediaviewControlFg mediaviewPlaybackProgressFg mediaviewPipControlsFg
mediaviewPipControlsFgOver mediaviewPipPlaybackActive groupCallVideoTextFg
groupCallVideoSubTextFg photoCropPointFg
""",
}


def mix(start, end, amount):
    channels = zip(bytes.fromhex(start[1:7]), bytes.fromhex(end[1:7]))
    return "#" + "".join(
        f"{int(a * (1 - amount) + b * amount + 0.5):02x}" for a, b in channels
    )


def luminance(color):
    channels = [c / 255 for c in bytes.fromhex(color[1:7])]
    linear = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        for c in channels
    ]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


def readable(color, *backgrounds, minimum=4.5):
    def score(candidate):
        return min(contrast(candidate, background) for background in backgrounds)

    if score(color) >= minimum:
        return color
    target = max(("#000000", "#ffffff"), key=score)
    for step in range(1, 101):
        candidate = mix(color, target, step / 100)
        if score(candidate) >= minimum:
            return candidate
    return target


def load_colors(path, mode):
    with path.open("rb") as source:
        raw = tomllib.load(source)
    colors = {}
    for key, aliases in LEGACY.items():
        for name in (key, *aliases):
            if name in raw:
                value = raw[name]
                if not isinstance(value, str) or not HEX.fullmatch(value):
                    raise ValueError(f"{name} must be a #RRGGBB color")
                colors[key] = value.lower()
                break
    for required in ("background", "foreground"):
        if required not in colors:
            raise ValueError(f"missing {required} (or its legacy alias)")
    if mode == "auto":
        mode = raw.get("mode", raw.get("theme_type"))
        if mode is None:
            if path.with_name("light.mode").is_file():
                mode = "light"
            else:
                brightness = sum(bytes.fromhex(colors["background"][1:]))
                mode = "light" if brightness > 382 else "dark"
    if mode not in ("dark", "light"):
        raise ValueError("mode/theme_type must be 'dark' or 'light'")
    return colors, mode


def make_roles(colors, mode):
    bg = colors["background"]
    fg = readable(colors["foreground"], bg)
    accent = colors.get("accent", fg)
    panel = colors.get("lighter_background", mix(bg, fg, 0.06))
    selection = colors.get("selection", mix(bg, accent, 0.25))
    red = colors.get("red", "#ef7070" if mode == "dark" else "#b42332")
    green = colors.get("green", "#79bb70" if mode == "dark" else "#26752b")
    service = mix(bg, accent, 0.20)
    outgoing = mix(bg, accent, 0.12)
    hover = mix(bg, fg, 0.12)
    fg = readable(fg, bg, panel, outgoing, hover)
    on_selection = readable(colors.get("bright_foreground", fg), selection)
    return {
        "background": bg,
        "panel": panel,
        "hover": hover,
        "foreground": fg,
        "muted": readable(
            colors.get("muted", mix(bg, fg, 0.55)),
            bg, panel, outgoing, hover, minimum=3,
        ),
        "border": mix(bg, fg, 0.25),
        "accent": accent,
        "link": readable(accent, bg, panel, outgoing, hover),
        "on_accent": readable(colors.get("bright_foreground", fg), accent),
        "selection": selection,
        "on_selection": on_selection,
        "selected_muted": readable(
            mix(selection, on_selection, 0.55), selection, minimum=3,
        ),
        "selected_badge": readable(fg, selection),
        "incoming": bg,
        "outgoing": outgoing,
        "service": service,
        "service_text": readable(fg, service),
        "red": readable(red, bg, panel, hover, minimum=3),
        "red_fill": red,
        "on_red": readable("#ffffff", red),
        "green": readable(green, bg, panel, hover, minimum=3),
        "media_white": "#ffffff",
    }


def load_palette(path):
    definitions = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        content = line.split("//", 1)[0].strip()
        if not content:
            continue
        match = PALETTE_LINE.fullmatch(content)
        if not match:
            raise ValueError(f"unsupported palette definition at {path}:{number}")
        key, value = match.groups()
        if key in definitions:
            raise ValueError(f"duplicate palette key: {key}")
        definitions[key] = value
    if not definitions:
        raise ValueError("Telegram palette is empty")
    return definitions


def generate(definitions, roles, alpha):
    overrides = {}
    for role, keys in ROLE_KEYS.items():
        for key in keys.split():
            if key not in definitions:
                raise ValueError(f"mapping key missing from Telegram palette: {key}")
            if key in overrides:
                raise ValueError(f"duplicate mapping key: {key}")
            overrides[key] = roles[role]
    if SURFACES - definitions.keys():
        raise ValueError("surface key missing from Telegram palette")
    original = {}
    mapped = definitions | overrides
    resolved = {}

    def resolve(key, values, cache, visiting):
        if key in cache:
            return cache[key]
        if key in visiting:
            raise ValueError(f"cyclic Telegram palette alias: {key}")
        if key not in values:
            raise ValueError(f"unknown Telegram palette alias: {key}")
        value = values[key]
        if value.startswith("#"):
            result = value.lower()
        else:
            result = resolve(value, values, cache, visiting | {key})
        cache[key] = result
        return result

    lines = ["// Prototype Omarchy palette: native effect alpha; explicit surface opacity."]
    for key in definitions:
        native = resolve(key, definitions, original, set())
        value = resolve(key, mapped, resolved, set())[:7]
        opacity = native[7:]
        if key in SURFACES:
            opacity = f"{int(alpha * 255 + 0.5):02x}" if alpha < 1 else ""
        lines.append(f"{key}: {value}{opacity};")
    return "\n".join(lines) + "\n", len(overrides)


def atomic_write(path, content):
    if path.is_symlink():
        raise ValueError("output must not be a symlink")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n",
            dir=path.parent, prefix=f".{path.name}.", delete=False,
        ) as target:
            temporary = Path(target.name)
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--colors", type=Path, required=True, help="explicit Omarchy colors.toml")
    parser.add_argument("--output", type=Path, required=True, help="output .tdesktop-palette; parent must exist")
    parser.add_argument("--palette", type=Path, default=DEFAULT_PALETTE, help="Telegram colors.palette schema/defaults")
    parser.add_argument("--surface-alpha", type=float, default=0.85, help="explicit surface opacity, 0..1 (default: 0.85)")
    parser.add_argument("--mode", choices=("auto", "dark", "light"), default="auto")
    args = parser.parse_args()
    try:
        if not math.isfinite(args.surface_alpha) or not 0 <= args.surface_alpha <= 1:
            raise ValueError("surface alpha must be finite and between 0 and 1")
        for source in (args.colors, args.palette):
            if args.output.resolve() == source.resolve():
                raise ValueError("output must differ from both input files")
            if args.output.exists() and os.path.samefile(args.output, source):
                raise ValueError("output must not be a hard link to an input file")
        colors, mode = load_colors(args.colors, args.mode)
        definitions = load_palette(args.palette)
        content, mapped = generate(definitions, make_roles(colors, mode), args.surface_alpha)
        atomic_write(args.output, content)
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(1, f"generate_palette: {error}\n")
    print(f"Wrote {args.output}: {len(definitions)} colors, {mapped} explicit mappings, mode={mode}")


if __name__ == "__main__":
    main()
