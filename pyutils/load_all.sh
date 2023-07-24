#!/bin/bash

./build-scripts/get_mods.py | \
            while read mods
            do
                ./cataclysm-tiles --check-mods "${mods}"
            done
