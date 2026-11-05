import json

import httpx
import pytest


@pytest.fixture(autouse=True)
def clear_chat_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NAVYLINK_LLM_API_KEY", raising=False)


def test_catalog_chat_returns_grounded_projects_without_openai(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/chat/catalog", json={"question": "How would I build a predictive maintenance workflow?"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "local"
    assert data["projects"]
    assert all(35 <= project["reliability"] <= 95 for project in data["projects"])
    assert "workflow" in data["answer"].casefold()
    assert "Reuse Candidates" in data["answer"]
    assert "Liability / Omit Candidates" in data["answer"]
    assert "OpenAI generation is not configured" not in data["answer"]
    assert data["suggested_questions"]


def test_catalog_chat_list_question_does_not_force_workflow(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/chat/catalog", json={"question": "List financial dashboard projects"})
    assert response.status_code == 200
    data = response.json()
    assert data["projects"]
    assert all("financial" in (project["domain"] + " " + project["mission_problem"]).casefold() or "dashboard" in project["project_type"].casefold() for project in data["projects"])
    assert "Suggested workflow:" not in data["answer"]


def test_catalog_chat_unrelated_question_does_not_force_matches(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/chat/catalog", json={"question": "Find submarine coffee roasting projects"})
    assert response.status_code == 200
    data = response.json()
    assert data["projects"] == []


def test_catalog_chat_accepts_long_history_and_lists_unreliable_projects(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/chat/catalog", json={
        "question": "Provide me with a list of the most unreliable projects or data so that I can avoid them",
        "history": [{"role": "assistant", "content": "previous answer " * 500}],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["projects"]
    assert "Least Reliable" in data["answer"]
    assert "Reliability" in data["answer"]
    assert all(project["reliability"] <= 75 for project in data["projects"][:3])
    assert len(data["projects"]) <= 5


@pytest.mark.parametrize("question", ["ship maintenance lltm", "Find risk forecasting projects"])
def test_catalog_chat_uses_same_si_top_five_as_search(client, monkeypatch, question):
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_TEST_KEY")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "configured-test-model")
    original = httpx.Client
    rankings = []
    contexts = []

    def handler(request):
        assert request.url == "https://api.openai.com/v1/responses"
        body = json.loads(request.content)
        assert body["model"] == "configured-test-model"
        assert body["store"] is False
        if "text" in body:
            prompt = json.loads(body["input"])
            assert prompt["query"] == question
            candidates = prompt["candidates"]
            assert len(candidates) > 8
            assert not {"maint-06", "maint-07", "fin-07"} & {p["id"] for p in candidates}
            # Promote candidates outside the old eight-record chat window.
            ranking = list(reversed(candidates))
            rankings.append(ranking)
            return httpx.Response(200, json={"output_text": json.dumps({"ranked_ids": [p["id"] for p in ranking]})})
        records = body["input"].split("Authorized catalog records with local reliability scores:\n", 1)[1]
        contexts.append([json.loads(line) for line in records.splitlines()])
        return httpx.Response(200, json={"output_text": "SI-ranked catalog answer."})

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    search = client.get("/api/v1/search", params={"q": question, "mode": "openai", "limit": 5})
    chat = client.post("/api/v1/chat/catalog", json={"question": question})
    assert search.status_code == chat.status_code == 200
    expected = [hit["project"]["id"] for hit in search.json()["results"]]
    data = chat.json()
    assert len(data["projects"]) == 5
    assert [project["id"] for project in data["projects"]] == expected
    assert len(rankings) == 2
    assert len(contexts) == 1
    assert [project["id"] for project in contexts[0]] == expected
    assert [p["description"] for p in contexts[0]] == [p["description"] for p in rankings[1][:5]]
    assert data["mode"] == "openai"
    assert data["answer"] == "SI-ranked catalog answer."


@pytest.mark.parametrize("failure", ["provider_error", "invalid_ranking", "timeout"])
def test_catalog_chat_reports_si_ranking_failure(client, monkeypatch, failure):
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_TEST_KEY")
    original = httpx.Client

    def handler(request):
        assert "text" in json.loads(request.content)
        if failure == "timeout":
            raise httpx.ReadTimeout("Provider timed out", request=request)
        if failure == "provider_error":
            return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})
        return httpx.Response(200, json={"output_text": json.dumps({"ranked_ids": ["hidden-project"]})})

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    response = client.post("/api/v1/chat/catalog", json={"question": "ship maintenance lltm"})
    assert response.status_code == 502
    assert "PRIVATE_TEST_KEY" not in response.text
    assert "hidden-project" not in response.text


def test_catalog_chat_keeps_si_top_five_when_answer_generation_fails(client, monkeypatch):
    monkeypatch.setenv("NAVYLINK_LLM_API_KEY", "PRIVATE_TEST_KEY")
    # Empty primary settings use the same fallback configuration as SI search.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "")
    monkeypatch.setenv("OPENAI_MODEL", "fallback-test-model")
    original = httpx.Client
    ranked_ids = []

    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "fallback-test-model"
        assert request.headers["Authorization"] == "Bearer PRIVATE_TEST_KEY"
        if "text" in body:
            ranked_ids.extend(p["id"] for p in reversed(json.loads(body["input"])["candidates"]))
            return httpx.Response(200, json={"output_text": json.dumps({"ranked_ids": ranked_ids})})
        return httpx.Response(500)

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    response = client.post("/api/v1/chat/catalog", json={"question": "ship maintenance lltm"})
    assert response.status_code == 200
    data = response.json()
    assert [p["id"] for p in data["projects"]] == ranked_ids[:5]
    assert all(p["name"] in data["answer"] for p in data["projects"])
    assert data["mode"] == "local"
