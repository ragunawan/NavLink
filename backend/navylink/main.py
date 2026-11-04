import os
import json
from datetime import date
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import delete, select, text

from . import advisor
from .catalog_records import register_catalog_routes, validate_references
from .rag import answer_question
from .rag_schemas import DiscoveryAnswer, DiscoveryQuestion
from .auth import USERS, authorized, present, require_project
from .database import Project, Run, connect
from .encoding import get_encoder
from .migrations import migrate_catalog
from .registry import save_project
from .schemas import AgentRun, Assessment, CompareRequest, Comparison, Health, Overview, ProjectCreate, ProjectInput, ProjectOut, ProjectPage, Proposal, SearchResponse
from .search import filter_projects, related, search
from .seed import seed
from .suggestions import SuggestRequest, SuggestResponse, suggest_metadata


def create_app(db_url=None, auto_seed=True):
    engine, factory = connect(db_url)

    @asynccontextmanager
    async def lifespan(app):
        with factory() as session:
            migrate_catalog(session)
        if auto_seed:
            with factory() as session:
                seed(session)
        yield
        engine.dispose()

    app = FastAPI(title="NavyLINK", version="0.1.0", description="Create once, discover everywhere, improve together. Offline synthetic capability catalog. Demo identities are not authentication.", lifespan=lifespan)
    app.state.factory = factory

    def session_dep():
        with factory() as session:
            yield session

    def identity(x_demo_user: Annotated[str, Header()] = "visitor"):
        if x_demo_user not in USERS:
            raise HTTPException(401, "Unknown demo identity")
        return USERS[x_demo_user]

    def editor(user=Depends(identity)):
        if not user.editor:
            raise HTTPException(403, "Select the demo catalog curator to edit projects")
        return user

    Session = Annotated[object, Depends(session_dep)]
    User = Annotated[object, Depends(identity)]
    Editor = Annotated[object, Depends(editor)]
    prefix = "/api/v1"
    register_catalog_routes(app, prefix, session_dep, identity, editor)

    @app.middleware("http")
    async def private_api_cache(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Vary"] = "X-Demo-User"
        return response

    @app.post(prefix + "/discovery/suggest-metadata", response_model=SuggestResponse)
    def suggestions(payload: SuggestRequest, session: Session, user: User):
        return suggest_metadata(session, user, payload.text)

    @app.get("/api/health", response_model=Health)
    @app.get(prefix + "/health", response_model=Health)
    def health():
        return {"status": "ok", "encoder": get_encoder().name}

    @app.get(prefix + "/identities")
    def identities():
        return [{"id": u.id, "label": u.label, "editor": u.editor} for u in USERS.values()]

    @app.get(prefix + "/projects", response_model=list[ProjectOut])
    def projects(session: Session, user: User, domain: str | None = None, organization: str | None = None, project_type: str | None = None, status: str | None = None, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0)):
        items = filter_projects(session, user, {"domain": domain, "organization": organization, "project_type": project_type, "status": status})
        items.sort(key=lambda p: (p.payload["last_updated"], p.id), reverse=True)
        return [present(p, user) for p in items[offset:offset + limit]]

    @app.post(prefix + "/projects", response_model=ProjectOut, status_code=201)
    def create(payload: ProjectCreate, session: Session, user: Editor):
        validate_references(session, payload, user)
        payload = payload.model_copy(update={"date_created": date.today(), "last_updated": date.today()})
        p = save_project(session, str(uuid4()), payload)
        session.execute(delete(Run))  # Invalidate stored evidence snapshots on catalog mutation.
        session.commit()
        return present(p, user)

    @app.get(prefix + "/projects/page", response_model=ProjectPage)
    def project_page(session: Session, user: User, domain: str | None = None, organization: str | None = None, project_type: str | None = None, status: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        items = filter_projects(session, user, {"domain": domain, "organization": organization, "project_type": project_type, "status": status})
        items.sort(key=lambda p: (p.payload["last_updated"], p.id), reverse=True)
        return {"total": len(items), "items": [present(p, user) for p in items[offset:offset + limit]]}

    @app.post(prefix + "/projects/compare", response_model=Comparison)
    @app.post("/api/projects/compare", response_model=Comparison, include_in_schema=False)
    def compare(payload: CompareRequest, session: Session, user: User):
        if len(set(payload.project_ids)) != len(payload.project_ids):
            raise HTTPException(422, "Select distinct projects")
        return advisor.compare(session, user, payload.project_ids)

    @app.get(prefix + "/projects/{project_id}", response_model=ProjectOut)
    def detail(project_id: str, session: Session, user: User):
        return present(require_project(session, project_id, user), user)

    @app.patch(prefix + "/projects/{project_id}", response_model=ProjectOut)
    def update(project_id: str, payload: dict, session: Session, user: Editor):
        p = require_project(session, project_id, user)
        if "date_created" in payload and payload["date_created"] != p.payload.get("date_created"):
            raise HTTPException(422, "Date created is maintained by the catalog and cannot be changed")
        try:
            validated = ProjectInput.model_validate({**p.payload, **payload})
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc
        validate_references(session, validated, user, fields=set(payload))
        for required_field in ("classification", "network_accessibility", "primary_poc_email"):
            if p.payload.get(required_field) and not getattr(validated, required_field):
                raise HTTPException(422, f"{required_field} is required once supplied")
        validated = validated.model_copy(update={"last_updated": date.today()})
        p = save_project(session, project_id, validated)
        session.execute(delete(Run))
        session.commit()
        return present(p, user)

    @app.delete(prefix + "/projects/{project_id}", status_code=204)
    def remove(project_id: str, session: Session, user: Editor):
        p = require_project(session, project_id, user)
        session.delete(p)
        session.execute(text("DELETE FROM project_fts WHERE id=:id"), {"id": project_id})
        session.execute(delete(Run))
        session.commit()
        return Response(status_code=204)

    @app.get(prefix + "/search", response_model=SearchResponse)
    def search_api(session: Session, user: User, q: str = Query(min_length=1, max_length=3000), mode: Literal["hybrid", "keyword", "semantic"] = "hybrid", domain: str | None = None, organization: str | None = None, project_type: str | None = None, status: str | None = None, limit: int = Query(30, ge=1, le=100)):
        return search(session, user, q, mode, {"domain": domain, "organization": organization, "project_type": project_type, "status": status}, limit)

    @app.get(prefix + "/projects/{project_id}/related", response_model=SearchResponse)
    @app.get("/api/projects/{project_id}/related", response_model=SearchResponse, include_in_schema=False)
    def related_api(project_id: str, session: Session, user: User):
        return related(session, user, project_id)

    @app.post(prefix + "/discovery/check-duplicate", response_model=Assessment)
    @app.post("/api/discovery/check-duplicate", response_model=Assessment, include_in_schema=False)
    def check(payload: Proposal, session: Session, user: User):
        return advisor.assess(session, user, payload)

    @app.post(prefix + "/agent/discover", response_model=AgentRun | DiscoveryAnswer)
    @app.post("/api/agent/discover", response_model=AgentRun | DiscoveryAnswer, include_in_schema=False)
    def discover(payload: Proposal | DiscoveryQuestion, session: Session, user: User):
        if isinstance(payload, DiscoveryQuestion):
            return answer_question(session, user, payload)
        return advisor.discover(session, user, payload)

    @app.post(prefix + "/agent/discover/stream")
    def discover_stream(payload: Proposal, session: Session, user: User):
        def events():
            try:
                for event in advisor.discover_events(session, user, payload):
                    yield json.dumps(event) + "\n"
            except Exception:
                session.rollback()
                # Do not put database errors or partially authorized evidence in a response.
                yield json.dumps({"type": "error", "message": "Discovery could not complete. Retry against the local catalog."}) + "\n"
            finally:
                session.rollback()  # Also release any unfinished read transaction on cancellation.
        return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.get(prefix + "/agent/runs/{run_id}", response_model=AgentRun)
    def run(run_id: str, session: Session, user: User):
        return advisor.load_run(session, user, run_id)

    @app.get(prefix + "/analytics/overview", response_model=Overview)
    def overview(session: Session, user: User):
        rows = authorized(session, user)
        return {"total": len(rows), "domains": dict(Counter(p.domain for p in rows)), "statuses": dict(Counter(p.payload["status"] for p in rows)), "recent": [present(p, user) for p in sorted(rows, key=lambda p: (p.payload["last_updated"], p.id), reverse=True)[:5]], "collaborators": [present(p, user) for p in rows if p.payload["status"] == "Seeking Collaborators"][:5]}

    @app.get(prefix + "/organizations", response_model=list[str])
    def organizations(session: Session, user: User):
        return sorted({p.organization for p in authorized(session, user)})

    @app.get(prefix + "/domains", response_model=list[str])
    def domains(session: Session, user: User):
        return sorted({p.domain for p in authorized(session, user)})

    dist = Path(os.getenv("NAVYLINK_FRONTEND", "frontend/dist"))
    if (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "Endpoint not found")
            return FileResponse(dist / "index.html")

    return app


app = create_app()
