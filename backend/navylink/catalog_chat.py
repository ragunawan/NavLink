import json
import os
import re
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from .auth import authorized, present
from .search import search


MAX_CONTEXT_CHARS = 18_000
MAX_HISTORY_CHARS = 12_000
STOPWORDS = {"what", "which", "would", "could", "should", "there", "with", "from", "that", "this", "have", "help", "using", "based", "about", "list", "show", "give"}
WORKFLOW_TERMS = {"workflow", "pipeline", "build", "implement", "combine", "end-to-end", "start", "finish", "steps", "process"}
UNRELIABLE_TERMS = {"unreliable", "avoid", "weak", "risky", "risk", "omit", "liability", "liabilities", "least"}


class CatalogChatMessage(BaseModel):
    role: str
    content: str = Field(max_length=12000)


class CatalogChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    history: list[CatalogChatMessage] = Field(default_factory=list, max_length=20)


class CatalogChatProject(BaseModel):
    id: str
    name: str
    url: str
    domain: str
    organization: str
    status: str
    project_type: str
    mission_problem: str
    datasets: list[str]
    technologies: list[str]
    reliability: int
    usefulness: str


class CatalogChatResponse(BaseModel):
    id: str
    answer: str
    projects: list[CatalogChatProject]
    suggested_questions: list[str]
    model: str
    mode: str


def _project_context(projects: list[CatalogChatProject]) -> str:
    blocks = []
    used = 0
    for project in projects:
        block = json.dumps(project.model_dump(), ensure_ascii=True)
        if used + len(block) > MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        used += len(block)
    return "\n".join(blocks)


def _projects_from_search(result) -> list[CatalogChatProject]:
    projects = []
    best = max([hit["ranking_score"] for hit in result["results"]] or [1])
    for hit in result["results"][:8]:
        project = hit["project"]
        reliability = max(35, min(95, round((hit["ranking_score"] / best) * 95)))
        projects.append(CatalogChatProject(
            id=project["id"],
            name=project["name"],
            url=f"/projects/{project['id']}",
            domain=project["domain"],
            organization=project["organization"],
            status=project["status"],
            project_type=project["project_type"],
            mission_problem=project["mission_problem"],
            datasets=[item["name"] for item in project["datasets"]],
            technologies=project["technologies"],
            reliability=reliability,
            usefulness="High" if reliability >= 75 else "Medium" if reliability >= 55 else "Low",
        ))
    return projects


