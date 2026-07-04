"""Trajectory recorder (G2, §4.2.1) — parse raw runs into the typed schema.

Two sources, one schema:

* **autocode (student)** emits the Tier-4.4 headless NDJSON
  (:mod:`autocode.backend.headless_schema`): ``tool_call_started`` /
  ``tool_call_completed`` carry ``tool_name`` + ``tool_family``; legacy
  ``item_started`` with ``kind == "tool_execution"`` is the fallback;
  ``turn_completed`` carries a usage block.
* **puku-cli (teacher)** emits Claude-Code-style ``stream-json``: ``assistant``
  messages whose ``content[]`` holds ``tool_use`` blocks, ``user`` messages whose
  ``content[]`` holds ``tool_result`` blocks, and a final ``result`` event.

Both are mapped onto :class:`Trajectory` so the classifier/reflector see a single
shape. Tool families are mapped to escalation layers (retrieval/analysis → L2,
edits/shell/reasoning → L4) so ``layer_distribution`` is meaningful — the basis
for the teacher-vs-student layer contrast (PLAN_05 Channel C).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from autocode.anvil.teacher.schemas import (
    Layer,
    ModelInfo,
    Step,
    Task,
    Trajectory,
)

# --------------------------------------------------------------------------- #
# Layer / action mappings                                                      #
# --------------------------------------------------------------------------- #

# autocode tool_family -> (layer, action)
_AUTOCODE_FAMILY: dict[str, tuple[str, str]] = {
    "file_read": (Layer.L2.value, "retrieve"),
    "search": (Layer.L2.value, "retrieve"),
    "lsp": (Layer.L2.value, "retrieve"),
    "git": (Layer.L1.value, "tool_call"),
    "file_write": (Layer.L4.value, "edit"),
    "shell": (Layer.L4.value, "tool_call"),
    "planning": (Layer.L4.value, "plan"),
    "subagent": (Layer.L4.value, "tool_call"),
    "user_interaction": (Layer.L4.value, "tool_call"),
    "cache": (Layer.L4.value, "tool_call"),
    "unknown": (Layer.L4.value, "tool_call"),
}

# puku tool name -> (layer, action)
_PUKU_TOOL: dict[str, tuple[str, str]] = {
    "Read": (Layer.L2.value, "retrieve"),
    "Grep": (Layer.L2.value, "retrieve"),
    "Glob": (Layer.L2.value, "retrieve"),
    "Bash": (Layer.L4.value, "tool_call"),
    "Edit": (Layer.L4.value, "edit"),
    "Write": (Layer.L4.value, "edit"),
    "NotebookEdit": (Layer.L4.value, "edit"),
    "WebFetch": (Layer.L4.value, "tool_call"),
    "WebSearch": (Layer.L4.value, "tool_call"),
    "Task": (Layer.L4.value, "tool_call"),
    "Skill": (Layer.L4.value, "tool_call"),
    "TodoWrite": (Layer.L4.value, "plan"),
}

_PUKU_RETRIEVAL_LAYER = {Layer.L2.value}


def _digest(text: str) -> str:
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def _iter_events(data: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    events: list[dict[str, Any]] = []
    for line in str(data).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


# --------------------------------------------------------------------------- #
# autocode student NDJSON                                                       #
# --------------------------------------------------------------------------- #


def from_autocode_ndjson(
    data: str | list[dict[str, Any]],
    *,
    trajectory_id: str,
    task: Task,
    model: ModelInfo | None = None,
    final_diff: str | None = None,
    wall_s: float = 0.0,
) -> Trajectory:
    events = _iter_events(data)
    steps: list[Step] = []
    seen_item_ids: set[str] = set()
    tokens_in = tokens_out = 0
    i = 0

    for ev in events:
        etype = ev.get("type", "")
        if etype in ("tool_call_started", "tool_call_completed"):
            # Prefer the typed events; dedupe by tool_call_id/item_id.
            key = str(ev.get("tool_call_id") or ev.get("item_id") or "")
            if etype == "tool_call_completed" and key and key in seen_item_ids:
                continue
            if etype == "tool_call_started":
                name = ev.get("tool_name", "")
                fam = ev.get("tool_family", "") or _family_for(name)
                layer, action = _AUTOCODE_FAMILY.get(fam, _AUTOCODE_FAMILY["unknown"])
                steps.append(
                    Step(
                        i=i,
                        layer=layer,
                        action=action,
                        tool=name,
                        args=dict(ev.get("args", {}) or {}),
                    )
                )
                i += 1
                if key:
                    seen_item_ids.add(key)
        elif etype == "item_started" and ev.get("kind") == "tool_execution":
            key = str(ev.get("item_id") or "")
            if key and key in seen_item_ids:
                continue
            name = ev.get("tool_name", "") or ev.get("name", "")
            fam = ev.get("tool_family", "") or _family_for(name)
            layer, action = _AUTOCODE_FAMILY.get(fam, _AUTOCODE_FAMILY["unknown"])
            steps.append(Step(i=i, layer=layer, action=action, tool=name))
            i += 1
            if key:
                seen_item_ids.add(key)
        elif etype == "item_completed" and ev.get("result"):
            # attach a digest to the most recent step lacking one
            for s in reversed(steps):
                if not s.observation_digest:
                    s.observation_digest = _digest(str(ev.get("result")))
                    break
        elif etype == "turn_completed":
            usage = ev.get("usage", {}) or {}
            tokens_in += int(usage.get("input_tokens", 0))
            tokens_out += int(usage.get("output_tokens", 0))

    tj = Trajectory(
        trajectory_id=trajectory_id,
        task=task,
        model=model or ModelInfo(),
        steps=steps,
        final_diff=final_diff,
        cost={"usd": 0.0, "wall_s": float(wall_s)},
        role="student",
    )
    if steps and (tokens_in or tokens_out):
        # spread total tokens across steps as a coarse per-step estimate
        per_in = tokens_in // len(steps)
        per_out = tokens_out // len(steps)
        for s in steps:
            s.tokens = {"in": per_in, "out": per_out}
    tj.compute_layer_distribution()
    return tj


def _family_for(tool_name: str) -> str:
    try:
        from autocode.backend.headless_schema import tool_family

        return tool_family(tool_name)
    except Exception:  # noqa: BLE001 - schema import is best-effort
        return "unknown"


# --------------------------------------------------------------------------- #
# puku-cli teacher stream-json                                                  #
# --------------------------------------------------------------------------- #


def from_puku_stream(
    data: str | list[dict[str, Any]],
    *,
    trajectory_id: str,
    task: Task,
    model: ModelInfo | None = None,
    final_diff: str | None = None,
) -> Trajectory:
    events = _iter_events(data)
    steps: list[Step] = []
    by_tool_use_id: dict[str, Step] = {}
    model_name = model.alias if model else ""
    wall_s = 0.0
    cost_usd = 0.0
    i = 0

    for ev in events:
        etype = ev.get("type", "")
        if etype == "assistant":
            msg = ev.get("message", {}) or {}
            if not model_name:
                model_name = msg.get("model", "") or model_name
            for block in msg.get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    name = block.get("name", "")
                    layer, action = _PUKU_TOOL.get(name, (Layer.L4.value, "tool_call"))
                    step = Step(
                        i=i,
                        layer=layer,
                        action=action,
                        tool=name,
                        args=dict(block.get("input", {}) or {}),
                    )
                    steps.append(step)
                    tuid = block.get("id", "")
                    if tuid:
                        by_tool_use_id[tuid] = step
                    i += 1
        elif etype == "user":
            msg = ev.get("message", {}) or {}
            for block in msg.get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tuid = block.get("tool_use_id", "")
                matched = by_tool_use_id.get(tuid)
                if matched is not None:
                    content = block.get("content", "")
                    matched.observation_digest = _digest(
                        content if isinstance(content, str) else json.dumps(content)
                    )
                    if block.get("is_error"):
                        matched.args = {**matched.args, "_observed_error": True}
        elif etype == "result":
            wall_s = float(ev.get("duration_ms", 0)) / 1000.0
            cost_usd = float(ev.get("total_cost_usd", 0.0) or 0.0)

    mi = model or ModelInfo()
    if model_name and not mi.alias:
        mi = ModelInfo(alias=model_name, provider=mi.provider, is_local=mi.is_local)

    tj = Trajectory(
        trajectory_id=trajectory_id,
        task=task,
        model=mi,
        steps=steps,
        final_diff=final_diff,
        cost={"usd": cost_usd, "wall_s": wall_s},
        role="teacher",
    )
    tj.compute_layer_distribution()
    return tj


__all__ = ["from_autocode_ndjson", "from_puku_stream"]
