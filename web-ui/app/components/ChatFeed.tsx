"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface ChatMessage {
    id: string;
    type: "transcript" | "analysis" | "task" | "agent_spawned" | "agent_result" | "system";
    text: string;
    meta?: Record<string, unknown>;
    time: Date;
}

interface ChatFeedProps {
    serverUrl: string;
    onTaskSpawned?: (todoId: number, slotId: number | null) => void;
}

export default function ChatFeed({ serverUrl, onTaskSpawned }: ChatFeedProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isRecording, setIsRecording] = useState(false);
    const [currentTranscript, setCurrentTranscript] = useState("");
    const feedRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const mediaRef = useRef<MediaRecorder | null>(null);
    const prevTailRef = useRef<string>("");

    const addMessage = useCallback((msg: ChatMessage) => {
        setMessages((prev) => [...prev.slice(-100), msg]);
    }, []);

    const scrollToBottom = useCallback(() => {
        setTimeout(() => {
            feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
        }, 50);
    }, []);

    useEffect(scrollToBottom, [messages, scrollToBottom]);

    // WebSocket connection
    const connectAudioWs = useCallback(() => {
        const wsUrl = `${serverUrl.replace("http", "ws")}/ws/audio`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            addMessage({
                id: crypto.randomUUID(),
                type: "system",
                text: "Session connected. Ready for voice input.",
                time: new Date(),
            });
        };

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);

            if (data.type === "transcript") {
                const cleaned = deduplicateOverlap(data.text, prevTailRef);
                if (cleaned.length > 3) {
                    addMessage({
                        id: crypto.randomUUID(),
                        type: "transcript",
                        text: cleaned,
                        time: new Date(),
                    });
                }
            }

            if (data.type === "analysis") {
                addMessage({
                    id: crypto.randomUUID(),
                    type: "analysis",
                    text: data.summary || "",
                    meta: { intent: data.intent, priority: data.priority, confidence: data.confidence },
                    time: new Date(),
                });
            }

            if (data.type === "todo") {
                addMessage({
                    id: crypto.randomUUID(),
                    type: "task",
                    text: data.task,
                    meta: { todoId: data.id, priority: data.priority, category: data.category },
                    time: new Date(),
                });
            }

            if (data.type === "agent_spawned") {
                addMessage({
                    id: crypto.randomUUID(),
                    type: "agent_spawned",
                    text: data.task,
                    meta: { todoId: data.todo_id, slotId: data.slot_id },
                    time: new Date(),
                });
                onTaskSpawned?.(data.todo_id, data.slot_id);
            }

            if (data.type === "agent_result") {
                // Remove the "spawned" message for this todo
                setMessages((prev) =>
                    prev.filter(
                        (m) => !(m.type === "agent_spawned" && (m.meta?.todoId as number) === data.todo_id)
                    )
                );
                addMessage({
                    id: crypto.randomUUID(),
                    type: "agent_result",
                    text: data.result || "No result.",
                    meta: { todoId: data.todo_id, slotId: data.slot_id, task: data.task, status: data.status },
                    time: new Date(),
                });
            }
        };

        ws.onclose = () => {
            setTimeout(connectAudioWs, 3000);
        };
    }, [serverUrl, addMessage, onTaskSpawned]);

    useEffect(() => {
        connectAudioWs();
        return () => wsRef.current?.close();
    }, [connectAudioWs]);

    // Voice recording
    const toggleRecording = useCallback(async () => {
        if (isRecording) {
            mediaRef.current?.stop();
            setIsRecording(false);
            setCurrentTranscript("");
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { noiseSuppression: true, autoGainControl: true, echoCancellation: true },
            });
            const mr = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
            mediaRef.current = mr;

            let chunks: Blob[] = [];
            const BUFFER_DURATION = 10000; // 10s buffers

            mr.ondataavailable = (e) => {
                if (e.data.size > 0) chunks.push(e.data);
            };

            // Every 10s, send accumulated audio
            const interval = setInterval(() => {
                if (chunks.length === 0) return;
                const blob = new Blob(chunks, { type: "audio/webm" });
                chunks = [];

                // Convert to WAV and send
                blobToWav(blob).then((wav) => {
                    if (wsRef.current?.readyState === WebSocket.OPEN) {
                        wsRef.current.send(wav);
                    }
                });
            }, BUFFER_DURATION);

            mr.onstop = () => {
                clearInterval(interval);
                // Send remaining chunks
                if (chunks.length > 0) {
                    const blob = new Blob(chunks, { type: "audio/webm" });
                    blobToWav(blob).then((wav) => {
                        if (wsRef.current?.readyState === WebSocket.OPEN) {
                            wsRef.current.send(wav);
                        }
                    });
                }
                stream.getTracks().forEach((t) => t.stop());
            };

            mr.start(500); // 500ms slices
            setIsRecording(true);
        } catch (err) {
            console.error("Mic access error:", err);
        }
    }, [isRecording]);

    const timeStr = (d: Date) => d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

    return (
        <div className="flex flex-col h-full">
            {/* Feed */}
            <div ref={feedRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-neutral-500 text-sm">
                        <div className="text-4xl mb-3">🌑</div>
                        <div>Start a voice session</div>
                        <div className="text-xs text-neutral-600 mt-1">Press the mic to begin</div>
                    </div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id} className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        {msg.type === "transcript" && (
                            <div className="flex gap-2.5">
                                <div className="w-6 h-6 rounded-full bg-neutral-800 flex items-center justify-center text-xs shrink-0 mt-0.5">🎤</div>
                                <div>
                                    <div className="text-xs text-neutral-500 mb-1">{timeStr(msg.time)}</div>
                                    <div className="text-sm text-neutral-200">{msg.text}</div>
                                </div>
                            </div>
                        )}

                        {msg.type === "analysis" && (
                            <div className="ml-8 px-3 py-2 bg-[#111] border border-[#262626] rounded-lg text-xs">
                                <span className="text-neutral-400">Analysis</span>
                                <span className="mx-2 text-neutral-600">·</span>
                                <span className={`font-mono ${(msg.meta?.intent as string) === "urgent" ? "text-red-400" :
                                        (msg.meta?.intent as string) === "task" ? "text-amber-400" :
                                            "text-neutral-500"
                                    }`}>
                                    [{((msg.meta?.intent as string) || "info").toUpperCase()}]
                                </span>
                                <span className="ml-2 text-neutral-400">{msg.text}</span>
                            </div>
                        )}

                        {msg.type === "task" && (
                            <div className="ml-8 px-3 py-2 bg-amber-500/5 border border-amber-500/20 rounded-lg text-xs">
                                <div className="flex items-center gap-2 text-amber-400 font-medium">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" /></svg>
                                    Task Extracted
                                </div>
                                <div className="mt-1 text-neutral-300">{msg.text}</div>
                            </div>
                        )}

                        {msg.type === "agent_spawned" && (
                            <div className="ml-8 px-3 py-2.5 bg-blue-500/5 border border-blue-500/20 rounded-lg text-xs">
                                <div className="flex items-center gap-2 text-blue-400 font-medium">
                                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                                    Working on it… {msg.meta?.slotId != null ? `(CLI-${msg.meta.slotId})` : "(queued)"}
                                </div>
                                <div className="mt-1 text-neutral-400">{msg.text}</div>
                                <div className="flex gap-1 mt-2 text-blue-400">
                                    <span className="animate-bounce" style={{ animationDelay: "0ms" }}>●</span>
                                    <span className="animate-bounce" style={{ animationDelay: "150ms" }}>●</span>
                                    <span className="animate-bounce" style={{ animationDelay: "300ms" }}>●</span>
                                </div>
                            </div>
                        )}

                        {msg.type === "agent_result" && (
                            <div className="ml-8 px-3 py-2.5 bg-emerald-500/5 border border-emerald-500/20 rounded-lg">
                                <div className="flex items-center gap-2 text-emerald-400 text-xs font-medium mb-2">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
                                    {(msg.meta?.status as string) === "done" ? "✅" : "❌"} Solution
                                    {msg.meta?.slotId != null && <span className="text-neutral-500">· CLI-{msg.meta.slotId as number}</span>}
                                </div>
                                <div className="text-xs text-neutral-500 mb-2 font-medium">{msg.meta?.task as string}</div>
                                <div
                                    className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap font-mono"
                                    style={{ fontSize: "0.8125rem" }}
                                >
                                    {msg.text}
                                </div>
                            </div>
                        )}

                        {msg.type === "system" && (
                            <div className="text-center text-xs text-neutral-600 py-1">
                                {msg.text}
                            </div>
                        )}
                    </div>
                ))}

                {currentTranscript && (
                    <div className="flex gap-2.5 opacity-50">
                        <div className="w-6 h-6 rounded-full bg-neutral-800 flex items-center justify-center text-xs shrink-0">🎤</div>
                        <div className="text-sm text-neutral-400 italic">{currentTranscript}…</div>
                    </div>
                )}
            </div>

            {/* Bottom bar */}
            <div className="p-3 border-t border-[#262626] bg-[#0d0d0d]">
                <div className="flex items-center justify-center gap-3">
                    <button
                        onClick={toggleRecording}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-all ${isRecording
                                ? "bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30"
                                : "bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30"
                            }`}
                    >
                        {isRecording ? (
                            <>
                                <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                                Stop Recording
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" /><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" /></svg>
                                Start Recording
                            </>
                        )}
                    </button>

                    <button
                        onClick={() => fetch(`${serverUrl}/api/cli/kill-all`, { method: "POST" })}
                        className="px-3 py-2.5 rounded-full text-xs text-neutral-500 border border-[#262626] hover:text-red-400 hover:border-red-500/30 transition-colors"
                    >
                        KILL ALL
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Helpers ──

function deduplicateOverlap(text: string, prevTailRef: React.MutableRefObject<string>): string {
    if (!prevTailRef.current || !text) {
        prevTailRef.current = getLastWords(text, 5);
        return text;
    }

    const tailWords = prevTailRef.current.split(/\s+/);
    const newWords = text.split(/\s+/);

    let overlapLen = 0;
    for (let tryLen = Math.min(tailWords.length, 6); tryLen >= 2; tryLen--) {
        const tailSlice = tailWords.slice(-tryLen).join(" ").toLowerCase();
        const newSlice = newWords.slice(0, tryLen).join(" ").toLowerCase();
        if (tailSlice === newSlice) {
            overlapLen = tryLen;
            break;
        }
    }

    const cleaned = overlapLen > 0 ? newWords.slice(overlapLen).join(" ") : text;
    prevTailRef.current = getLastWords(text, 5);
    return cleaned;
}

function getLastWords(text: string, n: number): string {
    return text.split(/\s+/).slice(-n).join(" ");
}

async function blobToWav(blob: Blob): Promise<ArrayBuffer> {
    const audioCtx = new AudioContext({ sampleRate: 16000 });
    const arrayBuf = await blob.arrayBuffer();
    const audioBuf = await audioCtx.decodeAudioData(arrayBuf);
    const samples = audioBuf.getChannelData(0);

    // Create WAV
    const wavBuf = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(wavBuf);

    const writeStr = (o: number, s: string) => {
        for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i));
    };

    writeStr(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(8, "WAVE");
    writeStr(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, 16000, true);
    view.setUint32(28, 32000, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, "data");
    view.setUint32(40, samples.length * 2, true);

    for (let i = 0; i < samples.length; i++) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    audioCtx.close();
    return wavBuf;
}
