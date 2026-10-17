"""The CyUI look of the interface: saved preferences, palettes and colour helpers (no window needed)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import cyui
import ui_common


class Interface(unittest.TestCase):
    def test_preferences_of_the_stock_themes_map_to_cyui_themes(self):
        folder = Path(tempfile.mkdtemp(prefix='cy-audiolib-ui-'))
        for old, new in (('dark', 'mid-grey'), ('light', 'light-grey'), ('classic', 'navy'), ('violet', 'violet'), ('unknown', 'mid-grey')):
            path = folder/f'{old}.json'
            path.write_text(json.dumps({'language': 'fr', 'theme': old, 'font_scale': 1.2}), 'utf-8')
            values = ui_common.Preferences(path).values
            self.assertEqual(values['theme'], new)
            self.assertEqual((values['language'], values['font_scale'], values['density']), ('fr', 1.2, 'compact'), 'other preferences are kept')
        self.assertEqual(set(ui_common.THEMES), set(cyui.THEMES))

    def test_every_palette_has_every_role(self):
        for key, (name, light, palette) in cyui.THEMES.items():
            for role in cyui.ROLES: self.assertIsInstance(getattr(palette, role), int, (key, role))
            self.assertEqual(light, key == 'light-grey')
            self.assertGreater(abs(cyui.contrast_text(palette.bg1)-palette.text), 0, 'text is not drawn in the colour of its ground')

    def test_colour_helpers_keep_imgui_packing(self):
        self.assertEqual(cyui.rgb(0x112233), 0xff332211)
        self.assertEqual(cyui.rgb(0x112233, 0.0), 0x00332211)
        self.assertEqual(cyui.alpha(cyui.rgb(0xffffff), 0.5) >> 24, 128)
        self.assertEqual(cyui.mix(cyui.rgb(0x000000), cyui.rgb(0xffffff), 0.5) & 0xff, 128)
        self.assertEqual(cyui.brighter(cyui.rgb(0x000000), 1.0), cyui.rgb(0xffffff))


if __name__ == '__main__':
    unittest.main()
