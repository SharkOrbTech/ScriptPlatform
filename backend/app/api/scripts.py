"""API routes for script generation and management."""
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, Depends
from pydantic import BaseModel

from app.services.script_generator import script_generator
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
from app.services.copyright_checker import copyright_checker
from app.models.schemas import (
    ScriptRequest, ScriptResponse, Script,
)

router = APIRouter(prefix="/api/scripts", tags=["scripts"])

# Default owner used when migrating legacy scripts without an owner field.
DEFAULT_LEGACY_OWNER = "admin"


def _sanitize_json(obj):
    """Recursively sanitize strings to remove control characters that break JSON."""
    if isinstance(obj, str):
        return _sanitize_json_str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(v) for v in obj]
    return obj


def _sanitize_json_str(s: str) -> str:
    """Sanitize a string by escaping control characters."""
    return s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t').replace('\b', '\\b').replace('\f', '\\f')


SCRIPTS_CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
SCRIPTS_CACHE_FILE = SCRIPTS_CACHE_DIR / "scripts_cache.json"


# In-memory script storage
_script_store: dict[str, dict] = {}


def _repair_foreshadowing(script: dict):
    """Extract foreshadowing index from episode shots for old scripts that lack it."""
    if script.get("foreshadowing"):
        return  # already has the field
    episodes = script.get("episodes", [])
    if not episodes:
        return
    items = []
    seen = set()
    for ep in episodes:
        for shot in ep.get("shots", []):
            if shot.get("hook_type") == "foreshadowing" and shot.get("hook_detail"):
                detail = shot["hook_detail"]
                if detail not in seen:
                    seen.add(detail)
                    items.append({
                        "setup": detail,
                        "episode": ep.get("episode_number", 0),
                        "payoff_episode": 0,
                        "payoff_description": "",
                    })
    if items:
        script["foreshadowing"] = items


def _load_disk_cache():
    try:
        if SCRIPTS_CACHE_FILE.exists():
            data = json.loads(SCRIPTS_CACHE_FILE.read_text(encoding='utf-8'))
            items = data.get("scripts", {})
            repaired = 0
            migrated_owner = 0
            for s in items.values():
                if not s.get("foreshadowing"):
                    _repair_foreshadowing(s)
                    if s.get("foreshadowing"):
                        repaired += 1
                # Migrate legacy scripts without owner field → default to admin
                if not s.get("owner"):
                    s["owner"] = DEFAULT_LEGACY_OWNER
                    migrated_owner += 1
            _script_store.update(items)
            logger.info(
                f"Loaded {len(items)} scripts from disk cache "
                f"(repaired foreshadowing for {repaired}, migrated owner for {migrated_owner})"
            )
    except Exception as e:
        logger.warning(f"Failed to load scripts disk cache: {e}")


def _save_disk_cache():
    try:
        SCRIPTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Convert datetime objects to ISO format strings for JSON serialization
        serializable_store = {}
        for k, v in _script_store.items():
            item = dict(v)
            if 'created_at' in item and hasattr(item['created_at'], 'isoformat'):
                item['created_at'] = item['created_at'].isoformat()
            serializable_store[k] = item
        data = {"scripts": serializable_store, "saved_at": datetime.now().isoformat()}
        SCRIPTS_CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.warning(f"Failed to save scripts disk cache: {e}")


# Expose save function to script_generator module
save_script_to_disk_cache = _save_disk_cache


_load_disk_cache()


def _user_can_access(script: dict, user: dict) -> bool:
    """Check whether the user is allowed to access a given script."""
    if user.get("is_admin"):
        return True
    return script.get("owner") == user.get("username")


def _set_owner_on_completed(task_id: str, owner: str):
    """Called when the generator finishes — ensures the stored script has an owner."""
    if not owner:
        return
    if task_id in _script_store:
        _script_store[task_id]["owner"] = owner
    save_script_to_disk_cache()


# Expose to script_generator
set_owner_on_completed = _set_owner_on_completed

# In-memory Q&A sessions
_qa_sessions: dict[str, list[dict]] = {}


class QARequest(BaseModel):
    session_id: str = ""
    topic: str
    genre: str = "重生"
    style: str = "古风"
    user_message: str
    history: list[dict] = []  # [{role: "assistant"|"user", content: "..."}]


class QARewriteRequest(BaseModel):
    script_id: str
    target: str  # "overall" | "episode" | "character" | "scene" | "prop"
    target_name: str = ""  # e.g. episode number or character name
    instruction: str  # natural language rewrite instruction


@router.post("/generate")
async def generate_script(request: ScriptRequest, user: dict = Depends(get_current_user)):
    """开始生成剧本（异步）"""
    task_id = await script_generator.start_generation(request, owner=user["username"])
    return {"task_id": task_id, "status": "generating"}


