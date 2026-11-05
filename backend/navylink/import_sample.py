"""Validate and replace the demo catalog from the three related sample CSVs."""
import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import UUID

from sqlalchemy import delete

from .catalog_records import save_record
from .database import CatalogMigration, Datasource, Domain, Organization, Person, Project, Run, connect
from .migrations import REMOVED_COLUMNS
from .registry import save_project
from .schemas import DatasourceInput, PersonInput, ProjectCreate

HEADERS = {
    "people": ["Email", "Full Name", "Organization", "Job Title", "Work Phone", "Areas of Expertise"],
    "datasources": ["Name", "Project Description", "Mission Domain", "Owning Organization"],
    "projects": ["Project ID", "Project Name", "Project Description", "Mission Problem", "Project Type", "Classification", "Mission Domain", "Owning Organization", "Network Accessibility", "Project Status", "Team Lead / Primary POC", "Team Members", "Sponsors", "Project URL", "Documentation URL", "Datasource", "Access Information", "Technologies Used", "Date Created", "Last Updated"],
}


def terms(value):
    return list(dict.fromkeys(part.strip() for part in value.split(";") if part.strip()))


def domain(value):
    return "Financial management" if value == "Financial Management" else value


def rows(directory, kind):
    path = directory / f"navylink_{kind}.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames is None or len(reader.fieldnames) != len(HEADERS[kind]) or set(reader.fieldnames) != set(HEADERS[kind]):
            raise ValueError(f"{path}: expected columns {', '.join(HEADERS[kind])}")
        count = 0
        for row in reader:
            count += 1
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}:{reader.line_num}: inconsistent number of columns")
            yield {key: value.strip() for key, value in row.items()}
        if not count:
            raise ValueError(f"{path}: no records")


@dataclass
class SampleCatalog:
    people: dict[str, PersonInput]
    datasources: dict[str, DatasourceInput]
    projects: dict[str, ProjectCreate]

    def counts(self):
        return {"projects": len(self.projects), "people": len(self.people), "datasources": len(self.datasources)}


def unique(records, key, payload):
    if key in records:
        raise ValueError(f"Duplicate identifier: {key}")
    records[key] = payload


def load_sample(directory):
    """Validate all rows and cross-file references before touching the database."""
    directory = Path(directory)
    people, sources, projects = {}, {}, {}
    for row in rows(directory, "people"):
        person = PersonInput(email=row["Email"], full_name=row["Full Name"], organization=row["Organization"],
                             job_title=row["Job Title"], work_phone=row["Work Phone"] or None,
                             areas_of_expertise=terms(row["Areas of Expertise"]))
        unique(people, person.email, person)
    for row in rows(directory, "datasources"):
        source = DatasourceInput(name=row["Name"], description=row["Project Description"], domain=domain(row["Mission Domain"]), organization=row["Owning Organization"])
        unique(sources, source.name, source)
    for row in rows(directory, "projects"):
        project_id = str(UUID(row["Project ID"]))
        source_name = row["Datasource"] or None
        if source_name and source_name not in sources:
            raise ValueError(f"Project {project_id}: unknown datasource {source_name}")
        payload = ProjectCreate(
            name=row["Project Name"], description=row["Project Description"], mission_problem=row["Mission Problem"],
            project_type=row["Project Type"], classification=row["Classification"], domain=domain(row["Mission Domain"]),
            organization=row["Owning Organization"], network_accessibility=terms(row["Network Accessibility"]), status=row["Project Status"],
            primary_poc_email=row["Team Lead / Primary POC"], team_members=terms(row["Team Members"]), sponsors=terms(row["Sponsors"]),
            project_url=row["Project URL"] or None, documentation_url=row["Documentation URL"] or None,
            datasource=source_name, datasets=[{"name": source_name, "description": sources[source_name].description}] if source_name else [],
            access_instructions=row["Access Information"], technologies=terms(row["Technologies Used"]),
            date_created=row["Date Created"], last_updated=row["Last Updated"],
        )
        missing = ({payload.primary_poc_email, *payload.team_members} - people.keys())
        if missing:
            raise ValueError(f"Project {project_id}: unknown personnel {', '.join(sorted(missing))}")
        if payload.last_updated < payload.date_created:
            raise ValueError(f"Project {project_id}: last updated precedes date created")
        unique(projects, project_id, payload)
    return SampleCatalog(people, sources, projects)


def replace_catalog(session, catalog):
    """Replace records, facets, workflow history and search indexes in one transaction."""
    try:
        for model in (Run, Project, Person, Datasource, Domain, Organization):
            session.execute(delete(model))
        session.connection().exec_driver_sql("DELETE FROM project_fts")
        for email, person in catalog.people.items():
            save_record(session, Person, email, person)
        for name, source in catalog.datasources.items():
            save_record(session, Datasource, name, source)
        for project_id, payload in catalog.projects.items():
            save_project(session, project_id, payload)
        # These CSVs already contain the full registry; startup must not derive extras.
        for migration in (REMOVED_COLUMNS, "2026-11-personnel-datasources"):
            if session.get(CatalogMigration, migration) is None:
                session.add(CatalogMigration(name=migration))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return catalog.counts()


def backup_database(engine):
    path = Path(engine.url.database)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(path.name + ".backup-" + stamp)
    with sqlite3.connect(path) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("data/sample"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate CSVs without opening or changing the database")
    mode.add_argument("--replace", action="store_true", help="Back up SQLite, then replace the entire demo catalog and workflow history")
    args = parser.parse_args()
    try:
        catalog = load_sample(args.directory)
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(1, f"Import validation failed: {exc}\n")
    print(f"Validated {catalog.counts()}")
    if args.dry_run:
        return
    engine, factory = connect()
    try:
        print(f"Database backup: {backup_database(engine)}", flush=True)
        with factory() as session:
            print(f"Replaced catalog: {replace_catalog(session, catalog)}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
