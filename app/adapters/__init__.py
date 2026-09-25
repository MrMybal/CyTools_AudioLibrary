"""Engine-side adapters. Imported only by worker.py, inside an AI engine environment."""
import importlib
import importlib.util
from pathlib import Path


def load_adapter_class(name):
    if name.startswith('file:'):
        path = Path(name[5:])
        spec = importlib.util.spec_from_file_location('cy_custom_adapter_'+path.stem, path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    else:
        if not name.replace('_', '').isalnum(): raise ValueError('Invalid adapter name')
        module = importlib.import_module('adapters.'+name)
    return module.Adapter
