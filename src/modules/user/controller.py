from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.user.dependencies import get_user_service
from src.modules.user.schemas import UserCreate, UserRead
from src.modules.user.service import (
    DuplicateEmailError,
    DuplicateUsernameError,
    UserService,
)

router = APIRouter(prefix="/users", tags=["users"])

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