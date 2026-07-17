"""Alert simulator/replayer — streams sample Wazuh/Sysmon/Suricata alerts
against the Sentris ingest webhook to drive live demos.

Usage (from inside the api container, see `make demo`):

    python -m simulator.replay --dataset simulator/datasets/brute_force_scenario.json
    python -m simulator.replay --all --loop

Each dataset is a short, human-authored incident narrative: a handful of
alerts with relative delays that tell one story (brute force -> lateral
movement, phishing -> credential theft, etc). The simulator logs in with
the demo account, then POSTs each alert to `/alerts` at the delay offsets
so they land in the live dashboard the way a real detection pipeline
would, ingested one at a time rather than all at once.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DATASETS_DIR = Path(__file__).parent / "datasets"
DEMO_EMAIL = "demo@sentris.io"
DEMO_PASSWORD = "demo12345"


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return str(resp.json()["access_token"])


async def replay_dataset(
    client: httpx.AsyncClient, token: str, dataset_path: Path, speed: float
) -> None:
    dataset: dict[str, Any] = json.loads(dataset_path.read_text(encoding="utf-8"))
    alerts: list[dict[str, Any]] = dataset["alerts"]
    print(f"\n=== {dataset.get('name', dataset_path.stem)} ({len(alerts)} alerts) ===")

    start = time.monotonic()
    for alert in alerts:
        target_elapsed = alert["delay"] / speed
        remaining = target_elapsed - (time.monotonic() - start)
        if remaining > 0:
            await asyncio.sleep(remaining)

        payload = {k: v for k, v in alert.items() if k != "delay"}
        payload["occurred_at"] = datetime.now(UTC).isoformat()

        resp = await client.post(
            "/alerts", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code != 201:
            print(f"  ! failed to ingest '{payload['title']}': {resp.status_code} {resp.text}")
            continue
        alert_id = resp.json()["id"]
        print(f"  -> [{payload['severity']}] {payload['title']} (alert {alert_id})")


async def run(args: argparse.Namespace) -> None:
    dataset_paths = (
        sorted(DATASETS_DIR.glob("*.json")) if args.all else [Path(args.dataset)]
    )
    missing = [p for p in dataset_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"Dataset {p} not found.", file=sys.stderr)
        sys.exit(1)

    async with httpx.AsyncClient(base_url=args.api_url, timeout=15.0) as client:
        token = await login(client, args.email, args.password)
        print(f"Authenticated as {args.email}")

        while True:
            for path in dataset_paths:
                await replay_dataset(client, token, path, args.speed)
            if not args.loop:
                break
            print("\n--- looping ---")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay sample alerts into Sentris.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset", help="Path to a single dataset JSON file")
    group.add_argument(
        "--all", action="store_true", help="Replay every dataset in simulator/datasets/"
    )
    parser.add_argument(
        "--api-url", default="http://api:8000/api/v1", help="Base API URL"
    )
    parser.add_argument("--email", default=DEMO_EMAIL, help="Login email")
    parser.add_argument("--password", default=DEMO_PASSWORD, help="Login password")
    parser.add_argument(
        "--speed", type=float, default=1.0, help="Playback speed multiplier (2.0 = twice as fast)"
    )
    parser.add_argument(
        "--loop", action="store_true", help="Replay continuously for a live demo feed"
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(args))
    except httpx.HTTPStatusError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
