#!/usr/bin/env python3
"""Continuously probe OSWorld servers on ECS instances belonging to one run."""

from __future__ import annotations

import argparse
import json
import os
import socket
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from engiworld.scheduler.volcengine_ecs import (
    EcsInstance,
    VolcengineEcsClient,
    VolcengineLaunchConfig,
)


SUCCESS_STATES = {"healthy", "legacy_healthy"}
DIRECT_HTTP_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@dataclass(frozen=True)
class ProbeResult:
    state: str
    detail: str = ""
    version: str = ""
    content_sha256: str = ""
    latency_ms: int = 0


@dataclass
class ProbeHistory:
    instance: EcsInstance
    results: list[tuple[float, ProbeResult]] = field(default_factory=list)

    def add(self, elapsed_seconds: float, result: ProbeResult) -> bool:
        changed = not self.results or self.results[-1][1].state != result.state
        self.results.append((elapsed_seconds, result))
        return changed

    def classification(self) -> str:
        states = [result.state for _, result in self.results]
        successes = [index for index, state in enumerate(states) if state in SUCCESS_STATES]
        if not successes:
            return "unhealthy"
        first_success = successes[0]
        if any(state not in SUCCESS_STATES for state in states[first_success + 1 :]):
            return "flapping"
        if first_success > 0:
            return "slow_start"
        if all(state == "legacy_healthy" for state in states):
            return "legacy"
        return "healthy"

    def as_dict(self) -> dict[str, Any]:
        states = [result.state for _, result in self.results]
        first_success = next(
            (elapsed for elapsed, result in self.results if result.state in SUCCESS_STATES),
            None,
        )
        last = self.results[-1][1]
        return {
            "classification": self.classification(),
            "instance_id": self.instance.instance_id,
            "private_ip": self.instance.private_ip,
            "snapshot": self.instance.tags.get("snapshot", ""),
            "image_id": self.instance.image_id,
            "os_type": self.instance.os_type,
            "ecs_status": self.instance.status,
            "probe_count": len(self.results),
            "state_counts": dict(sorted(Counter(states).items())),
            "first_healthy_seconds": round(first_success, 1) if first_success is not None else None,
            "last_state": last.state,
            "last_detail": last.detail,
            "version": last.version,
            "content_sha256": last.content_sha256,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Evaluation run_id ECS tag value.")
    parser.add_argument(
        "--project-name",
        default=os.getenv("VOLCENGINE_PROJECT_NAME", "agent-eval"),
        help="ECS project name (default: VOLCENGINE_PROJECT_NAME or agent-eval).",
    )
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--watch-seconds",
        type=float,
        default=60.0,
        help="Observe for this long; use 0 for a one-shot check (default: 60).",
    )
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=3.0)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument(
        "--expected-content-sha256",
        default="",
        help="Also flag healthy servers whose installed bundle hash differs.",
    )
    parser.add_argument(
        "--fail-on-unhealthy",
        action="store_true",
        help="Exit with status 2 if any VM is unhealthy or flapping.",
    )
    args = parser.parse_args()
    if args.watch_seconds < 0:
        parser.error("--watch-seconds must be >= 0")
    if args.interval_seconds <= 0:
        parser.error("--interval-seconds must be > 0")
    if args.request_timeout_seconds <= 0:
        parser.error("--request-timeout-seconds must be > 0")
    if args.workers <= 0:
        parser.error("--workers must be > 0")
    return args


