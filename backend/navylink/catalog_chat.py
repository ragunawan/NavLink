import json
import os
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from .search import search


MAX_CONTEXT_CHARS = 18_000


class CatalogChatMessage(BaseModel):
    role: str
    content: str = Field(max_length=3000)


class CatalogChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    history: list[CatalogChatMessage] = Field(default_factory=list, max_length=10)


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


def _fallback(question: str, projects: list[CatalogChatProject]) -> str:
    if not projects:
        return "I could not find matching projects in the authorized catalog view. Try asking about a mission area, dataset, technology, or workflow."
    lead = projects[0]
    dataset_names = sorted({name for project in projects for name in project.datasets})
    technology_names = sorted({name for project in projects for name in project.technologies})
    return (
        f"Best catalog lead: {lead.name} ({lead.reliability}% useful match). "
        f"It addresses: {lead.mission_problem}\n\n"
        "Suggested workflow:\n"
        "1. Start with the highest-reliability matching project and confirm access with the owner.\n"
        f"2. Reuse or inspect related data sources: {', '.join(dataset_names[:6]) or 'none stated'}.\n"
        f"3. Check technical fit against stated technologies: {', '.join(technology_names[:6]) or 'none stated'}.\n"
        "4. Add only the missing pieces that the catalog does not already cover.\n\n"
        "OpenAI generation is not configured, so this answer is a local deterministic fallback."
    )


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


def answer_catalog_chat(session, user, payload: CatalogChatRequest) -> CatalogChatResponse:
    result = search(session, user, payload.question, mode="hybrid", limit=8)
    projects = _projects_from_search(result)
    model = os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_MODEL", "terra-6.1"))
    api_key = os.getenv("OPENAI_API_KEY", os.getenv("NAVYLINK_LLM_API_KEY", ""))
    if not api_key:
        return CatalogChatResponse(id=str(uuid4()), answer=_fallback(payload.question, projects), projects=projects, suggested_questions=_suggestions(payload.question, projects), model=model, mode="local")

    history = "\n".join(f"{item.role}: {item.content}" for item in payload.history[-6:])
    instructions = (
        "You are the NavyLINK catalog chatbot. Answer only from the supplied authorized catalog records. "
        "When the user asks what exists, return concrete matching projects and why they matter. "
        "When the user asks how to build a workflow, give an end-to-end workflow: objective, pipeline steps, data sources, project/capability reuse, expected output, reliability/usefulness for each part, and what can be added or omitted. "
        "Do not claim access, deployment approval, or reuse permission. Make gaps explicit. Keep the response concise and practical for a hackathon demo."
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
