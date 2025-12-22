"""Simple audio capture and preprocessing placeholder.

This module provides a lightweight API to capture microphone audio in
1-second chunks and perform basic normalization. It's a scaffold —
replace or extend with more advanced filtering and buffering later.
"""
import queue
import time
import numpy as np
import sounddevice as sd


class AudioCapture:
    def __init__(self, samplerate=44100, channels=1, chunk_seconds=1):
        self.samplerate = samplerate
        self.channels = channels
        self.chunk_seconds = chunk_seconds
        self.chunk_size = int(samplerate * chunk_seconds)
        self._q = queue.Queue()

    def _callback(self, indata, frames, time_info, status):
        if status:
            print("Audio status:", status)
        self._q.put(indata.copy())

    def start_stream(self):
        self.stream = sd.InputStream(samplerate=self.samplerate,
                                     channels=self.channels,
                                     callback=self._callback)
        self.stream.start()

    def stop_stream(self):
        if hasattr(self, "stream"):
            self.stream.stop()
            self.stream.close()

    def read_chunk(self, timeout=2.0):
        frames = []
        needed = self.chunk_size
        start = time.time()
        while needed > 0:
            try:
                data = self._q.get(timeout=timeout)
            except queue.Empty:
                break
            frames.append(data)
            needed -= len(data)
            if time.time() - start > timeout:
                break
        if not frames:
            return None
        arr = np.concatenate(frames, axis=0)
        arr = arr[: self.chunk_size]
        # simple normalization
        maxv = np.max(np.abs(arr))
        if maxv > 0:
            arr = arr / maxv
        return arr

    def capture_for_seconds(self, seconds=5):
        self.start_stream()
        try:
            t_end = time.time() + seconds
            while time.time() < t_end:
                chunk = self.read_chunk()
                if chunk is None:
                    print("No audio captured for chunk")
                else:
                    print(f"Captured chunk shape={chunk.shape}")
        finally:
            self.stop_stream()
