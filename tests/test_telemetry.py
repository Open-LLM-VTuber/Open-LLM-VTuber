"""Tests for telemetry module."""

from unittest.mock import MagicMock, patch

from src.open_llm_vtuber.telemetry import (
    OpenTelemetrySetup,
    init_opentelemetry,
    get_tracer,
    get_meter,
    get_metrics,
    VTuberMetrics,
    OTelLoguruHandler,
)


class TestOpenTelemetrySetup:
    """Tests for OpenTelemetrySetup class."""

    def test_initialization(self):
        """Test initialization with default values."""
        setup = OpenTelemetrySetup()
        assert setup.service_name == "open-llm-vtuber"
        assert setup._initialized is False

    def test_initialization_custom(self):
        """Test initialization with custom values."""
        setup = OpenTelemetrySetup(
            service_name="test-service",
            otlp_endpoint="http://localhost:4317",
            enable_console=False,
        )
        assert setup.service_name == "test-service"
        assert setup.otlp_endpoint == "http://localhost:4317"
        assert setup.enable_console is False


class TestGlobalFunctions:
    """Tests for global telemetry functions."""

    @patch("src.open_llm_vtuber.telemetry.trace")
    @patch("src.open_llm_vtuber.telemetry.metrics")
    def test_init_opentelemetry(self, mock_metrics, mock_trace):
        """Test init_opentelemetry creates setup."""
        setup = init_opentelemetry()
        assert setup is not None
        assert setup._initialized is True

    @patch("src.open_llm_vtuber.telemetry._otel_setup", None)
    @patch("src.open_llm_vtuber.telemetry.trace")
    @patch("src.open_llm_vtuber.telemetry.metrics")
    def test_get_tracer(self, mock_metrics, mock_trace):
        """Test get_tracer returns tracer."""
        mock_tracer = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer
        
        tracer = get_tracer("test")
        assert tracer == mock_tracer
        mock_trace.get_tracer.assert_called_once_with("test")

    @patch("src.open_llm_vtuber.telemetry._otel_setup", None)
    @patch("src.open_llm_vtuber.telemetry.trace")
    @patch("src.open_llm_vtuber.telemetry.metrics")
    def test_get_meter(self, mock_metrics, mock_trace):
        """Test get_meter returns meter."""
        mock_meter = MagicMock()
        mock_metrics.get_meter.return_value = mock_meter
        
        meter = get_meter("test")
        assert meter == mock_meter
        mock_metrics.get_meter.assert_called_once_with("test")


class TestVTuberMetrics:
    """Tests for VTuberMetrics class."""

    @patch("src.open_llm_vtuber.telemetry.get_meter")
    def test_metrics_creation(self, mock_get_meter):
        """Test metrics creation."""
        mock_meter = MagicMock()
        mock_get_meter.return_value = mock_meter
        
        metrics = VTuberMetrics()
        
        # Check that all metrics were created
        assert hasattr(metrics, "ws_connections")
        assert hasattr(metrics, "ws_messages")
        assert hasattr(metrics, "tts_requests")
        assert hasattr(metrics, "asr_requests")
        assert hasattr(metrics, "agent_requests")
        assert hasattr(metrics, "cache_hits")
        assert hasattr(metrics, "cache_misses")
        assert hasattr(metrics, "errors")
        assert hasattr(metrics, "ws_latency")
        assert hasattr(metrics, "tts_latency")
        assert hasattr(metrics, "asr_latency")
        assert hasattr(metrics, "agent_latency")
        assert hasattr(metrics, "active_connections")
        assert hasattr(metrics, "active_sessions")


class TestOTelLoguruHandler:
    """Tests for OTelLoguruHandler class."""

    def test_handler_creation(self):
        """Test handler creation."""
        handler = OTelLoguruHandler()
        assert handler._handler_id is None

    def test_handler_call(self):
        """Test handler call with trace context."""
        handler = OTelLoguruHandler()
        
        # Mock record
        record = {"extra": {}}
        message = MagicMock()
        message.record = record
        
        # Should not modify record without trace context
        handler(message)
        assert "trace_id" not in record["extra"]


class TestGetMetrics:
    """Tests for get_metrics global function."""

    @patch("src.open_llm_vtuber.telemetry._vtuber_metrics", None)
    @patch("src.open_llm_vtuber.telemetry.VTuberMetrics")
    def test_get_metrics_creates_instance(self, mock_metrics_class):
        """Test get_metrics creates global instance."""
        mock_instance = MagicMock()
        mock_metrics_class.return_value = mock_instance
        
        metrics = get_metrics()
        assert metrics == mock_instance
        mock_metrics_class.assert_called_once()