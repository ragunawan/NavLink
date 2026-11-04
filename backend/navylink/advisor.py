"""Bounded, offline discovery with inspectable decisions and field-level evidence."""
import hashlib
import json
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from .auth import authorized, present, require_project
from .database import Run
from .encoding import concepts, tokens
from .evidence import citation
from .schemas import AgentRun
from .search import related, search

SEARCH_LIMIT = 12
RELATED_SEEDS = 3
RELATED_LIMIT = 4
INSPECTION_LIMIT = 24
CANDIDATE_LIMIT = 8
DECISION_NOTICE = (
    "You make the final determination. Similarity does not establish duplication, "
    "permission, compatibility or reusability. No personnel were contacted and no access was requested."
)


def open_questions(p):
    return [label for key, label in [
        ("license", "Confirm licensing and reuse permission."),
        ("deployment", "Confirm deployment environment and operational support."),
        ("integration", "Confirm integration compatibility and data schemas."),
    ] if not p.get(key)] + ["Confirm current access approval and dataset availability with the owner."]


def evaluate_constraints(project, proposal):
    """Catalog statements are evidence to investigate, never permission grants."""
    constraints = []

    def add(dimension, field, question, detail=None, state=None):
        value = project[field]
        constraints.append({
            "dimension": dimension,
            "state": state or ("requires_confirmation" if value else "unknown"),
            "detail": detail or (f"Catalog states: {value}" if value else "Not stated in the catalog."),
            "question": question, "citation": citation(project, field),
        })

    add("Licensing", "license", "Does the owner authorize reuse under terms suitable for your intended use?")
    add("Access", "access_instructions", "Can your team obtain approved project and dataset access?")
    add("Deployment", "deployment", "Can this run in your approved target environment, including offline requirements?")
    add("Integration", "integration", "Are interfaces, schemas and dependencies compatible with the intended solution?")
    names = [d["name"] for d in project["datasets"]]
    matches = [name for name in names if name.casefold() in {d.casefold() for d in proposal.datasets}]
    add("Datasets", "datasets", "Are the associated datasets accessible, suitable, current and approved for this use?",
        ("Exact proposed dataset names: " + ", ".join(matches) + ". Access and suitability remain unverified.")
        if matches else "Catalog dataset associations do not establish access or suitability.")
    retired = project["status"] == "Retired"
    experimental = project["status"] in {"Concept", "In Development"}
    add("Support", "status", "Is there an active owner, operational support and a supported reuse path?",
        f"Catalog status: {project['status']}. " + ("A retired capability is a historical reference, not a supported reuse path." if retired else "Status alone does not establish operational suitability."),
        "blocking" if retired else "potential_mismatch" if experimental else "requires_confirmation")
    requested = {t.casefold() for t in proposal.technologies}
    stated = {t.casefold() for t in project["technologies"]}
    disjoint = bool(requested and stated and not requested & stated)
    add("Technology", "technologies", "Can the technical approach integrate with your proposed stack?",
        "No stated technologies coincide with the proposed stack; interoperability has not been evaluated." if disjoint
        else "A shared technology, if any, does not prove compatibility.",
        "potential_mismatch" if disjoint else None)
    add("Contact", "contacts", "Who can confirm access, ownership, reuse terms and current support?",
        "Approved project liaisons are listed; no contact has been made." if project["contacts"] else "No approved contact is available in this catalog view.")
    return constraints


def compare(session, user, ids):
    projects = [present(require_project(session, i, user), user) for i in ids]
    shared = sorted(set.intersection(*[{d["name"] for d in p["datasets"]} for p in projects]))
    shared_tags = sorted(set.intersection(*[set(p["tags"]) for p in projects]))
    shared_tech = sorted(set.intersection(*[set(p["technologies"]) for p in projects]))
    shared_users = sorted(set.intersection(*[set(p.get("intended_users", [])) for p in projects]))
    return {
        "projects": projects, "shared_datasets": shared, "shared_tags": shared_tags,
        "potential_overlap": "Shared catalog datasets and mission tags suggest overlap requiring human review." if shared or shared_tags else "No shared dataset names or tags are stated; assess mission descriptions manually.",
        "differences": [f"{p['name']}: {p['project_type']}; {p['status']}; {', '.join(p['technologies'])}; {p['organization']}" for p in projects],
        "open_questions": list(dict.fromkeys(q for p in projects for q in open_questions(p))),
        "shared_technologies": shared_tech, "shared_intended_users": shared_users,
        "similarities": [f"Shared {label}: {', '.join(values)}" for label, values in [("datasets", shared), ("technologies", shared_tech), ("intended users", shared_users), ("tags", shared_tags)] if values],
        "collaboration_opportunities": [f"{p['name']} is seeking collaborators; discuss its stated mission with {p['organization']}." for p in projects if p["status"] == "Seeking Collaborators"],
    }


