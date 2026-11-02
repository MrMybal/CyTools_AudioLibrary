"""Interactive waveform: cached peak pyramid, real-time playhead, zoom, pan, seek, selection.

Drawing reads at most one (min, max) pair per pixel column from the pyramid level that fits
the zoom, so a one hour file costs the same as a short one. Below the finest level the
decoded samples of the player are used (sample-level detail). Interaction:
  wheel = zoom around the cursor, Shift+wheel or middle-drag = pan, click = seek,
  drag = selection, double-click = clear selection.
"""
import numpy as np
from imgui_bundle import imgui

import ui_style as cy
from cyui_modules.audioviews import WaveformState, waveform
from cyui_modules.common import Range
from audiolib.waveform import BASE, Pyramid


def clock(seconds):
    seconds = max(0.0, float(seconds))
    return '%02d:%06.3f' % (int(seconds//60), seconds % 60)


class WaveformView:
    def __init__(self):
        self.state = WaveformState()
        self._pending_seek = None
        self._selection_before = None
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
        """Host decoding/cache + the shared waveform, without moving playback on a drag."""
        events={}
        if self.pyramid is None:
            cy.empty_state(tr('Waveform not available yet: scan the Library'))
            return events
        width=max(cy.dp(64),imgui.get_content_region_avail().x)
        origin=imgui.get_cursor_screen_pos()
        duration=self.pyramid.duration
        coverage=Range(*self.view)
        low,high=self._peaks(player,width)
        self.state.view=coverage
        if not self.state.selecting:
            self.state.selection=Range(*(player.selection or (0.,0.)))
        was_selecting=self.state.selecting
        result=waveform('##waveform',self.state,[list(zip(low,high))],coverage,
                        player.position if player.path else 0.,(width,height))
        io=imgui.get_io()
        hovered=imgui.is_item_hovered()
        if result['seek'] is not None:
            self._pending_seek=max(0.,min(duration,result['seek']))
            self._selection_before=player.selection
        if self.state.selecting or was_selecting:
            a,b=self.state.selection.minimum,self.state.selection.maximum
            dragged=abs(b-a)/max(1e-9,self.state.view.span)*width>=cy.dp(4)
            if dragged:
                player.selection=(max(0.,min(duration,a)),max(0.,min(duration,b)))
            if not self.state.selecting:
                if dragged: events['selection']=player.selection
                elif self._pending_seek is not None:
                    events['seek']=self._pending_seek
                    player.selection=self._selection_before
                self._pending_seek=None
        if hovered and imgui.is_mouse_double_clicked(0):
            self.state.selection=Range(0,0)
            player.selection=None;events['selection']=None;self._pending_seek=None
        # Keep the host's finite file bounds and sample-detail lower limit.
        span=min(duration,max(64/self.pyramid.sample_rate,self.state.view.span))
        start=max(0.,min(duration-span,self.state.view.minimum))
        self.view=(start,start+max(1e-9,span))
        # Search-result marker and timecode are application metadata overlays.
        draw=imgui.get_window_draw_list();p=cy.palette()
        x=lambda t:origin.x+(t-self.state.view.minimum)/self.state.view.span*width
        draw.push_clip_rect(origin,(origin.x+width,origin.y+height),True)
        if self.marker:
            draw.add_rect_filled((x(self.marker[0]),origin.y),(x(self.marker[1]),origin.y+height),cy.alpha(p.warning,.16))
        draw.add_text((origin.x+cy.dp(6),origin.y+cy.dp(4)),p.text,clock(player.position if player.path else 0.)+' / '+clock(duration))
        ticks=max(2,int(width//cy.dp(120)))
        label_size=imgui.calc_text_size('00:00.000')
        for index in range(ticks+1):
            time=self.state.view.minimum+self.state.view.span*index/ticks
            pixel=x(time)
            draw.add_line((pixel,origin.y+height-cy.dp(6)),(pixel,origin.y+height),p.lineStrong)
            draw.add_text((min(pixel+cy.dp(3),origin.x+width-label_size.x-cy.dp(4)),origin.y+height-label_size.y-cy.dp(4)),p.textFaint,clock(time))
        draw.pop_clip_rect()
        if hovered:cy.tooltip(clock(self.state.view.minimum+(io.mouse_pos.x-origin.x)/width*self.state.view.span))
        return events
