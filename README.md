# Date-Aware Filename Normalizer
A Python tool for safely normalizing date-based filenames (MMDD) without disrupting existing unique dates. When multiple files share the same date, the tool automatically assigns the nearest unused date using a ±1, ±2, ±3 offset search. Thumbnail companions (PNG/JPG) are always respected and preserved.

## ✨ Features
- ✔ Keeps original dates when they are unique  
- ✔ Reassigns duplicates only (never renames unnecessarily)  
- ✔ Nearest free date selection using expanding offset search  
- ✔ Avoids collisions within the same year  
- ✔ Skips files with thumbnails to preserve video–image pairs  
- ✔ Clear logs showing detection, decisions, and assignments  
- ✔ Works on large folders (100–1000+ files)

## 📌 How It Works
1. Extracts dates from filenames (SYYYYE MMDD - Title.ext or standard YYYYMMDD formats).  
2. Keeps the original date if it's unique.  
3. If a duplicate date appears:
   - Searches for the closest unused MMDD  
4. Renames *only* duplicates.  
5. Displays clean, human-readable logs for every file processed.
