# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.security import create_access_token, hash_password, verify_password
# from app.database import get_db
# from app.models import User
# from app.schemas import LoginRequest, TokenResponse, UserCreate, UserRead

# router = APIRouter(prefix="/auth", tags=["auth"])


# @router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
# async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
#     # Check uniqueness
#     existing = await db.execute(
#         select(User).where((User.email == body.email) | (User.username == body.username))
#     )
#     if existing.scalar_one_or_none():
#         raise HTTPException(status_code=400, detail="Email or username already taken")

#     user = User(
#         username=body.username,
#         email=body.email,
#         hashed_password=hash_password(body.password),
#     )
#     db.add(user)
#     await db.flush()
#     await db.refresh(user)
#     return user


# @router.post("/login", response_model=TokenResponse)
# async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.username == body.username))
#     user = result.scalar_one_or_none()

#     if user is None or not verify_password(body.password, user.hashed_password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")
#     if not user.is_active:
#         raise HTTPException(status_code=403, detail="Account disabled")

#     return TokenResponse(access_token=create_access_token(user.id))


# @router.get("/me", response_model=UserRead)
# async def me(current_user: User = Depends(get_current_user_dep)):
#     return current_user


# # Local import to avoid circular deps
# from app.core.deps import get_current_user as get_current_user_dep  # noqa: E402
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already taken")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user