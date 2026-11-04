def test_catalog_chat_returns_grounded_projects_without_openai(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/chat/catalog", json={"question": "How would I build a predictive maintenance workflow?"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "local"
    assert data["projects"]
    assert all(35 <= project["reliability"] <= 95 for project in data["projects"])
    assert "workflow" in data["answer"].casefold()
    assert data["suggested_questions"]
