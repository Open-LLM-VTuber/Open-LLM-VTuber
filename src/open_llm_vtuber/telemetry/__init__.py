"""OpenTelemetry integration for structured logging and metrics."""

import os
from typing import Optional
from contextvars import ContextVar
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.semconv.resource import ResourceAttributes
from loguru import logger


# Context variables for trace correlation
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)


class OpenTelemetrySetup:
    """OpenTelemetry configuration for tracing and metrics."""

    def __init__(
        self,
        service_name: str = "open-llm-vtuber",
        otlp_endpoint: Optional[str] = None,
        enable_console: bool = True,
    ):
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        self.enable_console = enable_console
        self._initialized = False

    def initialize(self) -> None:
        """Initialize OpenTelemetry tracing and metrics."""
        if self._initialized:
            return

        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            ResourceAttributes.SERVICE_VERSION: "1.2.1",
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development"),
        })

        # Tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        if self.enable_console:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )
        
        if self.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(tracer_provider)

        # Meter provider
        metric_readers = []
        if self.enable_console:
            metric_readers.append(
                PeriodicExportingMetricReader(ConsoleMetricExporter())
            )
        if self.otlp_endpoint:
            metric_readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=self.otlp_endpoint)
                )
            )

        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)

        # Set up propagators
        set_global_textmap(TraceContextTextMapPropagator())

        # Auto-instrument libraries
        try:
            FastAPIInstrumentor().instrument()
        except Exception:
            pass
        try:
            HTTPXClientInstrumentor().instrument()
        except Exception:
            pass
        try:
            RedisInstrumentor().instrument()
        except Exception:
            pass
        try:
            AioHttpClientInstrumentor().instrument()
        except Exception:
            pass

        self._initialized = True
        logger.info(f"OpenTelemetry initialized for {self.service_name}")

    def get_tracer(self, name: str) -> trace.Tracer:
        """Get a tracer for the given name."""
        return trace.get_tracer(name)

    def get_meter(self, name: str) -> metrics.Meter:
        """Get a meter for the given name."""
        return metrics.get_meter(name)

    def shutdown(self) -> None:
        """Shutdown OpenTelemetry providers."""
        trace.get_tracer_provider().shutdown()
        metrics.get_meter_provider().shutdown()
        self._initialized = False


# Global instance
_otel_setup: Optional[OpenTelemetrySetup] = None


def init_opentelemetry(
    service_name: str = "open-llm-vtuber",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = True,
) -> OpenTelemetrySetup:
    """Initialize global OpenTelemetry setup."""
    global _otel_setup
    if _otel_setup is None:
        _otel_setup = OpenTelemetrySetup(service_name, otlp_endpoint, enable_console)
        _otel_setup.initialize()
    return _otel_setup


def get_tracer(name: str) -> trace.Tracer:
    """Get tracer from global setup."""
    if _otel_setup is None:
        init_opentelemetry()
    return _otel_setup.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get meter from global setup."""
    if _otel_setup is None:
        init_opentelemetry()
    return _otel_setup.get_meter(name)


# Custom Loguru handler for OpenTelemetry correlation
class OTelLoguruHandler:
    """Loguru handler that adds trace context to logs."""

    def __init__(self):
        self._handler_id = None

    def __call__(self, message):
        record = message.record
        trace_id = trace_id_var.get()
        span_id = span_id_var.get()
        
        if trace_id and span_id:
            record["extra"]["trace_id"] = trace_id
            record["extra"]["span_id"] = span_id

    def install(self) -> int:
        """Install the handler."""
        self._handler_id = logger.add(self, format="{time} {level} {message} {extra}")
        return self._handler_id

    def uninstall(self) -> None:
        """Uninstall the handler."""
        if self._handler_id is not None:
            logger.remove(self._handler_id)
            self._handler_id = None


# Metrics definitions
class VTuberMetrics:
    """Pre-defined metrics for the VTuber application."""

    def __init__(self, meter_name: str = "vtuber.metrics"):
        self.meter = get_meter(meter_name)
        
        # Counters
        self.ws_connections = self.meter.create_counter(
            "vtuber.ws.connections.total",
            description="Total WebSocket connections",
        )
        self.ws_messages = self.meter.create_counter(
            "vtuber.ws.messages.total",
            description="Total WebSocket messages processed",
        )
        self.tts_requests = self.meter.create_counter(
            "vtuber.tts.requests.total",
            description="Total TTS generation requests",
        )
        self.asr_requests = self.meter.create_counter(
            "vtuber.asr.requests.total",
            description="Total ASR transcription requests",
        )
        self.agent_requests = self.meter.create_counter(
            "vtuber.agent.requests.total",
            description="Total agent/LLM requests",
        )
        self.cache_hits = self.meter.create_counter(
            "vtuber.cache.hits.total",
            description="Total cache hits",
        )
        self.cache_misses = self.meter.create_counter(
            "vtuber.cache.misses.total",
            description="Total cache misses",
        )
        self.errors = self.meter.create_counter(
            "vtuber.errors.total",
            description="Total errors",
        )

        # Histograms
        self.ws_latency = self.meter.create_histogram(
            "vtuber.ws.latency",
            description="WebSocket message processing latency",
            unit="ms",
        )
        self.tts_latency = self.meter.create_histogram(
            "vtuber.tts.latency",
            description="TTS generation latency",
            unit="ms",
        )
        self.asr_latency = self.meter.create_histogram(
            "vtuber.asr.latency",
            description="ASR transcription latency",
            unit="ms",
        )
        self.agent_latency = self.meter.create_histogram(
            "vtuber.agent.latency",
            description="Agent/LLM request latency",
            unit="ms",
        )

        # Gauges
        self.active_connections = self.meter.create_up_down_counter(
            "vtuber.ws.active_connections",
            description="Currently active WebSocket connections",
        )
        self.active_sessions = self.meter.create_up_down_counter(
            "vtuber.sessions.active",
            description="Currently active sessions",
        )


# Global metrics instance
_vtuber_metrics: Optional[VTuberMetrics] = None


def get_metrics() -> VTuberMetrics:
    """Get global metrics instance."""
    global _vtuber_metrics
    if _vtuber_metrics is None:
        _vtuber_metrics = VTuberMetrics()
    return _vtuber_metrics