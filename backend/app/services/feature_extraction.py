from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import librosa
import numpy as np


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
    onset_strength: float
    harmonic_ratio: float


def load_audio(path: str, sr: int = 22050) -> tuple[np.ndarray, int]:
    y, sampled_rate = librosa.load(path, sr=sr, mono=True)
    if len(y) == 0:
        raise ValueError("Audio file appears empty.")
    return y, sampled_rate


def select_best_segment(y: np.ndarray, sr: int, segment_seconds: int = 30) -> np.ndarray:
    """Pick a musically active segment using RMS + onset strength."""
    segment_len = segment_seconds * sr
    if len(y) <= segment_len:
        return y

    hop = sr // 2
    best_start = 0
    best_score = -1.0

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    rms = librosa.feature.rms(y=y, hop_length=512)[0]

    for start in range(0, len(y) - segment_len, hop):
        end = start + segment_len
        rms_slice = rms[start // 512 : end // 512]
        onset_slice = onset_env[start // 512 : end // 512]
        if len(rms_slice) == 0 or len(onset_slice) == 0:
            continue
        score = float(np.mean(rms_slice) * 0.6 + np.mean(onset_slice) * 0.4)
        if score > best_score:
            best_score = score
            best_start = start

    return y[best_start : best_start + segment_len]


def extract_raw_features(y: np.ndarray, sr: int) -> RawFeatures:
    tempo_arr, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo_arr).item())

    rms = librosa.feature.rms(y=y)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    onset = librosa.onset.onset_strength(y=y, sr=sr)

    harmonic, percussive = librosa.effects.hpss(y)
    harmonic_energy = float(np.mean(np.abs(harmonic)) + 1e-9)
    percussive_energy = float(np.mean(np.abs(percussive)) + 1e-9)

    return RawFeatures(
        tempo=tempo,
        rms=float(np.mean(rms)),
        zcr=float(np.mean(zcr)),
        spectral_centroid=float(np.mean(centroid)),
        spectral_bandwidth=float(np.mean(bandwidth)),
        loudness_db=float(librosa.amplitude_to_db(np.array([np.max(np.abs(y)) + 1e-9]), ref=1.0)[0]),
        chroma_mean=float(np.mean(chroma)),
        mfcc_mean=float(np.mean(mfcc)),
        onset_strength=float(np.mean(onset)),
        harmonic_ratio=harmonic_energy / (harmonic_energy + percussive_energy),
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
        "onset_strength": raw.onset_strength,
        "harmonic_ratio": raw.harmonic_ratio,
    }