def assess(session, user, proposal, hits=None):
    text = proposal.search_text()
    query_concepts = set(concepts(text))
    if hits is None:
        hits = search(session, user, text, mode="hybrid", limit=SEARCH_LIMIT)
    candidates = []
    for hit in hits["results"]:
        # A caller-supplied hit is neither an authorization decision nor an evidence snapshot.
        p = present(require_project(session, hit["project"]["id"], user), user)
        project_concepts = set(concepts(p["mission_problem"]))
        shared = query_concepts & project_concepts
        mission_concepts = query_concepts - {"dashboard", "dataset", "ship"}
        coverage = len(shared & mission_concepts) / max(1, len(mission_concepts))
        shared_data = sorted(d["name"] for d in p["datasets"] if d["name"].casefold() in {x.casefold() for x in proposal.datasets})
        word_overlap = set(tokens(text)) & set(tokens(p["mission_problem"]))
        # Specific catalog terms can establish evidence even outside the bundled concept vocabulary.
        # This keeps missions such as hull corrosion inspection discoverable without a new ontology rule.
        exact_mission_overlap = len(word_overlap) >= 3 and len(word_overlap) / max(1, len(set(tokens(text)))) >= .5
        substantive = shared - {"dataset", "dashboard", "ship", "automation", "reporting", "forecast"}
        shared_tech = sorted(set(x.casefold() for x in proposal.technologies) & set(x.casefold() for x in p["technologies"]))
        shared_users = sorted(set(x.casefold() for x in proposal.intended_users) & set(x.casefold() for x in p.get("intended_users", [])))
        same_domain = proposal.domain == p["domain"] if proposal.domain else None
        audience_differs = bool(proposal.intended_users and p.get("intended_users") and not shared_users)
        if (not substantive or len(shared) < 2) and not shared_data and not exact_mission_overlap:
            continue
        if p["status"] == "Retired":
            classification = "Historical reference"
            recommendation = "Review archived lessons with the owner; do not assume the retired capability is supported."
        elif p["project_type"] == "Dataset":
            classification = "Relevant dataset"
            recommendation = "Evaluate dataset access and suitability with the listed organization."
        elif ((coverage >= .65 and (len(shared) >= 3 or len(substantive) >= 2) and len(word_overlap) >= 3) or exact_mission_overlap) and ("failure" not in query_concepts or "failure" in project_concepts):
            classification = "Potential duplicate"
            recommendation = "Investigate this initiative before building; ask the owner whether reuse or collaboration is feasible."
        elif p["status"] == "Seeking Collaborators":
            classification = "Collaboration opportunity"
            recommendation = "Discuss the stated mission overlap with the organization seeking collaborators."
        else:
            classification = "Complementary capability"
            recommendation = "Evaluate whether this capability addresses part of the mission or provides a useful component."
        evidence = [f"Stated mission: {p['mission_problem']}", f"Catalog type / status: {p['project_type']} / {p['status']}"]
        if shared_data:
            evidence.append("Exact dataset names shared with proposal: " + ", ".join(shared_data))
        constraints = evaluate_constraints(p, proposal)
        relationship = "Potential Duplicate" if classification == "Potential duplicate" else "Complementary"
        if classification == "Historical reference":
            relationship = "Weakly Related"
        elif proposal.intended_solution.casefold() == "dataset" and p["project_type"] != "Dataset":
            relationship = "Complementary"
            classification = "Complementary capability"
            recommendation = "Evaluate this capability as a potential consumer or component of the proposed dataset; its stated deliverable differs."
        elif audience_differs and relationship == "Potential Duplicate":
            relationship = "Strongly Related"
            classification = "Complementary capability"
            recommendation = "Investigate mission overlap and the different stated audiences before choosing reuse or independent development."
        elif classification == "Complementary capability" and same_domain and coverage >= .5 and not shared_data:
            relationship = "Strongly Related"
        differences = []
        if proposal.domain and not same_domain:
            differences.append(f"Proposed domain: {proposal.domain}; catalog domain: {p['domain']}.")
        if proposal.technologies:
            differences.append(f"Proposed technologies: {', '.join(proposal.technologies)}; catalog technologies: {', '.join(p['technologies']) or 'unknown'}.")
        if proposal.intended_users:
            differences.append(f"Proposed intended users: {', '.join(proposal.intended_users)}; catalog intended users: {', '.join(p.get('intended_users', [])) or 'unknown'}.")
        if proposal.datasets:
            differences.append("Proposed datasets not stated on this record: " + (", ".join(x for x in proposal.datasets if x.casefold() not in {d['name'].casefold() for d in p['datasets']}) or "none by exact name") + ".")
        differences.append(f"Catalog technical approach: {p['technical_summary'] or 'unknown'}. Integration with the proposal is unverified.")
        candidates.append({
            "project": p, "classification": classification, "evidence": evidence,
            "inference": f"Rule-based assessment from shared mission concepts ({', '.join(sorted(shared))}) and {len(word_overlap)} exact mission terms. This is a lead for human review, not proof of duplication.",
            "recommendation": recommendation,
            "open_questions": list(dict.fromkeys(c["question"] for c in constraints)),
            "citations": [citation(p, field) for field in ["mission_problem", "project_type", "status", "datasets", "domain", "technologies", "intended_users", "technical_summary"]],
            "constraints": constraints, "origins": hit.get("origins", [{"kind": "hybrid", "via_project_id": None}]),
            "relationship": relationship, "differences": differences,
            "similarity_components": {"matching_concepts": sorted(shared), "matching_mission_terms": sorted(word_overlap), "shared_datasets": shared_data, "shared_technologies": shared_tech,
                                      "shared_intended_users": shared_users, "same_domain": same_domain, "catalog_status": p["status"], "mission_concept_coverage": round(coverage, 4),
                                      "relative_score": round(coverage * 4 + min(len(word_overlap), 10) * .2 + len(shared_data) * 1.5 + len(shared_users) * .5 + len(shared_tech) * .2 + (.4 if same_domain else 0) - (.5 if p['status']=='Retired' else 0), 4)},
        })
    priority = {"Potential duplicate": 0, "Relevant dataset": 1, "Collaboration opportunity": 2, "Complementary capability": 3, "Historical reference": 4}
    candidates.sort(key=lambda c: (
        priority[c["classification"]],
        -c["similarity_components"]["relative_score"],
        -sum(d["name"].casefold() in {x.casefold() for x in proposal.datasets} for d in c["project"]["datasets"]),
        -len(set(tokens(text)) & set(tokens(c["project"]["mission_problem"]))),
    ))
    # Keep distinct paths visible even when a proposal has many near-duplicate or dataset leads.
    quotas = {"Potential duplicate": 4, "Relevant dataset": 2, "Collaboration opportunity": 1, "Complementary capability": 1}
    selected = []
    for classification, count in quotas.items():
        selected.extend([c for c in candidates if c["classification"] == classification][:count])
    chosen = {c["project"]["id"] for c in selected}
    selected.extend(c for c in candidates if c["project"]["id"] not in chosen)
    selected = selected[:CANDIDATE_LIMIT]
    for rank, candidate in enumerate(selected, 1):
        candidate["rank"] = rank
    return {"concepts": sorted(query_concepts), "candidates": selected, "decision_notice": DECISION_NOTICE, "proposal": proposal.model_dump(mode="json")}


