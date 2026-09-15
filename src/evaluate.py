
import json
from pathlib import Path
from quality import detect_issues

def evaluate_demo(csv_path: str, labels_path: str, out_path: str) -> dict:
    labels = json.loads(Path(labels_path).read_text())
    truth = set(labels.get("anomaly_rows", []))
    pred = set(detect_issues(csv_path).get("anomaly_rows", []))
    tp = len(truth & pred)
    fp = len(pred - truth)
    fn = len(truth - pred)
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else 0.0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
    result = {
        "true_anomalies": sorted(truth),
        "predicted_anomalies": sorted(pred),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision,3),
        "recall": round(recall,3),
        "f1": round(f1,3),
    }
    Path(out_path).write_text(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    print(json.dumps(evaluate_demo(
        "data/demo_registry.csv",
        "data/demo_labels.json",
        "outputs/evaluation.json"
    ), indent=2))
