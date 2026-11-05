import json
import socket

import pytest
from sqlalchemy import select

from navylink.database import Project
from navylink.encoding import get_encoder
from navylink.seed import fixtures

PREFIX = "/api/v1"
PROPOSAL = {"description": "Build a predictive maintenance dashboard to forecast ship equipment failures and readiness using maintenance work orders and supply inventory.", "datasets": ["Maintenance work orders", "Supply inventory"], "domain": "Maintenance"}


def test_seed_and_authorized_metrics(client, curator):
    public = client.get(PREFIX + "/analytics/overview").json()
    all_data = client.get(PREFIX + "/analytics/overview", headers=curator).json()
    assert public["total"] == 42
    assert all_data["total"] == 56
    assert len(all_data["domains"]) == 7
    assert sum(all_data["domains"].values()) == 56
    assert sum(all_data["statuses"].values()) == 56
    assert all(p["synthetic"] for p in client.get(PREFIX + "/projects", headers=curator).json())


@pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
def test_search_modes_and_vertical_slice(client, mode):
    r = client.get(PREFIX + "/search", params={"q": PROPOSAL["description"], "mode": mode})
    assert r.status_code == 200
    result = r.json()
    assert {"maint-01", "maint-02"} & {h["project"]["id"] for h in result["results"][:5]}
    first = result["results"][0]
    assert first["evidence"] and "similarity" in first["inference"]
    p = client.get(PREFIX + "/projects/" + first["project"]["id"]).json()
    assert p["id"] == first["project"]["id"]
    related = client.get(PREFIX + "/projects/" + p["id"] + "/related").json()["results"]
    assert related and all(h["project"]["id"] != p["id"] for h in related)
    assert related[0]["evidence"]


def test_filters_before_ranking(client):
    data = client.get(PREFIX + "/search", params={"q": "budget execution", "domain": "Financial management", "status": "Operational", "project_type": "Dashboard"}).json()
    assert data["total"] == 1
    assert data["results"][0]["project"]["id"] == "fin-01"


@pytest.mark.parametrize("project_id", ["maint-06", "maint-07", "fin-07", "does-not-exist"])
def test_hidden_and_missing_indistinguishable(client, project_id):
    for suffix in ["", "/related"]:
        response = client.get(PREFIX + "/projects/" + project_id + suffix)
        assert response.status_code == 404
        assert response.json() == {"detail": "Project not found"}
    response = client.post(PREFIX + "/projects/compare", json={"project_ids": ["maint-01", project_id]})
    assert response.status_code == 404


def test_group_boundaries_and_contact_visibility(client):
    assert client.get(PREFIX + "/projects/maint-07", headers={"X-Demo-User": "analyst"}).status_code == 404
    assert client.get(PREFIX + "/projects/maint-07", headers={"X-Demo-User": "maintainer"}).status_code == 200
    assert client.get(PREFIX + "/projects/fin-07", headers={"X-Demo-User": "maintainer"}).status_code == 404
    public = client.get(PREFIX + "/projects/maint-03").json()
    assert public["contacts"] == [] and public["contacts_withheld"]
    assert client.get(PREFIX + "/projects/maint-03", headers={"X-Demo-User": "analyst"}).json()["contacts"]


def test_restricted_records_do_not_influence_public_scores(client, curator):
    def snapshot():
        r = client.get(PREFIX + "/search", params={"q": "predictive maintenance"}).json()
        r.pop("elapsed_ms")
        return r
    before = snapshot()
    response = client.patch(PREFIX + "/projects/maint-07", headers=curator, json={"description": "SECRET_SENTINEL predictive maintenance " * 50})
    assert response.status_code == 200
    assert snapshot() == before
    search = client.get(PREFIX + "/search", params={"q": "SECRET_SENTINEL", "mode": "keyword"}).json()
    assert search["total"] == 0
    for endpoint in ["/projects", "/organizations", "/analytics/overview"]:
        assert "SECRET_SENTINEL" not in client.get(PREFIX + endpoint).text
    run = client.post(PREFIX + "/agent/discover", json=PROPOSAL)
    assert "SECRET_SENTINEL" not in run.text
    assert '"id":"maint-07"' not in run.text


