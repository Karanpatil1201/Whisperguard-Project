"""Rule-based ultrasonic detection utilities."""

import numpy as np


def detect_ultrasonic(audio_chunk, samplerate, threshold=0.1, min_freq=18000):
    """Return energy ratio above min_freq and boolean flag using NumPy FFT.

    audio_chunk: 1-D numpy array
    samplerate: int
    threshold: fraction of total energy
    """
    if audio_chunk is None or len(audio_chunk) == 0:
        return 0.0, False
    n = len(audio_chunk)
    # Use real FFT for efficiency
    yf = np.abs(np.fft.rfft(audio_chunk))
    freqs = np.fft.rfftfreq(n, d=1.0 / samplerate)
    high_idx = freqs >= min_freq
    high_energy = np.sum(yf[high_idx] ** 2)
    total_energy = np.sum(yf ** 2) + 1e-12
    ratio = high_energy / total_energy
    return ratio, ratio >= threshold
