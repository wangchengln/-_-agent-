"use client";

import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import LearnPanel from "@/components/layout/LearnPanel";
import MemoryFileList from "@/components/memory/MemoryFileList";
import MemoryEditor from "@/components/memory/MemoryEditor";
import { useState } from "react";
import { useApp } from "@/lib/store";

export default function MemoryPage() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [learnOpen, setLearnOpen] = useState(false);
  const { sidebarOpen } = useApp();

  return (
    <div className="h-screen flex flex-col" style={{ background: "var(--bg-page)" }}>
      <Header
        onToggleLearnMode={() => setLearnOpen((v) => !v)}
        learnModeOpen={learnOpen}
      />
      <div className="flex-1 flex overflow-hidden">
        {learnOpen && <LearnPanel onClose={() => setLearnOpen(false)} />}
        <div className={`shrink-0 overflow-hidden transition-all duration-300 ${sidebarOpen ? "w-64" : "w-0"}`}>
          <Sidebar />
        </div>
        <div className="w-96 shrink-0 overflow-y-auto" style={{ borderRight: "1px solid var(--border)", background: "var(--bg-surface)" }}>
          <MemoryFileList selectedFile={selectedFile} onSelect={setSelectedFile} />
        </div>
        <div className="flex-1 overflow-hidden">
          <MemoryEditor filePath={selectedFile} />
        </div>
      </div>
    </div>
  );
}
