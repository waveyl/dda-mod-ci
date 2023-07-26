#!/bin/bash

# Script made specifically for running tests on GitHub Actions
{
echo "Using bash version $BASH_VERSION"
#set -x pipefail

cata_test_opts="--min-duration 20 --use-colour yes --rng-seed time ${EXTRA_TEST_OPTS}"
[ -z $NUM_TEST_JOBS ] && num_test_jobs=3 || num_test_jobs=$NUM_TEST_JOBS

# We might need binaries installed via pip, so ensure that our personal bin dir is on the PATH
export PATH=$HOME/.local/bin:$PATH
# export so run_test can read it when executed by parallel
} &> /dev/null
function run_test
{
    {
    #set -o pipefail
    test_exit_code=0 sed_exit_code=0 exit_code=0
    test_bin=$1
    prefix=$2
    shift 2
    } &> /dev/null
    $WINE "$test_bin" ${cata_test_opts} "$@" 2>&1 | sed -E 's/^(::(warning|error|debug)[^:]*::)?/\1'"$prefix"'/' || test_exit_code="${PIPESTATUS[0]}" sed_exit_code="${PIPESTATUS[1]}"
    if [ "$test_exit_code" -ne "0" ]
    then
        echo "$3test exited with code $test_exit_code"
        exit_code=1
    fi
    if [ "$sed_exit_code" -ne "0" ]
    then
        echo "$3sed exited with code $sed_exit_code"
        exit_code=1
    fi
    return $exit_code
}
export -f run_test

# Run the tests with all the mods, without actually running any tests,
# just to verify that all the mod data can be successfully loaded.
# Because some mods might be mutually incompatible we might need to run a few times.

./build-scripts/full_get_mods.py | \
            while read mods
            do
            {
                run_test ./tests/cata_test "(${mods})=>" '~*' --user-dir=all_modded --mods="${mods}"
                result=$?
                if [[ $result -eq 0 ]]
                then
                    echo "${mods}: OK" >> result.json
                fi
                if [[ $result -eq 1 ]]
                then
                    echo "${mods}: ERROR" >> result.json
                fi
            }
            done
