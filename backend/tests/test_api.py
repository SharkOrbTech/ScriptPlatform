"""End-to-end API tests for the Script Workshop backend."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.schemas import ScriptRequest, ScriptGenre, TrendItem, TrendSource


# ============================================================
# Health & Config Tests
# ============================================================

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_get_config(client):
    mock_analysis = {
        "dynamic_genres": [{"name": "重生", "count": 10}, {"name": "复仇", "count": 5}],
        "dynamic_styles": [{"name": "古风", "count": 3}],
        "total_count": 10,
    }
    with patch("app.services.trend_service.trend_service.get_trend_analysis", new_callable=AsyncMock, return_value=mock_analysis):
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "genres" in data
        assert "styles" in data
        assert isinstance(data["genres"], list)
        assert len(data["genres"]) > 0
        for g in data["genres"]:
            assert "value" in g
            assert "label" in g


# ============================================================
# Trends Tests
# ============================================================

@pytest.mark.asyncio
async def test_get_trends_empty(client):
    """Test trends endpoint returns structure even with no data."""
    with patch("app.services.trend_service.trend_service.get_all_trends", new_callable=AsyncMock, return_value=[]):
        resp = await client.get("/api/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_get_trends_with_data(client):
    """Test trends endpoint with mock data."""
    mock_trends = [
        TrendItem(
            id="test1",
            title="重生千金复仇记",
            source=TrendSource.HONGGUO,
            category="重生",
            heat=9500,
            description="重生千金强势归来",
            tags=["重生", "复仇", "千金"],
        ),
        TrendItem(
            id="test2",
            title="战神归来",
            source=TrendSource.TOMATO,
            category="男频",
            heat=8800,
            description="战神回归都市",
            tags=["战神", "逆袭", "都市"],
        ),
    ]
    with patch("app.services.trend_service.trend_service.get_all_trends", new_callable=AsyncMock, return_value=mock_trends):
        resp = await client.get("/api/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["title"] == "重生千金复仇记"


@pytest.mark.asyncio
async def test_trend_analysis(client):
    """Test trend analysis endpoint."""
    mock_trends = [
        TrendItem(
            id="test1",
            title="重生千金",
            source=TrendSource.HONGGUO,
            category="重生",
            heat=9500,
            tags=["重生", "复仇"],
        ),
    ]
    with patch("app.services.trend_service.trend_service.get_all_trends", new_callable=AsyncMock, return_value=mock_trends):
        resp = await client.get("/api/trends/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "hot_keywords" in data
        assert "dynamic_genres" in data


@pytest.mark.asyncio
async def test_trends_fetch_status(client):
    resp = await client.get("/api/trends/fetch-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "fetching" in data


# ============================================================
# Script Generation Tests
# ============================================================

@pytest.mark.asyncio
async def test_generate_script(client):
    """Test script generation starts successfully."""
    with patch("app.api.scripts.script_generator.start_generation", new_callable=AsyncMock, return_value="test-task-123"):
        resp = await client.post("/api/scripts/generate", json={
            "topic": "重生千金的复仇之路",
            "genre": "重生",
            "episode_count": 3,
            "episode_duration": 90,
            "target_audience": "18-35岁女性",
            "style": "古风",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "generating"


@pytest.mark.asyncio
async def test_script_status_not_found(client):
    resp = await client.get("/api/scripts/status/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_script_list_empty(client):
    resp = await client.get("/api/scripts/list")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_script_not_found(client):
    resp = await client.get("/api/scripts/nonexistent")
    assert resp.status_code == 404


# ============================================================
# Script Q&A Tests
# ============================================================

@pytest.mark.asyncio
async def test_script_qa(client):
    """Test Q&A endpoint with mocked AI response."""
    mock_response = "好的，让我了解一下你的故事核心。你希望这个重生故事的核心冲突是什么？是复仇、逆袭还是救赎？"

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/qa", json={
            "topic": "重生千金",
            "genre": "重生",
            "style": "古风",
            "user_message": "",
            "history": [],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "response" in data
        assert data["is_complete"] == False


@pytest.mark.asyncio
async def test_script_qa_with_summary(client):
    """Test Q&A endpoint when AI provides a summary."""
    mock_response = """很好，信息已经足够了！

