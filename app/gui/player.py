"""Audio preview engine of the interface: PortAudio output stream fed from a decoded buffer.

The playhead is the frame counter of the audio callback itself, so the waveform cursor is
synchronised with what is actually heard, not with a UI timer. Decoding happens in a
background thread; selecting another file while one is loading cancels the older request.
No model is loaded here and nothing is written: files are opened read-only.
"""
import threading

import numpy as np

MAX_PREVIEW_SECONDS = 1800      # longer recordings are previewed from the requested position, by windows


class Player:
    def __init__(self):
        self.stream = None
        self.audio = np.zeros((0, 2), np.float32)   # [frames, channels] at self.rate
        self.rate = 0
        self.offset = 0.0           # time of audio[0] in the file, seconds (windowed preview of long files)
        self.frame = 0              # next frame to play, written by the audio callback
        self.playing = False
        self.loop = False
        self.volume = 1.0
        self.selection = None       # (start, stop) seconds in file time; loops inside it when loop is on
        self.path = None
        self.duration = 0.0
        self.error = ''
        self.loading = False
        self._lock = threading.Lock()
        self._request = 0

    # -- loading -------------------------------------------------------------
    def load(self, path, duration, autoplay=False, start=0.0):
        """Decode in the background; returns immediately. The newest request wins."""
        self._request += 1
        request = self._request
        self.stop(); self.path, self.duration, self.error, self.loading = str(path), float(duration or 0), '', True
        self.selection = None
        def work():
            try:
                from audiolib.audiofile import decode
                begin = 0.0
                stop = None
                if self.duration > MAX_PREVIEW_SECONDS:
                    begin = max(0.0, start-5.0); stop = begin+MAX_PREVIEW_SECONDS
                audio, rate = decode(path, start=begin, stop=stop)
                if audio.shape[1] > 2: audio = audio[:, :2]
                if request != self._request: return
                with self._lock:
                    self.audio, self.rate, self.offset = np.ascontiguousarray(audio), rate, begin
                    self.frame = max(0, int((start-begin)*rate))
                self.loading = False
                if autoplay: self.play()
            except Exception as exc:
                if request == self._request: self.error, self.loading = type(exc).__name__+': '+str(exc), False
        threading.Thread(target=work, daemon=True).start()

    # -- transport -----------------------------------------------------------
    def _callback(self, out, frames, time_info, status):
        with self._lock:
            audio, position = self.audio, self.frame
            low, high = 0, len(audio)
            if self.selection and self.loop:
                low = max(0, int((self.selection[0]-self.offset)*self.rate)); high = min(len(audio), int((self.selection[1]-self.offset)*self.rate))
                if position < low or position >= high: position = low
            written = 0
            while written < frames and self.playing:
                chunk = audio[position:min(high, position+frames-written)]
                if len(chunk):
                    block = chunk*self.volume
                    if block.shape[1] < out.shape[1]: block = np.repeat(block, out.shape[1], axis=1)
                    out[written:written+len(chunk)] = block[:, :out.shape[1]]
                    written += len(chunk); position += len(chunk)
                if position >= high:
                    if self.loop and high > low: position = low
                    else: self.playing = False
            out[written:] = 0
            self.frame = position

    def _open(self):
        import sounddevice
        channels = 2 if self.audio.shape[1] >= 2 else 1
        if self.stream is not None and (self.stream.samplerate != self.rate or self.stream.channels != channels): self._close()
        if self.stream is None:
            self.stream = sounddevice.OutputStream(samplerate=self.rate, channels=channels, dtype='float32', callback=self._callback, blocksize=0, latency='low')
            self.stream.start()

    def _close(self):
        if self.stream is not None:
            try: self.stream.stop(); self.stream.close()
            except Exception: pass
            self.stream = None

    def play(self):
        if not len(self.audio): return
        try:
            with self._lock:
                if self.frame >= len(self.audio): self.frame = 0
                self.playing = True
            self._open()
        except Exception as exc:
            self.playing = False; self.error = 'Audio output unavailable: '+str(exc)

    def pause(self): self.playing = False

    def toggle(self):
        if self.playing: self.pause()
        else: self.play()

    def stop(self):
        self.playing = False
        with self._lock: self.frame = 0

    def seek(self, seconds):
        if self.duration > MAX_PREVIEW_SECONDS and not (self.offset <= seconds < self.offset+len(self.audio)/max(1, self.rate)):
            self.load(self.path, self.duration, autoplay=self.playing, start=seconds); return
        with self._lock: self.frame = int(np.clip((seconds-self.offset)*self.rate, 0, max(0, len(self.audio)-1)))

    @property
    def position(self):
        """Playhead in file time, seconds."""
        return self.offset+(self.frame/self.rate if self.rate else 0.0)

    def samples(self, start, stop):
        """Decoded samples of a time range (mono envelope source for sample-level zoom), or None when outside the buffer."""
        if not self.rate: return None
        a, b = int((start-self.offset)*self.rate), int((stop-self.offset)*self.rate)
        if a < 0 or b > len(self.audio) or b <= a: return None
        return self.audio[a:b]

    def close(self):
        self._request += 1; self.playing = False; self._close()
