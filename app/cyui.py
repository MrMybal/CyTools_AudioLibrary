"""CyUI for Python: the look of CyDAW 2, Shaderixel and CyEngineHub on imgui-bundle.

A port of the C++ library CyUI (CyImgui_Interface) for this Tool, which draws with imgui-bundle and
cannot link the C++ one: the same five palettes, the two densities, the fonts (Segoe UI, Semibold, Consolas and the
Segoe MDL2 icons) and the controls the interface uses. Every colour comes from palette() by its role, every size
goes through dp(). Stock ImGui calls keep working and follow the theme.

Widgets whose text is an interface literal (buttons, titles, property labels, tooltips of icon buttons...) translate
it through the catalogue, like the ui_common facade; text helpers (text_dim, callout, notify...) show their text as
given, so callers pass tr(...) for literals and never translate user data.
"""
import math
import os
import sys
from pathlib import Path

from imgui_bundle import imgui

DEFAULT_THEME = 'mid-grey'
DENSITIES = ('compact', 'comfortable')


def rgb(value, a=1.0):
    """0xRRGGBB (+ alpha 0..1) packed like ImGui's ImU32 (ABGR)."""
    r, g, b = (value >> 16) & 0xff, (value >> 8) & 0xff, value & 0xff
    return (int(round(max(0.0, min(1.0, a))*255)) << 24) | (b << 16) | (g << 8) | r


ROLES = ('bg0', 'bg1', 'bg2', 'bg3', 'bg4', 'bg5', 'line', 'lineStrong', 'grid', 'gridStrong', 'text', 'textDim', 'textFaint',
         'accent', 'accentHover', 'accentDim', 'accentText', 'selection', 'success', 'warning', 'error', 'info')


class Palette:
    """bg0 deepest (canvases, wells, status bar), bg1 panels, bg2 headers/cards/popups, bg3 fields and buttons at rest,
    bg4 hovered, bg5 pressed. line/lineStrong lines, text/textDim/textFaint the three text levels, ONE accent, and
    success/warning/error/info for meaning."""
    def __init__(self, *colours):
        for role, colour in zip(ROLES, colours): setattr(self, role, colour)


THEMES = {
    # CyDAW 2 default: Bitwig's mid greys, dark seams between panels, orange.
    'mid-grey': ('Mid grey (CyDAW)', False, Palette(
        rgb(0x262626), rgb(0x2e2e2e), rgb(0x373737), rgb(0x414141), rgb(0x4b4b4b), rgb(0x565656),
        rgb(0x1f1f1f), rgb(0x181818), rgb(0x2d2d2d), rgb(0x383838),
        rgb(0xdadada), rgb(0xa6a6a6), rgb(0x707070),
        rgb(0xf28a2e), rgb(0xffa552), rgb(0x7d4a1d), rgb(0x1e1e1e), rgb(0xf28a2e, 0.24),
        rgb(0x5cd26e), rgb(0xf5a623), rgb(0xee5149), rgb(0x5cb4ef))),
    # CyDAW 2: Ableton Live's light greys, dark text, orange, blue selections.
    'light-grey': ('Light grey (CyDAW)', True, Palette(
        rgb(0xb3b3b3), rgb(0xc2c2c2), rgb(0xcbcbcb), rgb(0xd6d6d6), rgb(0xe0e0e0), rgb(0xebebeb),
        rgb(0x9c9c9c), rgb(0x7f7f7f), rgb(0xa9a9a9), rgb(0x969696),
        rgb(0x161616), rgb(0x3d3d3d), rgb(0x6e6e6e),
        rgb(0xff8a00), rgb(0xffa233), rgb(0xf0c27e), rgb(0x161616), rgb(0x3d8eff, 0.26),
        rgb(0x15a34e), rgb(0xd98200), rgb(0xe0302b), rgb(0x2a86d1))),
    # CyDAW 2's first dark one: deep blue-greys, an amber accent.
    'amber-night': ('Amber night (CyDAW)', False, Palette(
        rgb(0x111317), rgb(0x16181d), rgb(0x1c1f25), rgb(0x24282f), rgb(0x2c313a), rgb(0x363c47),
        rgb(0x262a31), rgb(0x363b45), rgb(0x1f2228), rgb(0x2b2f37),
        rgb(0xdce1e8), rgb(0x9aa3b0), rgb(0x5f6875),
        rgb(0xf0a43a), rgb(0xf8b95c), rgb(0x7a5524), rgb(0x111317), rgb(0xf0a43a, 0.22),
        rgb(0x3dd68c), rgb(0xf5a623), rgb(0xe5484d), rgb(0x5ab0f0))),
    # Shaderixel: dark slate, a violet accent, cyan for information.
    'violet': ('Violet (Shaderixel)', False, Palette(
        rgb(0x16171b), rgb(0x1b1c21), rgb(0x222329), rgb(0x282a32), rgb(0x343640), rgb(0x40424e),
        rgb(0x30323a), rgb(0x3a3c46), rgb(0xffffff, 0.04), rgb(0xffffff, 0.09),
        rgb(0xdee0e8), rgb(0x8c909e), rgb(0x686c7a),
        rgb(0x7c5cff), rgb(0x967cff), rgb(0x4c3fa0), rgb(0xffffff), rgb(0x7c5cff, 0.35),
        rgb(0x4cd4a0), rgb(0xf5a623), rgb(0xf0505a), rgb(0x2ec4d6))),
    # CyEngineHub: a very dark navy, flat, a blue accent.
    'navy': ('Navy (CyEngineHub)', False, Palette(
        rgb(0x0a0e13), rgb(0x0d1218), rgb(0x111820), rgb(0x18212c), rgb(0x1f2a37), rgb(0x263343),
        rgb(0x1c2632), rgb(0x283748), rgb(0x111820), rgb(0x1c2632),
        rgb(0xd9e2ec), rgb(0xa4b3c2), rgb(0x65788d),
        rgb(0x2d7ff9), rgb(0x4a93ff), rgb(0x1d4e7a), rgb(0xffffff), rgb(0x2d7ff9, 0.25),
        rgb(0x65cca9), rgb(0xf2b84b), rgb(0xe8747c), rgb(0x70a8fa))),
}

