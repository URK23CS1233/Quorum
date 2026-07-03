"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Network, RefreshCw } from "lucide-react";
import dynamic from "next/dynamic";

const KnowledgeGraph = dynamic(() => import("@/components/KnowledgeGraph"), { ssr: false });

export default function GraphPage() {
  const [graph, setGraph] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.getGraph().then(g => setGraph(g)).finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="h-full flex flex-col">
      <div className="h-14 border-b border-[#1e1e2e] px-5 flex items-center gap-2 shrink-0">
        <Network size={15} className="text-[#6366f1]" />
        <span className="font-semibold text-white">Knowledge Graph</span>
        <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-[#6366f1]/15 text-[#6366f1] font-bold">
          {graph.nodes.length}n · {graph.edges.length}e
        </span>
        <div className="flex-1" />
        <button onClick={load} className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[#1e1e2e] bg-[#0e0e18] text-slate-400 hover:border-[#6366f1]/30 transition-colors">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>
      <div className="flex-1 p-4">
        <KnowledgeGraph nodes={graph.nodes} edges={graph.edges} />
      </div>
    </div>
  );
}
