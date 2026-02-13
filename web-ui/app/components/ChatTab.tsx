"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface ChatMessage {
    id: string;
    type: "shadow" | "user" | "task_auto" | "task_suggest" | "agent_spawned" | "agent_result" | "system";
    text: string;
    meta?: Record<string, unknown>;
    time: Date;
}

interface ChatTabProps {
    serverUrl: string;
}

export default function ChatTab({ serverUrl }: ChatTabProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isListening, setIsListening] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const feedRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const mediaRef = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const prevTailRef = useRef<string>("");
    const mountedRef = useRef(true);

    const addMsg = useCallback((msg: ChatMessage) => {
        setMessages((prev) => [...prev.slice(-150), msg]);
    }, []);

    const scrollBottom = useCallback(() => {
        setTimeout(() => feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" }), 50);
    }, []);

    useEffect(scrollBottom, [messages, scrollBottom]);

    // WebSocket
    useEffect(() => {
        const connect = () => {
            const ws = new WebSocket(`${serverUrl.replace("http", "ws")}/ws/audio`);
            wsRef.current = ws;

            ws.onmessage = (e) => {
                const d = JSON.parse(e.data);

                if (d.type === "shadow_message") {
                    addMsg({
                        id: crypto.randomUUID(), type: "shadow", text: d.text,
                        meta: { suggestion: d.suggestion, task_data: d.task_data },
                        time: new Date(),
                    });
                }

                if (d.type === "transcript") {
                    const cleaned = dedup(d.text, prevTailRef);
                    if (cleaned.length > 3) {
                        addMsg({ id: crypto.randomUUID(), type: "user", text: cleaned, time: new Date() });
                    }
                }

                if (d.type === "todo_auto") {
                    addMsg({
                        id: crypto.randomUUID(), type: "task_auto",
                        text: d.task, meta: { todoId: d.id, priority: d.priority, category: d.category },
                        time: new Date(),
                    });
                }

                if (d.type === "agent_spawned") {
                    addMsg({
                        id: crypto.randomUUID(), type: "agent_spawned",
                        text: d.task, meta: { todoId: d.todo_id, slotId: d.slot_id },
                        time: new Date(),
                    });
                }

                if (d.type === "agent_result") {
                    setMessages((prev) =>
                        prev.filter((m) => !(m.type === "agent_spawned" && (m.meta?.todoId as number) === d.todo_id))
                    );
                    addMsg({
                        id: crypto.randomUUID(), type: "agent_result",
                        text: d.result || "No result.",
                        meta: { todoId: d.todo_id, slotId: d.slot_id, task: d.task, status: d.status },
                        time: new Date(),
                    });
                }
            };

            ws.onclose = () => setTimeout(connect, 3000);
        };

        connect();
        return () => wsRef.current?.close();
    }, [serverUrl, addMsg]);

    // Auto-start voice on mount — always listening
    const startListening = useCallback(async () => {
        if (mediaRef.current) return; // Already running

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { noiseSuppression: true, autoGainControl: true, echoCancellation: true },
            });
            streamRef.current = stream;

            const mr = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
            mediaRef.current = mr;

            let chunks: Blob[] = [];
            const INTERVAL = 8000;

            mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

            timerRef.current = setInterval(() => {
                if (!chunks.length || isMuted) return;
                const blob = new Blob(chunks, { type: "audio/webm" });
                chunks = [];
                blobToWav(blob).then((wav) => {
                    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(wav);
                });
            }, INTERVAL);

            mr.onstop = () => {
                if (timerRef.current) clearInterval(timerRef.current);
                if (chunks.length && !isMuted) {
                    const blob = new Blob(chunks, { type: "audio/webm" });
                    blobToWav(blob).then((wav) => {
                        if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(wav);
                    });
                }
                stream.getTracks().forEach((t) => t.stop());
                mediaRef.current = null;
                streamRef.current = null;
            };

            mr.start(500);
            setIsListening(true);
        } catch (err) {
            console.error("Mic error:", err);
            addMsg({ id: crypto.randomUUID(), type: "system", text: "Microphone access denied. Click to enable.", time: new Date() });
        }
    }, [isMuted, addMsg]);

    // Auto-start on mount
    useEffect(() => {
        mountedRef.current = true;
        // Small delay to let WS connect first
        const timeout = setTimeout(() => {
            if (mountedRef.current) startListening();
        }, 1500);

        return () => {
            mountedRef.current = false;
            clearTimeout(timeout);
            mediaRef.current?.stop();
            if (timerRef.current) clearInterval(timerRef.current);
            streamRef.current?.getTracks().forEach((t) => t.stop());
        };
    }, [startListening]);

    // Mute/unmute — keeps mic stream alive but stops sending
    const toggleMute = useCallback(() => {
        setIsMuted((prev) => !prev);
    }, []);

    // Approve a suggestion
    const approveSuggestion = useCallback(async (taskData: Record<string, unknown>) => {
        try {
            const res = await fetch(`${serverUrl}/api/todos`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(taskData),
            });
            if (res.ok) {
                addMsg({ id: crypto.randomUUID(), type: "system", text: "Task added to your To-Do list.", time: new Date() });
            }
        } catch {
            // Fallback: just acknowledge
            addMsg({ id: crypto.randomUUID(), type: "system", text: "Task noted.", time: new Date() });
        }
    }, [serverUrl, addMsg]);

    const ts = (d: Date) => d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" });

    return (
        <div className="flex flex-col h-full">
            {/* Chat feed */}
            <div ref={feedRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-neutral-600 text-sm gap-2">
                        <div className="text-5xl">🌑</div>
                        <div className="text-neutral-400 text-base font-medium">Shadow is listening</div>
                        <div className="text-xs text-neutral-600">Voice is always on — just speak</div>
                    </div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id} className="animate-in fade-in slide-in-from-bottom-1 duration-200">
                        {/* Shadow speaks */}
                        {msg.type === "shadow" && (
                            <div className="flex gap-3 max-w-[85%]">
                                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5">S</div>
                                <div>
                                    <div className="text-[11px] text-neutral-600 mb-1">{ts(msg.time)}</div>
                                    <div className="bg-[#111] border border-[#1e1e1e] rounded-xl rounded-tl-sm px-3.5 py-2.5 text-sm text-neutral-200 leading-relaxed">
                                        {msg.text}
                                    </div>
                                    {(msg.meta?.suggestion as boolean) && (
                                        <div className="flex gap-2 mt-2">
                                            <button
                                                onClick={() => approveSuggestion(msg.meta?.task_data as Record<string, unknown>)}
                                                className="px-3 py-1 rounded-md text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
                                            >
                                                Yes, add it
                                            </button>
                                            <button className="px-3 py-1 rounded-md text-xs text-neutral-500 border border-[#262626] hover:text-neutral-300 transition-colors">
                                                Later
                                            </button>
                                            <button className="px-3 py-1 rounded-md text-xs text-neutral-600 hover:text-neutral-400 transition-colors">
                                                Ignore
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* User speaks */}
                        {msg.type === "user" && (
                            <div className="flex gap-3 justify-end">
                                <div className="max-w-[75%]">
                                    <div className="text-[11px] text-neutral-600 mb-1 text-right">{ts(msg.time)}</div>
                                    <div className="bg-[#1a1a2e] border border-[#252540] rounded-xl rounded-tr-sm px-3.5 py-2.5 text-sm text-neutral-200">
                                        {msg.text}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Auto-added task */}
                        {msg.type === "task_auto" && (
                            <div className="mx-8 px-3 py-2 bg-amber-500/5 border border-amber-500/15 rounded-lg text-xs flex items-center gap-2">
                                <span className="text-amber-400">⚡</span>
                                <span className="text-amber-300/80">Auto-added:</span>
                                <span className="text-neutral-300">{msg.text}</span>
                                <span className="ml-auto text-neutral-600 font-mono text-[10px]">P{msg.meta?.priority as number}</span>
                            </div>
                        )}

                        {/* Agent spawned */}
                        {msg.type === "agent_spawned" && (
                            <div className="mx-8 px-3 py-2 bg-blue-500/5 border border-blue-500/15 rounded-lg text-xs flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                                <span className="text-blue-400">CLI-{((msg.meta?.slotId as number) ?? 0) + 1} working:</span>
                                <span className="text-neutral-400">{msg.text}</span>
                            </div>
                        )}

                        {/* Agent result */}
                        {msg.type === "agent_result" && (
                            <div className="flex gap-3 max-w-[90%]">
                                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-600 to-green-500 flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5">✓</div>
                                <div className="flex-1">
                                    <div className="text-[11px] text-neutral-600 mb-1">
                                        Solution · CLI-{((msg.meta?.slotId as number) ?? 0) + 1} · {ts(msg.time)}
                                    </div>
                                    <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-xl rounded-tl-sm px-3.5 py-2.5">
                                        <div className="text-xs text-emerald-400 font-medium mb-2">{msg.meta?.task as string}</div>
                                        <div className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap font-mono" style={{ fontSize: "0.8125rem" }}>
                                            {msg.text}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* System */}
                        {msg.type === "system" && (
                            <div className="text-center text-[11px] text-neutral-600 py-1">{msg.text}</div>
                        )}
                    </div>
                ))}
            </div>

            {/* Bottom bar — always-on voice indicator */}
            <div className="px-5 py-2.5 border-t border-[#1a1a1a] bg-[#0a0a0a] flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {isListening && !isMuted ? (
                        <>
                            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                            <span className="text-xs text-neutral-500">Listening…</span>
                        </>
                    ) : isMuted ? (
                        <>
                            <span className="w-2 h-2 rounded-full bg-neutral-700" />
                            <span className="text-xs text-neutral-600">Muted</span>
                        </>
                    ) : (
                        <>
                            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                            <span className="text-xs text-amber-500/70">Connecting mic…</span>
                        </>
                    )}
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={toggleMute}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 ${isMuted
                            ? "bg-neutral-800 text-neutral-400 border border-[#333] hover:text-white"
                            : "bg-red-500/10 text-red-400/80 border border-red-500/15 hover:bg-red-500/20"
                            }`}
                    >
                        {isMuted ? (
                            <><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 11h-1.7c0 .74-.16 1.43-.43 2.05l1.23 1.23c.56-.98.9-2.09.9-3.28zm-4.02.17c0-.06.02-.11.02-.17V5c0-1.66-1.34-3-3-3S9 3.34 9 5v.18l5.98 5.99zM4.27 3L3 4.27l6.01 6.01V11c0 1.66 1.33 3 2.99 3 .22 0 .44-.03.65-.08l1.66 1.66c-.71.33-1.5.52-2.31.52-2.76 0-5.3-2.1-5.3-5.1H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c.91-.13 1.77-.45 2.54-.9L19.73 21 21 19.73 4.27 3z" /></svg>Unmute</>
                        ) : (
                            <><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" /><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" /></svg>Mute</>
                        )}
                    </button>

                    <button
                        onClick={() => fetch(`${serverUrl}/api/cli/kill-all`, { method: "POST" })}
                        className="px-2.5 py-1.5 rounded-full text-[10px] text-neutral-700 border border-[#1e1e1e] hover:text-red-400 hover:border-red-500/25 transition-colors"
                    >
                        KILL
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Helpers ──
function dedup(text: string, ref: React.MutableRefObject<string>): string {
    if (!ref.current || !text) { ref.current = text.split(/\s+/).slice(-5).join(" "); return text; }
    const tail = ref.current.split(/\s+/);
    const words = text.split(/\s+/);
    let overlap = 0;
    for (let n = Math.min(tail.length, 6); n >= 2; n--) {
        if (tail.slice(-n).join(" ").toLowerCase() === words.slice(0, n).join(" ").toLowerCase()) { overlap = n; break; }
    }
    const cleaned = overlap > 0 ? words.slice(overlap).join(" ") : text;
    ref.current = text.split(/\s+/).slice(-5).join(" ");
    return cleaned;
}

async function blobToWav(blob: Blob): Promise<ArrayBuffer> {
    const ctx = new AudioContext({ sampleRate: 16000 });
    const buf = await ctx.decodeAudioData(await blob.arrayBuffer());
    const samples = buf.getChannelData(0);
    const wav = new ArrayBuffer(44 + samples.length * 2);
    const v = new DataView(wav);
    const w = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    w(36, "data"); v.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) { const s = Math.max(-1, Math.min(1, samples[i])); v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true); }
    ctx.close();
    return wav;
}