def _question_terms(question: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", question.casefold()) if len(term) >= 3 and term not in STOPWORDS}


def _is_workflow_question(question: str) -> bool:
    terms = _question_terms(question)
    return bool(terms & WORKFLOW_TERMS) or "start to finish" in question.casefold()


def _is_unreliable_question(question: str) -> bool:
    return bool(_question_terms(question) & UNRELIABLE_TERMS)


def _project_text(project: CatalogChatProject) -> str:
    return " ".join([
        project.name,
        project.domain,
        project.organization,
        project.status,
        project.project_type,
        project.mission_problem,
        " ".join(project.datasets),
        " ".join(project.technologies),
    ]).casefold()


def _filter_projects(question: str, projects: list[CatalogChatProject]) -> list[CatalogChatProject]:
    terms = _question_terms(question) - WORKFLOW_TERMS - UNRELIABLE_TERMS
    if not terms:
        return projects[:5]
    filtered = []
    for project in projects:
        text = _project_text(project)
        matches = {term for term in terms if term in text}
        if matches or project.reliability >= 80:
            filtered.append(project)
    return filtered[:5]


def _catalog_reliability(project: dict) -> int:
    score = {"Operational": 82, "Seeking Collaborators": 67, "In Development": 60, "Concept": 48, "Retired": 30}.get(project["status"], 55)
    if not project.get("license"):
        score -= 6
    if not project.get("deployment"):
        score -= 6
    if not project.get("integration"):
        score -= 6
    if not project.get("datasets"):
        score -= 6
    if not project.get("contacts"):
        score -= 5
    return max(20, min(95, score))


def _unreliable_projects(session, user, question: str) -> list[CatalogChatProject]:
    terms = _question_terms(question) - UNRELIABLE_TERMS
    rows = []
    for row in authorized(session, user):
        project = present(row, user)
        text = " ".join([
            project["name"], project["domain"], project["status"], project["project_type"], project["mission_problem"],
            " ".join(item["name"] for item in project["datasets"]), " ".join(project["technologies"]),
        ]).casefold()
        if terms and not any(term in text for term in terms):
            continue
        reliability = _catalog_reliability(project)
        rows.append(CatalogChatProject(
            id=project["id"], name=project["name"], url=f"/projects/{project['id']}", domain=project["domain"],
            organization=project["organization"], status=project["status"], project_type=project["project_type"],
            mission_problem=project["mission_problem"], datasets=[item["name"] for item in project["datasets"]],
            technologies=project["technologies"], reliability=reliability,
            usefulness="Low" if reliability < 55 else "Medium" if reliability < 75 else "High",
        ))
    rows.sort(key=lambda project: (project.reliability, project.status != "Retired", project.name))
    return rows[:8]


def _format_project_line(project: CatalogChatProject) -> str:
    return f"- {project.name} -- Category {project.project_type}; Reliability {project.reliability}/100; Usefulness {project.usefulness}. {project.mission_problem}"


def _fallback(question: str, projects: list[CatalogChatProject]) -> str:
    if not projects:
        return "I could not find matching projects in the authorized catalog view. Try asking about a mission area, dataset, technology, or workflow."
    if _is_unreliable_question(question):
        return "\n".join([
            "Least Reliable / Highest Verification Burden",
            *[_format_project_line(project) for project in projects[:6]],
            "",
            "Avoid / Defer Guidance",
            "- Defer retired records unless you only need lessons learned.",
            "- Verify concept or in-development records before reuse.",
            "- Treat missing license, deployment, integration, contact, or dataset details as blockers until confirmed.",
        ])
    if not _is_workflow_question(question):
        lines = ["Closest matching projects:"]
        for project in projects[:5]:
            lines.append(_format_project_line(project))
        return "\n".join(lines)
    lead = projects[0]
    dataset_names = sorted({name for project in projects for name in project.datasets})
    technology_names = sorted({name for project in projects for name in project.technologies})
    optional = [project.name for project in projects if project.reliability < 60]
    reusable = [project.name for project in projects if project.reliability >= 70]
    supporting = [project for project in projects if project.id != lead.id]
    project_parts = [_format_project_line(project) for project in projects[:5]]
    data_steps = [f"- {name}: validate availability, schema, freshness and access before use." for name in dataset_names[:6]]
    tech_steps = [f"- {name}: candidate implementation/deployment technology from matched records." for name in technology_names[:6]]
    return "\n".join([
        "Technical Workflow",
        f"Anchor capability: {lead.name} ({lead.reliability}% useful match)",
        f"Target outcome: a predictive fleet maintenance dashboard using the strongest matching catalog capability as the baseline.",
        "",
        "1. Reusable Project Parts",
        *(project_parts or ["- No reusable project parts were identified."]),
        "",
        "2. Data Pipeline",
        *(data_steps or ["- No data sources were stated in the matched records."]),
        "- Normalize identifiers across work orders, supply parts, readiness/backlog records and project-specific crosswalks.",
        "- Create quality checks for missing dates, stale work orders, duplicate equipment IDs and unmatched parts.",
        "",
        "3. Processing And Model Layer",
        *(tech_steps or ["- No technologies were stated in the matched records."]),
        "- Join maintenance history, supply availability and backlog signals into a feature table.",
        "- Score risk or priority using the most relevant matched model/forecast project, then preserve explainable fields for watchstander review.",
        "",
        "4. Dashboard / End Result",
        "- Display prioritized maintenance risks, supply blockers, recommended actions and confidence/reliability notes.",
        "- Link each recommendation back to the source dataset or reused project pattern.",
        "- Keep export/import paths simple enough for disconnected or edge use.",
        "",
        "Reuse Candidates",
        f"{', '.join(reusable) or 'None with high local reliability.'}",
        "",
        "Supporting Candidates",
        f"{', '.join(project.name for project in supporting[:4]) or 'None identified.'}",
        "",
        "Liability / Omit Candidates",
        f"{', '.join(optional) or 'None flagged by low local reliability.'}",
        "Omit or defer any part with weak reliability, missing access instructions, unclear data ownership, stale data, or incompatible technology until verified.",
        "",
        "Required Confirmation",
        "Confirm access, licensing, data freshness, integration compatibility and ownership before using any part.",
    ])


def _extract_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text") or content.get("output_text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def _suggestions(question: str, projects: list[CatalogChatProject]) -> list[str]:
    if projects:
        lead = projects[0]
        return [
            f"How would I build a workflow using {lead.name}?",
            f"What data sources support {lead.domain} workflows?",
            "Which parts should I reuse, add, or omit?",
        ]
    return [
        "Which projects are closest to this mission?",
        "What datasets are available for this workflow?",
        "How should I build this from start to finish?",
    ]


def _history_text(history: list[CatalogChatMessage]) -> str:
    lines = []
    used = 0
    for item in reversed(history[-10:]):
        content = item.content.strip()
        if len(content) > 1800:
            content = content[:1800] + "..."
        line = f"{item.role}: {content}"
        if used + len(line) > MAX_HISTORY_CHARS:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(reversed(lines))


def answer_catalog_chat(session, user, payload: CatalogChatRequest) -> CatalogChatResponse:
    if _is_unreliable_question(payload.question):
        projects = _unreliable_projects(session, user, payload.question)
    else:
        result = search(session, user, payload.question, mode="hybrid", limit=8)
        projects = _filter_projects(payload.question, _projects_from_search(result))
    model = os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_MODEL", "terra-6.1"))
    api_key = os.getenv("OPENAI_API_KEY", os.getenv("NAVYLINK_LLM_API_KEY", ""))
    if not api_key:
        return CatalogChatResponse(id=str(uuid4()), answer=_fallback(payload.question, projects), projects=projects, suggested_questions=_suggestions(payload.question, projects), model=model, mode="local")

    history = _history_text(payload.history)
    instructions = (
        "You are LinkBot, the NavyLINK catalog chatbot. Answer only from the supplied authorized catalog records. "
        "Users may ask any freeform question about the current database; the three starter questions are examples only. "
        "First classify the user's request. If they ask to list, find, compare, or identify projects/data, answer exactly that and do not add a workflow. "
        "If they ask for unreliable, risky, avoid, liability, or omit candidates, rank records by low reliability and explain why they should be avoided, deferred, or verified. "
        "Only provide a workflow when the user explicitly asks how to build, implement, pipeline, combine, or create a workflow. "
        "For workflow requests, format the answer with clear section headings: Technical Workflow, Reusable Project Parts, Data Pipeline, Processing And Model Layer, Dashboard / End Result, Reuse Candidates, Liability / Omit Candidates, and Required Confirmation. "
        "For each workflow part, explain which catalog project or dataset supports it, how useful/reliable it is, and whether the user should reuse, add, verify, omit, or defer that part. "
        "Do not use markdown heading markers like ###. Do not output markdown links. Format project references as '- Project Name -- Category [project type]; Reliability [number]/100; Usefulness [High/Medium/Low]. Description.' "
        "If the supplied records are weakly related or insufficient, say so and do not force a match. "
        "Do not claim access, deployment approval, or reuse permission. Make gaps explicit. Keep the response concise and practical."
    )
    user_input = (
        f"Recent chat history:\n{history or 'None'}\n\n"
        f"User question:\n{payload.question}\n\n"
        f"Authorized catalog records with local reliability scores:\n{_project_context(projects) or 'No matching records.'}"
    )
    body = {
        "model": model,
        "instructions": instructions,
        "input": user_input,
        "store": False,
        "max_output_tokens": 900,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(25, connect=5), follow_redirects=False, trust_env=False) as client:
            response = client.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=body)
            response.raise_for_status()
        answer = _extract_text(response.json()) or _fallback(payload.question, projects)
        return CatalogChatResponse(id=str(uuid4()), answer=answer, projects=projects, suggested_questions=_suggestions(payload.question, projects), model=model, mode="openai")
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return CatalogChatResponse(id=str(uuid4()), answer=_fallback(payload.question, projects), projects=projects, suggested_questions=_suggestions(payload.question, projects), model=model, mode="local")
