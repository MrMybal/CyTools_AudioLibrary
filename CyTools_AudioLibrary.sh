#!/bin/sh
# Linux launcher (not executed by the author). Run app/install_linux.sh once first.
cd "$(dirname "$0")" || exit 1
if [ ! -x runtime/python/bin/python ]; then echo "Private runtime missing: run app/install_linux.sh"; exit 2; fi
exec runtime/python/bin/python runtime/bootstrap.py "$@"
