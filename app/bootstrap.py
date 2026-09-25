"""Start-up of CyTools_AudioLibrary. This file is the source: the installers copy it to runtime/bootstrap.py,
outside app/, because it is what replaces app/ when an update is activated.

1. activate a staged application (runtime/updates -> app/, previous one kept in runtime/backups);
2. open the Dear ImGui interface. Any failure is written to data/logs/bootstrap.log and shown in a dialog.
"""
import os
import runpy
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)


def report(text):
    log = ROOT/'data'/'logs'/'bootstrap.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a', encoding='utf-8') as handle: handle.write(text+'\n')
    if os.name == 'nt' and '--smoke-test' not in sys.argv:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text[-1500:], 'CyTools AudioLibrary', 0x10)


def main():
    sys.path.insert(0, str(ROOT/'app'))
    try:
        import maintenance
        version = maintenance.apply_pending()
        if version:
            for name in [n for n in sys.modules if n in ('maintenance', 'config')]: del sys.modules[name]
    except Exception:
        report('Update activation failed; the current application is unchanged.\n'+traceback.format_exc())
    try: runpy.run_path(str(ROOT/'app'/'gui'/'main.py'), run_name='__main__')
    except SystemExit: raise
    except Exception:
        report('The interface stopped with an error.\n'+traceback.format_exc()); raise SystemExit(1)


if __name__ == '__main__':
    main()
