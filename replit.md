# WhisperGuard

WhisperGuard is a local-first microphone monitoring prototype that detects ultrasonic, hidden, and AI-generated voice anomalies.

## Overview

This application provides:
- Local audio capture (browser-based and CLI)
- Rule-based ultrasonic detector + ML fusion stub
- Evidence packaging: WAV, spectrogram PNG, metadata JSON
- Web UI: upload, single-shot record, continuous 1s chunks, evidence list
- Modern cybersecurity-focused dark theme interface

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

The Flask web server runs on port 5000 at 0.0.0.0:
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
- React 18 (frontend)
- Bootstrap 5 (UI framework)

## Features

### File Scan
- Upload audio files for analysis
- Adjustable sensitivity slider (0-100%)
- Force save evidence toggle for testing
- Analyze, Reset buttons
- Audio file support via soundfile + ffmpeg conversion

### Continuous Capture
- Start/Stop listening with browser microphone access
- Real-time 1-second chunk analysis
- Continuous threat detection and logging

### Evidence Management
- Automatic evidence packaging on threat/suspicious detection
- Saved evidence accessible in sidebar with links to:
  - Audio files (WAV)
  - Spectrograms (PNG)
  - Metadata (JSON)
- Evidence list displays threat levels with color coding

### UI/UX
- Modern dark theme with cyan accents
- Responsive design for mobile/tablet
- Professional cybersecurity aesthetic
- Real-time status indicators
- Color-coded threat levels (green=safe, yellow=suspicious, red=threat)

## Recent Changes

- **December 27, 2025 (Latest)**:
  - Complete UI redesign with modern dark theme
  - Fixed Python f-string syntax compatibility issue
  - Improved CSS with gradients, animations, and hover effects
  - Enhanced button styling and form controls
  - Fixed "Start Continuous" button functionality
  - Removed duplicate script loading in HTML
  - Configured deployment for autoscale mode

## Hackathon Notes

Ready for demo:
- Click "Start Listening" to capture and analyze audio continuously
- Upload audio files using "Choose File" + "Analyze File"
- Check "Force save evidence" to test evidence saving
- Adjust sensitivity slider to tune detection thresholds
- View all saved evidence in the Evidence section with downloadable files

All buttons are now fully functional and responsive.
