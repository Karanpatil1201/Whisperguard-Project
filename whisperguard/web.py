"""Flask web interface for WhisperGuard audio analysis.

Endpoints:
- /            : web UI (upload or record)
- /analyze     : POST audio file blob, returns JSON analysis

This is a lightweight demo server to test detection from a browser.
"""
from flask import Flask, render_template, request, jsonify
import tempfile
import os
import time
import subprocess
import soundfile as sf
import logging

# configure module logger
logger = logging.getLogger('whisperguard.web')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

from whisperguard.detection.ultrasonic import detect_ultrasonic
from whisperguard.model.spectrogram import waveform_to_log_mel
from whisperguard.model.cnn import CNNSpectrogramClassifier
from whisperguard.fusion import fuse_scores
from whisperguard.logger import EventLogger
from whisperguard.evidence import save_evidence


app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"), static_folder=os.path.join(os.path.dirname(__file__), "static"))

# ensure evidence directory exists and is writable
EVIDENCE_STATIC = os.path.join(os.path.dirname(__file__), 'static', 'evidence')
try:
    os.makedirs(EVIDENCE_STATIC, exist_ok=True)
    logger.debug(f"Evidence static dir: {EVIDENCE_STATIC}")
except Exception as e:
    logger.exception("Could not create evidence dir")

classifier = CNNSpectrogramClassifier()
event_logger = EventLogger()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    if request.method == 'GET':
        return jsonify({
            "message": "POST audio file to this endpoint using multipart/form-data with key 'audio'",
            "methods": ["POST"],
            "note": "Use curl: curl -F \"audio=@file.wav\" http://<host>:5000/analyze"
        })
    debug_msgs = []
    def add_debug(m):
        debug_msgs.append(m)
        logger.debug(m)

    add_debug('Analyze called')
    add_debug(f'Form keys: {list(request.form.keys())}  Files: {list(request.files.keys())}')

    f = request.files.get("audio")
    if not f:
        add_debug('No audio file in request')
        return jsonify({"error": "no file uploaded", "debug": debug_msgs}), 400

    tmp_in = None
    tmp_out = None
    in_path = None
    try:
        tmp_in = tempfile.NamedTemporaryFile(delete=False)
        filename = getattr(f, 'filename', '') or 'upload'
        ext = os.path.splitext(filename)[1]
        if not ext:
            in_path = tmp_in.name + '.bin'
        else:
            in_path = tmp_in.name + ext
        add_debug(f'Writing upload to: {in_path}')
        with open(in_path, 'wb') as w:
            f.stream.seek(0)
            data_bytes = f.read()
            w.write(data_bytes)
        add_debug(f'Wrote {len(data_bytes)} bytes')

        # Try reading directly with soundfile first
        try:
            data, sr = sf.read(in_path, dtype="float32")
            add_debug(f'soundfile read success sr={sr} len={len(data)}')
        except Exception:
            add_debug('soundfile failed to read uploaded file, attempting ffmpeg conversion')
            tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            out_path = tmp_out.name
            cmd = ['ffmpeg', '-y', '-i', in_path, '-ar', '44100', '-ac', '1', out_path]
            try:
                add_debug(f'Running ffmpeg: {cmd}')
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                add_debug(f'ffmpeg returncode={res.returncode}')
            except FileNotFoundError:
                add_debug('ffmpeg not found')
                return jsonify({"error": "ffmpeg not found on server. Install ffmpeg or upload WAV files.", "debug": debug_msgs}), 400
            except Exception as e:
                add_debug(f'ffmpeg conversion failed: {e}')
                return jsonify({"error": f"ffmpeg conversion failed: {e}", "debug": debug_msgs}), 500

            if res.returncode != 0:
                add_debug(f'ffmpeg stderr: {res.stderr}')
                return jsonify({"error": "ffmpeg conversion failed", "stderr": res.stderr, "debug": debug_msgs}), 500

            try:
                data, sr = sf.read(out_path, dtype="float32")
                add_debug(f'read converted wav sr={sr} len={len(data)}')
            except Exception as e:
                add_debug(f'could not read converted audio: {e}')
                return jsonify({"error": "could not read converted audio", "details": str(e), "debug": debug_msgs}), 500
    finally:
        try:
            if tmp_in is not None:
                tmp_in.close()
        except Exception:
            pass
        try:
            if in_path and os.path.exists(in_path):
                os.unlink(in_path)
        except Exception:
            pass
        try:
            if tmp_out is not None:
                tmp_out.close()
                if os.path.exists(tmp_out.name):
                    os.unlink(tmp_out.name)
        except Exception:
            pass

    if data is None or len(data) == 0:
        add_debug('No audio data after read')
        return jsonify({"error": "could not read audio", "debug": debug_msgs}), 400

    if data.ndim > 1:
        waveform = data.mean(axis=1)
    else:
        waveform = data

    rule_ratio, rule_flag = detect_ultrasonic(waveform, sr)
    log_mel = waveform_to_log_mel(waveform, sr=sr)
    ml_scores = classifier.predict(log_mel, waveform=waveform, sr=sr)
    sensitivity = float(request.form.get("sensitivity", 0.5))
    level, score = fuse_scores(rule_ratio, ml_scores, sensitivity=sensitivity, whitelist=False)

    # support a test-only override to force saving evidence for debugging
    force_save = str(request.form.get('force_save', '')).lower() in ('1', 'true', 'yes')

    evidence = None
    # Save evidence when suspicious OR when force_save flag present (debug/testing)
    if level in ("THREAT", "SUSPICIOUS") or force_save:
        ev = {"ts": time.time(), "level": level, "score": float(score)}
        if force_save:
            ev['note'] = 'force_saved'
            add_debug('force_save enabled: saving evidence regardless of fused level')
        event_logger.append(ev)
        try:
            evidence = save_evidence(waveform, sr, ml_scores, rule_ratio, level, score)
            add_debug(f'Evidence saved: {evidence}')
        except Exception as e:
            add_debug(f'Failed saving evidence: {e}')
            evidence = {"error": str(e)}

    resp = {
        "rule_ratio": float(rule_ratio),
        "ml_scores": ml_scores,
        "level": level,
        "score": float(score),
        "events": event_logger.list(),
    }
    if evidence is not None:
        resp['evidence'] = evidence
    resp['debug'] = debug_msgs
    return jsonify(resp)


@app.route('/evidence/list', methods=['GET'])
def list_evidence():
    """Return a JSON list of saved evidence event folders and metadata."""
    items = []
    try:
        if not os.path.exists(EVIDENCE_STATIC):
            return jsonify({'events': [], 'note': 'evidence dir does not exist'}), 200

        for name in sorted(os.listdir(EVIDENCE_STATIC)):
            entry = os.path.join(EVIDENCE_STATIC, name)
            if not os.path.isdir(entry):
                continue
            meta = None
            meta_path = os.path.join(entry, 'metadata.json')
            try:
                if os.path.exists(meta_path):
                    import json
                    with open(meta_path, 'r', encoding='utf-8') as mf:
                        meta = json.load(mf)
            except Exception:
                meta = {'error': 'could not read metadata'}

            files = []
            try:
                for f in sorted(os.listdir(entry)):
                    files.append(f)
            except Exception:
                files = []

            items.append({'name': name, 'metadata': meta, 'files': files})
    except Exception as e:
        logger.exception('listing evidence failed')
        return jsonify({'error': str(e)}), 500

    return jsonify({'events': items}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
