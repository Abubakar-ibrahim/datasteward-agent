
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_RULES = {
    "year": {"min": 2000, "max": 2035},
    "amount": {"min": 0},
    "status": {"allowed": ["complete", "pending"]},
}

def profile_csv(path: str) -> dict:
    df = pd.read_csv(path)
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_by_column": {k:int(v) for k,v in df.isna().sum().items()},
        "dtypes": {k:str(v) for k,v in df.dtypes.items()},
    }

def robust_numeric_anomalies(series: pd.Series, z_threshold: float = 3.5) -> list[int]:
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()
    if len(valid) < 8:
        return []
    median = float(valid.median())
    mad = float(np.median(np.abs(valid - median)))
    if mad == 0:
        return []
    modified_z = 0.6745 * (valid - median) / mad
    return valid.index[np.abs(modified_z) > z_threshold].tolist()

def detect_issues(path: str, rules: dict | None = None) -> dict:
    rules = rules or DEFAULT_RULES
    df = pd.read_csv(path)
    issues = []
    row_flags = {}

    for col in df.columns:
        n = int(df[col].isna().sum())
        if n:
            issues.append({
                "type":"missing",
                "column":col,
                "count":n,
                "severity":"medium",
                "action":"human_review"
            })

    dup_mask = df.duplicated(keep="first")
    dup_count = int(dup_mask.sum())
    if dup_count:
        issues.append({
            "type":"duplicate",
            "column":"*",
            "count":dup_count,
            "severity":"high",
            "action":"safe_auto_fix"
        })
        for i in df.index[dup_mask]:
            row_flags.setdefault(int(i), []).append("exact_duplicate")

    for col, rule in rules.items():
        if col not in df.columns:
            continue
        s = df[col]
        if "allowed" in rule:
            bad = s.notna() & ~s.isin(rule["allowed"])
            n = int(bad.sum())
            if n:
                issues.append({
                    "type":"invalid_category",
                    "column":col,
                    "count":n,
                    "severity":"high",
                    "action":"human_review"
                })
                for i in df.index[bad]:
                    row_flags.setdefault(int(i), []).append(f"invalid_{col}")

        if "min" in rule or "max" in rule:
            num = pd.to_numeric(s, errors="coerce")
            bad = pd.Series(False, index=df.index)
            if "min" in rule:
                bad |= num.notna() & (num < rule["min"])
            if "max" in rule:
                bad |= num.notna() & (num > rule["max"])
            n = int(bad.sum())
            if n:
                issues.append({
                    "type":"out_of_range",
                    "column":col,
                    "count":n,
                    "severity":"high",
                    "action":"human_review"
                })
                for i in df.index[bad]:
                    row_flags.setdefault(int(i), []).append(f"out_of_range_{col}")

    anomaly_rows = set()
    for col in df.select_dtypes(include="number").columns:
        rows = robust_numeric_anomalies(df[col])
        if rows:
            anomaly_rows.update(rows)
            issues.append({
                "type":"numeric_anomaly",
                "column":col,
                "count":len(rows),
                "severity":"review",
                "action":"human_review"
            })
            for i in rows:
                row_flags.setdefault(int(i), []).append(f"numeric_anomaly_{col}")

    return {
        "issues": issues,
        "anomaly_rows": sorted(map(int, anomaly_rows)),
        "row_flags": {str(k):v for k,v in sorted(row_flags.items())},
    }

def quality_score(path: str, rules: dict | None = None) -> dict:
    df = pd.read_csv(path)
    n_rows = max(len(df), 1)
    n_cells = max(df.shape[0] * df.shape[1], 1)

    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())
    detected = detect_issues(path, rules)
    validity_count = sum(
        i["count"] for i in detected["issues"]
        if i["type"] in {"invalid_category","out_of_range"}
    )

    completeness = max(0.0, 1 - missing / n_cells)
    uniqueness = max(0.0, 1 - duplicates / n_rows)
    validity = max(0.0, 1 - validity_count / n_rows)

    score = round(100 * (
        0.45*completeness +
        0.30*uniqueness +
        0.25*validity
    ), 1)

    return {
        "overall_score": score,
        "dimensions": {
            "completeness": round(completeness*100,1),
            "uniqueness": round(uniqueness*100,1),
            "validity": round(validity*100,1),
        }
    }

def clean_safe(path: str, out_path: str) -> dict:
    df = pd.read_csv(path)
    before = len(df)
    cleaned = df.drop_duplicates(keep="first").copy()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(out_path, index=False)
    return {
        "rows_before": int(before),
        "rows_after": int(len(cleaned)),
        "duplicates_removed": int(before-len(cleaned)),
        "note":"Only exact duplicates were removed automatically. Missing, invalid and anomalous values were preserved for human review."
    }

def build_report(path: str, out_path: str) -> dict:
    report = {
        "profile": profile_csv(path),
        "quality": quality_score(path),
        **detect_issues(path),
    }
    Path(out_path).write_text(json.dumps(report, indent=2))
    return report
