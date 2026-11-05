import json
import platform
import resource
import statistics
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from .evaluation_data import PROPOSALS, QUERIES, SIMILAR_PAIRS, UNRELATED_PAIRS
from .main import create_app


def evaluate():
    started = time.perf_counter()
    header = {"X-Demo-User": "curator"}
    with tempfile.TemporaryDirectory() as tmp, TestClient(create_app(f"sqlite:///{tmp}/evaluation.db")) as client:
        startup_ms = (time.perf_counter() - started) * 1000
        precisions, recalls, rr, latencies, rows = [], [], [], [], []
        for query, relevant in QUERIES:
            result = client.get("/api/v1/search", params={"q": query, "limit": 5}, headers=header).json()
            ids = [h["project"]["id"] for h in result["results"]]
            found = len(set(ids) & set(relevant))
            precisions.append(found / 5)
            recalls.append(found / len(relevant))
            rr.append(next((1 / (i + 1) for i, k in enumerate(ids) if k in relevant), 0))
            latencies.append(result["elapsed_ms"])
            rows.append({"query": query, "relevant": relevant, "returned": ids, "precision_at_5": found / 5, "recall_at_5": round(found / len(relevant), 4)})
        tp = fp = fn = workflow_success = complement_found = complement_total = 0
        citation_total = citation_valid = constraint_total = constraint_valid = 0
        workflow_latencies = []

        def citations(value):
            if isinstance(value, dict):
                if {"project_id", "field", "value", "url"} <= value.keys():
                    yield value
                for item in value.values():
                    yield from citations(item)
            elif isinstance(value, list):
                for item in value:
                    yield from citations(item)
        proposal_rows = []
        for case in PROPOSALS:
            workflow_start = time.perf_counter()
            response = client.post("/api/v1/agent/discover", json={key: value for key, value in case.items() if key not in {"duplicates", "complementary"}}, headers=header)
            response.raise_for_status()
            run = response.json()
            workflow_latencies.append((time.perf_counter() - workflow_start) * 1000)
            grounded = True
            project_cache = {}
            for ref in citations(run):
                citation_total += 1
                project_id = ref["project_id"]
                if project_id not in project_cache:
                    project_cache[project_id] = client.get("/api/v1/projects/" + project_id, headers=header).json()
                project = project_cache[project_id]
                valid = ref["field"] in project and ref["value"] == project[ref["field"]] and ref["url"] == "/projects/" + project_id and ref["project_name"] == project["name"]
                citation_valid += int(valid)
                grounded = grounded and valid
            for candidate in run["assessment"]["candidates"]:
                constraint_total += 1
                dimensions = {c["dimension"] for c in candidate["constraints"]}
                constraint_valid += int(dimensions == {"Licensing", "Access", "Deployment", "Integration", "Datasets", "Support", "Technology", "Contact"})
            predicted = {c["project"]["id"] for c in run["assessment"]["candidates"] if c["classification"] == "Potential duplicate"}
            expected = set(case["duplicates"])
            tp += len(predicted & expected)
            fp += len(predicted - expected)
            fn += len(expected - predicted)
            evidence_ids = {c["project"]["id"] for c in run["assessment"]["candidates"] if c["evidence"]}
            complement_found += len(evidence_ids & set(case["complementary"]))
            complement_total += len(case["complementary"])
            supported = all(c["evidence"] and c["open_questions"] for c in run["assessment"]["candidates"])
            # Functional success requires persisted output, evidence and at least one known lead (or no false duplicate for the unrelated proposal).
            known_leads = expected | set(case["complementary"])
            workflow_success += int(supported and grounded and client.get("/api/v1/agent/runs/" + run["id"], headers=header).status_code == 200 and (bool(evidence_ids & known_leads) if known_leads else not predicted))
            proposal_rows.append({"description": case["description"], "expected_duplicates": sorted(expected), "predicted_duplicates": sorted(predicted), "decision": run["recommendation"]["decision"], "candidate_ids": [c["project"]["id"] for c in run["assessment"]["candidates"]], "all_citations_valid": grounded})
        pair_rows = []
        for a, b in SIMILAR_PAIRS + UNRELATED_PAIRS:
            result = client.get(f"/api/v1/projects/{a}/related", headers=header).json()
            pair_rows.append({"pair": [a, b], "known_similar": (a, b) in SIMILAR_PAIRS, "in_related_top_6": b in [h["project"]["id"] for h in result["results"]]})
        boundaries = [client.get("/api/v1/projects/maint-07").status_code == 404, client.get("/api/v1/projects/fin-07", headers={"X-Demo-User": "maintainer"}).status_code == 404, client.get("/api/v1/analytics/overview").json()["total"] == 42]
        for mode in ["keyword", "semantic", "hybrid"]:
            ids = [h["project"]["id"] for h in client.get("/api/v1/search", params={"q": "Acoustic Health Kit", "mode": mode}).json()["results"]]
            boundaries.append("maint-07" not in ids)
        report = {"environment": {"platform": platform.platform(), "python": platform.python_version(), "encoder": client.get("/api/health").json()["encoder"], "catalog_records": 56, "identity": "curator", "note": "In-process TestClient; no HTTP transport or browser time. Synthetic labels, not an independent real-world benchmark."},
                "summary": {"queries": len(QUERIES), "precision_at_5": round(statistics.mean(precisions), 4), "recall_at_5": round(statistics.mean(recalls), 4), "mrr": round(statistics.mean(rr), 4), "duplicate_precision": round(tp / max(1, tp + fp), 4), "duplicate_recall": round(tp / max(1, tp + fn), 4), "duplicate_tp_fp_fn": [tp, fp, fn], "complementary_lead_recall": round(complement_found / max(1, complement_total), 4), "workflow_success_rate": workflow_success / len(PROPOSALS), "permission_checks_passed": sum(boundaries), "permission_checks_total": len(boundaries), "similar_pairs_in_top_6": sum(r["known_similar"] and r["in_related_top_6"] for r in pair_rows), "unrelated_pairs_in_top_6": sum(not r["known_similar"] and r["in_related_top_6"] for r in pair_rows), "search_latency_median_ms": round(statistics.median(latencies), 2), "search_latency_max_ms": max(latencies), "startup_and_seed_ms": round(startup_ms, 2), "process_peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if platform.system() == "Darwin" else 1024), 2)}, "queries": rows, "proposals": proposal_rows, "pairs": pair_rows}
        report["summary"].update(citations_checked=citation_total, citations_valid=citation_valid,
                                 proposal_cases=len(PROPOSALS), near_duplicate_proposals=sum(bool(c["duplicates"]) for c in PROPOSALS),
                                 complementary_or_nonduplicate_proposals=sum(not c["duplicates"] for c in PROPOSALS),
                                 search_latency_average_ms=round(statistics.mean(latencies), 2),
                                 candidates_with_complete_constraints=constraint_valid, candidates_checked=constraint_total,
                                 workflow_latency_median_ms=round(statistics.median(workflow_latencies), 2),
                                 workflow_latency_max_ms=round(max(workflow_latencies), 2))
        return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/evaluation.json")
    args = parser.parse_args()
    report = evaluate()
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
