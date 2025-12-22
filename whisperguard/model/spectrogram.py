"""Spectrogram and feature conversion utilities."""

import numpy as np

try:
    import librosa
    _HAS_LIBROSA = True
except Exception:
    _HAS_LIBROSA = False


def waveform_to_log_mel(waveform, sr=44100, n_mels=64, n_fft=1024, hop_length=512):
    """Convert waveform to log-mel spectrogram.

    If `librosa` is unavailable, return None as a safe fallback (classifier is
    a placeholder and accepts None).
    """
    if waveform is None:
        return None
    if waveform.ndim > 1:
        waveform = np.mean(waveform, axis=1)

    if _HAS_LIBROSA:
        S = librosa.feature.melspectrogram(y=waveform.astype(float), sr=sr, n_fft=n_fft,
                                           hop_length=hop_length, n_mels=n_mels)
        log_S = librosa.power_to_db(S, ref=np.max)
        return log_S

    # Fallback: return None so downstream dummy classifier uses default behavior.
    return None
