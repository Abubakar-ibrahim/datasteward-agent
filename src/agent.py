from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from strands import Agent, tool
from strands.vended_interventions.hitl import HumanInTheLoop

from quality import build_report, clean_safe, detect_issues, profile_csv, quality_score

load_dotenv()

_TOOL_TRACE: list[dict[str, Any]] = []


def reset_trace() -> None:
    _TOOL_TRACE.clear()


def get_trace() -> list[dict[str, Any]]:
    return list(_TOOL_TRACE)


def _record(tool_name: str, summary: str, result: dict[str, Any] | None = None) -> None:
    _TOOL_TRACE.append({"tool": tool_name, "summary": summary, "result": result or {}})


def _compact_analysis(csv_path: str) -> dict[str, Any]:
    profile = profile_csv(csv_path)
    issues = detect_issues(csv_path)
    score = quality_score(csv_path)
    return {
        "rows": profile["rows"],
        "columns": profile["columns"],
        "missing_cells": profile["missing_cells"],
        "duplicate_rows": profile["duplicate_rows"],
        "quality_score": score["overall_score"],
        "quality_dimensions": score["dimensions"],
        "issue_groups": len(issues["issues"]),
        "anomaly_rows": issues["anomaly_rows"],
        "issues": issues["issues"],
    }


@tool
def analyze_dataset(csv_path: str) -> str:
    """Profile the CSV, detect quality issues, and compute the transparent quality score in one safe analysis step."""
    result = _compact_analysis(csv_path)
    _record(
        "analyze_dataset",
        (
            f"Analyzed {result['rows']} rows × {result['columns']} columns; "
            f"score {result['quality_score']}/100; "
            f"{result['duplicate_rows']} duplicate row(s); "
            f"{result['missing_cells']} missing cell(s)"
        ),
        result,
    )
    return json.dumps(result, separators=(",", ":"))


