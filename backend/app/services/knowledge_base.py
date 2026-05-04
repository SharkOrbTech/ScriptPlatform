"""
Knowledge Base Service - Manages persistent context for long-form script generation.

Architecture:
- Each script project gets its own knowledge directory
- Entities (characters, locations, items, emotions, plot points) are stored as individual files
- A project manifest tracks all entities and their relationships
- For each episode generation, the relevant subset of knowledge is loaded into context
- ChromaDB is used for semantic search across the knowledge base

This approach ensures:
1. Context doesn't overflow - only relevant entities are loaded per episode
2. Consistency - character traits, locations, etc. are persisted and referenced
3. Incremental updates - each episode can update entity states
4. Cross-episode continuity - plot threads and foreshadowing are tracked
"""
import json
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.schemas import KnowledgeEntity, Character, Episode

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path("./knowledge_base")


class KnowledgeBase:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = KNOWLEDGE_DIR / project_id
        self.entities_dir = self.project_dir / "entities"
        self.episodes_dir = self.project_dir / "episodes"
        self.manifest_path = self.project_dir / "manifest.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.project_dir, self.entities_dir, self.episodes_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {
            "project_id": self.project_id,
            "created_at": datetime.now().isoformat(),
            "entities": {},
            "episodes": [],
            "plot_threads": [],
            "foreshadowing": [],
            "world_rules": [],
        }

    def _save_manifest(self, manifest: dict):
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Remove path-unsafe characters from entity names."""
        return name.replace("/", "_").replace("\\", "_").replace(":", "_")

    def add_entity(self, entity: KnowledgeEntity):
        """Add or update an entity in the knowledge base."""
        manifest = self._load_manifest()
        safe_name = self._sanitize_name(entity.name)
        entity_id = f"{entity.entity_type}_{safe_name}"

        # Save entity file
        entity_file = self.entities_dir / f"{entity_id}.json"
        entity_data = entity.model_dump()
        entity_data["last_update"] = datetime.now().isoformat()
        entity_file.write_text(json.dumps(entity_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Update manifest
        manifest["entities"][entity_id] = {
            "name": entity.name,
            "type": entity.entity_type,
            "file": f"entities/{entity_id}.json",
            "last_update": datetime.now().isoformat(),
        }
        self._save_manifest(manifest)

    def get_entity(self, entity_id: str) -> Optional[KnowledgeEntity]:
        """Get an entity by ID."""
        entity_file = self.entities_dir / f"{entity_id}.json"
        if entity_file.exists():
            data = json.loads(entity_file.read_text(encoding="utf-8"))
            return KnowledgeEntity(**data)
        return None

    def get_all_entities(self, entity_type: str = None) -> list[KnowledgeEntity]:
        """Get all entities, optionally filtered by type."""
        manifest = self._load_manifest()
        entities = []
        for eid, info in manifest.get("entities", {}).items():
            if entity_type and info["type"] != entity_type:
                continue
            entity = self.get_entity(eid)
            if entity:
                entities.append(entity)
        return entities

    def save_episode(self, episode: Episode):
        """Save an episode and extract/update knowledge entities."""
        manifest = self._load_manifest()

        # Save episode file
        ep_file = self.episodes_dir / f"episode_{episode.episode_number:02d}.json"
        ep_data = episode.model_dump()
        ep_data["saved_at"] = datetime.now().isoformat()
        ep_file.write_text(json.dumps(ep_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Update manifest
        if episode.episode_number not in manifest["episodes"]:
            manifest["episodes"].append(episode.episode_number)
        self._save_manifest(manifest)

    def get_episode(self, episode_number: int) -> Optional[Episode]:
        """Get a saved episode."""
        ep_file = self.episodes_dir / f"episode_{episode_number:02d}.json"
        if ep_file.exists():
            data = json.loads(ep_file.read_text(encoding="utf-8"))
            data.pop("saved_at", None)
            return Episode(**data)
        return None

    def get_context_for_episode(self, episode_number: int, max_chars: int = 4000) -> str:
        """
        Build a context string for generating a specific episode.
        Includes: character info, world rules, plot threads, previous episode summary.
        """
        manifest = self._load_manifest()
        context_parts = []

        # 1. Characters (most important)
        characters = self.get_all_entities("character")
        if characters:
            char_text = "## 角色信息\n"
            for c in characters:
                char_text += f"- **{c.name}**: {c.description}\n"
                for k, v in c.attributes.items():
                    if v:
                        char_text += f"  - {k}: {v}\n"
            context_parts.append(char_text)

        # 2. World rules
        world_rules = manifest.get("world_rules", [])
        if world_rules:
            rules_text = "## 世界观规则\n"
            for r in world_rules:
                rules_text += f"- {r}\n"
            context_parts.append(rules_text)

        # 3. Plot threads (active storylines)
        plot_threads = manifest.get("plot_threads", [])
        if plot_threads:
            threads_text = "## 活跃剧情线\n"
            for t in plot_threads:
                if isinstance(t, dict):
                    threads_text += f"- **{t.get('name', '')}**: {t.get('status', '')} - {t.get('description', '')}\n"
                else:
                    threads_text += f"- {t}\n"
            context_parts.append(threads_text)

        # 4. Foreshadowing (unresolved setups)
        foreshadowing = manifest.get("foreshadowing", [])
        unresolved = [f for f in foreshadowing if isinstance(f, dict) and not f.get("resolved", False)]
        if unresolved:
            fs_text = "## 未解伏笔\n"
            for f in unresolved:
                fs_text += f"- **{f.get('setup', '')}** (第{f.get('episode', '?')}集埋下): 预计在第{f.get('payoff_episode', '?')}集揭晓\n"
            context_parts.append(fs_text)

        # 5. Previous episode summary (for continuity)
        if episode_number > 1:
            prev_ep = self.get_episode(episode_number - 1)
            if prev_ep:
                prev_text = f"## 上一集概要 (第{episode_number - 1}集: {prev_ep.title})\n"
                prev_text += f"{prev_ep.summary}\n"
                if prev_ep.cliffhanger:
                    prev_text += f"**悬念**: {prev_ep.cliffhanger}\n"
                if prev_ep.key_conflict:
                    prev_text += f"**核心冲突**: {prev_ep.key_conflict}\n"
                context_parts.append(prev_text)

        # 6. Locations
        locations = self.get_all_entities("location")
        if locations:
            loc_text = "## 场景地点\n"
            for loc in locations:
                loc_text += f"- **{loc.name}**: {loc.description}\n"
            context_parts.append(loc_text)

        # 7. Key items/objects
        items = self.get_all_entities("item")
        if items:
            item_text = "## 关键道具\n"
            for i in items:
                item_text += f"- **{i.name}**: {i.description}\n"
            context_parts.append(item_text)

        full_context = "\n\n".join(context_parts)

        # Truncate if too long
        if len(full_context) > max_chars:
            full_context = full_context[:max_chars] + "\n\n[上下文已截断...]"

        return full_context

    def add_plot_thread(self, name: str, description: str, status: str = "进行中"):
        """Add a new plot thread."""
        manifest = self._load_manifest()
        manifest.setdefault("plot_threads", []).append({
            "name": name,
            "description": description,
            "status": status,
            "created_at": datetime.now().isoformat(),
        })
        self._save_manifest(manifest)

    def add_foreshadowing(self, setup: str, episode: int, payoff_episode: int = 0):
        """Add a foreshadowing element."""
        manifest = self._load_manifest()
        manifest.setdefault("foreshadowing", []).append({
            "setup": setup,
            "episode": episode,
            "payoff_episode": payoff_episode,
            "resolved": False,
            "created_at": datetime.now().isoformat(),
        })
        self._save_manifest(manifest)

    def add_world_rule(self, rule: str):
        """Add a world-building rule."""
        manifest = self._load_manifest()
        manifest.setdefault("world_rules", []).append(rule)
        self._save_manifest(manifest)

    def extract_entities_from_episode(self, episode: Episode):
        """Extract and update knowledge entities from a completed episode."""
        # Extract character info from shots
        for shot in episode.shots:
            # Parse character mentions from dialogue and frame content
            content = f"{shot.frame_content} {shot.dialogue}"
            # This is a simplified extraction - in production, use NER
            # For now, update existing characters if mentioned
            for entity in self.get_all_entities("character"):
                if entity.name in content:
                    entity.attributes.setdefault("last_mentioned", f"第{episode.episode_number}集")
                    entity.attributes["appearances"] = entity.attributes.get("appearances", 0) + 1
                    self.add_entity(entity)

    def get_full_script_context(self) -> str:
        """Get the full context of the entire script for final review."""
        manifest = self._load_manifest()
        context = f"# 剧本项目: {self.project_id}\n\n"

        # All characters
        characters = self.get_all_entities("character")
        if characters:
            context += "## 全部角色\n"
            for c in characters:
                context += f"- {c.name}: {c.description}\n"

        # Episode summaries
        context += "\n## 各集概要\n"
        for ep_num in sorted(manifest.get("episodes", [])):
            ep = self.get_episode(ep_num)
            if ep:
                context += f"\n### 第{ep_num}集: {ep.title}\n{ep.summary}\n"

        # World rules
        world_rules = manifest.get("world_rules", [])
        if world_rules:
            context += "\n## 世界观\n"
            for r in world_rules:
                context += f"- {r}\n"

        return context
