#!/bin/sh
# NOT EXECUTED by the author: written for Linux, never run. Creates the private runtime; the AI engine
# and the models are installed from the Installation tab (or: runtime/python/bin/python app/setup_backend.py).
set -eu
cd "$(dirname "$0")/.."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || { echo "Python 3.11+ is required"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git is required to install CyToolsCore from https://github.com/MrMybal/CyToolsCore"; exit 1; }
[ -x runtime/python/bin/python ] || python3 -m venv runtime/python
runtime/python/bin/python -m pip --disable-pip-version-check install -r app/requirements.txt
echo "Done. Start ./CyTools_AudioLibrary.sh (PortAudio and a desktop OpenGL session are required)."
