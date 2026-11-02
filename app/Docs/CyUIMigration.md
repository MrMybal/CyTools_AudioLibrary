# Modular CyUI integration

The standalone application uses [CyUI](https://github.com/MrMybal/CyUI) 1.2.0,
pinned to [`ff023e6`](https://github.com/MrMybal/CyUI/tree/ff023e646c6a3038b3dfbfd53f6d2b4a2f5955e3).

## Selected modules and replacements

Core; AudioViews; Plots; Canvas; Diagnostics.

- The selected-sound waveform uses AudioViews for waveform drawing, playhead, navigation and selection.
- The host still chooses/cache-reads peak pyramid levels and raw sample detail. A click seeks after release; a drag selects without seeking.
- Structured logs use Diagnostics, with the original character-selectable text and full-file copy retained.
- Core replaces the private palette, styles, fonts and common widget implementations. `ui_style.py` handles host translation, action naming, filter chips and wrapping banners.

## Reproducible source and delivery

`app/cyui-source.json` records every selected upstream file and its SHA-256.
`app/cyui.py` and `app/cyui_modules/*.py` are unchanged official sources, normalized
to LF. Do not edit them: host adapters live outside the library. Refresh only from
the exact pinned checkout:

```sh
python app/scripts/sync_cyui.py /path/to/CyUI
```

The sources are included with the application using its existing source-vendoring
mechanism. Neither a developer checkout elsewhere on disk nor an editable pip
installation is needed. There is one imgui-bundle renderer, at the version pinned
in `app/requirements.txt`; no C++ umbrella, CMake demo/gallery, CEF, extra model,
AI engine, NumPy installation or browser dependency is introduced by this migration.
Existing application/DSP/rendering dependencies are kept where required.

Keep `LICENCES/CyUI-MIT.txt` with the product. The application's own license does
not change. The Options licenses list identifies the upstream revision and source.

## Host responsibilities and retained adaptations

The searchable/sortable audio table, ranked search matches, tag edits, file operations and OS drag/drop remain host-owned. CyUI Assets does not represent ranked multi-model matches, editable analysis columns and the existing file-transfer contract. These are not replaced by a less capable generic browser. Peak decoding, sample storage, player state and file bounds remain in the host. No Audio, Nodes or browser runtime is added.

SDK operations, permissions, exclusive groups, temporary AI task files, model
installation, licenses/acceptance, generation recipes and Undo remain host-owned.
No CyToolsCore runtime or AI library is copied into CyUI. English remains the
default and French the persistent selectable second language.

## Verification

63 unit/integration tests; native library and options views. The waveform integration tests exercise real mouse click/release and drag/release.

Run the adapter tests from `app/` with the private Python:

```sh
python -m unittest discover -s tests -p test_modular_ui.py -v
```

They verify pinned-source integrity, bounded log refresh/redaction and native ImGui
frames across five themes, both densities, EN/FR and scale 1.0/1.5/2.0, plus the
application-specific data/edit routing. This simulated DPI check is not a physical
multi-monitor test. Windows native views are tested locally. Linux/macOS remain
unverified by this migration; the source integration stays platform-independent.

Windows packages include the migrated sources and their license notices.

Final local results: 63 unittest tests passed; the native Library/Options views rendered, including the waveform and time ruler in a light theme and in French/navy/comfortable. Real ImGui mouse tests verify click-to-seek versus drag-to-select.


CyUI license: [https://github.com/MrMybal/CyUI/blob/main/LICENSE](https://github.com/MrMybal/CyUI/blob/main/LICENSE). The complete MIT text ships with the application, including when the upstream repository is private.
