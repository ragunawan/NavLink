"""Editable, evidence-linked metadata suggestions. No catalog writes or invented owners."""
import re

from pydantic import BaseModel, Field

from .auth import authorized
from .encoding import concepts


class SuggestRequest(BaseModel):
    text: str = Field(min_length=15, max_length=8000)


class SuggestResponse(BaseModel):
    domain: str | None
    project_type: str | None
    datasets: list[str]
    technologies: list[str]
    evidence: list[dict[str, str]]
    notice: str = "Editable deterministic suggestions from your text and authorized dataset names. Review before applying; no catalog record has been saved."


DOMAIN_CONCEPTS = {
    "Financial management": {"finance", "execution"}, "Logistics": {"logistics"},
    "Readiness": {"readiness"}, "Maintenance": {"maintenance", "failure"},
    "Personnel": {"personnel", "training"}, "Acquisition": {"acquisition"}, "Cybersecurity": {"cybersecurity"},
}
TECHNOLOGIES = ["Python", "React", "TypeScript", "JavaScript", "SQLite", "SQL", "R", "Shiny", "Power BI", "Tableau", "Parquet", "ONNX", "scikit-learn", "Java", "NumPy", "DuckDB"]


def suggest_metadata(session, user, text):
    known = set(concepts(text))
    scores = {domain: len(known & indicators) for domain, indicators in DOMAIN_CONCEPTS.items()}
    domain = max(scores, key=scores.get) if any(scores.values()) else None
    kind = None
    for pattern, label in [(r"\bdashboards?\b", "Dashboard"), (r"\bdatasets?\b", "Dataset"), (r"\b(automate|automation|automated)\b", "Automation"), (r"\b(model|machine learning)\b", "Model"), (r"\b(app|application|platform)\b", "Application"), (r"\b(tool|connector|software)\b", "Software"), (r"\banalytics\b", "Analytics Product"), (r"\b(documentation|user guide|manual)\b", "Documentation")]:
        if re.search(pattern, text, re.I):
            kind = label
            break
    technologies = [tech for tech in TECHNOLOGIES if re.search(r"(?<!\w)" + re.escape(tech) + r"(?!\w)", text, 0 if tech == "R" else re.I)]
    datasets = sorted({d["name"] for p in authorized(session, user) for d in p.payload["datasets"] if re.search(r"(?<!\w)" + re.escape(d["name"]) + r"(?!\w)", text, re.I)})
    # Explicitly named new datasets are text extraction, not a claim that they exist in the catalog.
    datasets = list(dict.fromkeys(datasets + re.findall(r"\bdataset\s+(?:named\s+|called\s+)?[\"']([^\"']{3,120})[\"']", text, re.I)))[:20]
    evidence = [{"field": "domain", "suggested_value": domain, "matched_text": ", ".join(sorted(known & DOMAIN_CONCEPTS[domain]))}] if domain else []
    if kind:
        evidence.append({"field": "project_type", "suggested_value": kind, "matched_text": "An explicit capability term in the supplied description"})
    evidence.extend({"field": field, "suggested_value": value, "matched_text": value} for field, values in [("datasets", datasets), ("technologies", technologies)] for value in values)
    return {"domain": domain, "project_type": kind, "datasets": datasets, "technologies": technologies, "evidence": evidence}
