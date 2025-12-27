# WhisperGuard

WhisperGuard is a local-first microphone monitoring prototype that detects ultrasonic, hidden, and AI-generated voice anomalies.

## Overview

This application provides:
- Local audio capture (browser-based)
- Rule-based ultrasonic detector + ML fusion stub
- Evidence packaging: WAV, spectrogram PNG, metadata JSON
- Web UI: upload, single-shot record, continuous 1s chunks, evidence list

## Project Structure

```
whisperguard/
├── audio/         - Audio capture utilities
├── detection/     - Ultrasonic detection logic
├── model/         - ML model and spectrogram utilities
├── static/        - Frontend assets (JS, CSS)
├── templates/     - HTML templates
├── evidence.py    - Evidence packaging
├── fusion.py      - Score fusion logic
├── logger.py      - Event logging
├── main.py        - CLI entry point
├── response.py    - Response/alert utilities
├── ui.py          - UI utilities
└── web.py         - Flask web server
scripts/           - Utility scripts
tests/             - Test files
```

## Running the Application

The Flask web server runs on port 5000:
```bash
python -m whisperguard.web
```

## Key Technologies

- Python 3.11
- Flask (web framework)
- NumPy, SciPy, librosa (audio processing)
- scikit-learn (ML)
- matplotlib (visualization)
- sounddevice, soundfile (audio I/O)

## Recent Changes

- December 27, 2025: Imported to Replit and configured for the environment
- Fixed f-string syntax compatibility issue in evidence.py
