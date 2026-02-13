"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";

interface TerminalTabProps {
    slotId: number;
    serverUrl: string;
    isActive: boolean;
}

export default function TerminalTab({ slotId, serverUrl, isActive }: TerminalTabProps) {
    const termRef = useRef<HTMLDivElement>(null);
    const termInstance = useRef<Terminal | null>(null);
    const fitAddon = useRef<FitAddon | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const [status, setStatus] = useState<string>("idle");
    const [task, setTask] = useState<string>("");

    const initTerminal = useCallback(() => {
        if (!termRef.current || termInstance.current) return;

        const term = new Terminal({
            theme: {
                background: "#0a0a0a",
                foreground: "#ededed",
                cursor: "#3b82f6",
                selectionBackground: "#3b82f644",
                black: "#0a0a0a",
                red: "#ef4444",
                green: "#10b981",
                yellow: "#f59e0b",
                blue: "#3b82f6",
                magenta: "#8b5cf6",
                cyan: "#06b6d4",
                white: "#ededed",
                brightBlack: "#737373",
                brightRed: "#f87171",
                brightGreen: "#34d399",
                brightYellow: "#fbbf24",
                brightBlue: "#60a5fa",
                brightMagenta: "#a78bfa",
                brightCyan: "#22d3ee",
                brightWhite: "#ffffff",
            },
            fontSize: 13,
            fontFamily: '"Geist Mono", "SF Mono", "Fira Code", monospace',
            cursorBlink: true,
            cursorStyle: "bar",
            scrollback: 5000,
            allowProposedApi: true,
        });

        const fit = new FitAddon();
        fitAddon.current = fit;
        term.loadAddon(fit);
        term.loadAddon(new WebLinksAddon());
        term.open(termRef.current);
        fit.fit();

        // Welcome message
        term.writeln("\x1b[1;36m╔══════════════════════════════════════╗\x1b[0m");
        term.writeln(`\x1b[1;36m║\x1b[0m  Shadow CLI — Slot ${slotId}                \x1b[1;36m║\x1b[0m`);
        term.writeln("\x1b[1;36m╚══════════════════════════════════════╝\x1b[0m");
        term.writeln("\x1b[0;90mWaiting for task assignment...\x1b[0m");
        term.writeln("");

        termInstance.current = term;
    }, [slotId]);

    // Connect WebSocket
    useEffect(() => {
        initTerminal();

        const wsUrl = `${serverUrl.replace("http", "ws")}/ws/terminal/${slotId}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log(`[Terminal ${slotId}] Connected`);
        };

        ws.onmessage = (e) => {
            if (typeof e.data === "string") {
                try {
                    const msg = JSON.parse(e.data);
                    if (msg.type === "slot_status") {
                        setStatus(msg.status);
                        setTask(msg.task || "");
                    }
                } catch {
                    // Plain text — write to terminal
                    termInstance.current?.write(e.data);
                }
            } else if (e.data instanceof Blob) {
                // Binary PTY output
                e.data.arrayBuffer().then((buf: ArrayBuffer) => {
                    const text = new TextDecoder().decode(buf);
                    termInstance.current?.write(text);
                });
            }
        };

        ws.onclose = () => {
            console.log(`[Terminal ${slotId}] Disconnected`);
        };

        return () => {
            ws.close();
            termInstance.current?.dispose();
            termInstance.current = null;
        };
    }, [slotId, serverUrl, initTerminal]);

    // Resize on visibility change
    useEffect(() => {
        if (isActive && fitAddon.current) {
            setTimeout(() => fitAddon.current?.fit(), 50);
        }
    }, [isActive]);

    // Window resize
    useEffect(() => {
        const handleResize = () => fitAddon.current?.fit();
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, []);

    const statusColor =
        status === "running" ? "bg-blue-500" :
            status === "done" ? "bg-emerald-500" :
                status === "failed" ? "bg-red-500" :
                    "bg-neutral-600";

    return (
        <div className={`h-full flex flex-col ${isActive ? "" : "hidden"}`}>
            {/* Terminal header */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[#111] border-b border-[#262626] text-xs">
                <span className={`w-2 h-2 rounded-full ${statusColor} ${status === "running" ? "animate-pulse" : ""}`} />
                <span className="text-neutral-400 font-mono">
                    CLI-{slotId}
                </span>
                {task && (
                    <span className="text-neutral-500 truncate ml-2">
                        {task.length > 40 ? task.slice(0, 40) + "…" : task}
                    </span>
                )}
                <span className="ml-auto text-neutral-600">{status}</span>
            </div>
            {/* Terminal body */}
            <div ref={termRef} className="flex-1 bg-[#0a0a0a]" />
        </div>
    );
}
