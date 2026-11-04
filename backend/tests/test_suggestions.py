from sqlalchemy import func, select

from navylink.database import Project


def test_suggestions_are_editable_text_extraction_without_catalog_writes(client):
    with client.app.state.factory() as session:
        count = session.scalar(select(func.count()).select_from(Project))
    response = client.post("/api/v1/discovery/suggest-metadata", json={"text": "Build a Python and React dashboard for budget execution with Budget execution ledger and Obligation transactions."})
    assert response.status_code == 200
    result = response.json()
    assert result["domain"] == "Financial management"
    assert result["project_type"] == "Dashboard"
    assert set(result["technologies"]) == {"Python", "React"}
    assert "Budget execution ledger" in result["datasets"]
    assert result["evidence"]
    assert not {"organization", "status", "contacts", "access_instructions"} & result.keys()
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == count


def test_hidden_dataset_names_do_not_become_catalog_suggestions(client, curator):
    client.patch("/api/v1/projects/maint-07", headers=curator, json={"datasets": [{"name": "PrivateCanaryDataset", "description": "Restricted demo fixture"}]})
    response = client.post("/api/v1/discovery/suggest-metadata", json={"text": "Consider PrivateCanaryDataset for a fictional project description."})
    assert "PrivateCanaryDataset" not in response.json()["datasets"]
    unknown = client.post("/api/v1/discovery/suggest-metadata", json={"text": 'Use dataset named "My newly proposed fixture" for this dashboard.'}).json()
    assert unknown["datasets"] == ["My newly proposed fixture"]


def test_api_views_cannot_be_cached_across_identities(client):
    response = client.get("/api/v1/projects/maint-01")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Vary"] == "X-Demo-User"