# font size, window padding, frame padding, item spacing, item inner spacing, cell padding, indent, scrollbar, grab min,
# rounding (frames), rounding large (windows, cards), rounding small (grabs, badges), card padding, toolbar height
METRICS = {
    'compact': dict(font=14.0, window=(8, 6), frame=(6, 3), item=(6, 4), inner=(4, 4), cell=(5, 2), indent=14.0, scrollbar=10.0,
                    grab=9.0, rounding=4.0, large=6.0, small=3.0, card=10.0, toolbar=14.0),
    'comfortable': dict(font=16.0, window=(10, 10), frame=(8, 5), item=(8, 6), inner=(6, 4), cell=(6, 4), indent=16.0, scrollbar=11.0,
                        grab=10.0, rounding=6.0, large=8.0, small=4.0, card=14.0, toolbar=16.0),
}

_state = {'theme': DEFAULT_THEME, 'density': 'compact', 'light': False, 'dpi': 1.0, 'palette': THEMES[DEFAULT_THEME][2],
          'icons': False, 'fonts': [], 'toasts': [], 'toast_id': 0}


def palette(): return _state['palette']
def metrics(): return METRICS[_state['density']]
def theme_key(): return _state['theme']
def density(): return _state['density']
def light(): return _state['light']


def dp(x, y=None):
    """A size in pixels at 96 dpi, scaled to the screen."""
    scale = _state['dpi']
    return x*scale if y is None else (x*scale, y*scale)


# -- colour helpers (ImGui's ABGR packing) ---------------------------------------------------------------------------
def alpha(colour, factor):
    current = ((colour >> 24) & 0xff)/255.0
    return (colour & 0x00ffffff) | (int(max(0.0, min(1.0, current*factor))*255+0.5) << 24)


def mix(a, b, t):
    out = 0
    for shift in (0, 8, 16, 24):
        x, y = (a >> shift) & 0xff, (b >> shift) & 0xff
        out |= (int(x+(y-x)*t+0.5) & 0xff) << shift
    return out


def brighter(colour, amount): return mix(colour, (colour & 0xff000000) | 0x00ffffff, amount)
def darker(colour, amount): return mix(colour, colour & 0xff000000, amount)
def vec(colour): return imgui.color_convert_u32_to_float4(colour)


def contrast_text(ground):
    r, g, b = (ground & 0xff)/255.0, ((ground >> 8) & 0xff)/255.0, ((ground >> 16) & 0xff)/255.0
    return rgb(0x141414) if 0.2126*r+0.7152*g+0.0722*b > 0.55 else rgb(0xffffff)


CATEGORICAL = (0xf0a43a, 0x5ab0f0, 0x52d1a2, 0xc792ea, 0xe8765a, 0x7fd1e8, 0xe8c547, 0x9ccc65, 0xf06292, 0x8c9eff, 0x4dd0b5, 0xffb74d)
def categorical(index): return rgb(CATEGORICAL[index % len(CATEGORICAL)])


# -- icons: Segoe MDL2 Assets, Windows only; each has a text fallback ------------------------------------------------
ICONS = {'play': ('\ue768', '>'), 'pause': ('\ue769', '||'), 'stop': ('\ue71a', '[]'), 'add': ('\ue710', '+'), 'remove': ('\ue738', '-'),
         'trash': ('\ue74d', 'Del'), 'settings': ('\ue713', '*'), 'search': ('\ue721', '?'), 'folder': ('\ue8b7', 'Dir'),
         'openFile': ('\ue8e5', 'Open'), 'save': ('\ue74e', 'Save'), 'edit': ('\ue70f', 'Edit'), 'close': ('\ue711', 'x'),
         'check': ('\ue73e', 'ok'), 'chevronDown': ('\ue70d', 'v'), 'chevronRight': ('\ue76c', '>'), 'more': ('\ue712', '...'),
         'refresh': ('\ue72c', 'R'), 'zoomIn': ('\ue8a3', '+'), 'zoomOut': ('\ue71f', '-'), 'filter': ('\ue71c', 'F'),
         'loop': ('\ue8ee', 'L'), 'volume': ('\ue767', 'Vol'), 'library': ('\ue8f1', 'Lib'), 'tag': ('\ue8ec', '#'),
         'star': ('\ue734', '-'), 'starFill': ('\ue735', '*'), 'copy': ('\ue8c8', 'Copy'), 'info': ('\ue946', '(i)'),
         'warning': ('\ue7ba', '!'), 'error': ('\ue783', '!'), 'clock': ('\ue823', 'T'), 'download': ('\ue896', 'v'),
         'upload': ('\ue898', '^'), 'sync': ('\ue895', 'S'), 'audio': ('\ue8d6', '~'), 'list': ('\uea37', '='),
         'exportFile': ('\uede1', '>>'), 'link': ('\ue71b', 'Link'), 'help': ('\ue897', '?'), 'repair': ('\ue90f', 'Fix'),
         'document': ('\ue8a5', 'Doc'), 'view': ('\ue890', 'o'), 'hide': ('\ued1a', '-'), 'lock': ('\ue72e', 'Lock'),
         'globe': ('\ue774', 'Web'), 'statusCircle': ('\uea3b', 'o'), 'rename': ('\ue8ac', 'Ren'), 'cloud': ('\ue753', 'Cloud'),
         'power': ('\ue7e8', 'Off'), 'grid': ('\uf0e2', '#'),
         'undo': ('\ue7a7', 'Undo'), 'back': ('\ue72b', '<')}


def icon(name):
    glyph, fallback = ICONS[name]
    return glyph if _state['icons'] else fallback


def icons_available(): return _state['icons']


# -- fonts -------------------------------------------------------------------------------------------------------------
def _windows_font(name): return Path(os.environ.get('WINDIR', r'C:\Windows'))/'Fonts'/name


