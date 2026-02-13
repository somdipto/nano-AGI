/* ============================================
   Voice Memory — Frontend Application
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
    const timer = document.getElementById('timer');
    const timerText = document.getElementById('timerText');
    const transcriptSection = document.getElementById('transcriptSection');
    const transcriptFeed = document.getElementById('transcriptFeed');
    const chunkBadge = document.getElementById('chunkBadge');
    const summarySection = document.getElementById('summarySection');
    const summaryCard = document.getElementById('summaryCard');
    const newSessionBtn = document.getElementById('newSessionBtn');
    const historyBtn = document.getElementById('historyBtn');
    const historyPanel = document.getElementById('historyPanel');
    const closeHistory = document.getElementById('closeHistory');
    const historyList = document.getElementById('historyList');
    const overlay = document.getElementById('overlay');
    const vizCanvas = document.getElementById('vizCanvas');
    const heroSection = document.getElementById('heroSection');

    // ── State ──
    let isRecording = false;
    let mediaRecorder = null;
    let audioStream = null;
    let ws = null;
    let timerInterval = null;
    let startTime = null;
    let chunkCount = 0;
    let audioContext = null;
    let analyser = null;
    let vizRAF = null;
    let allTranscripts = [];

    // Audio chunk interval (ms) — send audio every N seconds
    const CHUNK_INTERVAL_MS = 10000; // 10 seconds

    // ── Init ──
    micBtn.addEventListener('click', toggleRecording);
    newSessionBtn.addEventListener('click', resetToReady);
    historyBtn.addEventListener('click', openHistory);
    closeHistory.addEventListener('click', closeHistoryPanel);
    overlay.addEventListener('click', closeHistoryPanel);

    // ── Toggle recording ──
    async function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
            await startRecording();
        }
    }

    // ── Start recording ──
    async function startRecording() {
        try {
            // Request microphone
            audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                },
            });

            // Setup audio visualization
            setupVisualizer(audioStream);

            // Connect WebSocket
            const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${wsProtocol}//${location.host}/ws/audio`);

            ws.onopen = () => {
                console.log('🔌 WebSocket connected');
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                handleServerMessage(msg);
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
            };

            ws.onclose = () => {
                console.log('🔌 WebSocket closed');
            };

            // Setup MediaRecorder
            // Try wav first, fallback to webm
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'audio/webm';
            }
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = ''; // Let browser choose
            }

            const options = mimeType ? { mimeType } : {};
            mediaRecorder = new MediaRecorder(audioStream, options);

            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    // Convert to WAV before sending (whisper.cpp needs wav)
                    const wavBlob = await convertToWav(event.data);
                    ws.send(wavBlob);
                }
            };

            // Record in chunks
            mediaRecorder.start(CHUNK_INTERVAL_MS);

            // Update UI
            isRecording = true;
            chunkCount = 0;
            allTranscripts = [];
            document.body.classList.add('recording');
            micIcon.classList.add('hidden');
            stopIcon.classList.remove('hidden');
            heroTitle.textContent = 'Listening...';
            heroSub.textContent = 'Speak naturally. I\'m capturing everything.';
            statusPill.classList.add('active');
            statusText.textContent = 'Recording';
            timer.classList.remove('hidden');
            transcriptSection.classList.remove('hidden');
            summarySection.classList.add('hidden');
            transcriptFeed.innerHTML = '<div class="transcript-empty"><p>Listening... Speak and your words will appear here.</p></div>';
            chunkBadge.textContent = '0 chunks';

            // Start timer
            startTime = Date.now();
            timerInterval = setInterval(updateTimer, 1000);

        } catch (err) {
            console.error('Failed to start recording:', err);
            alert('Microphone access denied. Please allow microphone access and try again.');
        }
    }

    // ── Stop recording ──
    function stopRecording() {
        isRecording = false;

        // Stop MediaRecorder
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }

        // Stop audio stream
        if (audioStream) {
            audioStream.getTracks().forEach(t => t.stop());
            audioStream = null;
        }

        // Close WebSocket
        if (ws) {
            ws.close();
            ws = null;
        }

        // Stop timer
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }

        // Stop visualizer
        if (vizRAF) {
            cancelAnimationFrame(vizRAF);
            vizRAF = null;
        }

        // Update UI
        document.body.classList.remove('recording');
        micIcon.classList.remove('hidden');
        stopIcon.classList.add('hidden');
        heroTitle.textContent = 'Session Complete';
        heroSub.textContent = 'Your voice has been transcribed and stored.';
        statusPill.classList.remove('active');
        statusText.textContent = 'Ready';
        timer.classList.add('hidden');

        // Show summary
        showSummary();
    }

    // ── Handle server messages ──
    function handleServerMessage(msg) {
        switch (msg.type) {
            case 'session_started':
                console.log('📝 Session:', msg.session_id);
                break;

            case 'transcript':
                chunkCount = msg.chunk || chunkCount + 1;
                allTranscripts.push(msg);
                addTranscriptItem(msg);
                chunkBadge.textContent = `${chunkCount} chunks`;
                break;

            case 'session_ended':
                // Server-side summary (if available)
                if (msg.summary) {
                    renderSummary(msg);
                }
                break;

            case 'error':
                console.error('Server error:', msg.message);
                break;
        }
    }

    // ── Add transcript item to feed ──
    function addTranscriptItem(msg) {
        // Remove empty state
        const empty = transcriptFeed.querySelector('.transcript-empty');
        if (empty) empty.remove();

        const time = new Date(msg.timestamp).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });

        const div = document.createElement('div');
        div.className = 'transcript-item';
        div.innerHTML = `
            <div class="transcript-meta">
                <span class="transcript-time">${time}</span>
                <span class="transcript-chunk">#${msg.chunk}</span>
            </div>
            <div class="transcript-text">${escapeHtml(msg.text)}</div>
        `;

        transcriptFeed.appendChild(div);
        transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
    }

    // ── Show summary ──
    function showSummary() {
        summarySection.classList.remove('hidden');

        const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        const fullText = allTranscripts.map(t => t.text).join(' ');
        const wordCount = fullText ? fullText.split(/\s+/).length : 0;

        summaryCard.innerHTML = `
            <div class="summary-stats">
                <div class="stat-box">
                    <div class="stat-value">${minutes}:${String(seconds).padStart(2, '0')}</div>
                    <div class="stat-label">Duration</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${wordCount}</div>
                    <div class="stat-label">Words</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${allTranscripts.length}</div>
                    <div class="stat-label">Chunks</div>
                </div>
            </div>
            ${fullText ? `
                <div class="summary-full-transcript">
                    <h4>Full Transcript</h4>
                    <p>${escapeHtml(fullText)}</p>
                </div>
            ` : '<div class="summary-text">No speech was detected during this session. Try speaking louder or closer to the microphone.</div>'}
        `;
    }

    // ── Render server summary ──
    function renderSummary(msg) {
        // Update summary card with server data if available
        const existing = summaryCard.querySelector('.summary-text');
        if (existing) {
            existing.textContent = msg.summary;
        }
    }

    // ── Reset to ready state ──
    function resetToReady() {
        heroTitle.textContent = 'Tap to Start Listening';
        heroSub.textContent = 'Everything you say will be captured, transcribed, and remembered.';
        transcriptSection.classList.add('hidden');
        summarySection.classList.add('hidden');
        transcriptFeed.innerHTML = '';
        chunkCount = 0;
        allTranscripts = [];
        chunkBadge.textContent = '0 chunks';
    }

    // ── Timer ──
    function updateTimer() {
        if (!startTime) return;
        const elapsed = Math.round((Date.now() - startTime) / 1000);
        const m = Math.floor(elapsed / 60);
        const s = elapsed % 60;
        timerText.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    // ── Audio Visualizer ──
    function setupVisualizer(stream) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;

        const ctx = vizCanvas.getContext('2d');
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        function draw() {
            vizRAF = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);

            const w = vizCanvas.width;
            const h = vizCanvas.height;
            const cx = w / 2;
            const cy = h / 2;
            const radius = 110;

            ctx.clearRect(0, 0, w, h);

            // Draw circular frequency bars
            const bars = 64;
            const step = Math.floor(bufferLength / bars);

            for (let i = 0; i < bars; i++) {
                const val = dataArray[i * step] / 255;
                const angle = (i / bars) * Math.PI * 2 - Math.PI / 2;
                const barLen = 6 + val * 30;

                const x1 = cx + Math.cos(angle) * radius;
                const y1 = cy + Math.sin(angle) * radius;
                const x2 = cx + Math.cos(angle) * (radius + barLen);
                const y2 = cy + Math.sin(angle) * (radius + barLen);

                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.strokeStyle = `rgba(167, 139, 250, ${0.3 + val * 0.7})`;
                ctx.lineWidth = 2;
                ctx.lineCap = 'round';
                ctx.stroke();
            }
        }

        draw();
    }

    // ── Convert WebM to WAV ──
    async function convertToWav(blob) {
        try {
            const ctx = new OfflineAudioContext(1, 16000 * 15, 16000);
            const arrayBuffer = await blob.arrayBuffer();
            const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

            // Get PCM data
            const pcmData = audioBuffer.getChannelData(0);
            const length = pcmData.length;

            // Build WAV
            const wavBuffer = new ArrayBuffer(44 + length * 2);
            const view = new DataView(wavBuffer);

            // WAV header
            writeString(view, 0, 'RIFF');
            view.setUint32(4, 36 + length * 2, true);
            writeString(view, 8, 'WAVE');
            writeString(view, 12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);        // PCM
            view.setUint16(22, 1, true);        // mono
            view.setUint32(24, 16000, true);    // sample rate
            view.setUint32(28, 32000, true);    // byte rate
            view.setUint16(32, 2, true);        // block align
            view.setUint16(34, 16, true);       // bits per sample
            writeString(view, 36, 'data');
            view.setUint32(40, length * 2, true);

            // PCM data
            let offset = 44;
            for (let i = 0; i < length; i++) {
                const s = Math.max(-1, Math.min(1, pcmData[i]));
                view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                offset += 2;
            }

            return new Blob([wavBuffer], { type: 'audio/wav' });

        } catch (err) {
            console.warn('WAV conversion failed, sending raw:', err);
            return blob;
        }
    }

    function writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    // ── History panel ──
    function openHistory() {
        // Fetch sessions from API
        fetch('/api/sessions')
            .then(r => r.json())
            .then(sessions => {
                if (!sessions.length) {
                    historyList.innerHTML = '<div class="empty-state">No sessions yet. Start recording!</div>';
                } else {
                    historyList.innerHTML = sessions.map(s => {
                        const time = new Date(s.started_at).toLocaleString();
                        const dur = s.duration || 0;
                        const m = Math.floor(dur / 60);
                        const sec = dur % 60;
                        return `
                            <div class="history-item" data-id="${s.id}">
                                <div class="history-item-header">
                                    <span class="history-item-time">${time}</span>
                                    <span class="history-item-duration">${m}m ${sec}s</span>
                                </div>
                                <div class="history-item-text">
                                    ${s.transcript_count} chunks • ${escapeHtml((s.summary || 'No summary').substring(0, 120))}...
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            })
            .catch(() => {
                historyList.innerHTML = '<div class="empty-state">Failed to load sessions.</div>';
            });

        historyPanel.classList.add('open');
        overlay.classList.remove('hidden');
    }

    function closeHistoryPanel() {
        historyPanel.classList.remove('open');
        overlay.classList.add('hidden');
    }

    // ── Utilities ──
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

})();
