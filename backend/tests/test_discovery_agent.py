"""Grounding, bounded execution, streaming, offline and policy regression tests."""
import json
import socket
from dataclasses import replace
from datetime import datetime

import pytest
from sqlalchemy import func, select

from navylink import advisor
from navylink.auth import USERS
from navylink.database import Project, Run
from navylink.schemas import Proposal

URL = "/api/v1"
MISSION = {
    "description": "Forecast ship equipment failures and readiness using historical maintenance work orders and supply inventory.",
    "datasets": ["Maintenance work orders", "Supply inventory"], "technologies": ["Python", "React"],
}


def references(value):
    if isinstance(value, dict):
        if {"project_id", "field", "value", "url"} <= value.keys():
            yield value
        for item in value.values():
            yield from references(item)
    elif isinstance(value, list):
        for item in value:
            yield from references(item)


def test_every_citation_matches_an_authorized_record_field(client):
    run = client.post(URL + "/agent/discover", json=MISSION).json()
    citations = list(references(run))
    assert len(citations) > 30
    for ref in citations:
        response = client.get(URL + "/projects/" + ref["project_id"])
        assert response.status_code == 200
        project = response.json()
        assert ref["url"] == "/projects/" + project["id"]
        assert ref["project_name"] == project["name"]
        assert ref["value"] == project[ref["field"]]
    inspected = {i for event in run["timeline"] if event["tool"] == "get_project_details" for i in event["project_ids"]}
    assert {ref["project_id"] for ref in citations} <= inspected
    assert run["recommendation"]["decision"] == "investigate_reuse"
    assert run["recommendation"]["actions"]
    assert all(action["citations"] for action in run["recommendation"]["actions"])
    assert "unconfirmed" in run["recommendation"]["summary"]
    assert "_policy" not in run and "_records" not in run


def test_related_findings_are_inspected_and_assessed(client, monkeypatch):
    # A one-result initial retrieval forces real related-project exploration to contribute leads.
    original = advisor.search

    def narrow(*args, **kwargs):
        result = original(*args, **kwargs)
        result["results"] = result["results"][:1]
        return result

    monkeypatch.setattr(advisor, "search", narrow)
    run = client.post(URL + "/agent/discover", json=MISSION).json()
    candidates = run["assessment"]["candidates"]
    assert len(candidates) >= 2
    added = [c for c in candidates if all(o["kind"] == "related" for o in c["origins"])]
    assert added
    assert all(o["via_project_id"] for c in added for o in c["origins"])
    assert run["comparison"]


def test_constraint_states_preserve_uncertainty_and_stack_differences(client):
    run = client.post(URL + "/agent/discover", json=MISSION).json()
    candidates = {c["project"]["id"]: c for c in run["assessment"]["candidates"]}
    first = {c["dimension"]: c for c in candidates["maint-01"]["constraints"]}
    second = {c["dimension"]: c for c in candidates["maint-02"]["constraints"]}
    assert first["Licensing"]["state"] == "requires_confirmation"
    assert first["Access"]["state"] == "requires_confirmation"
    assert second["Licensing"]["state"] == "unknown"
    assert second["Integration"]["state"] == "unknown"
    assert second["Technology"]["state"] == "potential_mismatch"
    assert second["Support"]["state"] == "potential_mismatch"
    assert len(first) == 8
    assert {x["state"] for c in candidates.values() for x in c["constraints"]} <= {"unknown", "requires_confirmation", "potential_mismatch", "blocking"}


def test_candidate_selection_and_actions_preserve_distinct_reuse_paths(client):
    proposal = {**MISSION, "description": "I want to build a predictive maintenance platform that uses historical equipment failures, work orders, and supply data to forecast equipment readiness.", "datasets": ["Equipment failure history", "Maintenance work orders", "Supply inventory"]}
    run = client.post(URL + "/agent/discover", json=proposal).json()
    candidates = run["assessment"]["candidates"]
    classifications = {c["classification"] for c in candidates}
    assert {"Potential duplicate", "Relevant dataset", "Collaboration opportunity", "Complementary capability"} <= classifications
    assert len(candidates) <= advisor.CANDIDATE_LIMIT
    complementary = {c["project"]["id"] for c in candidates if c["classification"] == "Complementary capability"}
    action_sources = {ref["project_id"] for action in run["recommendation"]["actions"] for ref in action["citations"]}
    assert complementary & action_sources


def test_retired_record_is_historical_and_blocks_supported_reuse(client):
    with client.app.state.factory() as session:
        assessment = advisor.assess(session, USERS["visitor"], Proposal(**MISSION), {"results": [{"project": {"id": "maint-08"}}]})
    candidate = assessment["candidates"][0]
    assert candidate["classification"] == "Historical reference"
    assert next(c for c in candidate["constraints"] if c["dimension"] == "Support")["state"] == "blocking"
    assert advisor.recommend(assessment)["decision"] == "continue_discovery"


def test_stream_events_match_completed_persisted_workflow(client):
    response = client.post(URL + "/agent/discover/stream", json=MISSION)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["cache-control"] == "no-store"
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["type"] == "run" and events[-1]["type"] == "result"
    run = events[-1]["run"]
    assert events[0]["run_id"] == run["id"]
    activities = [e["activity"] for e in events if e["type"] == "activity"]
    assert [a["status"] for a in activities] == [status for _ in run["timeline"] for status in ("running", "complete")]
    for before, after in zip(activities[::2], activities[1::2]):
        assert before["step"] == after["step"]
        assert before["finished_at"] is None
        assert datetime.fromisoformat(after["finished_at"]) >= datetime.fromisoformat(before["started_at"])
        assert after["elapsed_ms"] >= 0
    assert [a for a in activities if a["status"] == "complete"] == run["timeline"]
    assert client.get(URL + "/agent/runs/" + run["id"]).json() == run
    assert sum(a["tool"] == "get_project_details" for a in run["timeline"]) <= advisor.INSPECTION_LIMIT
    assert sum(a["tool"] == "find_related_projects" for a in run["timeline"]) <= advisor.RELATED_SEEDS


