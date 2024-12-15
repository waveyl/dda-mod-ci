#!/bin/bash

# Script made specifically for running tests on GitHub Actions
{
echo "Using bash version $BASH_VERSION"
set -x pipefail

cata_test_opts="--min-duration 20 --use-colour yes --rng-seed time --drop-world --user-dir=all_modded ${EXTRA_TEST_OPTS}"
num_test_jobs=1

# We might need binaries installed via pip, so ensure that our personal bin dir is on the PATH
export PATH=$HOME/.local/bin:$PATH
# export so run_test can read it when executed by parallel
} &> /dev/null
function run_test
{
    {
    set -o pipefail
    test_bin=./tests/cata_test
    mods="$@"
    prefix="(${mods})=>"
    shift 2
    } &> /dev/null
    $WINE "$test_bin" ${cata_test_opts} '[force_load_game]' --mods="${mods}" 2>&1 | sed -E 's/^(::(warning|error|debug)[^:]*::)?/\1'"$prefix"'/' > "${mods}.data" || result="${PIPESTATUS[0]}"
    if [[ $result -eq 0 ]]
    then
        echo "${mods}: OK" >> result.json
    else
        echo "error" >> error.sig
        echo "${mods}: ERROR" >> result.json
        cat "${mods}.data"
    fi
}
export -f run_test

# Run the tests with all the mods, without actually running any tests,
# just to verify that all the mod data can be successfully loaded.
# Because some mods might be mutually incompatible we might need to run a few times.

./build-scripts/full_get_mods.py | parallel -j $num_test_jobs run_test
cat result.json

if [ ! -f "error.sig" ];then
    exit 0
else
    exit 1
fi

