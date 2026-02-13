/* ============================================
   Nano-AGI — Shadow Core Frontend
   ============================================ */

(function () {
    'use strict';

    // ── DOM refs ──
    const micBtn = document.getElementById('micBtn');
    const micIcon = document.getElementById('micIcon');
    const stopIcon = document.getElementById('stopIcon');
    const heroTitle = document.getElementById('heroTitle');
    const heroSub = document.getElementById('heroSub');
    const heroSection = document.getElementById('heroSection');
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

    // ── State ──
    let isRecording = false;
    let mediaRecorder = null;
    let audioStream = null;
    let ws = null;
    let timerInterval = null;
    let startTime = null;
    let chunkCount = 0;
    let todoCount = 0;
    let audioContext = null;
    let analyser = null;
    let vizRAF = null;
    let allTranscripts = [];
    let serverSummary = null;

    const CHUNK_INTERVAL_MS = 8000; // 8 seconds

    // ── Init ──
    micBtn.addEventListener('click', toggleRecording);
    newSessionBtn.addEventListener('click', resetToReady);
    historyBtn.addEventListener('click', openHistory);
    closeHistory.addEventListener('click', closeHistoryPanel);
    overlay.addEventListener('click', closeHistoryPanel);

    // ── Toggle ──
    async function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
            await startRecording();
        }
    }

    // ── Start ──
    async function startRecording() {
        try {
            audioStream = await navigator.mediaDevices.getUserMedia({
                audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
            });

            setupVisualizer(audioStream);

            // WebSocket
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${proto}//${location.host}/ws/audio`);
            ws.onopen = () => { agentState.textContent = 'Listening'; };
            ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
            ws.onerror = (e) => console.error('WS error:', e);
            ws.onclose = () => { agentState.textContent = 'Disconnected'; };

            // MediaRecorder
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

            // UI
            isRecording = true;
            chunkCount = 0;
            todoCount = 0;
            allTranscripts = [];
            serverSummary = null;
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
            transcriptFeed.innerHTML = '<div class="panel-empty">Listening... speak and words appear here.</div>';
            analysisFeed.innerHTML = '<div class="panel-empty">Agent analyzing in real-time...</div>';
            chunkBadge.textContent = '0';
            todoBadge.textContent = '0 todos';

            startTime = Date.now();
            timerInterval = setInterval(updateTimer, 1000);

        } catch (err) {
            console.error('Failed:', err);
            alert('Microphone access denied. Please allow and try again.');
        }
    }

    // ── Stop ──
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
        heroSub.textContent = 'Shadow Core has analyzed your voice session.';
        statusPill.classList.remove('active');
        statusText.textContent = 'Idle';
        agentState.textContent = 'Ready';
        timer.classList.add('hidden');

        showSummary();
    }

    // ── Handle server messages ──
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
                break;

            case 'heartbeat':
                chunkBadge.textContent = String(msg.chunk || chunkCount);
                break;

            case 'session_ended':
                serverSummary = msg;
                break;

            case 'error':
                console.error('Server:', msg.message);
                break;
        }
    }

    // ── Add transcript item ──
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

    // ── Add analysis item ──
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

    // ── Add todo item ──
    function addTodo(msg) {
        // Insert into analysis feed
        const div = document.createElement('div');
        div.className = 'todo-item';
        div.innerHTML = `
            <span class="todo-icon">📋</span>
            <div>
                <div class="todo-text">${esc(msg.task)}</div>
                <span class="todo-cat">${msg.category || 'other'} • P${msg.priority}</span>
            </div>
        `;
        analysisFeed.appendChild(div);
        analysisFeed.scrollTop = analysisFeed.scrollHeight;
    }

    // ── Summary ──
    function showSummary() {
        liveGrid.classList.add('hidden');
        summarySection.classList.remove('hidden');

        const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
        const m = Math.floor(elapsed / 60);
        const s = elapsed % 60;
        const full = allTranscripts.join(' ');
        const wc = full ? full.split(/\s+/).length : 0;

        const summaryText = serverSummary?.summary || (full ? full : 'No speech detected.');

        summaryCard.innerHTML = `
            <div class="summary-stats">
                <div class="stat-box">
                    <div class="stat-value">${m}:${String(s).padStart(2, '0')}</div>
                    <div class="stat-label">Duration</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${wc}</div>
                    <div class="stat-label">Words</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${chunkCount}</div>
                    <div class="stat-label">Chunks</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${todoCount}</div>
                    <div class="stat-label">Todos</div>
                </div>
            </div>
            <div class="summary-text">${esc(summaryText)}</div>
            ${full ? `
                <div class="summary-transcript">
                    <h4>Full Transcript</h4>
                    <p>${esc(full)}</p>
                </div>
            ` : ''}
        `;
    }

    // ── Reset ──
    function resetToReady() {
        heroTitle.textContent = 'Start Shadow Listening';
        heroSub.textContent = 'Everything you say is captured, analyzed, and acted upon autonomously.';
        liveGrid.classList.add('hidden');
        summarySection.classList.add('hidden');
        transcriptFeed.innerHTML = '';
        analysisFeed.innerHTML = '';
        chunkCount = 0;
        todoCount = 0;
        allTranscripts = [];
        serverSummary = null;
    }

    // ── Timer ──
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
            const w = vizCanvas.width, h = vizCanvas.height, cx = w / 2, cy = h / 2, r = 90;
            ctx.clearRect(0, 0, w, h);

            const bars = 64, step = Math.floor(buf.length / bars);
            for (let i = 0; i < bars; i++) {
                const v = buf[i * step] / 255;
                const a = (i / bars) * Math.PI * 2 - Math.PI / 2;
                const len = 4 + v * 28;
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

    // ── Convert to WAV ──
    async function toWav(blob) {
        try {
            const ctx = new OfflineAudioContext(1, 16000 * 15, 16000);
            const ab = await blob.arrayBuffer();
            const audio = await ctx.decodeAudioData(ab);
            const pcm = audio.getChannelData(0);
            const len = pcm.length;

            const wav = new ArrayBuffer(44 + len * 2);
            const v = new DataView(wav);

            str(v, 0, 'RIFF');
            v.setUint32(4, 36 + len * 2, true);
            str(v, 8, 'WAVE');
            str(v, 12, 'fmt ');
            v.setUint32(16, 16, true);
            v.setUint16(20, 1, true);
            v.setUint16(22, 1, true);
            v.setUint32(24, 16000, true);
            v.setUint32(28, 32000, true);
            v.setUint16(32, 2, true);
            v.setUint16(34, 16, true);
            str(v, 36, 'data');
            v.setUint32(40, len * 2, true);

            let off = 44;
            for (let i = 0; i < len; i++) {
                const s = Math.max(-1, Math.min(1, pcm[i]));
                v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                off += 2;
            }
            return new Blob([wav], { type: 'audio/wav' });
        } catch (e) {
            console.warn('WAV conv failed:', e);
            return blob;
        }
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
        }).catch(() => {
            historyList.innerHTML = '<div class="panel-empty">Failed to load.</div>';
        });
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

})();