def load_fonts():
    """hello_imgui's load_additional_fonts callback: Segoe UI, Segoe UI Semibold and Consolas, the MDL2 icons merged into
    the first two. Elsewhere (Linux) ImGui's own font, without icons."""
    fonts = imgui.get_io().fonts
    size = metrics()['font']
    loaded, _state['icons'] = [], False
    icons = _windows_font('segmdl2.ttf')
    for name in ('segoeui.ttf', 'seguisb.ttf', 'consola.ttf'):
        path = _windows_font(name)
        font = None
        if sys.platform == 'win32' and path.is_file():
            config = imgui.ImFontConfig(); config.oversample_h = config.oversample_v = 2; config.pixel_snap_h = True
            font = fonts.add_font_from_file_ttf(str(path), size-(1.0 if name == 'consola.ttf' else 0.0), config)
            if font is not None and name != 'consola.ttf' and icons.is_file():
                merge = imgui.ImFontConfig(); merge.merge_mode = True; merge.pixel_snap_h = True
                merge.glyph_offset = imgui.ImVec2(0.0, 2.0); merge.glyph_min_advance_x = size
                if fonts.add_font_from_file_ttf(str(icons), size*0.95, merge) is not None: _state['icons'] = True
        loaded.append(font if font is not None else (loaded[0] if loaded else fonts.add_font_default()))
    _state['fonts'] = loaded
    imgui.get_io().font_default = loaded[0]


def ui_font(): return _state['fonts'][0] if _state['fonts'] else None
def bold_font(): return _state['fonts'][1] if len(_state['fonts']) > 1 else None
def mono_font(): return _state['fonts'][2] if len(_state['fonts']) > 2 else None


class Font:
    """with Font(bold_font(), 1.2): a font and/or a size factor of the base size."""
    def __init__(self, font=None, factor=1.0): self.font, self.factor = font, factor
    def __enter__(self): imgui.push_font(self.font, imgui.get_style().font_size_base*self.factor); return self
    def __exit__(self, *exc): imgui.pop_font()


class Colours:
    """with Colours((imgui.Col_.text, palette().textDim), ...): pushed colours, popped on exit."""
    def __init__(self, *pairs): self.pairs = pairs
    def __enter__(self):
        for index, colour in self.pairs: imgui.push_style_color(index, colour)
        return self
    def __exit__(self, *exc): imgui.pop_style_color(len(self.pairs))


class Vars:
    def __init__(self, *pairs): self.pairs = pairs
    def __enter__(self):
        for index, value in self.pairs: imgui.push_style_var(index, value)
        return self
    def __exit__(self, *exc): imgui.pop_style_var(len(self.pairs))


# -- applying ----------------------------------------------------------------------------------------------------------
def configure(theme, density_key):
    """The theme and density to use, before the ImGui context exists (load_fonts sizes the fonts from the density)."""
    _state['theme'] = theme if theme in THEMES else DEFAULT_THEME
    _state['density'] = density_key if density_key in METRICS else 'compact'
    _, _state['light'], _state['palette'] = THEMES[_state['theme']]


def apply(theme=None, density_key=None, font_scale=None, dpi=None):
    """Palette + density on ImGui's style. Replaces any other theme; call again to switch."""
    if theme is not None: _state['theme'] = theme if theme in THEMES else DEFAULT_THEME
    if density_key is not None: _state['density'] = density_key if density_key in METRICS else 'compact'
    if dpi is None:
        try:
            from imgui_bundle import hello_imgui
            dpi = hello_imgui.dpi_window_size_factor()
        except Exception: dpi = 1.0
    _state['dpi'] = max(0.5, float(dpi or 1.0))
    _, _state['light'], _state['palette'] = THEMES[_state['theme']]
    m, scale = metrics(), _state['dpi']
    style = imgui.get_style()
    v = lambda pair: imgui.ImVec2(pair[0]*scale, pair[1]*scale)
    style.font_size_base = m['font']
    if font_scale is not None: style.font_scale_main = font_scale
    style.window_padding, style.frame_padding, style.item_spacing = v(m['window']), v(m['frame']), v(m['item'])
    style.item_inner_spacing, style.cell_padding = v(m['inner']), v(m['cell'])
    style.indent_spacing, style.scrollbar_size, style.grab_min_size = m['indent']*scale, m['scrollbar']*scale, m['grab']*scale
    style.window_border_size = style.child_border_size = style.popup_border_size = 1.0
    style.frame_border_size, style.tab_border_size, style.tab_bar_border_size, style.tab_bar_overline_size = 0.0, 0.0, 1.0, 2.0
    style.window_rounding, style.child_rounding, style.popup_rounding = m['large']*scale, (m['large']-1)*scale, m['large']*scale
    style.frame_rounding, style.grab_rounding, style.tab_rounding, style.scrollbar_rounding = m['rounding']*scale, m['small']*scale, (m['rounding']+1)*scale, 8.0*scale
    style.window_title_align = imgui.ImVec2(0.0, 0.5)
    style.separator_text_border_size, style.separator_text_padding = 1.0, v((10, 2))
    style.hover_delay_short, style.hover_delay_normal = 0.25, 0.55
    style.anti_aliased_lines = style.anti_aliased_fill = True
    _colours(style)


