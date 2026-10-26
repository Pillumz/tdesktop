#!/usr/bin/env python3
"""Launch the Omarchy fork (Python 3.11+, Linux, auto-updates disabled).

Normal launches activate the existing fork. Only tg:, ton: and tonsite: links
and the -autostart / -quit controls are accepted, not arbitrary Qt switches.
"""

import argparse
import ctypes
import fcntl
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
import generate_palette


def xdg_path(variable, fallback):
    value = os.environ.get(variable, "")
    return Path(value) if value and Path(value).is_absolute() else Path.home() / fallback


def default_profile():
    return (xdg_path("XDG_DATA_HOME", ".local/share") / "telegram-native").resolve()


def adopt_restarts():
    pr_set_child_subreaper = 36
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(pr_set_child_subreaper, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "cannot supervise detached Telegram restarts")


def telegram_children(child, binary):
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if not pid:
            break
        if pid == child.pid:
            child.returncode = os.waitstatus_to_exitcode(status)
    result = []
    for value in Path(f"/proc/self/task/{os.getpid()}/children").read_text().split():
        pid = int(value)
        try:
            if (pid == child.pid and child.returncode is None) or Path(f"/proc/{pid}/exe").samefile(binary):
                result.append(pid)
        except (FileNotFoundError, PermissionError):
            pass
    return result


def stop_children(child, binary, signum):
    deadline = time.monotonic() + 5
    while active := telegram_children(child, binary):
        for pid in active:
            try:
                os.kill(pid, signum if time.monotonic() < deadline else signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.05)


def run(args):
    shim = Path.home() / ".local/bin/Telegram"
    if shim.resolve() != Path(__file__).resolve():
        raise ValueError("install this package's ~/.local/bin/Telegram shim with install.py before launching")
    environment = os.environ.copy()
    environment["PATH"] = str(shim.parent) + os.pathsep + environment.get("PATH", "")
    command = [str(args.binary), "-workdir", str(args.profile)]
    if args.quit:
        if not args.profile.is_dir():
            return 0
        return subprocess.run(command + ["-quit"], cwd=args.profile, env=environment, check=False).returncode
    if args.autostart:
        command += ["-autostart", "-startintray"]
    if args.urls:
        command += ["--", *args.urls]

    requested_signal = None

    def request_stop(signum, frame):
        nonlocal requested_signal
        if requested_signal is None:
            requested_signal = signum

    adopt_restarts()
    previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    child = None
    try:
        args.profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        state = args.profile / "omarchy"
        state.mkdir(mode=0o700, exist_ok=True)
        output = state / "live.tdesktop-palette"
        environment.update(TDESKTOP_THEME=str(output), TDESKTOP_TRANSLUCENT="1")
        with (state / "watcher.lock").open("a") as lock:
            owns_palette = False
            definitions = None
            last_seen = None
            next_warning = 0.0

            def update_palette():
                nonlocal owns_palette, definitions, last_seen
                if not owns_palette:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        return
                    owns_palette = True
                if definitions is None:
                    definitions = generate_palette.load_palette(args.palette)
                current = (args.colors.read_bytes(), args.colors.with_name("light.mode").is_file())
                if current != last_seen:
                    colors, mode = generate_palette.load_colors(args.colors, "auto")
                    content, mapped = generate_palette.generate(
                        definitions, generate_palette.make_roles(colors, mode), args.opacity,
                    )
                    if not output.exists() or output.read_text(encoding="utf-8") != content:
                        generate_palette.atomic_write(output, content)
                    last_seen = current

            ready_deadline = time.monotonic() + 10
            while True:
                update_palette()
                if output.is_file() or requested_signal is not None:
                    break
                if time.monotonic() >= ready_deadline:
                    raise ValueError("palette owner did not publish its initial palette")
                time.sleep(0.05)
            if requested_signal is not None:
                return 128 + requested_signal
            child = subprocess.Popen(command, cwd=args.profile, env=environment, start_new_session=True)
            while telegram_children(child, args.binary):
                if requested_signal is not None:
                    stop_children(child, args.binary, requested_signal)
                    return 128 + requested_signal
                try:
                    update_palette()
                except (OSError, ValueError, RecursionError) as error:
                    now = time.monotonic()
                    if now >= next_warning:
                        print(f"telegram-native: keeping last good palette: {error}", file=sys.stderr)
                        next_warning = now + 60
                time.sleep(1)
            return child.returncode if child.returncode >= 0 else 128 - child.returncode
    finally:
        if child is not None:
            stop_children(child, args.binary, signal.SIGTERM)
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
    parser.add_argument("--opacity", type=float, default=0.85, help="surface opacity, 0..1 (default: 0.85)")
    control = parser.add_mutually_exclusive_group()
    control.add_argument("-autostart", action="store_true", dest="autostart", help="hidden session startup (enable autostart in Telegram first)")
    control.add_argument("-quit", action="store_true", dest="quit", help="ask the existing fork to quit; never start its UI")
    parser.add_argument("-workdir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("urls", nargs="*", metavar="URI")
    args = parser.parse_args()
    args.profile = default_profile()
    if args.workdir is not None and args.workdir.expanduser().resolve() != args.profile:
        parser.error("-workdir must be the isolated telegram-native profile")
    if not math.isfinite(args.opacity) or not 0 <= args.opacity <= 1:
        parser.error("opacity must be finite and between 0 and 1")
    if args.urls and (args.quit or args.autostart):
        parser.error("URI arguments cannot be combined with startup/quit controls")
    for url in args.urls:
        scheme, separator, rest = url.partition(":")
        if (scheme.lower() not in {"tg", "ton", "tonsite"} or not separator or not rest
                or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url)
                or len(url.encode("utf-16-le")) > 16384):
            parser.error("expected a tg:, ton: or tonsite: URI (percent-encode spaces; maximum 8192 UTF-16 units)")
    args.binary = args.binary.expanduser().resolve()
    args.palette = args.palette.expanduser().absolute()
    args.colors = args.colors.expanduser().absolute()
    try:
        return run(args)
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(1, f"telegram-native: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
