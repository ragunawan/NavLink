from datetime import date
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from navylink.database import Project
from navylink.auth import Identity, USERS
from navylink.main import create_app
from navylink.seed import fixtures

API = "/api/v1"
PERSON = {"email": "fictional.reviewer@navylink.example", "full_name": "Fictional Alex Harbor", "organization": "Fictional Review Lab", "job_title": "Data Engineer", "work_phone": "555-0100", "areas_of_expertise": ["AI/ML", "Logistics"]}
SOURCE = {"name": "Fictional CSV / Parquet Source", "description": "Fabricated records for catalog verification.", "domain": "Other", "organization": "Fictional Review Lab"}


def project_payload():
    return next(fixtures())[1].model_dump(mode="json")


def test_personnel_fields_crud_and_identifiers(client, curator):
    assert client.post(API + "/people", json=PERSON).status_code == 403
    created = client.post(API + "/people", headers=curator, json={**PERSON, "email": PERSON["email"].upper(), "areas_of_expertise": [" AI/ML ", "AI/ML", "Logistics"]})
    assert created.status_code == 201, created.text
    person = created.json()
    assert person == {**PERSON, "visibility": "public", "allowed_groups": []}
    url = API + "/people/" + PERSON["email"]
    assert client.get(url).json() == person
    assert client.post(API + "/people", headers=curator, json=PERSON).status_code == 409
    assert client.patch(url, headers=curator, json={"job_title": "Lead Engineer", "work_phone": None}).json()["job_title"] == "Lead Engineer"
    assert client.patch(url, headers=curator, json={"email": "different@navylink.example"}).status_code == 422
    assert client.delete(url).status_code == 403
    assert client.delete(url, headers=curator).status_code == 204
    assert client.get(url).status_code == 404


def test_datasource_fields_crud_and_path_names(client, curator):
    assert client.post(API + "/datasources", json=SOURCE).status_code == 403
    created = client.post(API + "/datasources", headers=curator, json=SOURCE)
    assert created.status_code == 201, created.text
    url = API + "/datasources/" + quote(SOURCE["name"], safe="")
    assert client.get(url).json() == {**SOURCE, "visibility": "public", "allowed_groups": []}
    assert client.post(API + "/datasources", headers=curator, json=SOURCE).status_code == 409
    assert client.patch(url, headers=curator, json={"description": "Updated synthetic source description."}).json()["description"] == "Updated synthetic source description."
    assert client.patch(url, headers=curator, json={"name": "Renamed"}).status_code == 422
    assert client.delete(url, headers=curator).status_code == 204
    assert client.get(url).status_code == 404


def test_project_documented_metadata_round_trip_and_reference_integrity(client, curator):
    client.post(API + "/people", headers=curator, json=PERSON)
    client.post(API + "/datasources", headers=curator, json=SOURCE)
    payload = {**project_payload(), "project_type": "Documentation", "domain": "Other", "classification": "CUI", "network_accessibility": ["NMCI", "CANES", "NMCI"],
               "primary_poc_email": PERSON["email"].upper(), "team_members": ["MAINT.2@NAVYLINK.EXAMPLE", "maint.2@navylink.example"], "sponsors": [" Fictional Sponsor ", "Fictional Sponsor"],
               "project_url": "https://projects.navylink.example/review", "datasource": SOURCE["name"]}
    response = client.post(API + "/projects", headers=curator, json=payload)
    assert response.status_code == 201, response.text
    project = response.json()
    assert project["primary_poc_email"] == PERSON["email"]
    assert project["team_members"] == ["maint.2@navylink.example"]
    assert project["network_accessibility"] == ["NMCI", "CANES"]
    assert project["sponsors"] == ["Fictional Sponsor"]
    assert project["date_created"] == project["last_updated"] == date.today().isoformat()
    for field in ["classification", "project_url", "datasource"]:
        assert project[field] == payload[field]
    url = API + "/projects/" + project["id"]
    assert client.get(url).status_code == 200  # Classification metadata does not replace the visibility policy.
    assert client.delete(API + "/people/" + PERSON["email"], headers=curator).status_code == 409
    assert client.delete(API + "/datasources/" + quote(SOURCE["name"], safe=""), headers=curator).status_code == 409
    assert client.patch(url, headers=curator, json={"date_created": "2020-01-01"}).status_code == 422
    assert client.patch(url, headers=curator, json={"sponsors": ["Updated sponsor"], "last_updated": "2020-01-01"}).json()["last_updated"] == date.today().isoformat()
    assert client.delete(url, headers=curator).status_code == 204
    assert client.delete(API + "/people/" + PERSON["email"], headers=curator).status_code == 204
    assert client.delete(API + "/datasources/" + quote(SOURCE["name"], safe=""), headers=curator).status_code == 204


