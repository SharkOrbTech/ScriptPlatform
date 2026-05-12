"""Admin management API endpoints.

Admin-only endpoints for:
  - Managing accounts (promote/demote, reset password)
  - Listing and managing scripts across all accounts
  - Transferring/copying/deleting scripts on behalf of any user
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, UserDB
from app.core.auth import hash_password, require_admin
from app.api import scripts as scripts_module

router = APIRouter(prefix="/api/admin", tags=["admin"])


class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


class TransferScriptRequest(BaseModel):
    owner: str = Field(..., description="新所有者的用户名")


class CopyScriptRequest(BaseModel):
    target_owner: str = Field(..., description="目标用户的用户名")
    new_title: str | None = Field(
        default=None, description="可选：复制出的剧本标题（默认保持原标题）"
    )


async def _ensure_user_exists(db: AsyncSession, username: str) -> UserDB:
    result = await db.execute(select(UserDB).where(UserDB.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")
    return user


# ---------- Account management ----------

@router.post("/accounts/{username}/promote")
async def promote_account(
    username: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """提升账号为管理员。"""
    user = await _ensure_user_exists(db, username)
    if user.is_admin:
        return {"message": "已经是管理员", "username": username}
    user.is_admin = True
    await db.commit()
    return {"message": "已提升为管理员", "username": username}


@router.post("/accounts/{username}/demote")
async def demote_account(
    username: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """取消账号的管理员权限。不能取消自己的。"""
    if username == admin["username"]:
        raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")
    user = await _ensure_user_exists(db, username)
    if not user.is_admin:
        return {"message": "该账号不是管理员", "username": username}
    user.is_admin = False
    await db.commit()
    return {"message": "已取消管理员权限", "username": username}


@router.post("/accounts/{username}/reset-password")
async def reset_account_password(
    username: str,
    request: PasswordResetRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员重置指定账号的密码。"""
    user = await _ensure_user_exists(db, username)
    user.password_hash = hash_password(request.new_password)
    await db.commit()
    return {"message": "密码已重置", "username": username}


# ---------- Script management (cross-account) ----------

def _script_summary(s: dict) -> dict:
    created_at = s.get("created_at", "")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    return {
        "id": s.get("id", ""),
        "title": s.get("title", ""),
        "genre": s.get("genre", ""),
        "logline": s.get("logline", ""),
        "episode_count": len(s.get("episodes", [])),
        "character_count": len(s.get("characters", [])),
        "created_at": created_at,
        "owner": s.get("owner") or scripts_module.DEFAULT_LEGACY_OWNER,
    }


@router.get("/scripts")
async def list_all_scripts(admin: dict = Depends(require_admin)):
    """列出所有账号的剧本（仅管理员）。"""
    items = [
        _script_summary(s) for s in scripts_module._script_store.values()
    ]
    # Sort newest first by created_at
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"items": items}


@router.get("/accounts/{username}/scripts")
async def list_scripts_for_account(
    username: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查看某个账号拥有的所有剧本（仅管理员）。"""
    await _ensure_user_exists(db, username)
    items = [
        _script_summary(s)
        for s in scripts_module._script_store.values()
        if (s.get("owner") or scripts_module.DEFAULT_LEGACY_OWNER) == username
    ]
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"username": username, "items": items}


@router.post("/scripts/{script_id}/transfer")
async def transfer_script(
    script_id: str,
    request: TransferScriptRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """将指定剧本的所有权转移到另一个账号（仅管理员）。"""
    if script_id not in scripts_module._script_store:
        raise HTTPException(status_code=404, detail="剧本不存在")
    await _ensure_user_exists(db, request.owner)
    scripts_module._script_store[script_id]["owner"] = request.owner
    scripts_module.save_script_to_disk_cache()
    return {
        "message": "剧本已转移",
        "script_id": script_id,
        "new_owner": request.owner,
    }


@router.post("/scripts/{script_id}/copy")
async def copy_script(
    script_id: str,
    request: CopyScriptRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """复制一份剧本给指定账号（原剧本保留）。"""
    if script_id not in scripts_module._script_store:
        raise HTTPException(status_code=404, detail="剧本不存在")
    await _ensure_user_exists(db, request.target_owner)

    import copy
    source = scripts_module._script_store[script_id]
    new_id = str(uuid.uuid4())[:8]
    cloned = copy.deepcopy(source)
    cloned["id"] = new_id
    cloned["owner"] = request.target_owner
    cloned["created_at"] = datetime.utcnow().isoformat()
    if request.new_title:
        cloned["title"] = request.new_title

    scripts_module._script_store[new_id] = cloned
    scripts_module.save_script_to_disk_cache()

    return {
        "message": "剧本已复制",
        "source_id": script_id,
        "new_id": new_id,
        "target_owner": request.target_owner,
        "title": cloned["title"],
    }


@router.delete("/scripts/{script_id}")
async def admin_delete_script(
    script_id: str,
    admin: dict = Depends(require_admin),
):
    """删除指定剧本（仅管理员，可删除任意账号的剧本）。"""
    if script_id not in scripts_module._script_store:
        raise HTTPException(status_code=404, detail="剧本不存在")
    removed = scripts_module._script_store.pop(script_id)
    scripts_module.save_script_to_disk_cache()
    return {
        "message": "剧本已删除",
        "script_id": script_id,
        "title": removed.get("title", ""),
    }


class BulkDeleteRequest(BaseModel):
    title: str = Field(..., description="要删除的剧本标题（精确匹配）")


@router.post("/scripts/bulk-delete-by-title")
async def bulk_delete_by_title(
    request: BulkDeleteRequest,
    admin: dict = Depends(require_admin),
):
    """按标题批量删除所有账号下同名剧本（仅管理员）。"""
    to_delete = [
        sid for sid, s in scripts_module._script_store.items()
        if s.get("title") == request.title
    ]
    deleted = []
    for sid in to_delete:
        removed = scripts_module._script_store.pop(sid, None)
        if removed:
            deleted.append({
                "id": sid,
                "title": removed.get("title", ""),
                "owner": removed.get("owner") or scripts_module.DEFAULT_LEGACY_OWNER,
            })
    if deleted:
        scripts_module.save_script_to_disk_cache()
    return {"deleted": deleted, "count": len(deleted)}
