"""Every literal string shown by the interface must exist in English and in French."""
import ast
import json
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
LABEL_CALLS = {'button', 'small_button', 'checkbox', 'radio_button', 'input_text', 'input_int', 'input_float', 'slider_float', 'combo',
               'collapsing_header', 'begin_tab_item', 'menu_item'}
# CyUI widgets (app/cyui.py) translate these arguments themselves: positions of the literal texts they show.
CY_TEXTS = {'button': (0,), 'primary_button': (0,), 'danger_button': (0,), 'ghost_button': (0,), 'icon_text_button': (1,), 'icon_button': (1,),
            'toggle_switch': (0,), 'segmented': (1,), 'heading': (0,), 'section_title': (0,), 'overline': (0,), 'badge': (0,),
            'property': (0, 1), 'begin_section': (0,), 'begin_card': (1,), 'empty_state': (0, 1), 'help_marker': (0,), 'panel_header': (0,),
            'search_field': (2,)}


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
            if owner == 'cy' and name in CY_TEXTS:
                for position in CY_TEXTS[name]:
                    if position < len(node.args): found.update(value.partition('##')[0] for value in constants(node.args[position]))
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
