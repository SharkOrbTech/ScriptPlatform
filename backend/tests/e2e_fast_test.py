#!/usr/bin/env python3
"""Fast E2E test with mocked LLM - no real API calls."""
import asyncio
import json
import sys
import os

# Patch ai_client BEFORE importing app
os.chdir("/Users/hsinli/Documents/script/backend")
sys.path.insert(0, "/Users/hsinli/Documents/script/backend")

# Create mock ai_client module
MOCK_EPISODE = {
    "title": "第1集",
    "summary": "主角重生归来，发现前世仇人已身居高位",
    "hook": "女主睁开眼，发现自己回到了三年前",
    "cliffhanger": "门外传来脚步声，一个熟悉的身影出现",
    "key_conflict": "重生后的女主面对前世的仇人",
    "emotional_arc": "震惊→愤怒→决心",
    "total_duration": 90,
    "shots": [
        {
            "shot_number": 1,
            "shot_type": "特写",
            "camera_movement": "固定",
            "frame_content": "女主睁开双眼，眼中充满震惊和不甘",
            "dialogue": "不...这不可能...",
            "narration": "她不知道，这个瞬间将彻底改变她的命运",
            "sound_effects": "心跳声",
            "duration": 3.0,
            "ai_prompt": "清晨的卧室里，阳光透过纱帘洒在床铺上，一个年轻女子猛然睁开双眼，瞳孔中倒映着难以置信的光芒",
            "lighting": "自然光",
            "emotion": "震惊",
            "hook_type": "hook",
            "hook_detail": "重生瞬间，制造强烈悬念"
        },
        {
            "shot_number": 2,
            "shot_type": "中景",
            "camera_movement": "推",
            "frame_content": "女主坐起身，看着镜中年轻的自己",
            "dialogue": "三年前...我回来了？",
            "narration": "三年前，她还是苏家最受宠的千金。直到那场阴谋，夺走了她的一切",
            "sound_effects": "",
            "duration": 4.0,
            "ai_prompt": "卧室梳妆台前，年轻女子坐在床边，镜中映出她惊讶的面容",
            "lighting": "侧光",
            "emotion": "不可思议"
        }
    ]
}

MOCK_STORY_PLAN = {
    "title": "重生千金的复仇之路",
    "logline": "重生千金逆袭复仇",
    "synopsis": "女主重生回到三年前，利用前世记忆步步为营",
    "theme": "复仇与救赎",
    "emotional_tone": "紧张刺激",
    "core_mystery": {
        "description": "女主前世被害的真相",
        "reveal_episode": 5,
        "hook_scene": "女主重生瞬间"
    },
    "characters": [
        {
            "name": "苏婉儿",
            "age": "22",
            "identity": "苏家千金",
            "personality": "外柔内刚，心思缜密",
            "appearance": "长发披肩，眉目如画",
            "clothing": "素雅长裙",
            "signature_element": "手腕上的玉镯",
            "arc": "从天真善良到心狠手辣再到内心释然",
            "three_view_prompt": "正面：长发披肩的年轻女子，面容清秀。侧面：轮廓柔和，气质优雅。背面：长发如瀑，身姿挺拔",
            "ai_prompt": "一个22岁的东方古典美人，长发披肩，眉目如画，身穿素雅长裙，手腕佩戴翠绿玉镯"
        },
        {
            "name": "顾北辰",
            "age": "28",
            "identity": "顾家总裁",
            "personality": "表面冷漠，内心深情",
            "appearance": "高大英俊，气质冷峻",
            "clothing": "黑色西装",
            "signature_element": "左手无名指的戒指",
            "arc": "从冷漠旁观到全力守护",
            "three_view_prompt": "正面：高大英俊的男子，面容冷峻。侧面：棱角分明，气场强大。背面：身姿挺拔，西装笔挺",
            "ai_prompt": "一个28岁的英俊男子，身穿黑色西装，气质冷峻，左手无名指佩戴银色戒指"
        }
    ],
    "scenes": [
        {"name": "苏家大宅", "description": "古典中式大宅院", "atmosphere": "压抑", "scene_prompt": "古典中式大宅院，雕梁画栋，庭院深深"},
        {"name": "顾氏集团", "description": "现代摩天大楼", "atmosphere": "冷峻", "scene_prompt": "现代玻璃幕墙摩天大楼，顶层办公室"}
    ],
    "props": [
        {"name": "玉镯", "description": "女主母亲遗物", "significance": "身份象征", "ai_prompt": "翠绿色翡翠手镯，通透温润"},
        {"name": "遗书", "description": "前世留下的证据", "significance": "复仇关键", "ai_prompt": "泛黄的信纸上写满娟秀字迹"}
    ],
    "episode_plan": [
        {"title": "重生归来", "key_conflict": "发现前世仇人", "key_events": ["重生", "发现真相"], "hook": "重生瞬间", "cliffhanger": "仇人出现", "emotional_arc": "震惊→决心"}
    ] * 3
}

