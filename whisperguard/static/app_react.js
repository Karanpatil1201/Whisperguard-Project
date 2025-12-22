const { useState, useRef } = React;

function App() {
  const [status, setStatus] = useState('idle');
  const [evidenceList, setEvidenceList] = useState([]);
  const [lastBlob, setLastBlob] = useState(null);
  const [result, setResult] = useState(null);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [forceSave, setForceSave] = useState(false);
  const fileRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  // encode Float32Array samples to 16-bit PCM WAV Blob
  function encodeWAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(view, offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }

    // RIFF identifier
    writeString(view, 0, 'RIFF');
    // file length minus RIFF and size
    view.setUint32(4, 36 + samples.length * 2, true);
    // WAVE
    writeString(view, 8, 'WAVE');
    // fmt chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // chunk length
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // channels
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // byte rate (sampleRate * blockAlign)
    view.setUint16(32, 2, true); // block align
    view.setUint16(34, 16, true); // bits per sample
    // data chunk
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // write PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  async function analyzeFile(file) {
    setStatus('uploading');
    const fd = new FormData();
    fd.append('audio', file, file.name || 'upload.wav');
    fd.append('sensitivity', sensitivity);
    if (forceSave) fd.append('force_save', '1');
    try {
      // let axios set the Content-Type boundary automatically
      console.debug('Uploading', file);
      const r = await axios.post('/analyze', fd, {
        onUploadProgress: (ev) => {
          // simple progress indicator
          if (ev.lengthComputable) {
            const pct = Math.round((ev.loaded / ev.total) * 100);
            setStatus(`uploading ${pct}%`);
          }
        }
      });
      console.debug('Server response', r.data);
      setResult(r.data);
      // refresh evidence list immediately after a successful analyze
      try { fetchEvidence(); } catch(_){}
      // if caller passed a Blob/File, draw it
      try { if (file instanceof Blob) { setLastBlob(file); } } catch(_){}
      setStatus('done');
    } catch (e) {
      console.error('Upload error', e);
      setResult({ error: e.response ? e.response.data : e.message });
      setStatus('error');
    }
  }

  async function fetchEvidence() {
    try {
      const r = await axios.get('/evidence/list');
      setEvidenceList(r.data.events || []);
    } catch (e) {
      console.warn('Could not fetch evidence list', e);
    }
  }

  // auto-refresh evidence list every 10s
  React.useEffect(()=>{
    fetchEvidence();
    const id = setInterval(fetchEvidence, 10000);
    return ()=>clearInterval(id);
  }, []);

  function onUploadClick() {
    const f = fileRef.current.files[0];
    if (!f) return alert('Choose a file first');
    analyzeFile(f);
  }

  // RECORDING USING AudioContext -> PCM -> WAV to avoid server-side ffmpeg
  const audioCtxRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);

  async function startRecording() {
    setStatus('recording');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      sourceRef.current = audioCtxRef.current.createMediaStreamSource(stream);
      const bufferLen = 4096;
      processorRef.current = audioCtxRef.current.createScriptProcessor(bufferLen, 1, 1);
      const samples = [];
      processorRef.current.onaudioprocess = (e) => {
        const ch = e.inputBuffer.getChannelData(0);
        samples.push(new Float32Array(ch));
      };
      sourceRef.current.connect(processorRef.current);
      try { processorRef.current.connect(audioCtxRef.current.destination); } catch(_) {}

      mediaRecorderRef.current = { stream, samples };
    } catch (e) {
      setStatus('error');
      setResult({ error: String(e) });
    }
  }

  async function stopRecording() {
    if (!mediaRecorderRef.current) return;
    setStatus('stopping');
    try {
      const { stream, samples } = mediaRecorderRef.current;
      // concat Float32 chunks
      let totalLen = samples.reduce((s, a) => s + a.length, 0);
      const out = new Float32Array(totalLen);
      let offset = 0;
      for (const s of samples) { out.set(s, offset); offset += s.length; }
      const blob = encodeWAV(out, audioCtxRef.current.sampleRate);
      const file = new File([blob], 'recording.wav', { type: 'audio/wav' });
      await analyzeFile(file);
    } catch (e) {
      setResult({ error: String(e) });
      setStatus('error');
    } finally {
      try { processorRef.current.disconnect(); } catch(_){ }
      try { sourceRef.current.disconnect(); } catch(_){ }
      try { audioCtxRef.current.close(); } catch(_){ }
      if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
      }
      mediaRecorderRef.current = null;
      try { audioCtxRef.current = null; } catch(_){}
      try { sourceRef.current = null; } catch(_){}
      try { processorRef.current = null; } catch(_){}
    }
  }

  // Continuous monitoring: capture 1s chunks and send repeatedly
  let continuousState = useRef({ running: false, intervalId: null, accum: [] });

  async function startContinuous() {
    setStatus('continuous');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // reuse audio context if exists
      if (!audioCtxRef.current) audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      sourceRef.current = audioCtxRef.current.createMediaStreamSource(stream);
      const bufferLen = 4096;
      processorRef.current = audioCtxRef.current.createScriptProcessor(bufferLen, 1, 1);
      // accumulates Float32Array chunks continuously
      const accum = [];
      processorRef.current.onaudioprocess = (e) => {
        const ch = e.inputBuffer.getChannelData(0);
        // copy the buffer to avoid referencing the underlying memory
        accum.push(new Float32Array(ch));
      };
      sourceRef.current.connect(processorRef.current);
      // Do NOT connect processor to destination to avoid playback feedback on most browsers
      try { processorRef.current.connect(audioCtxRef.current.destination); } catch(_) {}

      // periodic sender: every 1s, assemble exactly sampleRate samples and send
      const sendInterval = setInterval(()=>{
        try {
          const sampleRate = (audioCtxRef.current && audioCtxRef.current.sampleRate) || 44100;
          const needed = sampleRate;
          const total = accum.reduce((s,a)=>s+a.length,0);
          if (total < needed) return; // not enough yet
          const out = new Float32Array(needed);
          let off = 0;
          while (off < needed && accum.length) {
            const chunk = accum.shift();
            const take = Math.min(chunk.length, needed - off);
            out.set(chunk.subarray(0, take), off);
            if (take < chunk.length) {
              accum.unshift(chunk.subarray(take));
            }
            off += take;
          }
          const blob = encodeWAV(out, audioCtxRef.current.sampleRate);
          setLastBlob(blob);
          // draw immediately for live feedback
          try { drawWaveform(blob); } catch(_){}
          analyzeFile(new File([blob], 'chunk.wav', { type: 'audio/wav' }));
        } catch(e) {
          console.error('continuous send error', e);
        }
      }, 1000);

      continuousState.current = { running: true, stream, accum, intervalId: sendInterval };
    } catch (e) {
      setStatus('error');
      setResult({ error: String(e) });
    }
  }

  function stopContinuous() {
    try {
      if (continuousState.current && continuousState.current.intervalId) {
        clearInterval(continuousState.current.intervalId);
      }
      if (processorRef.current) try{ processorRef.current.disconnect(); }catch(_){ }
      if (sourceRef.current) try{ sourceRef.current.disconnect(); }catch(_){ }
      if (audioCtxRef.current) try{ audioCtxRef.current.close(); audioCtxRef.current = null; }catch(_){ }
      if (continuousState.current && continuousState.current.stream) {
        continuousState.current.stream.getTracks().forEach(t=>t.stop());
      }
    } catch(_){ }
    continuousState.current = { running: false, accum: [] };
    setStatus('idle');
  }

  // draw waveform of last sent blob
  const canvasRef = useRef(null);
  async function drawWaveform(blob) {
    if (!blob) return;
    try {
      const ab = await blob.arrayBuffer();
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const audioBuffer = await ctx.decodeAudioData(ab.slice(0));
      const data = audioBuffer.getChannelData(0);
      const canvas = canvasRef.current;
      if (!canvas) return;
      const w = canvas.width = canvas.clientWidth;
      const h = canvas.height = 100;
      const c = canvas.getContext('2d');
      c.fillStyle = '#071224'; c.fillRect(0,0,w,h);
      c.strokeStyle = '#6be4ff'; c.lineWidth = 1;
      c.beginPath();
      const step = Math.floor(data.length / w) || 1;
      for (let i=0;i<w;i++){
        const v = data[i*step];
        const y = (1 - v) * (h/2);
        if (i===0) c.moveTo(i,y); else c.lineTo(i,y);
      }
      c.stroke();
      try{ ctx.close(); }catch(_){}
    } catch(e) { console.warn('draw waveform failed', e); }
  }

  // auto-draw when lastBlob changes
  React.useEffect(()=>{
    if (lastBlob) drawWaveform(lastBlob);
  }, [lastBlob]);

  return (
    <div style={{maxWidth:900, margin:'0 auto'}}>
      <h1>WhisperGuard — React Demo</h1>
      <div style={{display:'flex', gap:20}}>
        <div style={{flex:1}}>
          <h3>Upload audio</h3>
          <input ref={fileRef} type="file" accept="audio/*" />
          <div style={{marginTop:8}}>
            <label>Sensitivity: {sensitivity}</label>
            <input type="range" min="0" max="1" step="0.01" value={sensitivity}
              onChange={(e)=>setSensitivity(parseFloat(e.target.value))} />
            <div style={{marginTop:6}}>
              <label style={{marginRight:8}}>Force save evidence:</label>
              <input type="checkbox" checked={forceSave} onChange={(e)=>setForceSave(e.target.checked)} />
            </div>
          </div>
          <div style={{marginTop:8}}>
            <button onClick={onUploadClick}>Analyze Upload</button>
          </div>

          <h3 style={{marginTop:20}}>Record (browser)</h3>
              <div style={{display:'flex', gap:8}}>
                <button onClick={startRecording}>Start Recording</button>
                <button onClick={stopRecording}>Stop & Send</button>
              </div>
              <h4 style={{marginTop:18}}>Continuous monitoring</h4>
              <div style={{display:'flex', gap:8}}>
                <button onClick={startContinuous}>Start Continuous</button>
                <button onClick={stopContinuous}>Stop Continuous</button>
              </div>
              <div style={{marginTop:8}} className="muted">Continuous mode sends 1s WAV chunks to the server while the mic is open.</div>
        </div>
          <div style={{flex:1}}>
          <h3>Saved Evidence</h3>
          <div style={{marginBottom:8}}>
            <button onClick={fetchEvidence}>Refresh Evidence List</button>
          </div>
          <div style={{maxHeight:220, overflow:'auto', background:'#071224', padding:8, borderRadius:6}}>
            {evidenceList.length === 0 && <div className="muted">No evidence saved yet.</div>}
            {evidenceList.map(ev=> (
              <div key={ev.name} style={{padding:6, borderBottom:'1px solid rgba(255,255,255,0.03)'}}>
                <div style={{fontWeight:600}}>{ev.name}</div>
                <div className="muted">{ev.metadata ? (ev.metadata.level || '') : ''}</div>
                <div style={{marginTop:6}}>
                  {ev.files.map(f=> (
                    <div key={f}><a target="_blank" rel="noreferrer" href={`/static/evidence/${ev.name}/${f}`}>{f}</a></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <h3>Status</h3>
          <div style={{padding:10, background:'#f6f6f6'}}>{status}</div>
          <h3 style={{marginTop:20}}>Result</h3>
          <pre style={{background:'#fff', border:'1px solid #ddd', padding:10, minHeight:200}}>{result ? JSON.stringify(result, null, 2) : 'No result yet.'}</pre>
          <div style={{marginTop:12}}>
            <h4>Last Sent Waveform</h4>
            <canvas ref={canvasRef} style={{width:'100%', border:'1px solid #ccc', borderRadius:6}} />
          </div>
          {result && result.evidence && (
            <div style={{marginTop:12}}>
              <h4>Evidence</h4>
              <div><a target="_blank" rel="noreferrer" href={`/static/${result.evidence.audio}`}>Download audio.wav</a></div>
              <div><a target="_blank" rel="noreferrer" href={`/static/${result.evidence.spectrogram}`}>View spectrogram</a></div>
              <div><a target="_blank" rel="noreferrer" href={`/static/${result.evidence.metadata}`}>View metadata</a></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
