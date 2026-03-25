from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.security import create_access_token, hash_password, verify_password
from ..db.mongodb import get_db
from ..dependencies.auth import get_current_user
from ..models.schemas import AuthResponse, UserLoginRequest, UserRegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(payload: UserRegisterRequest) -> AuthResponse:
    db = get_db()
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    doc = {
        "name": payload.name.strip(),
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
    }
    inserted = await db.users.insert_one(doc)

    token = create_access_token(str(inserted.inserted_id))
    user = UserResponse(id=str(inserted.inserted_id), name=doc["name"], email=doc["email"])
    return AuthResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLoginRequest) -> AuthResponse:
    db = get_db()
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(str(user["_id"]))
    user_response = UserResponse(id=str(user["_id"]), name=user["name"], email=user["email"])
    return AuthResponse(access_token=token, user=user_response)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=str(current_user["_id"]), name=current_user["name"], email=current_user["email"])
