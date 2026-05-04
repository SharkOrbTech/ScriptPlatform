"""Authentication API endpoints."""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, UserDB
from app.core.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateAccountRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with username and password."""
    result = await db.execute(select(UserDB).where(UserDB.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({
        "sub": user.username,
        "is_admin": user.is_admin,
    })

    return {
        "token": token,
        "username": user.username,
        "is_admin": user.is_admin,
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return user


@router.post("/create-account")
async def create_account(
    request: CreateAccountRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new account (admin only)."""
    # Check if username already exists
    result = await db.execute(select(UserDB).where(UserDB.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = UserDB(
        id=str(uuid.uuid4()),
        username=request.username,
        password_hash=hash_password(request.password),
        is_admin=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()

    return {"message": "账号创建成功", "username": request.username}


@router.get("/accounts")
async def list_accounts(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all accounts (admin only)."""
    result = await db.execute(select(UserDB).order_by(UserDB.created_at.desc()))
    users = result.scalars().all()

    return {
        "accounts": [
            {
                "id": u.id,
                "username": u.username,
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }


@router.delete("/accounts/{username}")
async def delete_account(
    username: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete an account (admin only). Cannot delete yourself."""
    if username == admin["username"]:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    result = await db.execute(select(UserDB).where(UserDB.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    await db.delete(user)
    await db.commit()

    return {"message": "账号已删除"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for current user."""
    result = await db.execute(select(UserDB).where(UserDB.username == user["username"]))
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(request.old_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    db_user.password_hash = hash_password(request.new_password)
    await db.commit()

    return {"message": "密码修改成功"}


async def create_default_admin(db: AsyncSession):
    """Create default admin account if no users exist."""
    result = await db.execute(select(UserDB))
    if result.scalar_one_or_none() is not None:
        return  # Users already exist

    admin = UserDB(
        id=str(uuid.uuid4()),
        username="admin",
        password_hash=hash_password("admin123"),
        is_admin=True,
        created_at=datetime.utcnow(),
    )
    db.add(admin)
    await db.commit()
    print("Default admin account created: admin / admin123")
