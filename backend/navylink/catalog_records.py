"""Personnel and datasource registries, scoped by the existing demo identity policy."""
from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from .auth import present_record, require_record, visible
from .database import Datasource, Person, Project, Run
from .schemas import DatasourceInput, DatasourceOut, PersonInput, PersonOut


def validate_references(session, payload, user, fields=None):
    fields = {"primary_poc_email", "team_members", "datasource"} if fields is None else fields
    # Omitted PATCH fields retain their stored references, including redacted ones.
    # Explicit assignments always require a currently available record.
    emails = ([payload.primary_poc_email] if "primary_poc_email" in fields else []) + (payload.team_members if "team_members" in fields else [])
    for email in emails:
        if not email:
            continue
        person = session.get(Person, email)
        if person is None or not visible(person, user):
            raise HTTPException(422, "Select an available person for the primary POC and team members")
    if "datasource" in fields and payload.datasource:
        record = session.get(Datasource, payload.datasource)
        if record is None or not visible(record, user):
            raise HTTPException(422, "Select an available datasource")


def save_record(session, model, key, payload):
    record = session.get(model, key)
    if record is None:
        record = model(**{"email" if model is Person else "name": key})
        session.add(record)
    record.payload = payload.model_dump(mode="json")
    record.visibility = payload.visibility
    return record


def commit_catalog(session):
    try:
        session.execute(delete(Run))
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "A record with that identifier already exists") from exc


def register_catalog_routes(app, prefix, session_dep, identity, editor):
    Session = Annotated[object, Depends(session_dep)]
    User = Annotated[object, Depends(identity)]
    Editor = Annotated[object, Depends(editor)]

    def get_people(session, user):
        return sorted([present_record(p, user) for p in session.scalars(select(Person)) if visible(p, user)], key=lambda p: (p["full_name"].casefold(), p["email"]))

    @app.get(prefix + "/people", response_model=list[PersonOut])
    def people(session: Session, user: User):
        return get_people(session, user)

    @app.get(prefix + "/people/{email:path}", response_model=PersonOut)
    def person(email: str, session: Session, user: User):
        return present_record(require_record(session, Person, email.casefold(), user, "Person"), user)

    @app.post(prefix + "/people", response_model=PersonOut, status_code=201)
    def create_person(payload: PersonInput, session: Session, user: Editor):
        if session.get(Person, payload.email):
            raise HTTPException(409, "A person with that email cannot be added")
        record = save_record(session, Person, payload.email, payload)
        commit_catalog(session)
        return present_record(record, user)

    @app.patch(prefix + "/people/{email:path}", response_model=PersonOut)
    def update_person(email: str, payload: dict, session: Session, user: Editor):
        record = require_record(session, Person, email.casefold(), user, "Person")
        try:
            validated = PersonInput.model_validate({**record.payload, **payload})
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc
        if validated.email != record.email:
            raise HTTPException(422, "Email is the person's identifier and cannot be changed")
        record = save_record(session, Person, record.email, validated)
        commit_catalog(session)
        return present_record(record, user)

    @app.delete(prefix + "/people/{email:path}", status_code=204)
    def delete_person(email: str, session: Session, user: Editor):
        record = require_record(session, Person, email.casefold(), user, "Person")
        if any(p.payload.get("primary_poc_email") == record.email or record.email in p.payload.get("team_members", []) for p in session.scalars(select(Project))):
            raise HTTPException(409, "This person is referenced by catalog projects; remove those references first")
        session.delete(record)
        commit_catalog(session)

    @app.get(prefix + "/datasources", response_model=list[DatasourceOut])
    def datasources(session: Session, user: User):
        return sorted([present_record(d, user) for d in session.scalars(select(Datasource)) if visible(d, user)], key=lambda d: d["name"].casefold())

    @app.get(prefix + "/datasources/{name:path}", response_model=DatasourceOut)
    def datasource(name: str, session: Session, user: User):
        return present_record(require_record(session, Datasource, name, user, "Datasource"), user)

    @app.post(prefix + "/datasources", response_model=DatasourceOut, status_code=201)
    def create_datasource(payload: DatasourceInput, session: Session, user: Editor):
        if session.get(Datasource, payload.name):
            raise HTTPException(409, "A datasource with that name cannot be added")
        record = save_record(session, Datasource, payload.name, payload)
        commit_catalog(session)
        return present_record(record, user)

    @app.patch(prefix + "/datasources/{name:path}", response_model=DatasourceOut)
    def update_datasource(name: str, payload: dict, session: Session, user: Editor):
        record = require_record(session, Datasource, name, user, "Datasource")
        try:
            validated = DatasourceInput.model_validate({**record.payload, **payload})
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc
        if validated.name != record.name:
            raise HTTPException(422, "Datasource name is its identifier and cannot be changed")
        record = save_record(session, Datasource, record.name, validated)
        commit_catalog(session)
        return present_record(record, user)

    @app.delete(prefix + "/datasources/{name:path}", status_code=204)
    def delete_datasource(name: str, session: Session, user: Editor):
        record = require_record(session, Datasource, name, user, "Datasource")
        if any(p.payload.get("datasource") == record.name for p in session.scalars(select(Project))):
            raise HTTPException(409, "This datasource is referenced by catalog projects; remove those references first")
        session.delete(record)
        commit_catalog(session)
