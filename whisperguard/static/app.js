// Minimal client-side recorder + uploader
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const recBtn = document.getElementById('recBtn');
const stopBtn = document.getElementById('stopBtn');
const sensitivityEl = document.getElementById('sensitivity');

let mediaRecorder;
let recordedChunks = [];

uploadBtn.onclick = async () => {
  const file = fileInput.files[0];
  if (!file) { statusEl.innerText = 'Select a file first'; return; }
  statusEl.innerText = 'Uploading...';
  const fd = new FormData();
  fd.append('audio', file);
  fd.append('sensitivity', sensitivityEl.value);
  const r = await fetch('/analyze', { method: 'POST', body: fd });
  const j = await r.json();
  resultEl.innerText = JSON.stringify(j, null, 2);
  statusEl.innerText = 'Done';
};

recBtn.onclick = async () => {
  recordedChunks = [];
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      const blob = new Blob(recordedChunks, { type: 'audio/webm' });
      // Convert webm to wav on server side; just send blob
      const fd = new FormData();
      fd.append('audio', blob, 'recording.webm');
      fd.append('sensitivity', sensitivityEl.value);
      statusEl.innerText = 'Sending recording...';
      const r = await fetch('/analyze', { method: 'POST', body: fd });
      const j = await r.json();
      resultEl.innerText = JSON.stringify(j, null, 2);
      statusEl.innerText = 'Done';
    };
    mediaRecorder.start();
    recBtn.disabled = true;
    stopBtn.disabled = false;
    statusEl.innerText = 'Recording...';
  } catch (e) {
    statusEl.innerText = 'Error starting microphone: ' + e;
  }
};

stopBtn.onclick = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    recBtn.disabled = false;
    stopBtn.disabled = true;
  }
};