def _colours(style):
    p, c = palette(), imgui.Col_
    table = {
        c.text: p.text, c.text_disabled: p.textFaint, c.window_bg: p.bg1, c.child_bg: alpha(p.bg2, 0.0), c.popup_bg: alpha(p.bg2, 0.98),
        c.border: p.line, c.border_shadow: 0, c.frame_bg: p.bg3, c.frame_bg_hovered: p.bg4, c.frame_bg_active: p.bg5,
        c.title_bg: p.bg0, c.title_bg_active: p.bg0, c.title_bg_collapsed: p.bg0, c.menu_bar_bg: p.bg0,
        c.scrollbar_bg: alpha(p.bg0, 0.0), c.scrollbar_grab: p.bg5, c.scrollbar_grab_hovered: brighter(p.bg5, 0.12),
        c.scrollbar_grab_active: p.accentDim, c.check_mark: p.accent, c.slider_grab: p.accent, c.slider_grab_active: p.accentHover,
        c.button: p.bg3, c.button_hovered: p.bg4, c.button_active: p.bg5,
        c.header: alpha(p.accent, 0.16), c.header_hovered: p.bg4, c.header_active: alpha(p.accent, 0.26),
        c.separator: p.line, c.separator_hovered: p.accentDim, c.separator_active: p.accent,
        c.resize_grip: alpha(p.bg5, 0.0), c.resize_grip_hovered: p.accentDim, c.resize_grip_active: p.accent,
        c.tab_hovered: p.bg4, c.tab: p.bg0, c.tab_selected: p.bg1, c.tab_selected_overline: p.accent, c.tab_dimmed: p.bg0,
        c.tab_dimmed_selected: p.bg1, c.tab_dimmed_selected_overline: alpha(p.accent, 0.35),
        c.plot_lines: p.info, c.plot_lines_hovered: p.accent, c.plot_histogram: p.accent, c.plot_histogram_hovered: p.accentHover,
        c.table_header_bg: p.bg2, c.table_border_strong: p.lineStrong, c.table_border_light: p.line, c.table_row_bg: 0,
        c.table_row_bg_alt: alpha(p.text, 0.025), c.text_link: p.info, c.text_selected_bg: alpha(p.accent, 0.30),
        c.drag_drop_target: p.accent, c.nav_cursor: p.accent, c.nav_windowing_highlight: alpha(p.accent, 0.7),
        c.nav_windowing_dim_bg: rgb(0, 0.35), c.modal_window_dim_bg: rgb(0, 0.25 if light() else 0.45),
    }
    for name, value in (('input_text_cursor', p.accent), ('tree_lines', p.line)):
        if hasattr(c, name): table[getattr(c, name)] = value
    for index, colour in table.items(): style.set_color_(index, vec(colour))


# -- text --------------------------------------------------------------------------------------------------------------
def _tr(text):
    from ui_common import tr
    return tr(text)


def _label(text):
    from ui_common import label
    return label(text)


def heading(text, level=2):
    """A title: 1 = page (1.5x semibold), 2 = panel (1.2x), 3 = group (1.0x)."""
    with Font(bold_font(), 1.5 if level <= 1 else 1.2 if level == 2 else 1.0), Colours((imgui.Col_.text, palette().text)):
        imgui.text_unformatted(_tr(text))


def section_title(text):
    with Font(bold_font(), 0.85), Colours((imgui.Col_.text, palette().textDim)): imgui.text_unformatted(_tr(text))


def overline(text, colour=0):
    p = palette()
    with Font(bold_font(), 0.78), Colours((imgui.Col_.text, colour or mix(p.accent, p.text, 0.35))): imgui.text_unformatted(_tr(text).upper())


def text_coloured(colour, text):
    with Colours((imgui.Col_.text, colour)): imgui.text_unformatted(text)


def text_dim(text): text_coloured(palette().textDim, text)
def text_faint(text): text_coloured(palette().textFaint, text)


def wrapped(text, colour=None):
    with Colours((imgui.Col_.text, colour if colour is not None else palette().text)): imgui.text_wrapped(text)


def wrapped_dim(text): wrapped(text, palette().textDim)
def wrapped_faint(text): wrapped(text, palette().textFaint)


def text_mono(text):
    with Font(mono_font(), 1.0): imgui.text_unformatted(text)


def kbd(keys):
    p = palette()
    with Font(None, 0.82):
        size = imgui.calc_text_size(keys); pad = dp(5, 1)
        origin = imgui.get_cursor_screen_pos(); box = (size.x+pad[0]*2, size.y+pad[1]*2)
        draw, rounding = imgui.get_window_draw_list(), dp(3)
        draw.add_rect_filled((origin.x, origin.y+dp(1)), (origin.x+box[0], origin.y+box[1]+dp(1)), p.lineStrong, rounding)
        draw.add_rect_filled(origin, (origin.x+box[0], origin.y+box[1]), p.bg3, rounding)
        draw.add_rect(origin, (origin.x+box[0], origin.y+box[1]), p.line, rounding)
        draw.add_text((origin.x+pad[0], origin.y+pad[1]), p.textDim, keys)
        imgui.dummy((box[0], box[1]+dp(1)))


def tooltip(text):
    """A delayed, wrapped tooltip for the last item. The text is shown as given."""
    if not text or not imgui.is_item_hovered(imgui.HoveredFlags_.delay_short | imgui.HoveredFlags_.no_shared_delay): return
    if imgui.begin_tooltip():
        imgui.push_text_wrap_pos(imgui.get_font_size()*32); imgui.text_unformatted(text); imgui.pop_text_wrap_pos()
        imgui.end_tooltip()


def help_marker(text):
    """A small (i) after the previous item; its tooltip explains an option."""
    imgui.same_line(0, dp(4))
    imgui.text_disabled(icon('info'))
    if imgui.is_item_hovered() and imgui.begin_tooltip():
        imgui.push_text_wrap_pos(imgui.get_font_size()*32); imgui.text_unformatted(_tr(text)); imgui.pop_text_wrap_pos()
        imgui.end_tooltip()


def clipped_text(draw, position, width, colour, text):
    if width <= 4: return
    if imgui.calc_text_size(text).x <= width: draw.add_text(position, colour, text); return
    room = width-imgui.calc_text_size('...').x
    while text and imgui.calc_text_size(text).x > room: text = text[:-1]
    draw.add_text(position, colour, text+'...')


def centred_text(draw, minimum, maximum, colour, text):
    size = imgui.calc_text_size(text)
    draw.add_text((minimum[0]+(maximum[0]-minimum[0]-size.x)*0.5, minimum[1]+(maximum[1]-minimum[1]-size.y)*0.5), colour, text)


# -- buttons -------------------------------------------------------------------------------------------------------
def _variant(variant):
    p = palette()
    if variant == 'primary': return p.accent, p.accentHover, brighter(p.accent, 0.2), p.accentText, 0
    if variant == 'ghost': return alpha(p.bg3, 0.0), p.bg4, p.bg5, p.text, 0
    if variant == 'outline': return alpha(p.bg3, 0.0), alpha(p.accent, 0.12), alpha(p.accent, 0.22), p.text, p.lineStrong
    if variant in ('danger', 'success'):
        tone = p.error if variant == 'danger' else p.success
        ground = mix(tone, p.bg1, 0.35 if variant == 'danger' else 0.25)
        return ground, tone, brighter(tone, 0.15), contrast_text(ground), 0
    return p.bg3, p.bg4, p.bg5, p.text, 0