@pytest.mark.parametrize("field,value", [("classification", None), ("classification", "   "), ("network_accessibility", []), ("network_accessibility", ["Invented network"]), ("primary_poc_email", None), ("primary_poc_email", "not-an-email"), ("primary_poc_email", "not.registered@navylink.example"), ("team_members", ["missing@navylink.example"]), ("datasource", "Unregistered datasource"), ("files", [{"name": "file", "url": "javascript:alert(1)"}])])
def test_new_project_metadata_validation(client, curator, field, value):
    response = client.post(API + "/projects", headers=curator, json={**project_payload(), field: value})
    assert response.status_code == 422, response.text


def test_hidden_personnel_and_source_references_do_not_leak(client, curator, monkeypatch):
    sentinel = "PrivateReferenceSentinel"
    private_person = {**PERSON, "email": "privatereferencesentinel@navylink.example", "visibility": "group", "allowed_groups": ["maintenance-demo"]}
    private_source = {**SOURCE, "name": sentinel, "visibility": "group", "allowed_groups": ["maintenance-demo"]}
    assert client.post(API + "/people", headers=curator, json=private_person).status_code == 201
    assert client.post(API + "/datasources", headers=curator, json=private_source).status_code == 201
    payload = {**project_payload(), "contacts": [], "primary_poc_email": private_person["email"], "team_members": [private_person["email"]], "datasource": sentinel}
    response = client.post(API + "/projects", headers=curator, json=payload)
    assert response.status_code == 201, response.text
    url = API + "/projects/" + response.json()["id"]
    public = client.get(url).json()
    assert public["primary_poc_email"] is None and public["team_members"] == [] and public["contacts"] == []
    assert public["personnel_withheld"] and public["contacts_withheld"]
    assert public["datasource"] is None and public["datasource_withheld"]
    for endpoint in ["/people", "/datasources", "/projects", "/analytics/overview", "/search?q=maintenance"]:
        assert sentinel.casefold() not in client.get(API + endpoint).text.casefold()
    assert client.get(API + "/people/" + private_person["email"]).json() == {"detail": "Person not found"}
    assert client.get(API + "/people/nonexistent@navylink.example").json() == {"detail": "Person not found"}
    assert client.get(API + "/datasources/" + sentinel).json() == {"detail": "Datasource not found"}
    assert client.get(API + "/datasources/nonexistent").json() == {"detail": "Datasource not found"}
    assert client.get(API + "/search", params={"q": sentinel, "mode": "keyword"}).json()["total"] == 0
    visible = client.get(url, headers={"X-Demo-User": "maintainer"}).json()
    assert visible["primary_poc_email"] == private_person["email"] and visible["datasource"] == sentinel
    assert visible["contacts"][0]["method"] == private_person["email"]
    assert client.get(API + "/people/" + private_person["email"], headers={"X-Demo-User": "maintainer"}).json()["allowed_groups"] == []
    assert client.post(API + "/projects", headers={"X-Demo-User": "analyst"}, json=payload).status_code == 403
    monkeypatch.setitem(USERS, "limited-curator", Identity("limited-curator", "Limited curator", internal=True, editor=True))
    limited = {"X-Demo-User": "limited-curator"}
    assert client.post(API + "/projects", headers=limited, json=payload).status_code == 422
    assert client.patch(url, headers=limited, json={"description": "An unrelated update preserving redacted project references."}).status_code == 200
    for field, value in [("primary_poc_email", private_person["email"]), ("team_members", [private_person["email"]]), ("datasource", sentinel)]:
        assert client.patch(url, headers=limited, json={field: value}).status_code == 422
    assert client.get(url, headers=curator).json()["primary_poc_email"] == private_person["email"]


