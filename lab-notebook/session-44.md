# Session 44 - the no-backward-compatibility ruling

## Addendum 109 - R-21: no backward compatibility

The author's ruling: "Remove any backward compatibility in full
benchmark. In this repo nothing is backward compatible except
explicitly requested." Registered as R-21 and pinned by
tests/test_precommit_env.py.

Removed in this pass:

- `v6_prototype.py` - deleted outright. It was the v6.1 sketch
  (superseded by the v7 reframe the same day, session 42) and was
  referenced by nothing: no test, no hook, no requirement. The
  b10964 build path it and v7 share is unchanged.
- `find_server`'s pre-reorg HOME fallback
  (`~/technical_reports/llama-b10964-gpu`) - `infra/llama_server.py`
  now resolves the binary repo-relative only and returns None when
  absent; `full_benchmark.py`'s check_tooling already fails loudly
  with install guidance in that case, so the fallback was a silent
  second chance, exactly the kind of compat R-21 retires.
- `certify_cells` (bench/state_store.py) - the FWE re-grading reader
  for the retired `certify` namespace. Historical certify/certify_arc
  cells stay in state files as history, but nothing reads them;
  the reader is gone (R-05 RETIRED finished).
- `_task_store`'s `.get(task, "certify")` fallback - an unknown task
  now KeyErrors instead of silently writing into the retired FWE
  namespace.

Kept, deliberately (not compat shims - the variant-attribution
ruling of session 40, addendum 26, and R-05's "history stays
readable"):

- `stored_variant`/`legacy` plain-int cell attribution: the
  never-re-measure rule (addendum 8) requires it - cells measured
  before variant tracking are attributed to the stored selection,
  so they load instead of being re-measured at real GPU cost.
- `--task all` (the combined speed+vt controller): a live mode, not
  a compat path.
- The `reports/` study's "legacy encodings" wording: prose about
  GGUF legacy-vs-K-quant formats, unrelated to code compat.

Coverage note: 12 tests in test_precommit_env.py now (10 + 2 R-21
pins).

## Addendum 110 - R-22: the state schema

The author: "Yes schemas are helpful. Databases out until we really
need them. No XML please." Parquet explained (columnar, typed,
compressed - wrong for our small nested data, right as a derived
results export if the full grid ever wants cross-cell analytics).

R-22: `validate_state` in bench/state_store.py. The failure modes it
replaces:

- full_benchmark.py had a SECOND, unguarded `load_state` (raw
  json.load, crash on corrupt) - now the orchestrator's loader is
  the guarded one, exactly one loader.
- state_store's old loader caught ALL exceptions and started
  fresh - silent loss of measured cells (the never-re-measure
  store's worst failure).

The schema is strict where machinery reads typed values (cell
records: int or {v,...}; v7 score: number or null) and loose where
state is prose (verdicts, tournament metadata). StateSchemaError is
a plain exception, so the crash rail owns it: traceback to
results.txt, git tail runs, the corrupt file is never wiped.

The R-22 pin class found its own test bug while at it: the corrupt
fixtures must nest under families.<name>, not at the state top
level - the validator correctly ignored the misplaced ones
(schemas work).
