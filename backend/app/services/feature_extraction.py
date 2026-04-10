from __future__ import annotations

from dataclasses import dataclass
from math import gcd
import os
from typing import Any

# Avoid environment-specific numba JIT DLL restrictions on locked-down Windows setups.
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("NUMBA_DISABLE_CUDA", "1")

import audioread
import numpy as np
import soundfile as sf
from scipy.fft import dct
from scipy.signal import find_peaks, resample_poly

try:
    import librosa
except Exception:  # pragma: no cover - optional decode helper
    librosa = None


MIN_VALID_AUDIO_RMS = 1e-4
FRAME_LENGTH = 2048
HOP_LENGTH = 512


@dataclass
class RawFeatures:
    tempo: float
    rms: float
    zcr: float
    spectral_centroid: float
    spectral_bandwidth: float
    loudness_db: float
    chroma_mean: float
    mfcc_mean: float
    mfcc_mean_1: float
    mfcc_mean_2: float
    mfcc_mean_3: float
    mfcc_mean_4: float
    mfcc_mean_5: float
    onset_strength: float
    harmonic_ratio: float
    beat_strength: float
    tempo_consistency: float


def _to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio
    # soundfile returns shape (frames, channels) for multichannel files.
    return np.mean(audio, axis=1)


def _resample_audio(audio: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    if source_sr == target_sr:
        return audio

    ratio_gcd = gcd(int(source_sr), int(target_sr))
    up = int(target_sr // ratio_gcd)
    down = int(source_sr // ratio_gcd)
    return resample_poly(audio, up=up, down=down).astype(np.float32, copy=False)


def _load_audio_with_audioread(path: str, target_sr: int) -> tuple[np.ndarray, int]:
    with audioread.audio_open(path) as source:
        source_sr = int(getattr(source, "samplerate", 0))
        channels = int(getattr(source, "channels", 1))
        if source_sr <= 0:
            raise RuntimeError("Invalid sample rate in uploaded audio.")

        chunks: list[np.ndarray] = []
        for raw in source:
            chunk = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            if channels > 1:
                chunk = chunk.reshape(-1, channels).mean(axis=1)
            chunk /= 32768.0
            chunks.append(chunk)

    if not chunks:
        raise RuntimeError("Uploaded audio has no decodable samples.")

    y = np.concatenate(chunks).astype(np.float32, copy=False)
    sampled_rate = source_sr

    if target_sr > 0 and sampled_rate != target_sr:
        y = _resample_audio(y, source_sr=sampled_rate, target_sr=target_sr)
        sampled_rate = target_sr

    return y, sampled_rate


def load_audio(path: str, sr: int = 22050) -> tuple[np.ndarray, int]:
    y: np.ndarray | None = None
    sampled_rate: int | None = None

    try:
        decoded, source_sr = sf.read(path, dtype="float32", always_2d=False)
        y = _to_mono(np.asarray(decoded, dtype=np.float32))
        sampled_rate = int(source_sr)
        if sampled_rate <= 0:
            raise RuntimeError("Invalid sample rate in uploaded audio.")

        if sr > 0 and sampled_rate != sr:
            y = _resample_audio(y, source_sr=sampled_rate, target_sr=sr)
            sampled_rate = sr
    except Exception:
        # librosa/audioread fallback keeps compatibility when libsndfile can't decode a format.
        try:
            if librosa is None:
                raise RuntimeError("librosa unavailable")
            y, sampled_rate = librosa.load(path, sr=sr, mono=True)
        except Exception:
            try:
                y, sampled_rate = _load_audio_with_audioread(path, target_sr=sr)
            except Exception as exc:
                raise ValueError("Please upload a valid music audio file (not empty or silent).") from exc

    if y is None or sampled_rate is None or len(y) == 0:
        raise ValueError("Please upload a valid music audio file (not empty or silent).")

    y = np.asarray(y, dtype=np.float32)
    if not np.all(np.isfinite(y)):
        raise ValueError("Please upload a valid music audio file (not empty or silent).")

    rms = float(np.sqrt(np.mean(np.square(y))))
    if not np.isfinite(rms) or rms < MIN_VALID_AUDIO_RMS:
        raise ValueError("Please upload a valid music audio file (not empty or silent).")

    return y, sampled_rate


def _frame_audio(y: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
    y = np.asarray(y, dtype=np.float32)
    if y.size == 0:
        return np.zeros((0, frame_length), dtype=np.float32)

    if y.size < frame_length:
        y = np.pad(y, (0, frame_length - y.size), mode="constant")

    y = np.ascontiguousarray(y)
    frame_count = 1 + (y.size - frame_length) // hop_length
    shape = (frame_count, frame_length)
    strides = (y.strides[0] * hop_length, y.strides[0])
    return np.lib.stride_tricks.as_strided(y, shape=shape, strides=strides, writeable=False)


def _rms_envelope_numpy(y: np.ndarray, frame_length: int = FRAME_LENGTH, hop_length: int = HOP_LENGTH) -> np.ndarray:
    frames = _frame_audio(y, frame_length=frame_length, hop_length=hop_length)
    if frames.size == 0:
        return np.zeros(1, dtype=np.float32)
    return np.sqrt(np.mean(np.square(frames), axis=1) + 1e-12).astype(np.float32, copy=False)


def _magnitude_spectrogram(y: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
    frames = _frame_audio(y, frame_length=frame_length, hop_length=hop_length)
    if frames.size == 0:
        return np.zeros((frame_length // 2 + 1, 1), dtype=np.float32)

    window = np.hanning(frame_length).astype(np.float32)
    stft = np.fft.rfft(frames * window[None, :], axis=1)
    return np.abs(stft).astype(np.float32, copy=False).T


def _spectral_centroid_and_bandwidth(magnitude: np.ndarray, sr: int, frame_length: int) -> tuple[float, float]:
    if magnitude.size == 0:
        return 0.0, 0.0

    freqs = np.fft.rfftfreq(frame_length, d=1.0 / float(sr)).astype(np.float32)
    power = np.sum(magnitude, axis=0) + 1e-9

    centroid = np.sum(freqs[:, None] * magnitude, axis=0) / power
    bandwidth = np.sqrt(np.sum(((freqs[:, None] - centroid[None, :]) ** 2) * magnitude, axis=0) / power)
    return float(np.mean(centroid)), float(np.mean(bandwidth))


def _chroma_mean_numpy(magnitude: np.ndarray, sr: int, frame_length: int) -> float:
    if magnitude.size == 0:
        return 0.0

    freqs = np.fft.rfftfreq(frame_length, d=1.0 / float(sr)).astype(np.float32)
    valid = freqs > 27.5
    if not np.any(valid):
        return 0.0

    chroma = np.zeros((12, magnitude.shape[1]), dtype=np.float32)
    midi = np.round(69.0 + 12.0 * np.log2(freqs[valid] / 440.0)).astype(np.int32)
    pitch_classes = np.mod(midi, 12)
    np.add.at(chroma, pitch_classes, magnitude[valid])

    chroma /= (np.sum(chroma, axis=0, keepdims=True) + 1e-9)
    return float(np.clip(np.mean(chroma), 0.0, 1.0))


def _mfcc_like_coefficients(magnitude: np.ndarray) -> tuple[float, list[float]]:
    if magnitude.size == 0:
        return 0.0, [0.0, 0.0, 0.0, 0.0, 0.0]

    power = np.mean(np.square(magnitude), axis=1) + 1e-9
    log_power = np.log(power)
    coeffs = dct(log_power, type=2, norm="ortho")
    coeffs = np.asarray(coeffs, dtype=np.float32)

    if coeffs.size < 5:
        coeffs = np.pad(coeffs, (0, 5 - coeffs.size), mode="constant")

    mfcc_5 = coeffs[:5]
    return float(np.mean(mfcc_5)), [float(v) for v in mfcc_5]


def _harmonic_ratio_numpy(magnitude: np.ndarray, sr: int, frame_length: int) -> float:
    if magnitude.size == 0:
        return 0.5

    freqs = np.fft.rfftfreq(frame_length, d=1.0 / float(sr)).astype(np.float32)
    harmonic_mask = freqs <= 1500.0
    if not np.any(harmonic_mask) or np.all(harmonic_mask):
        return 0.5

    harmonic_energy = float(np.mean(np.square(magnitude[harmonic_mask])) + 1e-9)
    percussive_energy = float(np.mean(np.square(magnitude[~harmonic_mask])) + 1e-9)
    return float(harmonic_energy / (harmonic_energy + percussive_energy))


def select_best_segment(y: np.ndarray, sr: int, segment_seconds: int = 30) -> np.ndarray:
    """Pick the highest-energy section by maximum mean RMS over sliding windows."""
    segment_len = segment_seconds * sr
    if len(y) <= segment_len:
        return y

    frame_length = FRAME_LENGTH
    hop_length = HOP_LENGTH
    hop = sr
    best_start = 0
    best_score = -1.0

    rms = _rms_envelope_numpy(y, frame_length=frame_length, hop_length=hop_length)
    samples_per_rms_frame = hop_length
    window_frames = max(1, segment_len // samples_per_rms_frame)

    for start in range(0, len(y) - segment_len + 1, hop):
        end = start + segment_len
        start_frame = start // samples_per_rms_frame
        end_frame = start_frame + window_frames
        rms_slice = rms[start_frame:end_frame]
        if len(rms_slice) == 0:
            continue
        score = float(np.mean(rms_slice))
        if score > best_score:
            best_score = score
            best_start = start

    return y[best_start : best_start + segment_len]


def _estimate_tempo_and_beat_density(
    onset: np.ndarray,
    sr: int,
    hop_length: int,
    duration_seconds: float,
) -> tuple[float, float, np.ndarray]:
    """
    Estimate tempo/beat density without relying on librosa.beat.beat_track.

    This avoids numba-heavy internals that can fail under strict Windows
    application control policies.
    """
    min_peak_distance = max(1, int((60.0 / 220.0) * sr / hop_length))
    onset_height = float(np.mean(onset)) if onset.size else 0.0
    peaks, _ = find_peaks(onset, distance=min_peak_distance, height=onset_height)

    beat_density = float(len(peaks)) / max(duration_seconds, 1.0)
    tempo = 120.0

    if len(peaks) >= 2:
        peak_times = (peaks.astype(np.float64) * float(hop_length)) / float(sr)
        intervals = np.diff(peak_times)
        valid_intervals = intervals[(intervals > 0.2) & (intervals < 2.0)]
        if len(valid_intervals) > 0:
            tempo = float(60.0 / np.median(valid_intervals))
    else:
        centered = onset - np.mean(onset)
        if centered.size > 4 and np.any(np.isfinite(centered)):
            autocorr = np.correlate(centered, centered, mode="full")[centered.size - 1 :]
            min_lag = max(1, int((60.0 / 220.0) * sr / hop_length))
            max_lag = min(len(autocorr) - 1, int((60.0 / 45.0) * sr / hop_length))
            if max_lag > min_lag:
                local = autocorr[min_lag : max_lag + 1]
                best_lag = int(np.argmax(local)) + min_lag
                tempo = float((60.0 * sr) / (best_lag * hop_length))

    return max(1.0, tempo), beat_density, peaks


def _tempo_consistency_from_peaks(peaks: np.ndarray) -> float:
    if peaks.size < 3:
        return 0.45

    intervals = np.diff(peaks.astype(np.float32))
    mean_interval = float(np.mean(intervals))
    if mean_interval <= 1e-6:
        return 0.45

    variation = float(np.std(intervals) / (mean_interval + 1e-9))
    return float(np.clip(np.exp(-variation), 0.0, 1.0))


def _zero_crossing_rate_numpy(y: np.ndarray) -> float:
    """Compute global zero-crossing rate without numba-dependent librosa helpers."""
    if y.size < 2:
        return 0.0

    signs = np.signbit(y)
    crossings = np.not_equal(signs[1:], signs[:-1])
    return float(np.mean(crossings))


def extract_raw_features(y: np.ndarray, sr: int) -> RawFeatures:
    hop_length = HOP_LENGTH
    frame_length = FRAME_LENGTH
    duration_seconds = max(float(len(y)) / float(sr), 1.0)

    rms = _rms_envelope_numpy(y, frame_length=frame_length, hop_length=hop_length)
    zcr = _zero_crossing_rate_numpy(y)
    magnitude = _magnitude_spectrogram(y, frame_length=frame_length, hop_length=hop_length)
    centroid_mean, bandwidth_mean = _spectral_centroid_and_bandwidth(magnitude, sr=sr, frame_length=frame_length)
    chroma_mean = _chroma_mean_numpy(magnitude, sr=sr, frame_length=frame_length)
    mfcc_mean, mfcc_components = _mfcc_like_coefficients(magnitude)

    onset = np.maximum(0.0, np.diff(rms, prepend=rms[:1])).astype(np.float32, copy=False)
    tempo, beat_density, peaks = _estimate_tempo_and_beat_density(onset, sr, hop_length, duration_seconds)
    tempo_consistency = _tempo_consistency_from_peaks(peaks)

    harmonic_ratio = _harmonic_ratio_numpy(magnitude, sr=sr, frame_length=frame_length)
    loudness_db = float(20.0 * np.log10(float(np.mean(rms)) + 1e-9))

    return RawFeatures(
        tempo=tempo,
        rms=float(np.mean(rms)),
        zcr=zcr,
        spectral_centroid=centroid_mean,
        spectral_bandwidth=bandwidth_mean,
        loudness_db=loudness_db,
        chroma_mean=chroma_mean,
        mfcc_mean=mfcc_mean,
        mfcc_mean_1=mfcc_components[0],
        mfcc_mean_2=mfcc_components[1],
        mfcc_mean_3=mfcc_components[2],
        mfcc_mean_4=mfcc_components[3],
        mfcc_mean_5=mfcc_components[4],
        onset_strength=float(np.mean(onset)),
        harmonic_ratio=harmonic_ratio,
        beat_strength=beat_density,
        tempo_consistency=tempo_consistency,
    )


def extract_features_from_path(path: str, segment_mode: str = "best") -> dict[str, Any]:
    y, sr = load_audio(path)
    if segment_mode == "best":
        y = select_best_segment(y, sr)

    raw = extract_raw_features(y, sr)
    return {
        "tempo": raw.tempo,
        "rms": raw.rms,
        "zcr": raw.zcr,
        "spectral_centroid": raw.spectral_centroid,
        "spectral_bandwidth": raw.spectral_bandwidth,
        "loudness_db": raw.loudness_db,
        "chroma_mean": raw.chroma_mean,
        "mfcc_mean": raw.mfcc_mean,
        "mfcc_mean_1": raw.mfcc_mean_1,
        "mfcc_mean_2": raw.mfcc_mean_2,
        "mfcc_mean_3": raw.mfcc_mean_3,
        "mfcc_mean_4": raw.mfcc_mean_4,
        "mfcc_mean_5": raw.mfcc_mean_5,
        "onset_strength": raw.onset_strength,
        "harmonic_ratio": raw.harmonic_ratio,
        "beat_strength": raw.beat_strength,
        "tempo_consistency": raw.tempo_consistency,
    }