@router.get("/status/{task_id}")
async def get_generation_status(task_id: str, user: dict = Depends(get_current_user)):
    """查询剧本生成状态"""
    status = await script_generator.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    # Enforce owner scoping: only the owner (or admin) can poll
    owner = script_generator.get_task_owner(task_id)
    if owner and not user.get("is_admin") and owner != user.get("username"):
        raise HTTPException(status_code=403, detail="无权访问该任务")

    result = status.model_dump()
    if status.script:
        result["script"] = status.script.model_dump()
        result["script"]["owner"] = owner or user["username"]
        _script_store[task_id] = result["script"]
        _save_disk_cache()
    return _sanitize_json(result)


@router.get("/list")
async def list_scripts(user: dict = Depends(get_current_user)):
    """获取当前账号的剧本列表（含生成中）。管理员默认也只看自己的；可通过 /api/admin/scripts 看全部。"""
    items = []
    seen_ids = set()
    username = user["username"]
    is_admin = user.get("is_admin", False)

    # Add stored (completed) scripts belonging to this user
    for s in _script_store.values():
        owner = s.get("owner") or DEFAULT_LEGACY_OWNER
        if owner != username:
            continue
        items.append({
            "id": s.get("id", ""),
            "title": s.get("title", ""),
            "genre": s.get("genre", ""),
            "logline": s.get("logline", ""),
            "episode_count": len(s.get("episodes", [])),
            "character_count": len(s.get("characters", [])),
            "created_at": s.get("created_at", ""),
            "status": "completed",
            "owner": owner,
        })
        seen_ids.add(s.get("id", ""))

    # Add tasks from script generator (includes in-progress and completed)
    for task in script_generator.list_all_tasks():
        if task["id"] in seen_ids:
            continue
        task_owner = script_generator.get_task_owner(task["id"])
        if task_owner and task_owner != username:
            continue
        items.append({
            "id": task["id"],
            "title": task["title"],
            "genre": task["genre"],
            "logline": "",
            "episode_count": 0,
            "character_count": 0,
            "created_at": task["created_at"],
            "status": task["status"],
            "progress": task["progress"],
            "current_phase": task["current_phase"],
            "owner": task_owner or username,
        })
        seen_ids.add(task["id"])

    return {"items": items}


@router.get("/{script_id}")
async def get_script(script_id: str, user: dict = Depends(get_current_user)):
    """获取完整剧本（含生成中和已完成）"""
    if script_id in _script_store:
        script = _script_store[script_id]
        if not _user_can_access(script, user):
            raise HTTPException(status_code=403, detail="无权访问该剧本")
        return script
    # Check generator's completed scripts as fallback
    completed = script_generator.get_completed_script(script_id)
    if completed:
        owner = completed.get("owner") or script_generator.get_task_owner(script_id)
        if owner and not user.get("is_admin") and owner != user.get("username"):
            raise HTTPException(status_code=403, detail="无权访问该剧本")
        return completed
    # Check if it's a generating task
    task = await script_generator.get_task_status(script_id)
    if task:
        task_owner = script_generator.get_task_owner(script_id)
        if task_owner and not user.get("is_admin") and task_owner != user.get("username"):
            raise HTTPException(status_code=403, detail="无权访问该剧本")
        return {
            "id": script_id,
            "status": task.status,
            "progress": task.progress,
            "current_phase": task.current_phase,
            "title": task.current_phase or "正在生成...",
        }
    raise HTTPException(status_code=404, detail="剧本不存在")


@router.delete("/{script_id}")
async def delete_script(script_id: str, user: dict = Depends(get_current_user)):
    """删除剧本（仅剧本所有者或管理员可操作）。"""
    script = _script_store.get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="剧本不存在")
    if not _user_can_access(script, user):
        raise HTTPException(status_code=403, detail="无权删除该剧本")
    del _script_store[script_id]
    _save_disk_cache()
    return {"message": "已删除", "script_id": script_id}