```json
{
  "core_conflict": "女主重生后发现前世被害真相，步步为营复仇",
  "character_setup": "女主：重生千金，外表温柔内心坚韧；男主：冷面总裁，暗中保护女主",
  "hook_design": "第一集开头：女主在婚礼上被毒杀，睁眼回到三年前",
  "emotional_arc": "虐恋到甜宠，复仇到救赎"
}
```"""

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/qa", json={
            "topic": "重生千金",
            "genre": "重生",
            "style": "古风",
            "user_message": "我想要复仇类型的",
            "history": [{"role": "assistant", "content": "你想写什么？"}, {"role": "user", "content": "重生千金"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_complete"] == True
        assert data["summary"] is not None
        assert "core_conflict" in data["summary"]


# ============================================================
# Script Rewrite Tests
# ============================================================

@pytest.mark.asyncio
async def test_rewrite_not_found(client):
    resp = await client.post("/api/scripts/rewrite", json={
        "script_id": "nonexistent",
        "target": "overall",
        "instruction": "改成更虐的",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rewrite_overall(client):
    """Test rewriting overall script info."""
    # First, add a script to the store
    from app.api.scripts import _script_store
    _script_store["test-script"] = {
        "id": "test-script",
        "title": "原剧本",
        "genre": "重生",
        "logline": "原简介",
        "synopsis": "原梗概",
        "episodes": [],
        "characters": [],
        "scenes": [],
        "props": [],
    }

    mock_response = '```json\n{"title": "新剧本名", "logline": "新简介", "synopsis": "新梗概", "theme": "复仇"}\n```'

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/rewrite", json={
            "script_id": "test-script",
            "target": "overall",
            "instruction": "把标题改成更有悬念感的",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert data["result"]["title"] == "新剧本名"

    # Cleanup
    del _script_store["test-script"]


# ============================================================
# Copyright Check Tests
# ============================================================

@pytest.mark.asyncio
async def test_copyright_check_not_found(client):
    resp = await client.post("/api/scripts/nonexistent/copyright-check")
    assert resp.status_code == 404


# ============================================================
# Upload Novel Tests
# ============================================================

@pytest.mark.asyncio
async def test_upload_novel_with_mock(client):
    """Test upload novel endpoint with mocked AI."""
    mock_result = {
        "title": "改编剧本",
        "genre": "重生",
        "episodes": [{"episode_number": 1, "title": "第一集", "summary": "测试", "shots": []}],
        "characters": [],
    }
    with patch("app.api.scripts.script_generator.adapt_novel", new_callable=AsyncMock, return_value=mock_result):
        resp = await client.post("/api/scripts/upload-novel", files={
            "file": ("test.txt", "第一章\n这是测试小说内容。" * 50, "text/plain"),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data


# ============================================================
# Trend Refresh Tests
# ============================================================

@pytest.mark.asyncio
async def test_refresh_trends(client):
    resp = await client.post("/api/trends/refresh")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"


# ============================================================
# Topic-Specific Config Tests
# ============================================================

@pytest.mark.asyncio
async def test_get_config_for_topic(client):
    """Test topic-specific genre/style config endpoint."""
    mock_result = {
        "genres": [
            {"value": "重生", "label": "重生", "count": 15},
            {"value": "复仇", "label": "复仇", "count": 10},
        ],
        "styles": ["古风", "现代都市", "赛博朋克"],
    }
    with patch("app.services.trend_service.trend_service.get_genres_for_topic", new_callable=AsyncMock, return_value=mock_result):
        resp = await client.get("/api/config/topic/重生千金")
        assert resp.status_code == 200
        data = resp.json()
        assert "genres" in data
        assert "styles" in data
        assert len(data["genres"]) == 2
        assert data["genres"][0]["value"] == "重生"


@pytest.mark.asyncio
async def test_get_config_for_topic_empty(client):
    """Test topic config with no matching trends."""
    mock_result = {"genres": [], "styles": []}
    with patch("app.services.trend_service.trend_service.get_genres_for_topic", new_callable=AsyncMock, return_value=mock_result):
        resp = await client.get("/api/config/topic/xyznonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert "genres" in data
        assert "styles" in data


# ============================================================
# Q&A with Structured Choices Tests
# ============================================================

@pytest.mark.asyncio
async def test_script_qa_with_options(client):
    """Test Q&A endpoint returns parsed A/B/C/D options."""
    mock_response = """你希望这个重生故事的核心冲突是什么？
