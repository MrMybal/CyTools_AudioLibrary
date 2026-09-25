"""The multi-selection of the list: what a batch edit reaches is exactly what the user selected and can see.

Pure logic of the list state, no window: the clicks of the interface call these methods.

    runtime/python/Scripts/python.exe -m unittest discover -s app/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'gui'))
from state import Browser


class Selection(unittest.TestCase):
    def setUp(self):
        self.browser = Browser()
        self.browser.ids = [f'id{i}' for i in range(10)]
        self.browser.selected = 0
        self.browser.current = lambda: {'audio_id': self.browser.ids[self.browser.selected]}

    def test_a_plain_click_selects_one_sound(self):
        self.browser.mark_only(3)
        self.assertEqual(self.browser.targets(), ['id3'])

    def test_ctrl_click_adds_and_removes(self):
        self.browser.mark_only(1); self.browser.toggle_mark(4); self.browser.toggle_mark(6)
        self.assertEqual(self.browser.targets(), ['id1', 'id4', 'id6'])
        self.browser.toggle_mark(4)
        self.assertEqual(self.browser.targets(), ['id1', 'id6'])

    def test_shift_click_takes_the_range_from_the_last_click(self):
        self.browser.mark_only(2); self.browser.mark_range(5)
        self.assertEqual(self.browser.targets(), ['id2', 'id3', 'id4', 'id5'])
        self.browser.mark_range(0)                      # the anchor stays on the last plain click, as in a file explorer
        self.assertEqual(self.browser.targets(), ['id0', 'id1', 'id2'])

    def test_ctrl_shift_click_extends_instead_of_replacing(self):
        self.browser.mark_only(0); self.browser.toggle_mark(8); self.browser.mark_range(9, extend=True)
        self.assertEqual(self.browser.targets(), ['id0', 'id8', 'id9'])

    def test_targets_follow_the_list_order_not_the_click_order(self):
        self.browser.mark_only(7); self.browser.toggle_mark(2); self.browser.toggle_mark(5)
        self.assertEqual(self.browser.targets(), ['id2', 'id5', 'id7'])

    def test_ctrl_a_and_escape(self):
        self.browser.mark_all(); self.assertEqual(len(self.browser.targets()), 10)
        self.browser.clear_marks(); self.assertEqual(self.browser.targets(), ['id0'], 'nothing marked: the current sound')

    def test_a_new_list_drops_what_it_no_longer_shows(self):
        self.browser.mark_all()
        self.browser.ids = ['id3', 'id4', 'new']        # e.g. a folder was opened, or a search replaced the list
        self.browser.keep_visible_marks()
        self.assertEqual(self.browser.targets(), ['id3', 'id4'], 'an edit must never reach a sound that is not shown')


if __name__ == '__main__':
    unittest.main()
