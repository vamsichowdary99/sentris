from datetime import UTC, datetime

from httpx import AsyncClient


async def _create_alert(client: AsyncClient, title: str) -> str:
    resp = await client.post(
        "/api/v1/alerts",
        json={
            "source": "wazuh",
            "title": title,
            "raw": {},
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_case_links_alerts_and_writes_timeline(
    client: AsyncClient, org_and_user
) -> None:
    alert_id = await _create_alert(client, "Alert to promote into a case")

    create_resp = await client.post(
        "/api/v1/cases",
        json={
            "title": "Suspected compromise",
            "summary": "Investigating.",
            "severity": "high",
            "alert_ids": [alert_id],
        },
    )
    assert create_resp.status_code == 201
    case = create_resp.json()
    assert case["status"] == "open"

    detail_resp = await client.get(f"/api/v1/cases/{case['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert [a["id"] for a in detail["alerts"]] == [alert_id]
    timeline_kinds = [event["kind"] for event in detail["timeline"]]
    assert "case_opened" in timeline_kinds
    assert "alert_linked" in timeline_kinds


async def test_link_additional_alert_and_add_comment(
    client: AsyncClient, org_and_user
) -> None:
    create_resp = await client.post(
        "/api/v1/cases", json={"title": "Case without alerts", "severity": "medium"}
    )
    case_id = create_resp.json()["id"]

    alert_id = await _create_alert(client, "Second alert linked later")
    link_resp = await client.post(
        f"/api/v1/cases/{case_id}/alerts", json={"alert_ids": [alert_id]}
    )
    assert link_resp.status_code == 200

    alerts_resp = await client.get(f"/api/v1/cases/{case_id}/alerts")
    assert alerts_resp.status_code == 200
    assert [a["id"] for a in alerts_resp.json()] == [alert_id]

    comment_resp = await client.post(
        f"/api/v1/cases/{case_id}/comments", json={"body": "Escalating to on-call."}
    )
    assert comment_resp.status_code == 201

    comments_resp = await client.get(f"/api/v1/cases/{case_id}/comments")
    assert comments_resp.status_code == 200
    assert comments_resp.json()[0]["body"] == "Escalating to on-call."


async def test_closing_case_sets_closed_at_and_timeline_event(
    client: AsyncClient, org_and_user
) -> None:
    create_resp = await client.post(
        "/api/v1/cases", json={"title": "Case to close", "severity": "low"}
    )
    case_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/v1/cases/{case_id}", json={"status": "closed"})
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["status"] == "closed"
    assert body["closed_at"] is not None

    detail_resp = await client.get(f"/api/v1/cases/{case_id}")
    timeline_kinds = [event["kind"] for event in detail_resp.json()["timeline"]]
    assert "status_changed" in timeline_kinds
