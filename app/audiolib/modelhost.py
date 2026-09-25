"""Persistent model host: the owner of the engine worker process.

CyToolsCore ships one-shot ProcessWorker; a search must not reload a model for every query,
so this Tool keeps one worker process per engine environment alive between jobs. It plugs
into the Core through Runtime.register_worker (same state/release/health contract), which
means Runtime.close() and cy_release_resources stop it, and no second scheduler exists:
every request still comes from a job handler running under the Core scheduler.

Cancellation is real: a cancelled request kills the worker process and the handler only
returns once the process is gone, so reservations are released after the actual stop.
"""
import json
import os
import queue
import subprocess
import threading
import time
import uuid

import psutil

from config import APP, ENGINE_SOURCES, LOGS, device_for, engine_python, runtime_python, settings
from cytools_core import CyToolError


class ModelHost:
    def __init__(self, engine='torch'):
        self.engine = engine
        self.process, self.state = None, 'Stopped'
        self.loaded = {}                 # modelKey -> {'device', 'vramBytes'}
        self.last_used = time.monotonic()
        self.last_response = None
        self._lock = threading.RLock()   # one request at a time per worker
        self._responses = queue.Queue()
        self._events = []
        self._log = None
        self._stopper = None
        self.on_change = None            # callback(host) after load/unload/stop, used for ledger reservations

    # -- Core worker contract -------------------------------------------------
    def release(self, level):
        if level in ('Worker', 'All'): self.stop()
        elif level == 'Model': self.unload()
        elif level not in ('Temporary', 'Job'): raise CyToolError('InvalidParameters', 'Unknown release level')

    def health(self):
        alive = bool(self.process and self.process.poll() is None)
        return {'state': self.state, 'pid': self.process.pid if alive else None, 'alive': alive, 'engine': self.engine,
                'loadedModels': dict(self.loaded), 'lastResponseMonotonic': self.last_response, 'heartbeatSupported': False}

    # -- lifecycle ----------------------------------------------------------
    def interpreter(self):
        python = runtime_python() if self.engine == 'base' else engine_python(self.engine)
        if not python:
            raise CyToolError('MissingDependency', f"The AI engine '{self.engine}' is not installed", recoverable=True,
                              suggested_action='Open the Installation tab and install the AI engine, or run app/setup_backend.py')
        return python

    def start(self):
        with self._lock:
            if self.process and self.process.poll() is None: return
            python = self.interpreter()
            LOGS.mkdir(parents=True, exist_ok=True)
            self._log = (LOGS/f'model-worker-{self.engine}.log').open('a', encoding='utf-8', errors='replace')
            self._log.write(f'\n--- worker start {time.strftime("%Y-%m-%d %H:%M:%S")} ---\n'); self._log.flush()
            environment = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
            self.state = 'Starting'
            try:
                self.process = subprocess.Popen([python, str(APP/'worker.py')], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=self._log, text=True, encoding='utf-8', cwd=str(APP), env=environment,
                    creationflags=0x08000000 if os.name == 'nt' else 0)
            except OSError as exc:
                self.state = 'Failed'; raise CyToolError('MissingRuntime', str(exc)) from exc
            self._responses = queue.Queue()
            threading.Thread(target=self._read, args=(self.process, self._responses), daemon=True).start()
            ready = self._wait(None, None, 120)
            if ready.get('event') != 'ready':
                self.stop(); raise CyToolError('WorkerCrashed', 'Engine worker did not start; see data/logs/model-worker-%s.log' % self.engine)
            self.state = 'Idle'
            if self._stopper is None:
                self._stopper = threading.Thread(target=self._idle_watch, daemon=True); self._stopper.start()

    @staticmethod
    def _read(process, responses):
        for line in process.stdout:
            try: responses.put(json.loads(line))
            except ValueError: continue
        responses.put({'event': 'closed'})

    def _wait(self, request_id, cancelled, timeout, progress=None):
        deadline = time.monotonic()+timeout if timeout else None
        while True:
            if cancelled and cancelled():
                self.stop(); raise CyToolError('Cancelled', 'Cancelled; the engine worker was stopped')
            if deadline and time.monotonic() > deadline:
                self.stop(); raise CyToolError('Timeout', 'Engine worker did not answer in time; it was stopped')
            try: message = self._responses.get(timeout=0.1)
            except queue.Empty: continue
            self.last_response = time.monotonic()
            if message.get('event') == 'closed':
                code = self.process.poll() if self.process else None
                self.stop()
                raise CyToolError('WorkerCrashed', f'Engine worker exited (code {code}); see data/logs/model-worker-{self.engine}.log', recoverable=True)
            if message.get('event') == 'progress':
                if progress: progress(message)
                continue
            if request_id is None or message.get('id') == request_id: return message

    def request(self, op, payload=None, cancelled=None, timeout=1800, progress=None):
        with self._lock:
            self.start()
            request_id = uuid.uuid4().hex
            self.state = 'Busy'
            try:
                self.process.stdin.write(json.dumps({'id': request_id, 'op': op, **(payload or {})})+'\n'); self.process.stdin.flush()
            except OSError as exc:
                self.stop(); raise CyToolError('WorkerCrashed', 'Engine worker is not reachable: '+str(exc), recoverable=True) from exc
            try: response = self._wait(request_id, cancelled, timeout, progress)
            finally:
                self.last_used = time.monotonic()
                if self.state == 'Busy': self.state = 'Idle'
            if not response.get('ok'):
                raise CyToolError(response.get('code') or 'EngineError', response.get('message', 'Engine error'),
                                  recoverable=response.get('code') == 'InsufficientVRAM')
            return response

    def stop(self):
        """Terminate the worker and its descendants; returns only when the process is gone."""
        with self._lock:
            process, self.process = self.process, None
            if process is not None:
                self.state = 'Stopping'
                try:
                    parent = psutil.Process(process.pid); family = parent.children(recursive=True)+[parent]
                except psutil.NoSuchProcess: family = []
                try:
                    if process.poll() is None and process.stdin: process.stdin.close()
                    process.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired): pass
                for member in family:
                    try: member.terminate()
                    except psutil.NoSuchProcess: pass
                _, alive = psutil.wait_procs(family, timeout=5)
                for member in alive:
                    try: member.kill()
                    except psutil.NoSuchProcess: pass
                psutil.wait_procs(alive, timeout=10)
                try: process.wait(timeout=10)      # reap: the job may only report Cancelled once the process is gone
                except (OSError, subprocess.TimeoutExpired): pass
                for stream in (process.stdout,):
                    try: stream.close()
                    except OSError: pass
            if self._log:
                try: self._log.close()
                except OSError: pass
                self._log = None
            self.loaded.clear(); self.state = 'Stopped'
        if self.on_change: self.on_change(self)

    def _idle_watch(self):
        while True:
            time.sleep(5)
            limit = settings()['idleUnloadSeconds']
            if limit and self.process is not None and self.state == 'Idle' and time.monotonic()-self.last_used > limit:
                if self._lock.acquire(blocking=False):
                    try:
                        if self.state == 'Idle' and time.monotonic()-self.last_used > limit: self.stop()
                    finally: self._lock.release()

    # -- capabilities -------------------------------------------------------
    def load(self, descriptor, device=None, cancelled=None):
        if descriptor.key in self.loaded and self.process and self.process.poll() is None:
            wanted = device_for(descriptor.key, device)
            if wanted == 'auto' or (wanted == 'cpu') == (self.loaded[descriptor.key]['device'] == 'cpu'): return self.loaded[descriptor.key]
            self.unload(descriptor.key)
        if not descriptor.get('adapter'):
            raise CyToolError('NotImplemented', descriptor['displayName']+' is declared in the registry but has no adapter in this version')
        if not descriptor.installed:
            raise CyToolError('ModelNotInstalled', descriptor['displayName']+' is not installed', recoverable=True,
                              suggested_action='Install it from the Installation tab or with: python app/download_model.py --model '+descriptor.key)
        response = self.request('load', {'modelKey': descriptor.key, 'descriptor': descriptor.data, 'modelDir': str(descriptor.install_dir),
                                         'sources': str(ENGINE_SOURCES), 'device': device_for(descriptor.key, device)}, cancelled, timeout=1800)
        self.loaded[descriptor.key] = {'device': response['device'], 'vramBytes': response.get('vramBytes', 0)}
        if self.on_change: self.on_change(self)
        return self.loaded[descriptor.key]

    def unload(self, model_key=None):
        if self.process is None: return
        self.request('unload', {'modelKey': model_key} if model_key else {}, timeout=120)
        if model_key: self.loaded.pop(model_key, None)
        else: self.loaded.clear()
        if self.on_change: self.on_change(self)

    def embed_text(self, descriptor, texts, device=None, cancelled=None):
        import numpy as np
        self.load(descriptor, device, cancelled)
        response = self.request('embed_text', {'modelKey': descriptor.key, 'texts': list(texts)}, cancelled, timeout=600)
        return np.asarray(response['vectors'], dtype=np.float32)

    def embed_selection(self, descriptor, path, start, stop, device=None, cancelled=None):
        import numpy as np
        self.load(descriptor, device, cancelled)
        response = self.request('embed_wave', {'modelKey': descriptor.key, 'path': str(path), 'start': float(start), 'stop': float(stop)}, cancelled, timeout=600)
        return np.asarray(response['vectors'], dtype=np.float32)

    def embed_audio(self, descriptor, items, output, device=None, cancelled=None):
        self.load(descriptor, device, cancelled)
        return self.request('embed_audio', {'modelKey': descriptor.key, 'items': items, 'output': str(output)}, cancelled, timeout=3600)['results']

    def generate(self, descriptor, messages, max_new_tokens=512, device=None, cancelled=None):
        self.load(descriptor, device, cancelled)
        return self.request('generate', {'modelKey': descriptor.key, 'messages': messages, 'maxNewTokens': max_new_tokens}, cancelled, timeout=600)['text']


