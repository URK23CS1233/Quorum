"use client";
import { Database } from "lucide-react";
import SourcesManager from "@/components/SourcesManager";

export default function SourcesPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="h-14 border-b border-[#1e1e2e] px-5 flex items-center gap-2 shrink-0">
        <Database size={15} className="text-[#6366f1]" />
        <span className="font-semibold text-white">Data Sources</span>
        <span className="text-xs text-slate-600 ml-1">— all sources feed into Cognee memory</span>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <SourcesManager />
      </div>
    </div>
  );
}
