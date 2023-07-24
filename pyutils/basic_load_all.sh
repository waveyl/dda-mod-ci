#!/bin/bash

./build-scripts/basic_get_mods.py | \
            while read mods
            do
                ./cataclysm-tiles --check-mods "${mods}"
            done
