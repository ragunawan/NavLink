from sqlalchemy import text

from .database import Domain, Organization, Project
from .encoding import get_encoder, lexical_text, searchable


def save_project(session, project_id, payload):
    data = payload.model_dump(mode="json")
    for model, value in [(Domain, data["domain"]), (Organization, data["organization"])]:
        if session.get(model, value) is None:
            session.add(model(name=value))
    session.flush()
    encoder = get_encoder()
    body = searchable(data)
    p = session.get(Project, project_id)
    if p is None:
        p = Project(id=project_id)
        session.add(p)
    p.organization, p.domain, p.visibility = data["organization"], data["domain"], data["visibility"]
    p.payload, p.vector, p.encoder = data, encoder.encode(body).tobytes(), encoder.name
    session.execute(text("DELETE FROM project_fts WHERE id=:id"), {"id": project_id})
    session.execute(text("INSERT INTO project_fts(id,content) VALUES (:id,:content)"), {"id": project_id, "content": lexical_text(data)})
    session.flush()
    return p
