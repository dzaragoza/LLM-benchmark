"""The state-file contract (addendum 87).

The addendum-79 lesson: a dry run that writes the state file poisons
the real run (phases marked done with no file on disk). save_state
guards at a single choke point via the module flag DRY_RUN_ACTIVE.
"""

import json

import pytest

import full_benchmark as fb


@pytest.fixture
def state():
    return {"families": {"Fam": {"spec": "org/repo",
                                 "runs": {}, "selected": None}}}


def test_load_state_missing_file(tmp_path):
    """No state file -> a fresh empty structure, never a crash."""
    s = fb.load_state(str(tmp_path / "absent.json"))
    assert s == {"families": {}}


def test_save_and_load_roundtrip(tmp_path, state):
    path = str(tmp_path / "state.json")
    fb.save_state(path, state)
    assert fb.load_state(path) == state


def test_dry_run_never_writes(tmp_path, state):
    """THE addendum-79 invariant: under DRY_RUN_ACTIVE, save_state is
    a no-op - the file is not created, not truncated, not touched."""
    path = str(tmp_path / "state.json")
    fb.DRY_RUN_ACTIVE = True
    try:
        fb.save_state(path, state)
        assert not (tmp_path / "state.json").exists()
        # an EXISTING file survives untouched too
        fb.DRY_RUN_ACTIVE = False
        fb.save_state(path, state)
        before = (tmp_path / "state.json").read_text()
        fb.DRY_RUN_ACTIVE = True
        state["families"]["Fam"]["selected"] = "Q8_0"
        fb.save_state(path, state)
        assert (tmp_path / "state.json").read_text() == before
    finally:
        fb.DRY_RUN_ACTIVE = False


def test_dry_run_writes_nothing_even_after_real_save(tmp_path):
    """The flag is module-global state: once set, EVERY save is a no-op
    until cleared - the guard must not depend on call order."""
    path = str(tmp_path / "state.json")
    fb.save_state(path, {"families": {}})
    fb.DRY_RUN_ACTIVE = True
    try:
        fb.save_state(path, {"families": {"X": {"spec": "y/z",
                                                "runs": {},
                                                "selected": "Q8_0"}}})
        assert json.loads((tmp_path / "state.json").read_text()) == \
            {"families": {}}
    finally:
        fb.DRY_RUN_ACTIVE = False
