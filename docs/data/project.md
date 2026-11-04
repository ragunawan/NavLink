| Column Name | Data Type | Required | Description / Options |
|---|---|---|---|
| Project ID | UUID / String | Y | Unique identifier for each project. Primary Key. |
| Project Name | String | Y | Official name of the project or digital product. |
| Project Description | Text | Y | Brief description of what the project does and its capabilities. |
| Mission Problem | Text | Y | Problem, challenge, or mission need the project addresses. |
| Project Type | List | Y | Dataset, Dashboard, Software, Automation, Model, Application, Analytics Product, Documentation, Other |
| Classification | String | Y | CUI, SECRET, TOP SECRET, ETC |
| Mission Domain | List | Y | Financial Management, Logistics, Readiness, Maintenance, Personnel, Acquisition, Cybersecurity, Other |
| Owning Organization | String | Y | Navy command, program office, warfare center, or participating organization responsible for the project. |
| Network Accessibility | List | Y | NMCI, CANES, SIPR, Other |
| Project Status | List | Y | Concept, In Development, Operational, Retired |
| Team Lead / Primary POC | String (Email) | Y | Email of the primary project contact. References Personnel dataset. |
| Team Members | List (Email) | N | Email addresses of all personnel associated with the project. References Personnel dataset. |
| Sponsors | List (String) | N | List of Project Sponsors |
| Project URL | URL | N | Link to the approved project location, application, or repository. |
| Documentation URL | URL | N | Link to documentation, user guides, or technical documentation. |
| Datasource | String | N | Name of Datasource |
| Access Information | Text | N | Instructions for accessing the project or requesting access. |
| Technologies Used | List | N | Technologies, programming languages, platforms, or frameworks used. |
| Date Created | Date | Y | Date the project was added to the catalog. |
| Last Updated | Date | Y | Date the project was updated. |