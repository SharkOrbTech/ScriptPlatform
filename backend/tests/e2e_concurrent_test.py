#!/usr/bin/env python3
"""Concurrent generation test - multiple simultaneous script generation tasks."""
import asyncio
import json
import sys
import os

os.chdir("/Users/hsinli/Documents/script/backend")
sys.path.insert(0, "/Users/hsinli/Documents/script/backend")

# Mock LLM
MOCK_EPISODE = {
    "title": "第1集",
    "summary": "测试摘要",
    "hook": "测试钩子",
    "cliffhanger": "测试悬念",
    "key_conflict": "测试冲突",
    "emotional_arc": "测试弧线",
    "total_duration": 90,
    "shots": [
        {
            "shot_number": 1,
            "shot_type": "特写",
            "camera_movement": "固定",
            "frame_content": "测试画面",
            "dialogue": "测试台词",
            "narration": "测试旁白",
            "duration": 5.0,
            "video_prompt": "测试提示词",
            "hook_type": "hook",
            "hook_detail": "测试钩子详情"
        },
        {
            "shot_number": 2,
            "shot_type": "中景",
            "camera_movement": "推",
            "frame_content": "测试画面2",
            "dialogue": "测试台词2",
            "narration": "",
            "duration": 5.0,
            "video_prompt": "测试提示词2"
        }
    ]
}

MOCK_STORY_PLAN = {
    "title": "并发测试剧本",
    "logline": "测试并发",
    "synopsis": "并发生成测试",
    "theme": "测试",
    "emotional_tone": "测试",
    "core_mystery": {"description": "测试", "reveal_episode": 3, "hook_scene": "测试"},
    "characters": [
        {"name": "角色A", "age": "20", "identity": "测试", "personality": "测试",
         "appearance": "测试", "clothing": "测试", "signature_element": "测试",
         "arc": "测试", "three_view_prompt": "正面：测试。侧面：测试。背面：测试",
         "three_view_prompt": "测试角色提示词"}
    ],
    "scenes": [{"name": "场景A", "description": "测试", "atmosphere": "测试", "scene_prompt": "测试场景提示词"}],
    "props": [{"name": "道具A", "description": "测试", "significance": "测试", "ai_prompt": "测试道具提示词"}],
    "episode_plan": [{"title": "第1集", "key_conflict": "测试", "key_events": ["测试"], "hook": "测试", "cliffhanger": "测试", "emotional_arc": "测试"}] * 3
}

call_count = 0
task_calls = {}  # track calls per task

async def mock_chat(messages, temperature=0.8, max_tokens=8192):
    global call_count
    call_count += 1
    sys_msg = messages[0]["content"] if messages else ""
    user_msg = messages[-1]["content"] if messages else ""
    if "策划" in sys_msg or "策划专家" in sys_msg:
        plan = dict(MOCK_STORY_PLAN)
        # Extract topic from user message to make titles unique
        for line in user_msg.split('\n'):
            if '主题' in line:
                plan["title"] = line.split(':')[-1].strip() or plan["title"]
                break
        return json.dumps(plan, ensure_ascii=False)
    elif "分镜" in sys_msg or "分集" in sys_msg:
        return json.dumps(MOCK_EPISODE, ensure_ascii=False)
    elif "角色" in sys_msg and "设计" in sys_msg:
        return json.dumps({"name": "角色A", "age": "20", "identity": "测试", "personality": "测试",
                           "appearance": "测试", "clothing": "测试", "signature_element": "测试",
                           "three_view_prompt": "正面：测试。侧面：测试。背面：测试",
                           "expression_prompts": {"happy": "微笑"}, "action_prompts": {"walk": "行走"}}, ensure_ascii=False)
    elif "场景" in sys_msg and "设计" in sys_msg:
        return json.dumps({"name": "场景A", "description": "测试", "atmosphere": "测试",
                           "scene_prompt": "测试", "scene_variants": ["白天", "夜晚"]}, ensure_ascii=False)
    else:
        return json.dumps(MOCK_EPISODE, ensure_ascii=False)

import app.core.ai_client as ai_mod
ai_mod.ai_client.chat = mock_chat

from httpx import AsyncClient, ASGITransport
from app.main import app

stats = {"pass": 0, "fail": 0}

def check(desc, condition):
    if condition:
        print(f"  ✓ {desc}")
        stats["pass"] += 1
    else:
        print(f"  ✗ {desc}")
        stats["fail"] += 1

async def generate_one(client, headers, topic, ep_count):
    """Generate a script and return (task_id, status, script_data)."""
    resp = await client.post("/api/scripts/generate", headers=headers, json={
        "topic": topic,
        "genre": "重生",
        "episode_count": ep_count,
        "episode_duration": 90,
    })
    if resp.status_code != 200:
        return None, f"generate_failed_{resp.status_code}", None
    task_id = resp.json().get("task_id")

    # Poll
    for _ in range(120):
        await asyncio.sleep(0.5)
        resp = await client.get(f"/api/scripts/status/{task_id}", headers=headers)
        data = resp.json()
        if data.get("status") in ("completed", "failed"):
            break

    status = data.get("status")
    if status == "completed":
        resp = await client.get(f"/api/scripts/{task_id}", headers=headers)
        return task_id, status, resp.json()
    return task_id, status, None

