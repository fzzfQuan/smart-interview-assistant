from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.db_models import User, UserProfile
from app.models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

from .deps import create_access_token, hash_password, require_user, verify_password

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_session)):
    """用户注册。"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已被使用",
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被使用",
        )

    # 创建用户
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        display_name=req.display_name or req.username,
    )
    db.add(user)
    await db.flush()  # 获取 user.id

    # 同步创建用户画像记录
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.flush()

    # 生成令牌
    access_token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=access_token,
        user=UserOut(
            id=str(user.id),
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_session)):
    """用户登录。"""
    result = await db.execute(
        select(User).where(User.username == req.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    access_token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=access_token,
        user=UserOut(
            id=str(user.id),
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
    )


@router.get("/auth/me", response_model=UserOut)
async def get_me(user: User = Depends(require_user)):
    """获取当前登录用户信息。"""
    return UserOut(
        id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