def button(text, variant='secondary', size=(0, 0), small=False):
    """secondary (most buttons), primary (the ONE main action of a view), ghost (toolbars), outline, danger, success."""
    ground, hovered, active, colour, border = _variant(variant)
    c = imgui.Col_
    pairs = [(c.button, ground), (c.button_hovered, hovered), (c.button_active, active), (c.text, colour)]+([(c.border, border)] if border else [])
    with Colours(*pairs), Vars(*([(imgui.StyleVar_.frame_border_size, 1.0)] if border else [])):
        return imgui.small_button(_label(text)) if small else imgui.button(_label(text), size)


def primary_button(text, size=(0, 0)): return button(text, 'primary', size)
def danger_button(text, size=(0, 0)): return button(text, 'danger', size)
def ghost_button(text, size=(0, 0)): return button(text, 'ghost', size)


def icon_text_button(name, text, variant='secondary', size=(0, 0), small=False):
    """An icon then a label. The label keeps its identity, so adding the icon changes no ID."""
    visible, _, identity = _label(text).partition('###')
    return button((icon(name)+'  ' if icons_available() else '')+visible+'###'+identity, variant, size, small)


def icon_button(name, tip=None, active=False, active_colour=0, size=None, id=None, colour=0):
    """A flat square icon button, tinted when active; every one has a tooltip naming the action (and its shortcut)."""
    p = palette()
    height = imgui.get_frame_height()
    width = (size or (0, 0))[0] or height+dp(2)
    tall = (size or (0, 0))[1] or height
    origin = imgui.get_cursor_screen_pos()
    imgui.push_id(id or (name+'|'+(tip or '')))
    clicked = imgui.invisible_button('##icon', (width, tall))
    hovered, held = imgui.is_item_hovered(), imgui.is_item_active()
    imgui.pop_id()
    draw = imgui.get_window_draw_list()
    tint, rounding, maximum = active_colour or p.accent, imgui.get_style().frame_rounding, (origin.x+width, origin.y+tall)
    if active: draw.add_rect_filled(origin, maximum, alpha(tint, 0.28 if held else 0.18), rounding)
    elif hovered: draw.add_rect_filled(origin, maximum, p.bg5 if held else p.bg4, rounding)
    if not imgui.is_item_visible(): return clicked
    centred_text(draw, (origin.x, origin.y), maximum, tint if active else (colour or (p.text if hovered else p.textDim)), icon(name))
    if tip: tooltip(_tr(tip))
    return clicked


def toggle_switch(text, value):
    """An on/off switch with its label after it (settings). Returns (clicked, value)."""
    p, style = palette(), imgui.get_style()
    height = imgui.get_frame_height()
    track_height = round(height*0.72); track_width = round(track_height*1.8)
    shown = _label(text)
    visible = shown.partition('##')[0]
    size = imgui.calc_text_size(visible)
    origin = imgui.get_cursor_screen_pos()
    clicked = imgui.invisible_button(shown, (track_width+(style.item_inner_spacing.x+size.x if visible else 0), height))
    if clicked: value = not value
    hovered = imgui.is_item_hovered()
    storage, key, target = imgui.get_state_storage(), imgui.get_item_id(), 1.0 if value else 0.0
    t = storage.get_float(key, target)
    step = imgui.get_io().delta_time*12
    t = min(target, t+step) if t < target else max(target, t-step)
    storage.set_float(key, t)
    draw = imgui.get_window_draw_list()
    top = origin.y+(height-track_height)*0.5
    off, on = (p.bg5 if hovered else p.bg4), (p.accentHover if hovered else p.accent)
    draw.add_rect_filled((origin.x, top), (origin.x+track_width, top+track_height), mix(off, on, t), track_height*0.5)
    radius = track_height*0.5-dp(2.5)
    centre = (origin.x+track_height*0.5+(track_width-track_height)*t, top+track_height*0.5)
    off_knob = p.text if contrast_text(p.bg1) == rgb(0xffffff) else rgb(0xffffff)
    draw.add_circle_filled((centre[0], centre[1]+dp(0.5)), radius+dp(0.5), rgb(0, 0.18), 20)
    draw.add_circle_filled(centre, radius, mix(off_knob, contrast_text(p.accent), t), 20)
    if visible: draw.add_text((origin.x+track_width+style.item_inner_spacing.x, origin.y+(height-size.y)*0.5), p.text, visible)
    return clicked, value


def segmented(id, labels, current, width=0.0):
    """Joined buttons, one selected (modes, views). width -1 fills the row. Returns (changed, current)."""
    p, style = palette(), imgui.get_style()
    imgui.push_id(id)
    height, inset = imgui.get_frame_height(), dp(2)
    texts = [_tr(text) for text in labels]
    widths = [imgui.calc_text_size(text).x+style.frame_padding.x*2.6 for text in texts]
    natural = sum(widths)
    total = width if width > 0 else (imgui.get_content_region_avail().x if width < 0 else natural+inset*2)
    scale = (total-inset*2)/natural if natural else 1.0
    origin = imgui.get_cursor_screen_pos()
    draw = imgui.get_window_draw_list()
    draw.add_rect_filled(origin, (origin.x+total, origin.y+height), p.bg0, style.frame_rounding+inset)
    changed, x = False, origin.x+inset
    for index, text in enumerate(texts):
        w = widths[index]*scale
        imgui.set_cursor_screen_pos((x, origin.y+inset))
        imgui.push_id(index)
        if imgui.invisible_button('##segment', (w, height-inset*2)) and current != index: current, changed = index, True
        hovered = imgui.is_item_hovered()
        imgui.pop_id()
        selected = current == index
        low, high = (x, origin.y+inset), (x+w, origin.y+height-inset)
        if selected: draw.add_rect_filled(low, high, p.accentDim, style.frame_rounding)
        elif hovered: draw.add_rect_filled(low, high, p.bg3, style.frame_rounding)
        size = imgui.calc_text_size(text)
        draw.add_text((low[0]+(w-size.x)*0.5, low[1]+(height-inset*2-size.y)*0.5),
                      contrast_text(p.accentDim) if selected else (p.text if hovered else p.textDim), text)
        x += w
    imgui.set_cursor_screen_pos(origin); imgui.dummy((total, height))
    imgui.pop_id()
    return changed, current


