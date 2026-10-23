"""Preview date-based MP4 duplicate renames; write only with --apply."""
import argparse
import calendar
import os
import re
import sys
import time
from bisect import bisect_left
from collections import Counter
from datetime import date, timedelta
from pathlib import Path


def extract_date_anywhere(s):
    for pattern in (r"S(\d{4})E(\d{2})(\d{2})", r"(\d{4})_(\d{2})-(\d{2})",
                    r"(\d{4})[-_](\d{2})[-_](\d{2})", r"(\d{4})(\d{2})(\d{2})"):
        match = re.search(pattern, s)
        if match:
            value = "".join(match.groups())
            date(int(value[:4]), int(value[4:6]), int(value[6:]))
            return value
    return None


def extract_title(filename):
    base = os.path.splitext(filename)[0]
    return base.split(" - ", 1)[1] if base.startswith("S") and " - " in base else base


def find_free_mmdd(year, month, day, forbidden):
    original = date(int(year), int(month), int(day))
    start = date(original.year, 1, 1)
    days = 366 if calendar.isleap(original.year) else 365
    # Forward first, wrapping within the original year; never invent February 29.
    for offset in range(1, days):
        candidate = start + timedelta(days=((original - start).days + offset) % days)
        if candidate.strftime("%m%d") not in forbidden:
            return candidate.strftime("%m"), candidate.strftime("%d")
    raise ValueError("No unused month/day remains in the original year")


def local_directory(value):
    root = Path(os.path.abspath(value))
    if str(root).startswith(("\\\\", "//")):
        raise ValueError("Choose a local directory, not a network path")
    for parent in (root, *root.parents):
        if parent.is_symlink() or getattr(parent.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Choose a folder reached without symbolic links or folder junctions")
    if not root.is_dir():
        raise ValueError("Directory does not exist")
    if os.name == "nt":
        import ctypes
        if ctypes.windll.kernel32.GetDriveTypeW(str(root.anchor)) == 4:
            raise ValueError("Choose a local drive")
    return root


def entries_in(root, maximum):
    entries = []
    with os.scandir(root) as scan:
        for entry in scan:
            if len(entries) >= maximum:
                raise ValueError("Directory entry limit reached; use a smaller folder or --max-files")
            entries.append(entry)
    return sorted(entries, key=lambda e: (e.name.casefold(), e.name))


def plan_renames(root, maximum=10000, timeout=30):
    deadline = time.monotonic() + timeout
    entries = entries_in(root, maximum)
    occupied = {e.name.casefold() for e in entries}
    thumbnails = sorted(e.name.casefold() for e in entries
                        if Path(e.name).suffix.lower() in (".png", ".jpg", ".jpeg"))
    files, reserved = [], set()
    for entry in entries:
        if time.monotonic() > deadline:
            raise ValueError("Scanning took too long; use a smaller folder or increase --timeout")
        if not entry.name.lower().endswith(".mp4"):
            continue
        if entry.is_symlink() or getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked MP4 files are not supported; use the original files in a local folder")
        if not entry.is_file(follow_symlinks=False):
            continue
        try:
            stamp = extract_date_anywhere(Path(entry.name).stem)
        except ValueError:
            print("Skipping invalid date:", entry.name)
            continue
        if not stamp:
            print("Skipping undated file:", entry.name)
            continue
        reserved.add(stamp[4:])
        base = Path(entry.name).stem.casefold()
        index = bisect_left(thumbnails, base)
        if index < len(thumbnails) and thumbnails[index].startswith(base):
            print("Skipping video with a thumbnail companion:", entry.name)
            continue
        files.append((entry.name, stamp))
    counts = Counter(stamp[4:] for _, stamp in files)
    seen, plans = set(), []
    for name, stamp in files:
        if time.monotonic() > deadline:
            raise ValueError("Preparing the rename plan took too long; use a smaller folder or increase --timeout")
        mmdd = stamp[4:]
        if counts[mmdd] == 1 or mmdd not in seen:
            seen.add(mmdd)
            continue
        mm, dd = find_free_mmdd(stamp[:4], mmdd[:2], mmdd[2:], reserved)
        new_name = f"S{stamp[:4]}E{mm}{dd} - {extract_title(name)}{Path(name).suffix}"
        if new_name.casefold() in occupied:
            raise ValueError("Destination already exists: " + new_name)
        occupied.add(new_name.casefold())
        reserved.add(mm + dd)
        plans.append((name, new_name))
    return plans


def apply_renames(root, plans):
    # Preflight the full plan. Each rename also refuses an existing destination.
    for old, new in plans:
        source = root / old
        if source.is_symlink() or not source.is_file() or getattr(source.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("File changed while this run was preparing the renames: " + old)
        if os.path.lexists(root / new):
            raise ValueError("Destination already exists: " + new)
    for old, new in plans:
        if os.name == "nt":
            os.rename(root / old, root / new)
        else:
            os.link(root / old, root / new, follow_symlinks=False)
            os.unlink(root / old)
        print("Renamed:", old, "->", new)


def main(argv=None):
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11 or newer is required.", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(
        description='Move duplicate MP4 dates to unused days. Preview first; rename only with --apply.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples (use .\\ before BAT commands in PowerShell):
  fixfile.bat "C:\\Videos\\Example Folder"
  fixfile.bat "C:\\Videos\\Example Folder" --apply

Preview changes no filenames. Back up important media before --apply.
Existing files are never overwritten; a write error may leave a partial batch.
Python 3.11+ is required. No network access or uploads.
Exit codes: 0 completed preview/rename; 1 operational error; 2 bad arguments.""")
    parser.add_argument("directory", nargs="?", default=".", help="local MP4 folder (default: current directory)")
    parser.add_argument("--apply", action="store_true", help="rename files using the plan; default: preview only")
    parser.add_argument("--max-files", type=int, default=10000, help="maximum directory entries to scan (default: 10000; range: 1-100000)")
    parser.add_argument("--timeout", type=int, default=30, help="scan/planning time limit in seconds (default: 30; range: 1-300)")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.max_files <= 100000 or not 1 <= args.timeout <= 300:
            raise ValueError("Limits: --max-files 1-100000, --timeout 1-300")
        root = local_directory(args.directory)
        plans = plan_renames(root, args.max_files, args.timeout)
        for old, new in plans:
            print("Plan:", old, "->", new)
        print(f"{len(plans)} rename(s). " + ("Applying." if args.apply else "Preview only; use --apply to rename."))
        if args.apply:
            apply_renames(root, plans)
        return 0
    except (OSError, ValueError, OverflowError) as exc:
        if isinstance(exc, FileNotFoundError):
            message = "A required file or folder was not found. Check the selected folder and whether files changed during the run."
        elif isinstance(exc, PermissionError):
            message = "A file or folder could not be accessed. Check permissions and close programs that may be using the files."
        elif isinstance(exc, OSError):
            message = "A file operation failed. Check folder access and free disk space. If applying, check completed renames before retrying."
        else:
            message = str(exc)
        print("ERROR:", message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
