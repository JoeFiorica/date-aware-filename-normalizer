import os
import re
import glob
from datetime import date, timedelta

# -----------------------------------------
# UTILITIES
# -----------------------------------------

def extract_date_anywhere(s):
    """Extract YYYYMMDD from SYYYYEMMDD or other variations."""
    patterns = [
        r"S(\d{4})E(\d{2})(\d{2})",
        r"(\d{4})_(\d{2})-(\d{2})",
        r"(\d{4})[-_](\d{2})[-_](\d{2})",
        r"(\d{4})(\d{2})(\d{2})",
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            y, m1, d1 = m.groups()
            return f"{y}{m1}{d1}"
    return None


def extract_title(filename):
    base = os.path.splitext(filename)[0]
    if base.startswith("S") and " - " in base:
        return base.split(" - ", 1)[1]
    return base


def has_thumbnail(base):
    for pattern in [base + "*.png", base + "*.jpg", base + "*.jpeg"]:
        if glob.glob(pattern):
            return True
    return False


# -----------------------------------------
#  OFFSET SEARCH
# -----------------------------------------

def find_free_mmdd(year, month, day, forbidden):
    """
    Find the next free MMDD.
    NEW LOGIC:
      1. Try +1, +2, +3, ... forward first
      2. If forward exhausted, try -1, -2, -3 backward
    """

    original = date(int(year), int(month), int(day))

    # how far forward/backward we are willing to search
    max_spread = 400  # well beyond year length; you have ~250 files

    # 1️⃣ Try forward +1, +2, +3 ...
    for offset in range(1, max_spread):
        try_date = original + timedelta(days=offset)
        mmdd = try_date.strftime("%m%d")

        if mmdd not in forbidden:
            return (
                try_date.strftime("%m"),
                try_date.strftime("%d"),
            )

    # 2️⃣ Try backward -1, -2, -3 ...
    for offset in range(1, max_spread):
        try_date = original - timedelta(days=offset)
        mmdd = try_date.strftime("%m%d")

        if mmdd not in forbidden:
            return (
                try_date.strftime("%m"),
                try_date.strftime("%d"),
            )

    raise RuntimeError("No free MMDD found — impossible with 250 files")

# -----------------------------------------
# MAIN LOGIC
# -----------------------------------------

def main():
    # -------------------------------------
    # PASS 1 — Count MMDD occurrences
    # -------------------------------------
    mmdd_count = {}  # {'0122': 1, '0123': 3, ...}

    files = sorted([f for f in os.listdir(".") if f.lower().endswith(".mp4")])

    extracted = {}  # filename -> (year, mmdd)

    for f in files:
        base = os.path.splitext(f)[0]
        d = extract_date_anywhere(base)
        if not d:
            continue

        year = d[:4]
        mmdd = d[4:8]

        # Skip counting if thumbnail exists
        if has_thumbnail(base):
            continue

        extracted[f] = (year, mmdd)
        mmdd_count[mmdd] = mmdd_count.get(mmdd, 0) + 1

    # -------------------------------------
    # PART 2 — Track forbidden MMDDs
    # (any MMDD appearing in folder counts as forbidden)
    # -------------------------------------
    forbidden = set(mmdd_count.keys())

    # Also track MMDDs assigned DURING renaming
    used_in_process = set()

    # -------------------------------------
    # PASS 2 — Process for renaming
    # -------------------------------------
    seen_for_mmdd = {}  # tracks how many times we've processed a given mmdd

    for f in files:
        base, ext = os.path.splitext(f)
        real_ext = ext  # preserve extension

        # skip if thumbnail exists
        if has_thumbnail(base):
            print(f"\n🖼 Skipping {f} (thumbnail detected)")
            continue

        # get extracted date for this file
        if f not in extracted:
            print(f"\n📛 No date found in {f} → skipping")
            continue

        year, mmdd = extracted[f]
        count = mmdd_count[mmdd]

        print(f"\n🎬 Processing: {f}")
        print(f"  Found date MMDD={mmdd} YEAR={year}")

        # first time seeing this MMDD?
        seen_for_mmdd[mmdd] = seen_for_mmdd.get(mmdd, 0) + 1

        # ---------------------------------
        # CASE 1 — unique date → KEEP
        # ---------------------------------
        if count == 1:
            print("  ✔ Unique MMDD → keeping original")
            used_in_process.add(mmdd)
            continue

        # ---------------------------------
        # CASE 2 — duplicate:
        # Keep the first occurrence, offset later ones
        # ---------------------------------
        if seen_for_mmdd[mmdd] == 1:
            print("  ✔ First duplicate instance → keeping original")
            used_in_process.add(mmdd)
            continue

        # ---------------------------------
        # CASE 3 — must offset (2nd, 3rd, 4th instance...)
        # ---------------------------------
        print("  ❗ Duplicate instance → offset required")

        # convert MMDD back into a base date in its actual year
        base_date = date(int(year), int(mmdd[:2]), int(mmdd[2:4]))

        mm, dd = find_free_mmdd(year, mmdd[:2], mmdd[2:4], forbidden | used_in_process)

        new_mmdd = mm + dd
        new_name = f"S{year}E{mm}{dd} - {extract_title(f)}{real_ext}"

        print(f"  → Assigned new MMDD={new_mmdd}")
        print(f"  → Renaming to: {new_name}")

        os.rename(f, new_name)

        used_in_process.add(new_mmdd)

    print("\n\n✅ Completed successfully.")


if __name__ == "__main__":
    main()
