const form = document.getElementById('form');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const logsEl = document.getElementById('logs');
const jobSelect = document.getElementById('job-select');
const loadJobBtn = document.getElementById('load-job');
const viewer = document.getElementById('viewer');
const audioEl = document.getElementById('audio');
const subsEl = document.getElementById('subs');

let cues = [] // {start,end,kanji,hira}
let currentCue = -1

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  resultEl.innerHTML = '';
  logsEl.textContent = '';
  statusEl.textContent = ' running...';
  const url = document.getElementById('url').value;
  const lang = document.getElementById('lang').value;

  try {
    const res = await fetch('/process', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, lang})
    });
    const data = await res.json();
    if (!res.ok) {
      logsEl.textContent = JSON.stringify(data, null, 2);
      statusEl.textContent = ' error';
      return;
    }
    statusEl.textContent = ' done';
    // show links
    const ul = document.createElement('ul');
    const add = (name, href) => {
      if (!href) return;
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = href; a.target = '_blank'; a.textContent = name + ' — ' + href;
      li.appendChild(a); ul.appendChild(li);
    };
    add('audio', data.audio);
    add('srt', data.srt);
    add('converted srt', data.converted_srt);
    resultEl.appendChild(ul);
    logsEl.textContent = JSON.stringify(data.logs, null, 2);
  } catch (err) {
    statusEl.textContent = ' error';
    logsEl.textContent = String(err);
  }
});

  // load job list on start
  async function loadJobs(){
    try{
      const res = await fetch('/jobs');
      const jobs = await res.json();
      jobSelect.innerHTML = '';
      jobs.forEach(j=>{
        const opt = document.createElement('option');
        opt.value = JSON.stringify(j);
        opt.textContent = j.job + (j.audio?(' — '+j.audio.split('/').pop()):'');
        jobSelect.appendChild(opt);
      })
    }catch(e){
      console.warn('jobs load failed', e);
    }
  }

  loadJobBtn.addEventListener('click', async (e)=>{
    e.preventDefault();
    const val = jobSelect.value;
    if(!val) return;
    const job = JSON.parse(val);
    if(!job.audio){
      alert('job has no audio');
      return;
    }
    viewer.style.display = '';
    audioEl.src = job.audio;
    subsEl.textContent = '';
    cues = [];
    currentCue = -1;

    // fetch srt files
    const srtPromise = job.srt ? fetch(job.srt).then(r=>r.text()) : Promise.resolve(null);
    const kanaPromise = job.converted_srt ? fetch(job.converted_srt).then(r=>r.text()) : Promise.resolve(null);
    const [srtText, kanaText] = await Promise.all([srtPromise, kanaPromise]);
    const srtCues = srtText ? parseSrt(srtText) : [];
    const kanaCues = kanaText ? parseSrt(kanaText) : [];

    // combine cues by index: take kanji from srtCues, hira from kanaCues (second text line if present)
    const n = Math.max(srtCues.length, kanaCues.length);
    for(let i=0;i<n;i++){
      const a = srtCues[i] || {};
      const b = kanaCues[i] || {};
      let kanji = a.text || (b.text||'');
      let hira = '';
      if(b.text){
        // kana file often contains original line then kana line; choose second line if present
        const lines = b.text.split('\n').map(s=>s.trim()).filter(Boolean);
        if(lines.length>=2) hira = lines.slice(1).join(' ');
        else hira = lines[0] || '';
      }
      cues.push({start: a.start||b.start||0, end: a.end||b.end||0, kanji, hira});
    }
  });

  function parseSrt(text){
    const parts = text.replace(/\r\n/g,'\n').split('\n\n');
    const out = [];
    for(const p of parts){
      const lines = p.split('\n').map(l=>l.trim());
      if(lines.length<2) continue;
      // first line may be index
      let idx = 0;
      if(/^\d+$/.test(lines[0])) idx = 1;
      const timeLine = lines[idx];
      const m = timeLine.match(/(\d{2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{1,3})/);
      if(!m) continue;
      const start = parseTime(m[1]);
      const end = parseTime(m[2]);
      const textLines = lines.slice(idx+1).join('\n');
      out.push({start,end,text:textLines});
    }
    return out;
  }

  function parseTime(t){
    // formats like 00:00:08,640 or 00:00.000
    t = t.replace(',', '.');
    const parts = t.split(':');
    if(parts.length===3){
      return parseInt(parts[0],10)*3600 + parseInt(parts[1],10)*60 + parseFloat(parts[2]);
    }
    if(parts.length===2){
      return parseInt(parts[0],10)*60 + parseFloat(parts[1]);
    }
    return parseFloat(t)||0;
  }

  audioEl.addEventListener('timeupdate', ()=>{
    const t = audioEl.currentTime;
    // find the cue index
    let idx = -1;
    for(let i=0;i<cues.length;i++){
      if(t >= cues[i].start && t <= cues[i].end){ idx = i; break }
    }
    if(idx !== currentCue){
      currentCue = idx;
      if(idx===-1){ subsEl.innerHTML = ''; }
      else{
        const c = cues[idx];
        // show kanji and hiragana
        const kanji = c.kanji || '';
        const hira = c.hira || '';
        subsEl.innerHTML = `<div style="font-size:22px">${escapeHtml(kanji)}</div>${hira?`<div style="font-size:18px;opacity:0.95">${escapeHtml(hira)}</div>`:''}`;
      }
    }
  });

  function escapeHtml(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

  // initial load
  loadJobs();
