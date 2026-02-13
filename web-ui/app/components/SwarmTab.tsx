"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const TerminalTab = dynamic(() => import("./TerminalTab"), { ssr: false });

interface PoolSlot {
    slot_id: number;
    status: string;
    task: string;
    todo_id: number | null;
    elapsed: number;
    result_preview: string;
}

interface SwarmTabProps {
    serverUrl: string;
    pool: {
        slots: PoolSlot[];
        active_count: number;
        queue_size: number;
    };
}

const STATUS_STYLES: Record<string, { dot: string; bg: string; border: string; label: string }> = {
    idle: { dot: "bg-neutral-700", bg: "bg-[#0d0d0d]", border: "border-[#1a1a1a]", label: "Idle" },
    running: { dot: "bg-blue-500 animate-pulse", bg: "bg-blue-500/[0.03]", border: "border-blue-500/15", label: "Running" },
    done: { dot: "bg-emerald-500", bg: "bg-emerald-500/[0.03]", border: "border-emerald-500/15", label: "Done" },
    failed: { dot: "bg-red-500", bg: "bg-red-500/[0.03]", border: "border-red-500/15", label: "Failed" },
};

export default function SwarmTab({ serverUrl, pool }: SwarmTabProps) {
    const [expanded, setExpanded] = useState<number | null>(null);

    const formatTime = (s: number) => {
        if (s < 60) return `${s}s`;
        return `${Math.floor(s / 60)}m ${s % 60}s`;
    };

    return (
        <div className="h-full flex flex-col">
            {/* Top summary */}
            <div className="px-5 pt-4 pb-3 border-b border-[#1a1a1a] flex items-center gap-4">
                <div className="text-sm text-neutral-400">
                    <span className="text-white font-medium">{pool.active_count}</span> active
                </div>
                {pool.queue_size > 0 && (
                    <div className="text-sm text-amber-400/80">
                        {pool.queue_size} queued
                    </div>
                )}
                <div className="ml-auto">
                    <button
                        onClick={() => fetch(`${serverUrl}/api/cli/kill-all`, { method: "POST" })}
                        className="px-3 py-1 text-[11px] text-neutral-600 border border-[#1e1e1e] rounded-md hover:text-red-400 hover:border-red-500/25 transition-colors"
                    >
                        Kill All
                    </button>
                </div>
            </div>

            {/* Slot cards */}
            <div className="flex-1 overflow-y-auto px-5 py-4">
                <div className="grid grid-cols-5 gap-3">
                    {(pool.slots.length > 0 ? pool.slots : defaultSlots()).map((slot) => {
                        const style = STATUS_STYLES[slot.status] || STATUS_STYLES.idle;
                        const isExpanded = expanded === slot.slot_id;

                        return (
                            <div key={slot.slot_id} className="flex flex-col gap-2">
                                <button
                                    onClick={() => setExpanded(isExpanded ? null : slot.slot_id)}
                                    className={`${style.bg} border ${style.border} rounded-xl p-3.5 text-left transition-all duration-200 hover:border-neutral-600 group`}
                                >
                                    {/* Status line */}
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <span className={`w-2.5 h-2.5 rounded-full ${style.dot}`} />
                                            <span className="text-xs font-medium text-neutral-300">CLI-{slot.slot_id + 1}</span>
                                        </div>
                                        <span className="text-[10px] text-neutral-600 font-mono">{style.label}</span>
                                    </div>

                                    {/* Task info */}
                                    {slot.task ? (
                                        <div className="text-xs text-neutral-500 leading-relaxed line-clamp-2 mb-2">
                                            {slot.task}
                                        </div>
                                    ) : (
                                        <div className="text-xs text-neutral-700 italic mb-2">No task</div>
                                    )}

                                    {/* Timer */}
                                    {slot.status === "running" && slot.elapsed > 0 && (
                                        <div className="text-[10px] text-blue-400/70 font-mono">
                                            ⏱ {formatTime(slot.elapsed)}
                                        </div>
                                    )}

                                    {/* Expand hint */}
                                    <div className="text-[10px] text-neutral-700 mt-2 group-hover:text-neutral-500 transition-colors">
                                        {isExpanded ? "▲ Collapse" : "▶ Terminal"}
                                    </div>
                                </button>
                            </div>
                        );
                    })}
                </div>

                {/* Expanded terminal */}
                {expanded !== null && (
                    <div className="mt-4 rounded-xl border border-[#1e1e1e] bg-[#0d0d0d] overflow-hidden" style={{ height: "400px" }}>
                        <div className="flex items-center justify-between px-3 py-1.5 bg-[#111] border-b border-[#1a1a1a]">
                            <span className="text-xs text-neutral-400 font-mono">CLI-{expanded + 1} Terminal</span>
                            <button
                                onClick={() => setExpanded(null)}
                                className="text-xs text-neutral-600 hover:text-neutral-300 transition-colors"
                            >
                                ✕ Close
                            </button>
                        </div>
                        <div className="h-[calc(100%-32px)]">
                            <TerminalTab slotId={expanded} serverUrl={serverUrl} isActive={true} />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

function defaultSlots(): PoolSlot[] {
    return Array.from({ length: 5 }, (_, i) => ({
        slot_id: i,
        status: "idle",
        task: "",
        todo_id: null,
        elapsed: 0,
        result_preview: "",
    }));
}
