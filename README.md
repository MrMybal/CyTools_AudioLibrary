# CyTools_AudioLibrary

Maintenance: **Cyberalien**.

A desktop Tool to manage, analyse and search large local sound libraries. It references your
folders without ever moving or copying the files, draws their waveforms, plays them, and lets
you find a sound by describing it in any language: several audio embedding models (M2D-CLAP 2025,
LAION-CLAP, Omni-Embed-Audio) search at once and their rankings are fused, and an optional small
local LLM turns a messy request into clean captions first. Your own tags, categories, ratings and
notes can be set on one sound, a selection or a whole folder. The same library can be searched by
an AI assistant through MCP.

It runs as a Dear ImGui application, as a command line and as an MCP server, all on the same
[CyToolsCore](https://github.com/MrMybal/CyToolsCore) runtime.

The user guide, in French, is [LISEZ-MOI.md](LISEZ-MOI.md). The developer notes are in
[app/README.md](app/README.md), and what was measured, with its limits, in
[app/Docs/AudioLibrary-Validation.md](app/Docs/AudioLibrary-Validation.md).

Only Windows 10 with an NVIDIA card has been executed. The Linux launcher exists and has never
been run.

## What this repository contains, and what it does not

The repository carries the application (`app/`), the user guide and the Linux launcher.

It does **not** carry:

- **model weights** (`data/models/`, about 2 GB for the default search pair, about 26 GB with
  every catalogue model): installed from the Installation tab or with `install_model`, from the
  pinned catalogue in `app/models/catalog.json`. M2D-CLAP and the Omni-Embed-Audio backbone come
  under their own licences, the latter non-commercial, which each user accepts personally in
  that tab.
- **`runtime/`**: the private Python of the application, the PyTorch engine, the pinned engine
  sources, staged updates and backups. It is rebuilt with the steps below.
- **your data** (`data/`): libraries, caches, waveforms, embeddings, jobs, logs, settings and
  reports stay on your machine. Nothing is ever written next to your audio files, except by the
  two File Tools operations, which ask for confirmation.
- **the Windows launcher** `CyTools_AudioLibrary.exe`: compiled from `app/launcher.cpp`.

## From a release

Download `CyTools_AudioLibrary-<version>-windows-x64.zip` from the
[releases](https://github.com/MrMybal/CyTools_AudioLibrary/releases), unzip it where the application
should live (it creates its private environment in that folder), then run once, from that folder:

```powershell
powershell -ExecutionPolicy Bypass -File app\Install.ps1
.\CyTools_AudioLibrary.exe
```

Python 3.11 or newer and `git` are needed for that step; the launcher says so if it was skipped.
`cytools-app.zip` and its `.sha256`, also attached to each release, are what the Updates tab of an
installed copy downloads: they are not meant to be unzipped by hand.

## From a clone

Windows, PowerShell. Python 3.11 or newer and `git` must be on the PATH: the SDK is installed
from its repository at the exact commit pinned in `app/requirements.txt`. These steps were
executed on the development machine from a fresh clone, with Python 3.11: installation, the
tests, and the interface started both through the launcher and through `runtime\bootstrap.py`.
Building the launcher itself was not repeated there.

```powershell
git clone https://github.com/MrMybal/CyTools_AudioLibrary.git
cd CyTools_AudioLibrary
powershell -ExecutionPolicy Bypass -File app\Install.ps1           # private runtime in runtime\python
powershell -ExecutionPolicy Bypass -File app\build_launcher.ps1    # CyTools_AudioLibrary.exe (Visual C++ build tools)
.\CyTools_AudioLibrary.exe
```

Without the Visual C++ build tools, start the same interface with
`.\runtime\python\Scripts\pythonw.exe runtime\bootstrap.py`.

In the application, the **Installation** tab installs the AI engine (a private PyTorch
environment, several GB) and the models, with their size, source and licence. Then create a
Library, add your folders, scan, and search. `app\Install.ps1 -Engine` installs the engine from
the command line instead.

## From an AI assistant (MCP)

```json
{"mcpServers": {"cytools-audiolibrary": {"command": "<tool>/runtime/python/Scripts/python.exe",
  "args": ["<tool>/app/tool.py", "--data-dir", "<tool>/data/jobs-mcp", "mcp"]}}}
```

Replace `<tool>` with the absolute path of the clone. The assistant can search every library,
browse the folder tree, edit tags and notes, and scan or analyse on request. Installing a model
under a personal licence, renaming files and writing tags into files always need your explicit
yes: the operations refuse to run without it. Details in [app/README.md](app/README.md).

## Updates

The Updates tab reads the releases of this repository. A release carries `cytools-app.zip` and
`cytools-app.zip.sha256`, built by `app\scripts\build_release.py`. An update replaces `app/` only,
is verified before it is activated at the next start, keeps the previous version for a rollback,
and never touches `data/`. Packages of the private Python environment, such as the CyToolsCore SDK, are not
part of an application update: run `app\Install.ps1` again to install the versions the new `app/requirements.txt` pins. The engine sources and the model weights are separate update streams.

## Tests

```powershell
.\runtime\python\Scripts\python.exe -m unittest discover -s app\tests -v   # no PyTorch, no weights
.\runtime\python\Scripts\cytools.exe validate app\CyTool.json
```

## Licence

Copyright (C) 2026 Cyberalien. This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License, version 3 only, as published by the
Free Software Foundation. It is distributed WITHOUT ANY WARRANTY; see [LICENSE](LICENSE).

The licence covers the application code. It is built on [CyToolsCore](https://github.com/MrMybal/CyToolsCore)
0.10.1, under the MIT licence. [LICENCES/](LICENCES/) holds the full text of the SDK licence and the sources of
every component; the engines and model weights keep their own terms, listed in the Options tab and in
[app/licenses.json](app/licenses.json).
