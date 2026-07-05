"""
Support Assistant — end-to-end example.

A Vellum workflow that:
1. Ingests a resolved support conversation into cognee (CogneeRememberNode).
2. Answers a new question using graph memory (CogneeRecallNode).
3. Checks if the answer drifts from stored knowledge (CogneeMemoryDriftNode).

Run:
    pip install cognee-integration-vellum python-dotenv
    cp ../.env.template .env   # fill in LLM_API_KEY
    python examples/support_assistant.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# ── Standalone demo (no Vellum account needed) ──────────────────────────
# The nodes work as plain Python objects. To use them in the Vellum visual
# editor, run `vellum push` — they appear as drag-and-drop blocks automatically.

from cognee_integration_vellum import (
    CogneeMemoryDriftNode,
    CogneeRecallNode,
    CogneeRememberNode,
    MemoryScope,
)


async def run_demo():
    print("=" * 60)
    print("cognee-integration-vellum · Support Assistant Demo")
    print("=" * 60)

    # ── Step 1: Ingest a resolved conversation ──────────────────────────
    print("\n[1] Ingesting past support conversation…")
    remember_node = CogneeRememberNode(
        text=(
            "RESOLVED TICKET #1042\n"
            "Customer: My payment keeps failing with error code 402.\n"
            "Support: Error 402 means your card was declined. "
            "Please verify billing address matches the card on file. "
            "Resolved by updating billing address. Date: 2024-03-15."
        ),
        workflow_name="support-assistant",
        scope=MemoryScope.WORKFLOW,
    )
    remember_out = remember_node.run()
    print(f"   ✓ Stored in dataset: {remember_out.dataset}")
    print(f"   ✓ Success: {remember_out.success}")

    # ── Step 2: Answer a new similar question ────────────────────────────
    print("\n[2] New customer asks: 'Why is my payment failing?'")
    recall_node = CogneeRecallNode(
        query="Why is my payment failing?",
        workflow_name="support-assistant",
        scope=MemoryScope.WORKFLOW,
    )
    recall_out = recall_node.run()
    print(f"   Answer: {recall_out.answer or '(no memory yet — run cognify first)'}")
    print(f"   Citations: {recall_out.citations}")

    # ── Step 3: Drift check ──────────────────────────────────────────────
    # Simulate an LLM that's starting to hallucinate
    hallucinated_answer = (
        "Payment failures are caused by server outages and DNS problems. "
        "Contact your internet provider."
    )
    print(f"\n[3] Checking LLM answer for drift…")
    print(f"   LLM said: '{hallucinated_answer[:60]}…'")

    drift_node = CogneeMemoryDriftNode(
        query="Why is my payment failing?",
        current_answer=hallucinated_answer,
        workflow_name="support-assistant",
        scope=MemoryScope.WORKFLOW,
        drift_threshold=0.65,
    )
    drift_out = drift_node.run()

    print(f"   Drift score:    {drift_out.drift_score:.2f}  (0=grounded, 1=diverged)")
    print(f"   Is drifting:    {drift_out.is_drifting}")
    print(f"   Grounded truth: {drift_out.grounded_answer[:80] or '(needs memory first)'}")

    print("\n" + "=" * 60)
    if drift_out.is_drifting:
        print("⚠️  DRIFT DETECTED — LLM answer diverges from stored knowledge.")
        print("   Consider: human review, re-grounding, or memory refresh.")
    else:
        print("✓  Answer is grounded in cognee memory.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_demo())
