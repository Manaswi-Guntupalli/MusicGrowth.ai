from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

# Avoid environment-specific numba JIT DLL restrictions on locked-down Windows setups.
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("NUMBA_DISABLE_CUDA", "1")

import librosa
import numpy as np
from scipy.signal import find_peaks


MIN_VALID_AUDIO_RMS = 1e-4


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


def load_audio(path: str, sr: int = 22050) -> tuple[np.ndarray, int]:
    try:
        y, sampled_rate = librosa.load(path, sr=sr, mono=True)
    except Exception as exc:
        raise ValueError("Please upload a valid music audio file (not empty or silent).") from exc
    
    if len(y) == 0:
        raise ValueError("Please upload a valid music audio file (not empty or silent).")

    rms = float(np.sqrt(np.mean(np.square(y))))
    if not np.isfinite(rms) or rms < MIN_VALID_AUDIO_RMS:
        raise ValueError("Please upload a valid music audio file (not empty or silent).")

    return y, sampled_rate


def select_best_segment(y: np.ndarray, sr: int, segment_seconds: int = 30) -> np.ndarray:
    """Pick the highest-energy section by maximum mean RMS over sliding windows."""
    segment_len = segment_seconds * sr
    if len(y) <= segment_len:
        return y

    frame_length = 2048
    hop_length = 512
    hop = sr
    best_start = 0
    best_score = -1.0

    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
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


def _estimate_tempo_and_beat_density(onset: np.ndarray, sr: int, hop_length: int, duration_seconds: float) -> tuple[float, float]:
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
        peak_times = librosa.frames_to_time(peaks, sr=sr, hop_length=hop_length)
        intervals = np.diff(peak_times)
        valid_intervals = intervals[(intervals > 0.2) & (intervals < 2.0)]
        if len(valid_intervals) > 0:
            tempo = float(60.0 / np.median(valid_intervals))
    else:
        try:
            tempo_candidates = librosa.feature.tempo(onset_envelope=onset, sr=sr, hop_length=hop_length)
            tempo = float(np.atleast_1d(tempo_candidates).item())
        except Exception:
            tempo = 120.0

    return max(1.0, tempo), beat_density


def _zero_crossing_rate_numpy(y: np.ndarray) -> float:
    """Compute global zero-crossing rate without numba-dependent librosa helpers."""
    if y.size < 2:
        return 0.0

    signs = np.signbit(y)
    crossings = np.not_equal(signs[1:], signs[:-1])
    return float(np.mean(crossings))


def extract_raw_features(y: np.ndarray, sr: int) -> RawFeatures:
    hop_length = 512
    duration_seconds = max(float(len(y)) / float(sr), 1.0)

    rms = librosa.feature.rms(y=y)[0]
    zcr = _zero_crossing_rate_numpy(y)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    # Force fixed tuning to avoid pitch-stencil internals that require compiled numba.
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, tuning=0.0)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    tempogram = librosa.feature.tempogram(onset_envelope=onset, sr=sr, hop_length=hop_length)
    tempo, beat_density = _estimate_tempo_and_beat_density(onset, sr, hop_length, duration_seconds)

    harmonic, percussive = librosa.effects.hpss(y)
    harmonic_energy = float(np.mean(np.abs(harmonic)) + 1e-9)
    percussive_energy = float(np.mean(np.abs(percussive)) + 1e-9)

    # Higher values mean a clearer dominant pulse across frames.
    tempo_peak = np.max(tempogram, axis=0)
    tempo_mean = np.mean(tempogram, axis=0) + 1e-9
    pulse_clarity = tempo_peak / tempo_mean
    tempo_consistency = float(np.mean(np.tanh((pulse_clarity - 1.0) / 3.0)))

    return RawFeatures(
        tempo=tempo,
        rms=float(np.mean(rms)),
        zcr=zcr,
        spectral_centroid=float(np.mean(centroid)),
        spectral_bandwidth=float(np.mean(bandwidth)),
        loudness_db=float(librosa.amplitude_to_db(np.array([float(np.mean(rms)) + 1e-9]), ref=1.0)[0]),
        chroma_mean=float(np.mean(chroma)),
        mfcc_mean=float(np.mean(mfcc[:5])),
        mfcc_mean_1=float(np.mean(mfcc[0])),
        mfcc_mean_2=float(np.mean(mfcc[1])),
        mfcc_mean_3=float(np.mean(mfcc[2])),
        mfcc_mean_4=float(np.mean(mfcc[3])),
        mfcc_mean_5=float(np.mean(mfcc[4])),
        onset_strength=float(np.mean(onset)),
        harmonic_ratio=harmonic_energy / (harmonic_energy + percussive_energy),
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