# -- fields --------------------------------------------------------------------------------------------------------
def search_field(id, value, hint='Search', width=0.0, flags=0):
    """A rounded search box: magnifier, hint, a clear button. Returns (activated, value); with
    InputTextFlags_.enter_returns_true, activated means Enter (or the clear button) was pressed."""
    p, style = palette(), imgui.get_style()
    height = imgui.get_frame_height(); room = height*0.9
    imgui.push_id(id)
    origin = imgui.get_cursor_screen_pos()
    field = max(dp(40), width if width > 0 else (imgui.get_content_region_avail().x+width if width < 0 else imgui.calc_item_width()))
    imgui.set_next_item_width(field); imgui.set_next_item_allow_overlap()
    with Vars((imgui.StyleVar_.frame_padding, imgui.ImVec2(style.frame_padding.x+room*0.75, style.frame_padding.y)), (imgui.StyleVar_.frame_rounding, height*0.5)):
        activated, value = imgui.input_text_with_hint('##search', _tr(hint), value, flags)
    focused = imgui.is_item_active()
    end = imgui.get_cursor_screen_pos()
    draw = imgui.get_window_draw_list()
    centre, radius = (origin.x+style.frame_padding.x+room*0.3, origin.y+height*0.5), height*0.48*0.32
    colour = p.accent if focused else p.textFaint
    draw.add_circle((centre[0]-radius*0.25, centre[1]-radius*0.25), radius, colour, 16, dp(1.4))
    draw.add_line((centre[0]+radius*0.45, centre[1]+radius*0.45), (centre[0]+radius*1.35, centre[1]+radius*1.35), colour, dp(1.6))
    if value:
        imgui.set_cursor_screen_pos((origin.x+field-height, origin.y))
        if imgui.invisible_button('##clear', (height, height)): value, activated = '', True
        tooltip(_tr('Clear'))
        hovered = imgui.is_item_hovered()
        cx, cy, half = origin.x+field-height*0.5, origin.y+height*0.5, height*0.26*0.5
        cross = p.text if hovered else p.textFaint
        draw.add_line((cx-half, cy-half), (cx+half, cy+half), cross, dp(1.4)); draw.add_line((cx-half, cy+half), (cx+half, cy-half), cross, dp(1.4))
        imgui.set_cursor_screen_pos(end)
    imgui.pop_id()
    return activated, value


# -- containers ----------------------------------------------------------------------------------------------------
TONES = ('neutral', 'accent', 'success', 'warning', 'error', 'info')


def tone_colour(tone):
    p = palette()
    return {'accent': p.accent, 'success': p.success, 'warning': p.warning, 'error': p.error, 'info': p.info}.get(tone, p.textDim)


def begin_card(id, title=None, height=0.0, tone='neutral', width=0.0):
    """A card: raised ground (bg2), a line, padding, an optional title. ALWAYS call end_card().
    height 0 = fit content, > 0 = fixed (dp), < 0 = fill minus that much."""
    p, m = palette(), metrics()
    toned = tone != 'neutral'
    ground = mix(p.bg2, tone_colour(tone), 0.08) if toned else p.bg2
    border = mix(p.line, tone_colour(tone), 0.55) if toned else p.line
    flags = imgui.ChildFlags_.borders | imgui.ChildFlags_.always_use_window_padding | (imgui.ChildFlags_.auto_resize_y if height == 0 else 0)
    with Colours((imgui.Col_.child_bg, ground), (imgui.Col_.border, border)), \
         Vars((imgui.StyleVar_.child_rounding, dp(m['large']+2)), (imgui.StyleVar_.window_padding, imgui.ImVec2(*dp(m['card'], m['card'])))):
        shown = imgui.begin_child(id, (width, 0 if height == 0 else (dp(height) if height > 0 else height)), flags)
    if shown and title: heading(title, 3); imgui.dummy((0, dp(2)))
    return shown


def end_card(): imgui.end_child()


def begin_section(text, default_open=True, id=None):
    """A collapsible section with a full-width header bar. Call end_section() only when it returned True."""
    p = palette()
    with Colours((imgui.Col_.header, p.bg2), (imgui.Col_.header_hovered, p.bg3), (imgui.Col_.header_active, p.bg4)), Font(bold_font(), 0.92):
        return imgui.collapsing_header(_label(text), imgui.TreeNodeFlags_.default_open if default_open else 0)


def end_section(): imgui.dummy((0, dp(4)))


def begin_properties(id, label_width=0.0):
    """Label / value rows in two aligned columns. Call end_properties() only when it returned True."""
    avail = imgui.get_content_region_avail().x
    width = dp(label_width) if label_width > 0 else max(dp(80), avail*0.38)
    if not imgui.begin_table(id, 2, 0): return False
    imgui.table_setup_column('##label', imgui.TableColumnFlags_.width_fixed, width)
    imgui.table_setup_column('##value', imgui.TableColumnFlags_.width_stretch)
    return True


def property(text, help=None):
    """The label of the next row; the value column is readied, full width, for the control."""
    imgui.table_next_row(); imgui.table_set_column_index(0)
    imgui.align_text_to_frame_padding()
    shown = _tr(text)
    room = imgui.get_content_region_avail().x-(imgui.get_font_size() if help else 0)
    if imgui.calc_text_size(shown).x <= room: text_dim(shown)
    else:
        position = imgui.get_cursor_screen_pos()
        clipped_text(imgui.get_window_draw_list(), (position.x, position.y+imgui.get_style().frame_padding.y), room, palette().textDim, shown)
        imgui.dummy((room, imgui.get_frame_height())); tooltip(shown)
    if help: help_marker(help)
    imgui.table_set_column_index(1); imgui.set_next_item_width(-1e-6)


def end_properties(): imgui.end_table()


def toolbar_separator():
    imgui.same_line(0, dp(6))
    origin, height = imgui.get_cursor_screen_pos(), imgui.get_frame_height()
    imgui.get_window_draw_list().add_line((origin.x, origin.y+height*0.18), (origin.x, origin.y+height*0.82), palette().lineStrong)
    imgui.dummy((dp(1), height)); imgui.same_line(0, dp(6))


