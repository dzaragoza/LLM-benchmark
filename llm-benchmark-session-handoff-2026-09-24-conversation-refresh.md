# LLM-benchmark Session Handoff — 2026-09-24

*Compact state-of-the-conversation for the next session. Companion artifact: the lab notebook canvas (Sessions 1–25, fully concatenated, with all rulings, patches, and prediction grades). Repo: github.com/dzaragoza/LLM-benchmark (main branch).*

## People & conventions

- **Daniela Zaragoza Rodriguez** = the **author** (never "owner" — third-party readers see the notebook; author ruled on this and the notebook was swept, 76 occurrences → author). In chat: Daniela is fine.
- Working style: pre-registered predictions, scientific method, byte-exact verification rituals, no guessed repo/asset names, corrections acknowledged plainly. Terminology rule + "study #2 is a DRAFT, not published" are logged in the notebook (Session 24 rev. 4 correction).
- Machine: **ThinkPad T14s Gen 4 AMD** (Ryzen 7 7840U, 780M, LPDDR5-6400 → the 102.4 GB/s witness machine; dmidecode-confirmed, SMBIOS says LPDDR5 quad-32-bit channels). OS: openSUSE Slowroll. Floor ruling: **20 t/s** (comfort threshold, rung-stress design).

## Current rosters (pre-registered, rules 1–8)

Selection rules now on record (README): (1) Ollama popularity walk-down, snapshot 2026-09-23/24; (2) distinct families (family = publisher/owner, so deepseek-r1 ≠ qwen despite Qwen base); (3) non-thinking category must *run* non-thinking mode; (4) size class passes the speed gate; (5) first-party HF weights only; (6) ≥1 published paper in family (LFM2 report covers lineage — but lfm2.5 was later removed as sub-class); (7) latest generation supersedes (qwen3.5 > qwen3; phi4-mini > phi3); (8) **hybrids allowed in BOTH categories, always run in the category's mode** (mode control is protocol, logged per run).

**Non-thinking (T14s, five models):** Phi-3-mini Q6_K 84.8% (draft champion) · Gemma-3-4B Q6_K 73.3% · Llama3.2-3B Q8_0 72.6% · phi4-mini:3.8b (`microsoft/Phi-4-mini-instruct`, TO MEASURE) · qwen3.5:4b non-thinking mode (`Qwen/Qwen3.5-4B`, TO MEASURE). qwen2.5:3b 76.1% retired by rule 7 (kept as superseded data point).

**Thinking (two-model head-to-head):** `Qwen/Qwen3.5-4B` (thinking mode) vs `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF`. Excluded on the walk-down: deepseek-r1 (no class member: 1.5b sub-class, 7b over-class — both author rulings), gemma4 (e2b 2.3B effective sub-class; e4b fails gate), lfm2.5 (sub-class), phi4-mini-reasoning (no Ollama thinking tag — category is tag-defined), qwen3 (rule 7), gpt-oss/glm/magistral/nemotron-super (too big). Ecosystem finding for the report: 2026 thinking models cluster at 1–2b and 20b+; the 3–4b band is nearly empty and contains only hybrids.

## Measurement state & predictions standing

**Qwen3.5-4B thinking mode (DONE, allowance 1024):** selected **Q5_K_M**, worst 21.1 t/s (mean 21.2, σ 0.02) — and the later bug-reveal showed Q8_0 15.3 FAIL / Q6_K 18.8 FAIL, so Q5_K_M is the ONLY passing rung. **82% of turns answer_empty** (18/22; natural thinking 790–1440 tokens vs 1024 allowance) → author ruled **THINK_ALLOWANCE = 2048** (unrestricted-thinking preserved; no --reasoning-budget). Rung prediction Q4_K_M graded MISS (one rung low); <10% overrun graded BIG MISS (82%) — both logged as findings.
**Rerun needed:** Qwen3.5 thinking selection at allowance 2048 (fresh `.live-dump.think.json` dumps). Prediction: worst unchanged ~21.0–21.3, answer_empty <15% (possibly 0%).