def recommend(assessment):
    candidates = assessment["candidates"]
    duplicates = [c for c in candidates if c["classification"] == "Potential duplicate"]
    active = [c for c in candidates if c["classification"] != "Historical reference"]
    leaders = (duplicates or active)[:2]
    if duplicates:
        decision = "investigate_reuse"
        summary = f"Investigate {', '.join(c['project']['name'] for c in leaders)} before independent development. Stated mission overlap warrants an owner review; reuse remains unconfirmed."
    elif active:
        decision = "explore_collaboration"
        summary = f"Explore {', '.join(c['project']['name'] for c in leaders)} for a component, dataset or collaboration path. The retrieved evidence does not establish a duplicate or permission to reuse."
    else:
        decision = "continue_discovery"
        summary = "No active evidence-backed lead was identified in the retrieved authorized subset. Refine the mission need and assess remaining gaps before deciding to develop independently."
    actions = []
    action_candidates = list(leaders)
    for classification in ["Relevant dataset", "Collaboration opportunity", "Complementary capability", "Historical reference"]:
        matches = [c for c in candidates if c["classification"] == classification]
        if matches and matches[0] not in action_candidates:
            action_candidates.append(matches[0])
    for c in action_candidates[:5]:
        p = c["project"]
        actions.append({
            "action": c["recommendation"],
            "reason": f"{p['name']} is assessed as {c['classification'].lower()} from its stated mission, type and status.",
            "citations": c["citations"][:3],
        })
    for c in leaders:
        unresolved = [x for x in c["constraints"] if x["state"] in {"unknown", "potential_mismatch", "blocking"}]
        if unresolved:
            actions.append({
                "action": f"Resolve reuse constraints for {c['project']['name']} before adoption.",
                "reason": "; ".join(f"{x['dimension']}: {x['detail']}" for x in unresolved),
                "citations": [x["citation"] for x in unresolved],
            })
    return {
        "decision": decision, "summary": summary,
        "citations": [ref for c in leaders for ref in c["citations"][:3]], "actions": actions,
        "gaps": [
            "This bounded retrieval covers only authorized catalog metadata; missing matches do not establish that no similar capability exists.",
            "Licensing, data access, target deployment and integration require owner confirmation. No reusable solution has been confirmed.",
        ],
    }