def ecs_query_config(project_name: str) -> VolcengineLaunchConfig:
    required = {
        "VOLCENGINE_ACCESS_KEY_ID": os.getenv("VOLCENGINE_ACCESS_KEY_ID"),
        "VOLCENGINE_SECRET_ACCESS_KEY": os.getenv("VOLCENGINE_SECRET_ACCESS_KEY"),
        "VOLCENGINE_REGION": os.getenv("VOLCENGINE_REGION"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise EnvironmentError("Missing Volcengine configuration: " + ", ".join(missing))
    return VolcengineLaunchConfig(
        region=required["VOLCENGINE_REGION"] or "",
        access_key_id=required["VOLCENGINE_ACCESS_KEY_ID"] or "",
        secret_access_key=required["VOLCENGINE_SECRET_ACCESS_KEY"] or "",
        subnet_id="",
        security_group_id="",
        instance_type="",
        zone_id="",
        project_name=project_name,
    )


def probe_instance(
    instance: EcsInstance,
    *,
    port: int,
    timeout_seconds: float,
    expected_content_sha256: str = "",
) -> ProbeResult:
    if instance.status.upper() != "RUNNING":
        return ProbeResult("ecs_not_running", f"ECS status is {instance.status or 'unknown'}")
    if not instance.private_ip:
        return ProbeResult("no_private_ip", "DescribeInstances returned no private IP")

    started = time.monotonic()
    health_url = f"http://{instance.private_ip}:{port}/health"
    try:
        status, body = _request_json(health_url, timeout_seconds=timeout_seconds)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return _probe_legacy_execute(instance, port, timeout_seconds, started)
        return ProbeResult(
            "http_error",
            f"GET /health returned HTTP {exc.code}",
            latency_ms=_elapsed_ms(started),
        )
    except Exception as exc:
        return ProbeResult(
            _network_error_state(exc),
            f"{type(exc).__name__}: {exc}",
            latency_ms=_elapsed_ms(started),
        )

    if status != 200:
        return ProbeResult(
            "http_error",
            f"GET /health returned HTTP {status}",
            latency_ms=_elapsed_ms(started),
        )
    if not isinstance(body, dict) or str(body.get("status", "")).lower() != "ok":
        return ProbeResult(
            "invalid_health",
            f"Unexpected /health response: {_compact(body)}",
            latency_ms=_elapsed_ms(started),
        )

    content_sha256 = str(body.get("content_sha256") or "")
    version = str(body.get("version") or "")
    if expected_content_sha256 and content_sha256.lower() != expected_content_sha256.lower():
        return ProbeResult(
            "content_mismatch",
            f"expected {expected_content_sha256}, got {content_sha256 or 'missing'}",
            version=version,
            content_sha256=content_sha256,
            latency_ms=_elapsed_ms(started),
        )
    return ProbeResult(
        "healthy",
        version=version,
        content_sha256=content_sha256,
        latency_ms=_elapsed_ms(started),
    )


def _probe_legacy_execute(
    instance: EcsInstance,
    port: int,
    timeout_seconds: float,
    started: float,
) -> ProbeResult:
    if "windows" in instance.os_type.lower():
        command = ["cmd.exe", "/d", "/s", "/c", "echo arena-osworld-probe"]
    else:
        command = ["/bin/sh", "-c", "printf arena-osworld-probe"]
    url = f"http://{instance.private_ip}:{port}/execute"
    payload = json.dumps({"command": command, "shell": False, "timeout": 10}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with DIRECT_HTTP_OPENER.open(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read(64 * 1024).decode("utf-8"))
            if (
                response.status == 200
                and body.get("status") == "success"
                and body.get("returncode") == 0
            ):
                return ProbeResult(
                    "legacy_healthy",
                    "Server responds to /execute but has no /health route",
                    latency_ms=_elapsed_ms(started),
                )
            return ProbeResult(
                "execute_error",
                f"Unexpected /execute response: {_compact(body)}",
                latency_ms=_elapsed_ms(started),
            )
    except Exception as exc:
        return ProbeResult(
            _network_error_state(exc),
            f"POST /execute after /health=404 failed: {type(exc).__name__}: {exc}",
            latency_ms=_elapsed_ms(started),
        )


def _request_json(url: str, *, timeout_seconds: float) -> tuple[int, Any]:
    request = urllib.request.Request(url, method="GET")
    with DIRECT_HTTP_OPENER.open(request, timeout=timeout_seconds) as response:
        raw = response.read(64 * 1024)
        return response.status, json.loads(raw.decode("utf-8"))


def _network_error_state(exc: Exception) -> str:
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    text = f"{type(reason).__name__}: {reason}".lower()
    if isinstance(reason, ConnectionRefusedError) or "connection refused" in text:
        return "connection_refused"
    if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in text:
        return "timeout"
    if "no route to host" in text or "network is unreachable" in text:
        return "network_unreachable"
    if "connection reset" in text:
        return "connection_reset"
    return "network_error"


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _compact(value: Any, limit: int = 300) -> str:
    text = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _emit(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


def run(args: argparse.Namespace) -> int:
    client = VolcengineEcsClient(ecs_query_config(args.project_name))
    instances = client.list_instances(
        project_name=args.project_name,
        tags={"managed_by": "arena-osworld", "run_id": args.run_id},
    )
    if not instances:
        raise RuntimeError(
            f"No ECS instances found for run_id={args.run_id!r}, project={args.project_name!r}"
        )

    instances.sort(key=lambda item: (item.tags.get("snapshot", ""), item.instance_id))
    started = time.monotonic()
    histories = {instance.instance_id: ProbeHistory(instance=instance) for instance in instances}
    _emit(
        "vm_osworld_probe_started",
        run_id=args.run_id,
        project_name=args.project_name,
        instance_count=len(instances),
        watch_seconds=args.watch_seconds,
        interval_seconds=args.interval_seconds,
    )

    while True:
        elapsed = time.monotonic() - started
        with ThreadPoolExecutor(max_workers=min(args.workers, len(instances))) as executor:
            results = list(
                executor.map(
                    lambda instance: probe_instance(
                        instance,
                        port=args.port,
                        timeout_seconds=args.request_timeout_seconds,
                        expected_content_sha256=args.expected_content_sha256,
                    ),
                    instances,
                )
            )
        for instance, result in zip(instances, results):
            if histories[instance.instance_id].add(elapsed, result):
                _emit(
                    "vm_osworld_probe_state_changed",
                    elapsed_seconds=round(elapsed, 1),
                    instance_id=instance.instance_id,
                    private_ip=instance.private_ip,
                    snapshot=instance.tags.get("snapshot", ""),
                    image_id=instance.image_id,
                    state=result.state,
                    detail=result.detail,
                    latency_ms=result.latency_ms,
                )

        remaining = args.watch_seconds - (time.monotonic() - started)
        if remaining <= 0:
            break
        time.sleep(min(args.interval_seconds, remaining))

    reports = [history.as_dict() for history in histories.values()]
    rank = {"unhealthy": 0, "flapping": 1, "slow_start": 2, "legacy": 3, "healthy": 4}
    reports.sort(
        key=lambda item: (rank[item["classification"]], item["snapshot"], item["instance_id"])
    )
    for report in reports:
        _emit("vm_osworld_probe_result", **report)
    counts = Counter(report["classification"] for report in reports)
    _emit(
        "vm_osworld_probe_summary",
        run_id=args.run_id,
        instance_count=len(reports),
        classification_counts=dict(sorted(counts.items())),
        problematic_instance_ids=[
            report["instance_id"]
            for report in reports
            if report["classification"] in {"unhealthy", "flapping", "slow_start"}
        ],
    )
    if args.fail_on_unhealthy and any(
        report["classification"] in {"unhealthy", "flapping"} for report in reports
    ):
        return 2
    return 0


def main() -> None:
    try:
        raise SystemExit(run(parse_args()))
    except KeyboardInterrupt:
        _emit("vm_osworld_probe_interrupted")
        raise SystemExit(130)
    except Exception as exc:
        _emit("vm_osworld_probe_aborted", error=f"{type(exc).__name__}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
