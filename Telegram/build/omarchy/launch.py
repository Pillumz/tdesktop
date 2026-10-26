#!/usr/bin/env python3
"""Run the native Telegram prototype with an isolated profile and live palette.

Requires Python 3.11+ and a fork built with DISABLE_AUTOUPDATE=ON; the launcher
cannot verify that build option. No URLs or extra Telegram switches are accepted.
"""

import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
import generate_palette


def xdg_path(variable, fallback):
    value = os.environ.get(variable, "")
    return Path(value) if value and Path(value).is_absolute() else Path.home() / fallback


def absolute(path):
    return path.expanduser().absolute()


def stop_child(child, signum):
    if child.poll() is not None:
        return
    try:
        os.killpg(child.pid, signum)
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()
    except ProcessLookupError:
        child.wait()


def run(args):
    requested_signal = None

    def request_stop(signum, frame):
        nonlocal requested_signal
        if requested_signal is None:
            requested_signal = signum

    previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    child = None
    try:
        definitions = generate_palette.load_palette(args.palette)
        args.profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix="telegram-native-") as directory:
            output = Path(directory) / "omarchy.tdesktop-palette"

            def regenerate():
                colors, mode = generate_palette.load_colors(args.colors, "auto")
                content, mapped = generate_palette.generate(
                    definitions, generate_palette.make_roles(colors, mode), args.opacity,
                )
                if not output.exists() or output.read_text(encoding="utf-8") != content:
                    generate_palette.atomic_write(output, content)

            def fingerprint():
                return args.colors.read_bytes(), args.colors.with_name("light.mode").is_file()

            last_seen = fingerprint()
            regenerate()
            if requested_signal is not None:
                return 128 + requested_signal
            environment = os.environ.copy()
            environment.update(TDESKTOP_THEME=str(output), TDESKTOP_TRANSLUCENT="1")
            child = subprocess.Popen(
                [str(args.binary), "-many", "-workdir", str(args.profile)],
                cwd=args.profile, env=environment, start_new_session=True,
            )
            next_warning = 0.0
            while child.poll() is None:
                if requested_signal is not None:
                    stop_child(child, requested_signal)
                    break
                try:
                    current = fingerprint()
                    if current != last_seen:
                        regenerate()
                        last_seen = current
                except (OSError, ValueError, RecursionError) as error:
                    now = time.monotonic()
                    if now >= next_warning:
                        print(f"telegram-native: keeping last good palette: {error}", file=sys.stderr)
                        next_warning = now + 60
                try:
                    child.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
            return child.returncode if child.returncode >= 0 else 128 - child.returncode
    finally:
        if child is not None:
            stop_child(child, signal.SIGTERM)
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main():
    adjacent = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--binary", type=Path, default=adjacent / "Telegram")
    parser.add_argument("--palette", type=Path, default=adjacent / "colors.palette", help="Telegram palette schema")
    parser.add_argument(
        "--colors", type=Path,
        default=xdg_path("XDG_STATE_HOME", ".local/state") / "omarchy/current/theme/colors.toml",
    )
    parser.add_argument(
        "--profile", type=Path,
        default=xdg_path("XDG_DATA_HOME", ".local/share") / "telegram-native",
        help="isolated profile; never point this at your installed Telegram profile",
    )
    parser.add_argument("--opacity", type=float, default=0.85, help="surface opacity, 0..1 (default: 0.85)")
    args = parser.parse_args()
    if not math.isfinite(args.opacity) or not 0 <= args.opacity <= 1:
        parser.error("opacity must be finite and between 0 and 1")
    args.binary = absolute(args.binary)
    args.palette = absolute(args.palette)
    args.colors = absolute(args.colors)
    args.profile = absolute(args.profile)
    try:
        return run(args)
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(1, f"telegram-native: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
