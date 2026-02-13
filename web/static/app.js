/* ============================================
   Nano-AGI — Vercel AI SDK Frontend Logic
   Smooth Voice Pipeline + 3 Full Pages
   ============================================ */

(function () {
    'use strict';

    // ── DOM refs ──
    const micBtn = document.getElementById('micBtn');
    const micIcon = document.getElementById('micIcon');
    const stopIcon = document.getElementById('stopIcon');
    const micText = document.getElementById('micText');
    const timer = document.getElementById('timer');
    const feedMessages = document.getElementById('feedMessages');
    const emptyState = document.getElementById('emptyState');
    const agentGrid = document.getElementById('agentGrid');
    const todoQueue = document.getElementById('todoQueue');
    const killAllBtn = document.getElementById('killAllBtn');
    const sandboxModal = document.getElementById('sandboxModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const closeModal = document.getElementById('closeModal');
    const tabNav = document.getElementById('tabNav');
    const vizCanvas = document.getElementById('vizCanvas');
    const statusDot = document.getElementById('statusDot');
    const statusLabel = document.getElementById('statusLabel');

    // Swarm stats
    const statActive = document.getElementById('statActive');
    const statPending = document.getElementById('statPending');
    const statCompleted = document.getElementById('statCompleted');

    // Kanban columns
    const pendingCol = document.getElementById('pendingCol');
    const activeCol = document.getElementById('activeCol');
    const completedCol = document.getElementById('completedCol');
    const pendingCount = document.getElementById('pendingCount');
    const activeCount = document.getElementById('activeCount');
    const completedCount = document.getElementById('completedCount');
    const taskCount = document.getElementById('taskCount');

    // ── State ──
    let isRecording = false;
    let mediaRecorder = null;
    let audioStream = null;
    let ws = null;
    let swarmWs = null;
    let timerInterval = null;
    let startTime = null;
    let audioContext = null;
    let analyser = null;
    let vizRAF = null;
    let currentTab = 'listen';

    // ── Voice Pipeline Config ──
    // Overlap strategy: record 10s chunks, send with 3s overlap buffer
    // This prevents cutting words at chunk boundaries
    const CHUNK_INTERVAL_MS = 10000;  // 10s chunks (longer = more context)
    let prevChunkTail = '';           // Last ~3 words of previous chunk for dedup

    // ── Init ──
    micBtn.addEventListener('click', toggleRecording);
    killAllBtn.addEventListener('click', killAll);
    closeModal.addEventListener('click', () => sandboxModal.classList.add('hidden'));

    tabNav.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-trigger');
        if (!btn || !btn.dataset.tab) return;
        switchTab(btn.dataset.tab);
    });

    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('.tab-trigger').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
        document.querySelectorAll('.tab-content').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));

        if (tab === 'swarm') refreshSwarm();
        if (tab === 'todos') refreshTodos();
    }

    connectSwarmWs();
    refreshTodos();

    // ══════════════════════════════════════════════
    //  SWARM WEBSOCKET
    // ══════════════════════════════════════════════

    function connectSwarmWs() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        swarmWs = new WebSocket(`${proto}//${location.host}/ws/swarm`);
        swarmWs.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'swarm_update') {
                // Always update stats
                const sw = data.swarm;
                if (statActive) statActive.textContent = sw.active_count || 0;
                if (statPending) statPending.textContent = data.pending_count || 0;
                if (statCompleted) statCompleted.textContent = data.completed_count || 0;

                if (currentTab === 'swarm') renderAgentGrid(sw.agents);
            }
        };
        swarmWs.onclose = () => setTimeout(connectSwarmWs, 5000);
    }

    // ══════════════════════════════════════════════
    //  CHAT PAGE — Feed Rendering (Vercel Style)
    // ══════════════════════════════════════════════

    function handleMessage(msg) {
        emptyState.classList.add('hidden');

        if (msg.type === 'transcript') {
            // Deduplicate overlapping text from chunk boundaries
            const cleaned = deduplicateOverlap(msg.text);
            if (cleaned.length > 3) {
                appendChatBubble(cleaned);
            }
        }

        if (msg.type === 'analysis') {
            appendToolBlock(
                'Shadow Analysis',
                `[${(msg.intent || 'info').toUpperCase()}] ${msg.summary}`,
                msg.intent || 'INFO',
                msg.priority || 0
            );
        }

        if (msg.type === 'todo') {
            appendToolBlock(
                'Task Extracted',
                msg.task,
                'EXEC',
                msg.priority || 5
            );
            refreshTodos();
        }

        if (msg.type === 'agent_spawned') {
            appendAgentProgress(msg.todo_id, msg.task);
        }

        if (msg.type === 'agent_result') {
            resolveAgentProgress(msg.todo_id, msg.task, msg.result, msg.status);
            refreshTodos();
        }
    }

    // ── Agent Progress Card (animated "Working on it…") ──

    function appendAgentProgress(todoId, task) {
        const div = document.createElement('div');
        div.className = 'activity-card agent-progress';
        div.id = `agent-progress-${todoId}`;
        const ts = timeStr();
        div.innerHTML = `
            <div class="activity-header" style="color: var(--blue);">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                Shadow Agent · ${ts}
            </div>
            <div class="agent-working-card">
                <div class="agent-working-header">
                    <span class="agent-pulse"></span>
                    <span>Working on it…</span>
                </div>
                <div class="agent-working-task">${esc(task)}</div>
                <div class="agent-working-dots"><span>●</span><span>●</span><span>●</span></div>
            </div>
        `;
        feedMessages.appendChild(div);
        scrollToBottom();
    }

    function resolveAgentProgress(todoId, task, result, status) {
        // Remove progress card if exists
        const progress = document.getElementById(`agent-progress-${todoId}`);
        if (progress) progress.remove();

        // Insert solution card
        const div = document.createElement('div');
        div.className = 'activity-card';
        const ts = timeStr();
        const statusBadge = status === 'completed' ? '✅' : status === 'timeout' ? '⏱️' : '❌';
        const rendered = renderMarkdown(result || 'No result returned.');
        div.innerHTML = `
            <div class="activity-header" style="color: var(--green, #10b981);">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                Shadow Agent Solution · ${ts}
            </div>
            <div class="agent-result-card">
                <div class="agent-result-header">
                    <span>${statusBadge} ${esc(task)}</span>
                </div>
                <div class="agent-result-body">${rendered}</div>
            </div>
        `;
        feedMessages.appendChild(div);
        scrollToBottom();
    }

    function renderMarkdown(text) {
        // Lightweight markdown → HTML for solution display
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/^### (.+)$/gm, '<h4 style="margin: 0.75rem 0 0.25rem;">$1</h4>')
            .replace(/^## (.+)$/gm, '<h3 style="margin: 0.75rem 0 0.25rem;">$1</h3>')
            .replace(/^# (.+)$/gm, '<h2 style="margin: 0.75rem 0 0.25rem;">$1</h2>')
            .replace(/^- (.+)$/gm, '<li style="margin-left: 1rem;">$1</li>')
            .replace(/^(\d+)\. (.+)$/gm, '<li style="margin-left: 1rem;">$2</li>')
            .replace(/\n/g, '<br>');
    }

    function deduplicateOverlap(text) {
        if (!prevChunkTail || !text) {
            prevChunkTail = getLastWords(text, 5);
            return text;
        }

        // Check if beginning of new text overlaps with end of previous
        const tailWords = prevChunkTail.split(/\s+/);
        const newWords = text.split(/\s+/);

        let overlapLen = 0;
        for (let tryLen = Math.min(tailWords.length, 6); tryLen >= 2; tryLen--) {
            const tailSlice = tailWords.slice(-tryLen).join(' ').toLowerCase();
            const newSlice = newWords.slice(0, tryLen).join(' ').toLowerCase();
            if (tailSlice === newSlice) {
                overlapLen = tryLen;
                break;
            }
        }

        const dedupedText = overlapLen > 0
            ? newWords.slice(overlapLen).join(' ')
            : text;

        prevChunkTail = getLastWords(text, 5);
        return dedupedText;
    }

    function getLastWords(text, n) {
        const words = text.trim().split(/\s+/);
        return words.slice(-n).join(' ');
    }

    function appendChatBubble(text) {
        const div = document.createElement('div');
        div.className = 'activity-card';
        const ts = timeStr();
        div.innerHTML = `
            <div class="activity-header">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
                Transcription · ${ts}
            </div>
            <div class="transcript-bubble">${esc(text)}</div>
        `;
        feedMessages.appendChild(div);
        scrollToBottom();
    }

    function appendToolBlock(title, content, badge, priority) {
        const div = document.createElement('div');
        div.className = 'activity-card';
        const ts = timeStr();
        const color = badge === 'EXEC' ? 'var(--blue)' : badge === 'urgent' ? 'var(--red)' : 'var(--muted-foreground)';
        div.innerHTML = `
            <div class="activity-header">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.5"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                ${title} · ${ts}
            </div>
            <div class="tool-block">
                <div class="tool-header">
                    <div class="tool-title">${esc(title)}</div>
                    <span class="tool-badge">${badge}</span>
                </div>
                <div class="tool-content">${esc(content)}</div>
            </div>
        `;
        feedMessages.appendChild(div);
        scrollToBottom();
    }

    // ══════════════════════════════════════════════
    //  SWARM PAGE
    // ══════════════════════════════════════════════

    function renderAgentGrid(agents) {
        if (!agents || !agents.length) {
            agentGrid.innerHTML = '<div class="empty-placeholder">No agents deployed. Speak a task to spawn one.</div>';
            return;
        }
        agentGrid.innerHTML = agents.map(a => {
            const isRunning = a.running;
            const statusClass = isRunning ? 'running' : 'done';
            const dotClass = isRunning ? 'live' : 'done';
            const statusText = isRunning ? 'Processing' : 'Completed';
            return `
                <div class="agent-node ${statusClass}">
                    <div class="agent-node-header">
                        <span class="agent-node-id">agent-${a.todo_id}</span>
                        <div class="agent-node-status">
                            <span class="status-dot ${dotClass}"></span>
                            ${statusText}
                        </div>
                    </div>
                    <div class="agent-node-task">${esc(a.task)}</div>
                    <div class="agent-node-meta">
                        <span class="meta-tag">${a.category}</span>
                        <span class="meta-tag">P${a.priority}</span>
                    </div>
                    <div class="agent-node-actions">
                        <button class="btn-node" onclick="window._viewSandbox(${a.todo_id})">View files</button>
                        ${!isRunning ? `<button class="btn-node primary" onclick="window._approveTodo(${a.todo_id})">Approve</button>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    function refreshSwarm() {
        fetch('/api/swarm/status')
            .then(r => r.json())
            .then(data => {
                renderAgentGrid(data.agents);
                if (statActive) statActive.textContent = data.active_count || 0;
            })
            .catch(() => { });
    }

    // ══════════════════════════════════════════════
    //  TASKS PAGE — Kanban Board
    // ══════════════════════════════════════════════

    function refreshTodos() {
        fetch('/api/todos')
            .then(r => r.json())
            .then(todos => renderKanban(todos))
            .catch(() => { });
    }

    function renderKanban(todos) {
        if (!todos || !todos.length) {
            if (pendingCol) pendingCol.innerHTML = '<div class="empty-placeholder" style="padding: 1rem;">No tasks</div>';
            if (activeCol) activeCol.innerHTML = '';
            if (completedCol) completedCol.innerHTML = '';
            if (taskCount) taskCount.textContent = '0 tasks';
            return;
        }

        const pending = todos.filter(t => t.status === 'pending');
        const active = todos.filter(t => t.status === 'active');
        const completed = todos.filter(t => ['completed', 'approved', 'rejected'].includes(t.status));

        if (pendingCount) pendingCount.textContent = pending.length;
        if (activeCount) activeCount.textContent = active.length;
        if (completedCount) completedCount.textContent = completed.length;
        if (taskCount) taskCount.textContent = `${todos.length} tasks`;

        if (pendingCol) pendingCol.innerHTML = pending.length
            ? pending.map(t => taskCardHTML(t)).join('')
            : '<div class="empty-placeholder" style="padding: 1rem;">Queue clear</div>';

        if (activeCol) activeCol.innerHTML = active.length
            ? active.map(t => taskCardHTML(t)).join('')
            : '<div class="empty-placeholder" style="padding: 1rem;">—</div>';

        if (completedCol) completedCol.innerHTML = completed.length
            ? completed.map(t => taskCardHTML(t)).join('')
            : '<div class="empty-placeholder" style="padding: 1rem;">—</div>';
    }

    function taskCardHTML(t) {
        const pClass = t.priority >= 7 ? 'p-high' : t.priority >= 4 ? 'p-medium' : 'p-low';
        const actions = [];
        if (t.status === 'pending') {
            actions.push(`<button class="action-spawn" onclick="window._spawnAgent(${t.id})">Spawn agent</button>`);
            actions.push(`<button class="action-approve" onclick="window._approveTodo(${t.id})">Approve</button>`);
            actions.push(`<button class="action-reject" onclick="window._rejectTodo(${t.id})">Reject</button>`);
        }
        return `
            <div class="task-card">
                <div class="task-card-top">
                    <span class="priority-dot ${pClass}"></span>
                    <span class="meta-tag">${t.category}</span>
                    <span class="meta-tag">P${t.priority}</span>
                </div>
                <div class="task-card-task">${esc(t.task)}</div>
                ${t.deadline ? `<div class="task-card-meta">Due: ${esc(t.deadline)}</div>` : ''}
                ${actions.length ? `<div class="task-card-actions">${actions.join('')}</div>` : ''}
            </div>
        `;
    }

    // ══════════════════════════════════════════════
    //  MODAL ACTIONS
    // ══════════════════════════════════════════════

    window._viewSandbox = async function (todoId) {
        modalTitle.textContent = `Sandbox · agent-${todoId}`;
        modalBody.innerHTML = '<div class="empty-placeholder">Loading files…</div>';
        sandboxModal.classList.remove('hidden');
        try {
            const files = await fetch(`/api/swarm/sandbox/${todoId}/files`).then(r => r.json());
            if (!files.length) {
                modalBody.innerHTML = '<div class="empty-placeholder">No artifacts generated yet.</div>';
                return;
            }
            modalBody.innerHTML = files.map(f => `
                <div class="file-list-item" onclick="window._viewFile(${todoId}, '${esc(f.name)}')">
                    <span style="font-size: 0.8125rem; font-weight: 500;">${esc(f.name)}</span>
                    <span style="font-size: 0.6875rem; color: var(--muted-foreground);">${(f.size / 1024).toFixed(1)} KB</span>
                </div>
            `).join('');
        } catch {
            modalBody.innerHTML = '<div class="empty-placeholder">Could not access sandbox.</div>';
        }
    };

    window._viewFile = async function (todoId, path) {
        try {
            const data = await fetch(`/api/swarm/sandbox/${todoId}/file?path=${encodeURIComponent(path)}`).then(r => r.json());
            modalBody.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 1rem;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-size: 0.8125rem; font-family: var(--font-mono);">${esc(path)}</span>
                        <button class="btn-node" onclick="window._viewSandbox(${todoId})">← Back</button>
                    </div>
                    <pre style="background: var(--muted); padding: 1rem; border-radius: 8px; font-size: 0.75rem; font-family: var(--font-mono); overflow: auto; border: 1px solid var(--border); line-height: 1.6; max-height: 60vh; white-space: pre-wrap;">${esc(data.content)}</pre>
                </div>
            `;
        } catch {
            modalBody.innerHTML = '<div class="empty-placeholder">Error reading file.</div>';
        }
    };

    window._approveTodo = async (id) => {
        await fetch(`/api/todos/${id}/approve`, { method: 'POST' });
        refreshSwarm(); refreshTodos();
    };

    window._rejectTodo = async (id) => {
        await fetch(`/api/todos/${id}/reject`, { method: 'POST' });
        refreshTodos();
    };

    window._spawnAgent = async (id) => {
        await fetch(`/api/todos/${id}/spawn`, { method: 'POST' });
        switchTab('swarm');
    };

    function killAll() {
        if (confirm('Terminate all swarm agents?')) {
            fetch('/api/swarm/kill-all', { method: 'POST' }).then(() => refreshSwarm());
        }
    }

    // ══════════════════════════════════════════════
    //  VOICE SESSION — Smooth Capture Pipeline
    // ══════════════════════════════════════════════

    async function toggleRecording() {
        if (isRecording) stopRecording(); else await startRecording();
    }

    async function startRecording() {
        try {
            // Request higher quality audio with noise suppression
            audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,  // Reduce background noise
                    autoGainControl: true,   // Normalize volume
                }
            });

            setupVisualizer(audioStream);

            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${proto}//${location.host}/ws/audio`);
            ws.onopen = () => {
                micText.textContent = 'Listening…';
                statusDot.style.background = '#ef4444';
                statusLabel.textContent = 'Recording';
            };
            ws.onmessage = (e) => handleMessage(JSON.parse(e.data));

            // Use timeslice for continuous streaming (no gap between chunks)
            mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });

            // Accumulating buffer for overlap
            let audioChunks = [];
            let chunkStartTime = Date.now();

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };

            // Use a recurring interval to send accumulated audio
            // This gives us precise control over chunk boundaries
            const sendInterval = setInterval(async () => {
                if (!isRecording || !ws || ws.readyState !== WebSocket.OPEN) return;
                if (!audioChunks.length) return;

                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                audioChunks = []; // Reset for next chunk

                if (blob.size < 500) return;

                try {
                    const wav = await toWav(blob);
                    ws.send(wav);
                } catch (err) {
                    console.warn('Conversion error:', err);
                }
            }, CHUNK_INTERVAL_MS);

            // Record in small slices (500ms) for smooth accumulation
            mediaRecorder.start(500);

            isRecording = true;
            micBtn.classList.add('recording');
            micIcon.classList.add('hidden');
            stopIcon.classList.remove('hidden');
            timer.classList.remove('hidden');
            startTime = Date.now();
            prevChunkTail = '';

            timerInterval = setInterval(() => {
                const e = Math.round((Date.now() - startTime) / 1000);
                timer.textContent = `${String(Math.floor(e / 60)).padStart(2, '0')}:${String(e % 60).padStart(2, '0')}`;
            }, 1000);

            // Store interval for cleanup
            micBtn._sendInterval = sendInterval;

        } catch (err) {
            console.error(err);
            alert('Microphone access is required.');
        }
    }

    function stopRecording() {
        isRecording = false;
        if (micBtn._sendInterval) clearInterval(micBtn._sendInterval);
        if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
        if (audioStream) audioStream.getTracks().forEach(t => t.stop());
        if (ws) ws.close();
        if (timerInterval) clearInterval(timerInterval);
        if (vizRAF) cancelAnimationFrame(vizRAF);

        micBtn.classList.remove('recording');
        micIcon.classList.remove('hidden');
        stopIcon.classList.add('hidden');
        timer.classList.add('hidden');
        micText.textContent = 'Session ended';
        statusDot.style.background = '#10b981';
        statusLabel.textContent = 'Online';
        setTimeout(() => { micText.textContent = 'Press to command'; }, 3000);
        refreshTodos();
    }

    // ══════════════════════════════════════════════
    //  AUDIO VISUALIZER
    // ══════════════════════════════════════════════

    function setupVisualizer(stream) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        audioContext.createMediaStreamSource(stream).connect(analyser);
        analyser.fftSize = 64;
        const ctx = vizCanvas.getContext('2d');
        const buf = new Uint8Array(analyser.frequencyBinCount);
        vizCanvas.width = 120; vizCanvas.height = 24;

        function draw() {
            vizRAF = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(buf);
            ctx.clearRect(0, 0, 120, 24);
            ctx.fillStyle = isRecording ? '#fafafa' : '#27272a';
            const barW = 4;
            let x = 0;
            for (let i = 0; i < 12; i++) {
                const h = Math.max(2, (buf[i] / 255) * 20);
                ctx.fillRect(x, 12 - h / 2, barW, h);
                x += barW + 6;
            }
        }
        draw();
    }

    // ══════════════════════════════════════════════
    //  AUDIO CONVERSION (WebM → WAV for Whisper)
    // ══════════════════════════════════════════════

    async function toWav(blob) {
        const ab = await blob.arrayBuffer();
        const audio = await new AudioContext().decodeAudioData(ab);
        const pcm = audio.getChannelData(0);

        // Resample to 16kHz if needed
        const targetRate = 16000;
        const sourceRate = audio.sampleRate;
        let samples = pcm;

        if (sourceRate !== targetRate) {
            const ratio = sourceRate / targetRate;
            const newLen = Math.round(pcm.length / ratio);
            samples = new Float32Array(newLen);
            for (let i = 0; i < newLen; i++) {
                samples[i] = pcm[Math.round(i * ratio)];
            }
        }

        // Build WAV
        const wav = new ArrayBuffer(44 + samples.length * 2);
        const v = new DataView(wav);
        const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
        w(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true);
        w(8, 'WAVE'); w(12, 'fmt '); v.setUint32(16, 16, true);
        v.setUint16(20, 1, true); v.setUint16(22, 1, true);
        v.setUint32(24, targetRate, true); v.setUint32(28, targetRate * 2, true);
        v.setUint16(32, 2, true); v.setUint16(34, 16, true);
        w(36, 'data'); v.setUint32(40, samples.length * 2, true);

        // Clamp and convert to 16-bit PCM
        for (let i = 0; i < samples.length; i++) {
            const s = Math.max(-1, Math.min(1, samples[i]));
            v.setInt16(44 + i * 2, s * 0x7FFF, true);
        }

        return new Blob([wav], { type: 'audio/wav' });
    }

    // ══════════════════════════════════════════════
    //  UTILITIES
    // ══════════════════════════════════════════════

    function scrollToBottom() {
        const vp = document.querySelector('.scroll-viewport');
        vp.scrollTop = vp.scrollHeight;
    }

    function timeStr() {
        return new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function esc(t) {
        if (!t) return '';
        const d = document.createElement('div');
        d.textContent = t;
        return d.innerHTML;
    }
})();
