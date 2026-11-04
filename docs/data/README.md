# Catalog field implementation

The field definitions in [project.md](project.md), [people.md](people.md), and [datasource.md](datasource.md) are connected to the API, registry forms, project detail view, comparison, and authorized discovery responses.

## Project fields

| Documented field | API field | Implementation |
| --- | --- | --- |
| Project ID | `id` | Server-generated UUID for new projects; existing string IDs remain valid. Displayed read-only. |
| Project Name | `name` | Required name in registration and detail views. |
| Project Description | `description` | Required description. |
| Mission Problem | `mission_problem` | Required mission problem; retained by search and advisory workflows. |
| Project Type | `project_type` | Dataset, Dashboard, Software, Automation, Model, Application, Analytics Product, Documentation, Other. |
| Classification | `classification` | Required recorded text for new registrations. Stored separately from application visibility. |
| Mission Domain | `domain` | Existing mission domains plus Other; existing custom domain names remain valid. |
| Owning Organization | `organization` | Required organization. |
| Network Accessibility | `network_accessibility` | Required nonempty list for new registrations: NMCI, CANES, SIPR, Other. |
| Project Status | `status` | Concept, In Development, Operational, Retired; the existing Seeking Collaborators value is retained for compatibility and collaboration discovery. |
| Team Lead / Primary POC | `primary_poc_email` | Required for new registrations. Normalized email references a registered, available person. |
| Team Members | `team_members` | Optional list of normalized personnel email references. |
| Sponsors | `sponsors` | Optional list, displayed in details and comparison and included in project search text. |
| Project URL | `project_url` | Optional HTTP/HTTPS project location link. Existing repository and demonstration URLs remain supported. |
| Documentation URL | `documentation_url` | Existing optional HTTP/HTTPS documentation link. |
| Datasource | `datasource` | Optional name referencing a registered, available datasource. Associated datasets remain a separate existing list. |
| Access Information | `access_instructions` | Existing access information and request instructions. |
| Technologies Used | `technologies` | Existing searchable list. |
| Date Created | `date_created` | Assigned by the server for new registrations and immutable through the API. |
| Last Updated | `last_updated` | Set by the server on project creation and update. Imported historical dates remain intact until an edit. |

The required classification, network, and primary POC fields cannot be cleared once supplied. New entries use `ProjectCreate`; existing project documents retain compatible defaults through `ProjectInput` and `ProjectOut`.

## Personnel

The `/people` interface supports search by name, email, organization, job title, and expertise. Catalog curators can create, edit, and delete unreferenced records.

| Documented field | API field |
| --- | --- |
| Email | `email` — required, unique primary key; trimmed and case normalized; immutable after creation. |
| Full Name | `full_name` — required. |
| Organization | `organization` — required. |
| Job Title | `job_title` — required. |
| Work Phone | `work_phone` — optional. |
| Areas of Expertise | `areas_of_expertise` — optional list. |

Endpoints: `GET/POST /api/v1/people` and `GET/PATCH/DELETE /api/v1/people/{email}`.

## Datasources

The `/datasources` interface supports search by name, description, mission domain, and organization. Curators can create, edit, and delete unreferenced records. The source document calls its description “Project Description” and describes its name as “Name of Project”; these are interpreted as the datasource's name and description.

| Documented field | API field |
| --- | --- |
| Name | `name` — required unique reference key; immutable after creation. |
| Project Description | `description` — required datasource description. |
| Mission Domain | `domain` — required. |
| Owning Organization | `organization` — required. |

Endpoints: `GET/POST /api/v1/datasources` and `GET/PATCH/DELETE /api/v1/datasources/{name}`. URL-encode identifier path segments; datasource names containing slashes are supported.

## Compatibility and permissions

- `File(s)` and `Keywords / Tags` have been removed. The API rejects `files` and `tags` on writes. A one-time startup migration removes them from existing JSON records, rebuilds the affected vectors and lexical documents, and invalidates saved runs that could cite removed fields. Documentation and project URL links remain supported.