**Pending measurements:** (1) qwen3.5:4b `--no-thinking` run — was blocked twice (stale script, then the mode-dump-reuse bug, both fixed); doubles as the **mode-blindness check** (predicted same rung Q5_K_M, worst 21.0–21.3, dump `reasoning_chars: 0`) — a different rung means wiring bug. (2) phi4-mini addendum run (predicted rung Q4_K_M coin-flip vs Q6_K; ARC **78–86% straddling the champion's 84.8** — dethroning genuinely open). (3) nemotron-3-nano selection (predicted Q4_0 — its first-party Q4_K_M ships 2.8 GB, over the gate). (4) both ARCs (n=1172, raw protocol, mode-blind by design). (5) final McNemar both categories — restrict non-thinking ranking to the five roster rungs (`--arc-only --arc-models`) since qwen2.5 lingers in state as superseded. ARC predictions: qwen3.5 non-thinking 58–70 (below retired qwen2.5's 76.1 — the rule-7 cost hypothesis), thinking-category near-tie across modes, neither beats Phi-3-mini 84.8.

## Tooling state (all pushed & byte-verified)

- **live-bench.py** = 18,656 B, sha256 `9429933806a7f42c341399182e04bc3c1f298a43447ee349612ba7d2f72dcaf1` (commit e77f09c5): `--thinking` (reasoning-format deepseek, THINK_ALLOWANCE 2048), `--no-thinking` (per-request `chat_template_kwargs {"enable_thinking": false}` + server `--chat-template-kwargs`; mutually exclusive flags).
- **full-benchmark.py** = 36,524 B, sha256 `8ea152c033f8c8a0f35a65a04b0b8978ea457a07aa9d5b3ed8dd3b9fde1a102f` (commit 80821702): `--no-thinking` threads to live-bench; **mode-suffixed dump names** (`.live-dump.think.json` / `.live-dump.nothink.json` / default unchanged) — fixes the Session-25 bug where a `--no-thinking` run reused thinking-mode dumps (resume check was timestamps-only; mode was an invisible cache input).
- **README.md.b64** = 16,748 B, sha256 `c75f2e66…` (commit 2f479eba): rules 1–8, thinking section, four-generation roster history, hybrid mode rule, run commands.
- **.gitignore** (d0ebc2e8): machine-local state/results/ARC cache ignored.
- **Deleted:** benchmark-state.json from repo; patch-no-thinking.py one-off (superseded by direct pipeline).

## Tooling pipeline (the big change this session)

The GitHub-API fetch bottleneck is **gone**: the upgraded execution environment gives direct network (curl, no 32,793-char truncation) + the sandbox reads the same filesystem. New loop: curl full fetch → sha-gated python patch + py_compile → sandbox reads artifact → connector push → **pinned-commit re-fetch + diff (byte-exact)**. Proven end-to-end twice this session. git CLI is still unavailable (no package installs, no push credentials), so pushes remain via the connector. Author's ritual is deliberately kept as human verification: decode .b64, check byte count + sha256, commit text files.

## Author's decode ritual (current)

```
git pull
base64 -d live-bench.py.b64 > live-bench.py         # 18,656 B, sha256 94299338…
base64 -d full-benchmark.py.b64 > full-benchmark.py # 36,524 B, sha256 8ea152c0…
base64 -d README.md.b64 > README.md                # 16,748 B, sha256 c75f2e66…
python3 -m py_compile live-bench.py full-benchmark.py
git add …; git commit; git push
```

## Immediately next

1. Author decodes the three files (ritual above), commits.
2. Rerun `python3 full-benchmark.py --no-thinking "Qwen/Qwen3.5-4B"` → grade mode-blindness check + kwarg verification.
3. Rerun Qwen3.5 thinking selection at allowance 2048.
4. phi4-mini addendum run → champion-dethroning question.
5. nemotron selection; both ARCs; final McNemar both categories (with the --arc-models roster restriction).
6. Then: back to the **report draft** (study #2 is a draft; the roster history + all prediction grades are report material — the draft needs the five-model roster, the hybrid/mode rules, and the two-category design).

## Open items / flags

- **51.2-class roster audit (OPEN, author decision pending):** rule 7 + 8 re-admit hybrids there, but qwen3.5:2b ships 2.7 GB (over that tier's ≤1.3 GiB gate) and 0.8b is far under → the Qwen family may have NO in-class member at 51.2 (strict reading vacates qwen2.5:1.5b's slot). Unresolved; T14s work unaffected.
- llama.cpp `--chat-template-kwargs` server-flag form has a known bug (issue #20409, ignored on some builds) — per-request kwarg is primary; first-turn dump check is mandatory per mode run.
- Old allowance-1024 thinking dumps are orphans under the new naming — kept as data, never reused.
- Windows fresh-clone README test: still on the to-do list, lower priority now that the study runs on the T14s.