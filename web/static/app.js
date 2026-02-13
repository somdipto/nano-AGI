/* ============================================
   Nano-AGI — Shadow Swarm Frontend
   ============================================ */

(function () {
    'use strict';

    // ── DOM refs ──
    const micBtn = document.getElementById('micBtn');
    const micIcon = document.getElementById('micIcon');
    const stopIcon = document.getElementById('stopIcon');
    const heroTitle = document.getElementById('heroTitle');
    const heroSub = document.getElementById('heroSub');
    const statusPill = document.getElementById('statusPill');
    const statusText = document.getElementById('statusText');
    const agentState = document.getElementById('agentState');
    const timer = document.getElementById('timer');
    const timerText = document.getElementById('timerText');
    const liveGrid = document.getElementById('liveGrid');
    const transcriptFeed = document.getElementById('transcriptFeed');
    const analysisFeed = document.getElementById('analysisFeed');
    const chunkBadge = document.getElementById('chunkBadge');
    const todoBadge = document.getElementById('todoBadge');
    const summarySection = document.getElementById('summarySection');
    const summaryCard = document.getElementById('summaryCard');
    const newSessionBtn = document.getElementById('newSessionBtn');
    const historyBtn = document.getElementById('historyBtn');
    const historyPanel = document.getElementById('historyPanel');
    const closeHistory = document.getElementById('closeHistory');
    const historyList = document.getElementById('historyList');
    const overlay = document.getElementById('overlay');
    const vizCanvas = document.getElementById('vizCanvas');
    const tabNav = document.getElementById('tabNav');
    const swarmBadge = document.getElementById('swarmBadge');
    const todosBadge = document.getElementById('todosBadge');
    const activeCount = document.getElementById('activeCount');
    const maxCount = document.getElementById('maxCount');
    const pendingCount = document.getElementById('pendingCount');
    const completedCount = document.getElementById('completedCount');
    const agentGrid = document.getElementById('agentGrid');
    const completedList = document.getElementById('completedList');
    const todoQueue = document.getElementById('todoQueue');
    const killAllBtn = document.getElementById('killAllBtn');
    const sandboxModal = document.getElementById('sandboxModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const closeModal = document.getElementById('closeModal');

    // ── State ──
    let isRecording = false;
    let mediaRecorder = null;
    let audioStream = null;
    let ws = null;
    let swarmWs = null;
    let timerInterval = null;
    let startTime = null;
    let chunkCount = 0;
    let todoCount = 0;
    let audioContext = null;
    let analyser = null;
    let vizRAF = null;
    let allTranscripts = [];
    let serverSummary = null;
    let currentTab = 'listen';

    const CHUNK_INTERVAL_MS = 8000;

    // ── Init ──
    micBtn.addEventListener('click', toggleRecording);
    newSessionBtn.addEventListener('click', resetToReady);
    historyBtn.addEventListener('click', openHistory);
    closeHistory.addEventListener('click', closeHistoryPanel);
    overlay.addEventListener('click', closeHistoryPanel);
    killAllBtn.addEventListener('click', killAll);
    closeModal.addEventListener('click', () => sandboxModal.classList.add('hidden'));

    // Tab switching
    tabNav.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-btn');
        if (!btn) return;
        const tab = btn.dataset.tab;
        switchTab(tab);
    });

    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
        document.querySelectorAll('.tab-content').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));

        if (tab === 'swarm') refreshSwarm();
        if (tab === 'todos') refreshTodos();
    }

    // Start swarm WebSocket
    connectSwarmWs();
    // Initial load
    refreshTodos();

    // ── Swarm WebSocket ──
    function connectSwarmWs() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        swarmWs = new WebSocket(`${proto}//${location.host}/ws/swarm`);
        swarmWs.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'swarm_update') {
                updateSwarmUI(data);
            }
        };
        swarmWs.onclose = () => setTimeout(connectSwarmWs, 5000);
        swarmWs.onerror = () => { };
    }

    function updateSwarmUI(data) {
        const sw = data.swarm;
        activeCount.textContent = sw.active_count;
        maxCount.textContent = sw.max_parallel;
        pendingCount.textContent = data.pending_count;
        completedCount.textContent = data.completed_count;
        swarmBadge.textContent = sw.active_count;

        // Update agent grid if on swarm tab
        if (currentTab === 'swarm' && sw.agents) {
            renderAgentGrid(sw.agents);
        }
    }

    function renderAgentGrid(agents) {
        if (!agents.length) {
            agentGrid.innerHTML = '<div class="panel-empty">No active agents. Waiting for high-priority todos...</div>';
            return;
        }
        agentGrid.innerHTML = agents.map(a => `
            <div class="agent-card ${a.running ? 'running' : 'completed'}">
                <div class="agent-card-header">
                    <span class="agent-label">
                        <span class="agent-status-dot"></span>
                        Agent #${a.todo_id}
                    </span>
                    <span class="agent-elapsed">${Math.round(a.elapsed)}s</span>
                </div>
                <div class="agent-task">${esc(a.task)}</div>
                <div class="agent-meta">
                    <span class="agent-tag cat">${a.category}</span>
                    <span class="agent-tag pri">P${a.priority}</span>
                </div>
                ${a.artifacts.length ? `
                    <div class="agent-artifacts">
                        ${a.artifacts.map(f => `<span class="artifact-tag" onclick="window._viewSandbox(${a.todo_id})">${f}</span>`).join('')}
                    </div>
                ` : ''}
                <div class="agent-actions">
                    <button onclick="window._viewSandbox(${a.todo_id})">📁 Files</button>
                    <button class="btn-approve" onclick="window._approveTodo(${a.todo_id})">✓ Approve</button>
                    <button class="btn-reject" onclick="window._rejectTodo(${a.todo_id})">✗ Reject</button>
                </div>
            </div>
        `).join('');
    }

    // ── Refresh Swarm ──
    function refreshSwarm() {
        fetch('/api/swarm/status').then(r => r.json()).then(data => {
            activeCount.textContent = data.active_count;
            maxCount.textContent = data.max_parallel;
            swarmBadge.textContent = data.active_count;
            renderAgentGrid(data.agents);
        }).catch(() => { });

        // Completed
        fetch('/api/todos?status=completed').then(r => r.json()).then(todos => {
            completedCount.textContent = todos.length;
            if (!todos.length) {
                completedList.innerHTML = '<div class="panel-empty">No completed tasks yet.</div>';
                return;
            }
            completedList.innerHTML = todos.slice(0, 10).map(t => `
                <div class="agent-card completed">
                    <div class="agent-card-header">
                        <span class="agent-label">
                            <span class="agent-status-dot"></span>
                            Todo #${t.id}
                        </span>
                        <span class="agent-tag cat">${t.category || 'other'}</span>
                    </div>
                    <div class="agent-task">${esc(t.task)}</div>
                    <div class="agent-actions">
                        <button onclick="window._viewSandbox(${t.id})">📁 View Files</button>
                        <button class="btn-approve" onclick="window._approveTodo(${t.id})">✓ Approve</button>
                    </div>
                </div>
            `).join('');
        }).catch(() => { });
    }

    // ── Refresh Todos ──
    function refreshTodos() {
        fetch('/api/todos').then(r => r.json()).then(todos => {
            todosBadge.textContent = todos.filter(t => t.status === 'pending').length;
            if (!todos.length) {
                todoQueue.innerHTML = '<div class="panel-empty">No todos yet. Start a voice session to extract tasks.</div>';
                return;
            }
            todoQueue.innerHTML = todos.map(t => {
                const priClass = t.priority >= 8 ? 'high' : t.priority >= 5 ? 'med' : 'low';
                const showActions = t.status === 'pending' || t.status === 'completed';
                return `
                    <div class="todo-card">
                        <span class="todo-card-pri ${priClass}">P${t.priority}</span>
                        <div class="todo-card-body">
                            <div class="todo-card-task">${esc(t.task)}</div>
                            <div class="todo-card-meta">${t.category || 'other'} • ${t.created_at || ''}</div>
                        </div>
                        <span class="todo-card-status ${t.status}">${t.status}</span>
                        ${showActions ? `
                            <div class="todo-card-actions">
                                ${t.status === 'pending' ? `<button class="spawn-btn" onclick="window._spawnAgent(${t.id})">⚡ Run</button>` : ''}
                                <button class="approve-btn" onclick="window._approveTodo(${t.id})">✓</button>
                                <button class="reject-btn" onclick="window._rejectTodo(${t.id})">✗</button>
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
        }).catch(() => { });
    }

    // ── Global actions ──
    window._viewSandbox = async function (todoId) {
        modalTitle.textContent = `Sandbox: Todo #${todoId}`;
        modalBody.innerHTML = '<div class="panel-empty">Loading...</div>';
        sandboxModal.classList.remove('hidden');

        try {
            const files = await fetch(`/api/swarm/sandbox/${todoId}/files`).then(r => {
                if (!r.ok) throw new Error('not found');
                return r.json();
            });
            modalBody.innerHTML = files.map(f => `
                <div class="file-list-item" onclick="window._viewFile(${todoId}, '${esc(f.name)}')">
                    <span class="file-name">📄 ${esc(f.name)}</span>
                    <span class="file-size">${formatSize(f.size)}</span>
                </div>
            `).join('');
        } catch {
            modalBody.innerHTML = '<div class="panel-empty">Sandbox not found or no files.</div>';
        }
    };

    window._viewFile = async function (todoId, path) {
        try {
            const data = await fetch(`/api/swarm/sandbox/${todoId}/file?path=${encodeURIComponent(path)}`).then(r => r.json());
            modalBody.innerHTML = `
                <button class="btn-ghost" onclick="window._viewSandbox(${todoId})" style="margin-bottom:10px;width:auto;padding:4px 12px;font-size:0.7rem;">← Back</button>
                <h4 style="font-size:0.78rem;color:var(--accent);margin-bottom:8px;">${esc(path)}</h4>
                <div class="file-content-view">${esc(data.content)}</div>
            `;
        } catch {
            modalBody.innerHTML = '<div class="panel-empty">Failed to load file.</div>';
        }
    };

    window._approveTodo = async function (todoId) {
        await fetch(`/api/todos/${todoId}/approve`, { method: 'POST' });
        refreshSwarm();
        refreshTodos();
    };

    window._rejectTodo = async function (todoId) {
        await fetch(`/api/todos/${todoId}/reject`, { method: 'POST' });
        refreshSwarm();
        refreshTodos();
    };

    window._spawnAgent = async function (todoId) {
        await fetch(`/api/todos/${todoId}/spawn`, { method: 'POST' });
        switchTab('swarm');
        refreshSwarm();
    };

    function killAll() {
        if (confirm('Kill all active agents?')) {
            fetch('/api/swarm/kill-all', { method: 'POST' }).then(() => refreshSwarm());
        }
    }

    // ══════════════════════════════════════════
    //  LISTEN TAB — Voice capture (unchanged)
    // ══════════════════════════════════════════

    async function toggleRecording() {
        if (isRecording) stopRecording(); else await startRecording();
    }

    async function startRecording() {
        try {
            audioStream = await navigator.mediaDevices.getUserMedia({
                audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
            });
            setupVisualizer(audioStream);

            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${proto}//${location.host}/ws/audio`);
            ws.onopen = () => { agentState.textContent = 'Listening'; };
            ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
            ws.onerror = (e) => console.error('WS error:', e);
            ws.onclose = () => { agentState.textContent = 'Disconnected'; };

            let mime = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mime)) mime = 'audio/webm';
            if (!MediaRecorder.isTypeSupported(mime)) mime = '';

            mediaRecorder = new MediaRecorder(audioStream, mime ? { mimeType: mime } : {});
            mediaRecorder.ondataavailable = async (e) => {
                if (e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    const wav = await toWav(e.data);
                    ws.send(wav);
                }
            };
            mediaRecorder.start(CHUNK_INTERVAL_MS);

            isRecording = true;
            chunkCount = 0; todoCount = 0; allTranscripts = []; serverSummary = null;
            document.body.classList.add('recording');
            micIcon.classList.add('hidden');
            stopIcon.classList.remove('hidden');
            heroTitle.textContent = 'Listening...';
            heroSub.textContent = 'Speak naturally — Shadow Core is analyzing in real-time.';
            statusPill.classList.add('active');
            statusText.textContent = 'Recording';
            timer.classList.remove('hidden');
            liveGrid.classList.remove('hidden');
            summarySection.classList.add('hidden');
            transcriptFeed.innerHTML = '<div class="panel-empty">Listening...</div>';
            analysisFeed.innerHTML = '<div class="panel-empty">Agent analyzing...</div>';
            chunkBadge.textContent = '0';
            todoBadge.textContent = '0 todos';

            startTime = Date.now();
            timerInterval = setInterval(updateTimer, 1000);
        } catch (err) {
            console.error('Failed:', err);
            alert('Microphone access denied.');
        }
    }

    function stopRecording() {
        isRecording = false;
        if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
        if (audioStream) { audioStream.getTracks().forEach(t => t.stop()); audioStream = null; }
        if (ws) { ws.close(); ws = null; }
        if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
        if (vizRAF) { cancelAnimationFrame(vizRAF); vizRAF = null; }

        document.body.classList.remove('recording');
        micIcon.classList.remove('hidden');
        stopIcon.classList.add('hidden');
        heroTitle.textContent = 'Session Complete';
        heroSub.textContent = 'Shadow Core has analyzed your session.';
        statusPill.classList.remove('active');
        statusText.textContent = 'Idle';
        agentState.textContent = 'Ready';
        timer.classList.add('hidden');
        showSummary();
    }

    function handleMessage(msg) {
        switch (msg.type) {
            case 'session_started':
                agentState.textContent = 'Analyzing';
                break;
            case 'transcript':
                chunkCount = msg.chunk || chunkCount + 1;
                allTranscripts.push(msg.text);
                addTranscript(msg);
                chunkBadge.textContent = String(chunkCount);
                break;
            case 'analysis':
                addAnalysis(msg);
                break;
            case 'todo':
                todoCount++;
                addTodo(msg);
                todoBadge.textContent = `${todoCount} todo${todoCount !== 1 ? 's' : ''}`;
                todosBadge.textContent = String(parseInt(todosBadge.textContent || '0') + 1);
                break;
            case 'session_ended':
                serverSummary = msg;
                break;
            case 'error':
                console.error('Server:', msg.message);
                break;
        }
    }

    function addTranscript(msg) {
        clearEmpty(transcriptFeed);
        const time = new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const div = document.createElement('div');
        div.className = 't-item';
        div.innerHTML = `
            <div class="t-meta">
                <span class="t-time">${time}</span>
                <span class="t-chunk">#${msg.chunk}</span>
            </div>
            <div class="t-text">${esc(msg.text)}</div>
        `;
        transcriptFeed.appendChild(div);
        transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
    }

    function addAnalysis(msg) {
        clearEmpty(analysisFeed);
        const div = document.createElement('div');
        div.className = `a-item intent-${msg.intent}`;
        div.innerHTML = `
            <div class="a-header">
                <span class="a-intent ${msg.intent}">${msg.intent}</span>
                <span class="a-priority">P${msg.priority}/10 • ${Math.round((msg.confidence || 0) * 100)}%</span>
            </div>
            <div class="a-summary">${esc(msg.summary || '')}</div>
        `;
        analysisFeed.appendChild(div);
        analysisFeed.scrollTop = analysisFeed.scrollHeight;
    }

    function addTodo(msg) {
        const div = document.createElement('div');
        div.className = 'todo-item';
        div.innerHTML = `
            <span class="todo-icon">📋</span>
            <div><div class="todo-text">${esc(msg.task)}</div><span class="todo-cat">${msg.category || 'other'} • P${msg.priority}</span></div>
        `;
        analysisFeed.appendChild(div);
        analysisFeed.scrollTop = analysisFeed.scrollHeight;
    }

    function showSummary() {
        liveGrid.classList.add('hidden');
        summarySection.classList.remove('hidden');
        const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
        const m = Math.floor(elapsed / 60), s = elapsed % 60;
        const full = allTranscripts.join(' ');
        const wc = full ? full.split(/\s+/).length : 0;
        const summary = serverSummary?.summary || full || 'No speech detected.';

        summaryCard.innerHTML = `
            <div class="summary-stats">
                <div class="stat-box"><div class="stat-value">${m}:${String(s).padStart(2, '0')}</div><div class="stat-label">Duration</div></div>
                <div class="stat-box"><div class="stat-value">${wc}</div><div class="stat-label">Words</div></div>
                <div class="stat-box"><div class="stat-value">${chunkCount}</div><div class="stat-label">Chunks</div></div>
                <div class="stat-box"><div class="stat-value">${todoCount}</div><div class="stat-label">Todos</div></div>
            </div>
            <div class="summary-text">${esc(summary)}</div>
            ${full ? `<div class="summary-transcript"><h4>Full Transcript</h4><p>${esc(full)}</p></div>` : ''}
        `;

        // Refresh todos tab
        refreshTodos();
    }

    function resetToReady() {
        heroTitle.textContent = 'Start Shadow Listening';
        heroSub.textContent = 'Everything you say is captured, analyzed, and acted upon autonomously.';
        liveGrid.classList.add('hidden');
        summarySection.classList.add('hidden');
        transcriptFeed.innerHTML = '';
        analysisFeed.innerHTML = '';
        chunkCount = 0; todoCount = 0; allTranscripts = []; serverSummary = null;
    }

    function updateTimer() {
        if (!startTime) return;
        const e = Math.round((Date.now() - startTime) / 1000);
        timerText.textContent = `${String(Math.floor(e / 60)).padStart(2, '0')}:${String(e % 60).padStart(2, '0')}`;
    }

    // ── Visualizer ──
    function setupVisualizer(stream) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        audioContext.createMediaStreamSource(stream).connect(analyser);
        analyser.fftSize = 256;
        const ctx = vizCanvas.getContext('2d');
        const buf = new Uint8Array(analyser.frequencyBinCount);

        function draw() {
            vizRAF = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(buf);
            const w = vizCanvas.width, h = vizCanvas.height, cx = w / 2, cy = h / 2, r = 85;
            ctx.clearRect(0, 0, w, h);
            const bars = 64, step = Math.floor(buf.length / bars);
            for (let i = 0; i < bars; i++) {
                const v = buf[i * step] / 255;
                const a = (i / bars) * Math.PI * 2 - Math.PI / 2;
                const len = 4 + v * 26;
                ctx.beginPath();
                ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
                ctx.lineTo(cx + Math.cos(a) * (r + len), cy + Math.sin(a) * (r + len));
                ctx.strokeStyle = `rgba(6, 214, 160, ${0.25 + v * 0.75})`;
                ctx.lineWidth = 2;
                ctx.lineCap = 'round';
                ctx.stroke();
            }
        }
        draw();
    }

    // ── WAV conversion ──
    async function toWav(blob) {
        try {
            const ctx = new OfflineAudioContext(1, 16000 * 15, 16000);
            const ab = await blob.arrayBuffer();
            const audio = await ctx.decodeAudioData(ab);
            const pcm = audio.getChannelData(0);
            const len = pcm.length;
            const wav = new ArrayBuffer(44 + len * 2);
            const v = new DataView(wav);
            str(v, 0, 'RIFF'); v.setUint32(4, 36 + len * 2, true);
            str(v, 8, 'WAVE'); str(v, 12, 'fmt ');
            v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
            v.setUint32(24, 16000, true); v.setUint32(28, 32000, true);
            v.setUint16(32, 2, true); v.setUint16(34, 16, true);
            str(v, 36, 'data'); v.setUint32(40, len * 2, true);
            let off = 44;
            for (let i = 0; i < len; i++) {
                const s = Math.max(-1, Math.min(1, pcm[i]));
                v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                off += 2;
            }
            return new Blob([wav], { type: 'audio/wav' });
        } catch { return blob; }
    }
    function str(v, off, s) { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)); }

    // ── History ──
    function openHistory() {
        fetch('/api/sessions').then(r => r.json()).then(sessions => {
            if (!sessions.length) {
                historyList.innerHTML = '<div class="panel-empty">No sessions yet.</div>';
            } else {
                historyList.innerHTML = sessions.map(s => {
                    const t = new Date(s.started_at).toLocaleString();
                    const d = s.duration || 0;
                    return `
                        <div class="h-item">
                            <div class="h-header">
                                <span class="h-time">${t}</span>
                                <span class="h-dur">${Math.floor(d / 60)}m ${d % 60}s</span>
                            </div>
                            <div class="h-text">${esc((s.summary || 'No summary').substring(0, 150))}...</div>
                        </div>
                    `;
                }).join('');
            }
        }).catch(() => { historyList.innerHTML = '<div class="panel-empty">Failed to load.</div>'; });
        historyPanel.classList.add('open');
        overlay.classList.remove('hidden');
    }
    function closeHistoryPanel() {
        historyPanel.classList.remove('open');
        overlay.classList.add('hidden');
    }

    // ── Helpers ──
    function clearEmpty(el) { const e = el.querySelector('.panel-empty'); if (e) e.remove(); }
    function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
    function formatSize(b) {
        if (b < 1024) return b + ' B';
        if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
        return (b / 1024 / 1024).toFixed(1) + ' MB';
    }
})();
