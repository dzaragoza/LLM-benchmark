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
    return {"families": {"Fam": {"spec": "org/repo", "runs": {}, "selected": None}}}


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
        fb.save_state(path, {"families": {"X": {"spec": "y/z", "runs": {}, "selected": "Q8_0"}}})
        assert json.loads((tmp_path / "state.json").read_text()) == {"families": {}}
    finally:
        fb.DRY_RUN_ACTIVE = False


class TestStateSchema:
    """Pins: R-22. The state file carries a schema: corruption fails
    LOUDLY with the exact offending path - never the silent
    start-fresh that discarded measured cells, never a bare
    json.load crash from the orchestrator's unguarded loader."""

    def _load(self, tmp_path, state):
        import json as _json

        p = tmp_path / "state.json"
        p.write_text(_json.dumps(state))
        return fb.load_state(str(p))

    def _fam(self, state):
        import copy

        ok = copy.deepcopy(state)
        return ok, ok["families"]["Fam"]

    def test_valid_state_passes(self, tmp_path, state):
        ok, fam = self._fam(state)
        fam["certify_vt"] = {"8192": {"1": 5, "2": {"v": 4, "rung": "Q8_0"}}}
        fam["v7"] = {"4096": {"score": 0.5, "ctx": 4096}}
        assert self._load(tmp_path, ok) == ok

    def test_corrupt_cell_record_names_the_path(self, tmp_path, state):
        bad, fam = self._fam(state)
        fam["certify_vt"] = {"8192": {"3": "five"}}
        with pytest.raises(fb._state_store.StateSchemaError) as e:
            self._load(tmp_path, bad)
        assert "families.Fam.certify_vt.8192.3" in str(e.value)

    def test_record_object_without_v_names_the_path(self, tmp_path, state):
        bad, fam = self._fam(state)
        fam["certify_speed"] = {"4096": {"1": {"rung": "Q8_0"}}}
        with pytest.raises(fb._state_store.StateSchemaError) as e:
            self._load(tmp_path, bad)
        assert "lacks 'v'" in str(e.value)

    def test_corrupt_v7_score_names_the_path(self, tmp_path, state):
        bad, fam = self._fam(state)
        fam["v7"] = {"2048": {"score": "high"}}
        with pytest.raises(fb._state_store.StateSchemaError) as e:
            self._load(tmp_path, bad)
        assert "families.Fam.v7.2048.score" in str(e.value)

    def test_boolean_cell_record_rejected(self, tmp_path, state):
        """Booleans are int subclasses - a stored True is a retired
        boolean-graded record, not a graded count; the schema rejects
        it (the never-re-measure store re-measures it instead of
        trusting it at an unverifiable bar)."""
        bad, fam = self._fam(state)
        fam["certify_vt"] = {"8192": {"1": True}}
        with pytest.raises(fb._state_store.StateSchemaError):
            self._load(tmp_path, bad)

    def test_unwritable_shape_at_families_level(self, tmp_path):
        with pytest.raises(fb._state_store.StateSchemaError) as e:
            self._load(tmp_path, {"families": []})
        assert "families: expected object, got list" in str(e.value)

    def test_orchestrator_loader_is_the_guarded_one(self):
        """The orchestrator's load_state IS state_store.load_state -
        the unguarded raw json.load duplicate (full_benchmark.py,
        session 43) is gone; there is exactly one loader."""
        import inspect

        src = inspect.getsource(fb.load_state)
        assert "_state_store.load_state(path)" in src and "json.load" not in src
