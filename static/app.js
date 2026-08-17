document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const targetBtn = document.getElementById('targetBtn');
  const targetLabel = document.getElementById('targetLabel');
  const targetChips = document.getElementById('targetChips');

  const videoBtn = document.getElementById('videoBtn');
  const videoLabel = document.getElementById('videoLabel');
  const videoFolderBtn = document.getElementById('videoFolderBtn');
  const videoFolderLabel = document.getElementById('videoFolderLabel');
  const videoStats = document.getElementById('videoStats');
  const batchQueueEl = document.getElementById('batchQueue');

  const threshSlider = document.getElementById('threshSlider');
  const threshVal = document.getElementById('threshVal');
  const perfSelect = document.getElementById('perfSelect');
  const perfHint = document.getElementById('perfHint');

  const startBtn = document.getElementById('startBtn');
  const runningControls = document.getElementById('runningControls');
  const pauseBtn = document.getElementById('pauseBtn');
  const stopBtn = document.getElementById('stopBtn');

  const videoPlaceholder = document.getElementById('videoPlaceholder');
  const videoStream = document.getElementById('videoStream');
  const reviewVideo = document.getElementById('reviewVideo');
  const tabLiveBtn = document.getElementById('tabLiveBtn');
  const tabReviewBtn = document.getElementById('tabReviewBtn');

  const progressBarContainer = document.getElementById('progressBarContainer');
  const progressBar = document.getElementById('progressBar');
  const progressTicks = document.getElementById('progressTicks');

  const statProcessed = document.getElementById('statProcessed');
  const statFps = document.getElementById('statFps');
  const statEta = document.getElementById('statEta');
  const statMatches = document.getElementById('statMatches');

  const matchesList = document.getElementById('matchesList');
  const exportBtn = document.getElementById('exportBtn');
  const hardwarePill = document.getElementById('hardwarePill');

  const inspectorModal = document.getElementById('inspectorModal');
  const inspectorTarget = document.getElementById('inspectorTarget');
  const inspectorTargetName = document.getElementById('inspectorTargetName');
  const inspectorMatch = document.getElementById('inspectorMatch');
  const inspectorTime = document.getElementById('inspectorTime');
  const inspectorScore = document.getElementById('inspectorScore');
  const inspectorJumpBtn = document.getElementById('inspectorJumpBtn');
  const modalClose = document.getElementById('modalClose');

  // State
  let targetsReady = false;
  let videoReady = false;
  let videoPath = "";
  let currentVideoDuration = 0;
  let activeTab = 'live';

  let videoQueue = [];
  let queueIndex = -1;
  let batchMode = false;

  const targetsById = {};   // target_id -> {name, thumbnail_url}
  let pendingJumpTimestamp = null;

  function updateStartButton() {
    startBtn.disabled = !(targetsReady && videoReady);
  }

  // --- Target Subject Management ---

  function renderTargetChips() {
    const ids = Object.keys(targetsById);
    if (ids.length === 0) {
      targetChips.innerHTML = '';
      targetLabel.textContent = "Add Target Photo";
      targetBtn.classList.remove("success");
      targetsReady = false;
      updateStartButton();
      return;
    }
    targetChips.innerHTML = ids.map(id => {
      const t = targetsById[id];
      const warn = t.is_blurry
        ? `<span class="chip-warning" title="Image may be too blurry for reliable matching">⚠</span>`
        : '';
      return `
        <div class="target-chip" data-id="${id}">
          <img class="target-chip-img" src="${t.thumbnail_url}" alt="${t.name}">
          <span class="target-chip-name">${t.name}</span>
          ${warn}
          <button class="target-chip-remove" data-id="${id}" title="Remove target">&times;</button>
        </div>`;
    }).join('');

    targetChips.querySelectorAll('.target-chip-remove').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        await fetch('/api/remove_target', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_id: id })
        });
        delete targetsById[id];
        renderTargetChips();
      });
    });

    targetLabel.textContent = "Add Another Target";
    targetBtn.classList.add("success");
    targetsReady = true;
    updateStartButton();
  }

  targetBtn.addEventListener('click', async () => {
    const res = await fetch('/api/select_target', { method: 'POST' });
    const data = await res.json();
    if (data.success && data.targets) {
      data.targets.forEach(t => { targetsById[t.target_id] = t; });
      renderTargetChips();
    }
    if (data.errors && data.errors.length > 0) {
      const msg = data.errors.map(e => `${e.file}: ${e.message}`).join('\n');
      console.warn('Some target photos could not be added:\n' + msg);
    }
  });

  // --- Video Selection (single file) ---

  videoBtn.addEventListener('click', async () => {
    const res = await fetch('/api/select_video', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      batchMode = false;
      videoQueue = [];
      batchQueueEl.style.display = 'none';
      applyVideoInfo(data);
      videoLabel.textContent = "Video Selected ✓";
      videoBtn.classList.add("success");
      videoFolderBtn.classList.remove("success");
    }
  });

  // --- Batch Folder Selection ---

  videoFolderBtn.addEventListener('click', async () => {
    const res = await fetch('/api/select_video_folder', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      videoQueue = data.videos;
      queueIndex = 0;
      batchMode = true;
      videoBtn.classList.remove("success");
      videoFolderBtn.classList.add("success");
      videoFolderLabel.textContent = `${videoQueue.length} Videos Queued ✓`;
      renderBatchQueue();
      await loadQueueItem(0);
    } else if (data.message) {
      console.warn(data.message);
    }
  });

  function renderBatchQueue() {
    if (videoQueue.length === 0) {
      batchQueueEl.style.display = 'none';
      return;
    }
    batchQueueEl.style.display = 'flex';
    batchQueueEl.innerHTML = videoQueue.map((path, i) => {
      const name = path.split(/[\\/]/).pop();
      let cls = 'queue-item';
      if (i < queueIndex) cls += ' done';
      else if (i === queueIndex) cls += ' active';
      return `<div class="${cls}"><span class="queue-index">${i + 1}</span><span class="queue-name">${name}</span></div>`;
    }).join('');
  }

  async function loadQueueItem(index) {
    if (index >= videoQueue.length) {
      batchMode = false;
      return false;
    }
    queueIndex = index;
    renderBatchQueue();
    const path = videoQueue[index];
    const res = await fetch('/api/video_info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    const data = await res.json();
    if (!data.success) {
      // Skip unreadable file and try the next one in queue.
      return loadQueueItem(index + 1);
    }
    applyVideoInfo(data);
    return true;
  }

  function applyVideoInfo(data) {
    videoReady = true;
    videoPath = data.path;
    currentVideoDuration = data.duration || 0;
    videoStats.style.display = 'block';
    videoStats.innerHTML = `${data.resolution} • ${data.fps.toFixed(2)} FPS • ${(data.duration / 60).toFixed(1)} mins`;
    reviewVideo.src = '/video_file?' + new Date().getTime();
    updateStartButton();
  }

  // --- Settings ---

  threshSlider.addEventListener('input', async (e) => {
    const val = e.target.value;
    threshVal.textContent = val;
    await fetch('/api/thresholds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cosine: parseFloat(val) })
    });
  });

  const PERF_HINTS = {
    "0": "Analyzes every frame for maximum detection accuracy.",
    "1": "Skips 1 of every 2 frames. Faster on very long footage; may miss extremely brief appearances.",
    "3": "Skips 3 of every 4 frames. Best for quickly triaging large archives."
  };
  perfSelect.addEventListener('change', async (e) => {
    const val = e.target.value;
    perfHint.textContent = PERF_HINTS[val] || '';
    await fetch('/api/thresholds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame_skip: parseInt(val, 10) })
    });
  });

  // --- Tabs (Live Scan / Review) ---

  function setTab(tab) {
    activeTab = tab;
    tabLiveBtn.classList.toggle('active', tab === 'live');
    tabReviewBtn.classList.toggle('active', tab === 'review');

    if (tab === 'live') {
      reviewVideo.pause();
      reviewVideo.style.display = 'none';
      if (videoStream.getAttribute('src')) {
        videoStream.style.display = 'block';
        videoPlaceholder.style.display = 'none';
      } else {
        videoPlaceholder.style.display = 'block';
      }
    } else {
      videoStream.style.display = 'none';
      videoPlaceholder.style.display = 'none';
      reviewVideo.style.display = 'block';
    }
  }

  tabLiveBtn.addEventListener('click', () => setTab('live'));
  tabReviewBtn.addEventListener('click', () => setTab('review'));

  function jumpToTimestamp(seconds) {
    setTab('review');
    if (reviewVideo.readyState === 0) {
      pendingJumpTimestamp = seconds;
    } else {
      reviewVideo.currentTime = seconds;
    }
  }
  reviewVideo.addEventListener('loadedmetadata', () => {
    if (pendingJumpTimestamp !== null) {
      reviewVideo.currentTime = pendingJumpTimestamp;
      pendingJumpTimestamp = null;
    }
  });

  // --- Interactive Timeline / Seekbar ---

  progressBarContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('progress-tick')) return; // handled separately
    if (!currentVideoDuration) return;
    const rect = progressBarContainer.getBoundingClientRect();
    const pct = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    jumpToTimestamp(pct * currentVideoDuration);
  });

  function addTick(timestamp) {
    if (!currentVideoDuration) return;
    const pct = Math.min(100, Math.max(0, (timestamp / currentVideoDuration) * 100));
    const tick = document.createElement('div');
    tick.className = 'progress-tick';
    tick.style.left = `${pct}%`;
    tick.title = `Match at ${timestamp.toFixed(1)}s — click to jump`;
    tick.addEventListener('click', (e) => {
      e.stopPropagation();
      jumpToTimestamp(timestamp);
    });
    progressTicks.appendChild(tick);
  }

  function resetTimeline() {
    progressTicks.innerHTML = '';
    progressBar.style.width = '0%';
  }

  // --- Controls ---

  async function beginScan() {
    matchesList.innerHTML = '';
    resetTimeline();
    statProcessed.textContent = '0 / 0 frames';
    statFps.textContent = '0.00';
    statEta.textContent = '0s';
    statMatches.textContent = '0';

    setTab('live');
    videoPlaceholder.style.display = 'none';
    videoStream.style.display = 'block';
    videoStream.src = '/video_feed?' + new Date().getTime(); // cache bust

    startBtn.style.display = 'none';
    runningControls.style.display = 'flex';

    await fetch('/api/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: 'start', video_path: videoPath })
    });
  }

  startBtn.addEventListener('click', () => { beginScan(); });

  pauseBtn.addEventListener('click', async () => {
    const isPaused = pauseBtn.textContent.includes('Resume');
    const cmd = isPaused ? 'resume' : 'pause';

    await fetch('/api/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd })
    });

    if (isPaused) {
      pauseBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg> Pause';
    } else {
      pauseBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Resume';
    }
  });

  stopBtn.addEventListener('click', async () => {
    batchMode = false; // stopping cancels the rest of the batch queue too
    await fetch('/api/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: 'terminate' })
    });
  });

  exportBtn.addEventListener('click', () => {
    window.location.href = '/api/export_report';
  });

  // --- Match Inspector Modal ---

  function openInspector(match) {
    const target = targetsById[match.target_id];
    inspectorTarget.src = target ? target.thumbnail_url : '';
    inspectorTargetName.textContent = target ? target.name : (match.target_name || 'Target');
    inspectorMatch.src = match.image_url;
    inspectorTime.textContent = `${match.timestamp_str}${match.video_name ? ' • ' + match.video_name : ''}`;
    inspectorScore.textContent = `${(match.similarity * 100).toFixed(1)}% Match`;
    inspectorJumpBtn.onclick = () => {
      inspectorModal.style.display = 'none';
      jumpToTimestamp(match.timestamp);
    };
    inspectorModal.style.display = 'flex';
  }

  modalClose.addEventListener('click', () => { inspectorModal.style.display = 'none'; });
  inspectorModal.addEventListener('click', (e) => {
    if (e.target === inspectorModal) inspectorModal.style.display = 'none';
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
    addTick(match.timestamp);

    const card = document.createElement('div');
    card.className = 'match-card';
    card.innerHTML = `
      <img class="match-img" src="${match.image_url}" alt="Face Crop">
      <div class="match-details">
        <span class="match-time">${match.timestamp_str}</span>
        <span class="match-target">${match.target_name || ''}</span>
        <span class="match-score">${(match.similarity * 100).toFixed(1)}% Match</span>
      </div>
    `;
    card.addEventListener('click', () => openInspector(match));
    matchesList.prepend(card);
  });

  evtSource.addEventListener('status', (e) => {
    const data = JSON.parse(e.data);
    if (data.state === 'COMPLETED' || data.state === 'TERMINATED' || data.state === 'IDLE') {
      runningControls.style.display = 'none';
      startBtn.style.display = 'flex';
      pauseBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg> Pause';

      if (data.state === 'COMPLETED' && batchMode && queueIndex < videoQueue.length - 1) {
        loadQueueItem(queueIndex + 1).then(loaded => {
          if (loaded) beginScan();
        });
      } else {
        if (activeTab === 'live') {
          videoStream.style.display = 'none';
          videoPlaceholder.style.display = 'block';
        }
        batchMode = false;
      }
    }
  });

  // --- Engine info (hardware acceleration badge) ---
  fetch('/api/engine_info').then(r => r.json()).then(data => {
    if (data.success) {
      hardwarePill.textContent = data.gpu_accelerated ? 'GPU Accelerated' : 'CPU';
      hardwarePill.classList.toggle('pill-gpu', !!data.gpu_accelerated);
    }
  }).catch(() => {});
});
