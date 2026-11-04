"""One-time upgrades for persisted catalog documents and retrieval indexes."""
from sqlalchemy import delete, select

from .database import CatalogMigration, Project, Run
from .registry import save_project
from .schemas import ProjectInput

REMOVED_COLUMNS = "2026-11-remove-project-files-keywords"


def migrate_catalog(session):
    if session.get(CatalogMigration, REMOVED_COLUMNS):
        return
    for project in session.scalars(select(Project)).all():
        if {"tags", "files"} & project.payload.keys():
            data = {key: value for key, value in project.payload.items() if key not in {"tags", "files"}}
            save_project(session, project.id, ProjectInput.model_validate(data))
    session.execute(delete(Run))  # Earlier snapshots may cite the removed fields.
    session.add(CatalogMigration(name=REMOVED_COLUMNS))
    session.commit()
