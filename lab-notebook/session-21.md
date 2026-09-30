## Session 21 — 2026-09-23 (multiplatform port: Windows run prep + pre-registered predictions)

**Done:**
- `live-bench.py` Windows patch pushed (b64, verified at commit): `llama-server.exe` auto-detection (`os.name == "nt"`) and `taskkill /PID /T /F` tree-kill escalation in `stop_server` (the lingering-port bug class from strict-arc, now handled on both OSes).
- `full-benchmark.py` Windows patches in progress (same find_server/.exe + arc_stop_server/taskkill + platform-neutral GUIDE text).
- **README rewritten** as a full cross-platform reproduction guide (Windows PowerShell + Linux, steps 1–7, per-phase troubleshooting, resume semantics, provenance, protocol notes). Pushed as `README.md.b64` (8,389 bytes decoded); author decodes + commits so GitHub shows clean text.
- Verified against the release manifest (never guess asset names): `llama-b10964-bin-win-vulkan-x64.zip` and `llama-b10964-bin-win-cpu-x64.zip` exist in the pinned b10964 release; converter stays at b29c606e2.
- Transport lesson (tooling): the GitHub connector inserts newlines at ~2,000-char intervals in BOTH directions (push and fetch), and open_url truncates fetches at 32,793 chars. Workaround that held: fetch the committed `.b64` sibling, strip whitespace, decode locally → byte-exact source. This recovered live-bench.py (14,688 → patched 15,196 bytes) without any copy-paste.

**Author ruling (floor): keep `--floor 20` for the Windows run.** Predictions re-derived for floor 20 (using study #1's live formula ≈ 26 ÷ size GiB × per-family worst/mean factors):
1. **The 51.2 tier pushes 3–4B families to the bottom of the ladder or off it entirely.** Qwen and Llama can scrape past 20 **only at Q2_K** (predicted worst ≈ 20.6 and ≈ 20.1 — both borderline, single-blank-line margins); Phi fails every rung (best ≈ 14.9 at Q2_K); Gemma fails every rung (best ≈ 14.4). Expected outcome: 2 selections at Q2_K + 2 NO PASSING RUNG.
2. **Floor 20 at this tier lands selections at the study-#3 damage cliff** (~2.5–3 bpw, "never quantize below Q3_K_M") — a direct stress test of that rule. Predicted ARC if the Q2_K rungs pass: Qwen ≈ 70–74% (damage cliff, worse than its Q4_K_M 75.9 at the 102.4 tier), Llama ≈ 68–72%.
3. **ARC scores reproduce within ±1 pp of the same-config Linux values** wherever the same rung is selected (portability proven at 12/12 configs in run51).
4. **Ranking order (Phi > Qwen > Gemma ≈ Llama) cannot be fully re-tested** if Phi/Gemma select nothing — the cross-tier comparison will be partial by construction. The tier itself becomes the headline: half the 102.4-tier roster cannot make the comfort line at 51.2 GB/s.
5. Windows-specific risk: llama-server.exe lingering on port 8081/8077 between runs — patched, but watch for the "port still busy" warning on the first run.

**Author's remaining ritual: T14s pull + decode all three .b64 files (full-benchmark.py 34,305 B / live-bench.py 15,196 B / README.md 8,389 B), py_compile, sha256 check, commit decoded text files, then fresh clone + README-following on the Windows box.** ✅ DONE — all three decoded files committed byte-exact (author's wc + sha256 verified), README shows clean on GitHub.

