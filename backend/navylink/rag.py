"""Authorized retrieval and independently validated answer construction."""
from uuid import uuid4

from . import generation
from .advisor import DiscoveryTools, compare
from .auth import authorized, present, require_project
from .evidence import citation
from .rag_schemas import DiscoveryAnswer, ModelAnswer
from .schemas import DOMAINS, STATUSES
from .search import search

FIELDS = ("name", "mission_problem", "description", "organization", "domain", "project_type", "status", "datasets", "technologies", "intended_users", "contacts", "access_instructions", "license", "deployment", "integration", "documentation_url")
ACTION_TEXT = {
    "investigate_reuse": "Investigate possible reuse with the owner; permission and suitability remain unconfirmed.",
    "contact_owner": "Use an approved listed contact to ask about the capability; no contact has been made.",
    "explore_collaboration": "Discuss the stated mission and possible collaboration with the owning organization.",
    "evaluate_integration": "Confirm schemas, dependencies, approved deployment and integration compatibility before adoption.",
}


def field_text(value):
    if value is None or value == "":
        return "Unknown / not stated"
    if isinstance(value, list):
        if not value:
            return "None listed in this authorized view"
        return "; ".join(x if isinstance(x, str) else " | ".join(str(x.get(key, "")) for key in ("name", "method", "description") if x.get(key)) for x in value)
    return str(value)


def build_context(projects):
    return [{"project_id": p["id"], "fields": {field: field_text(p.get(field)) for field in FIELDS}} for p in projects]


def retrieve_evidence(session, user, request):
    filters = request.filters.model_dump(exclude_none=True)
    question = request.question.casefold()
    for status in STATUSES:
        if status.casefold() in question:
            filters.setdefault("status", status)
    for domain in DOMAINS:
        if f"in {domain.casefold()}" in question or f"{domain.casefold()} domain" in question or (domain == "Financial management" and domain.casefold() in question):
            filters.setdefault("domain", domain)
    if "dashboard" in question:
        filters.setdefault("project_type", "Dashboard")
    elif "dataset" in question and not any(term in question for term in ["tools", "use ", "using "]):
        filters.setdefault("project_type", "Dataset")
    ids = list(dict.fromkeys(request.project_ids))
    if not ids:
        ids = [p.id for p in authorized(session, user) if p.payload["name"].casefold() in question][:2]
    # Always run hybrid retrieval; explicitly named authorized records can supply comparison evidence.
    result = search(session, user, request.question, mode="hybrid", filters=filters, limit=5)
    projects = [present(require_project(session, project_id, user), user) for project_id in ids]
    seen = set(ids)
    if not ids:
        projects.extend(hit["project"] for hit in result["results"] if hit["project"]["id"] not in seen)
    return projects[:5], result["encoder"]


def validate_selection(selection, context):
    sources = {p["project_id"]: p["fields"] for p in context}
    if not selection.claims:
        raise ValueError("No grounded model claims")
    for claim in selection.claims:
        if claim.project_id not in sources or claim.field not in sources[claim.project_id] or claim.quote != sources[claim.project_id][claim.field]:
            raise ValueError("Unsupported evidence claim")
    for action in selection.recommendations:
        if action.project_id not in sources:
            raise ValueError("Unsupported action source")
        if action.action == "contact_owner" and sources[action.project_id]["contacts"] == "None listed in this authorized view":
            raise ValueError("No approved contact for selected action")


def deterministic_selection(question, projects):
    q = question.casefold()
    fields = ["mission_problem", "organization", "status"]
    if "dataset" in q or "data" in q:
        fields = ["mission_problem", "datasets", "organization"]
    if any(term in q for term in ["contact", "poc", "who", "collaborat"]):
        fields = ["mission_problem", "organization", "status", "contacts"]
    context = build_context(projects)
    return ModelAnswer.model_validate({
        "claims": [{"project_id": p["project_id"], "field": field, "quote": p["fields"][field]} for p in context for field in fields][:15],
        "recommendations": [{"project_id": p["id"], "action": "explore_collaboration" if p["status"] == "Seeking Collaborators" else "evaluate_integration"} for p in projects[:3]],
        "insufficient_evidence": not projects,
    })


def answer_question(session, user, request):
    tools = DiscoveryTools(session, user)

    def step(name, operation, detail, ids=()):
        iterator = tools.execute(name, operation, detail, ids)
        while True:
            try:
                next(iterator)
            except StopIteration as done:
                return done.value

    projects, encoder = step("hybrid_retrieval", lambda: retrieve_evidence(session, user, request), "Ran FTS5 and local semantic retrieval over the authorized filtered catalog.")
    context = step("build_authorized_context", lambda: build_context(projects), "Constructed context with stable IDs, exact metadata and approved contacts.", [p["id"] for p in projects])
    selection, detail = (None, "Deterministic mode requested; generated without an LLM.")
    if projects and request.generation == "auto":
        selection, detail = step("generate_answer", lambda: generation.generate_selection(request.question, context), "Attempted configured generation; deterministic fallback remains available.")
    mode = "deterministic"
    if selection is not None:
        try:
            step("validate_model_citations", lambda: validate_selection(selection, context), "Validated every model-selected source, field, exact quote and action ID.")
            mode = "llm"
        except ValueError:
            selection = None
            detail = "Model evidence validation failed; generated without an LLM."
    if selection is None:
        selection = step("deterministic_answer", lambda: deterministic_selection(request.question, projects), "Constructed a structured answer from authorized catalog facts and bounded next steps.")
    indexed = {p["id"]: p for p in projects}
    facts = [{"text": f"{indexed[c.project_id]['name']} — {c.field.replace('_', ' ')}: {c.quote}", "citation": citation(indexed[c.project_id], c.field), "provenance": "catalog_fact"} for c in selection.claims]
    recommendations = [{"action": ACTION_TEXT[a.action], "reason": f"An advisory next step for {indexed[a.project_id]['name']}; access and suitability are not confirmed.", "citations": [citation(indexed[a.project_id], "mission_problem"), citation(indexed[a.project_id], "access_instructions")]} for a in selection.recommendations]
    comparison = None
    if len(projects) == 2 and (request.project_ids or any(word in request.question.casefold() for word in ["difference", "compare"])):
        comparison = step("compare_projects", lambda: compare(session, user, [p["id"] for p in projects]), "Compared the two retrieved authorized records.", [p["id"] for p in projects])
    refs = [f["citation"] for f in facts] + [c for action in recommendations for c in action["citations"]]
    answer = "\n".join(f["text"] for f in facts) if facts else "No supporting record was found in the retrieved authorized subset. This does not establish that no such capability exists."
    uncertainty = ["Catalog facts are reported metadata, not independently verified capabilities.", "Retrieval is limited to at most five authorized records; results are not exhaustive.", "Licensing, data access, integration and deployment remain subject to owner confirmation."]
    if selection.insufficient_evidence:
        uncertainty.append("The supplied evidence is insufficient to establish a complete answer.")
    return DiscoveryAnswer.model_validate({"id": str(uuid4()), "question": request.question, "answer": answer, "facts": facts, "citations": refs,
        "referenced_project_ids": sorted({ref["project_id"] for ref in refs}), "retrieved_projects": projects, "recommendations": recommendations,
        "uncertainty": uncertainty, "execution_steps": tools.timeline, "generation_mode": mode, "generation_detail": detail, "encoder": encoder, "comparison": comparison})