class DiscoveryTools:
    """Real local operations. Each execute yields progress before and after its call."""
    def __init__(self, session, user):
        self.session, self.user, self.timeline = session, user, []

    def execute(self, name, operation, detail, project_ids=()):
        started = time.perf_counter()
        activity = {
            "step": len(self.timeline) + 1, "tool": name, "detail": "Executing local catalog operation.",
            "project_ids": list(project_ids), "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "finished_at": None, "elapsed_ms": 0,
        }
        yield {"type": "activity", "activity": dict(activity)}
        try:
            result = operation()
        except Exception:
            activity.update(status="failed", detail="The local operation failed; no recommendation was completed.", finished_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), elapsed_ms=round((time.perf_counter() - started) * 1000, 3))
            self.timeline.append(activity)
            yield {"type": "activity", "activity": activity}
            raise
        activity.update(status="complete", detail=detail(result) if callable(detail) else detail,
                        finished_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), elapsed_ms=round((time.perf_counter() - started) * 1000, 3))
        self.timeline.append(activity)
        yield {"type": "activity", "activity": dict(activity)}
        return result

    def search_projects(self, query):
        return search(self.session, self.user, query, mode="hybrid", limit=SEARCH_LIMIT)

    def get_project_details(self, project_id):
        return present(require_project(self.session, project_id, self.user), self.user)

    def find_related_projects(self, project_id):
        return related(self.session, self.user, project_id, RELATED_LIMIT)

    def compare_projects(self, ids):
        return compare(self.session, self.user, ids)

    def find_domain_experts(self, domain):
        return [{"project_id": p.id, "project_name": p.payload["name"], "contacts": present(p, self.user)["contacts"]}
                for p in authorized(self.session, self.user) if p.domain == domain and present(p, self.user)["contacts"]][:5]

    def check_project_overlap(self, proposal, hits):
        return assess(self.session, self.user, proposal, hits)

    def get_access_information(self, project_id):
        p = self.get_project_details(project_id)
        return {"project_id": project_id, "instructions": p["access_instructions"], "contacts": p["contacts"], "documentation_url": p["documentation_url"]}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def policy_fingerprint(user):
    return fingerprint([user.id, user.internal, sorted(user.groups), user.editor])


