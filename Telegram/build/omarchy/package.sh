#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf '%s\n' \
        'Usage: package.sh --binary /path/to/Debug/Telegram --palette /path/to/colors.palette --output /new/directory' \
        'Supply the native fork Debug binary built with DISABLE_AUTOUPDATE=ON.' \
        'This helper does not detect build options, build dependencies, or install anything.'
}

binary=
palette=
output=
while (($#)); do
    case "$1" in
        --binary|--palette|--output)
            if (($# < 2)) || [[ -z $2 ]]; then
                usage >&2
                exit 2
            fi
            case "$1" in
                --binary) binary=$2 ;;
                --palette) palette=$2 ;;
                --output) output=$2 ;;
            esac
            shift 2
            ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
if [[ -z $binary || -z $palette || -z $output ]]; then
    usage >&2
    exit 2
fi
if [[ ! -f $binary || ! -x $binary || ! -f $palette ]]; then
    printf '%s\n' 'package: binary must be an executable file and palette must be a file' >&2
    exit 1
fi
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -m 755 -- "$output"
trap 'rm -rf -- "$output"' EXIT
install -m 755 -- "$binary" "$output/Telegram"
install -m 755 -- "$source_dir/launch.py" "$output/launch.py"
install -m 644 -- "$source_dir/generate_palette.py" "$output/generate_palette.py"
install -m 644 -- "$palette" "$output/colors.palette"
install -m 644 -- "$source_dir/README.md" "$output/README.md"
install -m 644 -- "$source_dir/../../../LICENSE" "$output/LICENSE"
install -m 644 -- "$source_dir/../../../LEGAL" "$output/LEGAL"
trap - EXIT
printf '%s\n' \
    "Package created: $output" \
    'Run python3 /path/to/package/launch.py (Python 3.11+ required).' \
    'Verify the supplied native fork was built with DISABLE_AUTOUPDATE=ON before launching.' \
    'No libraries, accounts, desktop registration, or compositor rules are bundled.'
