OLD = '''    # the PAPER is the model's own training window: -c is NOT set -
    # llama-server defaults ctx to 0 = load from model, so the
    # window is exactly n_ctx_train, one parameter less to worry
    ctx = bell_window(state, fam, models_dir) or 262144
    records: list[dict[str, Any]] = []
    # THE KV PROGRESS (the author's ruling): a dot per combination,
    # the count at every multiple of 7 - the 49-combo sweep reads
    # as ......7......14......21 ......49, live in the console
    n_kv_ladder = len(KV_LADDER)
    try:
        n_combo = 0
        for k_quant in KV_LADDER:
            for v_quant in KV_LADDER:
                rec = _run_combo(
                    fam,
                    rung,
                    k_quant,
                    v_quant,
                    gguf,
                    ctx,
                    models_dir,
                    port,
                    entropy_get,
                )
                records.append(rec)
                n_combo += 1
                print(".", end="", flush=True)
                if n_combo % n_kv_ladder == 0:
                    print(n_combo, end="", flush=True)
        print()  # the sweep's line ends
    finally:'''

NEW = '''    # the PAPER is the model's own training window: -c is NOT set -
    # llama-server defaults ctx to 0 = load from model, so the
    # window is exactly n_ctx_train, one parameter less to worry
    ctx = bell_window(state, fam, models_dir) or 262144

    # THE SWEEP RESUME (the author's ruling): the state's results
    # ARE the kv-combo memory - every completed combo's record is
    # in the state the moment it lands (saved per combo below), so a
    # stop mid-sweep re-picks the pair and SKIPS the combos whose
    # records already exist; the sweep resumes at the next untested
    # (k, v) instead of starting from 0. The answer files stay too
    # (per combo, on disk), but the RECORD is the resume's truth: it
    # carries the verdict, not just the prose.
    done_combos = {
        (r.get("k_quant"), r.get("v_quant"))
        for r in state.get("results", [])
        if r.get("fam") == fam and r.get("rung") == rung
    }
    records: list[dict[str, Any]] = [
        r
        for r in state.get("results", [])
        if r.get("fam") == fam and r.get("rung") == rung
    ]
    n_resume = len(done_combos)

    # THE KV PROGRESS (the author's ruling): a dot per combination,
    # the count at every multiple of 7 - the 49-combo sweep reads
    # as ......7......14......21 ......49, live in the console.
    # A resumed sweep starts at its true position: (n_resume // 7)
    # marker segments print at once, then the live dots continue.
    n_kv_ladder = len(KV_LADDER)
    try:
        n_combo = 0
        for k_quant in KV_LADDER:
            for v_quant in KV_LADDER:
                if (k_quant, v_quant) in done_combos:
                    continue  # already measured: the resume skips it
                rec = _run_combo(
                    fam,
                    rung,
                    k_quant,
                    v_quant,
                    gguf,
                    ctx,
                    models_dir,
                    port,
                    entropy_get,
                )
                records.append(rec)
                # THE PER-COMBO PERSISTENCE: the record lands in the
                # state NOW - a crash after this combo keeps it, the
                # resume after the crash never re-runs it
                state.setdefault("results", []).append(rec)
                state["results"] = state["results"][-5000:]
                _state_store.save_state(state_file, state)
                n_combo += 1
                print(".", end="", flush=True)
                if (n_resume + n_combo) % n_kv_ladder == 0:
                    print(n_resume + n_combo, end="", flush=True)
        print()  # the sweep's line ends
        if n_resume:
            print(f"[ei] sweep resumed: {n_resume} combos already done, {n_combo} run")
    finally:'''
