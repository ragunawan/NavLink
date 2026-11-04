from sqlalchemy import select

from .database import Project, connect
from .migrations import migrate_catalog
from .registry import save_project
from .schemas import ProjectInput


if __name__ == "__main__":
    _, factory = connect()
    with factory() as session:
        migrate_catalog(session)
        projects = list(session.scalars(select(Project)))
        for p in projects:
            save_project(session, p.id, ProjectInput.model_validate(p.payload))
        session.commit()
        print(f"Rebuilt local vectors and lexical documents for {len(projects)} projects.")
