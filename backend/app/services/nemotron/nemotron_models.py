"""
Pydantic models for the Nemotron client and agent layer.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# OpenAI-compatible chat models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ToolFunction(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolDefinition(BaseModel):
    type: Literal["function"] = "function"
    function: ToolFunction


class ChatRequest(BaseModel):
    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    tool_choice: str = "auto"
    max_tokens: int = 512
    temperature: float = 0.1
    stream: bool = False


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: Literal["function"]
    function: ToolCallFunction


class AssistantMessage(BaseModel):
    role: Literal["assistant"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class Choice(BaseModel):
    index: int
    message: AssistantMessage
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


# ---------------------------------------------------------------------------
# CIVICHEAT agent structured decision output
# ---------------------------------------------------------------------------

class RecommendedAction(BaseModel):
    action: str
    reason: str
    urgency: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"


class ReassessmentPlan(BaseModel):
    recommended: bool = True
    interval_minutes: int = 60


class AgentDecision(BaseModel):
    """
    Structured final decision from the CIVICHEAT Nemotron agent.
    Validated by Pydantic — never accept malformed data silently.
    """
    decision: str
    priority_zone: str = ""
    risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"] = "HIGH"
    risk_score: int = Field(0, ge=0, le=100)
    evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reassessment: ReassessmentPlan = Field(default_factory=ReassessmentPlan)

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> "AgentDecision":  # type: ignore[override]
        """Coerce evidence items to strings if model returns dicts."""
        if isinstance(obj, dict):
            if "evidence" in obj and isinstance(obj["evidence"], list):
                coerced = []
                for item in obj["evidence"]:
                    if isinstance(item, str):
                        coerced.append(item)
                    elif isinstance(item, dict):
                        # Convert common evidence dict shapes to readable string
                        parts = []
                        for k, v in item.items():
                            parts.append(f"{k}: {v}")
                        coerced.append(", ".join(parts))
                    else:
                        coerced.append(str(item))
                obj["evidence"] = coerced
        return super().model_validate(obj, **kwargs)


class AgentResponse(BaseModel):
    """Full agent endpoint response."""
    agent: dict[str, str]
    decision: AgentDecision
    tools_used: list[str]
    fallback_mode: bool = False
    fallback_reason: str | None = None


class ActionPlanResponse(BaseModel):
    """Structured government action plan."""
    incident_summary: str
    priority: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]
    zone: str
    actions: list[RecommendedAction]
    evidence: list[str]
    limitations: list[str]
    reassessment: ReassessmentPlan
    fallback_mode: bool = False


class PublicAdvisoryResponse(BaseModel):
    """AI-generated public advisory draft."""
    title: str
    body: str
    disclaimer: str = "AI-generated draft — requires official review before publication."
    fallback_mode: bool = False
