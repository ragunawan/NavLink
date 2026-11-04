from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .schemas import Activity, Citation, Comparison, ProjectOut, RecommendedAction


class DiscoveryFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str | None = Field(default=None, max_length=100)
    project_type: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=100)
    organization: str | None = Field(default=None, max_length=160)


class DiscoveryQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=5, max_length=3000)
    filters: DiscoveryFilters = Field(default_factory=DiscoveryFilters)
    project_ids: list[str] = Field(default_factory=list, max_length=2)
    generation: Literal["auto", "deterministic"] = "auto"

    @field_validator("question", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


class AnswerFact(BaseModel):
    text: str
    citation: Citation
    provenance: Literal["catalog_fact"] = "catalog_fact"


class DiscoveryAnswer(BaseModel):
    id: str
    question: str
    answer: str
    facts: list[AnswerFact]
    citations: list[Citation]
    referenced_project_ids: list[str]
    retrieved_projects: list[ProjectOut]
    recommendations: list[RecommendedAction]
    uncertainty: list[str]
    execution_steps: list[Activity]
    generation_mode: Literal["llm", "deterministic"]
    generation_detail: str
    encoder: str
    comparison: Comparison | None = None


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(max_length=100)
    field: str = Field(max_length=100)
    quote: str = Field(max_length=6000)


class SelectedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(max_length=100)
    action: Literal["investigate_reuse", "contact_owner", "explore_collaboration", "evaluate_integration"]


class ModelAnswer(BaseModel):
    """The model can select exact evidence and bounded actions, not invent facts."""
    model_config = ConfigDict(extra="forbid")
    claims: list[EvidenceClaim] = Field(max_length=15)
    recommendations: list[SelectedAction] = Field(default_factory=list, max_length=5)
    insufficient_evidence: bool
