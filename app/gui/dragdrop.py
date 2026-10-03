"""Dragging sounds out of the list into another program: Explorer, a DAW, Unreal Engine's Content Browser...

Windows only. The drag carries the list of files (CF_HDROP), exactly what Explorer itself offers, so any program
that accepts files dropped from Explorer accepts these. The only effect offered is COPY: a drop can create
copies, never move or delete the originals of a Library, whatever the target or the keys held.

DoDragDrop is a modal loop: it returns when the button is released, the drop has happened or Escape was
pressed. The window does not redraw meanwhile, which is how every Windows program behaves during such a drag.
"""
import struct
import sys

AVAILABLE = sys.platform == 'win32'

if AVAILABLE:
    import pythoncom
    import win32clipboard
    import win32con
    import winerror
    from win32com.server.exception import COMException
    from win32com.server.util import NewEnum, wrap

    DROPEFFECT_COPY = 1
    PREFERRED_EFFECT = win32clipboard.RegisterClipboardFormat('Preferred DropEffect')
    METHODS = 'GetData GetDataHere QueryGetData GetCanonicalFormatEtc SetData EnumFormatEtc DAdvise DUnadvise EnumDAdvise'.split()


def dropfiles(paths):
    """The DROPFILES block of CF_HDROP: a 20 byte header, then the wide paths, each ending with NUL, then a final NUL."""
    header = struct.pack('<IiiII', 20, 0, 0, 0, 1)       # offset of the list, drop point x/y, not client area, wide chars
    return header+''.join(str(path)+'\0' for path in paths).encode('utf-16-le')+'\0'.encode('utf-16-le')


def files_of(block):
    """Inverse of dropfiles, for tests and diagnostics."""
    offset, _, _, _, wide = struct.unpack('<IiiII', block[:20])
    body = block[offset:]
    if wide: body = body[:len(body)//2*2]       # pywin32 appends one terminating byte to the memory it hands over
    text = body.decode('utf-16-le' if wide else 'mbcs')
    return [item for item in text.split('\0') if item]


if AVAILABLE:
    class FileDataObject:
        """IDataObject holding a file list, with COPY as the preferred and only drop effect."""
        _com_interfaces_ = [pythoncom.IID_IDataObject]
        _public_methods_ = METHODS

        def __init__(self, paths):
            self.data = {win32con.CF_HDROP: dropfiles(paths), PREFERRED_EFFECT: struct.pack('<I', DROPEFFECT_COPY)}
            self.formats = [(fmt, None, pythoncom.DVASPECT_CONTENT, -1, pythoncom.TYMED_HGLOBAL) for fmt in self.data]

        def _query_interface_(self, iid):
            if iid == pythoncom.IID_IEnumFORMATETC: return NewEnum(self.formats, iid=iid)

        def _supported(self, fe):
            fmt, _, aspect, _, tymed = fe
            return fmt in self.data and aspect & pythoncom.DVASPECT_CONTENT and tymed & pythoncom.TYMED_HGLOBAL

        def GetData(self, fe):
            if not self._supported(fe): raise COMException(hresult=winerror.DV_E_FORMATETC)
            medium = pythoncom.STGMEDIUM()
            medium.set(pythoncom.TYMED_HGLOBAL, self.data[fe[0]])
            return medium

        def QueryGetData(self, fe):
            if not self._supported(fe): raise COMException(hresult=winerror.DV_E_FORMATETC)
            return None

        def EnumFormatEtc(self, direction):
            if direction != pythoncom.DATADIR_GET: raise COMException(hresult=winerror.E_NOTIMPL)
            return NewEnum(self.formats, iid=pythoncom.IID_IEnumFORMATETC)

        def GetCanonicalFormatEtc(self, fe): raise COMException(hresult=winerror.DATA_S_SAMEFORMATETC)
        def GetDataHere(self, fe): raise COMException(hresult=winerror.E_NOTIMPL)
        def SetData(self, fe, medium, release): raise COMException(hresult=winerror.E_NOTIMPL)
        def DAdvise(self, fe, flags, sink): raise COMException(hresult=winerror.OLE_E_ADVISENOTSUPPORTED)
        def DUnadvise(self, connection): raise COMException(hresult=winerror.OLE_E_ADVISENOTSUPPORTED)
        def EnumDAdvise(self): raise COMException(hresult=winerror.OLE_E_ADVISENOTSUPPORTED)

    class DropSource:
        _com_interfaces_ = [pythoncom.IID_IDropSource]
        _public_methods_ = ['QueryContinueDrag', 'GiveFeedback']

        def QueryContinueDrag(self, escape, keys):
            if escape: return winerror.DRAGDROP_S_CANCEL
            if not keys & win32con.MK_LBUTTON: return winerror.DRAGDROP_S_DROP
            return winerror.S_OK

        def GiveFeedback(self, effect): return winerror.DRAGDROP_S_USEDEFAULTCURSORS


def data_object(paths):
    return wrap(FileDataObject(paths), pythoncom.IID_IDataObject, useDispatcher=0)


def drag_files(paths):
    """Start a native drag of `paths`. Returns 'copied', 'cancelled' or an error message; never raises."""
    if not AVAILABLE: return 'Dragging files out of the application is only available on Windows.'
    if not paths: return 'cancelled'
    import win32api
    if not win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
        # Released already: OLE's modal loop would wait for a mouse message that may never come.
        return 'cancelled'
    try:
        try: pythoncom.OleInitialize()
        except pythoncom.com_error: pass       # already initialised on this thread
        result = pythoncom.DoDragDrop(data_object(paths), wrap(DropSource(), pythoncom.IID_IDropSource, useDispatcher=0), DROPEFFECT_COPY)
        effect = result[1] if isinstance(result, tuple) else result
        return 'copied' if effect & DROPEFFECT_COPY else 'cancelled'
    except Exception as exc:      # a drag must never take the window down with it
        return f'The drag could not start: {exc}'
