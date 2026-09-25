# Updates: three separate streams

| Stream | Source | Mechanism | Where |
|---|---|---|---|
| Application (`app/`) | GitHub releases of `MrMybal/CyTools_AudioLibrary`, declared as `repository` in `app/release.json`; the Updates tab can override it for a fork, and nothing else is ever guessed. The check is anonymous, so the repository must be public | `cytools-app.zip` + `cytools-app.zip.sha256` | staged in `runtime/updates/tool/<sha256>/` |
| Engine sources | `nttcslab/m2d`, `JudeJiwoo/Omni-Embed-Audio`, exact revisions pinned in `app/engine.json` | `git ls-remote`, clone of one revision | staged in `runtime/updates/engine/<name>/<revision>/` |
| Model weights | the catalogue (`app/models/catalog.json`: pinned revision, size, SHA-256) | Installation tab / `install_model` | `data/models/` |

The PyTorch environment is not an update stream: a new pin in `engine.json` is installed into a **new**
folder with `setup_backend.py --environment runtime/engines/<name> --no-activate`, then activated by
`data/settings/backend.json`; the previous environment stays for rollback.

## Expected application release

A release of the Tool's repository carries two assets:

* `cytools-app.zip` — a single top-level folder `app/` (no `data/`, no `runtime/`, no weights, no symlink);
* `cytools-app.zip.sha256` — the SHA-256 of the archive (first token of the file).

`app/release.json` of the archive must name `toolId: cy.tool.audiolibrary` and the same `runtime_abi` as the
installed application; a release that needs new dependencies changes `runtime_abi` and is refused with a
message asking for a full installation.

Checks before anything becomes *pending*: URL under the configured repository, SHA-256, archive size limit,
no absolute path / drive letter / `..` / backslash / symlink entry, manifest identity, ABI, required files,
no `data` folder. Activation happens only at the next start (`runtime/bootstrap.py` → `apply_pending`), never
while a model worker is alive; the previous `app/` is kept in `runtime/backups/app/` and *Roll back
application* re-stages it. `data/` is never part of a replacement.

## Limits, stated plainly

* No GitHub repository exists for this Tool: check/download against a real release was **not** executed.
  Staging, the hostile-archive rejections, activation, rollback and data preservation are tested with
  fixture archives (`tests/test_maintenance.py`).
* The engine-source check was executed against the real upstream repositories (both at their pinned
  revision on the validation day, so stage/activate/rollback of a *newer* revision was not exercised for
  real; the code path is covered by the same rename-and-backup logic as the application).
* A checksum published next to a release is not an independent signature of its author.
* An engine-source update does not change the analysis key (it is keyed on the model, not on the inference
  code). After activating new engine sources, validate with a real search and roll back if an adapter fails.
