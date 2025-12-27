const { useState, useRef, useEffect } = React;

function VendorTag({name, score}){
  const pct = Math.round((score||0)*100);
  const cls = score > 0.7 ? 'result-danger' : (score > 0.4 ? 'result-warning' : 'result-safe');
  return (<span className={`vendor-tag ${cls}`} title={`${pct}%`}>{name} <small className="small-muted">{pct}%</small></span>);
}

function AppHeader(){
  return (
    <nav className="navbar navbar-dark bg-dark">
      <div className="container-fluid">
        <a className="navbar-brand" href="#">WhisperGuard</a>
        <div className="d-flex">
          <a className="nav-link text-light" href="#">Scan</a>
          <a className="nav-link text-light" href="#">Evidence</a>
        </div>
      </div>
    </nav>
  );
}

function App(){
  const [status, setStatus] = useState('idle');
  const [evidenceList, setEvidenceList] = useState([]);
  const [result, setResult] = useState(null);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [forceSave, setForceSave] = useState(false);
  const fileRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const continuousRef = useRef({ running: false, stream: null });
  const [continuousRunning, setContinuousRunning] = useState(false);

  async function fetchEvidence(){
    try{ const r = await axios.get('/evidence/list'); setEvidenceList(r.data.events || []); }catch(e){ console.warn(e); }
  }

  useEffect(()=>{ fetchEvidence(); const id = setInterval(fetchEvidence, 10000); return ()=>clearInterval(id); }, []);

  function encodeWAV(samples, sampleRate){
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    function writeString(v, o, s){ for(let i=0;i<s.length;i++) v.setUint8(o+i,s.charCodeAt(i)); }
    writeString(view,0,'RIFF'); view.setUint32(4,36 + samples.length*2, true); writeString(view,8,'WAVE');
    writeString(view,12,'fmt '); view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
    view.setUint32(24,sampleRate,true); view.setUint32(28,sampleRate*2,true); view.setUint16(32,2,true); view.setUint16(34,16,true);
    writeString(view,36,'data'); view.setUint32(40,samples.length*2,true);
    let off=44; for(let i=0;i<samples.length;i++,off+=2){ let s=Math.max(-1,Math.min(1,samples[i])); view.setInt16(off, s<0?s*0x8000:s*0x7FFF, true); }
    return new Blob([view], {type:'audio/wav'});
  }

  async function startContinuous(){
    if (continuousRunning) return;
    try{
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const opts = {};
      let mime = '';
      try{ mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''); }catch(_){ mime = ''; }
      if (mime) opts.mimeType = mime;
      const mr = new MediaRecorder(stream, opts);
      mr.ondataavailable = async (e) => {
        if (!e.data || e.data.size === 0) return;
        try{
          const ab = await e.data.arrayBuffer();
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const audioBuf = await ctx.decodeAudioData(ab.slice(0));
          const data = audioBuf.numberOfChannels > 1 ? audioBuf.getChannelData(0) : audioBuf.getChannelData(0);
          const wav = encodeWAV(data, audioBuf.sampleRate);
          await analyzeFile(new File([wav],'chunk.wav',{type:'audio/wav'}));
          try{ ctx.close(); }catch(_){ }
        }catch(err){ console.warn('continuous chunk decode/send failed', err); }
      };
      mr.onerror = (ev)=> console.warn('MediaRecorder error', ev);
      mr.start(1000);
      mediaRecorderRef.current = mr;
      continuousRef.current = { running: true, stream };
      setContinuousRunning(true);
      setStatus('continuous');
    }catch(e){ console.warn('startContinuous failed', e); setStatus('error'); }
  }

  function stopContinuous(){
    try{
      const mr = mediaRecorderRef.current;
      if (mr && mr.state !== 'inactive') mr.stop();
      if (continuousRef.current && continuousRef.current.stream){
        continuousRef.current.stream.getTracks().forEach(t=>t.stop());
      }
    }catch(_){ }
    mediaRecorderRef.current = null;
    continuousRef.current = { running:false, stream:null };
    setContinuousRunning(false);
    setStatus('idle');
  }

  async function analyzeFile(file){
    setStatus('uploading');
    const fd = new FormData(); fd.append('audio', file, file.name||'upload.wav'); fd.append('sensitivity', sensitivity); if (forceSave) fd.append('force_save','1');
    try{
      const r = await axios.post('/analyze', fd, { headers: {'Accept':'application/json'} });
      setResult(r.data);
      setStatus('done');
      fetchEvidence();
    }catch(e){ setStatus('error'); setResult({error: e.message || String(e)}); }
  }

  function onUpload(){ const f = fileRef.current.files[0]; if(!f) return alert('Select a file'); analyzeFile(f); }

  function vendorListFromResult(res){
    const vendors = ['Vendor A','Vendor B','Vendor C','Ultrasonic Detector'];
    const scores = (res && res.ml_scores) ? Object.values(res.ml_scores) : [0,0,0, (res&&res.rule_ratio)||0];
    return vendors.map((v,i)=>({name:v, score: scores[i] || 0}));
  }

  return (
    <div>
      <AppHeader />
      <div className="container app-container">
        <div className="row">
          <div className="col-lg-4">
            <div className="panel">
              <h5>File Scan</h5>
              <input ref={fileRef} type="file" accept="audio/*" className="form-control mt-2" />
              <div className="mt-2 d-flex align-items-center">
                <label className="small-muted me-2">Sensitivity</label>
                <input type="range" min="0" max="1" step="0.01" value={sensitivity} onChange={(e)=>setSensitivity(parseFloat(e.target.value))} />
              </div>
              <div className="form-check mt-2">
                <input className="form-check-input" type="checkbox" id="forceSave" checked={forceSave} onChange={(e)=>setForceSave(e.target.checked)} />
                <label className="form-check-label small-muted" htmlFor="forceSave">Force save evidence</label>
              </div>
              <div className="mt-3">
                <button className="btn btn-primary me-2" onClick={onUpload}><i className="fa fa-upload"></i> Analyze</button>
                <button className="btn btn-outline-secondary me-2" onClick={()=>{ setResult(null); setStatus('idle'); }}>Reset</button>
                {!continuousRunning ? (
                  <button className="btn btn-success" onClick={startContinuous}><i className="fa fa-play me-1"></i> Start Continuous</button>
                ) : (
                  <button className="btn btn-danger" onClick={stopContinuous}><i className="fa fa-stop me-1"></i> Stop Continuous</button>
                )}
              </div>
              <hr />
              <h6>Saved Evidence</h6>
              <div className="card-list mt-2">
                {evidenceList.length===0 && <div className="small-muted">No evidence saved.</div>}
                {evidenceList.map(ev=> (
                  <div className="mb-2" key={ev.name}>
                    <div className="fw-bold">{ev.name}</div>
                    <div className="small-muted">{ev.metadata ? ev.metadata.level : ''}</div>
                    <div className="mt-1">
                      {ev.files.map(f=> (<a className="evidence-link d-block" key={f} href={`/static/evidence/${ev.name}/${f}`} target="_blank" rel="noreferrer">{f}</a>))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="col-lg-8">
            <div className="panel">
              <div className="d-flex justify-content-between align-items-center">
                <h5>Scan Result</h5>
                <div className="small-muted">Status: {status}</div>
              </div>
              {!result && <div className="small-muted mt-3">Run a scan to see interactive vendor detections and evidence.</div>}
              {result && (
                <div className="mt-3">
                  <div className="d-flex align-items-center mb-2">
                    <h6 className="me-3">Overall: <span className={result.level === 'THREAT' ? 'result-danger' : (result.level === 'SUSPICIOUS' ? 'result-warning' : 'result-safe')}>{result.level}</span></h6>
                    <div className="small-muted">Rule ratio: {result.rule_ratio}</div>
                  </div>
                  <div className="mb-3">
                    {vendorListFromResult(result).map(v=> <VendorTag key={v.name} name={v.name} score={v.score} />)}
                  </div>
                  <div className="mb-2"><strong>Details</strong></div>
                  <pre style={{whiteSpace:'pre-wrap', background:'#041021', padding:12, borderRadius:6, color:'#cfeefe'}}>{JSON.stringify(result, null, 2)}</pre>
                  {result.evidence && (
                    <div className="mt-3">
                      <h6>Evidence Files</h6>
                      <a className="evidence-link d-block" href={`/static/${result.evidence.audio}`} target="_blank" rel="noreferrer">Download audio</a>
                      <a className="evidence-link d-block" href={`/static/${result.evidence.spectrogram}`} target="_blank" rel="noreferrer">View spectrogram</a>
                      <a className="evidence-link d-block" href={`/static/${result.evidence.metadata}`} target="_blank" rel="noreferrer">View metadata</a>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
