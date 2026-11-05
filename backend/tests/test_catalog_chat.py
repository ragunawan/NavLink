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
