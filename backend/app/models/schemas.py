from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SoundDNA(BaseModel):
    tempo: float
    energy: float
    danceability: float
    valence: float
    acousticness: float
    instrumentalness: float
    speechiness: float
    loudness: float
    liveness: float
    mfcc_mean_1: float
    mfcc_mean_2: float
    mfcc_mean_3: float
    mfcc_mean_4: float
    mfcc_mean_5: float
    production_style: str
    mood: str


class SimilarReference(BaseModel):
    artist: str
    song: str
    cluster: str
    similarity: float


class DifferenceInsight(BaseModel):
    feature: str
    song_value: float
    reference_mean: float
    delta_percent: float
    interpretation: str


class StrategicPath(BaseModel):
    id: str
    title: str
    strategy: str
    expected: str
    tradeoff: str
    actions: list[str]


class StyleClusterPrediction(BaseModel):
    cluster_id: int
    label: str
    confidence: float


class AnalysisResponse(BaseModel):
    analysis_id: str | None = None
    sound_dna: SoundDNA
    style_cluster: StyleClusterPrediction
    top_similar: list[SimilarReference]
    differences: list[DifferenceInsight]
    market_gaps: list[str]
    paths: list[StrategicPath]


class UserRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AnalysisHistoryItem(BaseModel):
    id: str
    filename: str
    segment_mode: str
    mood: str
    production_style: str
    created_at: datetime
    result: AnalysisResponse | None = None


class Analysis(BaseModel):
    id: str
    user_id: str
    filename: str
    segment_mode: str
    result: AnalysisResponse
    created_at: datetime = Field(default_factory=datetime.utcnow)