class HostPool:
    """One ModelHost per engine environment, registered once with the Core runtime."""
    def __init__(self, runtime=None):
        self.runtime, self.hosts = runtime, {}
        self._lock = threading.Lock()

    def host(self, descriptor):
        engine = descriptor.get('engine') or 'torch'
        with self._lock:
            if engine not in self.hosts:
                host = ModelHost(engine); self.hosts[engine] = host
                if self.runtime is not None:
                    self.runtime.register_worker('modelhost-'+engine, host)
                    host.on_change = self._account
            return self.hosts[engine]

    def _account(self, host):
        """Mirror resident VRAM in the Core ledger so that CanRun of other jobs sees loaded models."""
        owner = 'worker:modelhost-'+host.engine
        try:
            self.runtime.ledger.release(owner)
            resident = sum(v.get('vramBytes', 0) for v in host.loaded.values() if v.get('device') == 'cuda')
            if resident: self.runtime.ledger.reserve(owner, {'vramBytes': {'auto': int(resident)}})
        except Exception: pass

    def status(self):
        out = {}
        for engine, host in self.hosts.items():
            out[engine] = host.health()
            if out[engine]['alive'] and host.state == 'Idle':      # measured figures from the worker itself (peak VRAM, device)
                try: out[engine]['measured'] = {k: v for k, v in host.request('status', timeout=30).items() if k not in ('id', 'ok')}
                except CyToolError: pass
        return out

    def stop(self):
        for host in list(self.hosts.values()): host.stop()
