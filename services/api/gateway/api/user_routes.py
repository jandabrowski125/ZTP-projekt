from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel, EmailStr, Field

from gateway.clients.user_client import UserServiceClient
from gateway.config import settings
from gateway.dto.users import TokenResponseDTO, UpdateProfileBody, UserProfileDTO
from gateway.mappers.user_mapper import to_user_profile_dto, update_body_to_snake

router = APIRouter(prefix="/api/v1")


def get_user_client() -> UserServiceClient:
    return UserServiceClient(
        settings.user_service_url,
        internal_token=settings.internal_service_token,
    )


class RegisterBody(BaseModel):
    model_config = {"populate_by_name": True}

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=1, max_length=200, alias="fullName")
    bio: str | None = None
    location: str | None = None
    avatar_url: str | None = Field(default=None, alias="avatarUrl")


class LoginBody(BaseModel):
    email: EmailStr
    password: str


def _proxy_error(exc: HTTPStatusError) -> HTTPException:
    detail = "User service error"
    try:
        body = exc.response.json()
        if isinstance(body, dict) and "detail" in body:
            detail = body["detail"]
    except Exception:
        pass
    return HTTPException(status_code=exc.response.status_code, detail=detail)


def _token_dto(raw: dict) -> TokenResponseDTO:
    return TokenResponseDTO(
        accessToken=raw["access_token"],
        tokenType=raw.get("token_type", "bearer"),
    )


@router.post("/auth/register", response_model=TokenResponseDTO, response_model_by_alias=True)
async def register(
    body: RegisterBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
) -> TokenResponseDTO:
    payload = body.model_dump(by_alias=True, exclude_none=True)
    snake = {
        "email": payload["email"],
        "password": payload["password"],
        "username": payload["username"],
        "full_name": payload["fullName"],
        "bio": payload.get("bio"),
        "location": payload.get("location"),
        "avatar_url": payload.get("avatarUrl"),
    }
    try:
        return _token_dto(await client.register(snake))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.post("/auth/login", response_model=TokenResponseDTO, response_model_by_alias=True)
async def login(
    body: LoginBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
) -> TokenResponseDTO:
    try:
        return _token_dto(await client.login(body.model_dump(mode="json")))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/users/me", response_model=UserProfileDTO, response_model_by_alias=True)
async def get_me(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> UserProfileDTO:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        raw = await client.get_me(authorization)
        return to_user_profile_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.patch("/users/me", response_model=UserProfileDTO, response_model_by_alias=True)
async def update_me(
    body: UpdateProfileBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> UserProfileDTO:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = update_body_to_snake(body.model_dump(by_alias=True, exclude_unset=True))
    try:
        raw = await client.update_me(authorization, payload)
        return to_user_profile_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc
