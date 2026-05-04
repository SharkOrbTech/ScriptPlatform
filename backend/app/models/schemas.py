from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TrendSource(str, Enum):
    HONGGUO = "hongguo"
    TOMATO = "tomato"


class TrendItem(BaseModel):
    id: str
    title: str
    source: TrendSource
    category: str = ""
    heat: int = 0
    description: str = ""
    cover_url: str = ""
    url: str = ""
    tags: list[str] = []
    scraped_at: datetime = Field(default_factory=datetime.now)


class ScriptGenre(str, Enum):
    FANTASY = "玄幻"
    ROMANCE = "甜宠"
    REBIRTH = "重生"
    REVENGE = "复仇"
    URBAN = "都市"
    PERIOD = "古装"
    SUSPENSE = "悬疑"
    COMEDY = "喜剧"
    FEMALE_LEAD = "女强"
    MALE_LEAD = "男频"


class ScriptRequest(BaseModel):
    topic: str = Field(..., description="剧本主题/话题")
    genre: str = Field(default="重生", description="题材类型")
    episode_count: int = Field(default=8, ge=3, le=200, description="集数")
    episode_duration: int = Field(default=90, ge=30, le=300, description="每集时长(秒)")
    target_audience: str = Field(default="18-35岁女性", description="目标受众")
    style: str = Field(default="古风", description="漫剧风格")
    special_requirements: str = Field(default="", description="特殊要求")
    trend_context: Optional[str] = Field(default=None, description="热点上下文")


class Shot(BaseModel):
    shot_number: int
    shot_type: str  # 远景/中景/近景/特写
    camera_movement: str  # 推/拉/摇/移/跟/固定
    frame_content: str  # 画面内容描述
    dialogue: str = ""  # 台词
    sound_effects: str = ""  # 音效
    duration: float = 3.0  # 时长(秒)
    ai_prompt: str = ""  # AI绘图提示词
    lighting: str = ""  # 光影
    emotion: str = ""  # 情绪氛围
    notes: str = ""  # 备注
    hook_type: Optional[str] = None  # 钩子类型: hook/cliffhanger/foreshadowing/turning_point/emotional_peak/revelation/conflict
    hook_detail: str = ""  # 钩子详细分析


class Episode(BaseModel):
    episode_number: int
    title: str
    summary: str
    hook: str = ""  # 开头钩子
    cliffhanger: str = ""  # 结尾悬念
    shots: list[Shot] = []
    total_duration: float = 0
    key_conflict: str = ""  # 核心冲突
    emotional_arc: str = ""  # 情感弧线


class Character(BaseModel):
    name: str
    age: str = ""
    identity: str = ""
    personality: str = ""
    appearance: str = ""
    clothing: str = ""
    signature_element: str = ""
    arc: str = ""
    relationships: dict[str, str] = {}
    ai_prompt: str = ""


class Script(BaseModel):
    id: str
    title: str
    genre: str
    logline: str = ""
    synopsis: str = ""
    characters: list[Character] = []
    episodes: list[Episode] = []
    theme: str = ""
    emotional_tone: str = ""
    target_audience: str = ""
    style: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    copyright_risk: Optional["CopyrightResult"] = None


class CopyrightResult(BaseModel):
    risk_level: str  # low/medium/high
    risk_score: float  # 0-100
    similar_titles: list[dict] = []
    suggestions: list[str] = []
    checked_at: datetime = Field(default_factory=datetime.now)


class NovelUpload(BaseModel):
    filename: str
    content: str
    episode_count: int = 8
    genre: str = "重生"
    style: str = "古风"


class ScriptResponse(BaseModel):
    id: str
    status: str  # generating/completed/failed
    progress: float = 0.0
    current_episode: int = 0
    total_episodes: int = 0
    current_phase: str = ""
    script: Optional[Script] = None
    error: str = ""


class KnowledgeEntity(BaseModel):
    name: str
    entity_type: str  # character/location/emotion/item/plot_point
    description: str
    attributes: dict = {}
    first_appearance: str = ""
    last_update: str = ""
