from datetime import date, datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue, field_validator, model_validator

PROJECT_TYPES = ["Dataset", "Dashboard", "Software", "Automation", "Model", "Application", "Analytics Product", "Documentation", "Other", "Software tool", "Analytics product"]
STATUSES = ["Concept", "In Development", "Operational", "Retired", "Seeking Collaborators"]
DOMAINS = ["Financial management", "Logistics", "Readiness", "Maintenance", "Personnel", "Acquisition", "Cybersecurity", "Other"]
NETWORKS = ["NMCI", "CANES", "SIPR", "Other"]


def normalize_email(value):
    value = value.strip().casefold()
    if len(value) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", value):
        raise ValueError("Provide a valid email address")
    return value


class RecordPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    visibility: Literal["public", "internal", "group"] = "public"
    allowed_groups: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("allowed_groups")
    @classmethod
    def validate_groups(cls, values):
        if any(not value.strip() or len(value) > 200 for value in values):
            raise ValueError("Groups must be nonempty and at most 200 characters")
        return list(dict.fromkeys(value.strip() for value in values))

    @model_validator(mode="after")
    def group_policy(self):
        if self.visibility == "group" and not self.allowed_groups:
            raise ValueError("Group visibility requires at least one authorized group")
        return self


class PersonInput(RecordPolicy):
    email: str
    full_name: str = Field(min_length=1, max_length=160)
    organization: str = Field(min_length=2, max_length=160)
    job_title: str = Field(min_length=1, max_length=160)
    work_phone: str | None = Field(default=None, max_length=80)
    areas_of_expertise: list[str] = Field(default_factory=list, max_length=30)

    _email = field_validator("email")(normalize_email)

    @field_validator("areas_of_expertise")
    @classmethod
    def expertise(cls, values):
        if any(not value.strip() or len(value) > 200 for value in values):
            raise ValueError("Expertise values must be nonempty and at most 200 characters")
        return list(dict.fromkeys(value.strip() for value in values))


class PersonOut(PersonInput):
    @model_validator(mode="after")
    def group_policy(self):
        return self


class DatasourceInput(RecordPolicy):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=5000)
    domain: str = Field(min_length=2, max_length=100)
    organization: str = Field(min_length=2, max_length=160)


class DatasourceOut(DatasourceInput):
    @model_validator(mode="after")
    def group_policy(self):
        return self


class Contact(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="Project liaison", max_length=120)
    method: str = Field(max_length=200)
    visibility: Literal["public", "internal", "group"] = "public"


