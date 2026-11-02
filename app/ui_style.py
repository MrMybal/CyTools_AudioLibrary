"""AudioLibrary layout/translation adapters; CyUI itself is unchanged upstream code."""
from cyui import *
import cyui as core
from ui_common import tr as _tr, label as _label
def Colours(*pairs): return core.scoped_color(*(x for pair in pairs for x in pair))
def Vars(*pairs): return core.scoped_var(*(x for pair in pairs for x in pair))
Font=core.scoped_font
light=core.is_light; theme_key=core.current_theme
DEFAULT_THEME='mid-grey'; DENSITIES=('compact','comfortable')
THEMES={k:(name,light,type('Palette',(),palette)()) for k,name,palette,light in core.THEMES}
def dp(x,y=None): return core.dp(x) if y is None else tuple(core.dp2(x,y))
_configuration={'theme':'mid-grey','density':'compact'}
def load_fonts(*args,**kwargs):
    kwargs.setdefault('size',16. if _configuration['density']=='comfortable' else 14.)
    return core.load_fonts(*args,**kwargs)
def configure(theme,density_key):
    _configuration.update(theme=theme,density=density_key)
def apply(theme=None,density_key=None,font_scale=None,dpi=None):
    if dpi is None:
        from imgui_bundle import hello_imgui
        dpi=hello_imgui.dpi_window_size_factor()
    core.apply(theme or core.current_theme(),density_key or core.density(),dpi)
    if font_scale is not None: imgui.get_style().font_scale_main=font_scale
def icon(name): return getattr(core.icon,name,name if len(name)==1 else '')
def icon_button(name,tip=None,active=False,active_colour=0,size=None,id=None,colour=0):
    with core.scoped_id(id or name+'|'+str(tip)):
        return core.icon_button(icon(name),_tr(tip or ''),active,active_colour,size or (0,0))
def icon_text_button(name,text,variant='secondary',size=(0,0),small=False):
    return core.button((icon(name)+'  ' if core.icons_available() else '')+_label(text),variant,size,small)
def button(text,variant='secondary',size=(0,0),small=False): return core.button(_label(text),variant,size,small)
def primary_button(text,size=(0,0)): return button(text,'primary',size)
def danger_button(text,size=(0,0)): return button(text,'danger',size)
def ghost_button(text,size=(0,0)): return button(text,'ghost',size)
def heading(text,level=2): core.heading(_tr(text),level)
def section_title(text): core.section_title(_tr(text))
def wrapped_dim(text):
    imgui.push_text_wrap_pos(0);core.text_dim(text);imgui.pop_text_wrap_pos()
def wrapped_faint(text):
    imgui.push_text_wrap_pos(0);core.text_faint(text);imgui.pop_text_wrap_pos()
def wrapped(text,colour=0):
    imgui.push_text_wrap_pos(0);core.text_coloured(colour or core.palette().text,text);imgui.pop_text_wrap_pos()
def property(text,help=None): core.property(_tr(text),_tr(help or ''))
def begin_section(text,default_open=True,id=None): return core.begin_section(_label(text) if id is None else _tr(text)+'###'+id,default_open)
def begin_card(id,title=None,height=0.,tone='neutral',width=0.): return core.begin_card(id,_tr(title or ''),height,tone)
def badge(text,tone='neutral',translate=True): return core.badge(_tr(text) if translate else text,tone)
def status_dot(colour,tip=None,framed=False): return core.status_dot(colour,_tr(tip or ''))
def progress_bar(fraction,size=(-1,0),overlay=None,tone='accent'): return core.progress_bar(fraction,size,overlay or '',tone)
def panel_header(title,subtitle=None): return core.panel_header(_tr(title),_tr(subtitle or ''))
def empty_state(title,message=None,icon_name=None): return core.empty_state(_tr(title),_tr(message or ''),icon(icon_name or ''))
def callout(tone,text,width=0.): return core.callout(tone,text)
def segmented(id,labels,current,width=0.): return core.segmented(id,[_tr(x) for x in labels],current,width)
def toggle_switch(text,value): return core.toggle_switch(_label(text),value)

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

def segmented_width(labels):
    return sum(imgui.calc_text_size(_tr(text)).x+imgui.get_style().frame_padding.x*2.6 for text in labels)+dp(4)

def search_field(identifier,text,hint='Search',width=0.,flags=0):
    changed,text=core.search_field(identifier,text,_tr(hint),width)
    if flags & imgui.InputTextFlags_.enter_returns_true:
        return imgui.is_item_active() and imgui.is_key_pressed(imgui.Key.enter,False),text
    return changed,text
