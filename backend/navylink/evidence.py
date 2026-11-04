"""Exact, authorized record citations shared by discovery and question answering."""


def citation(project, field):
    return {"project_id": project["id"], "project_name": project["name"],
            "url": f"/projects/{project['id']}", "field": field, "value": project.get(field)}