class Dataset(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=1000)


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=20, max_length=5000)
    mission_problem: str = Field(min_length=10, max_length=3000)
    project_type: Literal["Dataset", "Dashboard", "Software", "Software tool", "Automation", "Model", "Application", "Analytics Product", "Analytics product", "Documentation", "Other"]
    domain: str = Field(min_length=2, max_length=100)
    organization: str = Field(min_length=2, max_length=160)
    status: Literal["Concept", "In Development", "Operational", "Retired", "Seeking Collaborators"]
    classification: str | None = Field(default=None, min_length=1, max_length=100)
    network_accessibility: list[Literal["NMCI", "CANES", "SIPR", "Other"]] = Field(default_factory=list, max_length=4)
    primary_poc_email: str | None = None
    team_members: list[str] = Field(default_factory=list, max_length=100)
    sponsors: list[str] = Field(default_factory=list, max_length=30)
    project_url: HttpUrl | None = None
    datasource: str | None = Field(default=None, min_length=1, max_length=160)
    date_created: date | None = None
    technical_summary: str = Field(default="", max_length=3000)
    contacts: list[Contact] = Field(default_factory=list, max_length=10)
    repository_url: HttpUrl | None = None
    documentation_url: HttpUrl | None = None
    demo_url: HttpUrl | None = None
    access_instructions: str = Field(default="Access and reuse terms are unknown; contact the owner.", max_length=2000)
    availability: str = Field(default="Synthetic demonstration only", max_length=250)
    visibility: Literal["public", "internal", "group"] = "public"
    allowed_groups: list[str] = Field(default_factory=list, max_length=20)
    technologies: list[str] = Field(default_factory=list, max_length=30)
    datasets: list[Dataset] = Field(default_factory=list, max_length=20)
    use_cases: list[str] = Field(default_factory=list, max_length=20)
    intended_users: list[str] = Field(default_factory=list, max_length=20)
    last_updated: date = Field(default_factory=date.today)
    license: str | None = Field(default=None, max_length=200)
    deployment: str | None = Field(default=None, max_length=200)
    integration: str | None = Field(default=None, max_length=500)
    extensions: dict[str, str] = Field(default_factory=dict)

    @field_validator("primary_poc_email")
    @classmethod
    def primary_email(cls, value):
        return normalize_email(value) if value is not None else None

    @field_validator("team_members")
    @classmethod
    def member_emails(cls, values):
        return list(dict.fromkeys(normalize_email(value) for value in values))

    @field_validator("classification", "datasource", mode="before")
    @classmethod
    def trim_metadata(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("network_accessibility")
    @classmethod
    def deduplicate_networks(cls, values):
        return list(dict.fromkeys(values))

    @field_validator("technologies", "use_cases", "allowed_groups", "intended_users", "sponsors")
    @classmethod
    def clean_lists(cls, value):
        if any(not x.strip() or len(x) > 200 for x in value):
            raise ValueError("List values must be nonempty and at most 200 characters")
        return list(dict.fromkeys(x.strip() for x in value))

    @model_validator(mode="after")
    def group_policy(self):
        if self.visibility == "group" and not self.allowed_groups:
            raise ValueError("Group visibility requires at least one authorized group")
        return self


class ProjectCreate(ProjectInput):
    classification: str = Field(min_length=1, max_length=100)
    network_accessibility: list[Literal["NMCI", "CANES", "SIPR", "Other"]] = Field(min_length=1, max_length=4)
    primary_poc_email: str


class ProjectOut(ProjectInput):
    id: str
    synthetic: bool = True
    contacts_withheld: bool = False
    personnel_withheld: bool = False
    datasource_withheld: bool = False

    @model_validator(mode="after")
    def group_policy(self):
        # Responses intentionally redact membership policy.
        return self


class ProjectPage(BaseModel):
    total: int
    items: list[ProjectOut]


class SearchHit(BaseModel):
    project: ProjectOut
    rank: int
    ranking_score: float
    evidence: list[str]
    inference: str
    citations: list["Citation"] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    mode: str
    encoder: str
    total: int
    elapsed_ms: float
    results: list[SearchHit]


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposed_name: str = Field(default="", max_length=160)
    mission_problem: str = Field(default="", max_length=3000)
    description: str = Field(default="", max_length=5000)
    intended_solution: str = Field(default="", max_length=2000)
    domain: str | None = Field(default=None, max_length=100)
    datasets: list[str] = Field(default_factory=list, max_length=20)
    technologies: list[str] = Field(default_factory=list, max_length=30)
    intended_users: list[str] = Field(default_factory=list, max_length=20)
    desired_capabilities: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("description", "mission_problem", "proposed_name", "intended_solution", "domain", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("datasets", "technologies", "intended_users", "desired_capabilities")
    @classmethod
    def validate_terms(cls, values):
        if any(not x.strip() or len(x) > 200 for x in values):
            raise ValueError("Terms must be nonempty and at most 200 characters")
        return list(dict.fromkeys(x.strip() for x in values))

    @model_validator(mode="after")
    def require_mission(self):
        if max(len(self.description), len(self.mission_problem)) < 15:
            raise ValueError("Provide a mission problem or description of at least 15 characters")
        return self

    def search_text(self):
        return " ".join(filter(None, [self.mission_problem, self.description, self.intended_solution, *self.desired_capabilities]))


class CompareRequest(BaseModel):
    project_ids: list[str] = Field(min_length=2, max_length=3)


class Comparison(BaseModel):
    projects: list[ProjectOut]
    shared_datasets: list[str]
    potential_overlap: str
    differences: list[str]
    open_questions: list[str]
    shared_technologies: list[str] = Field(default_factory=list)
    shared_intended_users: list[str] = Field(default_factory=list)
    similarities: list[str] = Field(default_factory=list)
    collaboration_opportunities: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    project_id: str
    project_name: str
    url: str
    field: str
    value: JsonValue


class ReuseConstraint(BaseModel):
    dimension: str
    state: Literal["unknown", "requires_confirmation", "potential_mismatch", "blocking"]
    detail: str
    question: str
    citation: Citation


class RetrievalOrigin(BaseModel):
    kind: Literal["hybrid", "related"]
    via_project_id: str | None = None


class SimilarityComponents(BaseModel):
    matching_concepts: list[str]
    matching_mission_terms: list[str]
    shared_datasets: list[str]
    shared_technologies: list[str]
    shared_intended_users: list[str]
    same_domain: bool | None
    catalog_status: str
    mission_concept_coverage: float
    relative_score: float
    notice: str = "Relative evidence components, not a duplicate probability."


class Candidate(BaseModel):
    project: ProjectOut
    classification: str
    evidence: list[str]
    inference: str
    recommendation: str
    open_questions: list[str]
    citations: list[Citation] = Field(default_factory=list)
    constraints: list[ReuseConstraint] = Field(default_factory=list)
    origins: list[RetrievalOrigin] = Field(default_factory=list)
    rank: int = 0
    relationship: Literal["Potential Duplicate", "Strongly Related", "Complementary", "Weakly Related"]
    similarity_components: SimilarityComponents
    differences: list[str]


class Assessment(BaseModel):
    concepts: list[str]
    candidates: list[Candidate]
    decision_notice: str
    proposal: Proposal


class Activity(BaseModel):
    step: int
    tool: str
    detail: str
    project_ids: list[str] = Field(default_factory=list)
    project_names: list[str] = Field(default_factory=list)
    status: Literal["running", "complete", "failed"] = "complete"
    started_at: datetime
    finished_at: datetime | None = None
    elapsed_ms: float = 0


class RecommendedAction(BaseModel):
    action: str
    reason: str
    citations: list[Citation]


class Recommendation(BaseModel):
    decision: Literal["investigate_reuse", "explore_collaboration", "continue_discovery"]
    summary: str
    citations: list[Citation]
    actions: list[RecommendedAction]
    gaps: list[str]


class AgentRun(BaseModel):
    id: str
    status: Literal["complete"] = "complete"
    timeline: list[Activity]
    assessment: Assessment
    comparison: Comparison | None = None
    experts: list[dict]
    access: list[dict]
    proposal: Proposal
    recommendation: Recommendation
    encoder: str
    workflow_version: int = 2
    generation_mode: Literal["deterministic"] = "deterministic"


class Overview(BaseModel):
    total: int
    domains: dict[str, int]
    statuses: dict[str, int]
    recent: list[ProjectOut]
    collaborators: list[ProjectOut]


class Health(BaseModel):
    status: str
    encoder: str
    synthetic: bool = True
    authentication: str = "Demo identity selection; not production authentication"