A. 复仇：女主重生后向害死她的人复仇
B. 逆袭：女主重生后逆袭成为商业女王
C. 救赎：女主重生后试图弥补前世遗憾
D. 守护：女主重生后守护前世失去的亲人"""

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/qa", json={
            "topic": "重生千金",
            "genre": "重生",
            "style": "古风",
            "user_message": "",
            "history": [],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "options" in data
        assert len(data["options"]) == 4
        assert data["options"][0]["key"] == "A"
        assert "复仇" in data["options"][0]["text"]
        assert data["options"][1]["key"] == "B"
        assert data["options"][2]["key"] == "C"
        assert data["options"][3]["key"] == "D"


@pytest.mark.asyncio
async def test_script_qa_no_options(client):
    """Test Q&A when AI doesn't return structured options."""
    mock_response = "请告诉我更多关于你想要的故事类型。"

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/qa", json={
            "topic": "测试",
            "genre": "重生",
            "style": "古风",
            "user_message": "",
            "history": [],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["options"] == []
        assert data["is_complete"] == False


# ============================================================
# Rewrite Different Targets Tests
# ============================================================

@pytest.mark.asyncio
async def test_rewrite_episode(client):
    """Test rewriting a specific episode."""
    from app.api.scripts import _script_store
    _script_store["test-ep-rewrite"] = {
        "id": "test-ep-rewrite",
        "title": "测试剧本",
        "genre": "重生",
        "episodes": [
            {"episode_number": 1, "title": "第一集", "summary": "原概要", "shots": []},
            {"episode_number": 2, "title": "第二集", "summary": "原概要", "shots": []},
        ],
        "characters": [],
        "scenes": [],
        "props": [],
    }

    mock_response = '```json\n{"episode_number": 1, "title": "新第一集", "summary": "新概要", "shots": []}\n```'

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/rewrite", json={
            "script_id": "test-ep-rewrite",
            "target": "episode",
            "target_name": "1",
            "instruction": "让第一集更紧张刺激",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert data["result"]["title"] == "新第一集"

    del _script_store["test-ep-rewrite"]


@pytest.mark.asyncio
async def test_rewrite_character(client):
    """Test rewriting a character."""
    from app.api.scripts import _script_store
    _script_store["test-char-rewrite"] = {
        "id": "test-char-rewrite",
        "title": "测试剧本",
        "genre": "重生",
        "episodes": [],
        "characters": [
            {"name": "女主", "personality": "温柔", "appearance": "长发"},
        ],
        "scenes": [],
        "props": [],
    }

    mock_response = '```json\n{"name": "女主", "personality": "坚韧果敢", "appearance": "短发干练"}\n```'

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/rewrite", json={
            "script_id": "test-char-rewrite",
            "target": "character",
            "target_name": "女主",
            "instruction": "让女主性格更强势",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert data["result"]["personality"] == "坚韧果敢"

    del _script_store["test-char-rewrite"]


@pytest.mark.asyncio
async def test_rewrite_scene(client):
    """Test rewriting a scene."""
    from app.api.scripts import _script_store
    _script_store["test-scene-rewrite"] = {
        "id": "test-scene-rewrite",
        "title": "测试剧本",
        "genre": "重生",
        "episodes": [],
        "characters": [],
        "scenes": [{"name": "皇宫", "description": "金碧辉煌的宫殿", "atmosphere": "庄严"}],
        "props": [],
    }

    mock_response = '```json\n{"name": "皇宫", "description": "阴暗压抑的宫殿", "atmosphere": "肃杀"}\n```'

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/rewrite", json={
            "script_id": "test-scene-rewrite",
            "target": "scene",
            "target_name": "皇宫",
            "instruction": "改成更阴暗压抑的氛围",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert "阴暗" in data["result"]["description"]

    del _script_store["test-scene-rewrite"]


