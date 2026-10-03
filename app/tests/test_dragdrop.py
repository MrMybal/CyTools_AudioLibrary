"""The data a drag out of the list carries, read back through COM the way Explorer or Unreal reads it.

The drag itself needs a person holding the mouse: what is tested here is everything the receiving program
gets, through the real COM interfaces. Windows only.

    runtime/python/Scripts/python.exe -m unittest discover -s app/tests -v
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'gui'))
import dragdrop

PATHS = [r'C:\Sounds\Doors\metal door é.wav', r'D:\Library\Impacts\hit 01.wav']


class FileList(unittest.TestCase):
    def test_dropfiles_round_trip_keeps_every_character(self):
        block = dragdrop.dropfiles(PATHS)
        self.assertEqual(struct.unpack('<I', block[:4])[0], 20)
        self.assertEqual(dragdrop.files_of(block), PATHS)
        self.assertTrue(block.endswith(b'\0\0\0\0'), 'the list ends with an empty string')


@unittest.skipUnless(dragdrop.AVAILABLE, 'Windows only')
class ThroughCom(unittest.TestCase):
    def setUp(self):
        import pythoncom
        self.pythoncom = pythoncom
        pythoncom.CoInitialize()
        self.data = dragdrop.data_object(PATHS)

    def fe(self, fmt, tymed=None):
        return fmt, None, self.pythoncom.DVASPECT_CONTENT, -1, tymed if tymed is not None else self.pythoncom.TYMED_HGLOBAL

    def test_the_receiver_gets_the_file_list(self):
        import win32con
        medium = self.data.GetData(self.fe(win32con.CF_HDROP))
        self.assertEqual(dragdrop.files_of(medium.data), PATHS)

    def test_copy_is_the_only_effect_offered(self):
        medium = self.data.GetData(self.fe(dragdrop.PREFERRED_EFFECT))
        self.assertEqual(struct.unpack('<I', medium.data[:4])[0], dragdrop.DROPEFFECT_COPY)

    def test_formats_are_listed_and_others_refused(self):
        import win32con
        listed = {item[0] for item in self.data.EnumFormatEtc(self.pythoncom.DATADIR_GET)}
        self.assertEqual(listed, {win32con.CF_HDROP, dragdrop.PREFERRED_EFFECT})
        self.assertIsNone(self.data.QueryGetData(self.fe(win32con.CF_HDROP)))
        with self.assertRaises(self.pythoncom.com_error): self.data.QueryGetData(self.fe(win32con.CF_UNICODETEXT))
        with self.assertRaises(self.pythoncom.com_error): self.data.GetData(self.fe(win32con.CF_HDROP, self.pythoncom.TYMED_ISTREAM))

    def test_a_receiver_asking_for_several_media_gets_memory(self):
        import win32con
        medium = self.data.GetData(self.fe(win32con.CF_HDROP, self.pythoncom.TYMED_HGLOBAL | self.pythoncom.TYMED_ISTREAM))
        self.assertEqual(dragdrop.files_of(medium.data), PATHS)


if __name__ == '__main__':
    unittest.main()
