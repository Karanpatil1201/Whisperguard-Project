"""Lightweight CNN classifier interface (placeholder).

This module is a scaffold for model inference. Replace with a real
inference backend (ONNXRuntime / TorchScript) and trained weights.
"""
import numpy as np


class CNNSpectrogramClassifier:
    def __init__(self, model_path=None):
        self.model_path = model_path

    def predict(self, log_mel, waveform=None, sr=44100):
        """Heuristic predictor returning interpretable, variable confidences.

        This is still a placeholder but derives scores from the provided
        `log_mel` when available, otherwise falls back to simple FFT
        statistics computed from `waveform`.

        Returns a dict with keys: Normal, Ultrasonic, Hidden, Deepfake
        """
        # Defaults
        normal = 0.6
        ultrasonic = 0.0
        hidden = 0.0
        deepfake = 0.0

        if log_mel is not None:
            # log_mel expected shape (n_mels, t) or (t, n_mels)
            arr = np.array(log_mel)
            if arr.ndim == 2:
                # ensure shape (n_mels, t)
                if arr.shape[0] < arr.shape[1]:
                    pass
                # energy per mel bin
                energies = np.mean(np.maximum(arr, -80.0), axis=1)  # dB-like
                # normalize to 0..1
                e_min, e_max = energies.min(), energies.max()
                if e_max - e_min > 1e-6:
                    norm = (energies - e_min) / (e_max - e_min)
                else:
                    norm = energies * 0.0

                n = len(norm)
                high_idx = np.arange(int(n * 0.75), n)
                mid_idx = np.arange(int(n * 0.3), int(n * 0.75))
                high_energy = float(np.mean(norm[high_idx])) if high_idx.size else 0.0
                mid_energy = float(np.mean(norm[mid_idx])) if mid_idx.size else 0.0

                ultrasonic = min(1.0, high_energy * 1.6)
                hidden = min(1.0, mid_energy * 1.2 * (1.0 - ultrasonic))
                # deepfake heuristic: low variance across time -> synthetic
                time_var = float(np.mean(np.var(arr, axis=1)))
                # normalize time variance to a 0..1-like scale then invert
                denom = (abs(arr).mean() + 1e-6)
                df_score = (1.0 - (time_var / denom)) * 0.8
                deepfake = float(np.clip(df_score, 0.0, 1.0))
                normal = max(0.0, 1.0 - (ultrasonic + hidden + deepfake) * 0.9)
        elif waveform is not None:
            x = np.asarray(waveform, dtype=float)
            if x.size == 0:
                return {"Normal": 1.0, "Ultrasonic": 0.0, "Hidden": 0.0, "Deepfake": 0.0}
            # FFT-based fallback
            n = len(x)
            yf = np.abs(np.fft.rfft(x * np.hanning(n)))
            freqs = np.fft.rfftfreq(n, d=1.0 / sr)
            high_mask = freqs >= 18000
            mid_mask = (freqs >= 300) & (freqs < 18000)
            high_energy = float(np.sum(yf[high_mask] ** 2))
            mid_energy = float(np.sum(yf[mid_mask] ** 2))
            total_energy = float(np.sum(yf ** 2)) + 1e-12
            high_ratio = high_energy / total_energy
            mid_ratio = mid_energy / total_energy
            ultrasonic = min(1.0, high_ratio * 10.0)
            hidden = min(1.0, mid_ratio * 2.0 * (1.0 - ultrasonic))
            # deepfake: overly smooth waveform (low variance)
            var = float(np.var(x))
            deepfake = 0.0 if var > 1e-6 else 0.0
            normal = max(0.0, 1.0 - (ultrasonic + hidden + deepfake))

        # assemble and normalize
        scores = np.array([normal, ultrasonic, hidden, deepfake], dtype=float)
        # ensure non-negative
        scores = np.clip(scores, 0.0, None)
        if scores.sum() <= 0:
            scores = np.array([1.0, 0.0, 0.0, 0.0])
        else:
            scores = scores / float(scores.sum())

        return {
            "Normal": float(scores[0]),
            "Ultrasonic": float(scores[1]),
            "Hidden": float(scores[2]),
            "Deepfake": float(scores[3]),
        }
