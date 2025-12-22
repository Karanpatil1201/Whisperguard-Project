# WhisperGuard

WhisperGuard is a local-first microphone monitoring prototype that detects ultrasonic, hidden,
and AI-generated voice anomalies. It provides a CLI pipeline and a web demo (browser recording,
continuous streaming, evidence packaging) for quick demonstration and evaluation.

Key features
- Local audio capture (CLI + browser)
- Rule-based ultrasonic detector + ML fusion stub
- Evidence packaging: WAV, spectrogram PNG, metadata JSON
- Web UI: upload, single-shot record, continuous 1s chunks, evidence list

Requirements
- Python 3.8+ (tested in virtualenv)
- See `requirements.txt` for Python package dependencies

Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m whisperguard.web
# open http://localhost:5000 in your browser
```

CLI quick test

```powershell
python -m whisperguard.main --duration 5
```

Testing synthetic ultrasonic audio

```powershell
python scripts/simulate_evidence.py
curl http://localhost:5000/evidence/list
```

Demo script (what to show judges)
- Start `python -m whisperguard.web`, open the UI.
- Click `Start Continuous` (allow microphone); show "Last Sent Waveform" updating.
- Enable `Force save evidence` if your mic can't capture ultrasonics; show evidence saved under `static/evidence/`.
- Show saved WAV + spectrogram and the metadata JSON.

Limitations & talking points
- The ML model is a placeholder; replace `whisperguard/model/cnn.py` with a trained model (ONNX recommended) for production.
- Ultrasonic detection depends on microphone hardware and browser resampling; many laptop mics cannot capture >18 kHz reliably.
- Evidence is saved locally; for tamper-resistance sign metadata or integrate secure upload.

Files of interest
- `whisperguard/web.py` — Flask server + endpoints
- `whisperguard/static/app_react.js` — browser UI code
- `whisperguard/detection/ultrasonic.py` — FFT-based rule
- `whisperguard/evidence.py` — evidence packaging
- `scripts/simulate_evidence.py` — generates/test ultrasonic event

License / Notes
- This prototype is for demonstration; remove `whisperguard/static/evidence/` from `.gitignore` only if you intentionally want to track recorded evidence.


