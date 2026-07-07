from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.user.dependencies import get_user_service
from src.modules.user.schemas import UserCreate, UserRead
from src.modules.user.service import (
    DuplicateEmailError,
    DuplicateUsernameError,
    UserService,
)
from src.modules.user.model import User

from src.modules.user.auth_service import AuthService, ReusedRefreshTokenError, InvalidRefreshTokenError
from src.modules.user.dependencies import get_auth_service, get_current_user
from src.modules.user.schemas import LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from src.modules.user.service import InvalidCredentialsError

router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    try:
        user = await service.create_user(
            email=data.email,
            username=data.username,
            plain_password=data.password,
        )
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DuplicateUsernameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return UserRead.model_validate(user)

@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        tokens = await service.login(email=data.email, plain_password=data.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )

@router.get("/me", response_model=UserRead)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(current_user)

@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        tokens = await service.refresh(data.refresh_token)
    except ReusedRefreshTokenError:
        # Same status as any other invalid-token case — don't reveal that
        # reuse specifically was detected. The client just needs to log in again.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
        )
    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
        )

    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)

@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await service.logout(data.refresh_token)