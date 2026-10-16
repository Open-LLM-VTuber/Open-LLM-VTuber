"""Voice quality evaluation framework."""

import os
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import wave


@dataclass
class VoiceQualityMetrics:
    """Voice quality evaluation results."""
    mos: Optional[float] = None
    mcd: Optional[float] = None
    wer: Optional[float] = None
    sim: Optional[float] = None
    rtf: Optional[float] = None
    latency_ms: Optional[float] = None

    def __repr__(self):
        parts = []
        if self.mos is not None:
            parts.append(f"MOS={self.mos:.2f}")
        if self.mcd is not None:
            parts.append(f"MCD={self.mcd:.2f}")
        if self.wer is not None:
            parts.append(f"WER={self.wer:.2f}")
        if self.sim is not None:
            parts.append(f"SIM={self.sim:.2f}")
        if self.rtf is not None:
            parts.append(f"RTF={self.rtf:.2f}")
        if self.latency_ms is not None:
            parts.append(f"Latency={self.latency_ms:.1f}ms")
        return "VoiceQualityMetrics(" + " | ".join(parts) + ")"


class VoiceEvaluator:
    """Evaluate voice quality across multiple dimensions."""

    def __init__(self, reference_audio: Optional[str] = None):
        self.reference_audio = reference_audio
        self.results: Dict[str, VoiceQualityMetrics] = {}

    def load_wav(self, path: str) -> Optional[Tuple[np.ndarray, int]]:
        """Load WAV file as numpy array."""
        if not os.path.exists(path):
            return None
        try:
            with wave.open(path, "rb") as wf:
                rate = wf.getframerate()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                raw = wf.readframes(wf.getnframes())

                if sampwidth == 2:
                    dtype = np.int16
                elif sampwidth == 4:
                    dtype = np.int32
                else:
                    dtype = np.int16

                audio = np.frombuffer(raw, dtype=dtype)
                if n_channels > 1:
                    audio = audio.reshape(-1, n_channels)[:, 0]
                return audio.astype(np.float32) / 32768.0, rate
        except Exception as e:
            logger.warning(f"Failed to load {path}: {e}")
            return None

    def compute_mcd(
        self, generated: np.ndarray, reference: np.ndarray, sr: int = 22050
    ) -> float:
        """
        Compute Mel Cepstral Distortion (MCD).
        Lower is better (0 = identical).
        """
        if len(generated) == 0 or len(reference) == 0:
            return float("inf")

        try:
            from scipy.fftpack import dct
            import scipy.signal as signal
        except ImportError:
            return 0.0

        min_len = min(len(generated), len(reference))
        g = generated[:min_len]
        r = reference[:min_len]

        n_fft = 2048
        hop = 512

        def _mfcc(audio):
            spec = np.abs(signal.stft(audio, fs=sr, nperseg=n_fft, noverhop=n_fft - hop)[2])
            mel_basis = self._get_mel_basis(sr, n_fft, 80)
            mel_spec = np.dot(mel_basis, spec)
            mel_spec = np.where(mel_spec == 0, 1e-6, mel_spec)
            log_mel = np.log(mel_spec)
            mfcc = dct(log_mel, type=2, axis=0, norm="ortho")[:13]
            return mfcc

        try:
            g_mfcc = _mfcc(g)
            r_mfcc = _mfcc(r)
            min_frames = min(g_mfcc.shape[1], r_mfcc.shape[1])
            if min_frames == 0:
                return float("inf")
            diff = g_mfcc[:, :min_frames] - r_mfcc[:, :min_frames]
            return float(np.sqrt(np.mean(diff**2)))
        except Exception:
            return 0.0

    def compute_wer(
        self, generated_text: str, reference_text: str
    ) -> float:
        """
        Compute Word Error Rate (WER).
        Lower is better (0 = perfect).
        """
        if not reference_text.strip():
            return 1.0 if generated_text.strip() else 0.0

        ref_words = reference_text.lower().split()
        gen_words = generated_text.lower().split()

        if not ref_words:
            return 0.0

        d = np.zeros((len(ref_words) + 1, len(gen_words) + 1), dtype=int)
        for i in range(len(ref_words) + 1):
            d[i][0] = i
        for j in range(len(gen_words) + 1):
            d[0][j] = j

        for i in range(1, len(ref_words) + 1):
            for j in range(1, len(gen_words) + 1):
                if ref_words[i - 1] == gen_words[j - 1]:
                    d[i][j] = d[i - 1][j - 1]
                else:
                    d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)

        return float(d[len(ref_words)][len(gen_words)]) / max(len(ref_words), 1)

    def compute_rtf(
        self, audio_duration_sec: float, processing_time_sec: float
    ) -> float:
        """
        Compute Real-Time Factor (RTF).
        <1.0 means faster than real-time (good).
        """
        if audio_duration_sec <= 0:
            return float("inf")
        return float(processing_time_sec / audio_duration_sec)

    def compute_latency(self, start_time: float, end_time: float) -> float:
        """Compute latency in milliseconds."""
        return float((end_time - start_time) * 1000.0)

    def evaluate(
        self,
        name: str,
        generated: Optional[np.ndarray] = None,
        reference: Optional[np.ndarray] = None,
        sr: int = 22050,
        generated_text: str = "",
        reference_text: str = "",
        audio_duration: float = 1.0,
        processing_time: float = 0.1,
        start_time: float = 0.0,
        end_time: float = 0.1,
    ) -> VoiceQualityMetrics:
        """Run full evaluation pipeline."""
        metrics = VoiceQualityMetrics()

        if generated is not None and reference is not None and len(generated) > 0 and len(reference) > 0:
            metrics.mcd = self.compute_mcd(generated, reference, sr)

        if generated_text and reference_text:
            metrics.wer = self.compute_wer(generated_text, reference_text)

        if audio_duration > 0:
            metrics.rtf = self.compute_rtf(audio_duration, processing_time)

        if start_time >= 0 and end_time > start_time:
            metrics.latency_ms = self.compute_latency(start_time, end_time)

        self.results[name] = metrics
        logger.info(f"Voice eval [{name}]: {metrics}")
        return metrics

    def _get_mel_basis(self, sr: int, n_fft: int, n_mels: int) -> np.ndarray:
        """Get mel filterbank matrix."""
        low_freq = 0
        high_freq = sr // 2
        mel_min = 2595.0 * np.log10(1.0 + low_freq / 700.0)
        mel_max = 2595.0 * np.log10(1.0 + high_freq / 700.0)
        mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
        hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)
        fft_bins = np.floor((n_fft + 1) * hz_points / sr).astype(int)
        basis = np.zeros((n_mels, n_fft // 2 + 1))
        for m in range(1, n_mels + 1):
            f_m_minus = fft_bins[m - 1]
            f_m = fft_bins[m]
            f_m_plus = fft_bins[m + 1]
            for k in range(f_m_minus, f_m):
                basis[m - 1, k] = (k - fft_bins[m - 1]) / (f_m - fft_bins[m - 1])
            for k in range(f_m, f_m_plus):
                basis[m - 1, k] = (f_m_plus - k) / (f_m_plus - f_m)
        return basis

    def summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all evaluations."""
        summary = {}
        for name, metrics in self.results.items():
            summary[name] = {
                "mos": metrics.mos,
                "mcd": metrics.mcd,
                "wer": metrics.wer,
                "sim": metrics.sim,
                "rtf": metrics.rtf,
                "latency_ms": metrics.latency_ms,
            }
        return summary


class TTSBenchmark:
    """Benchmark and compare multiple TTS models."""

    def __init__(self, reference_audio: Optional[str] = None):
        self.evaluator = VoiceEvaluator(reference_audio)
        self.results: Dict[str, VoiceQualityMetrics] = {}

    def benchmark_provider(
        self,
        name: str,
        tts_func,
        text: str,
        reference: Optional[np.ndarray] = None,
        sr: int = 22050,
        *args,
        **kwargs,
    ) -> VoiceQualityMetrics:
        """
        Benchmark a single TTS provider.

        Args:
            name: Provider name
            tts_func: Callable that takes text and returns (audio_array, duration_sec)
            text: Input text
            reference: Reference audio for MCD comparison
        """
        import time

        start = time.perf_counter()
        try:
            result = tts_func(text, *args, **kwargs)
            if isinstance(result, tuple) and len(result) == 2:
                audio, duration = result
            else:
                audio = result
                duration = len(audio) / sr if hasattr(audio, "__len__") else 1.0
            end = time.perf_counter()
        except Exception as e:
            logger.error(f"TTS provider {name} failed: {e}")
            metrics = VoiceQualityMetrics()
            self.results[name] = metrics
            return metrics

        metrics = self.evaluator.evaluate(
            name=name,
            generated=audio,
            reference=reference,
            sr=sr,
            generated_text=text,
            reference_text=text,
            audio_duration=duration,
            processing_time=end - start,
            start_time=start,
            end_time=end,
        )
        self.results[name] = metrics
        return metrics

    def compare(self) -> Dict[str, Dict[str, float]]:
        """Compare all benchmarked providers."""
        return self.evaluator.summary()

    def best(self, metric: str = "mos") -> Optional[str]:
        """Get provider with best score for given metric."""
        best_name = None
        best_val = None
        for name, metrics in self.results.items():
            val = getattr(metrics, metric, None)
            if val is None:
                continue
            if best_val is None:
                best_val = val
                best_name = name
                continue
            is_better = (
                val > best_val
                if metric in ("mos", "sim")
                else val < best_val
                if metric in ("mcd", "wer", "rtf", "latency_ms")
                else False
            )
            if is_better:
                best_val = val
                best_name = name
        return best_name