def test_crud_rebuilds_vectors_and_index(client, curator):
    payload = next(fixtures())[1].model_dump(mode="json")
    payload.update(name="Fictional Quasar Ledger", domain="Experimental domain", description="QuasarLedger tracks fabricated experimental cost records.")
    assert client.post(PREFIX + "/projects", json=payload).status_code == 403
    response = client.post(PREFIX + "/projects", json=payload, headers=curator)
    assert response.status_code == 201, response.text
    project_id = response.json()["id"]
    assert "Experimental domain" in client.get(PREFIX + "/domains").json()
    assert client.get(PREFIX + "/search", params={"q": "QuasarLedger", "mode": "keyword"}).json()["total"] == 1
    with client.app.state.factory() as session:
        before = session.get(Project, project_id).vector
    assert client.patch(PREFIX + "/projects/" + project_id, json={"description": "NebulaLedger manages entirely different fabricated account records."}, headers=curator).status_code == 200
    with client.app.state.factory() as session:
        assert before != session.get(Project, project_id).vector
    assert client.get(PREFIX + "/search", params={"q": "QuasarLedger", "mode": "keyword"}).json()["total"] == 0
    assert client.delete(PREFIX + "/projects/" + project_id, headers=curator).status_code == 204
    assert client.get(PREFIX + "/projects/" + project_id).status_code == 404


def test_validation_errors(client, curator):
    assert client.post(PREFIX + "/projects", json={}, headers=curator).status_code == 422
    assert client.patch(PREFIX + "/projects/maint-01", json={"visibility": "group", "allowed_groups": []}, headers=curator).status_code == 422
    assert client.patch(PREFIX + "/projects/maint-01", json={"repository_url": "javascript:alert(1)"}, headers=curator).status_code == 422
    assert client.get(PREFIX + "/search", params={"q": "hello", "mode": "invalid"}).status_code == 422
    assert client.get(PREFIX + "/projects", headers={"X-Demo-User": "unknown"}).status_code == 401
    # FTS metacharacters never become query syntax.
    assert client.get(PREFIX + "/search", params={"q": '" OR * - NEAR(foo)', "mode": "keyword"}).status_code == 200


def test_overlap_uses_evidence_and_type_rules(client):
    response = client.post(PREFIX + "/discovery/check-duplicate", json=PROPOSAL)
    assert response.status_code == 200, response.text
    candidates = {c["project"]["id"]: c for c in response.json()["candidates"]}
    assert candidates["maint-01"]["classification"] == "Potential duplicate"
    assert candidates["maint-03"]["classification"] == "Relevant dataset"
    assert candidates["maint-02"]["open_questions"]
    assert all(c["evidence"] and c["recommendation"] for c in candidates.values())
    unrelated = client.post(PREFIX + "/discovery/check-duplicate", json={"description": "Design an underwater sculpture exhibition with marble carving and coral portraits."}).json()
    assert unrelated["candidates"] == []


def test_overlap_distinguishes_prediction_targets_and_finance_type(client):
    result = client.post(PREFIX + "/discovery/check-duplicate", json=PROPOSAL).json()
    logistics = [c for c in result["candidates"] if c["project"]["id"] == "log-01"]
    assert logistics and logistics[0]["classification"] == "Complementary capability"
    finance = client.post(PREFIX + "/discovery/check-duplicate", json={"description": "Build a financial dashboard to track budget execution obligations and expenditures across funding lines."}).json()
    matches = {c["project"]["id"]: c["classification"] for c in finance["candidates"]}
    assert matches["fin-01"] == matches["fin-02"] == "Potential duplicate"


def test_agent_calls_real_tools_persists_and_isolates_runs(client, curator):
    response = client.post(PREFIX + "/agent/discover", json=PROPOSAL)
    assert response.status_code == 200, response.text
    run = response.json()
    names = {event["tool"] for event in run["timeline"]}
    assert {"search_projects", "get_project_details", "find_related_projects", "compare_projects", "find_domain_experts", "check_project_overlap", "get_access_information"} <= names
    assert run["assessment"]["candidates"] and run["comparison"]["projects"]
    assert client.get(PREFIX + "/agent/runs/" + run["id"]).json() == run
    assert client.get(PREFIX + "/agent/runs/" + run["id"], headers=curator).status_code == 404
    client.patch(PREFIX + "/projects/maint-01", headers=curator, json={"status": "Retired"})
    assert client.get(PREFIX + "/agent/runs/" + run["id"]).status_code == 404


def test_local_workflow_has_no_network_dependency(client, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Unexpected network request")
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    assert client.get(PREFIX + "/search", params={"q": "equipment failure forecasting", "mode": "semantic"}).status_code == 200
    assert client.post(PREFIX + "/agent/discover", json=PROPOSAL).status_code == 200


def test_persistence_across_app_restart(tmp_path):
    from fastapi.testclient import TestClient
    from navylink.main import create_app
    url = f"sqlite:///{tmp_path / 'persistent.db'}"
    with TestClient(create_app(url)) as client:
        client.patch(PREFIX + "/projects/maint-01", headers={"X-Demo-User": "curator"}, json={"name": "Persisted Fictional Capability"})
        run_id = client.post(PREFIX + "/agent/discover", json=PROPOSAL).json()["id"]
    with TestClient(create_app(url)) as client:
        assert client.get(PREFIX + "/projects/maint-01").json()["name"] == "Persisted Fictional Capability"
        assert client.get(PREFIX + "/agent/runs/" + run_id).status_code == 200