def discover_events(session, user, proposal):
    """One finite state machine serves both JSON and streamed endpoints."""
    tools = DiscoveryTools(session, user)
    run_id = str(uuid4())
    yield {"type": "run", "run_id": run_id}
    text = proposal.search_text()
    yield from tools.execute("extract_concepts", lambda: concepts(text), lambda terms: "Local mission concepts: " + (", ".join(terms) or "none recognized; keyword retrieval remains available."))
    hits = yield from tools.execute("search_projects", lambda: tools.search_projects(text), lambda result: f"Executed hybrid search; retrieved {len(result['results'])} authorized leads using {result['encoder']}.")
    merged = {h["project"]["id"]: {**h, "origins": [{"kind": "hybrid", "via_project_id": None}]} for h in hits["results"]}
    for seed in hits["results"][:RELATED_SEEDS]:
        seed_id = seed["project"]["id"]
        findings = yield from tools.execute("find_related_projects", lambda i=seed_id: tools.find_related_projects(i), "Inspected related mission, dataset and tag connections.", [seed_id])
        for h in findings["results"]:
            project_id = h["project"]["id"]
            if project_id not in merged and len(merged) < INSPECTION_LIMIT:
                merged[project_id] = {**h, "origins": []}
            if project_id in merged:
                merged[project_id]["origins"].append({"kind": "related", "via_project_id": seed_id})
    for project_id, hit in merged.items():
        hit["project"] = yield from tools.execute("get_project_details", lambda i=project_id: tools.get_project_details(i), "Retrieved authorized mission, datasets, technical approach and status.", [project_id])
    assessment = yield from tools.execute("check_project_overlap", lambda: tools.check_project_overlap(proposal, {"results": list(merged.values())}), "Classified inspected records using stated missions, dataset names, type and status.", list(merged))
    ids = [c["project"]["id"] for c in assessment["candidates"]]
    comparison = None
    if len(ids) >= 2:
        comparison = yield from tools.execute("compare_projects", lambda: tools.compare_projects(ids[:2]), "Compared the two leading assessed projects side by side.", ids[:2])
    access = []
    for project_id in ids:
        item = yield from tools.execute("get_access_information", lambda i=project_id: tools.get_access_information(i), "Read approved access instructions and available contacts; no external action taken.", [project_id])
        access.append(item)
    def constraints():
        for candidate in assessment["candidates"]:
            candidate["constraints"] = evaluate_constraints(candidate["project"], proposal)
        return assessment
    assessment = yield from tools.execute("evaluate_reuse_constraints", constraints, "Evaluated licensing, access, deployment, integration, datasets, support, technology and contact uncertainties.", ids)
    domain = proposal.domain or (assessment["candidates"][0]["project"]["domain"] if ids else "")
    experts = yield from tools.execute("find_domain_experts", lambda: tools.find_domain_experts(domain), "Retrieved approved project liaisons; expertise is not independently verified.")
    recommendation = yield from tools.execute("recommend", lambda: recommend(assessment), "Synthesized cited next steps and unresolved reuse questions from inspected records.", ids)
    result = AgentRun.model_validate({
        "id": run_id, "status": "complete", "timeline": tools.timeline, "assessment": assessment,
        "comparison": comparison, "experts": experts, "access": access, "proposal": proposal,
        "recommendation": recommendation, "encoder": hits["encoder"], "workflow_version": 3,
    }).model_dump(mode="json")
    referenced = set(merged) | {e["project_id"] for e in experts}
    payload = {**result, "_policy": policy_fingerprint(user),
               "_records": {i: fingerprint(tools.get_project_details(i)) for i in sorted(referenced)}}
    session.add(Run(id=run_id, user=user.id, payload=payload))
    session.commit()
    yield {"type": "result", "run": result}


def discover(session, user, proposal):
    for event in discover_events(session, user, proposal):
        if event["type"] == "result":
            return event["run"]
    raise RuntimeError("Discovery ended without a result")


def load_run(session, user, run_id):
    record = session.get(Run, run_id)
    if not record or record.payload.get("workflow_version") != 3 or record.user != user.id or record.payload.get("_policy") != policy_fingerprint(user):
        raise HTTPException(404, "Run not found")
    for project_id, digest in record.payload.get("_records", {}).items():
        try:
            project = present(require_project(session, project_id, user), user)
        except HTTPException:
            raise HTTPException(404, "Run not found") from None
        if fingerprint(project) != digest:
            raise HTTPException(404, "Run not found")
    return AgentRun.model_validate(record.payload)
