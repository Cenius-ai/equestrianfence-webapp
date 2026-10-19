#!/usr/bin/env bash
# EquestrianFence - non-interactive end-to-end demo.
#
#   bash demo.sh
#
# Walks a horse owner from "what does this do" to a bought-and-paid-for post
# count and a printable gate checklist. Nothing is written to disk, no network
# is used, and no step waits for input.
set -u
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
FENCE=("$PYTHON" equestrian_fence.py)

step() {
    printf '\n%s\n' "--------------------------------------------------------------"
    printf '%s\n' "$1"
    printf '%s\n' "--------------------------------------------------------------"
}

step "1/7  Help - the three subcommands and a worked example each"
"${FENCE[@]}" --help

step "2/7  Layout a 100 x 50 ft arena paddock on 10 ft post spacing"
"${FENCE[@]}" layout --length 100 --width 50 --spacing 10

step "3/7  Layout the 160 x 120 ft back field on 12 ft post spacing"
"${FENCE[@]}" layout --length 160 --width 120 --spacing 12

step "4/7  Spacing - fit equal segments to the 100 ft north run at 12 ft"
"${FENCE[@]}" spacing --run 100 --spacing 12

step "5/7  Spacing - the same run at an even 10 ft (no adjustment needed)"
"${FENCE[@]}" spacing --run 100 --spacing 10

step "6/7  Gate checklist - 2 gates at 12 ft, printable walk-the-line checks"
"${FENCE[@]}" checklist --gates 2 --gate-width 12

step "7/7  Bad input is a plain message and exit code 2 (no traceback)"
printf '$ %s layout --length 100 --width 50 --spacing 0\n' "$PYTHON"
"${FENCE[@]}" layout --length 100 --width 50 --spacing 0
printf '(exit code %s)\n' "$?"

printf '\n%s\n' "Machine-readable output for scripts:"
printf '$ %s layout --length 100 --width 50 --spacing 10 --json\n' "$PYTHON"
"${FENCE[@]}" layout --length 100 --width 50 --spacing 10 --json

printf '\nDemo complete. Nothing was written to disk.\n'
exit 0