MOCK_CHAR_DESIGN = {
    "name": "苏婉儿",
    "age": "22",
    "identity": "苏家千金",
    "personality": "外柔内刚",
    "appearance": "长发披肩，眉目如画",
    "clothing": "素雅长裙",
    "signature_element": "玉镯",
    "three_view_prompt": "正面：长发女子。侧面：轮廓柔和。背面：身姿优雅",
    "expression_prompts": {"happy": "微笑", "angry": "怒目", "sad": "泪眼"},
    "action_prompts": {"walk": "优雅行走", "fight": "利落出招"}
}

MOCK_SCENE_DESIGN = {
    "name": "苏家大宅",
    "description": "古典中式大宅院",
    "atmosphere": "压抑中带着华丽",
    "scene_prompt": "古典中式大宅院，雕梁画栋，红灯笼高挂",
    "scene_variants": ["白天", "夜晚", "雨天"]
}

MOCK_NOVEL_OVERVIEW = {
    "title": "测试小说",
    "main_characters": ["主角", "反派"],
    "core_conflict": "正邪对抗",
    "synopsis": "一个关于复仇的故事",
    "setting": "古代",
    "time_period": "架空",
    "key_relationships": "主角与反派的宿敌关系"
}

call_count = 0

async def mock_chat(messages, temperature=0.8, max_tokens=8192):
    global call_count
    call_count += 1
    # Determine what's being asked based on system prompt
    sys_msg = messages[0]["content"] if messages else ""
    user_msg = messages[-1]["content"] if messages else ""

    if "策划" in sys_msg or "策划专家" in sys_msg:
        return json.dumps(MOCK_STORY_PLAN, ensure_ascii=False)
    elif "分镜" in sys_msg or "分集" in sys_msg:
        return json.dumps(MOCK_EPISODE, ensure_ascii=False)
    elif "角色" in sys_msg and "设计" in sys_msg:
        return json.dumps(MOCK_CHAR_DESIGN, ensure_ascii=False)
    elif "场景" in sys_msg and "设计" in sys_msg:
        return json.dumps(MOCK_SCENE_DESIGN, ensure_ascii=False)
    elif "小说" in sys_msg and ("分析" in sys_msg or "提取" in sys_msg):
        return json.dumps(MOCK_NOVEL_OVERVIEW, ensure_ascii=False)
    elif "章节" in user_msg or "摘要" in user_msg:
        return json.dumps([
            {"chapter": 1, "summary": "故事开端，主角登场", "hooks": [
                {"type": "hook", "description": "女主重生睁眼瞬间", "position": "start"},
                {"type": "cliffhanger", "description": "门外传来熟悉脚步声", "position": "end"}
            ]},
            {"chapter": 2, "summary": "冲突初现，矛盾升级", "hooks": [
                {"type": "foreshadowing", "description": "玉镯发出微光", "position": "middle"}
            ]},
            {"chapter": 3, "summary": "危机爆发，命运转折", "hooks": [
                {"type": "turning_point", "description": "发现前世真相", "position": "end"},
                {"type": "emotional_peak", "description": "女主崩溃大哭", "position": "middle"}
            ]},
        ], ensure_ascii=False)
    elif "编剧顾问" in sys_msg or "问答" in sys_msg:
        return "你想写什么故事？\nA. 重生复仇\nB. 甜宠恋爱\nC. 都市逆袭\nD. 古装宫斗"
    elif "改写" in sys_msg or "修改" in sys_msg:
        return json.dumps(MOCK_STORY_PLAN, ensure_ascii=False)
    else:
        return json.dumps(MOCK_EPISODE, ensure_ascii=False)


