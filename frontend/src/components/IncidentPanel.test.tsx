import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import IncidentPanel from "./IncidentPanel";
import type { QuorumAnalysis } from "@/lib/api";

function analysis(overrides: Partial<QuorumAnalysis> = {}): QuorumAnalysis {
  return {
    triggered_at: "2026-01-01T00:00:00Z",
    anomaly_type: "error rate critical (12.0%)",
    current_metrics: { cpu: 90, error_rate: 12 },
    recall_answer: "This matches the payment-service outage from last month.",
    similar_incident_summary: "payment outage",
    safe_state_deployment_id: "dep-safe-01",
    safe_state_commit: "cafebabe1234deadbeef",
    safe_state_commit_message: "revert risky migration",
    confidence: "high",
    graph_insights: [
      { subject: "dep-bad", relationship: "caused", object: "inc-9" },
    ],
    ...overrides,
  };
}

describe("IncidentPanel", () => {
  it("renders the healthy state when there is no analysis", () => {
    render(<IncidentPanel analysis={null} onRollback={() => {}} />);
    expect(screen.getByText("All Systems Nominal")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders incident details from the analysis", () => {
    render(<IncidentPanel analysis={analysis()} onRollback={() => {}} />);
    expect(screen.getByText("error rate critical (12.0%)")).toBeInTheDocument();
    expect(screen.getByText(/payment-service outage/)).toBeInTheDocument();
    expect(screen.getByText("dep-safe-01")).toBeInTheDocument();
    expect(screen.getByText("revert risky migration")).toBeInTheDocument();
    // SHA is truncated to 12 chars
    expect(screen.getByText("cafebabe1234")).toBeInTheDocument();
    expect(screen.getByText("HIGH CONFIDENCE")).toBeInTheDocument();
  });

  it("renders graph insights", () => {
    render(<IncidentPanel analysis={analysis()} onRollback={() => {}} />);
    expect(screen.getByText("dep-bad")).toBeInTheDocument();
    expect(screen.getByText("→ caused →")).toBeInTheDocument();
    expect(screen.getByText("inc-9")).toBeInTheDocument();
  });

  it("calls onRollback with the safe deployment id when confirmed", async () => {
    const onRollback = vi.fn();
    render(<IncidentPanel analysis={analysis()} onRollback={onRollback} />);
    await userEvent.click(screen.getByRole("button", { name: /confirm rollback/i }));
    expect(onRollback).toHaveBeenCalledWith("dep-safe-01");
  });

  it("disables the button and shows progress while rolling back", () => {
    render(<IncidentPanel analysis={analysis()} onRollback={() => {}} isRollingBack />);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
    expect(screen.getByText(/rolling back/i)).toBeInTheDocument();
  });

  it("disables rollback when no safe state was identified", () => {
    render(<IncidentPanel
      analysis={analysis({ safe_state_deployment_id: "unknown" })}
      onRollback={() => {}} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
