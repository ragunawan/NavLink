import sqlite3
import time

import numpy as np

from .auth import authorized, present, require_project
from .encoding import concepts, get_encoder, lexical_text, searchable, tokens
from .evidence import citation


def filter_projects(session, user, filters=None):
    items = authorized(session, user)
    for key, value in (filters or {}).items():
        if value:
            # Canonical labels also find existing records using the previous UI labels.
            aliases = {"Software tool": "Software", "Analytics product": "Analytics Product"} if key == "project_type" else {"Financial Management": "Financial management"} if key == "domain" else {}
            items = [p for p in items if aliases.get(p.payload.get(key), p.payload.get(key)) == aliases.get(value, value)]
    return items


def lexical_ranks(items, query):
    # An ephemeral FTS index excludes unauthorized documents from BM25 statistics.
    # The persistent index is kept transactionally for local exports / future partitioning.
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE f USING fts5(id UNINDEXED,content)")
        conn.executemany("INSERT INTO f VALUES (?,?)", [(p.id, lexical_text(p.payload)) for p in items])
        words = list(dict.fromkeys(tokens(query)))[:40]
        if not words:
            return []
        expression = " OR ".join('"' + t + '"' for t in words)
        return [row[0] for row in conn.execute("SELECT id FROM f WHERE f MATCH ? ORDER BY bm25(f),id", (expression,))]
    finally:
        conn.close()


def evidence_for(query, p):
    words = set(tokens(query))
    evidence = []
    for label, value in [("Mission", p["mission_problem"]), ("Domain", p["domain"]), ("Status", p["status"]), ("Organization", p["organization"]), ("Datasets", ", ".join(d["name"] for d in p["datasets"]))]:
        if words & set(tokens(value)):
            evidence.append(f"{label}: {value}")
    return evidence or [f"Catalog mission: {p['mission_problem']}"]


def search(session, user, query, mode="hybrid", filters=None, limit=20, exclude=None):
    start = time.perf_counter()
    items = [p for p in filter_projects(session, user, filters) if p.id != exclude]
    encoder = get_encoder()
    query_vec = encoder.encode(query)
    similarities = {}
    for p in items:
        # Encoder changes rebuild only visible records during reads; normal edits persist vectors.
        vec = np.frombuffer(p.vector, dtype=np.float32) if p.encoder == encoder.name else encoder.encode(searchable(p.payload))
        similarities[p.id] = float(np.dot(query_vec, vec))
    lex = lexical_ranks(items, query)
    sem = sorted((p.id for p in items if similarities[p.id] > 0.08), key=lambda k: (-similarities[k], k))
    lex_rank, sem_rank = {k: n + 1 for n, k in enumerate(lex)}, {k: n + 1 for n, k in enumerate(sem)}
    from os import getenv
    weight = min(1.0, max(0.0, float(getenv("NAVYLINK_SEMANTIC_WEIGHT", "0.55"))))
    scores = {}
    for p in items:
        k = p.id
        if mode == "keyword" and k in lex_rank:
            scores[k] = 1 / (60 + lex_rank[k])
        elif mode == "semantic" and k in sem_rank:
            scores[k] = similarities[k]
        elif mode == "hybrid" and (k in lex_rank or k in sem_rank):
            scores[k] = ((1 - weight) / (60 + lex_rank[k]) if k in lex_rank else 0) + (weight / (60 + sem_rank[k]) if k in sem_rank else 0)
    indexed = {p.id: p for p in items}
    ranked = sorted(scores, key=lambda k: (-scores[k], k))
    hits = [{"project": present(indexed[k], user), "rank": rank, "ranking_score": round(scores[k], 6), "evidence": evidence_for(query, indexed[k].payload), "inference": "Relative retrieval rank from " + mode + " search; similarity alone does not establish duplication or reuse eligibility.", "citations": [citation(present(indexed[k], user), field) for field in ["mission_problem", "domain", "datasets"]]} for rank, k in enumerate(ranked[:limit], 1)]
    return {"query": query, "mode": mode, "encoder": encoder.name, "total": len(ranked), "elapsed_ms": round((time.perf_counter() - start) * 1000, 2), "results": hits}


def related(session, user, project_id, limit=6):
    source = require_project(session, project_id, user)
    p = source.payload
    result = search(session, user, p["mission_problem"], limit=100, exclude=project_id)
    src_data = {d["name"] for d in p["datasets"]}
    for hit in result["results"]:
        other = hit["project"]
        shared_data = sorted(src_data & {d["name"] for d in other["datasets"]})
        shared_tech = sorted(set(p["technologies"]) & set(other["technologies"]))
        shared_use_cases = sorted(set(p["use_cases"]) & set(other["use_cases"]))
        same_domain = p["domain"] == other["domain"]
        # Augment semantic/lexical ranking with explicit dataset, domain and technology overlap.
        hit["ranking_score"] += len(shared_data) * .005 + .002 * same_domain + len(shared_tech) * .0005 + len(shared_use_cases) * .001
        hit["evidence"] = (["Shared datasets: " + ", ".join(shared_data)] if shared_data else []) + (["Same domain: " + p["domain"]] if same_domain else []) + ["Candidate mission: " + other["mission_problem"]]
        hit["inference"] = "Potentially related based on mission retrieval and shared metadata. Technical and access compatibility require review."
        hit["evidence"] += (["Shared technologies: " + ", ".join(shared_tech)] if shared_tech else []) + (["Shared stated use cases: " + "; ".join(shared_use_cases)] if shared_use_cases else [])
        hit["citations"] += [citation(other, field) for field in ["technologies", "use_cases"]]
    result["results"].sort(key=lambda h: (-h["ranking_score"], h["project"]["id"]))
    result["results"] = result["results"][:limit]
    for rank, hit in enumerate(result["results"], 1):
        hit["rank"] = rank
    return result
