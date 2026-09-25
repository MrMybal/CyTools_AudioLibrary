# Validation report — CyTools_AudioLibrary 0.1.0 (2026-09-21)

Everything below was executed on one machine: Windows 10 x64 (build 10.0.19044), Ryzen 9 7900X,
127 GB RAM, NVIDIA GeForce RTX 3090 24 GB (driver 610.47), CPython 3.12.0, PyTorch 2.8.0+cu126,
transformers 4.57.6, imgui-bundle 1.92.900, CyToolsCore 0.9.0. The evidence files named below are written to
`data/reports/` on the validation machine and are not part of the repository: they list the files of a personal
sound library.
Three kinds of statement are kept apart: **real run**, **fixtures**, **not verified**.

## 1. Real runs (real weights, real audio, CUDA)

Real library used: 107 WAV files referenced read-only from three existing folders (5 captioned Clotho clips
shipped with the pinned Omni-Embed-Audio source, 77 files of `C:\Windows\Media`, 25 sounds generated earlier by
CyTools_AudioGen). It is small and WAV-only: it proves the pipeline and gives an indication of relevance, not a benchmark.

| What | Result | Evidence |
|---|---|---|
| Model installation through the Tool (`install_model`): M2D-CLAP 2025 (1.47 GB zip, SHA-256 from the GitHub release digest, resumed from a partial file), LAION-CLAP (0.6 GB), Qwen3-1.7B (4.1 GB), Omni-Embed-Audio Qwen3B-Cl + Qwen2.5-Omni-3B thinker shards (19.5 GB) | 4/4 `Installed`, receipts with per-file SHA-256 and model hash | `install-*.json` |
| Scan + metadata + loudness + waveform pyramid | 107 files, 0 failure; rescan: 107 unchanged in 0.03 s; 2 exact duplicate groups found | `real-m2d-clap.json` |
| M2D-CLAP 2025 embeddings (whole clip + 10 s windows, 2 s overlap) | 107 files in 9.8 s including model load | `real-m2d-clap.json` |
| Omni-Embed-Audio Qwen3B-Cl embeddings | 107 files in 32 s including ~20 s load of the 9.5 GB checkpoint | `real-three-models.json` |
| Caption → file retrieval on the 5 captioned clips (rank of the expected file) | M2D alone 3/5 top-1, 5/5 top-2 · M2D + LAION 4/5 top-1 · M2D + LAION + Omni 4/5 top-1 (ranks 2,1,1,1,1) | same files |
| Warm text search, three models, 107 files | 0.08–0.12 s per query | `real-three-models.json` |
| Qwen3-1.7B query understanding (French requests → English structured query) | 1.2–1.8 s warm; 7.8–16.6 s on the first call (model load). "gros impact métallique très lourd avec une longue réverbération" → `heavy metal impact with long reverb` | `real-m2d-laion-qwen3.json`, `library-search-fr.png` |
| Interface scenario: French query with a negation → LLM → three models → RRF | `water_stream.wav` first at 70 % (67 / 73 / 70), every other file ≤ 22 % | `library-search-fr.png`, `.json` |
| Measured VRAM (resident): M2D 0.75 GiB, LAION-CLAP 0.6 GiB, Omni-Embed 3B 8.9 GiB; 10.3 GiB peak with the three loaded | catalogue estimates lowered to 2 / 1.5 / 11 GiB | `real-three-models.json` |
| Measured cosines, unrelated vs matching: M2D 0.16 vs 0.30, LAION 0.03 vs 0.38–0.48, Omni 0.05 vs 0.62–0.83 | display ranges set from these values | catalogue `similarityRange` |
| Launcher: `CyTools_AudioLibrary.exe` started from `C:\` | interface opened with the private `pythonw`, 107 rows, waveform, decoded audio, details job | `library-en.json/.png` |
| ImGui tabs rendered: Library EN and FR, Options EN and FR, Application log, Advanced operations | screenshots saved, exit code 0 | `*.png` |
| CLI | `describe`, `invoke install_model`, `invoke` of every operation used above | — |
| Real MCP: official `mcp` stdio client → server → jobs | 8 expected tools present, real two-model search (9.4 s cold), `InvalidParameters` and `LicenseAcceptanceRequired` returned as job errors | `mcp-validation.json` |
| Engine update check against the real upstream repositories | both sources at their pinned revision | console output, §UPDATES |
| Fine tuned query assistant `cytools-search-assist@v1` (Qwen2.5-1.5B + LoRA, trained on Colab A100 in 3.9 min, merged locally) | 250/250 validation answers are valid JSON with the expected shape; agreement with the reference answers 92.0 % on categories, 83.2 % on tags | `search-assist-finetune.json`, `finetune-train_report.json` |
| Retrieval with that model, 150 messy multilingual queries replayed through the real engine on 5 764 files | top-5 hit 58.0 % raw query → 89.3 % with its caption → 95.3 % with caption and variations | `search-assist-finetune.json` |
| Category hint re-ordering, 250 queries, `hintBoost` swept 0 / 0.06 / 0.12 / 0.25 | first place 72.8 → 84.4 → 87.2 → 89.2 %; default kept at 0.12. Measures agreement with the Library's own automatic categories, not perceptual relevance | `search-assist-finetune.json` |
| Both prompt profiles end to end through the CLI | `caption`: 4 captions, 2 categories resolved, 46 candidates re-ordered, 8.5 s cold. `generic` with Qwen3-1.7B: unchanged behaviour, no hints | `search-assist-finetune.json` |
| Interface, real run: `--ui-test-library` with "il me faudrait des pas ds la neige bien proche, pas de musique", fine tune selected, 5 764 files | status line reads `LLM cytools-search-assist@v1 (8.52 s) | category hints: 16 results reordered`; results dominated by snow and footsteps files; waveform, decoded audio and details loaded | `search-assist-finetune.png`, `-ui.json` |
| Fine tune made the default model, for the interface, the CLI and MCP at once | `search_sounds` with neither `llmAssist` nor `llmModel` resolved to `cytools-search-assist@v1`, profile `caption`, 7.99 s; the interface opened on *Auto* with it selected, 313 candidates re-ordered | `search-assist-default.png`, `-ui.json` |
| Folders, selection and batch edits in the interface, 5 764 files | folder tree with recursive counts, 4 sounds selected, `Selection (4)` tab with the batch editor; single-sound view with category picker, description and notes | `selection-batch.png`, `selection-single.png` |
| Folders over real MCP | `op_list_folders`: 4 roots, 42 top-level folders; the largest holds 645 files and `op_browse_assets` with the same `rootIds` + `folderPrefix` returns 645; `op_update_assets` with an empty filter refused (`InvalidParameters`) | `mcp-validation.json` |
| Scale, synthetic: 20 000 WAV files | scan + metadata + waveforms 62 s; rescan 1.1 s; 40 000 embeddings through the worker protocol 120 s (test adapter, CPU); list 20 000 ids 16 ms; filtered list 16 ms; search over 2 × 20 000 vectors 0.09–0.11 s; cache 46 MB; audio folder untouched | `scale-test.json` |

## 2. Fixture tests (`app/tests`, 46 tests, all passing; no PyTorch, no weights)

Real CyToolsCore runtime, real worker process and protocol, synthetic audio, deterministic test adapter.
WAV 16/24-bit/float, FLAC, OGG, AIFF, MP3 and M4A/AAC decoding and metadata; known peak/RMS of a sine; waveform
pyramid and zoomed read; audio folders byte-identical after scan; external cache; incremental rescan (moved keeps
its AudioId, modified re-analysed, missing flagged, new added); two models with different dimensions in separate
stores; nothing recomputed on a second run; RRF weights; segment hit inside a long file; filters; similar and
selection search; LLM assist and parser fallback; user tags/rating survive re-analysis and re-labelling; a
second version of a model coexists and only it is computed; custom model files never deleted; pause → `Busy` for
a second maintenance job → resume; **cancellation during a model request: worker process confirmed dead before the
job reports `Cancelled`**, next run resumes; error codes; client B cannot read or cancel client A's job; cache
move (previous copy kept, cache inside an audio folder refused); exact and probable duplicates; configuration
save/load round-trip, no job started by loading, replay through the runtime; French catalogue complete for every
interface string; both answer schemas of the query assistant, including a garbled answer and a suggestion
that no Library has; the default model resolution, including a configured model that was uninstalled;
folder tree counts equal to what the same folder filter returns, one folder edited through filters (tags, categories added and removed, a note appended after the existing one) while the rest of the Library stays untouched, an empty filter refused instead of editing everything; multi-selection (click, Ctrl, Shift, Ctrl+Shift, Ctrl+A, Escape, list order, a new list dropping sounds it no longer shows);
update staging, 7 hostile/wrong archives and a symlink entry rejected, activation, rollback,
`data/` preserved, no repository invented.

## 3. Not verified — do not assume

* **Linux and macOS: never executed.** `CyTools_AudioLibrary.sh` and `install_linux.sh` are untested text.
* **Audible playback and mouse gestures** (zoom, pan, drag selection, loop, Space/Up/Down): the code ran (decode,
  stream setup path, rendering), but no automated test can hear or drag. A person must try them.
* **Real MP3/FLAC/OGG/M4A libraries**: formats are covered by fixtures only; the real library was WAV.
* **Large real libraries**: the 20 000-file figure is synthetic, 0.25 s files, test adapter. Real GPU throughput on
  tens of thousands of real files was not measured (extrapolating M2D: roughly 10–15 files/s on this GPU).
* **Segment-level retrieval on real long recordings**, and the temporal-order bonus: fixtures only.
* **Real models on CPU**: not run. CPU path exercised with the test adapter only.
* **Gated-model flow (401/403, stored token)**: no gated model was available; the token store command and the
  error mapping are implemented, not exercised against a provider.
* **Application update from a real GitHub release**: the repository `MrMybal/CyTools_AudioLibrary` is declared, but
  it holds no release and, on 2026-09-26, it answered 404 to an anonymous request, so it is private or empty. The real
  check was run and reports exactly that. Download, staging and activation are proved with fixtures only. Staging/activating a
  *newer* engine-source revision: not exercised (upstream had none).
* **M2D-CLAP 2024, Omni-Embed-Audio Qwen3B-AC, Qwen3-0.6B/4B**: catalogue entries on validated adapters, never installed.
* **The GGUF build of the fine tuned assistant**: the quantised file was not part of the Colab download, and
  the Tool has no llama.cpp adapter, so nothing was loaded from it. The model used here is the adapter merged
  locally into `Qwen/Qwen2.5-1.5B-Instruct`.
* **A second training run**: every fine tune figure comes from one run, on one seed. Nothing was repeated,
  so the numbers carry no error bar.
* **Audio Flamingo 3 / Deep mode**: not implemented (registry entry and capability slots only).
* **LUFS** values were not compared with a reference meter. **Redistributable installer without a system Python**: not provided.

## 3b. Additions of the second request (same day)

* **Real run (MCP):** search without `libraryId` returned `water_stream.wav` (71 %) with its absolute path and Library name;
  `check_library` on the real Library: 107 unchanged, nothing written; `suggest_names` (read-only) on real generically named
  files, e.g. `sound_01.wav` → `Explosions_Slam_Hit_Reverberant.wav`; `rename_files` without `confirm` refused; 57 MCP tools listed.
* **Fixtures (24 tests now):** background check, cross-Library search, rename + undo, tag writing in six formats with
  bit-identical decoded audio.
* **Deliberately not executed:** `rename_files` and `write_metadata` on any real folder of this machine. They change original
  files and nobody asked for a specific real file to be changed. First real use should be on a few files, with the backup on.
* **Not verified:** the *ask* banner and a complete automatic update cycle seen by a person; tags read back by another
  application (only mutagen read them); very large files (the rewrite needs free space for one copy next to the file).

## 4. Problems found during validation, and what was done

1. Licence acceptance is personal and cannot be delegated. `install_model` refuses a model whose licence requires
   acceptance until `acceptLicense` is set by the person installing it, the interface never pre-ticks that box, and
   the MCP test asserts that an installation without acceptance is refused with `LicenseAcceptanceRequired`.
2. A folder named `aux` (reserved on Windows) broke the first install → renamed `support`.
3. M2D-CLAP 2025 needs `flat_features=True` (upstream Example_4): first analysis failed on every file → adapter fixed,
   and a circuit breaker now stops an analysis when nothing ever succeeds instead of failing the whole Library.
4. The Omni-Embed checkpoint is a Linux training pickle containing `PosixPath` objects: unloadable on Windows →
   loaded with an inert path class inside the worker only; upstream appears untested on Windows.
5. Auto-labelling with an absolute cosine threshold labelled almost everything (14 "Weapons" among Windows sounds)
   → replaced by softmax zero-shot over the label set (3 left, shown with model and probability). Model errors remain.
6. Qwen3-1.7B invented an exclusion ("music") copied from a prompt example → exclusions are kept only when the
   request contains a negation.
7. `pip` replaced the CUDA PyTorch by a newer CPU wheel through a transitive dependency → constraints file + check.
8. One transient TLS failure (`self-signed certificate in certificate chain`) on the first PyPI install; a retry
   succeeded and certificate verification was never disabled. Worth knowing on networks that inspect TLS.