async def run_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("=" * 50)
        print("  Concurrent Generation Test")
        print("=" * 50)
        print()

        # Login
        resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[1] Login OK")

        # Test 1: 3 concurrent generations
        print("\n=== Test 1: 3 Concurrent Generations ===")
        call_count = 0
        tasks = [
            generate_one(client, headers, "并发测试A", 3),
            generate_one(client, headers, "并发测试B", 3),
            generate_one(client, headers, "并发测试C", 3),
        ]
        results = await asyncio.gather(*tasks)

        all_ok = True
        for i, (tid, status, script) in enumerate(results):
            check(f"Task {i+1} completed", status == "completed")
            if script:
                check(f"Task {i+1} has episodes", len(script.get("episodes", [])) == 3)
                check(f"Task {i+1} has title", bool(script.get("title")))
            else:
                all_ok = False
                print(f"  ✗ Task {i+1} has no script data")
                FAIL += 1
        print(f"  Total LLM calls: {call_count}")

        # Test 2: 5 concurrent generations
        print("\n=== Test 2: 5 Concurrent Generations ===")
        call_count = 0
        tasks = [
            generate_one(client, headers, f"并发测试{i}", 3)
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        completed = sum(1 for _, s, _ in results if s == "completed")
        check(f"All 5 tasks completed", completed == 5)
        for i, (tid, status, script) in enumerate(results):
            if script:
                check(f"Task {i+1} has episodes", len(script.get("episodes", [])) == 3)
        print(f"  Total LLM calls: {call_count}")

        # Test 3: Concurrent generation + list + detail (mixed operations)
        print("\n=== Test 3: Mixed Concurrent Operations ===")
        call_count = 0
        mixed_tasks = [
            generate_one(client, headers, "混合测试生成", 3),
            client.get("/api/scripts/list", headers=headers),
            client.get("/api/health"),
            client.post("/api/scripts/qa", headers=headers, json={
                "session_id": "", "topic": "测试", "genre": "重生", "style": "古风",
                "user_message": "", "history": [],
            }),
        ]
        mixed_results = await asyncio.gather(*mixed_tasks)

        gen_tid, gen_status, gen_script = mixed_results[0]
        check("Generation completed", gen_status == "completed")
        check("List succeeded", mixed_results[1].status_code == 200)
        check("Health succeeded", mixed_results[2].status_code == 200)
        check("QA succeeded", mixed_results[3].status_code == 200)
        print(f"  Total LLM calls: {call_count}")

        # Test 4: Verify all scripts are independent (no data leakage)
        print("\n=== Test 4: Script Independence ===")
        resp = await client.get("/api/scripts/list", headers=headers)
        items = resp.json().get("items", [])
        check("Has multiple scripts", len(items) >= 8)

        # Check each script has its own data
        script_ids = set()
        for item in items:
            resp = await client.get(f"/api/scripts/{item['id']}", headers=headers)
            if resp.status_code == 200:
                script = resp.json()
                check(f"Script {item['id'][:8]} has episodes", len(script.get("episodes", [])) > 0)
                script_ids.add(script.get("id", ""))
        check("All scripts have unique IDs", len(script_ids) == len(items))

        # Test 5: Rapid-fire generation (start tasks without waiting)
        print("\n=== Test 5: Rapid-Fire (10 tasks, no wait) ===")
        task_ids = []
        for i in range(10):
            resp = await client.post("/api/scripts/generate", headers=headers, json={
                "topic": f"快速测试{i}",
                "genre": "重生",
                "episode_count": 3,
                "episode_duration": 90,
            })
            if resp.status_code == 200:
                task_ids.append(resp.json().get("task_id"))
        check("All 10 tasks started", len(task_ids) == 10)

        # Wait for all to complete
        completed_count = 0
        for _ in range(120):
            await asyncio.sleep(0.5)
            statuses = []
            for tid in task_ids:
                resp = await client.get(f"/api/scripts/status/{tid}", headers=headers)
                statuses.append(resp.json().get("status"))
            completed_count = sum(1 for s in statuses if s == "completed")
            if completed_count == 10:
                break
        check("All 10 rapid-fire tasks completed", completed_count == 10)

        # Summary
        print()
        print("=" * 50)
        print(f"  Results: {stats['pass']} passed, {stats['fail']} failed")
        print("=" * 50)
        if stats["fail"] == 0:
            print("  ALL TESTS PASSED ✓")
        else:
            print("  SOME TESTS FAILED ✗")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests())
