"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import ChatTab from "./components/ChatTab";
import SwarmTab from "./components/SwarmTab";
import TodoTab from "./components/TodoTab";

const SERVER_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3777";

type Tab = "chat" | "swarm" | "todo";

interface PoolSlot {
  slot_id: number;
  status: string;
  task: string;
  todo_id: number | null;
  elapsed: number;
  result_preview: string;
}

interface PoolStatus {
  slots: PoolSlot[];
  active_count: number;
  queue_size: number;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("chat");
  const [pool, setPool] = useState<PoolStatus>({
    slots: [],
    active_count: 0,
    queue_size: 0,
  });

  // Connect to pool status WebSocket
  useEffect(() => {
    const wsUrl = `${SERVER_URL.replace("http", "ws")}/ws/pool`;
    let ws: WebSocket;

    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "pool_update") {
          setPool(data.pool);
        }
      };
      ws.onclose = () => setTimeout(connect, 3000);
    };

    connect();
    return () => ws?.close();
  }, []);

  const tabs: { id: Tab; label: string; badge?: number }[] = [
    { id: "chat", label: "Chat" },
    { id: "swarm", label: "Swarm", badge: pool.active_count || undefined },
    { id: "todo", label: "To-Do" },
  ];

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0a]">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-[#1a1a1a] bg-[#0a0a0a]">
        <div className="flex items-center gap-3">
          <span className="text-base font-semibold tracking-tight text-white">🌑 SHADOW</span>
        </div>

        {/* Tab buttons */}
        <div className="flex items-center gap-0.5 bg-[#111] rounded-lg p-0.5 border border-[#1e1e1e]">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-4 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${activeTab === tab.id
                  ? "bg-[#1a1a1a] text-white shadow-sm"
                  : "text-neutral-500 hover:text-neutral-300"
                }`}
            >
              {tab.label}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-blue-500 text-[9px] text-white flex items-center justify-center font-bold">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Voice status */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            {pool.slots.map((s) => (
              <div
                key={s.slot_id}
                className={`w-2 h-2 rounded-full transition-colors ${s.status === "running" ? "bg-blue-500 animate-pulse" :
                    s.status === "done" ? "bg-emerald-500" :
                      s.status === "failed" ? "bg-red-500" :
                        "bg-neutral-800"
                  }`}
                title={`CLI-${s.slot_id + 1}: ${s.status}${s.task ? ` — ${s.task}` : ""}`}
              />
            ))}
          </div>
        </div>
      </header>

      {/* ── Main content ── */}
      <div className="flex-1 min-h-0">
        {activeTab === "chat" && <ChatTab serverUrl={SERVER_URL} />}
        {activeTab === "swarm" && <SwarmTab serverUrl={SERVER_URL} pool={pool} />}
        {activeTab === "todo" && <TodoTab serverUrl={SERVER_URL} />}
      </div>
    </div>
  );
}
