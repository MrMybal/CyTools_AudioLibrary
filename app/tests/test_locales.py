"""Every literal string shown by the interface must exist in English and in French."""
import ast
import json
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
LABEL_CALLS = {'button', 'small_button', 'checkbox', 'radio_button', 'input_text', 'input_int', 'input_float', 'slider_float', 'combo',
               'collapsing_header', 'begin_tab_item', 'menu_item'}


def interface_strings():
    found = set()
    def constants(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str): yield node.value
        elif isinstance(node, ast.IfExp): yield from constants(node.body); yield from constants(node.orelse)
        elif isinstance(node, (ast.List, ast.Tuple)):
            for element in node.elts: yield from constants(element)
    for path in (APP/'gui').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text('utf-8'))):
            if not isinstance(node, ast.Call): continue
            function = node.func
            name = function.id if isinstance(function, ast.Name) else getattr(function, 'attr', '')
            owner = function.value.id if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name) else ''
            if name == 'tr' or (owner == 'imgui' and name in LABEL_CALLS):
                for value in constants(node.args[0]) if node.args else (): found.add(value.partition('##')[0])
            if owner == 'imgui' and name == 'combo' and len(node.args) > 2: found.update(constants(node.args[2]))
    return sorted(text for text in found if text.strip())


class Locales(unittest.TestCase):
    def test_every_interface_string_is_translated(self):
        catalog = json.loads((APP/'locales'/'ui.json').read_text('utf-8'))
        missing = [text for text in interface_strings() if not catalog.get(text, {}).get('fr')]
        self.assertEqual(missing, [], 'run app/scripts/merge_locales.py after adding these to audiolibrary.fr.json')

    def test_protocol_values_are_not_translated(self):
        catalog = json.loads((APP/'locales'/'ui.json').read_text('utf-8'))
        manifest = json.loads((APP/'CyTool.json').read_text('utf-8'))
        for operation in manifest['operations']: self.assertNotIn(operation['id'], catalog)


if __name__ == '__main__':
    unittest.main()
