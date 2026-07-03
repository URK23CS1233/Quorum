"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Deployment } from "@/lib/api";
import DeploymentTimeline from "@/components/DeploymentTimeline";
import { Clock } from "lucide-react";

export default function TimelinePage() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDeployments().then(d => setDeployments(d.deployments ?? [])).finally(() => setLoading(false));
    const t = setInterval(() => api.getDeployments().then(d => setDeployments(d.deployments ?? [])), 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="h-full flex flex-col">
      <div className="h-14 border-b border-[#1e1e2e] px-5 flex items-center gap-2 shrink-0">
        <Clock size={15} className="text-[#6366f1]" />
        <span className="font-semibold text-white">Deployment Memory</span>
        <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-[#6366f1]/15 text-[#6366f1] font-bold">
          {deployments.length} ingested
        </span>
      </div>
      <div className="flex-1 overflow-auto p-5">
        {loading
          ? <div className="text-slate-500 text-sm text-center mt-16">Loading memory…</div>
          : <div className="max-w-2xl mx-auto"><DeploymentTimeline deployments={deployments} /></div>
        }
      </div>
    </div>
  );
}
