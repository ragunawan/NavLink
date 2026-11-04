from dataclasses import dataclass
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import object_session

from .database import Datasource, Person, Project
from .schemas import ProjectInput

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


def visible(project, user: Identity) -> bool:
    return project.visibility == "public" or (project.visibility == "internal" and user.internal) or (project.visibility == "group" and bool(set(project.payload["allowed_groups"]) & set(user.groups)))


def authorized(session, user):
    # Visibility is applied before lexical indexing, vector ranking or aggregation.
    return [p for p in session.scalars(select(Project)) if visible(p, user)]


def require_project(session, project_id, user):
    p = session.get(Project, project_id)
    if p is None or not visible(p, user):
        raise HTTPException(404, "Project not found")
    return p


def present_record(record, user):
    return {**record.payload, "allowed_groups": record.payload["allowed_groups"] if user.editor else []}


def require_record(session, model, key, user, label):
    record = session.get(model, key)
    if record is None or not visible(record, user):
        raise HTTPException(404, f"{label} not found")
    return record


def present(p: Project, user: Identity):
    # Defaults allow existing JSON catalog records to remain readable without inventing metadata.
    data = ProjectInput.model_validate(p.payload).model_dump(mode="json")
    session = object_session(p)

    def contact_visible(contact):
        return contact["visibility"] == "public" or (contact["visibility"] == "internal" and user.internal) or (contact["visibility"] == "group" and bool(set(data["allowed_groups"]) & set(user.groups)))

    def person_visible(email):
        person = session.get(Person, email) if session else None
        matching = [c for c in data["contacts"] if c["method"].casefold() == email]
        return person is not None and visible(person, user) and (not matching or any(contact_visible(c) for c in matching))

    contacts = []
    for contact in data["contacts"]:
        if not contact_visible(contact):
            continue
        linked_person = session.get(Person, contact["method"].casefold()) if session else None
        if linked_person is None or visible(linked_person, user):
            contacts.append(contact)
    primary = data["primary_poc_email"] if data["primary_poc_email"] and person_visible(data["primary_poc_email"]) else None
    members = [email for email in data["team_members"] if person_visible(email)]
    if primary:
        person = session.get(Person, primary)
        contacts = [{**contact, "name": person.payload["full_name"], "role": person.payload["job_title"]} if contact["method"].casefold() == primary else contact for contact in contacts]
    if primary and not any(c["method"].casefold() == primary for c in data["contacts"]):
        person = session.get(Person, primary)
        contacts.append({"name": person.payload["full_name"], "role": person.payload["job_title"], "method": primary, "visibility": person.visibility})
    source = session.get(Datasource, data["datasource"]) if session and data["datasource"] else None
    source_visible = source is not None and visible(source, user)
    return {**data, "id": p.id, "contacts": contacts,
            "contacts_withheld": any(c["method"] not in {item["method"] for item in contacts} for c in data["contacts"]) or bool(data["primary_poc_email"] and not primary),
            "primary_poc_email": primary, "team_members": members,
            "personnel_withheld": bool(data["primary_poc_email"] and not primary) or len(members) < len(data["team_members"]),
            "datasource": data["datasource"] if source_visible else None,
            "datasource_withheld": bool(data["datasource"] and not source_visible),
            "allowed_groups": data["allowed_groups"] if user.editor else [], "synthetic": True}
