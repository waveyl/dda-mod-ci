#!/usr/bin/env python3
"""
Scan a mods directory (already copied into Cataclysm-DDA/data/mods) and output
one mod id per line by locating entries with {"type":"MOD_INFO","id":...}.

Usage:
  python ./pyutils/basic_get_mods.py --mods-dir ./data/mods

Optional: --only "modA modB" (space/comma separated) to limit.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable


def discover_mod_id(mod_dir: Path) -> str | None:
    # Try JSON load first, fallback to regex to tolerate comments
    jsons = list(mod_dir.rglob("*.json"))[:300]
    for jf in jsons:
        try:
            data = json.loads(jf.read_text(encoding="utf-8", errors="replace"))
            objs = data if isinstance(data, list) else [data]
            for it in objs:
                if isinstance(it, dict) and str(it.get("type")) == "MOD_INFO":
                    mid = it.get("id") or it.get("ident")
                    if isinstance(mid, str):
                        return mid
        except Exception:
            try:
                txt = jf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for blk in re.finditer(r"\{[^\}]*?\btype\s*:\s*\"MOD_INFO\"[^\}]*?\}", txt, re.I | re.S):
                m = re.search(r"\bid\s*:\s*\"([^\"]+)\"", blk.group(0))
                if m:
                    return m.group(1)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods-dir", default="./data/mods")
    ap.add_argument("--only", default="", help="Space/comma separated mod ids to limit")
    args = ap.parse_args()

    only = set([t for t in re.split(r"[\s,]+", args.only.strip()) if t])
    root = Path(args.mods-dir) if hasattr(args, 'mods-dir') else Path(args.mods_dir)
    # The above line ensures compatibility if argparse normalizes to mods_dir
    if not root.exists():
        root = Path(args.mods_dir)

    results: list[str] = []
    for sub in sorted([p for p in root.iterdir() if p.is_dir()]):
        mid = discover_mod_id(sub)
        if not mid:
            continue
        if only and mid not in only:
            continue
        results.append(mid)

    for mid in results:
        print(mid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3

import glob
import json

def print_modlist(modlist, master_list):
    print(','.join(modlist))
    master_list -= set(modlist)
    modlist.clear()

all_mods = set()

for info in glob.glob('data/mods/*/modinfo.json'):
    mod_info = json.load(open(info, encoding='utf-8'))
    for e in mod_info:
        if(e["type"] == "MOD_INFO" and
                ("obsolete" not in e or not e["obsolete"])):
            if("id" not in e):
                ident = e["ident"]
            else:
                ident = e["id"]
            all_mods.add(ident)

mods_remaining = set()

for mod in all_mods:
    print_modlist([mod], mods_remaining)