@router.post("/upload-novel")
async def upload_novel(
    file: UploadFile = File(...),
    episode_count: int = Form(default=8),
    genre: str = Form(default="重生"),
    style: str = Form(default="古风"),
    user: dict = Depends(get_current_user),
):
    """上传小说并异步转换为剧本（支持进度轮询）。

    支持格式:
    - .docx: 利用 Word 标题样式（Heading 1/2/3）识别章节边界，准确性最高
    - .txt: 纯文本，通过正则识别 "第X章" 等常见章节标记
    """
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    text = None
    docx_chapters = None  # pre-parsed chapter list from DOCX headings

    # Detect DOCX by ZIP magic bytes (DOCX is a ZIP archive)
    if content[:4] == b'PK\x03\x04':
        try:
            text, docx_chapters = script_generator.parse_docx(content)
            if not text:
                raise HTTPException(status_code=400, detail="无法从DOCX文件中提取文本内容")
            logger.info(f"Parsed DOCX: {len(text)} chars, {len(docx_chapters) if docx_chapters else 0} chapters via headings")
        except Exception as e:
            logger.error(f"DOCX parsing failed: {e}")
            raise HTTPException(status_code=400, detail=f"DOCX解析失败: {str(e)}")
    else:
        # Plain text: try different encodings
        for encoding in ["utf-8", "gbk", "gb2312", "big5", "latin-1"]:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if not text:
            raise HTTPException(status_code=400, detail="无法解码文件，请使用UTF-8或GBK编码")

    # Limit size to 10M characters
    if len(text) > 10000000:
        text = text[:10000000]

    # Start async adaptation with progress feedback
    task_id = await script_generator.start_novel_adaptation(
        text=text,
        episode_count=episode_count,
        genre=genre,
        style=style,
        chapters=docx_chapters,
        owner=user["username"],
    )

    return {"task_id": task_id, "status": "generating"}


@router.post("/{script_id}/copyright-check")
async def check_copyright(script_id: str, user: dict = Depends(get_current_user)):
    """检查剧本版权风险"""
    if script_id not in _script_store:
        raise HTTPException(status_code=404, detail="剧本不存在")

    stored = _script_store[script_id]
    if not _user_can_access(stored, user):
        raise HTTPException(status_code=403, detail="无权操作该剧本")
    # Create a minimal Script object for checking
    script = Script(
        id=script_id,
        title=stored.get("title", ""),
        genre=stored.get("genre", "重生"),
        logline=stored.get("logline", ""),
        synopsis=stored.get("synopsis", ""),
    )
    result = await copyright_checker.check_script(script)
    stored["copyright_risk"] = result.model_dump()
    _script_store[script_id] = stored
    _save_disk_cache()

    return result.model_dump()