def test_canonical_type_filters_find_legacy_labels(client):
    with client.app.state.factory() as session:
        for project_id, legacy in [("log-04", "Software tool"), ("maint-05", "Analytics product")]:
            project = session.get(Project, project_id)
            project.payload = {**project.payload, "project_type": legacy}
        session.commit()
    for current, legacy in [("Software", "Software tool"), ("Analytics Product", "Analytics product")]:
        result = client.get(API + "/projects", params={"project_type": current}).json()
        assert result and all(p["project_type"] in {current, legacy} for p in result)
    assert client.get(API + "/projects", params={"domain": "Financial Management"}).json()


@pytest.mark.parametrize("field,value", [("classification", None), ("network_accessibility", []), ("primary_poc_email", None)])
def test_known_required_metadata_cannot_be_cleared(client, curator, field, value):
    assert client.patch(API + "/projects/maint-01", headers=curator, json={field: value}).status_code == 422


def test_existing_json_records_keep_unknown_fields_and_remain_editable(client, curator):
    fields = {"classification", "network_accessibility", "primary_poc_email", "team_members", "sponsors", "project_url", "datasource", "date_created"}
    with client.app.state.factory() as session:
        project = session.get(Project, "maint-01")
        project.payload = {key: value for key, value in project.payload.items() if key not in fields}
        session.commit()
    record = client.get(API + "/projects/maint-01").json()
    assert record["classification"] is record["date_created"] is record["primary_poc_email"] is None
    assert record["network_accessibility"] == record["team_members"] == []
    updated = client.patch(API + "/projects/maint-01", headers=curator, json={"description": "Updated description of an existing legacy catalog record."})
    assert updated.status_code == 200, updated.text
    assert updated.json()["date_created"] is None


def test_personnel_change_invalidates_saved_evidence(client, curator):
    run = client.post(API + "/agent/discover", json={"description": "Forecast equipment failures using maintenance work orders."}).json()
    assert client.get(API + "/agent/runs/" + run["id"]).status_code == 200
    assert client.patch(API + "/people/maint.1@navylink.example", headers=curator, json={"job_title": "Updated project lead"}).status_code == 200
    assert client.get(API + "/agent/runs/" + run["id"]).status_code == 404


def test_registry_bootstrap_is_once_and_preserves_project_documents(tmp_path):
    url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    curator = {"X-Demo-User": "curator"}
    with TestClient(create_app(url)) as client:
        with client.app.state.factory() as session:
            project = session.get(Project, "maint-01")
            project.payload = {key: value for key, value in project.payload.items() if key not in {"primary_poc_email", "date_created", "classification"}}
            original = dict(project.payload)
            session.commit()
        assert client.delete(API + "/people/maint.1@navylink.example", headers=curator).status_code == 204
    with TestClient(create_app(url)) as client:
        assert client.get(API + "/people/maint.1@navylink.example").status_code == 404
        with client.app.state.factory() as session:
            assert session.get(Project, "maint-01").payload == original


@pytest.mark.parametrize("endpoint,payload", [("people", {**PERSON, "email": "bad email"}), ("people", {**PERSON, "full_name": " "}), ("people", {**PERSON, "job_title": ""}), ("people", {**PERSON, "areas_of_expertise": [" "]}), ("datasources", {**SOURCE, "description": " "}), ("datasources", {**SOURCE, "visibility": "group", "allowed_groups": []})])
def test_registry_validation(client, curator, endpoint, payload):
    assert client.post(API + "/" + endpoint, headers=curator, json=payload).status_code == 422
