#!/usr/bin/env python3
"""
Scan a mods directory (e.g. Kenan-Structured-Modpack), link/copy each mod into
Cataclysm-DDA/data/mods, then run --check-mods for each using check_mods_iter.py.

Example:
  python .\pyutils\run_all_mods.py \
    --cdda ./Cataclysm-DDA \
    --mods ./Kenan-Structured-Modpack \
    --exe ./Cataclysm-DDA/build/cataclysm \
    --log-dir ./modci-logs \
    --max-iters 80 \
    --fail-on-error true
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import re
from typing import Iterable, Tuple


def find_mod_ids(mod_dir: Path) -> Iterable[Tuple[str, Path]]:
    """Yield (mod_id, dirpath) for each mod folder under mod_dir.
    Detect by scanning json files for entries with {"type":"MOD_INFO","id":...}.
    """
    for sub in sorted([p for p in mod_dir.iterdir() if p.is_dir()]):
        found_id = None
        # scan up to a reasonable number of files to avoid excessive cost
        candidates = list(sub.rglob("*.json"))[:200]
        for jf in candidates:
            try:
                with jf.open("r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
            except Exception:
                # fallback: text scan for MOD_INFO id (tolerate comments)
                try:
                    text = jf.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                # Very permissive: look for an object containing type:"MOD_INFO" followed by id:"..."
                # This is not a full JSON parser but works for common patterns with comments
                modinfo_blocks = re.finditer(r"\{[^\}]*?\btype\s*:\s*\"MOD_INFO\"[^\}]*?\}", text, re.IGNORECASE | re.DOTALL)
                for blk in modinfo_blocks:
                    blk_text = blk.group(0)
                    m_id = re.search(r"\bid\s*:\s*\"([^\"]+)\"", blk_text)
                    if m_id:
                        found_id = m_id.group(1)
                        break
                if found_id:
                    break
                continue
            items = data if isinstance(data, list) else [data]
            for it in items:
                if isinstance(it, dict) and str(it.get("type")) == "MOD_INFO":
                    mid = it.get("id") or it.get("ident")
                    if isinstance(mid, str):
                        found_id = mid
                        break
            if found_id:
                break
        if found_id:
            yield (found_id, sub)


def ensure_mod_installed(mod_src: Path, mods_dest_root: Path) -> Path:
    target = mods_dest_root / mod_src.name
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Prefer symlink to save time/space on Linux runners
        os.symlink(mod_src.resolve(), target, target_is_directory=True)
    except Exception:
        shutil.copytree(mod_src, target)
    return target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdda", required=True, help="Path to Cataclysm-DDA repo root")
    ap.add_argument("--mods", required=True, help="Path to Kenan-Structured-Modpack root")
    ap.add_argument("--exe", required=True, help="Path to built cataclysm executable")
    ap.add_argument("--log-dir", default="modci-logs", help="Directory to write logs")
    ap.add_argument("--max-iters", type=int, default=50)
    ap.add_argument("--only", default="", help="Optional space/comma separated mod ids to limit run")
    ap.add_argument("--fail-on-error", default="true", choices=["true", "false"], help="Exit non-zero if any errors detected")
    args = ap.parse_args()

    cdda = Path(args.cdda).resolve()
    mods_root = Path(args.mods).resolve()
    exe = Path(args.exe).resolve()
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    mods_dest = cdda / "data" / "mods"
    mods_dest.mkdir(parents=True, exist_ok=True)

    # allow space/comma separated list
    only_tokens = [t for t in re.split(r"[\s,]+", args.only.strip()) if t]
    selected_only = set(only_tokens)

    discovered: list[Tuple[str, Path]] = list(find_mod_ids(mods_root))
    if selected_only:
        discovered = [(mid, p) for (mid, p) in discovered if mid in selected_only]

    if not discovered:
        print("No mods discovered to run.")
        return 0

    print(f"Discovered {len(discovered)} mods.")

    any_errors = False
    for mid, src in discovered:
        print(f"== Preparing mod {mid} from {src}")
        ensure_mod_installed(src, mods_dest)
        out_dir = log_dir / mid
        out_dir.mkdir(parents=True, exist_ok=True)
        merged_log = out_dir / f"{mid}.log"

        cmd = [sys.executable, str(Path(__file__).with_name("check_mods_iter.py")),
               "--exe", str(exe), "--modid", mid, "--log-dir", str(out_dir),
               "--max-iters", str(args.max_iters)]

        print("Running:", " ".join(cmd))
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        (out_dir / "runner.out.txt").write_text(proc.stdout, encoding="utf-8", errors="replace")

        if merged_log.exists():
            # Heuristic: if merged log contains any "DEBUG: error" markers or "JsonError" we flag errors
            text = merged_log.read_text(encoding="utf-8", errors="replace")
            if "Json file" in text or "Error loading" in text or "JsonError" in text:
                any_errors = True

    (log_dir / "SUMMARY.txt").write_text(
        ("Errors detected" if any_errors else "No errors detected"),
        encoding="utf-8",
    )

    return 1 if (args.fail_on_error == "true" and any_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