def divider(spacing=4.0):
    imgui.dummy((0, dp(spacing)))
    origin, width = imgui.get_cursor_screen_pos(), imgui.get_content_region_avail().x
    imgui.get_window_draw_list().add_line(origin, (origin.x+width, origin.y), palette().line)
    imgui.dummy((0, dp(spacing)))


def space(height=8.0): imgui.dummy((0, dp(height)))


# -- status & feedback -------------------------------------------------------------------------------------------------
def badge(text, tone='neutral', translate=True):
    """A small rounded pill on the text line: badge('Installed', 'success')."""
    p = palette()
    colour = p.textDim if tone == 'neutral' else tone_colour(tone)
    shown = _tr(text) if translate else text
    with Font(bold_font(), 0.74):
        size, pad = imgui.calc_text_size(shown), dp(6, 2)
        box = (size.x+pad[0]*2, size.y+pad[1]*2)
        origin = imgui.get_cursor_screen_pos()
        y = origin.y+max(0.0, (imgui.get_text_line_height()/0.74-box[1])*0.5)
        draw, rounding = imgui.get_window_draw_list(), dp(metrics()['small']+1)
        draw.add_rect_filled((origin.x, y), (origin.x+box[0], y+box[1]), p.bg4 if tone == 'neutral' else alpha(colour, 0.16), rounding)
        draw.add_rect((origin.x, y), (origin.x+box[0], y+box[1]), alpha(colour, 0.35), rounding)
        draw.add_text((origin.x+pad[0], y+pad[1]), p.text if tone == 'neutral' else mix(colour, p.text, 0.3), shown)
        imgui.dummy(box)


def status_dot(colour, tip=None, framed=False):
    """A coloured dot on the text line; framed=True on a line of frames (a property row, next to a button)."""
    line, origin = imgui.get_text_line_height(), imgui.get_cursor_screen_pos()
    height = imgui.get_frame_height() if framed else line
    radius = line*0.24
    imgui.dummy((radius*2+dp(2), height))
    draw, centre = imgui.get_window_draw_list(), (origin.x+radius+dp(1), origin.y+height*0.5)
    draw.add_circle_filled(centre, radius*1.8, alpha(colour, 0.18), 16)
    draw.add_circle_filled(centre, radius, colour, 16)
    if tip: tooltip(tip)


def progress_bar(fraction, size=(-1, 0), overlay=None, tone='accent'):
    """A thin bar (a full-height one with an overlay); fraction < 0 is indeterminate."""
    p = palette()
    width, height = size
    if width <= 0: width = max(dp(20), imgui.get_content_region_avail().x+(width+1 if width < 0 else 0))
    if height <= 0: height = imgui.get_frame_height() if overlay else dp(6)
    origin = imgui.get_cursor_screen_pos(); imgui.dummy((width, height))
    draw = imgui.get_window_draw_list()
    rounding = min(height*0.5, imgui.get_style().frame_rounding+dp(2))
    maximum = (origin.x+width, origin.y+height)
    colour = p.textDim if tone == 'neutral' else tone_colour(tone)
    draw.add_rect_filled(origin, maximum, p.bg3, rounding)
    if fraction >= 0:
        t = max(0.0, min(1.0, fraction))
        if t > 0: draw.add_rect_filled(origin, (origin.x+max(rounding*2, width*t), maximum[1]), alpha(colour, 0.85) if overlay else colour, rounding)
    else:
        phase = math.fmod(imgui.get_time()*0.8, 1.0); segment = width*0.3; x = origin.x-segment+(width+segment)*phase
        draw.push_clip_rect(origin, maximum, True); draw.add_rect_filled((x, origin.y), (x+segment, maximum[1]), colour, rounding); draw.pop_clip_rect()
    if overlay:
        draw.push_clip_rect(origin, maximum, True)
        clipped_text(draw, (origin.x+dp(8), origin.y+(height-imgui.get_text_line_height())*0.5), width-dp(16), p.text, overlay)
        draw.pop_clip_rect()


def empty_state(title, message=None, icon_name=None):
    """A centred title and message filling the rest of a panel: an empty panel always says why."""
    p = palette()
    area, origin = imgui.get_content_region_avail(), imgui.get_cursor_screen_pos()
    draw = imgui.get_window_draw_list()
    middle = origin.y+max(dp(60), area.y*0.45)
    if icon_name and icons_available():
        with Font(ui_font(), 2.4): centred_text(draw, (origin.x, middle-dp(70)), (origin.x+area.x, middle-dp(24)), p.textFaint, icon(icon_name))
    with Font(bold_font(), 1.1): centred_text(draw, (origin.x, middle-dp(22)), (origin.x+area.x, middle), p.textDim, _tr(title))
    if message:
        text = _tr(message); wrap = max(dp(60), area.x-dp(40))
        size = imgui.calc_text_size(text, None, False, wrap)
        x = origin.x+(area.x-min(size.x, wrap))*0.5
        draw.add_text(imgui.get_font(), imgui.get_font_size(), (x, middle+dp(2)), p.textFaint, text, None, wrap)
    imgui.dummy((area.x, max(0.0, middle+dp(40)-origin.y)))


def callout(tone, text, width=0.0):
    """A notice block with a coloured bar, for a standing condition: callout('warning', tr('...'))."""
    p = palette()
    colour = p.textDim if tone == 'neutral' else tone_colour(tone)
    width = width or imgui.get_content_region_avail().x
    pad, bar = dp(10, 7), dp(3)
    wrap = max(dp(40), width-pad[0]*2-bar)
    size = imgui.calc_text_size(text, None, False, wrap)
    origin = imgui.get_cursor_screen_pos()
    maximum = (origin.x+width, origin.y+size.y+pad[1]*2)
    draw, rounding = imgui.get_window_draw_list(), imgui.get_style().frame_rounding
    draw.add_rect_filled(origin, maximum, mix(p.bg2, colour, 0.10), rounding)
    draw.add_rect_filled(origin, (origin.x+bar, maximum[1]), colour, rounding, imgui.ImDrawFlags_.round_corners_left)
    draw.add_text(imgui.get_font(), imgui.get_font_size(), (origin.x+bar+pad[0], origin.y+pad[1]), p.text, text, None, wrap)
    imgui.dummy((width, maximum[1]-origin.y))


