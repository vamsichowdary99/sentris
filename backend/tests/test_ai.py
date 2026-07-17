import json
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.ai.router import AIRouter, LLMResponse, LLMUnavailableError
from app.db.session import async_session_factory
from app.models.mitre import MitreTechnique


def _fake_response(content: dict) -> LLMResponse:
    return LLMResponse(
        content=json.dumps(content),
        provider="test-provider",
        model="test-model",
        tokens_in=10,
        tokens_out=20,
        latency_ms=5,
    )


@pytest.fixture
def queued_responses(monkeypatch):
    """Patches AIRouter.complete to pop canned responses instead of calling
    a real LLM provider — lets AI service/route logic be tested without any
    provider configured."""
    responses: list[LLMResponse] = []

    async def fake_complete(self, *, user, system=None, json_mode=False, max_tokens=900):
        if not responses:
            raise LLMUnavailableError("no fake response queued for this test")
        return responses.pop(0)

    monkeypatch.setattr(AIRouter, "complete", fake_complete)
    return responses


async def _ensure_technique(technique_id: str, name: str, tactic: str) -> None:
    async with async_session_factory() as session:
        stmt = (
            pg_insert(MitreTechnique)
            .values(
                id=technique_id,
                name=name,
                tactic=tactic,
                description="test fixture technique",
                url=f"https://attack.mitre.org/techniques/{technique_id}/",
            )
            .on_conflict_do_nothing()
        )
        await session.execute(stmt)
        await session.commit()


async def _create_alert(client: AsyncClient, **overrides) -> str:
    payload = {
        "source": "wazuh",
        "title": "Suspicious login from unfamiliar location",
        "raw": {},
        "severity": "medium",
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/alerts", json=payload)
    assert resp.status_code == 201
    return str(resp.json()["id"])


async def test_summarize_alert_stores_ai_analysis(
    client: AsyncClient, org_and_user, queued_responses
) -> None:
    alert_id = await _create_alert(client)
    queued_responses.append(_fake_response({"summary": "A user logged in from a new location."}))

    resp = await client.post(f"/api/v1/ai/alerts/{alert_id}/summarize")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task"] == "summary"
    assert body["output"]["summary"] == "A user logged in from a new location."

    detail = await client.get(f"/api/v1/alerts/{alert_id}")
    tasks = {a["task"] for a in detail.json()["ai_analyses"]}
    assert "summary" in tasks


async def test_triage_alert_updates_severity_and_priority(
    client: AsyncClient, org_and_user, queued_responses
) -> None:
    alert_id = await _create_alert(client, severity="low")
    queued_responses.append(
        _fake_response(
            {
                "severity": "critical",
                "priority": 95,
                "confidence": 0.9,
                "reasoning": "Matches a known attack pattern.",
            }
        )
    )

    resp = await client.post(f"/api/v1/ai/alerts/{alert_id}/triage")
    assert resp.status_code == 200

    detail = await client.get(f"/api/v1/alerts/{alert_id}")
    body = detail.json()
    assert body["ai_severity"] == "critical"
    assert body["priority"] == 95


async def test_ai_unavailable_returns_503(
    client: AsyncClient, org_and_user, queued_responses
) -> None:
    alert_id = await _create_alert(client)
    # No responses queued — AIRouter.complete raises LLMUnavailableError.
    resp = await client.post(f"/api/v1/ai/alerts/{alert_id}/summarize")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "ai_unavailable"


async def test_invalid_json_triggers_repair_retry(
    client: AsyncClient, org_and_user, queued_responses
) -> None:
    alert_id = await _create_alert(client)
    queued_responses.append(_fake_response({"not_the_right_field": "oops"}))
    queued_responses.append(_fake_response({"summary": "Recovered after a repair prompt."}))

    resp = await client.post(f"/api/v1/ai/alerts/{alert_id}/summarize")
    assert resp.status_code == 200
    assert resp.json()["output"]["summary"] == "Recovered after a repair prompt."
    assert queued_responses == []


async def test_map_alert_mitre_ignores_hallucinated_technique(
    client: AsyncClient, org_and_user, queued_responses
) -> None:
    await _ensure_technique("T1110", "Brute Force", "credential-access")
    alert_id = await _create_alert(client)
    queued_responses.append(
        _fake_response(
            {
                "techniques": [
                    {"id": "T1110", "confidence": 0.8, "reasoning": "Repeated auth failures."},
                    {"id": "T9999", "confidence": 0.99, "reasoning": "Hallucinated technique."},
                ]
            }
        )
    )

    resp = await client.post(f"/api/v1/ai/alerts/{alert_id}/mitre")
    assert resp.status_code == 200
    assert resp.json()["output"]["applied"] == ["T1110"]

    detail = await client.get(f"/api/v1/alerts/{alert_id}")
    mitre_ids = {m["technique"]["id"] for m in detail.json()["mitre"]}
    assert mitre_ids == {"T1110"}


async def test_nl_search_compiles_safe_filter(
    client: AsyncClient, org_and_user, queued_responses
) -> None:
    await _create_alert(client, title="Critical ransomware detonation", severity="critical")
    await _create_alert(client, title="Benign scheduled task", severity="low")
    queued_responses.append(
        _fake_response(
            {
                "status": None,
                "severity": "critical",
                "source": None,
                "src_ip": None,
                "q": None,
                "mitre": None,
                "occurred_from": None,
                "occurred_to": None,
            }
        )
    )

    resp = await client.post("/api/v1/ai/search", json={"query": "critical alerts"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["filter"]["severity"] == "critical"
    assert body["total"] == 1
    assert body["items"][0]["severity"] == "critical"
