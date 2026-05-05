"""API routes for script generation and management."""
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from pydantic import BaseModel

from app.services.script_generator import script_generator

logger = logging.getLogger(__name__)
from app.services.copyright_checker import copyright_checker
from app.models.schemas import (
    ScriptRequest, ScriptResponse, Script,
)

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


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


def _load_disk_cache():
    try:
        if SCRIPTS_CACHE_FILE.exists():
            data = json.loads(SCRIPTS_CACHE_FILE.read_text(encoding='utf-8'))
            items = data.get("scripts", {})
            _script_store.update(items)
            logger.info(f"Loaded {len(items)} scripts from disk cache")
    except Exception as e:
        logger.warning(f"Failed to load scripts disk cache: {e}")


def _save_disk_cache():
    try:
        SCRIPTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {"scripts": _script_store, "saved_at": datetime.now().isoformat()}
        SCRIPTS_CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.warning(f"Failed to save scripts disk cache: {e}")


_load_disk_cache()

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
async def generate_script(request: ScriptRequest):
    """开始生成剧本（异步）"""
    task_id = await script_generator.start_generation(request)
    return {"task_id": task_id, "status": "generating"}


@router.get("/status/{task_id}")
async def get_generation_status(task_id: str):
    """查询剧本生成状态"""
    status = await script_generator.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = status.model_dump()
    if status.script:
        # Get extended data if available
        extended = getattr(status, '_extended_data', None)
        if extended:
            result["script"] = extended
        else:
            result["script"] = status.script.model_dump()
        _script_store[task_id] = result["script"]
        _save_disk_cache()
    return _sanitize_json(result)


@router.get("/list")
async def list_scripts():
    """获取所有剧本列表（含生成中）"""
    items = []
    seen_ids = set()

    # Add stored (completed via polling) scripts
    for s in _script_store.values():
        items.append({
            "id": s.get("id", ""),
            "title": s.get("title", ""),
            "genre": s.get("genre", ""),
            "logline": s.get("logline", ""),
            "episode_count": len(s.get("episodes", [])),
            "character_count": len(s.get("characters", [])),
            "created_at": s.get("created_at", ""),
            "status": "completed",
        })
        seen_ids.add(s.get("id", ""))

    # Add tasks from script generator (includes in-progress and completed)
    for task in script_generator.list_all_tasks():
        if task["id"] not in seen_ids:
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
            })
            seen_ids.add(task["id"])

    return {"items": items}


@router.get("/{script_id}")
async def get_script(script_id: str):
    """获取完整剧本（含生成中和已完成）"""
    if script_id in _script_store:
        return _script_store[script_id]
    # Check generator's completed scripts as fallback
    completed = script_generator.get_completed_script(script_id)
    if completed:
        return completed
    # Check if it's a generating task
    task = await script_generator.get_task_status(script_id)
    if task:
        return {
            "id": script_id,
            "status": task.status,
            "progress": task.progress,
            "current_phase": task.current_phase,
            "title": task.current_phase or "正在生成...",
        }
    raise HTTPException(status_code=404, detail="剧本不存在")


@router.post("/upload-novel")
async def upload_novel(
    file: UploadFile = File(...),
    episode_count: int = Form(default=8),
    genre: str = Form(default="重生"),
    style: str = Form(default="古风"),
):
    """上传小说并转换为剧本"""
    content = await file.read()

    # Try different encodings
    text = None
    for encoding in ["utf-8", "gbk", "gb2312", "big5", "latin-1"]:
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if not text:
        raise HTTPException(status_code=400, detail="无法解码文件，请使用UTF-8或GBK编码")

    # Limit size to 10M characters (supports very long novels)
    if len(text) > 10000000:
        text = text[:10000000]

    result = await script_generator.adapt_novel(
        novel_content=text,
        episode_count=episode_count,
        genre=genre,
        style=style,
    )

    # Store the result
    script_id = str(uuid.uuid4())[:8]
    if result:
        result["id"] = script_id
        result["created_at"] = datetime.now().isoformat()
        _script_store[script_id] = result
        _save_disk_cache()

    return {"task_id": script_id, "result": result}


@router.post("/{script_id}/copyright-check")
async def check_copyright(script_id: str):
    """检查剧本版权风险"""
    if script_id not in _script_store:
        raise HTTPException(status_code=404, detail="剧本不存在")

    stored = _script_store[script_id]
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
async def script_qa(request: QARequest):
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
async def rewrite_script_part(request: QARewriteRequest):
    """Rewrite a part of the script using natural language instruction."""
    from app.core.ai_client import ai_client

    if request.script_id not in _script_store:
        raise HTTPException(status_code=404, detail="剧本不存在")

    stored = _script_store[request.script_id]

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
