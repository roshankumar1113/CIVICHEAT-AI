"""
Phase 4 tests — Nemotron client, agent tools, agent loop, API endpoints.

All Nemotron calls are mocked — no live API required.
Phase 1/2/3 pipelines are exercised via their real code paths.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.fortyguard.fortyguard_parser import build_demo_intelligence
from app.services.heat_risk.risk_engine import run_risk_analysis
from app.services.nemotron.exceptions import (
    NemotronAuthError,
    NemotronMalformedResponseError,
    NemotronTimeoutError,
    NemotronUnavailableError,
)
from app.services.nemotron.nemotron_agent import (
    CIVICHEAT_TOOLS,
    AgentTools,
    build_fallback_decision,
)
from app.services.nemotron.nemotron_client import NemotronClient, _normalise_base_url
from app.services.nemotron.nemotron_models import (
    AgentDecision,
    AssistantMessage,
    ChatResponse,
    Choice,
    RecommendedAction,
    ToolCall,
    ToolCallFunction,
    Usage,
)
from app.services.priority.priority_engine import run_priority_analysis

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_demo_context() -> dict[str, Any]:
    """Build a real Phase 3 context from demo data."""
    intel = build_demo_intelligence()
    risk = run_risk_analysis(intel)
    priority = run_priority_analysis(risk)
    ctx = dict(priority.agent_context)
    ctx["data_limitations"] = priority.data_limitations
    return ctx


def _make_chat_response(
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    finish_reason: str = "stop",
) -> ChatResponse:
    msg = AssistantMessage(role="assistant", content=content)
    if tool_calls:
        msg.tool_calls = [
            ToolCall(
                id=f"call_{i}",
                type="function",
                function=ToolCallFunction(
                    name=tc["name"],
                    arguments=json.dumps(tc.get("args", {})),
                ),
            )
            for i, tc in enumerate(tool_calls)
        ]
        finish_reason = "tool_calls"
    return ChatResponse(
        id="test-id",
        object="chat.completion",
        created=1700000000,
        model="nvidia/nemotron-mini-4b-instruct",
        choices=[Choice(index=0, message=msg, finish_reason=finish_reason)],
        usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


def _valid_decision_json() -> str:
    return json.dumps({
        "decision": "Phoenix shows HIGH risk heat conditions. Immediate review recommended.",
        "priority_zone": "ZONE-001",
        "risk_level": "HIGH",
        "risk_score": 67,
        "evidence": ["Mean temperature 38.46°C", "HIGH risk classification"],
        "recommended_actions": [
            {"action": "Issue public advisory", "reason": "HIGH risk", "urgency": "HIGH"}
        ],
        "limitations": ["CIVICHEAT heuristic score only"],
        "reassessment": {"recommended": True, "interval_minutes": 60},
    })


# ---------------------------------------------------------------------------
# 1. URL normalisation
# ---------------------------------------------------------------------------

class TestUrlNormalisation:
    def test_url_without_v1_gets_v1_appended(self):
        assert _normalise_base_url("https://integrate.api.nvidia.com") == "https://integrate.api.nvidia.com/v1"

    def test_url_with_v1_unchanged(self):
        assert _normalise_base_url("https://integrate.api.nvidia.com/v1") == "https://integrate.api.nvidia.com/v1"

    def test_url_with_trailing_slash_normalised(self):
        assert _normalise_base_url("https://integrate.api.nvidia.com/v1/") == "https://integrate.api.nvidia.com/v1"

    def test_localhost_gets_v1(self):
        assert _normalise_base_url("http://localhost:8080") == "http://localhost:8080/v1"


# ---------------------------------------------------------------------------
# 2. NemotronClient configuration
# ---------------------------------------------------------------------------

class TestNemotronClientConfig:
    def test_not_configured_when_missing_keys(self):
        with patch("app.services.nemotron.nemotron_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                nemotron_base_url="", nemotron_api_key="", nemotron_model="test"
            )
            c = NemotronClient()
            assert not c.is_configured()

    def test_configured_when_both_keys_present(self):
        with patch("app.services.nemotron.nemotron_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                nemotron_base_url="https://api.example.com/v1",
                nemotron_api_key="test-key",
                nemotron_model="nvidia/nemotron-mini-4b-instruct",
            )
            c = NemotronClient()
            assert c.is_configured()

    def test_raises_unavailable_when_not_configured(self):
        with patch("app.services.nemotron.nemotron_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                nemotron_base_url="", nemotron_api_key="", nemotron_model="test"
            )
            c = NemotronClient()
            with pytest.raises(NemotronUnavailableError):
                import asyncio
                asyncio.get_event_loop().run_until_complete(c._call([]))


# ---------------------------------------------------------------------------
# 3. Tool definitions
# ---------------------------------------------------------------------------

class TestToolDefinitions:
    def test_all_tools_defined(self):
        names = {t["function"]["name"] for t in CIVICHEAT_TOOLS}
        assert "get_current_heat_analysis" in names
        assert "get_priority_zones" in names
        assert "inspect_zone" in names
        assert "compare_zones" in names
        assert "calculate_intervention_priority" in names

    def test_tool_has_required_schema_fields(self):
        for tool in CIVICHEAT_TOOLS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"

    def test_tool_descriptions_are_not_empty(self):
        for tool in CIVICHEAT_TOOLS:
            assert len(tool["function"]["description"]) > 10


# ---------------------------------------------------------------------------
# 4. AgentTools — real tool execution against demo data
# ---------------------------------------------------------------------------

class TestAgentTools:
    def setup_method(self):
        self.ctx = _make_demo_context()
        self.tools = AgentTools(self.ctx)

    def test_get_current_heat_analysis(self):
        result = json.loads(self.tools.execute("get_current_heat_analysis", {}))
        assert "mean_temperature_c" in result
        assert "overall_risk_level" in result
        assert "total_features" in result
        assert "score_disclaimer" in result
        assert result["total_features"] > 0

    def test_get_priority_zones(self):
        result = json.loads(self.tools.execute("get_priority_zones", {"limit": 3}))
        assert "zones" in result
        assert "total_zones" in result

    def test_get_priority_zones_no_raw_geojson(self):
        """Zones must NOT include full tile geometry — keep context small."""
        result = json.loads(self.tools.execute("get_priority_zones", {}))
        for zone in result.get("zones", []):
            assert "bbox" not in zone  # bbox excluded from agent context
            assert "coordinates" not in str(zone)  # no raw geometry

    def test_inspect_zone_valid(self):
        zones_result = json.loads(self.tools.execute("get_priority_zones", {"limit": 1}))
        if zones_result["zones"]:
            zone_id = zones_result["zones"][0]["zone_id"]
            result = json.loads(self.tools.execute("inspect_zone", {"zone_id": zone_id}))
            assert result["zone_id"] == zone_id
            assert "risk_level" in result
            assert "recommended_actions" in result

    def test_inspect_zone_invalid_returns_error(self):
        result = json.loads(self.tools.execute("inspect_zone", {"zone_id": "ZONE-999"}))
        assert "error" in result
        assert "available_zones" in result

    def test_compare_zones(self):
        zones_result = json.loads(self.tools.execute("get_priority_zones", {"limit": 2}))
        zone_ids = [z["zone_id"] for z in zones_result.get("zones", [])]
        if len(zone_ids) >= 2:
            result = json.loads(self.tools.execute("compare_zones", {"zone_ids": zone_ids[:2]}))
            assert "comparison" in result
            assert len(result["comparison"]) == 2

    def test_calculate_intervention_priority(self):
        zones_result = json.loads(self.tools.execute("get_priority_zones", {"limit": 1}))
        if zones_result["zones"]:
            zone_id = zones_result["zones"][0]["zone_id"]
            result = json.loads(self.tools.execute("calculate_intervention_priority", {
                "zone_id": zone_id,
                "intervention_type": "cooling_center",
            }))
            assert "urgency" in result
            assert "actions" in result
            assert "disclaimer" in result

    def test_unknown_tool_returns_error(self):
        result = json.loads(self.tools.execute("unknown_tool", {}))
        assert "error" in result

    def test_tools_used_tracking(self):
        self.tools.execute("get_current_heat_analysis", {})
        self.tools.execute("get_priority_zones", {})
        assert "get_current_heat_analysis" in self.tools.tools_used()
        assert "get_priority_zones" in self.tools.tools_used()


# ---------------------------------------------------------------------------
# 5. Fallback decision
# ---------------------------------------------------------------------------

class TestFallbackDecision:
    def test_fallback_uses_real_data(self):
        ctx = _make_demo_context()
        decision = build_fallback_decision(ctx)
        assert decision.risk_level in ("LOW", "MODERATE", "HIGH", "EXTREME")
        assert 0 <= decision.risk_score <= 100
        assert len(decision.evidence) > 0
        assert len(decision.recommended_actions) > 0

    def test_fallback_labels_itself(self):
        ctx = _make_demo_context()
        decision = build_fallback_decision(ctx)
        limitations_text = " ".join(decision.limitations)
        assert "FALLBACK" in limitations_text

    def test_fallback_no_fabricated_data(self):
        ctx = _make_demo_context()
        decision = build_fallback_decision(ctx)
        # Evidence should reference actual temperature values
        evidence_text = " ".join(decision.evidence)
        assert "°C" in evidence_text or "temperature" in evidence_text.lower()


# ---------------------------------------------------------------------------
# 6. Agent loop (mocked Nemotron)
# ---------------------------------------------------------------------------

class TestAgentLoop:

    @pytest.mark.asyncio
    async def test_single_tool_call_then_stop(self):
        ctx = _make_demo_context()
        call_sequence = [
            _make_chat_response(tool_calls=[{"name": "get_current_heat_analysis", "args": {}}]),
            _make_chat_response(content=_valid_decision_json(), finish_reason="stop"),
        ]

        with patch("app.services.nemotron.nemotron_agent.NemotronClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.is_configured.return_value = True
            mock_instance.chat_with_tools = AsyncMock(side_effect=call_sequence)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.nemotron.nemotron_agent import run_agent
            decision, tools_used = await run_agent("What should we do?", ctx)

        assert decision.risk_level == "HIGH"
        assert decision.risk_score == 67
        assert "get_current_heat_analysis" in tools_used

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self):
        ctx = _make_demo_context()
        zones = json.loads(AgentTools(ctx).execute("get_priority_zones", {}))
        zone_id = zones["zones"][0]["zone_id"] if zones["zones"] else "ZONE-001"

        call_sequence = [
            _make_chat_response(tool_calls=[{"name": "get_current_heat_analysis", "args": {}}]),
            _make_chat_response(tool_calls=[{"name": "get_priority_zones", "args": {"limit": 3}}]),
            _make_chat_response(tool_calls=[{"name": "inspect_zone", "args": {"zone_id": zone_id}}]),
            _make_chat_response(content=_valid_decision_json(), finish_reason="stop"),
        ]

        with patch("app.services.nemotron.nemotron_agent.NemotronClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.chat_with_tools = AsyncMock(side_effect=call_sequence)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.nemotron.nemotron_agent import run_agent
            decision, tools_used = await run_agent("Analyze Phoenix heat", ctx)

        assert len(tools_used) == 3
        assert "get_current_heat_analysis" in tools_used
        assert "get_priority_zones" in tools_used
        assert "inspect_zone" in tools_used

    @pytest.mark.asyncio
    async def test_malformed_json_triggers_correction(self):
        ctx = _make_demo_context()
        call_sequence = [
            _make_chat_response(content="This is not JSON at all", finish_reason="stop"),
            _make_chat_response(content=_valid_decision_json(), finish_reason="stop"),
        ]

        with patch("app.services.nemotron.nemotron_agent.NemotronClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.chat_with_tools = AsyncMock(side_effect=[call_sequence[0]])
            mock_instance.chat = AsyncMock(return_value=call_sequence[1])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.nemotron.nemotron_agent import run_agent
            decision, _ = await run_agent("test", ctx)

        assert decision.risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_malformed_json_twice_raises(self):
        ctx = _make_demo_context()
        bad_response = _make_chat_response(content="not json", finish_reason="stop")

        with patch("app.services.nemotron.nemotron_agent.NemotronClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.chat_with_tools = AsyncMock(return_value=bad_response)
            mock_instance.chat = AsyncMock(return_value=bad_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.nemotron.nemotron_agent import run_agent
            with pytest.raises(NemotronMalformedResponseError):
                await run_agent("test", ctx)


# ---------------------------------------------------------------------------
# 7. API endpoints (mocked Nemotron, real Phase 3 pipeline)
# ---------------------------------------------------------------------------

class TestAgentAnalyzeEndpoint:

    def _patch_nemotron(self, tools_used=None, decision_override=None):
        """Returns a context manager that patches run_agent."""
        decision = AgentDecision.model_validate(json.loads(_valid_decision_json()))
        if decision_override:
            decision = decision_override

        async def fake_run_agent(message, ctx, **kwargs):
            return decision, tools_used or ["get_current_heat_analysis", "get_priority_zones"]

        return patch("app.api.routes.agent.run_agent", side_effect=fake_run_agent)

    def test_analyze_fallback_when_nemotron_not_configured(self):
        """When Nemotron is not configured, should return fallback response, not 500."""
        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = False
            response = client.post("/api/agent/analyze", json={
                "message": "What should we do?",
                "city": "Phoenix, AZ",
                "date": "2025-08-01",
                "demo_mode": True,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["fallback_mode"] is True
        assert "decision" in data
        assert data["decision"]["risk_level"] in ("LOW", "MODERATE", "HIGH", "EXTREME")

    def test_analyze_with_mocked_nemotron(self):
        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = True
            MockClient.return_value._model = "nvidia/nemotron-mini-4b-instruct"
            with self._patch_nemotron():
                response = client.post("/api/agent/analyze", json={
                    "city": "Phoenix, AZ",
                    "date": "2025-08-01",
                    "demo_mode": True,
                })
        assert response.status_code == 200
        data = response.json()
        assert data["fallback_mode"] is False
        assert data["decision"]["risk_score"] == 67
        assert len(data["tools_used"]) >= 1

    def test_analyze_timeout_returns_fallback(self):
        async def fake_run_agent(*args, **kwargs):
            raise NemotronTimeoutError("timed out")

        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = True
            with patch("app.api.routes.agent.run_agent", side_effect=fake_run_agent):
                response = client.post("/api/agent/analyze", json={
                    "demo_mode": True,
                })
        assert response.status_code == 200
        data = response.json()
        assert data["fallback_mode"] is True
        assert "timed out" in data["fallback_reason"].lower()

    def test_analyze_unavailable_returns_fallback(self):
        async def fake_run_agent(*args, **kwargs):
            raise NemotronUnavailableError("endpoint down")

        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = True
            with patch("app.api.routes.agent.run_agent", side_effect=fake_run_agent):
                response = client.post("/api/agent/analyze", json={"demo_mode": True})
        assert response.status_code == 200
        assert response.json()["fallback_mode"] is True

    def test_analyze_response_has_required_fields(self):
        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = False
            response = client.post("/api/agent/analyze", json={"demo_mode": True})
        data = response.json()
        assert "agent" in data
        assert "decision" in data
        assert "tools_used" in data
        assert "fallback_mode" in data
        decision = data["decision"]
        assert "decision" in decision
        assert "risk_level" in decision
        assert "risk_score" in decision
        assert "evidence" in decision
        assert "recommended_actions" in decision
        assert "limitations" in decision
        assert "reassessment" in decision

    def test_no_fabricated_claims_in_response(self):
        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = False
            response = client.post("/api/agent/analyze", json={"demo_mode": True})
        body = response.text
        for forbidden in ["100,000 lives", "95% accuracy", "guaranteed reduction", "saves lives"]:
            assert forbidden not in body


class TestActionPlanEndpoint:
    def test_action_plan_invalid_zone_returns_404(self):
        response = client.post("/api/agent/action-plan", json={
            "zone_id": "ZONE-999",
            "city": "Phoenix, AZ",
            "date": "2025-08-01",
            "demo_mode": True,
        })
        assert response.status_code == 404

    def test_action_plan_valid_zone_fallback(self):
        # Build real context to get a valid zone ID
        intel = build_demo_intelligence()
        risk = run_risk_analysis(intel)
        priority = run_priority_analysis(risk)
        if not priority.priority_zones:
            pytest.skip("No priority zones in demo data")

        zone_id = priority.priority_zones[0].zone_id

        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = False
            response = client.post("/api/agent/action-plan", json={
                "zone_id": zone_id,
                "demo_mode": True,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["zone"] == zone_id
        assert data["fallback_mode"] is True
        assert len(data["actions"]) > 0
        assert len(data["evidence"]) > 0


class TestPublicAdvisoryEndpoint:
    def test_advisory_fallback(self):
        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = False
            response = client.post("/api/agent/public-advisory", json={"demo_mode": True})
        assert response.status_code == 200
        data = response.json()
        assert data["fallback_mode"] is True
        assert "ADVISORY" in data["title"]
        assert "official review" in data["disclaimer"].lower()
        assert len(data["body"]) > 20

    def test_advisory_never_makes_medical_claims(self):
        with patch("app.api.routes.agent.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = False
            response = client.post("/api/agent/public-advisory", json={"demo_mode": True})
        body = response.text
        for forbidden in ["diagnosis", "treatment", "medical", "will die", "mortality"]:
            assert forbidden not in body.lower()


# ---------------------------------------------------------------------------
# 8. AgentDecision model validation
# ---------------------------------------------------------------------------

class TestAgentDecisionModel:
    def test_valid_decision_parses(self):
        d = AgentDecision.model_validate(json.loads(_valid_decision_json()))
        assert d.risk_level == "HIGH"
        assert d.risk_score == 67
        assert len(d.recommended_actions) == 1

    def test_risk_score_must_be_0_to_100(self):
        data = json.loads(_valid_decision_json())
        data["risk_score"] = 150
        with pytest.raises(Exception):
            AgentDecision.model_validate(data)

    def test_risk_score_negative_rejected(self):
        data = json.loads(_valid_decision_json())
        data["risk_score"] = -5
        with pytest.raises(Exception):
            AgentDecision.model_validate(data)

    def test_invalid_risk_level_rejected(self):
        data = json.loads(_valid_decision_json())
        data["risk_level"] = "CATASTROPHIC"
        with pytest.raises(Exception):
            AgentDecision.model_validate(data)
