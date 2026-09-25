"""Interactive waveform: cached peak pyramid, real-time playhead, zoom, pan, seek, selection.

Drawing reads at most one (min, max) pair per pixel column from the pyramid level that fits
the zoom, so a one hour file costs the same as a short one. Below the finest level the
decoded samples of the player are used (sample-level detail). Interaction:
  wheel = zoom around the cursor, Shift+wheel or middle-drag = pan, click = seek,
  drag = selection, double-click = clear selection.
"""
import numpy as np
from imgui_bundle import imgui

from audiolib.waveform import BASE, Pyramid


def clock(seconds):
    seconds = max(0.0, float(seconds))
    return '%02d:%06.3f' % (int(seconds//60), seconds % 60)


class WaveformView:
    def __init__(self):
        self.pyramid = None
        self.view = (0.0, 1.0)      # visible time range, seconds
        self.drag_start = None
        self.marker = None          # (start, stop) of a matched search segment, drawn as a band
        self._cache_key, self._cache = None, None

    def set_file(self, path):
        self.pyramid, self._cache_key, self.marker, self.drag_start = None, None, None, None
        try:
            if path is not None and path.is_file(): self.pyramid = Pyramid(path)
        except (OSError, ValueError): self.pyramid = None
        self.view = (0.0, max(0.05, self.pyramid.duration if self.pyramid else 1.0))

    def reset_zoom(self):
        if self.pyramid: self.view = (0.0, max(0.05, self.pyramid.duration))

    def focus(self, start, stop):
        """Zoom on a matched segment, with context around it."""
        if not self.pyramid: return
        margin = max(1.0, (stop-start)*0.75)
        self.view = (max(0.0, start-margin), min(self.pyramid.duration, stop+margin))

    def _peaks(self, player, width):
        start, stop = self.view
        key = (id(self.pyramid), round(start, 6), round(stop, 6), int(width), len(player.audio))
        if key == self._cache_key: return self._cache
        per_pixel = (stop-start)*self.pyramid.sample_rate/max(1, width)
        samples = player.samples(start, stop) if per_pixel < BASE else None
        if samples is not None and len(samples):
            mono_low, mono_high = samples.min(axis=1), samples.max(axis=1)
            if len(mono_low) > width:
                edges = np.linspace(0, len(mono_low), int(width)+1).astype(int)[:-1]
                low, high = np.minimum.reduceat(mono_low, edges), np.maximum.reduceat(mono_high, edges)
            else: low, high = mono_low, mono_high
        else: low, high = self.pyramid.read(start, stop, width)
        self._cache_key, self._cache = key, (low, high)
        return self._cache

    def draw(self, player, height=150.0, tr=lambda text: text):
        """Returns an event dict: {'seek': seconds} and/or {'selection': (a, b) | None}."""
        events = {}
        width = max(64.0, imgui.get_content_region_avail().x)
        origin = imgui.get_cursor_screen_pos()
        imgui.invisible_button('##waveform', (width, height))
        hovered, active = imgui.is_item_hovered(), imgui.is_item_active()
        draw = imgui.get_window_draw_list()
        x0, y0, x1, y1 = origin.x, origin.y, origin.x+width, origin.y+height
        colour = lambda r, g, b, a=1.0: imgui.get_color_u32((r, g, b, a))
        draw.add_rect_filled((x0, y0), (x1, y1), colour(0.08, 0.09, 0.11))
        if self.pyramid is None:
            draw.add_text((x0+10, y0+height/2-8), colour(0.6, 0.6, 0.6), tr('Waveform not available yet: scan the Library'))
            return events
        duration = self.pyramid.duration
        start, stop = self.view
        span = max(1e-6, stop-start)
        to_x = lambda t: x0+(t-start)/span*width
        to_t = lambda x: start+(x-x0)/width*span
        mouse = imgui.get_mouse_pos()
        io = imgui.get_io()
        # -- zoom / pan ---------------------------------------------------------
        if hovered and io.mouse_wheel != 0:
            if io.key_shift: shift = -io.mouse_wheel*span*0.15
            else:
                factor = 0.8 if io.mouse_wheel > 0 else 1.25
                minimum = 64/self.pyramid.sample_rate       # never closer than 64 samples across the view
                new_span = float(np.clip(span*factor, minimum, duration))
                anchor = to_t(mouse.x); ratio = (mouse.x-x0)/width
                start, stop = anchor-ratio*new_span, anchor+(1-ratio)*new_span; shift = 0.0
            start, stop = start+shift, stop+shift
        if hovered and imgui.is_mouse_dragging(imgui.MouseButton_.middle):
            delta = -io.mouse_delta.x/width*span; start, stop = start+delta, stop+delta
        if start < 0: start, stop = 0.0, stop-start
        if stop > duration: start, stop = max(0.0, start-(stop-duration)), duration
        self.view = (start, stop); span = max(1e-6, stop-start)
        # -- selection / seek ------------------------------------------------------
        if hovered and imgui.is_mouse_double_clicked(imgui.MouseButton_.left):
            player.selection = None; events['selection'] = None
        elif hovered and imgui.is_mouse_clicked(imgui.MouseButton_.left):
            self.drag_start, self.dragged = float(np.clip(to_t(mouse.x), 0, duration)), False
        if self.drag_start is not None and active and imgui.is_mouse_dragging(imgui.MouseButton_.left, 4.0):
            self.dragged = True
            player.selection = tuple(sorted((self.drag_start, float(np.clip(to_t(mouse.x), 0, duration)))))
        if self.drag_start is not None and imgui.is_mouse_released(imgui.MouseButton_.left):
            if self.dragged: events['selection'] = player.selection      # a drag selects, a plain click seeks
            else: events['seek'] = self.drag_start
            self.drag_start = None
        # -- bands: matched segment, selection ---------------------------------------
        if self.marker:
            draw.add_rect_filled((max(x0, to_x(self.marker[0])), y0), (min(x1, to_x(self.marker[1])), y1), colour(0.95, 0.75, 0.2, 0.16))
        if player.selection:
            a, b = player.selection
            draw.add_rect_filled((max(x0, to_x(a)), y0), (min(x1, to_x(b)), y1), colour(0.35, 0.6, 1.0, 0.22))
        # -- waveform: played part in another colour ------------------------------------
        low, high = self._peaks(player, width)
        middle, half = (y0+y1)/2, height/2-4
        draw.add_line((x0, middle), (x1, middle), colour(0.25, 0.27, 0.3))
        playhead = player.position if player.path else 0.0
        head_x = to_x(playhead)
        played, ahead = colour(0.98, 0.62, 0.2), colour(0.36, 0.72, 0.95)
        count = len(low)
        if count:
            step = width/count
            for index in range(count):
                x = x0+(index+0.5)*step
                top, bottom = middle-float(high[index])*half, middle-float(low[index])*half
                if bottom-top < 1.0: bottom = top+1.0
                draw.add_line((x, top), (x, bottom), played if x <= head_x else ahead, max(1.0, step))
        if x0 <= head_x <= x1:
            draw.add_line((head_x, y0), (head_x, y1), colour(1, 1, 1), 1.5)
            draw.add_triangle_filled((head_x-5, y0), (head_x+5, y0), (head_x, y0+7), colour(1, 1, 1))
        # -- time ruler and readouts --------------------------------------------------------
        ticks = max(2, int(width//120))
        for index in range(ticks+1):
            t = start+span*index/ticks; x = to_x(t)
            draw.add_line((x, y1-6), (x, y1), colour(0.5, 0.5, 0.55))
            draw.add_text((min(x+3, x1-62), y1-18), colour(0.6, 0.62, 0.66), clock(t))
        draw.add_text((x0+6, y0+4), colour(0.95, 0.95, 0.95), clock(playhead)+' / '+clock(duration))
        if hovered: imgui.set_tooltip(clock(to_t(mouse.x)))
        return events
