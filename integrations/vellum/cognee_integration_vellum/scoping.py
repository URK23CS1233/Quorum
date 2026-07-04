"""
Memory scope resolution for cognee-integration-vellum.

A single MemoryScope enum drives how dataset names are constructed,
giving workflows three isolation levels out of the box.
"""

from __future__ import annotations

import os
from enum import Enum


class MemoryScope(str, Enum):
    """Controls which cognee dataset a node reads from / writes to.

    WORKFLOW (default)
        One dataset per Vellum workflow deployment.
        ``dataset = "vellum_<workflow_name>"``
        Good for: shared knowledge within a single workflow.

    USER
        One dataset per ``user_id`` workflow input.
        ``dataset = "vellum_<workflow_name>_u_<user_id>"``
        Good for: per-user personalised assistants.

    GLOBAL
        A single shared dataset across all deployments.
        ``dataset = "vellum_global"``
        Good for: organisation-wide knowledge bases.
    """

    WORKFLOW = "workflow"
    USER = "user"
    GLOBAL = "global"


def resolve_dataset(
    scope: MemoryScope,
    *,
    workflow_name: str = "",
    user_id: str = "",
) -> str:
    """Return the cognee dataset name for the given scope.

    Args:
        scope:          MemoryScope value.
        workflow_name:  Vellum workflow / deployment name. Falls back to the
                        ``VELLUM_WORKFLOW_NAME`` environment variable, then
                        the literal string ``"default"``.
        user_id:        Per-user identifier. Required when
                        ``scope == MemoryScope.USER``; ignored otherwise.

    Returns:
        A dataset name string safe to pass to ``cognee.add()``.

    Raises:
        ValueError: When ``scope == MemoryScope.USER`` and ``user_id`` is empty.
    """
    wf = (
        workflow_name
        or os.getenv("VELLUM_WORKFLOW_NAME", "")
        or "default"
    )
    # Sanitise: replace spaces/slashes with underscores
    wf = wf.replace(" ", "_").replace("/", "_").lower()

    if scope == MemoryScope.GLOBAL:
        return "vellum_global"

    if scope == MemoryScope.USER:
        if not user_id:
            raise ValueError(
                "user_id must be provided when scope=MemoryScope.USER"
            )
        uid = user_id.replace(" ", "_").lower()
        return f"vellum_{wf}_u_{uid}"

    # MemoryScope.WORKFLOW (default)
    return f"vellum_{wf}"
