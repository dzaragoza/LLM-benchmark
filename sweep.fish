#!/usr/bin/env fish
# sweep.fish -- the one benchmark command (addendum 272).
#
# The author's ruling: no more ad-hoc invocations - every run is THE
# SAME sweep, so none of the command-drift bugs (wrong roster count,
# a forgotten budget, a stale checkout) can happen again.
#
# The fixed protocol:
#   1. git pull -- always current
#   2. families = 42 -- the fixed roster cut
#   3. the FULL budget sweep: 0.25, 0.5, 1, 2, 4, 8 GiB, n=3 seeds each
#
# Everything already measured skips instantly; only new cells measure.
# Interrupt anywhere; re-running the same command resumes.

git pull --ff-only; or exit 1

# the registry update: re-pull every family's config extract so new
# roster additions (and geometry fixes) land before the sweep plans
python3 etc/registry_data.py fetch; or echo "WARNING: registry fetch failed - continuing with the checked-in store"

for budget in 0.25 0.5 1.0 2.0 4.0 8.0
    echo ""
    echo "============================================================"
    echo "sweep: budget $budget GiB, roster 42, n=3"
    echo "============================================================"
    python3 full_benchmark.py --task v7 --v7-families 42 --v7-grammar v71 --v7-n 3 --v7-budget-gib $budget
end
