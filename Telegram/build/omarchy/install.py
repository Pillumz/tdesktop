#!/usr/bin/env python3
"""Install this prepared package's user-level shim, desktop entry and URI defaults.

Run only after placing the package at its permanent location. Never runs Telegram,
changes account data, removes the official package, or enables session autostart.
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from launch import default_profile, xdg_path


MARKER = "# Installed by telegram-native install.py\n"


def desktop_string(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def desktop_argument(value):
    value = str(value).replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        value = value.replace(character, "\\" + character)
    return desktop_string('"' + value + '"')


def install():
    package = Path(__file__).resolve().parent
    for name in ("Telegram", "launch.py", "generate_palette.py", "colors.palette", "telegram-native.png"):
        if not (package / name).is_file():
            raise ValueError(f"missing package asset: {name}; use package.sh first")
    if not os.access(package / "Telegram", os.X_OK):
        raise ValueError("packaged Telegram is not executable")
    binary_dir = Path.home() / ".local/bin"
    search = [Path(item).absolute() for item in os.get_exec_path() if item]
    if binary_dir not in search:
        raise ValueError("add ~/.local/bin to your graphical session PATH, then log in again before installing")
    for directory in search[:search.index(binary_dir)]:
        if os.access(directory / "Telegram", os.X_OK):
            raise ValueError(f"{directory}/Telegram shadows ~/.local/bin; put ~/.local/bin first in the session PATH")
    if not shutil.which("xdg-mime"):
        raise ValueError("xdg-mime is required to register URI defaults")
    shim = binary_dir / "Telegram"
    entry = xdg_path("XDG_DATA_HOME", ".local/share") / "applications/org.telegram.desktop.native.desktop"
    if os.path.lexists(shim) and (not shim.is_symlink() or shim.readlink() != package / "launch.py"):
        raise ValueError(f"refusing to replace existing {shim}; coordinator must inspect it first")
    if entry.is_symlink() or (entry.exists() and not entry.read_text().startswith(MARKER)):
        raise ValueError(f"refusing to replace existing {entry}; coordinator must inspect it first")
    command = f"{desktop_argument(shim)} -workdir {desktop_argument(str(default_profile()) + '/')} -- %u"
    content = MARKER + "\n".join((
        "[Desktop Entry]",
        "Type=Application",
        "Name=Telegram Native",
        "Comment=Telegram with the Omarchy native theme",
        f"Exec={command}",
        f"Icon={desktop_string(package / 'telegram-native.png')}",
        "Terminal=false",
        "Categories=Network;InstantMessaging;",
        "MimeType=x-scheme-handler/tg;x-scheme-handler/ton;x-scheme-handler/tonsite;",
        "StartupNotify=true",
        "StartupWMClass=org.telegram.desktop.native",
        "DBusActivatable=false",
        "",
    ))
    binary_dir.mkdir(parents=True, exist_ok=True)
    entry.parent.mkdir(parents=True, exist_ok=True)
    if not shim.is_symlink():
        shim.symlink_to(package / "launch.py")
    entry.write_text(content, encoding="utf-8")
    for scheme in ("tg", "ton", "tonsite"):
        subprocess.run(["xdg-mime", "default", entry.name, f"x-scheme-handler/{scheme}"], check=True)
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(entry.parent)], check=True)
    print(f"Installed {shim} and {entry}")
    print("URI defaults set for tg:, ton: and tonsite:. No app was started.")
    print("Enable autostart in Telegram Settings if wanted; it uses this same shim.")


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        install()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"telegram-native install: {error}")


if __name__ == "__main__":
    main()