@tool
def prepare_safe_outputs(csv_path: str, safe_output_path: str, review_output_path: str) -> str:
    """Remove only exact duplicates and create a review queue for judgment-sensitive rows; never impute or delete anomalies."""
    Path(safe_output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(review_output_path).parent.mkdir(parents=True, exist_ok=True)

    cleaning = clean_safe(csv_path, safe_output_path)
    detected = detect_issues(csv_path)
    df = pd.read_csv(csv_path)

    review_rows: set[int] = set(detected.get("anomaly_rows", []))

    # Missing values are judgment-sensitive: queue the affected source rows.
    missing_mask = df.isna().any(axis=1)
    review_rows.update(int(i) for i in df.index[missing_mask])

    # Queue rule failures and anomalies, but not rows flagged only as exact duplicates.
    for idx_text, flags in detected.get("row_flags", {}).items():
        if any(flag != "exact_duplicate" for flag in flags):
            review_rows.add(int(idx_text))

    rows = sorted(review_rows)
    if rows:
        review = df.loc[rows].copy()
        review.insert(0, "source_row_index", review.index)
        review.insert(
            1,
            "review_reason",
            [";".join(detected.get("row_flags", {}).get(str(i), [])) or "missing_value" for i in rows],
        )
    else:
        review = pd.DataFrame(columns=["source_row_index", "review_reason", *df.columns])

    review.to_csv(review_output_path, index=False)

    result = {
        "safe_output_path": safe_output_path,
        "review_output_path": review_output_path,
        "duplicates_removed": cleaning["duplicates_removed"],
        "rows_after_safe_cleaning": cleaning["rows_after"],
        "review_rows": int(len(review)),
        "policy": "Only exact duplicates were removed automatically; missing, invalid and anomalous values were preserved for human review.",
    }
    _record(
        "prepare_safe_outputs",
        (
            f"Removed {result['duplicates_removed']} exact duplicate row(s) and "
            f"created a {result['review_rows']}-row human-review queue"
        ),
        result,
    )
    return json.dumps(result, separators=(",", ":"))


@tool
def publish_final_dataset(safe_cleaned_path: str, final_path: str, audit_path: str, review_queue_path: str = "outputs/review_queue.csv") -> str:
    """Publish the safe-cleaned CSV and audit report. This consequential export requires explicit human approval."""
    Path(final_path).parent.mkdir(parents=True, exist_ok=True)
    Path(audit_path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(safe_cleaned_path, final_path)
    audit = build_report(final_path, audit_path)

    # Add an explicit provenance / decision record so the publication is auditable.
    source_analysis = next((x.get("result", {}) for x in _TOOL_TRACE if x.get("tool") == "analyze_dataset"), {})
    preparation = next((x.get("result", {}) for x in _TOOL_TRACE if x.get("tool") == "prepare_safe_outputs"), {})
    audit["datasteward_audit"] = {
        "source_rows": source_analysis.get("rows"),
        "published_rows": audit["profile"]["rows"],
        "exact_duplicates_removed": preparation.get("duplicates_removed", 0),
        "human_review_rows": preparation.get("review_rows", 0),
        "human_publication_approved": True,
        "review_queue_path": review_queue_path,
        "tools_executed_before_audit_write": [x.get("tool") for x in _TOOL_TRACE],
        "source_quality_score": source_analysis.get("quality_score"),
        "published_quality_score": audit["quality"]["overall_score"],
        "policy": "Only exact duplicates were removed automatically. Missing, invalid and anomalous values were preserved for human review; publication required explicit human approval.",
    }
    Path(audit_path).write_text(json.dumps(audit, indent=2))

    result = {
        "published": True,
        "final_path": final_path,
        "audit_path": audit_path,
        "final_rows": audit["profile"]["rows"],
        "final_quality_score": audit["quality"]["overall_score"],
        "human_review_rows": preparation.get("review_rows", 0),
        "duplicates_removed": preparation.get("duplicates_removed", 0),
    }
    _record("publish_final_dataset", "Published final dataset after explicit human approval", result)
    return json.dumps(result, separators=(",", ":"))


SYSTEM = """You are DataSteward Agent, a human-centered data-quality operator built for reliable execution.
You MUST use the registered tools; never invent dataset findings.

Execute exactly this workflow, in order:
1. Call analyze_dataset once.
2. Call prepare_safe_outputs once with:
   safe_output_path='outputs/safe_cleaned.csv'
   review_output_path='outputs/review_queue.csv'
3. Call publish_final_dataset once with:
   safe_cleaned_path='outputs/safe_cleaned.csv'
   final_path='outputs/cleaned.csv'
   audit_path='outputs/audit.json'
4. After publication is approved or rejected, give a very short factual summary.

Policy:
- Autonomous where safe.
- Human approval where publication matters.
- Never impute missing values automatically.
- Never delete statistical anomalies automatically.
- Never overwrite the source CSV.
- Do not call extra tools and do not change output paths.
"""


def _make_model():
    provider = os.getenv("DATASTEWARD_MODEL_PROVIDER", "ollama").strip().lower()

    if provider == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model_id=os.getenv("OLLAMA_MODEL_ID", "qwen3:4b"),
            temperature=0.0,
            keep_alive="5m",
        )

    if provider == "bedrock":
        from strands.models.bedrock import BedrockModel

        return BedrockModel(
            model_id=os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-micro-v1:0"),
            region_name=os.getenv("AWS_REGION", "us-west-2"),
            temperature=0.0,
        )

    raise ValueError(f"Unsupported DATASTEWARD_MODEL_PROVIDER={provider!r}. Use 'ollama' or 'bedrock'.")


def provider_status() -> dict[str, str]:
    provider = os.getenv("DATASTEWARD_MODEL_PROVIDER", "ollama").strip().lower()
    if provider == "ollama":
        return {
            "provider": "Ollama",
            "model": os.getenv("OLLAMA_MODEL_ID", "qwen3:4b"),
            "endpoint": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        }
    return {
        "provider": "Amazon Bedrock",
        "model": os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-micro-v1:0"),
        "endpoint": os.getenv("AWS_REGION", "us-west-2"),
    }


def make_agent() -> Agent:
    # Only the two non-consequential tools are auto-approved. Publication pauses the real agent loop.
    return Agent(
        model=_make_model(),
        system_prompt=SYSTEM,
        tools=[analyze_dataset, prepare_safe_outputs, publish_final_dataset],
        interventions=[HumanInTheLoop(allowed_tools=["analyze_dataset", "prepare_safe_outputs"])],
    )


def start_run(csv_path: str) -> tuple[Agent, Any]:
    """Start one genuine Strands agent loop and return the paused/completed result."""
    reset_trace()
    Path("outputs").mkdir(exist_ok=True)
    agent = make_agent()
    prompt = (
        f"Process the CSV at '{csv_path}' now. Follow the required three-tool workflow exactly. "
        "Use the fixed output paths from your system instructions."
    )
    result = agent(prompt)
    return agent, result


def resume_run(agent: Agent, interrupt_id: str, approved: bool) -> Any:
    """Resume the same paused Strands run with the human's decision."""
    return agent([
        {
            "interruptResponse": {
                "interruptId": interrupt_id,
                "response": "yes" if approved else "no",
            }
        }
    ])


def result_text(result: Any) -> str:
    """Return a concise user-facing result instead of raw Strands metadata."""
    published = next((x.get("result", {}) for x in reversed(_TOOL_TRACE) if x.get("tool") == "publish_final_dataset"), None)
    if published and published.get("published"):
        return (
            f"Published {published.get('final_rows')} rows with a "
            f"{published.get('final_quality_score')} quality score after explicit human approval. "
            f"{published.get('duplicates_removed', 0)} exact duplicates were removed; "
            f"{published.get('human_review_rows', 0)} judgment-sensitive rows remain documented in the review queue."
        )
    for attr in ("message", "output", "text"):
        value = getattr(result, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Agent run completed."


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/demo_registry.csv"
    agent, result = start_run(path)
    print(result)
    if getattr(result, "stop_reason", None) == "interrupt":
        intr = result.interrupts[0]
        print(f"\nAPPROVAL REQUIRED: {getattr(intr, 'reason', 'Publication requires human approval')}")
        answer = input("Approve publication? [y/N]: ").strip().lower() in {"y", "yes"}
        print(resume_run(agent, intr.id, answer))