- Startup creates the new SQLite tables without replacing existing project records. A one-time migration derives personnel from existing email contacts and datasources from associated dataset metadata, retaining their applicable visibility. The migration marker prevents deleted registry entries from being recreated at every restart.
- Existing projects missing the new fields show unknown or empty values. Creation dates, classifications, primary POCs, and network deployment claims are not invented for older records. These records remain editable; existing project IDs and routes remain valid.
- New synthetic seed fixtures record UNCLASSIFIED and network Other. Their existing local laptop deployment does not imply NMCI, CANES, or SIPR deployment. No reset is required to upgrade an existing database.
- Old Software tool and Analytics product values remain accepted. Filters for Software and Analytics Product also find those old values. Financial Management and the existing Financial management domain spelling match the same catalog filter.
- Personnel and datasource records use the existing public/internal/group visibility policy and curator edit role. Unauthorized records return the same 404 as missing records. Non-editors do not receive group membership policy.
- Project responses redact unavailable personnel emails and datasource references. The detail view, search results, analytics, comparison, and assistant use the authorized project representation. Referenced people cannot be deleted while primary/team references remain; referenced datasources cannot be deleted while linked projects remain.
- The project form preserves references unavailable to the current editor when editing other metadata. Classification is catalog metadata; it does not grant access or replace the application's visibility policy.
- A registered primary POC supplies approved contact information to discovery workflows when visible. Existing contact visibility still applies. Registry writes invalidate saved advisory runs so changed personnel or datasource evidence is not replayed.
- `make reset` now clears the synthetic personnel and datasource registries along with projects and saved runs. It remains an explicitly destructive demo reset.

## Sample catalog

[data/sample](../../data/sample/) contains 500 projects, 176 people and 120 datasources. The importer validates the complete set, unique identifiers, dates, and personnel/datasource references before opening the database. Lists use semicolons. CSV project IDs and historical dates are preserved. Financial Management is normalized to the existing Financial management domain. Referenced datasource descriptions also populate associated datasets for discovery. Missing technical details and reuse terms remain unknown.

All sample records are fictional and imported with public demo visibility. Classification and network values are catalog metadata. Loading samples replaces projects, personnel, datasources, domain/organization lookups, search indexes, and saved workflow history in one transaction. A failed write rolls back the replacement. Repeating the command produces the same catalog without duplicates. Startup leaves the imported catalog in place.

Stop the API before replacement, then run:

```sh
PYTHONPATH=backend .venv/bin/python -m navylink.import_sample --dry-run
make sample
make run
```

`make sample` uses `NAVYLINK_DB` from the environment or `.env` (default `data/navylink.db`). It automatically saves a timestamped SQLite backup beside the database and prints its path before replacing records. To restore, stop the API and restore that backup to the configured database path. Use `--directory PATH` with the Python command to select another directory containing the same three CSV filenames and columns.

The Docker image includes these CSVs at `/app/sample`. With the API stopped, load its persistent database using `docker compose run --rm navylink python -m navylink.import_sample --directory /app/sample --replace`, then restart the service. `make reset` returns to the separate 56-project regression fixture catalog.

The catalog browses 50 projects per page and shows the complete authorized, filtered count. `GET /api/v1/projects/page` returns `{total, items}` with `limit` and `offset`; the existing list endpoint remains available.

## Verification

Verified November 4, 2026: **94 backend tests**, **18 regression browser journeys**, **2 browser checks against the imported sample catalog**, and the TypeScript/Vite production build passed. Database integrity and all 500 persistent search documents were checked.

The production TypeScript/Vite build, backend tests, and browser suite cover field round trips, mandatory metadata, malformed email and URL rejection, reference integrity, duplicate identifiers, role/group boundaries, redaction, legacy JSON reads, canonical/legacy filters, one-time migration, and full personnel → datasource → project create/edit flows. Browser checks also cover small-screen registries and all existing search, advisor, comparison, assistant, and CRUD workflows.

Run:

```sh
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run build
# With the sample catalog active at port 8000:
NAVYLINK_SAMPLE_TEST=1 npm --prefix frontend test -- sample-import.spec.ts
```

Run the remaining browser journeys against the separate regression fixture server as described in the [main README](../../README.md#verification-and-evaluation).
