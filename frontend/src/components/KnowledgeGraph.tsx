"use client";
import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

interface GraphNode {
  id: string;
  label: string;
  group: string;
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const GROUP_COLOR: Record<string, string> = {
  deployment:  "#6366f1",
  incident:    "#ef4444",
  commit:      "#f59e0b",
  service:     "#10b981",
  person:      "#a855f7",
  cause:       "#f97316",
  resolution:  "#06b6d4",
  concept:     "#64748b",
};

export default function KnowledgeGraph({ nodes, edges }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ label: string; x: number; y: number } | null>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const W = svgRef.current.clientWidth || 800;
    const H = svgRef.current.clientHeight || 500;

    // Arrow marker
    const defs = svg.append("defs");
    Object.entries(GROUP_COLOR).forEach(([group, color]) => {
      defs.append("marker")
        .attr("id", `arrow-${group}`)
        .attr("viewBox", "0 -4 8 8")
        .attr("refX", 20).attr("refY", 0)
        .attr("markerWidth", 6).attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-4L8,0L0,4")
        .attr("fill", color)
        .attr("opacity", 0.6);
    });

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on("zoom", (e) => g.attr("transform", e.transform.toString()));
    svg.call(zoom);

    const g = svg.append("g");

    const linkData = edges.map(e => ({
      ...e,
      source: nodes.find(n => n.id === (typeof e.source === "string" ? e.source : (e.source as any).id)) ?? e.source,
      target: nodes.find(n => n.id === (typeof e.target === "string" ? e.target : (e.target as any).id)) ?? e.target,
    }));

    const sim = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(linkData as any).id((d: any) => d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(W / 2, H / 2))
      .force("collision", d3.forceCollide(30));

    // Edges
    const link = g.append("g").selectAll("line")
      .data(linkData)
      .join("line")
      .attr("stroke", d => {
        const src = nodes.find(n => n.id === (typeof d.source === "string" ? d.source : (d.source as any).id));
        return GROUP_COLOR[src?.group ?? "concept"] + "60";
      })
      .attr("stroke-width", 1.5)
      .attr("marker-end", d => {
        const src = nodes.find(n => n.id === (typeof d.source === "string" ? d.source : (d.source as any).id));
        return `url(#arrow-${src?.group ?? "concept"})`;
      });

    // Edge labels
    const edgeLabel = g.append("g").selectAll("text")
      .data(linkData)
      .join("text")
      .attr("font-size", 8)
      .attr("fill", "#475569")
      .attr("text-anchor", "middle")
      .text(d => (d as any).label?.slice(0, 12) ?? "");

    // Node groups
    const node = g.append("g").selectAll("g")
      .data(nodes)
      .join("g")
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on("start", (e, d: any) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on("drag",  (e, d: any) => { d.fx = e.x; d.fy = e.y; })
          .on("end",   (e, d: any) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }) as any
      )
      .on("mouseenter", (e, d) => setTooltip({ label: d.label, x: e.clientX, y: e.clientY }))
      .on("mouseleave", () => setTooltip(null));

    // Glow ring
    node.append("circle")
      .attr("r", 18)
      .attr("fill", d => GROUP_COLOR[d.group] + "18")
      .attr("stroke", d => GROUP_COLOR[d.group] + "40")
      .attr("stroke-width", 1);

    // Main circle
    node.append("circle")
      .attr("r", 12)
      .attr("fill", d => GROUP_COLOR[d.group] + "cc")
      .attr("stroke", d => GROUP_COLOR[d.group])
      .attr("stroke-width", 1.5);

    // Label
    node.append("text")
      .attr("dy", 26)
      .attr("text-anchor", "middle")
      .attr("font-size", 9)
      .attr("fill", "#94a3b8")
      .text(d => d.label.slice(0, 14));

    sim.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);
      edgeLabel
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2);
      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => { sim.stop(); };
  }, [nodes, edges]);

  const hasData = nodes.length > 0;

  return (
    <div className="relative w-full h-full rounded-xl border border-[#1e1e2e] bg-[#0e0e18] overflow-hidden">
      {!hasData && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-500">
          <div className="w-16 h-16 rounded-full border-2 border-dashed border-[#1e1e2e] flex items-center justify-center">
            <div className="w-6 h-6 rounded-full bg-[#6366f1]/20 border border-[#6366f1]/40" />
          </div>
          <div className="text-sm">Knowledge graph empty</div>
          <div className="text-xs text-slate-600">Seed incident history to populate the Cognee graph</div>
        </div>
      )}
      <svg ref={svgRef} className="w-full h-full" />

      {/* Legend */}
      {hasData && (
        <div className="absolute bottom-3 left-3 flex flex-wrap gap-2">
          {Object.entries(GROUP_COLOR).map(([group, color]) => (
            <div key={group} className="flex items-center gap-1 text-xs text-slate-500">
              <div className="w-2 h-2 rounded-full" style={{ background: color }} />
              {group}
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {hasData && (
        <div className="absolute top-3 right-3 text-xs text-slate-600 font-mono">
          {nodes.length}n · {edges.length}e
        </div>
      )}

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 px-2 py-1 rounded bg-[#141422] border border-[#1e1e2e] text-xs text-slate-300 pointer-events-none"
          style={{ left: tooltip.x + 12, top: tooltip.y - 20 }}
        >
          {tooltip.label}
        </div>
      )}
    </div>
  );
}
