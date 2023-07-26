#!/usr/bin/env python3
import glob
import json
for info in glob.glob('data/mods/*/modinfo.json'):
    with open(info, encoding='utf-8') as f:
        mod_info = json.load(f)
    mod_info = json.load(open(info,'r', encoding='utf-8'))
    for e in mod_info:
            if(e["type"] == "MOD_INFO" and e["id"] != "dda" and
                ("obsolete" not in e or not e["obsolete"])):
                e["obsolete"] = True
    with open(info,'w', encoding='utf-8') as f:
        json.dump(mod_info,f,ensure_ascii=False)
