"""Evidence packaging utilities: save WAV, spectrogram PNG, and metadata JSON.

Saved under `whisperguard/static/evidence/<timestamp>/` so files can be served
by the Flask static server during demos.
"""
import os
import time
import json
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def save_spectrogram(waveform, sr, out_path):
    plt.figure(figsize=(6, 3))
    # use matplotlib.specgram for a dependency-light spectrogram
    Pxx, freqs, bins, im = plt.specgram(waveform, NFFT=1024, Fs=sr, noverlap=512, cmap='magma')
    plt.ylim(0, sr/2)
    plt.xlabel('Time')
    plt.ylabel('Frequency (Hz)')
    plt.colorbar(label='Intensity (dB)')
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def save_evidence(waveform, sr, ml_scores, rule_ratio, level, score, base_dir=None):
    """Save evidence artifacts and return paths.

    waveform: 1-D numpy array
    sr: sample rate
    ml_scores: dict
    rule_ratio: float
    level: str
    score: float
    base_dir: optional base dir for saving (defaults to whisperguard/static/evidence)
    """
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), 'static', 'evidence')
    ts = int(time.time())
    folder = os.path.join(base_dir, f'event_{ts}')
    _ensure_dir(folder)

    wav_path = os.path.join(folder, 'audio.wav')
    sf.write(wav_path, waveform, sr)

    png_path = os.path.join(folder, 'spectrogram.png')
    try:
        save_spectrogram(waveform, sr, png_path)
    except Exception:
        # fallback: save a simple waveform plot
        plt.figure(figsize=(6, 2))
        t = np.arange(len(waveform)) / float(sr)
        plt.plot(t, waveform)
        plt.xlabel('Time (s)')
        plt.tight_layout()
        plt.savefig(png_path, dpi=150)
        plt.close()

    fingerprint = sha256_file(wav_path)

    meta = {
        'ts': ts,
        'level': level,
        'score': float(score),
        'rule_ratio': float(rule_ratio),
        'ml_scores': ml_scores,
        'fingerprint': fingerprint,
    }
    meta_path = os.path.join(folder, 'metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    # Return paths relative to static so Flask can serve them
    rel_base = os.path.relpath(folder, os.path.join(os.path.dirname(__file__), 'static'))
    rel_base_normalized = rel_base.replace('\\', '/')
    return {
        'folder': rel_base_normalized,
        'audio': f'{rel_base_normalized}/audio.wav',
        'spectrogram': f'{rel_base_normalized}/spectrogram.png',
        'metadata': f'{rel_base_normalized}/metadata.json',
    }
