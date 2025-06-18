"""
小說寫作器的數據模型定義
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from .enums import CreationStatus, WritingStyle, PacingStyle


@dataclass
class APIConfig:
    """API配置數據類"""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    provider: str = "openai"
    api_key: str = ""
    max_retries: int = 3
    timeout: int = 60
    language: str = "zh-TW"
    use_traditional_quotes: bool = True
    disable_thinking: bool = False

    # 新增規劃模型設定
    use_planning_model: bool = False
    planning_base_url: str = "https://api.openai.com/v1"
    planning_model: str = "gpt-4-turbo"
    planning_provider: str = "openai"
    planning_api_key: str = ""


@dataclass
class Paragraph:
    """段落數據類"""
    order: int
    purpose: str
    content_type: str = ""
    key_points: List[str] = None
    estimated_words: int = 0
    mood: str = ""
    content: str = ""
    status: CreationStatus = CreationStatus.NOT_STARTED
    word_count: int = 0
    
    def __post_init__(self):
        if self.key_points is None:
            self.key_points = []


@dataclass
class Chapter:
    """章節數據類"""
    title: str
    summary: str
    key_events: List[str] = None
    characters_involved: List[str] = None
    estimated_words: int = 3000
    outline: Dict = None
    paragraphs: List[Paragraph] = None
    content: str = ""
    status: CreationStatus = CreationStatus.NOT_STARTED
    
    def __post_init__(self):
        if self.key_events is None:
            self.key_events = []
        if self.characters_involved is None:
            self.characters_involved = []
        if self.outline is None:
            self.outline = {}
        if self.paragraphs is None:
            self.paragraphs = []


@dataclass
class ChapterPlotSummary:
    """章節情節摘要"""
    chapter_index: int
    chapter_title: str
    plot_points: List[str] = field(default_factory=list)  # 該章節的詳細情節點
    summary: str = ""  # 章節完成後生成的詳細摘要
    key_developments: List[str] = field(default_factory=list)  # 關鍵劇情發展
    characters_introduced: List[str] = field(default_factory=list)  # 新登場角色
    settings_introduced: List[str] = field(default_factory=list)  # 新出現場景

@dataclass
class WorldBuilding:
    """世界設定數據類"""
    characters: Dict[str, str] = None
    settings: Dict[str, str] = None
    terminology: Dict[str, str] = None
    plot_points: List[str] = None  # 保留原有的全局情節點（向後兼容）
    relationships: List[Dict] = None
    style_guide: str = ""
    chapter_notes: List[str] = None  # 新增：章節註記，記錄各項設定出現的章節
    
    # 新增：按章節組織的情節處理
    chapter_plot_summaries: Dict[int, ChapterPlotSummary] = None  # 按章節索引存儲情節摘要
    current_chapter_plot_points: List[str] = None  # 當前章節正在累積的情節點
    
    def __post_init__(self):
        if self.characters is None:
            self.characters = {}
        if self.settings is None:
            self.settings = {}
        if self.terminology is None:
            self.terminology = {}
        if self.plot_points is None:
            self.plot_points = []
        if self.relationships is None:
            self.relationships = []
        if self.chapter_notes is None:
            self.chapter_notes = []
        if self.chapter_plot_summaries is None:
            self.chapter_plot_summaries = {}
        if self.current_chapter_plot_points is None:
            self.current_chapter_plot_points = []


@dataclass
class GlobalWritingConfig:
    """全局創作配置"""
    # 基本風格設定
    writing_style: WritingStyle = WritingStyle.THIRD_PERSON_LIMITED
    pacing_style: PacingStyle = PacingStyle.BALANCED
    tone: str = "溫暖"  # 用戶自定義語調
    
    # 持續考慮事項
    continuous_themes: List[str] = field(default_factory=list)  # ["友情的力量", "成長的代價"]
    must_include_elements: List[str] = field(default_factory=list)  # ["魔法系統邏輯", "政治背景"]
    avoid_elements: List[str] = field(default_factory=list)  # ["過度暴力", "簡單的善惡對立"]
    
    # 篇幅控制
    target_chapter_words: int = 3000
    target_paragraph_words: int = 300
    paragraph_count_preference: str = "適中"  # "簡潔", "適中", "詳細"
    
    # 文風特徵
    dialogue_style: str = "自然對話"  # 用戶自定義
    description_density: str = "適中"  # "簡潔", "適中", "豐富"
    emotional_intensity: str = "適中"  # "克制", "適中", "濃烈"
    
    # 用戶自定義全局指示
    global_instructions: str = ""  # 用戶的自由輸入區域


@dataclass
class StageSpecificConfig:
    """階段特定配置"""
    # 每個階段的用戶額外指示
    additional_prompt: str = ""
    
    # 階段特定參數
    creativity_level: float = 0.7  # 0-1, 創意程度
    detail_level: str = "適中"  # "簡潔", "適中", "詳細"
    focus_aspects: List[str] = field(default_factory=list)  # 本階段要重點關注的方面
    
    # 篇幅控制
    word_count_strict: bool = False  # 是否嚴格控制字數
    length_preference: str = "auto"  # "short", "medium", "long", "auto"


@dataclass
class NovelProject:
    """小說項目數據類"""
    title: str = ""
    theme: str = ""
    outline: str = ""
    outline_additional_prompt: str = ""  # 大綱生成額外指示
    chapters_additional_prompt: str = ""  # 章節劃分額外指示
    chapters: List[Chapter] = None
    world_building: WorldBuilding = None
    current_context: str = ""
    api_config: APIConfig = None
    global_config: GlobalWritingConfig = None  # 新增全局配置
    
    def __post_init__(self):
        if self.chapters is None:
            self.chapters = []
        if self.world_building is None:
            self.world_building = WorldBuilding()
        if self.api_config is None:
            self.api_config = APIConfig()
        if self.global_config is None:
            self.global_config = GlobalWritingConfig()