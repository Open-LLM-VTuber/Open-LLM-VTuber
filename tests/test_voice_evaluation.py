"""Tests for voice quality evaluation framework."""

import numpy as np

from src.open_llm_vtuber.evaluation.voice_evaluator import (
    VoiceEvaluator,
    VoiceQualityMetrics,
    TTSBenchmark,
)


class TestVoiceQualityMetrics:
    """Tests for VoiceQualityMetrics dataclass."""

    def test_default(self):
        metrics = VoiceQualityMetrics()
        assert metrics.mos is None
        assert metrics.mcd is None
        assert metrics.wer is None
        assert metrics.sim is None
        assert metrics.rtf is None
        assert metrics.latency_ms is None

    def test_with_values(self):
        metrics = VoiceQualityMetrics(
            mos=4.2, mcd=5.1, wer=0.05, sim=0.60, rtf=0.8, latency_ms=75.0
        )
        assert metrics.mos == 4.2
        assert metrics.mcd == 5.1
        assert metrics.wer == 0.05
        assert metrics.sim == 0.60
        assert metrics.rtf == 0.8
        assert metrics.latency_ms == 75.0

    def test_repr(self):
        metrics = VoiceQualityMetrics(mos=4.2, rtf=0.8)
        repr_str = repr(metrics)
        assert "MOS=4.20" in repr_str
        assert "RTF=0.80" in repr_str


class TestVoiceEvaluator:
    """Tests for VoiceEvaluator."""

    def test_init(self):
        evaluator = VoiceEvaluator()
        assert evaluator.reference_audio is None
        assert evaluator.results == {}

    def test_init_with_reference(self):
        evaluator = VoiceEvaluator(reference_audio="/path/to/ref.wav")
        assert evaluator.reference_audio == "/path/to/ref.wav"

    def test_load_wav_nonexistent(self):
        evaluator = VoiceEvaluator()
        result = evaluator.load_wav("/nonexistent/file.wav")
        assert result is None

    def test_compute_wer_perfect(self):
        evaluator = VoiceEvaluator()
        wer = evaluator.compute_wer("hello world", "hello world")
        assert wer == 0.0

    def test_compute_wer_total_failure(self):
        evaluator = VoiceEvaluator()
        wer = evaluator.compute_wer("abc def", "xyz ghi")
        assert wer == 1.0

    def test_compute_wer_partial(self):
        evaluator = VoiceEvaluator()
        wer = evaluator.compute_wer("hello world", "world")
        assert 0 <= wer <= 1

    def test_compute_wer_empty_reference(self):
        evaluator = VoiceEvaluator()
        wer = evaluator.compute_wer("hello", "")
        assert wer == 1.0

    def test_compute_rtf(self):
        evaluator = VoiceEvaluator()
        rtf = evaluator.compute_rtf(10.0, 5.0)
        assert rtf == 0.5

    def test_compute_rtf_slower(self):
        evaluator = VoiceEvaluator()
        rtf = evaluator.compute_rtf(5.0, 10.0)
        assert rtf == 2.0

    def test_compute_rtf_zero_duration(self):
        evaluator = VoiceEvaluator()
        rtf = evaluator.compute_rtf(0.0, 5.0)
        assert rtf == float("inf")

    def test_compute_latency(self):
        evaluator = VoiceEvaluator()
        latency = evaluator.compute_latency(0.0, 1.0)
        assert latency == 1000.0

    def test_evaluate_full(self):
        evaluator = VoiceEvaluator()
        generated = np.random.randn(1000).astype(np.float32)
        reference = np.random.randn(1000).astype(np.float32)
        metrics = evaluator.evaluate(
            name="test",
            generated=generated,
            reference=reference,
            sr=22050,
            generated_text="hello",
            reference_text="hello",
            audio_duration=1.0,
            processing_time=0.5,
            start_time=0.0,
            end_time=0.1,
        )
        assert isinstance(metrics, VoiceQualityMetrics)
        assert metrics.mcd is not None
        assert metrics.wer == 0.0
        assert metrics.rtf == 0.5
        assert metrics.latency_ms == 100.0

    def test_evaluate_no_audio(self):
        evaluator = VoiceEvaluator()
        metrics = evaluator.evaluate(
            name="test",
            generated_text="hello",
            reference_text="hello",
            audio_duration=1.0,
            processing_time=0.5,
            start_time=0.0,
            end_time=0.1,
        )
        assert metrics.mcd is None

    def test_summary(self):
        evaluator = VoiceEvaluator()
        generated = np.random.randn(500).astype(np.float32)
        reference = np.random.randn(500).astype(np.float32)
        evaluator.evaluate(
            name="provider1",
            generated=generated,
            reference=reference,
            sr=22050,
            audio_duration=1.0,
            processing_time=0.1,
            start_time=0.0,
            end_time=0.01,
        )
        summary = evaluator.summary()
        assert "provider1" in summary
        assert "mcd" in summary["provider1"]
        assert "rtf" in summary["provider1"]


class TestTTSBenchmark:
    """Tests for TTSBenchmark."""

    def test_init(self):
        benchmark = TTSBenchmark()
        assert isinstance(benchmark.evaluator, VoiceEvaluator)
        assert benchmark.results == {}

    def test_benchmark_success(self):
        def mock_tts(text):
            audio = np.random.randn(1000).astype(np.float32)
            return audio, 1.0

        benchmark = TTSBenchmark()
        metrics = benchmark.benchmark_provider(
            name="test_tts",
            tts_func=mock_tts,
            text="hello world",
        )
        assert isinstance(metrics, VoiceQualityMetrics)
        assert "test_tts" in benchmark.results

    def test_benchmark_failure(self):
        def failing_tts(text):
            raise RuntimeError("TTS failed")

        benchmark = TTSBenchmark()
        metrics = benchmark.benchmark_provider(
            name="failing_tts",
            tts_func=failing_tts,
            text="hello world",
        )
        assert metrics is not None
        assert "failing_tts" in benchmark.results

    def test_compare(self):
        def mock_tts(text):
            return np.random.randn(500).astype(np.float32), 1.0

        benchmark = TTSBenchmark()
        benchmark.benchmark_provider("provider_a", mock_tts, "test")
        benchmark.benchmark_provider("provider_b", mock_tts, "test")
        comparison = benchmark.compare()
        assert "provider_a" in comparison
        assert "provider_b" in comparison

    def test_best_mos(self):
        def mock_tts_a(text):
            return np.random.randn(500).astype(np.float32), 1.0

        benchmark = TTSBenchmark()
        benchmark.results["provider_a"] = VoiceQualityMetrics(mos=4.0)
        benchmark.results["provider_b"] = VoiceQualityMetrics(mos=4.5)
        best = benchmark.best("mos")
        assert best == "provider_b"

    def test_best_mcd(self):
        def mock_tts(text):
            return np.random.randn(500).astype(np.float32), 1.0

        benchmark = TTSBenchmark()
        benchmark.results["provider_a"] = VoiceQualityMetrics(mcd=5.0)
        benchmark.results["provider_b"] = VoiceQualityMetrics(mcd=3.0)
        best = benchmark.best("mcd")
        assert best == "provider_b"
