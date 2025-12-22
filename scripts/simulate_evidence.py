import io
import json
import os
import sys
import numpy as np
import soundfile as sf

# ensure project root is on sys.path so `import whisperguard` works
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from whisperguard import web

print('Generating 1s 19kHz sine...')
sr = 44100
t = np.linspace(0, 1.0, sr, endpoint=False)
sig = (0.5 * np.sin(2 * np.pi * 19000 * t)).astype('float32')

buf = io.BytesIO()
sf.write(buf, sig, sr, format='WAV', subtype='PCM_16')
buf.seek(0)

c = web.app.test_client()
print('Posting to /analyze...')
data = {
    'audio': (buf, 'ultrasonic.wav'),
    'sensitivity': '0.5'
}
resp = c.post('/analyze', data=data, content_type='multipart/form-data')
print('Status:', resp.status_code)
try:
    print(json.dumps(resp.get_json(), indent=2))
except Exception:
    print('No JSON response')

print('\nQuerying /evidence/list...')
rl = c.get('/evidence/list')
print('Status:', rl.status_code)
print(json.dumps(rl.get_json(), indent=2))
