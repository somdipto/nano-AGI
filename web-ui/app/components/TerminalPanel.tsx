"use client";

import { useState } from "react";
import TerminalTab from "./TerminalTab";

interface TerminalPanelProps {
    serverUrl: string;
}

export default function TerminalPanel({ serverUrl }: TerminalPanelProps) {
    const [activeSlot, setActiveSlot] = useState(0);
    const slots = [0, 1, 2, 3, 4];

    return (
        <div className="flex flex-col h-full border-t border-[#262626]">
            {/* Tab bar */}
            <div className="flex items-center bg-[#0d0d0d] border-b border-[#262626]">
                {slots.map((id) => (
                    <button
                        key={id}
                        onClick={() => setActiveSlot(id)}
                        className={`flex items-center gap-1.5 px-4 py-2 text-xs font-mono transition-colors border-b-2 ${activeSlot === id
                                ? "border-blue-500 text-white bg-[#111]"
                                : "border-transparent text-neutral-500 hover:text-neutral-300 hover:bg-[#111]"
                            }`}
                    >
                        <span className="text-[10px]">●</span>
                        CLI-{id}
                    </button>
                ))}
                <div className="ml-auto px-3 text-[10px] text-neutral-600 font-mono">
                    5 slots
                </div>
            </div>

            {/* Terminal instances */}
            <div className="flex-1 relative">
                {slots.map((id) => (
                    <TerminalTab
                        key={id}
                        slotId={id}
                        serverUrl={serverUrl}
                        isActive={activeSlot === id}
                    />
                ))}
            </div>
        </div>
    );
}
