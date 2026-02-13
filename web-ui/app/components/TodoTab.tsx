"use client";

import { useState, useEffect, useCallback } from "react";

interface Todo {
    id: number;
    task: string;
    priority: number;
    predicted_priority?: number;
    category: string;
    status: string;
    deadline?: string;
    source?: string;
    created_at?: string;
}

interface Prediction {
    task: string;
    source: string;
    confidence: number;
    priority: number;
}

interface TodoTabProps {
    serverUrl: string;
}

const CATEGORY_COLORS: Record<string, string> = {
    email: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
    code: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    research: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    schedule: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    call: "text-green-400 bg-green-500/10 border-green-500/20",
    purchase: "text-pink-400 bg-pink-500/10 border-pink-500/20",
    travel: "text-orange-400 bg-orange-500/10 border-orange-500/20",
    finance: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    health: "text-rose-400 bg-rose-500/10 border-rose-500/20",
    other: "text-neutral-400 bg-neutral-500/10 border-neutral-500/20",
};

export default function TodoTab({ serverUrl }: TodoTabProps) {
    const [todos, setTodos] = useState<Todo[]>([]);
    const [predictions, setPredictions] = useState<Prediction[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTodos = useCallback(async () => {
        try {
            const res = await fetch(`${serverUrl}/api/todos`);
            if (res.ok) {
                const data = await res.json();
                setTodos(data);
            }
        } catch { /* ignore */ }
        setLoading(false);
    }, [serverUrl]);

    const fetchPredictions = useCallback(async () => {
        try {
            const res = await fetch(`${serverUrl}/api/predictions`);
            if (res.ok) {
                const data = await res.json();
                setPredictions(data.today || []);
            }
        } catch { /* ignore */ }
    }, [serverUrl]);

    useEffect(() => {
        fetchTodos();
        fetchPredictions();
        const interval = setInterval(fetchTodos, 10000);
        return () => clearInterval(interval);
    }, [fetchTodos, fetchPredictions]);

    const spawnTask = async (todoId: number) => {
        await fetch(`${serverUrl}/api/todos/${todoId}/spawn`, { method: "POST" });
        fetchTodos();
    };

    const pendingTodos = todos.filter((t) => t.status === "pending" || t.status === "active");
    const doneTodos = todos.filter((t) => t.status === "done");

    const priorityBar = (p: number) => {
        const width = Math.min(100, p * 10);
        const color = p >= 8 ? "bg-red-500" : p >= 5 ? "bg-amber-500" : "bg-blue-500";
        return (
            <div className="w-12 h-1.5 rounded-full bg-[#1a1a1a]">
                <div className={`h-full rounded-full ${color}`} style={{ width: `${width}%` }} />
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col overflow-y-auto">
            <div className="px-5 py-4 space-y-6">

                {/* Predicted section */}
                {predictions.length > 0 && (
                    <section>
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-xs font-semibold text-neutral-300 tracking-wider uppercase">Predicted</span>
                            <span className="text-[10px] text-neutral-600">Based on your patterns</span>
                        </div>
                        <div className="space-y-2">
                            {predictions.map((pred, i) => (
                                <div
                                    key={i}
                                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#0d0d0d] border border-[#1a1a1a] hover:border-[#262626] transition-colors"
                                >
                                    <span className="text-neutral-700">◇</span>
                                    <span className="text-sm text-neutral-400 flex-1">{pred.task}</span>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${pred.source === "weekly_pattern" ? "text-blue-400/60 border-blue-500/15" :
                                            pred.source === "gap_detection" ? "text-amber-400/60 border-amber-500/15" :
                                                "text-neutral-500 border-[#262626]"
                                        }`}>
                                        {pred.source === "weekly_pattern" ? "Pattern" :
                                            pred.source === "gap_detection" ? "Gap" :
                                                pred.source === "stress_detection" ? "Stress" : pred.source}
                                    </span>
                                    <span className="text-[10px] text-neutral-600 font-mono">
                                        {(pred.confidence * 100).toFixed(0)}%
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Active tasks */}
                <section>
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-xs font-semibold text-neutral-300 tracking-wider uppercase">Today</span>
                        <span className="text-[10px] text-neutral-600">{pendingTodos.length} tasks</span>
                    </div>

                    {loading ? (
                        <div className="text-xs text-neutral-700 py-8 text-center">Loading tasks…</div>
                    ) : pendingTodos.length === 0 ? (
                        <div className="text-xs text-neutral-700 py-8 text-center border border-dashed border-[#1e1e1e] rounded-lg">
                            No tasks yet. Say something to start.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {pendingTodos.map((todo) => {
                                const catStyle = CATEGORY_COLORS[todo.category] || CATEGORY_COLORS.other;
                                const displayPriority = todo.predicted_priority ?? todo.priority;

                                return (
                                    <div
                                        key={todo.id}
                                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#0d0d0d] border border-[#1a1a1a] group hover:border-[#262626] transition-colors"
                                    >
                                        <button
                                            onClick={() => spawnTask(todo.id)}
                                            className="w-5 h-5 rounded-md border border-[#333] flex items-center justify-center text-neutral-600 hover:text-blue-400 hover:border-blue-500/30 transition-colors shrink-0"
                                            title="Assign to CLI agent"
                                        >
                                            {todo.status === "active" ? (
                                                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                                            ) : (
                                                <span className="text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">▶</span>
                                            )}
                                        </button>

                                        <span className="text-sm text-neutral-300 flex-1">{todo.task}</span>

                                        <span className={`text-[10px] px-1.5 py-0.5 rounded border ${catStyle}`}>
                                            {todo.category}
                                        </span>

                                        {priorityBar(displayPriority)}

                                        <span className="text-[10px] text-neutral-600 font-mono w-6 text-right">
                                            P{displayPriority.toFixed(0)}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </section>

                {/* Done section */}
                {doneTodos.length > 0 && (
                    <section>
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-xs font-semibold text-neutral-300 tracking-wider uppercase">Done</span>
                            <span className="text-[10px] text-neutral-600">{doneTodos.length}</span>
                        </div>
                        <div className="space-y-1.5">
                            {doneTodos.slice(0, 10).map((todo) => (
                                <div
                                    key={todo.id}
                                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-neutral-600"
                                >
                                    <span className="text-emerald-600">✓</span>
                                    <span className="text-xs line-through">{todo.task}</span>
                                </div>
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}
