from dataclasses import dataclass
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from fastapi import HTTPException
from sqlalchemy import select

from .database import Project

load_dotenv()


@dataclass(frozen=True)
class Identity:
    id: str
    label: str
    internal: bool = False
    groups: tuple[str, ...] = ()
    editor: bool = False


USERS = {
    "visitor": Identity("visitor", "Public visitor"),
    "analyst": Identity("analyst", "Internal analyst", True),
    "maintainer": Identity("maintainer", "Maintenance group", True, ("maintenance-demo",)),
    "curator": Identity("curator", "Catalog curator", True, ("maintenance-demo", "finance-demo"), True),
}

# Optional additional identities / overrides for a local demonstration.
if os.getenv("NAVYLINK_DEMO_USERS"):
    for row in json.loads(Path(os.environ["NAVYLINK_DEMO_USERS"]).read_text()):
        identity = Identity(**{**row, "groups": tuple(row.get("groups", []))})
        USERS[identity.id] = identity


def visible(project: Project, user: Identity) -> bool:
    return project.visibility == "public" or (project.visibility == "internal" and user.internal) or (project.visibility == "group" and bool(set(project.payload["allowed_groups"]) & set(user.groups)))


def authorized(session, user):
    # Visibility is applied before lexical indexing, vector ranking or aggregation.
    return [p for p in session.scalars(select(Project)) if visible(p, user)]


def require_project(session, project_id, user):
    p = session.get(Project, project_id)
    if p is None or not visible(p, user):
        raise HTTPException(404, "Project not found")
    return p


def present(p: Project, user: Identity):
    data = dict(p.payload)
    data.setdefault("intended_users", [])
    contacts = [c for c in data["contacts"] if c["visibility"] == "public" or (c["visibility"] == "internal" and user.internal) or (c["visibility"] == "group" and bool(set(data["allowed_groups"]) & set(user.groups)))]
    return {**data, "id": p.id, "contacts": contacts, "contacts_withheld": len(contacts) < len(data["contacts"]), "allowed_groups": data["allowed_groups"] if user.editor else [], "synthetic": True}
