"""Lightweight CNN classifier interface (placeholder).

This module is a scaffold for model inference. Replace with a real
inference backend (ONNXRuntime / TorchScript) and trained weights.
"""
import numpy as np


class CNNSpectrogramClassifier:
    def __init__(self, model_path=None):
        self.model_path = model_path

    def predict(self, log_mel):
        """Return dict of class->confidence. This is a dummy predictor.

        Expected classes: Normal, Ultrasonic, Hidden, Deepfake
        """
        if log_mel is None:
            return {"Normal": 1.0, "Ultrasonic": 0.0, "Hidden": 0.0, "Deepfake": 0.0}
        # dummy: uniform small uncertainty
        scores = np.array([0.7, 0.1, 0.1, 0.1])
        scores = scores / scores.sum()
        return {"Normal": float(scores[0]), "Ultrasonic": float(scores[1]),
                "Hidden": float(scores[2]), "Deepfake": float(scores[3])}
