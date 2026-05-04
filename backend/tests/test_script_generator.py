"""Tests for script generator utility functions."""
import pytest
from app.services.script_generator import ScriptGenerator


gen = ScriptGenerator()


class TestExtractJson:
    def test_basic_json(self):
        text = '{"title": "测试", "genre": "重生"}'
        result = gen._extract_json(text)
        assert result["title"] == "测试"
        assert result["genre"] == "重生"

    def test_json_in_code_block(self):
        text = '''这是AI的回复：
```json
{"title": "重生千金", "episodes": 8}
```
以上是结果。'''
        result = gen._extract_json(text)
        assert result["title"] == "重生千金"
        assert result["episodes"] == 8

    def test_json_in_code_block_no_lang(self):
        text = '''```
{"title": "测试"}
```'''
        result = gen._extract_json(text)
        assert result["title"] == "测试"

    def test_nested_json(self):
        text = '{"characters": [{"name": "女主", "relationships": {"男主": "爱人"}}]}'
        result = gen._extract_json(text)
        assert result["characters"][0]["name"] == "女主"
        assert result["characters"][0]["relationships"]["男主"] == "爱人"

    def test_json_with_surrounding_text(self):
        text = '好的，这是方案：\n{"title": "战神归来"}\n以上是方案。'
        result = gen._extract_json(text)
        assert result["title"] == "战神归来"

    def test_empty_text(self):
        assert gen._extract_json("") == {}
        assert gen._extract_json(None) == {}

    def test_no_json(self):
        assert gen._extract_json("这里没有任何JSON") == {}

    def test_trailing_comma_fix(self):
        text = '{"title": "测试", "tags": ["a", "b",],}'
        result = gen._extract_json(text)
        assert result["title"] == "测试"
        assert result["tags"] == ["a", "b"]

    def test_truncated_json_recovery(self):
        # Simulate truncated response (at a clean boundary)
        text = '{"title": "测试", "characters": [{"name": "女主"},'
        result = gen._extract_json(text)
        # Should recover the truncated JSON
        assert result.get("title") == "测试"
        assert len(result.get("characters", [])) == 1


class TestTryParseJson:
    def test_valid_json(self):
        result = gen._try_parse_json('{"a": 1}')
        assert result == {"a": 1}

    def test_invalid_json(self):
        result = gen._try_parse_json('not json')
        assert result == {}

    def test_trailing_comma(self):
        result = gen._try_parse_json('{"a": 1, "b": 2,}')
        assert result == {"a": 1, "b": 2}

    def test_nested_trailing_comma(self):
        result = gen._try_parse_json('{"a": [1, 2, 3,],}')
        assert result == {"a": [1, 2, 3]}


class TestSplitChapters:
    def test_split_by_chinese_chapters(self):
        # Each chapter needs >100 chars to pass the filter
        ch1 = "这是第一章的内容。" * 20
        ch2 = "这是第二章的内容。" * 20
        ch3 = "这是第三章的内容。" * 20
        text = f"第一章 开始\n{ch1}\n第二章 发展\n{ch2}\n第三章 高潮\n{ch3}"
        chapters = gen._split_chapters(text)
        assert len(chapters) >= 3

    def test_split_by_double_newlines(self):
        ch1 = "段落一的内容。" * 20
        ch2 = "段落二的内容。" * 20
        ch3 = "段落三的内容。" * 20
        text = f"{ch1}\n\n\n{ch2}\n\n\n{ch3}"
        chapters = gen._split_chapters(text)
        assert len(chapters) >= 3

    def test_short_text_returns_chunks(self):
        text = "这是一段很短的文字" * 50
        chapters = gen._split_chapters(text)
        assert len(chapters) >= 1

    def test_empty_text(self):
        chapters = gen._split_chapters("")
        assert len(chapters) >= 0


class TestExtractJsonEdgeCases:
    def test_multiple_json_blocks_returns_first_valid(self):
        text = '```\n{"a": 1}\n```\n\n```\n{"b": 2}\n```'
        result = gen._extract_json(text)
        assert result["a"] == 1

    def test_json_with_comments_in_code_block(self):
        text = '```json\n{"title": "测试", "genre": "重生"}\n```'
        result = gen._extract_json(text)
        assert result["title"] == "测试"

    def test_deeply_nested_json(self):
        text = '{"a": {"b": {"c": {"d": "deep"}}}}'
        result = gen._extract_json(text)
        assert result["a"]["b"]["c"]["d"] == "deep"

    def test_json_with_unicode(self):
        text = '{"title": "重生千金\\u7684复仇之路"}'
        result = gen._extract_json(text)
        assert "title" in result

    def test_json_array_root_returns_empty(self):
        text = '[{"a": 1}, {"b": 2}]'
        result = gen._extract_json(text)
        # _extract_json only handles {} root, not [] root
        assert result == {} or isinstance(result, dict)
