"""Merge app/locales/audiolibrary.fr.json into the facade catalogue app/locales/ui.json (idempotent).

    runtime/python/Scripts/python.exe app/scripts/merge_locales.py
"""
import json
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[1]/'locales'


def main():
    catalog = json.loads((LOCALES/'ui.json').read_text('utf-8'))
    french = json.loads((LOCALES/'audiolibrary.fr.json').read_text('utf-8'))
    # Protocol state codes stay untouched in jobs and JSON; only their display gets a readable English label.
    readable = {'NotInstalled': 'Not installed', 'LicenseAcceptanceRequired': 'Licence acceptance required', 'AccessRequired': 'Access required',
                'NotIntegrated': 'Declared, no adapter', 'Missing': 'Files missing'}
    for english, translation in french.items(): catalog[english] = {'en': readable.get(english, english), 'fr': translation}
    (LOCALES/'ui.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=0), 'utf-8')
    print(len(french), 'entries merged;', len(catalog), 'in the catalogue')


if __name__ == '__main__':
    main()