def begin_callout_row(id, tone, text):
    """A callout with buttons on its right: draw the buttons after it, then end_callout_row(). Always call the end."""
    p = palette()
    colour = p.textDim if tone == 'neutral' else tone_colour(tone)
    with Colours((imgui.Col_.child_bg, mix(p.bg2, colour, 0.10)), (imgui.Col_.border, alpha(colour, 0.0))), \
         Vars((imgui.StyleVar_.window_padding, imgui.ImVec2(*dp(10, 5))), (imgui.StyleVar_.child_rounding, imgui.get_style().frame_rounding)):
        shown = imgui.begin_child(id, (0, 0), imgui.ChildFlags_.auto_resize_y | imgui.ChildFlags_.always_use_window_padding,
                                  imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse)
    if shown:
        window_pos, window_size = imgui.get_window_pos(), imgui.get_window_size()
        imgui.get_window_draw_list().add_rect_filled(window_pos, (window_pos.x+dp(3), window_pos.y+window_size.y), colour,
                                                     imgui.get_style().frame_rounding, imgui.ImDrawFlags_.round_corners_left)
        imgui.align_text_to_frame_padding(); imgui.text_unformatted(text)
    return shown


def end_callout_row(): imgui.end_child(); imgui.dummy((0, dp(2)))


def notify(text, tone='neutral', seconds=4.0):
    """A toast, bottom-right of the window (events: saved, copied, finished). render_notifications() draws them."""
    _state['toast_id'] += 1
    _state['toasts'].append({'text': text, 'tone': tone, 'until': imgui.get_time()+seconds, 'id': _state['toast_id']})
    del _state['toasts'][:-6]


def render_notifications():
    now = imgui.get_time()
    _state['toasts'] = [toast for toast in _state['toasts'] if toast['until'] >= now]
    if not _state['toasts']: return
    p, m = palette(), metrics()
    viewport = imgui.get_main_viewport()
    x, y = viewport.work_pos.x+viewport.work_size.x-dp(16), viewport.work_pos.y+viewport.work_size.y-dp(40)
    flags = (imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.always_auto_resize | imgui.WindowFlags_.no_saved_settings |
             imgui.WindowFlags_.no_focus_on_appearing | imgui.WindowFlags_.no_nav | imgui.WindowFlags_.no_move)
    for toast in reversed(_state['toasts']):
        fade = max(0.0, min(1.0, (toast['until']-now)/0.3))
        imgui.set_next_window_pos((x, y), imgui.Cond_.always, (1.0, 1.0)); imgui.set_next_window_bg_alpha(0.98*fade)
        height = 0.0
        with Vars((imgui.StyleVar_.window_padding, imgui.ImVec2(*dp(14, 9))), (imgui.StyleVar_.window_rounding, dp(m['large']+2)), (imgui.StyleVar_.alpha, fade)), \
             Colours((imgui.Col_.window_bg, p.bg2), (imgui.Col_.border, p.lineStrong)):
            if imgui.begin('##cyuiToast%d' % toast['id'], None, flags)[0]:
                colour = p.accent if toast['tone'] == 'neutral' else tone_colour(toast['tone'])
                position, size = imgui.get_window_pos(), imgui.get_window_size()
                imgui.get_window_draw_list().add_rect_filled(position, (position.x+dp(3), position.y+size.y), colour, dp(m['large']+2), imgui.ImDrawFlags_.round_corners_left)
                imgui.push_text_wrap_pos(imgui.get_font_size()*26); imgui.text_unformatted(toast['text']); imgui.pop_text_wrap_pos()
                if imgui.is_window_hovered() and imgui.is_mouse_clicked(imgui.MouseButton_.left): toast['until'] = now+0.3
                height = size.y
            imgui.end()
        y -= height+dp(8)


def chip_width(text):
    return imgui.calc_text_size(text).x+dp(16)+imgui.get_font_size()*0.9


def chip(text, id, tip=None, tone='neutral'):
    """A pill with a cross (an active filter, a tag): True when clicked, which removes it. The text is shown as given."""
    p = palette()
    size, height = imgui.calc_text_size(text), imgui.get_frame_height()
    width = chip_width(text)
    origin = imgui.get_cursor_screen_pos()
    clicked = imgui.invisible_button(id, (width, height))
    hovered = imgui.is_item_hovered()
    colour = tone_colour(tone)
    ground = alpha(colour, 0.26 if hovered else 0.16) if tone != 'neutral' else (p.bg4 if hovered else p.bg3)
    draw = imgui.get_window_draw_list()
    draw.add_rect_filled(origin, (origin.x+width, origin.y+height), ground, height*0.5)
    draw.add_text((origin.x+dp(8), origin.y+(height-size.y)*0.5), p.text, text)
    cx, cy, half = origin.x+width-dp(8)-imgui.get_font_size()*0.35, origin.y+height*0.5, imgui.get_font_size()*0.2
    cross = p.text if hovered else p.textDim
    draw.add_line((cx-half, cy-half), (cx+half, cy+half), cross, dp(1.3)); draw.add_line((cx-half, cy+half), (cx+half, cy-half), cross, dp(1.3))
    if tip: tooltip(tip)
    return clicked


def flow(width):
    """Before an item of `width`: on the same line when it still fits, else on the next one (rows of chips)."""
    imgui.same_line()
    if imgui.get_content_region_avail().x < width: imgui.new_line()


def button_width(text):
    """Width of a button showing `text` (already translated), to align a row to the right."""
    return imgui.calc_text_size(text, None, True).x+imgui.get_style().frame_padding.x*2


def segmented_width(labels):
    return sum(imgui.calc_text_size(_tr(text)).x+imgui.get_style().frame_padding.x*2.6 for text in labels)+dp(4)


def status_text(tone, text):
    """Text of a status bar: faint when neutral, the tone's colour otherwise."""
    with Font(None, 0.86): text_coloured(palette().textFaint if tone == 'neutral' else tone_colour(tone), text)


def panel_header(title, subtitle=None):
    heading(title, 2)
    if subtitle:
        with Font(None, 0.88): text_faint(subtitle)