@pytest.mark.asyncio
async def test_rewrite_prop(client):
    """Test rewriting a prop."""
    from app.api.scripts import _script_store
    _script_store["test-prop-rewrite"] = {
        "id": "test-prop-rewrite",
        "title": "测试剧本",
        "genre": "重生",
        "episodes": [],
        "characters": [],
        "scenes": [],
        "props": [{"name": "玉佩", "description": "传家玉佩"}],
    }

    mock_response = '```json\n{"name": "凤凰玉佩", "description": "蕴含神秘力量的传家玉佩"}\n```'

    with patch("app.core.ai_client.ai_client.chat", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/scripts/rewrite", json={
            "script_id": "test-prop-rewrite",
            "target": "prop",
            "target_name": "玉佩",
            "instruction": "给玉佩增加神秘力量设定",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert "神秘" in data["result"]["description"]

    del _script_store["test-prop-rewrite"]


@pytest.mark.asyncio
async def test_rewrite_invalid_target(client):
    """Test rewrite with invalid target content."""
    from app.api.scripts import _script_store
    _script_store["test-invalid-rewrite"] = {
        "id": "test-invalid-rewrite",
        "title": "测试",
        "genre": "重生",
        "episodes": [],
        "characters": [],
        "scenes": [],
        "props": [],
    }

    resp = await client.post("/api/scripts/rewrite", json={
        "script_id": "test-invalid-rewrite",
        "target": "character",
        "target_name": "不存在的角色",
        "instruction": "改一下",
    })
    assert resp.status_code == 400

    del _script_store["test-invalid-rewrite"]


# ============================================================
# Novel Upload Enhanced Tests
# ============================================================

@pytest.mark.asyncio
async def test_upload_novel_with_characters(client):
    """Test novel upload returns characters with AI prompts."""
    mock_result = {
        "title": "改编剧本",
        "genre": "重生",
        "episodes": [
            {
                "episode_number": 1,
                "title": "第一集",
                "summary": "测试",
                "shots": [
                    {
                        "shot_number": 1,
                        "shot_type": "特写",
                        "frame_content": "女主睁眼",
                        "dialogue": "我重生了？",
                        "video_prompt": "特写镜头，女主缓缓睁开眼睛，瞳孔中倒映着天花板的灯光，她低声说'我重生了？'",
                        "hook_type": "hook",
                    }
                ],
            }
        ],
        "characters": [
            {
                "name": "女主",
                "identity": "重生千金",
                "personality": "坚韧",
                "appearance": "长发",
                "three_view_prompt": "front view of a young woman with long black hair",
                "portrait_prompt": "close-up portrait",
                "expression_prompts": {"happy": "smiling face", "angry": "angry face"},
            }
        ],
        "scenes": [
            {
                "name": "皇宫",
                "description": "金碧辉煌",
                "scene_prompt": "grand palace interior",
                "scene_variants": {"day": "palace in daylight", "night": "palace at night"},
            }
        ],
        "props": [
            {
                "name": "玉佩",
                "description": "传家之宝",
                "prop_prompt": "jade pendant with dragon motif",
            }
        ],
    }
    with patch("app.api.scripts.script_generator.adapt_novel", new_callable=AsyncMock, return_value=mock_result):
        resp = await client.post("/api/scripts/upload-novel", files={
            "file": ("test.txt", "第一章\n这是测试小说内容。" * 50, "text/plain"),
        })
        assert resp.status_code == 200
        data = resp.json()
        result = data["result"]
        assert result["title"] == "改编剧本"
        assert len(result["characters"]) == 1
        assert result["characters"][0]["three_view_prompt"] != ""
        assert result["characters"][0]["expression_prompts"]["happy"] != ""
        assert len(result["scenes"]) == 1
        assert result["scenes"][0]["scene_variants"]["day"] != ""
        assert len(result["props"]) == 1
        assert result["props"][0]["prop_prompt"] != ""
        assert len(result["episodes"]) == 1
        assert result["episodes"][0]["shots"][0]["hook_type"] == "hook"


# ============================================================
# Trends Search Test
# ============================================================

@pytest.mark.asyncio
async def test_trends_search(client):
    """Test trend search endpoint."""
    mock_results = [
        TrendItem(
            id="search1",
            title="搜索结果",
            source=TrendSource.HONGGUO,
            category="重生",
            heat=5000,
            tags=["重生"],
        ),
    ]
    with patch("app.services.trend_service.trend_service.search_across_platforms", new_callable=AsyncMock, return_value=mock_results):
        resp = await client.get("/api/trends/search?keyword=重生")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


@pytest.mark.asyncio
async def test_trends_related(client):
    """Test related trends endpoint."""
    mock_related = [
        TrendItem(
            id="related1",
            title="相关热点",
            source=TrendSource.HONGGUO,
            category="复仇",
            heat=4000,
            tags=["复仇"],
        ),
    ]
    with patch("app.services.trend_service.trend_service.get_related_trends", new_callable=AsyncMock, return_value=mock_related):
        resp = await client.get("/api/trends/related/test1")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
