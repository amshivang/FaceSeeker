document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const targetBtn = document.getElementById('targetBtn');
  const targetLabel = document.getElementById('targetLabel');
  const videoBtn = document.getElementById('videoBtn');
  const videoLabel = document.getElementById('videoLabel');
  const videoStats = document.getElementById('videoStats');
  
  const threshSlider = document.getElementById('threshSlider');
  const threshVal = document.getElementById('threshVal');
  
  const startBtn = document.getElementById('startBtn');
  const runningControls = document.getElementById('runningControls');
  const pauseBtn = document.getElementById('pauseBtn');
  const stopBtn = document.getElementById('stopBtn');
  
  const videoPlaceholder = document.getElementById('videoPlaceholder');
  const videoStream = document.getElementById('videoStream');
  const progressBar = document.getElementById('progressBar');
  
  const statProcessed = document.getElementById('statProcessed');
  const statFps = document.getElementById('statFps');
  const statEta = document.getElementById('statEta');
  const statMatches = document.getElementById('statMatches');
  
  const matchesList = document.getElementById('matchesList');

  // State
  let targetReady = false;
  let videoReady = false;
  let videoPath = "";
  
  function updateStartButton() {
    startBtn.disabled = !(targetReady && videoReady);
  }

  // --- API Calls for File Selection ---
  
  targetBtn.addEventListener('click', async () => {
    const res = await fetch('/api/select_target', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      targetReady = true;
      targetLabel.textContent = "Target Loaded ✓";
      targetBtn.classList.add("success");
      updateStartButton();
    }
  });

  videoBtn.addEventListener('click', async () => {
    const res = await fetch('/api/select_video', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      videoReady = true;
      videoPath = data.path;
      videoLabel.textContent = "Video Selected ✓";
      videoBtn.classList.add("success");
      
      videoStats.style.display = 'block';
      videoStats.innerHTML = `${data.resolution} • ${data.fps.toFixed(2)} FPS • ${(data.duration/60).toFixed(1)} mins`;
      updateStartButton();
    }
  });

  // --- Settings ---
  threshSlider.addEventListener('input', async (e) => {
    const val = e.target.value;
    threshVal.textContent = val;
    await fetch('/api/thresholds', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ cosine: parseFloat(val) })
    });
  });

  // --- Controls ---
  startBtn.addEventListener('click', async () => {
    // Reset UI
    matchesList.innerHTML = '';
    progressBar.style.width = '0%';
    statProcessed.textContent = '0 / 0 frames';
    statFps.textContent = '0.00';
    statEta.textContent = '0s';
    statMatches.textContent = '0';
    
    // Switch to video stream view
    videoPlaceholder.style.display = 'none';
    videoStream.style.display = 'block';
    videoStream.src = '/video_feed?' + new Date().getTime(); // cache bust
    
    // Update Controls
    startBtn.style.display = 'none';
    runningControls.style.display = 'flex';
    
    // Start Engine
    await fetch('/api/action', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ command: 'start', video_path: videoPath })
    });
  });

  pauseBtn.addEventListener('click', async () => {
    const isPaused = pauseBtn.textContent.includes('Resume');
    const cmd = isPaused ? 'resume' : 'pause';
    
    await fetch('/api/action', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ command: cmd })
    });
    
    if (isPaused) {
      pauseBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg> Pause';
    } else {
      pauseBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Resume';
    }
  });

  stopBtn.addEventListener('click', async () => {
    await fetch('/api/action', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ command: 'terminate' })
    });
  });

  // --- Server-Sent Events (SSE) Listener ---
  const evtSource = new EventSource('/api/stream');
  
  evtSource.addEventListener('stats', (e) => {
    const stats = JSON.parse(e.data);
    progressBar.style.width = `${stats.progress_percent}%`;
    statProcessed.textContent = `${stats.processed_frames} / ${stats.total_frames}`;
    statFps.textContent = `${stats.fps.toFixed(2)}`;
    statEta.textContent = `${stats.eta.toFixed(1)}s`;
    statMatches.textContent = `${stats.matches_count}`;
  });

  evtSource.addEventListener('match', (e) => {
    const match = JSON.parse(e.data);
    
    const card = document.createElement('div');
    card.className = 'match-card';
    card.innerHTML = `
      <img class="match-img" src="${match.image_url}" alt="Face Crop">
      <div class="match-details">
        <span class="match-time">${match.timestamp_str}</span>
        <span class="match-score">${(match.similarity * 100).toFixed(1)}% Match</span>
      </div>
    `;
    matchesList.prepend(card);
  });

  evtSource.addEventListener('status', (e) => {
    const data = JSON.parse(e.data);
    if (data.state === 'COMPLETED' || data.state === 'TERMINATED' || data.state === 'IDLE') {
      runningControls.style.display = 'none';
      startBtn.style.display = 'flex';
      videoStream.style.display = 'none';
      videoPlaceholder.style.display = 'block';
      pauseBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg> Pause';
    }
  });
});