async def mock_chat_stream(messages, temperature=0.8, max_tokens=8192):
    result = await mock_chat(messages, temperature, max_tokens)
    yield result


# Patch the ai_client module
import importlib
import app.core.ai_client as ai_mod
original_chat = ai_mod.ai_client.chat
ai_mod.ai_client.chat = mock_chat

from httpx import AsyncClient, ASGITransport
from app.main import app

PASS = 0
FAIL = 0

def check(desc, condition):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {desc}")
        PASS += 1
    else:
        print(f"  ✗ {desc}")
        FAIL += 1

async def run_tests():
    global call_count
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("=" * 50)
        print("  Fast E2E Test (Mocked LLM)")
        print("=" * 50)
        print()

        # Step 1: Login
        print("=== Step 1: Login ===")
        resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        check("Login succeeds", resp.status_code == 200)
        data = resp.json()
        check("Returns token", "token" in data)
        token = data["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print()

        # Step 2: Auth/me
        print("=== Step 2: Auth/me ===")
        resp = await client.get("/api/auth/me", headers=headers)
        check("Returns user info", resp.status_code == 200)
        check("Username is admin", resp.json().get("username") == "admin")
        print()

        # Step 3: Health
        print("=== Step 3: Health ===")
        resp = await client.get("/api/health")
        check("Health OK", resp.json().get("status") == "ok")
        print()

        # Step 4: Config
        print("=== Step 4: Config ===")
        resp = await client.get("/api/config", headers=headers)
        check("Config loaded", resp.status_code == 200)
        check("Has genres", len(resp.json().get("genres", [])) > 0)
        print()

        # Step 5: Generate script
        print("=== Step 5: Generate script (mocked LLM) ===")
        call_count = 0
        resp = await client.post("/api/scripts/generate", headers=headers, json={
            "topic": "重生千金的复仇之路",
            "genre": "重生",
            "episode_count": 3,
            "episode_duration": 90,
            "target_audience": "18-35岁女性",
            "style": "古风",
        })
        check("Generate returns task_id", resp.status_code == 200)
        task_id = resp.json().get("task_id")
        check("Task ID exists", bool(task_id))
        print(f"  → task_id: {task_id}")
        print()

        # Step 6: Poll status until done
        print("=== Step 6: Poll generation status ===")
        import asyncio as aio
        for i in range(60):
            await aio.sleep(0.5)
            resp = await client.get(f"/api/scripts/status/{task_id}", headers=headers)
            status_data = resp.json()
            status = status_data.get("status")
            if status in ("completed", "failed"):
                break

        check("Generation completed", status == "completed")
        check("Progress is 100%", status_data.get("progress") == 100.0)
        check("Has script data", status_data.get("script") is not None)
        print(f"  → LLM calls: {call_count}")
        print()

        # Step 7: Script detail
        print("=== Step 7: Script detail ===")
        resp = await client.get(f"/api/scripts/{task_id}", headers=headers)
        check("Script exists", resp.status_code == 200)
        script = resp.json()
        check("Has title", bool(script.get("title")))
        check("Has episodes", len(script.get("episodes", [])) == 3)
        check("Has characters", len(script.get("characters", [])) > 0)
        check("Has scenes", len(script.get("scenes", [])) > 0)
        check("Has props", len(script.get("props", [])) > 0)

        # Check shot structure
        ep1 = script["episodes"][0]
        check("Episode 1 has shots", len(ep1.get("shots", [])) > 0)
        if ep1.get("shots"):
            shot = ep1["shots"][0]
            check("Shot has shot_type", bool(shot.get("shot_type")))
            check("Shot has ai_prompt", bool(shot.get("ai_prompt")))
            check("Shot has hook_type", bool(shot.get("hook_type")))
            check("Shot has hook_detail", bool(shot.get("hook_detail")))
            check("Shot has narration", bool(shot.get("narration")))
        print()

        # Step 8: List scripts
        print("=== Step 8: List scripts ===")
        resp = await client.get("/api/scripts/list", headers=headers)
        check("List succeeds", resp.status_code == 200)
        check("Has items", len(resp.json().get("items", [])) > 0)
        print()

        # Step 9: Q&A
        print("=== Step 9: Script Q&A ===")
        resp = await client.post("/api/scripts/qa", headers=headers, json={
            "session_id": "",
            "topic": "重生千金",
            "genre": "重生",
            "style": "古风",
            "user_message": "",
            "history": [],
        })
        check("QA responds", resp.status_code == 200)
        check("Has response", bool(resp.json().get("response")))
        check("Has session_id", bool(resp.json().get("session_id")))
        print()

        # Step 10: Account management
        print("=== Step 10: Account management ===")
        resp = await client.get("/api/auth/accounts", headers=headers)
        check("Accounts list", resp.status_code == 200)

        resp = await client.post("/api/auth/create-account", headers=headers, json={
            "username": f"test_fast_{os.getpid()}",
            "password": "test123456",
        })
        check("Create account", resp.status_code == 200)

        resp = await client.post("/api/auth/login", json={
            "username": f"test_fast_{os.getpid()}",
            "password": "test123456",
        })
        check("New user login", resp.status_code == 200)
        new_token = resp.json().get("token")

        resp = await client.get("/api/auth/accounts", headers={"Authorization": f"Bearer {new_token}"})
        check("Non-admin gets 403", resp.status_code == 403)

        resp = await client.delete(f"/api/auth/accounts/test_fast_{os.getpid()}", headers=headers)
        check("Delete account", resp.status_code == 200)
        print()

        # Step 11: Novel upload (mocked)
        print("=== Step 11: Novel upload ===")
        call_count = 0
        import io
        novel_content = "第一章 重生\n\n苏婉儿睁开了眼睛。\n\n第二章 醒来\n\n她发现自己回到了三年前。"
        files = {"file": ("test.txt", novel_content.encode(), "text/plain")}
        resp = await client.post("/api/scripts/upload-novel", headers=headers, files=files, data={
            "episode_count": "3",
            "genre": "重生",
            "style": "古风",
        })
        check("Novel upload succeeds", resp.status_code == 200)
        check("Returns result", resp.json().get("result") is not None or resp.json().get("task_id"))
        print(f"  → LLM calls for novel: {call_count}")
        print()

        # Step 12: Change password
        print("=== Step 12: Change password ===")
        resp = await client.post("/api/auth/change-password", headers=headers, json={
            "old_password": "admin123",
            "new_password": "admin123",
        })
        check("Change password", resp.status_code == 200)
        print()

        # Step 13: Topic config
        print("=== Step 13: Topic config ===")
        resp = await client.get("/api/config/topic/重生千金", headers=headers)
        check("Topic config", resp.status_code == 200)
        check("Has genres", len(resp.json().get("genres", [])) > 0)
        print()

        # Step 14: Verify episode_count limit allows 200
        print("=== Step 14: Episode count limit ===")
        resp = await client.post("/api/scripts/generate", headers=headers, json={
            "topic": "测试200集",
            "genre": "重生",
            "episode_count": 200,
            "episode_duration": 90,
        })
        check("200 episodes accepted", resp.status_code == 200)
        # Clean up - don't actually wait for 200 episodes
        print()

        # Summary
        print("=" * 50)
        print(f"  Results: {PASS} passed, {FAIL} failed")
        print("=" * 50)

        if FAIL == 0:
            print("  ALL TESTS PASSED ✓")
        else:
            print("  SOME TESTS FAILED ✗")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_tests())