@router.post("/qa")
async def script_qa(request: QARequest, user: dict = Depends(get_current_user)):
    """Pre-generation Q&A: LLM asks clarifying questions about the script."""
    from app.core.ai_client import ai_client

    session_id = request.session_id or str(uuid.uuid4())[:8]

    system_prompt = """你是一个专业的短剧编剧顾问。用户想要创作一个短剧剧本，你需要通过选择题帮助他快速明确创作方向。

你需要了解的关键信息（按优先级）：
1. **核心冲突**: 故事的核心矛盾是什么？
2. **主角设定**: 男女主角的身份、性格、关系起点
3. **情感走向**: 虐恋/甜宠/逆袭/先婚后爱等情感主线
4. **关键钩子**: 开头3秒的爆点、每集结尾的悬念风格

输出规则：
- 每轮输出一个简短问题 + 4个选项（可点击选择）
- 选项要具体、有创意、覆盖主流方向
- 用户也可以输入自定义回答
- 最多问3轮，不要过于繁琐
- 用简洁友好的语气

输出格式（严格遵循）：
问题描述
A. 选项1
B. 选项2
C. 选项3
D. 选项4

当信息充分时，用```json包裹总结：
```json
{"core_conflict": "...", "character_setup": "...", "hook_design": "...", "emotional_arc": "..."}
```"""

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]

    # Add context about what user wants
    context_msg = f"""用户想要创作短剧：
- 主题: {request.topic}
- 题材: {request.genre}
- 风格: {request.style}

请根据以上信息开始第一轮提问。"""
    messages.append({"role": "user", "content": context_msg})

    # Add conversation history
    for msg in request.history:
        messages.append(msg)

    # Add current user message
    if request.user_message:
        messages.append({"role": "user", "content": request.user_message})

    try:
        response = await ai_client.chat(messages, temperature=0.7, max_tokens=1000)

        # Check if the response contains a JSON summary (meaning info is sufficient)
        import re
        json_match = re.search(r'```json\s*(\{[\s\S]*\})\s*```', response)
        summary = None
        if json_match:
            try:
                summary = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Parse structured options (A. xxx / B. xxx / C. xxx / D. xxx)
        options = []
        option_pattern = re.findall(r'^([A-D])[.、]\s*(.+)$', response, re.MULTILINE)
        for letter, text in option_pattern:
            options.append({"key": letter, "text": text.strip()})

        # Extract the question (first line before options)
        question = response.split('\n')[0] if response else ""

        return _sanitize_json({
            "session_id": session_id,
            "response": response,
            "question": question,
            "options": options,
            "summary": summary,
            "is_complete": summary is not None,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI调用失败: {str(e)}")


@router.post("/rewrite")
async def rewrite_script_part(request: QARewriteRequest, user: dict = Depends(get_current_user)):
    """Rewrite a part of the script using natural language instruction."""
    from app.core.ai_client import ai_client

    if request.script_id not in _script_store:
        raise HTTPException(status_code=404, detail="剧本不存在")

    stored = _script_store[request.script_id]
    if not _user_can_access(stored, user):
        raise HTTPException(status_code=403, detail="无权改写该剧本")

    # Build context based on target
    context = ""
    current_content = ""

    if request.target == "overall":
        context = "以下是完整剧本的基本信息："
        current_content = json.dumps({
            "title": stored.get("title", ""),
            "genre": stored.get("genre", ""),
            "logline": stored.get("logline", ""),
            "synopsis": stored.get("synopsis", ""),
            "theme": stored.get("theme", ""),
            "emotional_tone": stored.get("emotional_tone", ""),
        }, ensure_ascii=False, indent=2)
    elif request.target == "episode":
        episodes = stored.get("episodes", [])
        ep_num = int(request.target_name) if request.target_name.isdigit() else 1
        ep = next((e for e in episodes if e.get("episode_number") == ep_num), None)
        if ep:
            context = f"以下是第{ep_num}集的内容："
            current_content = json.dumps(ep, ensure_ascii=False, indent=2)[:6000]
    elif request.target == "character":
        characters = stored.get("characters", [])
        char = next((c for c in characters if c.get("name") == request.target_name), None)
        if char:
            context = f"以下是角色「{request.target_name}」的设定："
            current_content = json.dumps(char, ensure_ascii=False, indent=2)
    elif request.target == "scene":
        scenes = stored.get("scenes", [])
        scene = next((s for s in scenes if s.get("name") == request.target_name), None)
        if scene:
            context = f"以下是场景「{request.target_name}」的设定："
            current_content = json.dumps(scene, ensure_ascii=False, indent=2)
    elif request.target == "prop":
        props = stored.get("props", [])
        prop = next((p for p in props if p.get("name") == request.target_name), None)
        if prop:
            context = f"以下是道具「{request.target_name}」的设定："
            current_content = json.dumps(prop, ensure_ascii=False, indent=2)

    if not current_content:
        raise HTTPException(status_code=400, detail="未找到指定内容")

    system_prompt = """你是一个专业的短剧编剧AI助手。用户希望对剧本的某个部分进行修改。
请根据用户的修改要求，输出修改后的完整内容。

规则：
1. 保持JSON格式输出，与原格式一致
2. 只修改用户要求改动的部分，其他内容保持不变
3. 修改后的内容要与整体剧本风格一致
4. 用```json包裹输出"""

    prompt = f"""{context}

当前内容：
```json
{current_content}
```

用户的修改要求：{request.instruction}

请输出修改后的完整JSON内容："""

    try:
        response = await ai_client.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ], temperature=0.7, max_tokens=4096)

        # Extract JSON from response
        import re
        result = None
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', response)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                # Try sanitizing control characters
                try:
                    result = json.loads(_sanitize_json_str(json_match.group(1)))
                except (json.JSONDecodeError, Exception):
                    pass

        if not result:
            # Try brace matching
            start = response.find('{')
            if start != -1:
                depth = 0
                for i in range(start, len(response)):
                    if response[i] == '{':
                        depth += 1
                    elif response[i] == '}':
                        depth -= 1
                        if depth == 0:
                            try:
                                result = json.loads(response[start:i + 1])
                            except json.JSONDecodeError:
                                try:
                                    result = json.loads(_sanitize_json_str(response[start:i + 1]))
                                except (json.JSONDecodeError, Exception):
                                    pass
                            break

        if not result:
            raise HTTPException(status_code=500, detail="AI未能生成有效内容")

        # Apply the rewrite back to the stored script
        if request.target == "overall":
            for key in ["title", "logline", "synopsis", "theme", "emotional_tone"]:
                if key in result:
                    stored[key] = result[key]
        elif request.target == "episode":
            episodes = stored.get("episodes", [])
            ep_num = int(request.target_name) if request.target_name.isdigit() else 1
            for i, ep in enumerate(episodes):
                if ep.get("episode_number") == ep_num:
                    episodes[i] = result
                    break
        elif request.target == "character":
            characters = stored.get("characters", [])
            for i, c in enumerate(characters):
                if c.get("name") == request.target_name:
                    characters[i] = result
                    break
        elif request.target == "scene":
            scenes = stored.get("scenes", [])
            for i, s in enumerate(scenes):
                if s.get("name") == request.target_name:
                    scenes[i] = result
                    break
        elif request.target == "prop":
            props = stored.get("props", [])
            for i, p in enumerate(props):
                if p.get("name") == request.target_name:
                    props[i] = result
                    break

        _script_store[request.script_id] = stored
        _save_disk_cache()

        return _sanitize_json({"success": True, "result": result})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"改写失败: {str(e)}")