def test_progress_precedes_actual_operation_and_cancel_leaves_no_run(client, monkeypatch):
    original = advisor.DiscoveryTools.search_projects
    calls = []

    def tracked(self, query):
        calls.append(query)
        return original(self, query)

    monkeypatch.setattr(advisor.DiscoveryTools, "search_projects", tracked)
    with client.app.state.factory() as session:
        events = advisor.discover_events(session, USERS["visitor"], Proposal(**MISSION))
        assert next(events)["type"] == "run"
        next(events)  # interpretation begins
        next(events)  # interpretation completes
        event = next(events)
        assert event["activity"]["tool"] == "search_projects"
        assert event["activity"]["status"] == "running" and calls == []
        assert next(events)["activity"]["status"] == "complete" and len(calls) == 1
        events.close()
        assert session.scalar(select(func.count()).select_from(Run)) == 0


def test_failed_tool_emits_failure_without_internal_details_or_saved_success(client, monkeypatch):
    def fail(*args):
        raise RuntimeError("PRIVATE_DATABASE_SENTINEL")
    monkeypatch.setattr(advisor.DiscoveryTools, "search_projects", fail)
    response = client.post(URL + "/agent/discover/stream", json=MISSION)
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]["type"] == "error"
    assert any(e.get("activity", {}).get("status") == "failed" for e in events)
    assert not any(e["type"] == "result" for e in events)
    assert "PRIVATE_DATABASE_SENTINEL" not in response.text
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Run)) == 0


def test_saved_run_expires_after_direct_contact_policy_change(client):
    run = client.post(URL + "/agent/discover", json=MISSION).json()
    with client.app.state.factory() as session:
        project = session.get(Project, "maint-01")
        payload = json.loads(json.dumps(project.payload))
        payload["contacts"][0]["visibility"] = "internal"
        project.payload = payload
        session.commit()
    assert client.get(URL + "/agent/runs/" + run["id"]).status_code == 404
    assert client.get(URL + "/projects/maint-01").json()["contacts"] == []


def test_saved_run_expires_after_identity_scope_changes(client, monkeypatch):
    headers = {"X-Demo-User": "maintainer"}
    run = client.post(URL + "/agent/discover", json=MISSION, headers=headers).json()
    monkeypatch.setitem(USERS, "maintainer", replace(USERS["maintainer"], groups=()))
    assert client.get(URL + "/agent/runs/" + run["id"], headers=headers).status_code == 404


def test_hidden_data_never_appears_in_stream_comparison_constraints_or_citations(client, curator):
    client.patch(URL + "/projects/maint-07", headers=curator, json={"mission_problem": "HIDDEN_MISSION equipment failure maintenance forecasting", "access_instructions": "HIDDEN_ACCESS", "license": "HIDDEN_LICENSE"})
    response = client.post(URL + "/agent/discover/stream", json=MISSION)
    assert all(sentinel not in response.text for sentinel in ["HIDDEN_MISSION", "HIDDEN_ACCESS", "HIDDEN_LICENSE", "maint-07"])
    assert client.post(URL + "/projects/compare", json={"project_ids": ["maint-01", "maint-07"]}).status_code == 404
    assert client.post(URL + "/agent/discover/stream", headers={"X-Demo-User": "invalid"}, json=MISSION).status_code == 401


def test_offline_stream_and_cited_recommendations_without_network(client, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("External connection attempted")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    response = client.post(URL + "/agent/discover/stream", json=MISSION)
    assert json.loads(response.text.splitlines()[-1])["type"] == "result"


def test_no_match_has_no_invented_citations_or_clearance_to_build(client):
    response = client.post(URL + "/agent/discover", json={"description": "Create a marble sculpture exhibition featuring coral portraits and ceramic mosaics."})
    run = response.json()
    assert run["assessment"]["candidates"] == []
    assert run["recommendation"]["decision"] == "continue_discovery"
    assert run["recommendation"]["citations"] == []
    assert run["recommendation"]["gaps"]


@pytest.mark.parametrize("description,expected", [
    ("Map corrosion inspection findings and prioritize hull coating repair schedules.", "maint-05"),
    ("Prioritize cybersecurity vulnerabilities and remediation.", "cyber-01"),
    ("Coordinate exercise milestones and readiness assessment schedules.", "ready-04"),
])
def test_specific_mission_terms_work_beyond_the_concept_vocabulary(client, description, expected):
    run = client.post(URL + "/agent/discover", json={"description": description}).json()
    candidates = {c["project"]["id"]: c for c in run["assessment"]["candidates"]}
    assert expected in candidates
    assert candidates[expected]["classification"] == "Potential duplicate"
    assert candidates[expected]["citations"]


@pytest.mark.parametrize("patch", [{"description": " " * 20}, {"datasets": [" "]}, {"technologies": ["x" * 201]}, {"project_ids": ["maint-07"]}])
def test_proposal_contract_rejects_empty_or_unsupported_input(client, patch):
    assert client.post(URL + "/agent/discover/stream", json={**MISSION, **patch}).status_code == 422
