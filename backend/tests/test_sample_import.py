import csv
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select, text

from navylink.database import CatalogMigration, Datasource, Person, Project, Run, connect
from navylink.encoding import get_encoder, lexical_text, searchable
from navylink.import_sample import backup_database, load_sample, replace_catalog
from navylink.main import create_app
from navylink.migrations import REMOVED_COLUMNS

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample"


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_sample_replacement_preserves_fields_links_and_is_repeatable(client):
    catalog = load_sample(SAMPLE)
    assert catalog.counts() == {"projects": 500, "people": 176, "datasources": 120}
    with client.app.state.factory() as session:
        replace_catalog(session, catalog)
        replace_catalog(session, catalog)
        assert (count(session, Project), count(session, Person), count(session, Datasource)) == (500, 176, 120)
        assert count(session, Run) == 0
        assert session.get(Project, "maint-01") is None
        assert session.scalar(text("SELECT count(*) FROM project_fts")) == 500
        for project in session.scalars(select(Project)):
            assert "tags" not in project.payload and "files" not in project.payload
            assert session.get(Person, project.payload["primary_poc_email"])
            assert all(session.get(Person, email) for email in project.payload["team_members"])
            assert session.get(Datasource, project.payload["datasource"])
            assert session.scalar(text("SELECT content FROM project_fts WHERE id=:id"), {"id": project.id}) == lexical_text(project.payload)
    project_id, payload = next(iter(catalog.projects.items()))
    response = client.get("/api/v1/projects/" + project_id)
    assert response.status_code == 200, response.text
    record = response.json()
    for field in ("name", "date_created", "last_updated", "team_members", "primary_poc_email", "datasource", "documentation_url", "technologies", "network_accessibility"):
        assert record[field] == payload.model_dump(mode="json")[field]
    assert record["contacts"][0]["method"] == record["primary_poc_email"]
    assert client.get("/api/v1/analytics/overview").json()["total"] == 500
    ids = []
    for offset in range(0, 500, 50):
        page = client.get("/api/v1/projects/page", params={"offset": offset}).json()
        assert page["total"] == 500
        ids.extend(p["id"] for p in page["items"])
    assert len(ids) == len(set(ids)) == 500
    filtered = client.get("/api/v1/projects/page", params={"domain": "Financial Management"}).json()
    assert 0 < filtered["total"] < 500
    assert all(p["domain"] == "Financial management" for p in filtered["items"])
    hits = client.get("/api/v1/search", params={"q": "CASREP field dictionary", "mode": "hybrid"}).json()["results"]
    assert project_id in {hit["project"]["id"] for hit in hits}


def rewrite_csv(path, mutate):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        headers, rows = reader.fieldnames, list(reader)
    mutate(headers, rows)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("failure", ["duplicate", "reference", "removed_column", "dates", "empty"])
def test_invalid_sample_rejected_before_replacement(tmp_path, client, failure):
    directory = tmp_path / "sample"
    shutil.copytree(SAMPLE, directory)
    path = directory / "navylink_projects.csv"

    def mutate(headers, rows):
        if failure == "duplicate":
            rows.append(rows[0].copy())
        elif failure == "reference":
            rows[0]["Team Members"] = "missing@navylink-demo.example"
        elif failure == "removed_column":
            headers.append("Keywords")
        elif failure == "dates":
            rows[0]["Date Created"] = "2099-01-01"
        else:
            rows.clear()
    rewrite_csv(path, mutate)
    with pytest.raises(ValueError):
        load_sample(directory)
    assert client.get("/api/v1/projects/maint-01").status_code == 200


def test_failed_replacement_rolls_back_and_backup_keeps_original(tmp_path, client, monkeypatch):
    import navylink.import_sample as importer
    catalog = load_sample(SAMPLE)
    engine, factory = connect(f"sqlite:///{tmp_path / 'backup-check.db'}")
    with factory() as session:
        replace_catalog(session, catalog)
    backup = backup_database(engine)
    backup_engine, backup_factory = connect(f"sqlite:///{backup}")
    try:
        with backup_factory() as session:
            assert count(session, Project) == 500
        original_save = importer.save_project

        def fail_after_first(session, project_id, payload):
            original_save(session, project_id, payload)
            raise RuntimeError("encoder failure")
        monkeypatch.setattr(importer, "save_project", fail_after_first)
        with client.app.state.factory() as session:
            with pytest.raises(RuntimeError, match="encoder failure"):
                replace_catalog(session, catalog)
            assert count(session, Project) == 56
            assert session.scalar(text("SELECT count(*) FROM project_fts")) == 56
            assert session.get(Project, "maint-01")
    finally:
        backup_engine.dispose()
        engine.dispose()


def test_startup_removes_legacy_columns_and_reindexes(tmp_path):
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    with TestClient(create_app(url)) as client:
        with client.app.state.factory() as session:
            project = session.get(Project, "maint-01")
            project.payload = {**project.payload, "tags": ["RemovedKeywordSentinel"], "files": [{"name": "RemovedFileSentinel", "url": "https://navylink.example/old"}]}
            project.vector = b"\x00" * len(project.vector)
            session.execute(text("UPDATE project_fts SET content='RemovedKeywordSentinel' WHERE id='maint-01'"))
            session.delete(session.get(CatalogMigration, REMOVED_COLUMNS))
            session.add(Run(id="old-run", user="visitor", payload={"obsolete": True}))
            session.commit()
    with TestClient(create_app(url)) as client:
        record = client.get("/api/v1/projects/maint-01").json()
        assert "tags" not in record and "files" not in record
        with client.app.state.factory() as session:
            project = session.get(Project, "maint-01")
            assert "tags" not in project.payload and "files" not in project.payload
            assert project.vector == get_encoder().encode(searchable(project.payload)).tobytes()
            assert session.scalar(text("SELECT content FROM project_fts WHERE id='maint-01'")) == lexical_text(project.payload)
            assert count(session, Run) == 0
        for field, value in (("tags", ["keyword"]), ("files", [])):
            response = client.patch("/api/v1/projects/maint-01", headers={"X-Demo-User": "curator"}, json={field: value})
            assert response.status_code == 422


def test_project_pages_scope_totals_and_filters(client):
    public = client.get("/api/v1/projects/page", params={"limit": 20}).json()
    curator = client.get("/api/v1/projects/page", params={"limit": 20}, headers={"X-Demo-User": "curator"}).json()
    assert public["total"] == 42 and curator["total"] == 56
    assert len(public["items"]) == len(curator["items"]) == 20
    assert all(p["visibility"] == "public" for p in public["items"])
    page = client.get("/api/v1/projects/page", params={"domain": "Maintenance", "limit": 2, "offset": 2}).json()
    assert page["total"] == 6 and len(page["items"]) == 2
    assert all(p["domain"] == "Maintenance" for p in page["items"])
