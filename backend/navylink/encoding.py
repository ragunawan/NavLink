"""Corpus-independent local vectors: restricted entries never train a public index."""
import hashlib
import os
import re
from functools import lru_cache

import numpy as np

CONCEPTS = {
    "maintenance": {"maintenance", "repair", "repairs", "workorder", "workorders", "servicing"},
    "equipment": {"equipment", "machinery", "asset", "assets", "component", "components", "engine", "engines"},
    "failure": {"failure", "failures", "breakdown", "breakdowns", "fault", "faults"},
    "forecast": {"forecast", "forecasts", "forecasting", "predict", "predictive", "prediction", "predicting", "prognostics"},
    "readiness": {"readiness", "availability", "operability", "operational"},
    "finance": {"finance", "financial", "fiscal", "budget", "budgets", "funding", "expenditure", "expenditures"},
    "execution": {"execution", "obligation", "obligations", "spending", "spend", "disbursement"},
    "logistics": {"logistics", "supply", "inventory", "spares", "stock", "stockroom", "parts"},
    "personnel": {"personnel", "staff", "staffing", "workforce", "billet", "billets", "manning"},
    "training": {"training", "qualification", "qualifications", "certification", "certifications", "skills"},
    "acquisition": {"acquisition", "procurement", "contract", "contracts", "contracting", "purchasing"},
    "automation": {"automation", "automate", "automates", "automated", "workflow", "robotic"},
    "reporting": {"reporting", "report", "reports", "submission", "submissions"},
    "cybersecurity": {"cybersecurity", "cyber", "security", "vulnerability", "vulnerabilities", "threat", "threats"},
    "dashboard": {"dashboard", "dashboards", "visualization", "visualizations", "scorecard"},
    "dataset": {"dataset", "datasets", "data", "records", "logs", "history", "historical"},
    "ship": {"ship", "ships", "vessel", "vessels", "afloat"},
    "anomaly": {"anomaly", "anomalies", "outlier", "outliers", "unusual"},
}
STOP = set("a an the and or for to of in on with using uses use that this it is are be by from as at i want build develop platform system tool application product project fictional synthetic demonstration approved can across through into help enables local operational".split())
SYNONYMS = {word: concept for concept, words in CONCEPTS.items() for word in words}


def tokens(text: str) -> list[str]:
    text = re.sub(r"work[ -]orders?", "workorder", text.lower())
    return [t for t in re.findall(r"[a-z0-9]+", text) if t not in STOP and len(t) > 1]


def concepts(text: str) -> list[str]:
    return sorted({SYNONYMS[t] for t in tokens(text) if t in SYNONYMS})


class ConceptEncoder:
    name = "bundled-concept-v1 (local baseline)"
    dimensions = 512

    def encode(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        words = tokens(text)
        for word in set(words):
            canonical = SYNONYMS.get(word, word)
            index = int.from_bytes(hashlib.blake2b(canonical.encode(), digest_size=4).digest(), "little") % self.dimensions
            vector[index] += 2.5 if word in SYNONYMS else 1
        length = np.linalg.norm(vector)
        return vector / length if length else vector


class TransformerEncoder:
    def __init__(self, model_path):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_path, local_files_only=True, trust_remote_code=False, device="cpu")
        self.name = f"sentence-transformers:{model_path}"

    def encode(self, text):
        return self.model.encode(text, normalize_embeddings=True).astype(np.float32)


@lru_cache(maxsize=1)
def get_encoder():
    model_path = os.getenv("NAVYLINK_MODEL_PATH")
    return TransformerEncoder(model_path) if model_path else ConceptEncoder()


def searchable(p: dict) -> str:
    # No contacts, access URLs, visibility groups or private extensions in the vector.
    return " ".join([p["name"], p["description"], p["mission_problem"], p["domain"], p["project_type"], p["technical_summary"], *p["technologies"], *p["use_cases"], *p.get("sponsors", []), *[d["name"] + " " + d["description"] for d in p["datasets"]]])


def lexical_text(p: dict) -> str:
    return searchable(p) + " " + p["status"] + " " + p["organization"]
