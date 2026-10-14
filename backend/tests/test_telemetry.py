"""Tests for the OpenTelemetry telemetry module (backlog task 4)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.telemetry import RequestMetricsMiddleware, Telemetry


class _RecordingCounter:
    """Stand-in for an OpenTelemetry counter that records every ``add`` call."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, dict[str, object]]] = []

    def add(self, amount: int, attributes: dict[str, object] | None = None) -> None:
        self.calls.append((amount, attributes or {}))


class _RecordingSpan:
    """Stand-in for an OpenTelemetry span that records its attributes."""

    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


class _RecordingTracer:
    """Stand-in for an OpenTelemetry tracer that records started spans."""

    def __init__(self) -> None:
        self.spans: list[_RecordingSpan] = []

    def start_as_current_span(self, _name: str):
        span = _RecordingSpan()
        self.spans.append(span)

        class _SpanContext:
            def __enter__(self) -> _RecordingSpan:
                return span

            def __exit__(self, *_exc: object) -> None:
                return None

        return _SpanContext()


class _StubTelemetry:
    """Minimal telemetry object exposing only what the middleware uses."""

    def __init__(self) -> None:
        self.request_counter = _RecordingCounter()
        self.tracer = _RecordingTracer()


def test_telemetry_disabled_without_endpoint() -> None:
    telemetry = Telemetry(Settings(_env_file=None))
    try:
        assert telemetry.request_counter is not None
    finally:
        telemetry.shutdown()


def test_telemetry_enabled_with_endpoint() -> None:
    settings = Settings(_env_file=None, otel_exporter_otlp_endpoint="http://localhost:4317")
    telemetry = Telemetry(settings)
    try:
        assert telemetry.request_counter is not None
    finally:
        telemetry.shutdown()


def test_log_startup_emits_without_error() -> None:
    telemetry = Telemetry(Settings(_env_file=None))
    try:
        telemetry.log_startup()
    finally:
        telemetry.shutdown()


def test_middleware_counts_requests_by_route_and_status() -> None:
    stub = _StubTelemetry()
    app = FastAPI()
    app.add_middleware(RequestMetricsMiddleware, telemetry=stub)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/missing").status_code == 404

    assert stub.request_counter.calls == [
        (1, {"http.route": "/healthz", "http.response.status_code": 200}),
        (1, {"http.route": "<unmatched>", "http.response.status_code": 404}),
    ]
    assert [span.attributes for span in stub.tracer.spans] == [
        {"http.route": "/healthz", "http.response.status_code": 200},
        {"http.route": "<unmatched>", "http.response.status_code": 404},
    ]


def test_create_app_attaches_telemetry_and_shuts_down_cleanly() -> None:
    app = create_app(Settings(_env_file=None))
    assert isinstance(app.state.telemetry, Telemetry)

    # Entering and leaving the TestClient context runs the lifespan, which
    # shuts the providers down without raising.
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
