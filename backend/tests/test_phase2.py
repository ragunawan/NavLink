from navylink.schemas import Proposal


def test_full_proposal_and_mission_only(client):
    payload = {"proposed_name": "Fictional Readiness Idea", "mission_problem": "Forecast equipment failures from historical maintenance work orders and supply data.", "intended_users": ["Maintenance planners"], "desired_capabilities": ["Failure forecasting"], "technologies": ["Python"], "domain": "Maintenance"}
    response = client.post("/api/v1/agent/discover", json=payload)
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["proposal"]["proposed_name"] == payload["proposed_name"]
    assert run["assessment"]["proposal"] == run["proposal"]
    assert run["generation_mode"] == "deterministic"
    for candidate in run["assessment"]["candidates"]:
        assert candidate["relationship"] in {"Potential Duplicate", "Strongly Related", "Complementary", "Weakly Related"}
        assert candidate["similarity_components"]["matching_mission_terms"]
        assert candidate["differences"]


def test_comparison_real_audiences_and_shared_attributes(client):
    response = client.post("/api/v1/projects/compare", json={"project_ids": ["maint-01", "maint-02"]})
    assert response.status_code == 200
    result = response.json()
    assert result["shared_intended_users"]
    assert result["similarities"]
    assert result["projects"][0]["intended_users"]


def test_audience_difference_is_an_explicit_relationship_factor(client):
    response = client.post("/api/v1/discovery/check-duplicate", json={"description": "Forecast ship equipment failures and readiness using historical equipment failures, maintenance work orders and supply parts data.", "intended_users": ["A different fictional audience"]})
    first = next(c for c in response.json()["candidates"] if c["project"]["id"] == "maint-01")
    assert first["relationship"] == "Strongly Related"
    assert any("intended users" in text for text in first["differences"])


def test_phase2_endpoint_aliases_share_the_same_authorization(client):
    assert client.post("/api/discovery/check-duplicate", json={"mission_problem": "Forecast equipment failures from maintenance work orders."}).status_code == 200
    assert client.get("/api/projects/maint-01/related").status_code == 200
    assert client.get("/api/projects/maint-07/related").status_code == 404
    assert client.post("/api/projects/compare", json={"project_ids": ["maint-01", "maint-07"]}).status_code == 404
    answer = client.post("/api/agent/discover", json={"question": "Find financial dashboards", "generation": "deterministic"})
    assert answer.status_code == 200 and answer.json()["facts"]
