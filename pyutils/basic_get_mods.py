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
