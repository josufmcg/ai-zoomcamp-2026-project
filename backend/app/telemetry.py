"""OpenTelemetry setup for the EFINGES backend (backlog task 4).

The :class:`Telemetry` object owns the trace, metric, and log providers and the
instruments the application uses. Exporters are configured from the
``OTEL_EXPORTER_OTLP_ENDPOINT`` and ``OTEL_SERVICE_NAME`` settings:

* when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, spans, metrics, and logs are
  exported over OTLP/gRPC to the collector;
* when it is unset, telemetry is disabled: the providers are still created so
  application code can record data without branching, but nothing is exported.

Providers are created per application instance (rather than registered as the
process-wide OpenTelemetry providers) so that the application factory stays
testable and each app shuts its own providers down cleanly.
"""

from __future__ import annotations

from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings


class Telemetry:
    """Owns the OpenTelemetry providers and instruments for one application."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        resource = Resource.create({"service.name": settings.otel_service_name})

        metric_readers = []
        span_processors = []
        log_processors = []
        endpoint = settings.otel_exporter_otlp_endpoint
        if endpoint:
            metric_readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=endpoint),
                    export_interval_millis=5_000,
                )
            )
            span_processors.append(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            log_processors.append(BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint)))

        self.meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        self.tracer_provider = TracerProvider(resource=resource)
        self.logger_provider = LoggerProvider(resource=resource)
        for span_processor in span_processors:
            self.tracer_provider.add_span_processor(span_processor)
        for log_processor in log_processors:
            self.logger_provider.add_log_record_processor(log_processor)

        meter = self.meter_provider.get_meter(settings.otel_service_name)
        self.tracer = self.tracer_provider.get_tracer(settings.otel_service_name)
        self.logger = self.logger_provider.get_logger(settings.otel_service_name)
        self.request_counter = meter.create_counter(
            "http.server.request.count",
            unit="{request}",
            description="Number of HTTP requests handled by the backend",
        )

    def log_startup(self) -> None:
        """Emit a startup log record so the logs pipeline is exercised."""
        self.logger.emit(
            severity_number=SeverityNumber.INFO,
            severity_text="INFO",
            body="EFINGES backend started",
            attributes={
                "service.name": self._settings.otel_service_name,
                "telemetry.enabled": bool(self._settings.otel_exporter_otlp_endpoint),
            },
        )

    def shutdown(self) -> None:
        """Flush and stop the providers. Safe to call more than once."""
        self.meter_provider.shutdown()
        self.tracer_provider.shutdown()
        self.logger_provider.shutdown()


class RequestMetricsMiddleware:
    """Trace every HTTP request and count it by route and status code."""

    def __init__(self, app: ASGIApp, telemetry: Telemetry) -> None:
        self.app = app
        self.telemetry = telemetry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 500

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        with self.telemetry.tracer.start_as_current_span("http.server.request") as span:
            try:
                await self.app(scope, receive, send_with_status)
            finally:
                route = scope.get("route")
                route_path = getattr(route, "path", "<unmatched>")
                span.set_attribute("http.route", route_path)
                span.set_attribute("http.response.status_code", status_code)
                self.telemetry.request_counter.add(
                    1,
                    {
                        "http.route": route_path,
                        "http.response.status_code": status_code,
                    },
                )
