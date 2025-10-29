#!/usr/bin/env python3
"""
Iteratively run --check-mods and hide the first failing JSON file to aggregate
more errors in a single CI job. Restores hidden files at the end. Works on Windows/Linux.

Usage (pwsh example):
  python .\pyutils\check_mods_iter.py --exe .\cataclysm-tiles.exe --modid dda --log-dir .\modci-logs --max-iters 50
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


FIRST_ERROR_PATTERNS = [
    # JsonError from loader
    re.compile(r"Json file\s+(.+?\.json)\b", re.IGNORECASE),
    re.compile(r"Error parsing\s+(.+?\.json)\b", re.IGNORECASE),
    # Generic runtime error including a file path
    re.compile(r"Error loading data.*?((?:[A-Za-z]:)?[^\r\n\t]+?\.json)\b", re.IGNORECASE),
]


def run_check(exe: Path, modid: str) -> str:
    proc = subprocess.run([str(exe), "--check-mods", modid],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          text=True,
                          encoding="utf-8",
                          errors="replace")
    return proc.stdout


def find_first_error_path(log_text: str) -> Path | None:
    for pat in FIRST_ERROR_PATTERNS:
        m = pat.search(log_text)
        if m:
            return Path(m.group(1).strip().strip('"'))
    return None


def safe_hide_file(p: Path) -> Path:
    if not p.exists():
        return p
    hidden = p.with_suffix(p.suffix + ".ci-hide")
    hidden.parent.mkdir(parents=True, exist_ok=True)
    os.replace(p, hidden)
    return hidden


def restore_hidden_files(hidden_list: list[tuple[Path, Path]]):
    for hidden, original in reversed(hidden_list):
        if hidden.exists():
            os.replace(hidden, original)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True, help="Path to cataclysm-tiles or cataclysm")
    ap.add_argument("--modid", required=True, help="Mod id to check")
    ap.add_argument("--log-dir", default="modci-logs", help="Directory to write logs")
    ap.add_argument("--max-iters", type=int, default=50)
    args = ap.parse_args()

    exe = Path(args.exe).resolve()
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    hidden_stack: list[tuple[Path, Path]] = []
    seen_hidden: set[Path] = set()

    try:
        for i in range(1, args.max_iters + 1):
            log_text = run_check(exe, args.modid)
            (log_dir / f"{args.modid}.iter{i}.log").write_text(log_text, encoding="utf-8", errors="replace")

            first = find_first_error_path(log_text)
            if not first:
                break

            cand = Path(first)
            if not cand.exists():
                cand = Path.cwd() / first

            if not cand.exists():
                # couldn't resolve path; stop to avoid hiding random files
                break

            if cand in seen_hidden:
                # already hidden previously, avoid infinite loop
                break

            hidden = safe_hide_file(cand)
            if hidden != cand:
                hidden_stack.append((hidden, cand))
                seen_hidden.add(cand)
            else:
                break

        # Merge logs into one for convenience
        merged = log_dir / f"{args.modid}.log"
        with merged.open("w", encoding="utf-8", errors="replace") as out:
            for part in sorted(log_dir.glob(f"{args.modid}.iter*.log")):
                out.write(f"===== {part.name} =====\n")
                out.write(part.read_text(encoding="utf-8", errors="replace"))
                out.write("\n\n")

        print(f"Wrote merged log: {merged}")
        return 0
    finally:
        restore_hidden_files(hidden_stack)


if __name__ == "__main__":
    sys.exit(main())
