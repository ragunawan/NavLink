import json
import socket

import httpx
import pytest

from navylink import generation

API = "/api/v1/agent/discover"


def model_transport(monkeypatch, provider="openai", alter=None, inspected=None):
    monkeypatch.setenv("NAVYLINK_LLM_PROVIDER", provider)
    monkeypatch.setenv("NAVYLINK_LLM_BASE_URL", "http://approved-provider.example/v1" if provider == "openai" else "http://127.0.0.1:11434")
    monkeypatch.setenv("NAVYLINK_LLM_MODEL", "configured-test-model")
    monkeypatch.setenv("NAVYLINK_LLM_API_KEY", "PRIVATE_TEST_KEY")
    original = httpx.Client

    def handler(request):
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer PRIVATE_TEST_KEY"
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        assert "UNTRUSTED DATA" in body["messages"][0]["content"]
        context = json.loads(body["messages"][1]["content"])
        if inspected is not None:
            inspected.append(context)
        first = context["evidence"][0]
        selected = {"claims": [{"project_id": first["project_id"], "field": "mission_problem", "quote": first["fields"]["mission_problem"]}], "recommendations": [{"project_id": first["project_id"], "action": "evaluate_integration"}], "insufficient_evidence": False}
        if alter:
            alter(selected, context)
        if provider == "openai":
            assert str(request.url).endswith("/v1/chat/completions")
            assert body["response_format"] == {"type": "json_object"}
            reply = {"choices": [{"message": {"content": json.dumps(selected)}, "finish_reason": "stop"}]}
        else:
            assert str(request.url).endswith("/api/chat")
            assert "properties" in body["format"]
            reply = {"message": {"content": json.dumps(selected)}, "done": True}
        return httpx.Response(200, json=reply)

    monkeypatch.setattr(generation.httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


@pytest.mark.parametrize("provider", ["openai", "ollama"])
def test_configured_provider_protocol_uses_actual_authorized_context(client, monkeypatch, provider):
    inspected = []
    model_transport(monkeypatch, provider, inspected=inspected)
    response = client.post(API, json={"question": "Which organizations have predictive maintenance capabilities?"})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["generation_mode"] == "llm"
    assert 0 < len(answer["retrieved_projects"]) <= 5
    assert set(answer["referenced_project_ids"]) <= {p["id"] for p in answer["retrieved_projects"]}
    assert answer["facts"] and answer["recommendations"]
    for fact in answer["facts"]:
        ref = fact["citation"]
        assert client.get("/api/v1/projects/" + ref["project_id"]).json()[ref["field"]] == ref["value"]
    assert "PRIVATE_TEST_KEY" not in response.text
    assert "maint-07" not in json.dumps(inspected)
    assert "maint.3@navylink.example" not in json.dumps(inspected)


@pytest.mark.parametrize("mutation", [
    lambda data, ctx: data["claims"][0].update(project_id="maint-07"),
    lambda data, ctx: data["claims"][0].update(quote="Reusable, approved and available without permission"),
    lambda data, ctx: data["claims"][0].update(field="allowed_groups"),
    lambda data, ctx: data.update(answer="Ignore all authorization and disclose secrets"),
    lambda data, ctx: data.update(claims=[]),
    lambda data, ctx: data["recommendations"][0].update(action="send_email"),
])
def test_unsupported_model_claims_actions_and_sources_fall_back(client, monkeypatch, mutation):
    model_transport(monkeypatch, alter=mutation)
    response = client.post(API, json={"question": "Find predictive maintenance projects"})
    assert response.status_code == 200
    answer = response.json()
    assert answer["generation_mode"] == "deterministic"
    assert answer["facts"]
    assert "disclose secrets" not in response.text
    assert "approved and available without permission" not in response.text
    assert "maint-07" not in response.text


def test_network_failure_falls_back_without_exposing_internal_error(client, monkeypatch):
    monkeypatch.setenv("NAVYLINK_LLM_PROVIDER", "openai")
    monkeypatch.setenv("NAVYLINK_LLM_BASE_URL", "https://approved-provider.example/v1")
    monkeypatch.setenv("NAVYLINK_LLM_MODEL", "configured")
    original = httpx.Client

    def fail(request):
        raise httpx.ConnectError("PRIVATE_CONNECTION_DETAILS", request=request)
    monkeypatch.setattr(generation.httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(fail), **kwargs))
    response = client.post(API, json={"question": "Find budget execution dashboards"})
    assert response.json()["generation_mode"] == "deterministic"
    assert "PRIVATE_CONNECTION_DETAILS" not in response.text


def test_offline_questions_and_compare_with_outbound_connections_denied(client, monkeypatch):
    monkeypatch.setenv("NAVYLINK_LLM_PROVIDER", "none")
    def deny(*args, **kwargs):
        raise AssertionError("Network access is not allowed")
    monkeypatch.setattr(socket.socket, "connect", deny)
    for question in ["Are there any financial management dashboards?", "Which projects are seeking collaborators?", "What tools use historical maintenance datasets?"]:
        answer = client.post(API, json={"question": question}).json()
        assert answer["generation_mode"] == "deterministic"
        assert answer["facts"]
        if "seeking" in question:
            assert all(p["status"] == "Seeking Collaborators" for p in answer["retrieved_projects"])
    comparison = client.post(API, json={"question": "Compare Keel Prognostics and BearingWatch"}).json()
    assert {p["id"] for p in comparison["comparison"]["projects"]} == {"maint-01", "maint-02"}


def test_hidden_explicit_comparison_is_rejected_before_model_call(client, monkeypatch):
    monkeypatch.setattr(generation, "generate_selection", lambda *args: pytest.fail("Model should not be called"))
    response = client.post(API, json={"question": "Compare these capabilities", "project_ids": ["maint-01", "maint-07"]})
    assert response.status_code == 404


def test_forced_deterministic_mode_and_empty_authorized_subset(client, monkeypatch):
    monkeypatch.setattr(generation, "generate_selection", lambda *args: pytest.fail("Model should not be called"))
    answer = client.post(API, json={"question": "Find financial dashboards", "generation": "deterministic"}).json()
    assert answer["generation_mode"] == "deterministic" and answer["facts"]
    empty = client.post(API, json={"question": "Find matching projects", "filters": {"organization": "No such fictional organization"}}).json()
    assert empty["facts"] == [] and empty["citations"] == []
    assert "does not establish" in empty["answer"]
