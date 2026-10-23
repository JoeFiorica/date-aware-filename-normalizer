# Date-Aware Filename Normalizer

Resolve duplicate month/day dates in top-level MP4 filenames.
Unique dates and videos with PNG/JPG/JPEG thumbnail companions stay unchanged.
Output names use `SYYYYEMMDD - Title.mp4`.

## Requirements

Windows with Python 3.11+ available as `python`. Keep `fixfile.bat` and `fixfile.py` together.
No Python packages or network access are needed.

## Usage

Double-click `fixfile.bat` to preview MP4s beside the launcher, or give a local folder:

```bat
fixfile.bat "C:\Videos\Example Folder"
fixfile.bat "C:\Videos\Example Folder" --apply
python fixfile.py --help
```

Without `--apply`, no file is renamed. Review the plan and back up valuable media first.
Commands with arguments finish without pausing. In PowerShell, prefix BAT commands
with `.\`. Quote paths containing spaces.

## Behavior

- Recognizes `S2024E0122`, `2024_01-22`, `2024-01-22` and `20240122`.
- Keeps the first duplicate in case-insensitive filename order and moves later
  duplicates to the next unused month/day, searching forward first.
- Dates wrap within the original year; invalid leap days are never assigned.
  Month/day reservations span years and include thumbnail-protected dated MP4s.
- A thumbnail protects a video when its name starts with the video's literal stem,
  ignoring case. Thumbnail names stay unchanged.
- Undated and invalid-date files are reported and skipped. Only regular top-level
  MP4s are considered; subfolders and extension case stay unchanged.

## Outputs

Plans, skipped files and completed renames print to the console. No report files are created.
Exit codes: 0 completed preview/application; 1 operational error; 2 bad arguments.

## Safety and privacy

Media bytes are unchanged and existing destinations are never overwritten.
A conflicting plan stops before renaming. Linked files and network folders are refused.
Avoid changing the folder during a run: a filesystem error can leave a partial batch.
Keep the console output to help recover manually. No telemetry or uploads;
console filenames may identify your library.

The default scan limit is 10,000 entries and 30 seconds. Use `--max-files` (up to 100000)
and `--timeout` (1-300 seconds) to adjust.

## Troubleshooting

Check `python --version`; install Python separately with PATH enabled if missing.
Run `python fixfile.py "C:\Videos\Example Folder"` to see errors directly.
To try it safely, put two empty MP4s with the same date in a disposable folder:
preview leaves both unchanged; `--apply` moves only the second; the next preview is empty.

Report issues with example filenames, the command and expected/actual result.
Omit personal filenames and media.
