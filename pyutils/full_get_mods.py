#!/usr/bin/env python3

# The goal of this script is to print out sets of mods for testing.  Each line
# of output is a comma-separated list of mods.  Together the lines should cover
# all in-repo mods, in as few lines as possible.  Each line must contain only
# mods which are mutually compatible.

import glob
import json

mods_this_time = []

def add_mods(mods):
    for mod in mods:
        if mod not in all_mod_dependencies:
            # Either an invalid mod id, or blacklisted.
            return False
    for mod in mods:
        if mod not in mods_this_time:
            if add_mods(all_mod_dependencies[mod]):
                mods_this_time.append(mod)
            else:
                return False
    return True


def print_modlist(modlist, master_list):
    print(','.join(modlist))
    master_list -= set(modlist)
    modlist.clear()


all_mod_dependencies = {}
all_mods = set()

for info in glob.glob('data/mods/*/modinfo.json'):
    mod_info = json.load(open(info, encoding='utf-8'))
    for e in mod_info:
        if(e["type"] == "MOD_INFO"):
            if("id" not in e):
                ident = e["ident"]
            else:
                ident = e["id"]
            all_mod_dependencies[ident] = e.get("dependencies", [])
            if("obsolete" not in e or not e["obsolete"]):
                all_mods.add(ident)

mods_remaining = set()

for mod in all_mods:
    add_mods([mod])
    print_modlist(mods_this_time, mods_remaining)
