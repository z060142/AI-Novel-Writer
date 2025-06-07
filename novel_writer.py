"""
重構後的階層式小說編寫器 - 完整版
採用更清晰的架構和更好的錯誤處理
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import threading
import re
import traceback
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """任務類型枚舉"""
    OUTLINE = "outline"
    CHAPTERS = "chapters"
    CHAPTER_OUTLINE = "chapter_outline"
    PARAGRAPHS = "paragraphs"
    WRITING = "writing"
    WORLD_BUILDING = "world_building"

class CreationStatus(Enum):
    """創作狀態枚舉"""
    NOT_STARTED = "未開始"
    IN_PROGRESS = "進行中"
    COMPLETED = "已完成"
    ERROR = "錯誤"

class WritingStyle(Enum):
    """寫作風格枚舉"""
    FIRST_PERSON = "第一人稱"
    THIRD_PERSON_LIMITED = "第三人稱限制視角"
    THIRD_PERSON_OMNISCIENT = "第三人稱全知視角"
    MULTIPLE_POV = "多重視角"

class PacingStyle(Enum):
    """節奏風格枚舉"""
    SLOW_BURN = "慢熱型"
    FAST_PACED = "快節奏"
    BALANCED = "平衡型"
    EPISODIC = "章回體"

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
class WorldBuilding:
    """世界設定數據類"""
    characters: Dict[str, str] = None
    settings: Dict[str, str] = None
    terminology: Dict[str, str] = None
    plot_points: List[str] = None
    relationships: List[Dict] = None
    style_guide: str = ""
    chapter_notes: List[str] = None  # 新增：章節註記，記錄各項設定出現的章節
    
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

class APIException(Exception):
    """API相關異常"""
    pass

class JSONParseException(Exception):
    """JSON解析異常"""
    pass

def safe_execute(func: Callable) -> Callable:
    """安全執行裝飾器"""
    def wrapper(self, *args, **kwargs):
        try:
            logger.info(f"開始執行函數：{func.__name__}")
            result = func(self, *args, **kwargs)
            logger.info(f"函數執行完成：{func.__name__}")
            return result
        except Exception as e:
            error_msg = f"執行 {func.__name__} 時發生錯誤: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            if hasattr(self, 'debug_log'):
                self.debug_log(f"❌ {error_msg}")
                self.debug_log(f"❌ 詳細錯誤: {traceback.format_exc()}")
            
            raise
    return wrapper

class APIConnector:
    """LLM API連接器 - 重構版"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        
    def call_api(self, messages: List[Dict], max_tokens: int = 2000, 
                temperature: float = 0.7) -> Dict:
        """調用LLM API with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"API調用嘗試 {attempt + 1}/{self.config.max_retries}")
                
                if self.config.provider == "openai":
                    return self._call_openai_api(messages, max_tokens, temperature)
                elif self.config.provider == "anthropic":
                    return self._call_anthropic_api(messages, max_tokens, temperature)
                elif self.config.provider == "custom":
                    return self._call_custom_api(messages, max_tokens, temperature)
                else:
                    raise APIException(f"不支持的API提供商: {self.config.provider}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"API調用失敗 (嘗試 {attempt + 1}): {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise APIException(f"API調用失敗，已重試 {self.config.max_retries} 次: {str(e)}")
            except Exception as e:
                logger.error(f"API調用出現未預期錯誤: {str(e)}")
                raise APIException(f"API調用錯誤: {str(e)}")
    
    def _call_openai_api(self, messages: List[Dict], max_tokens: int, 
                        temperature: float) -> Dict:
        """調用OpenAI格式API"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 如果啟用了關閉thinking，添加thinking參數
        if self.config.disable_thinking:
            data["thinking"] = False
        
        response = requests.post(
            f"{self.config.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "content": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result.get("model", self.config.model)
            }
        else:
            raise APIException(f"API調用失敗: {response.status_code} {response.text}")
    
    def _call_anthropic_api(self, messages: List[Dict], max_tokens: int, 
                           temperature: float) -> Dict:
        """調用Anthropic API"""
        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # 轉換消息格式
        system_message = ""
        if messages and messages[0]["role"] == "system":
            system_message = messages[0]["content"]
            messages = messages[1:]
        
        data = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_message:
            data["system"] = system_message
        
        response = requests.post(
            f"{self.config.base_url}/messages",
            headers=headers,
            json=data,
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "content": result["content"][0]["text"],
                "usage": result.get("usage", {}),
                "model": result.get("model", self.config.model)
            }
        else:
            raise APIException(f"API調用失敗: {response.status_code} {response.text}")
    
    def _call_custom_api(self, messages: List[Dict], max_tokens: int, 
                        temperature: float) -> Dict:
        """調用自訂API"""
        return self._call_openai_api(messages, max_tokens, temperature)

class TextFormatter:
    """文本格式化器"""
    
    @staticmethod
    def format_novel_content(content: str, use_traditional_quotes: bool = True) -> str:
        """格式化小說內容"""
        if not content:
            return content
        
        # 統一引號
        if use_traditional_quotes:
            # 將所有英文引號轉換為中文引號
            content = re.sub(r'"([^"]*)"', r'「\1」', content)
            content = re.sub(r'"([^"]*)"', r'「\1」', content)
            content = re.sub(r'"([^"]*)"', r'「\1」', content)
        else:
            # 將所有中文引號轉換為英文引號
            content = re.sub(r'「([^」]*)」', r'"\1"', content)
        
        # 處理段落分行
        content = TextFormatter._format_paragraphs(content)
        
        # 處理對話格式
        content = TextFormatter._format_dialogue(content, use_traditional_quotes)
        
        # 清理多餘的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 確保句子結尾有適當的標點
        content = TextFormatter._fix_punctuation(content)
        
        return content.strip()
    
    @staticmethod
    def _format_paragraphs(content: str) -> str:
        """格式化段落分行"""
        # 在句號、感嘆號、問號後添加換行（如果後面不是換行的話）
        content = re.sub(r'([。！？])([^」\n])', r'\1\n\n\2', content)
        
        # 在引號結束後如果有句號等，也要換行
        content = re.sub(r'([」])([。！？])([^」\n])', r'\1\2\n\n\3', content)
        
        # 處理對話後的描述
        content = re.sub(r'([」])([^。！？\n][^」]*?[。！？])', r'\1\n\n\2', content)
        
        return content
    
    @staticmethod
    def _format_dialogue(content: str, use_traditional_quotes: bool) -> str:
        """格式化對話"""
        if use_traditional_quotes:
            # 確保對話前有適當的分行
            content = re.sub(r'([。！？])(\s*)([^」\n]*?)「', r'\1\n\n\3「', content)
        else:
            # 確保對話前有適當的分行
            content = re.sub(r'([。！？])(\s*)([^"\n]*?)"', r'\1\n\n\3"', content)
        
        return content
    
    @staticmethod
    def _fix_punctuation(content: str) -> str:
        """修復標點符號"""
        # 確保句子結尾有標點
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not re.search(r'[。！？」"]$', line):
                # 如果行末沒有標點，添加句號
                if re.search(r'[a-zA-Z0-9\u4e00-\u9fff]$', line):
                    line += '。'
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

class JSONParser:
    """JSON解析器 - 重構版"""
    
    @staticmethod
    def extract_json_from_content(content: str) -> Optional[Dict]:
        """從內容中提取JSON"""
        strategies = [
            (r'```json\s*(.*?)\s*```', re.DOTALL),
            (r'```\s*(\{.*?\})\s*```', re.DOTALL),
            (r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL),
        ]
        
        for pattern, flags in strategies:
            matches = re.findall(pattern, content, flags)
            
            for match in matches:
                json_str = match.strip() if isinstance(match, str) else match
                json_str = JSONParser._clean_json_string(json_str)
                
                try:
                    result = json.loads(json_str)
                    if isinstance(result, dict) and result:
                        return result
                except json.JSONDecodeError:
                    continue
        
        return JSONParser._attempt_json_repair(content)
    
    @staticmethod
    def _clean_json_string(json_str: str) -> str:
        """清理JSON字符串"""
        json_str = json_str.lstrip('\ufeff').strip()
        
        start_brace = json_str.find('{')
        if start_brace != -1:
            json_str = json_str[start_brace:]
        
        end_brace = json_str.rfind('}')
        if end_brace != -1:
            json_str = json_str[:end_brace + 1]
        
        return json_str
    
    @staticmethod
    def _attempt_json_repair(content: str) -> Optional[Dict]:
        """嘗試修復損壞的JSON"""
        json_start = content.find('{')
        if json_start == -1:
            return None
        
        json_part = content[json_start:]
        brace_count = 0
        valid_end = -1
        
        for i, char in enumerate(json_part):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    valid_end = i + 1
                    break
        
        if valid_end > 0:
            repaired_json = json_part[:valid_end]
            try:
                return json.loads(repaired_json)
            except json.JSONDecodeError:
                pass
        
        return None

class DynamicPromptBuilder:
    """動態Prompt構建器"""
    
    def __init__(self, global_config: GlobalWritingConfig):
        self.global_config = global_config
    
    def build_outline_prompt(self, title: str, theme: str, stage_config: StageSpecificConfig) -> str:
        """構建大綱生成prompt"""
        base_prompt = f"""請為小說《{title}》生成完整的創作大綱。

【基本信息】
- 標題：{title}
- 主題：{theme}
- 敘述風格：{self.global_config.writing_style.value}
- 節奏風格：{self.global_config.pacing_style.value}
- 整體語調：{self.global_config.tone}"""

        # 添加持續考慮事項
        if self.global_config.continuous_themes:
            base_prompt += f"\n- 核心主題：{', '.join(self.global_config.continuous_themes)}"
        
        if self.global_config.must_include_elements:
            base_prompt += f"\n- 必須包含：{', '.join(self.global_config.must_include_elements)}"
        
        if self.global_config.avoid_elements:
            base_prompt += f"\n- 需要避免：{', '.join(self.global_config.avoid_elements)}"

        # 添加創作要求
        base_prompt += f"""

【創作要求】
- 預計章節數：10-15章
- 每章目標字數：約{self.global_config.target_chapter_words}字
- 詳細程度：{stage_config.detail_level}
- 創意發揮：{self._get_creativity_instruction(stage_config.creativity_level)}"""

        # 添加全局指示
        if self.global_config.global_instructions.strip():
            base_prompt += f"""

【全局創作指導】
{self.global_config.global_instructions.strip()}"""

        # 添加階段特定指示
        if stage_config.additional_prompt.strip():
            base_prompt += f"""

【本階段特別指示】
{stage_config.additional_prompt.strip()}"""

        # 添加重點關注方面
        if stage_config.focus_aspects:
            base_prompt += f"""

【重點關注】請特別注意以下方面：{', '.join(stage_config.focus_aspects)}"""

        return base_prompt

    def build_chapter_division_prompt(self, outline: str, stage_config: StageSpecificConfig) -> str:
        """構建章節劃分prompt"""
        base_prompt = f"""基於以下大綱，請劃分章節結構：

【整體大綱】
{outline}

【劃分要求】
- 章節數量：10-15章
- 每章目標字數：{self.global_config.target_chapter_words}字
- 節奏風格：{self.global_config.pacing_style.value}
- 詳細程度：{stage_config.detail_level}"""

        # 添加持續考慮事項
        if self.global_config.continuous_themes:
            base_prompt += f"\n- 確保章節安排體現：{', '.join(self.global_config.continuous_themes)}"

        base_prompt += f"""

【章節要求】
1. 每章標題要具體且吸引人
2. 章節摘要控制在{self._get_summary_length(stage_config.detail_level)}字以內
3. 確保情節發展符合{self.global_config.pacing_style.value}的特點
4. 章節安排要支持{self.global_config.writing_style.value}的敘述方式"""

        return self._add_common_suffix(base_prompt, stage_config)

    def build_paragraph_writing_prompt(self, context: Dict, stage_config: StageSpecificConfig, 
                                     selected_context: str = "") -> str:
        """構建段落寫作prompt - 最重要的改進"""
        chapter_index = context['chapter_index']
        paragraph_index = context['paragraph_index']
        paragraph = context['paragraph']
        chapter = context['chapter']
        previous_content = context.get('previous_content', '')
        
        # 計算目標字數
        target_words = self._calculate_paragraph_words(paragraph.estimated_words, stage_config)
        
        base_prompt = f"""請寫作第{chapter_index+1}章第{paragraph_index+1}段：

【寫作風格】
- 敘述方式：{self.global_config.writing_style.value}
- 語調：{self.global_config.tone}
- 對話風格：{self.global_config.dialogue_style}
- 描述密度：{self.global_config.description_density}
- 情感強度：{self.global_config.emotional_intensity}

【段落任務】
- 目的：{paragraph.purpose}
- 目標字數：{target_words}字（{self._get_word_count_instruction(stage_config.word_count_strict)}）
- 氛圍要求：{paragraph.mood}"""

        if paragraph.key_points:
            base_prompt += f"\n- 要點：{', '.join(paragraph.key_points)}"

        # 添加持續考慮事項
        if self.global_config.continuous_themes:
            base_prompt += f"""

【持續主題】在寫作中請考慮體現：{', '.join(self.global_config.continuous_themes)}"""

        if self.global_config.must_include_elements:
            base_prompt += f"""

【必要元素】請適當融入：{', '.join(self.global_config.must_include_elements)}"""

        # 添加上下文
        base_prompt += f"""

【章節背景】
- 章節標題：{chapter.title}
- 章節目標：{chapter.summary}"""

        if chapter.outline:
            base_prompt += f"\n- 章節大綱：{json.dumps(chapter.outline, ensure_ascii=False)}"

        # 用戶選中的參考內容
        if selected_context.strip():
            base_prompt += f"""

【特別參考】用戶指定參考內容，請與之保持一致：
{selected_context.strip()}"""

        # 前文內容
        if previous_content:
            base_prompt += f"""

【前文內容】以下是前面的段落，請承接但不重複：
{previous_content}"""

        # 篇幅控制指導
        base_prompt += f"""

【篇幅控制】
{self._get_length_guidance(target_words, stage_config.length_preference)}"""

        return self._add_common_suffix(base_prompt, stage_config)

    def _add_common_suffix(self, base_prompt: str, stage_config: StageSpecificConfig) -> str:
        """添加通用後綴"""
        if self.global_config.global_instructions.strip():
            base_prompt += f"""

【全局創作指導】
{self.global_config.global_instructions.strip()}"""

        if stage_config.additional_prompt.strip():
            base_prompt += f"""

【特別指示】
{stage_config.additional_prompt.strip()}"""

        if stage_config.focus_aspects:
            base_prompt += f"""

【重點關注】請特別注意：{', '.join(stage_config.focus_aspects)}"""

        return base_prompt

    def _get_creativity_instruction(self, level: float) -> str:
        """獲取創意程度指導"""
        if level < 0.3:
            return "保守穩健，緊貼大綱"
        elif level < 0.7:
            return "適度創意，可以發揮"
        else:
            return "大膽創新，充分發揮"

    def _get_summary_length(self, detail_level: str) -> int:
        """根據詳細程度確定摘要長度"""
        lengths = {"簡潔": 30, "適中": 50, "詳細": 80}
        return lengths.get(detail_level, 50)

    def _calculate_paragraph_words(self, estimated: int, stage_config: StageSpecificConfig) -> int:
        """計算段落目標字數"""
        base_words = estimated or self.global_config.target_paragraph_words
        
        if stage_config.length_preference == "short":
            return int(base_words * 0.7)
        elif stage_config.length_preference == "long":
            return int(base_words * 1.3)
        else:
            return base_words

    def _get_word_count_instruction(self, strict: bool) -> str:
        """獲取字數控制指導"""
        if strict:
            return "嚴格控制，誤差不超過10%"
        else:
            return "大致符合即可，可適度調整"

    def _get_length_guidance(self, target_words: int, preference: str) -> str:
        """獲取篇幅指導"""
        guidance = f"目標字數：{target_words}字"
        
        if preference == "short":
            guidance += "，要求簡潔有力，避免冗長描述"
        elif preference == "long":
            guidance += "，可以豐富細節，充分展開情節"
        else:
            guidance += "，適度展開，保持節奏"
            
        return guidance

class PromptManager:
    """Prompt管理器"""
    
    TOKEN_LIMITS = {
        TaskType.OUTLINE: 8000,
        TaskType.CHAPTERS: 12000,
        TaskType.CHAPTER_OUTLINE: 6000,
        TaskType.PARAGRAPHS: 8000,
        TaskType.WRITING: 10000,
        TaskType.WORLD_BUILDING: 4000
    }
    
    @staticmethod
    def create_system_prompt(task_type: TaskType) -> str:
        """創建系統prompt"""
        base_prompt = """你是專業的小說創作助手。請直接回答用戶的要求，並將答案以JSON格式放在```json```代碼塊中。

重要要求：
1. 直接輸出JSON，不要多餘的解釋
2. 確保JSON格式正確且完整
3. 內容要實用且符合要求

"""
        
        task_prompts = {
            TaskType.OUTLINE: """
結構要求：
- 字數控制在3000-8000字
JSON格式：
{
    "title": "標題",
    "summary": "故事概要",
    "themes": ["主題1", "主題2"],
    "estimated_chapters": 數字,
    "main_characters": [{"name": "角色名", "desc": "角色描述"}],
    "world_setting": "世界觀",
    "story_flow": "完整的故事發展軌跡 - 從起始情境如何自然演變，經歷什麼樣的變化與轉折，最終走向什麼樣的結局",
    "key_moments": ["重要情節點1", "重要情節點2", "重要情節點3"],
    "character_arcs": "主要角色們在故事中的成長與變化歷程",
    "story_atmosphere": "整體故事的情感色調與氛圍營造",
    "central_conflicts": ["核心衝突1", "核心衝突2"],
    "story_layers": "故事的多重層次 - 表面情節與深層意涵的交織"
}""",
            
            TaskType.CHAPTERS: """
結構要求：
- 字數控制在2500-6000字
JSON格式：
{
    "chapters": [
        {
            "number": 1,
            "title": "章節標題",
            "summary": "章節概要（50字內）",
            "estimated_words": 3000
        }
    ]
}""",
            
            TaskType.CHAPTER_OUTLINE: """
結構要求：
- 字數控制在2500-6000字
JSON格式：
{
    "outline": {
        "story_spark": "這個章節的靈魂火花 - 什麼讓這段故事開始燃燒？",
        "rhythm_flow": "情節的節拍和流動 - 故事如何呼吸、加速、放緩？", 
        "turning_moments": "關鍵的轉折點 - 什麼時刻改變了一切？",
        "emotional_core": "情感的核心 - 什麼感受將貫穿整個章節？",
        "story_elements": "故事中的活躍元素 - 重要的人物、物件、場所會如何參與劇情？",
        "estimated_paragraphs": 8
    }
}""",
            
            TaskType.PARAGRAPHS: """
JSON格式：
{
    "paragraphs": [
        {
            "number": 1,
            "purpose": "段落目的與內容方向的完整描述",
            "estimated_words": 400
        }
    ]
}""",
            
            TaskType.WRITING: """
JSON格式：
{
    "content": "完整的段落內容",
    "word_count": 實際字數
}""",
            
            TaskType.WORLD_BUILDING: """
JSON格式：
{
    "new_characters": [{"name": "角色名", "desc": "簡短描述"}],
    "new_settings": [{"name": "地點名", "desc": "簡短描述"}],
    "new_terms": [{"term": "名詞", "def": "簡短定義"}],
    "plot_points": ["重要情節點"]
}"""
        }
        
        return base_prompt + task_prompts.get(task_type, "")
    
    @staticmethod
    def get_token_limit(task_type: TaskType) -> int:
        """獲取任務類型的token限制"""
        return PromptManager.TOKEN_LIMITS.get(task_type, 8000)

class LLMService:
    """LLM服務層"""
    
    def __init__(self, api_connector: APIConnector, debug_callback: Callable = None):
        self.api_connector = api_connector
        self.debug_callback = debug_callback or (lambda x: None)
        self.json_retry_max = 3  # JSON解析重試次數
    
    def call_llm_with_thinking(self, prompt: str, task_type: TaskType, 
                              max_tokens: int = None) -> Optional[Dict]:
        """使用thinking模式調用LLM，包含JSON解析重試機制"""
        if max_tokens is None:
            max_tokens = PromptManager.get_token_limit(task_type)
        
        system_prompt = PromptManager.create_system_prompt(task_type)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        self.debug_callback(f"\n=== {task_type.value.upper()} 任務開始 ===")
        self.debug_callback(f"使用token限制: {max_tokens}")
        
        # JSON解析重試循環
        for json_attempt in range(self.json_retry_max):
            try:
                self.debug_callback(f"📤 正在調用API... (JSON解析嘗試 {json_attempt + 1}/{self.json_retry_max})")
                
                result = self.api_connector.call_api(messages, max_tokens)
                content = result.get("content", "")
                
                self.debug_callback(f"✅ API調用成功，回應長度: {len(content)} 字符")
                self.debug_callback(f"📝 API完整回應:\n{content}")
                
                json_data = JSONParser.extract_json_from_content(content)
                
                if json_data:
                    self.debug_callback("✅ JSON解析成功")
                    self.debug_callback(f"📋 解析結果:\n{json.dumps(json_data, ensure_ascii=False, indent=2)}")
                    return json_data
                else:
                    self.debug_callback(f"❌ JSON解析失敗 (嘗試 {json_attempt + 1}/{self.json_retry_max})")
                    
                    # 如果不是最後一次嘗試，修改prompt並重試
                    if json_attempt < self.json_retry_max - 1:
                        self.debug_callback("🔄 準備重試，調整prompt以強調JSON格式...")
                        messages = self._enhance_json_prompt(messages, json_attempt + 1)
                        continue
                    else:
                        self.debug_callback("❌ JSON解析重試次數已用盡")
                        raise JSONParseException("經過多次重試仍無法解析JSON回應")
                        
            except JSONParseException:
                # JSON解析異常，繼續重試循環
                if json_attempt == self.json_retry_max - 1:
                    raise
                continue
            except Exception as e:
                self.debug_callback(f"❌ LLM調用失敗: {str(e)}")
                raise
        
        # 理論上不會到達這裡
        raise JSONParseException("JSON解析重試機制異常結束")
    
    def _enhance_json_prompt(self, messages: List[Dict], retry_count: int) -> List[Dict]:
        """增強JSON格式要求的prompt"""
        enhanced_messages = messages.copy()
        
        # 根據重試次數調整策略
        if retry_count == 1:
            # 第一次重試：強調JSON格式
            json_emphasis = """

⚠️ 重要提醒：請務必嚴格按照JSON格式回應！
- 必須使用```json```代碼塊包圍JSON內容
- 確保JSON語法正確，所有字符串都用雙引號包圍
- 不要在JSON前後添加任何解釋文字
- 確保所有括號和逗號都正確配對

示例格式：
```json
{
    "key": "value"
}
```"""
            
        elif retry_count == 2:
            # 第二次重試：更嚴格的要求
            json_emphasis = """

🚨 最後警告：JSON格式要求！
- 只能輸出JSON，不要任何其他文字
- 使用標準JSON語法，不要使用單引號
- 確保所有數字不要用引號包圍
- 確保布爾值使用true/false而不是True/False
- 陣列和物件的最後一個元素後不要有逗號

嚴格按照以下格式：
```json
{
    "required_field": "必填內容"
}
```

立即輸出JSON，不要任何解釋！"""
        
        else:
            # 其他情況的通用強調
            json_emphasis = """

📋 JSON格式檢查清單：
✓ 使用```json```代碼塊
✓ 所有字符串用雙引號
✓ 數字不用引號
✓ 布爾值用true/false
✓ 最後元素無逗號
✓ 括號正確配對

請立即輸出正確的JSON格式！"""
        
        # 修改用戶消息，添加JSON格式強調
        if enhanced_messages and enhanced_messages[-1]["role"] == "user":
            enhanced_messages[-1]["content"] += json_emphasis
        
        return enhanced_messages

class NovelWriterCore:
    """小說編寫器核心邏輯"""
    
    def __init__(self, project: NovelProject, llm_service: LLMService):
        self.project = project
        self.llm_service = llm_service
        self.current_chapter = 0
        self.current_paragraph = 0
        
        # 初始化動態Prompt構建器
        self.prompt_builder = DynamicPromptBuilder(self.project.global_config)
        
        # 各階段配置
        self.stage_configs = {
            TaskType.OUTLINE: StageSpecificConfig(),
            TaskType.CHAPTERS: StageSpecificConfig(),
            TaskType.CHAPTER_OUTLINE: StageSpecificConfig(),
            TaskType.PARAGRAPHS: StageSpecificConfig(),
            TaskType.WRITING: StageSpecificConfig(),
        }
    
    def set_global_config(self, **kwargs):
        """設置全局配置"""
        for key, value in kwargs.items():
            if hasattr(self.project.global_config, key):
                setattr(self.project.global_config, key, value)
        
        # 重新初始化prompt構建器
        self.prompt_builder = DynamicPromptBuilder(self.project.global_config)
    
    def set_stage_config(self, task_type: TaskType, **kwargs):
        """設置階段特定配置"""
        if task_type in self.stage_configs:
            for key, value in kwargs.items():
                if hasattr(self.stage_configs[task_type], key):
                    setattr(self.stage_configs[task_type], key, value)
    
    @safe_execute
    def generate_outline(self, additional_prompt: str = "", tree_callback: Callable = None) -> Dict:
        """生成整體大綱"""
        prompt = f"""
請為一部名為《{self.project.title}》的小說生成完整的整體大綱。

小說要求：
- 標題：{self.project.title}
- 主題/風格：{self.project.theme}

請創建一個完整的故事結構，包括主要角色、世界設定、情節發展等。"""
        
        # 如果有額外的prompt指示，添加到prompt中
        if additional_prompt.strip():
            prompt += f"""

額外指示：
{additional_prompt.strip()}"""
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.OUTLINE)
        
        if result:
            self.project.outline = json.dumps(result, ensure_ascii=False, indent=2)
            self._update_world_building_from_outline(result)
            
            # 通知樹視圖更新
            if tree_callback:
                tree_callback("outline_generated", result)
        
        return result
    
    @safe_execute
    def divide_chapters(self, additional_prompt: str = "", tree_callback: Callable = None) -> List[Chapter]:
        """劃分章節"""
        prompt = f"""
基於以下大綱，請劃分出10-15個章節：

{self.project.outline}

要求：
1. 每章標題要具體且吸引人
2. 章節摘要控制在50字以內
3. 確保情節發展有邏輯性
4. 每章預計3000-5000字

請直接輸出JSON格式。"""
        
        # 如果有額外的prompt指示，添加到prompt中
        if additional_prompt.strip():
            prompt += f"""

額外指示：
{additional_prompt.strip()}"""
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.CHAPTERS)
        
        if result and "chapters" in result:
            chapters = []
            for i, chapter_data in enumerate(result["chapters"]):
                chapter = Chapter(
                    title=chapter_data.get("title", f"第{i+1}章"),
                    summary=chapter_data.get("summary", ""),
                    key_events=chapter_data.get("key_events", []),
                    characters_involved=chapter_data.get("characters_involved", []),
                    estimated_words=chapter_data.get("estimated_words", 3000)
                )
                chapters.append(chapter)
            
            self.project.chapters = chapters
            
            # 通知樹視圖更新
            if tree_callback:
                tree_callback("chapters_generated", chapters)
            
            return chapters
        
        return []
    
    @safe_execute
    def generate_chapter_outline(self, chapter_index: int, tree_callback: Callable = None) -> Dict:
        """生成章節大綱"""
        if chapter_index >= len(self.project.chapters):
            raise ValueError("章節索引超出範圍")
        
        chapter = self.project.chapters[chapter_index]
        
        prompt = f"""
請為第{chapter_index+1}章生成詳細大綱：

整體大綱：
{self.project.outline}

章節信息：
- 標題：{chapter.title}
- 摘要：{chapter.summary}
- 主要事件：{', '.join(chapter.key_events)}
- 涉及角色：{', '.join(chapter.characters_involved)}

當前世界設定：
{self._get_world_context()}

請生成詳細的章節創作大綱。
        """
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.CHAPTER_OUTLINE)
        
        if result and "outline" in result:
            chapter.outline = result["outline"]
            
            # 通知樹視圖更新
            if tree_callback:
                tree_callback("chapter_outline_generated", {"chapter_index": chapter_index, "outline": result["outline"]})
            
            return result["outline"]
        
        return {}
    
    @safe_execute
    def divide_paragraphs(self, chapter_index: int, tree_callback: Callable = None) -> List[Paragraph]:
        """劃分段落"""
        if chapter_index >= len(self.project.chapters):
            raise ValueError("章節索引超出範圍")
        
        chapter = self.project.chapters[chapter_index]
        
        prompt = f"""
基於以下章節大綱，請劃分出具體的段落：

章節標題：{chapter.title}
章節大綱：{json.dumps(chapter.outline, ensure_ascii=False, indent=2)}

請將章節劃分為適當數量的段落，每段都有明確的目的和內容重點。
        """
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.PARAGRAPHS)
        
        if result and "paragraphs" in result:
            paragraphs = []
            for para_data in result["paragraphs"]:
                paragraph = Paragraph(
                    order=para_data.get("number", 0),
                    purpose=para_data.get("purpose", ""),
                    content_type=para_data.get("content_type", ""),
                    key_points=para_data.get("key_points", []),
                    estimated_words=para_data.get("estimated_words", 0),
                    mood=para_data.get("mood", "")
                )
                paragraphs.append(paragraph)
            
            chapter.paragraphs = paragraphs
            
            # 通知樹視圖更新
            if tree_callback:
                tree_callback("paragraphs_generated", {"chapter_index": chapter_index, "paragraphs": paragraphs})
            
            return paragraphs
        
        return []
    
    @safe_execute
    def write_paragraph(self, chapter_index: int, paragraph_index: int, tree_callback: Callable = None, selected_context: str = "") -> str:
        """寫作段落 - 使用動態Prompt構建器"""
        if chapter_index >= len(self.project.chapters):
            raise ValueError("章節索引超出範圍")
        
        chapter = self.project.chapters[chapter_index]
        
        if paragraph_index >= len(chapter.paragraphs):
            raise ValueError("段落索引超出範圍")
        
        paragraph = chapter.paragraphs[paragraph_index]
        
        # 準備上下文
        context = {
            'chapter_index': chapter_index,
            'paragraph_index': paragraph_index,
            'paragraph': paragraph,
            'chapter': chapter,
            'previous_content': self._get_previous_paragraphs_content(chapter_index, paragraph_index)
        }
        
        # 構建動態prompt
        stage_config = self.stage_configs[TaskType.WRITING]
        prompt = self.prompt_builder.build_paragraph_writing_prompt(
            context, stage_config, selected_context
        )
        
        # 獲取API配置中的語言和引號設定
        language = getattr(self.project.api_config, 'language', 'zh-TW')
        use_traditional_quotes = getattr(self.project.api_config, 'use_traditional_quotes', True)
        
        # 添加語言指示到prompt
        language_instruction = self._get_language_instruction(language, use_traditional_quotes)
        prompt = language_instruction + "\n\n" + prompt
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.WRITING)
        
        if result and "content" in result:
            raw_content = result["content"]
            
            # 應用文本格式化
            formatted_content = TextFormatter.format_novel_content(
                raw_content, use_traditional_quotes
            )
            
            paragraph.content = formatted_content
            paragraph.word_count = result.get("word_count", len(formatted_content))
            paragraph.status = CreationStatus.COMPLETED
            
            # 更新世界設定
            self._update_world_building_from_content(formatted_content, chapter_index, paragraph_index)
            
            # 通知樹視圖更新
            if tree_callback:
                tree_callback("paragraph_written", {"chapter_index": chapter_index, "paragraph_index": paragraph_index, "content": formatted_content})
            
            return formatted_content
        
        return ""
    
    def _update_world_building_from_outline(self, outline_data: Dict):
        """從大綱更新世界設定"""
        if "main_characters" in outline_data:
            for char in outline_data["main_characters"]:
                if isinstance(char, dict):
                    name = char.get("name", "")
                    desc = char.get("desc", char.get("description", ""))
                    if name and desc:
                        self.project.world_building.characters[name] = desc
        
        if "world_setting" in outline_data:
            self.project.world_building.settings["總體世界觀"] = outline_data["world_setting"]
    
    def _update_world_building_from_content(self, content: str, chapter_index: int = None, paragraph_index: int = None):
        """從內容更新世界設定"""
        prompt = f"""
分析以下段落，提取需要記錄的重要信息：

段落內容：
{content}

已知設定（避免重複）：
{self._get_world_summary()}

要求：
1. 只提取真正重要的新信息
2. 角色描述限15字內，場景描述限15字內，名詞定義限10字內
3. 忽略次要細節和一次性元素
4. 如果沒有重要新信息，返回空列表

直接輸出JSON格式。
        """
        
        try:
            result = self.llm_service.call_llm_with_thinking(prompt, TaskType.WORLD_BUILDING)
            
            if result:
                # 準備章節註記信息
                chapter_note = ""
                if chapter_index is not None:
                    if chapter_index < len(self.project.chapters):
                        chapter_title = self.project.chapters[chapter_index].title
                        if paragraph_index is not None:
                            chapter_note = f"第{chapter_index+1}章第{paragraph_index+1}段《{chapter_title}》"
                        else:
                            chapter_note = f"第{chapter_index+1}章《{chapter_title}》"
                    else:
                        if paragraph_index is not None:
                            chapter_note = f"第{chapter_index+1}章第{paragraph_index+1}段"
                        else:
                            chapter_note = f"第{chapter_index+1}章"
                
                # 記錄有新增內容的標記
                has_new_content = False
                
                # 更新角色
                for char in result.get("new_characters", []):
                    name = char.get("name", "")
                    desc = char.get("desc", char.get("description", ""))
                    if name and name not in self.project.world_building.characters:
                        self.project.world_building.characters[name] = desc
                        has_new_content = True
                
                # 更新場景
                for setting in result.get("new_settings", []):
                    name = setting.get("name", "")
                    desc = setting.get("desc", setting.get("description", ""))
                    if name and name not in self.project.world_building.settings:
                        self.project.world_building.settings[name] = desc
                        has_new_content = True
                
                # 更新名詞
                for term in result.get("new_terms", []):
                    term_name = term.get("term", "")
                    definition = term.get("def", term.get("definition", ""))
                    if term_name and term_name not in self.project.world_building.terminology:
                        self.project.world_building.terminology[term_name] = definition
                        has_new_content = True
                
                # 更新情節點
                for plot in result.get("plot_points", []):
                    if plot and plot not in self.project.world_building.plot_points:
                        self.project.world_building.plot_points.append(plot)
                        has_new_content = True
                
                # 如果有新增內容且有章節信息，添加章節註記
                if has_new_content and chapter_note:
                    # 構建註記信息
                    new_items = []
                    if result.get("new_characters"):
                        char_names = [char.get("name", "") for char in result.get("new_characters", []) if char.get("name", "")]
                        if char_names:
                            new_items.append(f"新增角色：{', '.join(char_names)}")
                    
                    if result.get("new_settings"):
                        setting_names = [setting.get("name", "") for setting in result.get("new_settings", []) if setting.get("name", "")]
                        if setting_names:
                            new_items.append(f"新增場景：{', '.join(setting_names)}")
                    
                    if result.get("new_terms"):
                        term_names = [term.get("term", "") for term in result.get("new_terms", []) if term.get("term", "")]
                        if term_names:
                            new_items.append(f"新增名詞：{', '.join(term_names)}")
                    
                    if result.get("plot_points"):
                        new_items.append(f"新增情節點：{len(result.get('plot_points', []))}個")
                    
                    if new_items:
                        note_content = f"{chapter_note} - {'; '.join(new_items)}"
                        self.project.world_building.chapter_notes.append(note_content)
        
        except Exception as e:
            logger.warning(f"世界設定更新失敗: {str(e)}")
    
    def _get_world_context(self) -> str:
        """獲取世界設定上下文"""
        world = self.project.world_building
        context = []
        
        if world.characters:
            context.append("人物設定：")
            for name, desc in world.characters.items():
                context.append(f"- {name}: {desc}")
        
        if world.settings:
            context.append("場景設定：")
            for name, desc in world.settings.items():
                context.append(f"- {name}: {desc}")
        
        if world.terminology:
            context.append("專有名詞：")
            for term, desc in world.terminology.items():
                context.append(f"- {term}: {desc}")
        
        return "\n".join(context)
    
    def _get_world_summary(self) -> str:
        """獲取世界設定簡要總結"""
        world = self.project.world_building
        summary = []
        
        if world.characters:
            char_names = list(world.characters.keys())
            summary.append(f"已知角色：{', '.join(char_names[:10])}")
        
        if world.settings:
            setting_names = list(world.settings.keys())
            summary.append(f"已知場景：{', '.join(setting_names[:8])}")
        
        if world.terminology:
            term_names = list(world.terminology.keys())
            summary.append(f"已知名詞：{', '.join(term_names[:8])}")
        
        return "\n".join(summary) if summary else "目前設定檔為空"
    
    def _get_previous_paragraphs_content(self, chapter_index: int, paragraph_index: int) -> str:
        """獲取前面段落的內容"""
        chapter = self.project.chapters[chapter_index]
        content = []
        
        # 只需要提供最近1-2個段落的完整內容
        start_index = max(0, paragraph_index - 2)
        
        for i in range(start_index, paragraph_index):
            paragraph = chapter.paragraphs[i]
            if paragraph.content:
                content.append(f"===== 第{i+1}段（已完成）=====\n{paragraph.content}")
        
        return "\n\n".join(content)
    
    def _get_language_instruction(self, language: str, use_traditional_quotes: bool) -> str:
        """獲取語言指令"""
        language_instructions = {
            "zh-TW": "請使用繁體中文寫作",
            "zh-CN": "請使用簡體中文寫作", 
            "en-US": "Please write in English",
            "ja-JP": "日本語で書いてください"
        }
        
        base_instruction = language_instructions.get(language, "請使用繁體中文寫作")
        
        if language.startswith("zh"):  # 中文
            if use_traditional_quotes:
                quote_instruction = "，對話請使用中文引號「」格式"
            else:
                quote_instruction = "，對話請使用英文引號\"\"格式"
        else:  # 其他語言
            quote_instruction = ', use appropriate quotation marks for dialogue'
        
        formatting_instruction = "。請確保內容分段清晰，每個句子後適當換行，避免所有文字擠在一起。" if language.startswith("zh") else ". Please ensure clear paragraph breaks and proper line spacing."
        
        return base_instruction + quote_instruction + formatting_instruction

class NovelWriterGUI:
    """小說編寫器GUI - 重構版"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("階層式LLM小說創作工具 v3.0 (重構版)")
        self.root.geometry("1400x900")
        
        # 初始化項目
        self.project = NovelProject()
        
        # 當前狀態
        self.current_action = ""
        self.selected_context_content = ""  # 存儲選中的上下文內容
        
        # 先設置UI
        self.setup_ui()
        
        # 然後載入配置和初始化服務
        self.load_api_config()
        self.api_connector = APIConnector(self.project.api_config)
        self.llm_service = LLMService(self.api_connector, self.debug_log)
        self.core = NovelWriterCore(self.project, self.llm_service)
    
    def tree_callback(self, event_type: str, data: Any):
        """樹視圖回調函數，處理生成階段的樹視圖更新"""
        try:
            if event_type == "outline_generated":
                self.debug_log("🌳 大綱生成完成，刷新樹視圖")
                self.root.after(0, self.refresh_tree)
                
            elif event_type == "chapters_generated":
                self.debug_log(f"🌳 章節劃分完成，共{len(data)}章，刷新樹視圖")
                self.root.after(0, self.refresh_tree)
                
            elif event_type == "chapter_outline_generated":
                chapter_index = data.get("chapter_index", 0)
                self.debug_log(f"🌳 第{chapter_index+1}章大綱生成完成，刷新樹視圖")
                self.root.after(0, self.refresh_tree)
                
            elif event_type == "paragraphs_generated":
                chapter_index = data.get("chapter_index", 0)
                paragraphs = data.get("paragraphs", [])
                self.debug_log(f"🌳 第{chapter_index+1}章段落劃分完成，共{len(paragraphs)}段，刷新樹視圖")
                self.root.after(0, self.refresh_tree)
                
            elif event_type == "paragraph_written":
                chapter_index = data.get("chapter_index", 0)
                paragraph_index = data.get("paragraph_index", 0)
                self.debug_log(f"🌳 第{chapter_index+1}章第{paragraph_index+1}段寫作完成，刷新樹視圖")
                self.root.after(0, self.refresh_tree)
                
        except Exception as e:
            self.debug_log(f"❌ 樹視圖回調處理失敗: {str(e)}")
    
    def setup_ui(self):
        """設置UI"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側控制面板
        left_panel = ttk.Frame(main_frame, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # 中間階層樹視圖
        tree_panel = ttk.Frame(main_frame, width=300)
        tree_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        tree_panel.pack_propagate(False)
        
        # 右側工作區域
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)  # 先設置右側面板，確保debug_text被初始化
        self.setup_tree_panel(tree_panel)    # 再設置樹面板
    
    def setup_left_panel(self, parent):
        """設置左側控制面板"""
        # 創建主容器
        main_container = ttk.Frame(parent)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 創建滾動框架 - 改進版本
        canvas = tk.Canvas(main_container, highlightthickness=0, bg='SystemButtonFace')
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置滾動區域
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 確保內容寬度填滿可用空間
            canvas_width = canvas.winfo_width()
            if canvas_width > 1:  # 確保canvas已經渲染
                canvas.itemconfig(canvas_window, width=canvas_width)
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_scroll_region)
        
        # 創建窗口並獲取引用
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 綁定滑鼠滾輪事件 - 改進版本
        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_mousewheel(widget):
            """遞歸綁定滑鼠滾輪事件到所有子控件"""
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel(child)
        
        # 延遲綁定滑鼠滾輪事件
        def delayed_bind():
            bind_mousewheel(scrollable_frame)
            bind_mousewheel(canvas)
        
        parent.after(100, delayed_bind)
        
        # 配置佈局 - 滾動條只在需要時顯示
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 檢查是否需要滾動條
        def check_scrollbar_needed():
            if canvas.winfo_exists() and scrollable_frame.winfo_exists():
                canvas.update_idletasks()
                canvas_height = canvas.winfo_height()
                content_height = scrollable_frame.winfo_reqheight()
                
                if content_height > canvas_height:
                    if not scrollbar.winfo_viewable():
                        scrollbar.pack(side="right", fill="y")
                else:
                    if scrollbar.winfo_viewable():
                        scrollbar.pack_forget()
        
        # 定期檢查是否需要滾動條
        def periodic_check():
            try:
                check_scrollbar_needed()
                parent.after(500, periodic_check)
            except tk.TclError:
                pass  # 窗口已關閉
        
        parent.after(200, periodic_check)
        
        # 項目信息 - 更緊湊
        project_frame = ttk.LabelFrame(scrollable_frame, text="項目信息", padding=5)
        project_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 標題和主題使用網格佈局
        ttk.Label(project_frame, text="標題:", font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.title_entry = ttk.Entry(project_frame, font=("Microsoft YaHei", 9))
        self.title_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=1)
        
        ttk.Label(project_frame, text="主題:", font=("Microsoft YaHei", 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.theme_entry = ttk.Entry(project_frame, font=("Microsoft YaHei", 9))
        self.theme_entry.grid(row=1, column=1, sticky=tk.W+tk.E, pady=1)
        
        project_frame.columnconfigure(1, weight=1)
        
        # API配置和創作流程合併
        main_control_frame = ttk.LabelFrame(scrollable_frame, text="主要控制", padding=5)
        main_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # API配置按鈕
        ttk.Button(main_control_frame, text="配置API", command=self.configure_api).pack(fill=tk.X, pady=(0, 3))
        
        # 主要流程按鈕 - 水平排列
        main_buttons_frame = ttk.Frame(main_control_frame)
        main_buttons_frame.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Button(main_buttons_frame, text="1.大綱", 
                  command=self.generate_outline, width=8).pack(side=tk.LEFT, padx=(0, 1))
        ttk.Button(main_buttons_frame, text="2.章節", 
                  command=self.divide_chapters, width=8).pack(side=tk.LEFT, padx=(0, 1))
        ttk.Button(main_buttons_frame, text="3.寫作", 
                  command=self.start_writing, width=8).pack(side=tk.LEFT)
        
        # 額外指示區域 - 可摺疊
        self.show_prompts = tk.BooleanVar(value=False)
        prompt_toggle = ttk.Checkbutton(main_control_frame, text="額外指示", 
                                       variable=self.show_prompts, command=self.toggle_prompt_area)
        prompt_toggle.pack(anchor=tk.W, pady=(3, 0))
        
        self.prompt_area = ttk.Frame(main_control_frame)
        # 初始隱藏
        
        # 大綱和章節指示使用標籤頁
        prompt_notebook = ttk.Notebook(self.prompt_area)
        prompt_notebook.pack(fill=tk.X, pady=(3, 0))
        
        # 大綱指示頁面
        outline_prompt_frame = ttk.Frame(prompt_notebook)
        prompt_notebook.add(outline_prompt_frame, text="大綱")
        self.outline_prompt_entry = tk.Text(outline_prompt_frame, height=3, wrap=tk.WORD, font=("Microsoft YaHei", 8))
        self.outline_prompt_entry.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 章節指示頁面
        chapters_prompt_frame = ttk.Frame(prompt_notebook)
        prompt_notebook.add(chapters_prompt_frame, text="章節")
        self.chapters_prompt_entry = tk.Text(chapters_prompt_frame, height=3, wrap=tk.WORD, font=("Microsoft YaHei", 8))
        self.chapters_prompt_entry.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 選擇和寫作控制合併
        work_frame = ttk.LabelFrame(scrollable_frame, text="寫作控制", padding=5)
        work_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 章節和段落選擇 - 網格佈局
        ttk.Label(work_frame, text="章節:", font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.chapter_var = tk.StringVar()
        self.chapter_combo = ttk.Combobox(work_frame, textvariable=self.chapter_var, 
                                         state="readonly", font=("Microsoft YaHei", 8))
        self.chapter_combo.grid(row=0, column=1, sticky=tk.W+tk.E, pady=1)
        self.chapter_combo.bind('<<ComboboxSelected>>', self.on_chapter_selected)
        
        ttk.Label(work_frame, text="段落:", font=("Microsoft YaHei", 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.paragraph_var = tk.StringVar()
        self.paragraph_combo = ttk.Combobox(work_frame, textvariable=self.paragraph_var,
                                           state="readonly", font=("Microsoft YaHei", 8))
        self.paragraph_combo.grid(row=1, column=1, sticky=tk.W+tk.E, pady=1)
        
        work_frame.columnconfigure(1, weight=1)
        
        # 寫作按鈕 - 水平排列
        write_buttons_frame = ttk.Frame(work_frame)
        write_buttons_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E, pady=(3, 0))
        
        ttk.Button(write_buttons_frame, text="寫作", 
                  command=self.write_current_paragraph, width=10).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(write_buttons_frame, text="智能寫作", 
                  command=self.enhanced_write_paragraph, width=10).pack(side=tk.LEFT)
        
        # 自動寫作控制 - 緊湊佈局
        auto_frame = ttk.LabelFrame(scrollable_frame, text="自動寫作", padding=5)
        auto_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.auto_writing = False
        self.auto_writing_mode = "normal"  # "normal" 或 "enhanced"
        
        # 自動寫作按鈕 - 水平排列
        auto_buttons_frame = ttk.Frame(auto_frame)
        auto_buttons_frame.pack(fill=tk.X, pady=(0, 2))
        
        self.auto_button = ttk.Button(auto_buttons_frame, text="自動寫作", 
                                     command=self.toggle_auto_writing, width=12)
        self.auto_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.smart_auto_button = ttk.Button(auto_buttons_frame, text="智能自動寫作", 
                                           command=self.toggle_smart_auto_writing, width=12)
        self.smart_auto_button.pack(side=tk.LEFT)
        
        # 自動寫作設置 - 水平排列
        settings_frame = ttk.Frame(auto_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 2))
        
        ttk.Label(settings_frame, text="延遲:", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="2")
        delay_spinbox = ttk.Spinbox(settings_frame, from_=1, to=10, width=4, 
                                   textvariable=self.delay_var, font=("Microsoft YaHei", 9))
        delay_spinbox.pack(side=tk.LEFT, padx=(3, 2))
        ttk.Label(settings_frame, text="秒", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        
        # 進度顯示
        self.progress_var = tk.StringVar(value="準備就緒")
        ttk.Label(auto_frame, textvariable=self.progress_var, 
                 font=("Microsoft YaHei", 8), foreground="blue").pack(fill=tk.X)
        
        # 快速設定 - 更緊湊
        quick_frame = ttk.LabelFrame(scrollable_frame, text="快速設定", padding=5)
        quick_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 使用網格佈局
        ttk.Label(quick_frame, text="敘述:", font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 3))
        self.quick_style_var = tk.StringVar(value="第三人稱限制視角")
        style_combo = ttk.Combobox(quick_frame, textvariable=self.quick_style_var,
                                  values=["第一人稱", "第三人稱限制視角", "第三人稱全知視角"],
                                  state="readonly", font=("Microsoft YaHei", 8))
        style_combo.grid(row=0, column=1, sticky=tk.W+tk.E, pady=1)
        style_combo.bind('<<ComboboxSelected>>', self.on_quick_style_change)
        
        ttk.Label(quick_frame, text="篇幅:", font=("Microsoft YaHei", 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 3))
        self.quick_length_var = tk.StringVar(value="適中")
        length_combo = ttk.Combobox(quick_frame, textvariable=self.quick_length_var,
                                   values=["簡潔", "適中", "詳細"],
                                   state="readonly", font=("Microsoft YaHei", 8))
        length_combo.grid(row=1, column=1, sticky=tk.W+tk.E, pady=1)
        length_combo.bind('<<ComboboxSelected>>', self.on_quick_length_change)
        
        quick_frame.columnconfigure(1, weight=1)
        
        # 段落控制 - 可摺疊，更緊湊
        self.dynamic_frame = ttk.LabelFrame(scrollable_frame, text="段落控制", padding=5)
        self.dynamic_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.show_advanced = tk.BooleanVar(value=False)
        advanced_toggle = ttk.Checkbutton(self.dynamic_frame, text="高級選項", 
                                         variable=self.show_advanced, command=self.toggle_advanced_area)
        advanced_toggle.pack(anchor=tk.W, pady=(0, 2))
        
        self.advanced_area = ttk.Frame(self.dynamic_frame)
        # 初始隱藏
        
        # 特別要求
        ttk.Label(self.advanced_area, text="特別要求:", font=("Microsoft YaHei", 9)).pack(anchor=tk.W)
        self.current_paragraph_prompt = tk.Text(self.advanced_area, height=2, wrap=tk.WORD, font=("Microsoft YaHei", 8))
        self.current_paragraph_prompt.pack(fill=tk.X, pady=(0, 2))
        
        # 參考和字數控制 - 網格佈局
        control_grid_frame = ttk.Frame(self.advanced_area)
        control_grid_frame.pack(fill=tk.X, pady=(0, 2))
        
        # 參考內容
        ttk.Label(control_grid_frame, text="參考:", font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 3))
        ref_buttons_frame = ttk.Frame(control_grid_frame)
        ref_buttons_frame.grid(row=0, column=1, sticky=tk.W+tk.E)
        ttk.Button(ref_buttons_frame, text="使用選中", 
                  command=self.use_selected_as_reference, width=8).pack(side=tk.LEFT, padx=(0, 1))
        ttk.Button(ref_buttons_frame, text="清除", 
                  command=self.clear_reference, width=6).pack(side=tk.LEFT)
        
        # 字數控制
        ttk.Label(control_grid_frame, text="字數:", font=("Microsoft YaHei", 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 3))
        words_frame = ttk.Frame(control_grid_frame)
        words_frame.grid(row=1, column=1, sticky=tk.W+tk.E)
        
        self.target_words_var = tk.StringVar(value="300")
        words_spinbox = ttk.Spinbox(words_frame, from_=100, to=1000, width=6,
                                   textvariable=self.target_words_var, font=("Microsoft YaHei", 9))
        words_spinbox.pack(side=tk.LEFT, padx=(0, 3))
        
        self.strict_words_var = tk.BooleanVar()
        ttk.Checkbutton(words_frame, text="嚴格", 
                       variable=self.strict_words_var).pack(side=tk.LEFT)
        
        control_grid_frame.columnconfigure(1, weight=1)
        
        # 重寫優化按鈕
        ttk.Button(self.advanced_area, text="重寫優化", 
                  command=self.rewrite_with_optimization).pack(fill=tk.X, pady=(2, 0))
        
        # 配置和文件操作合併
        tools_frame = ttk.LabelFrame(scrollable_frame, text="工具", padding=5)
        tools_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 配置按鈕 - 水平排列
        config_buttons_frame = ttk.Frame(tools_frame)
        config_buttons_frame.pack(fill=tk.X, pady=(0, 2))
        
        ttk.Button(config_buttons_frame, text="全局設定", 
                  command=self.open_global_config, width=12).pack(side=tk.LEFT, padx=(0, 1))
        ttk.Button(config_buttons_frame, text="階段配置", 
                  command=self.open_stage_configs, width=12).pack(side=tk.LEFT)
        
        # 文件操作按鈕 - 水平排列
        file_buttons_frame = ttk.Frame(tools_frame)
        file_buttons_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Button(file_buttons_frame, text="保存", command=self.save_project, width=8).pack(side=tk.LEFT, padx=(0, 1))
        ttk.Button(file_buttons_frame, text="載入", command=self.load_project, width=8).pack(side=tk.LEFT, padx=(0, 1))
        ttk.Button(file_buttons_frame, text="導出", command=self.export_novel, width=8).pack(side=tk.LEFT)
    
    def setup_tree_panel(self, parent):
        """設置階層樹視圖面板"""
        # 樹視圖標題
        tree_frame = ttk.LabelFrame(parent, text="小說結構樹", padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 創建樹視圖
        self.tree = ttk.Treeview(tree_frame, show="tree headings", height=20)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # 添加滾動條
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 設置列
        self.tree["columns"] = ("status", "words")
        self.tree.column("#0", width=200, minwidth=150)
        self.tree.column("status", width=80, minwidth=60)
        self.tree.column("words", width=60, minwidth=50)
        
        # 設置標題
        self.tree.heading("#0", text="內容", anchor=tk.W)
        self.tree.heading("status", text="狀態", anchor=tk.CENTER)
        self.tree.heading("words", text="字數", anchor=tk.CENTER)
        
        # 綁定事件
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
        # 右鍵菜單
        self.tree_menu = tk.Menu(self.tree, tearoff=0)
        self.tree_menu.add_command(label="編輯內容", command=self.edit_selected_content)
        self.tree_menu.add_command(label="重新生成", command=self.regenerate_selected_content)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="添加章節", command=self.add_chapter_node)
        self.tree_menu.add_command(label="添加段落", command=self.add_paragraph_node)
        self.tree_menu.add_command(label="刪除節點", command=self.delete_selected_node)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="展開全部", command=self.expand_all_tree)
        self.tree_menu.add_command(label="收起全部", command=self.collapse_all_tree)
        
        self.tree.bind("<Button-3>", self.show_tree_menu)
        
        # 操作按鈕框架
        button_frame = ttk.Frame(tree_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="刷新樹", command=self.refresh_tree).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="編輯", command=self.edit_selected_content).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="重新生成", command=self.regenerate_selected_content).pack(side=tk.LEFT)
        
        # 手動操作按鈕
        manual_frame = ttk.Frame(tree_frame)
        manual_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(manual_frame, text="添加章節", command=self.add_chapter_node).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_frame, text="添加段落", command=self.add_paragraph_node).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_frame, text="刪除節點", command=self.delete_selected_node).pack(side=tk.LEFT)
        
        # 初始化預設樹結構
        self.initialize_default_tree()
    
    def setup_right_panel(self, parent):
        """設置右側工作區域"""
        # 創建筆記本控件
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 內容編輯頁面
        content_frame = ttk.Frame(self.notebook)
        self.notebook.add(content_frame, text="內容編輯")
        
        self.content_text = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD, 
                                                     font=("Microsoft YaHei", 12))
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 調試日誌頁面
        debug_frame = ttk.Frame(self.notebook)
        self.notebook.add(debug_frame, text="調試日誌")
        
        self.debug_text = scrolledtext.ScrolledText(debug_frame, wrap=tk.WORD,
                                                   font=("Consolas", 10))
        self.debug_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 世界設定頁面
        world_frame = ttk.Frame(self.notebook)
        self.notebook.add(world_frame, text="世界設定")
        
        # 世界設定控制按鈕框架
        world_control_frame = ttk.Frame(world_frame)
        world_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(world_control_frame, text="保存修改", 
                  command=self.save_world_settings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(world_control_frame, text="重置設定", 
                  command=self.reset_world_settings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(world_control_frame, text="刷新顯示", 
                  command=self.update_world_display).pack(side=tk.LEFT)
        
        # 添加分隔線
        ttk.Separator(world_frame, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)
        
        self.world_text = scrolledtext.ScrolledText(world_frame, wrap=tk.WORD,
                                                   font=("Microsoft YaHei", 11))
        self.world_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def debug_log(self, message):
        """添加調試日誌"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.debug_text.insert(tk.END, log_message)
        self.debug_text.see(tk.END)
        self.root.update_idletasks()
    
    def load_api_config(self):
        """載入API配置"""
        try:
            if os.path.exists("api_config.json"):
                with open("api_config.json", "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    
                self.project.api_config.base_url = config_data.get("base_url", "https://api.openai.com/v1")
                self.project.api_config.model = config_data.get("model", "gpt-4.1-mini-2025-04-14")
                self.project.api_config.provider = config_data.get("provider", "openai")
                self.project.api_config.api_key = config_data.get("api_key", "")
                self.project.api_config.max_retries = config_data.get("max_retries", 3)
                self.project.api_config.timeout = config_data.get("timeout", 60)
                self.project.api_config.language = config_data.get("language", "zh-TW")
                self.project.api_config.use_traditional_quotes = config_data.get("use_traditional_quotes", True)
                self.project.api_config.disable_thinking = config_data.get("disable_thinking", False)
                
                self.debug_log("✅ API配置載入成功")
            else:
                self.debug_log("⚠️ 未找到API配置文件，使用默認配置")
        except Exception as e:
            self.debug_log(f"❌ 載入API配置失敗: {str(e)}")
    
    def configure_api(self):
        """配置API"""
        config_window = tk.Toplevel(self.root)
        config_window.title("API配置")
        config_window.geometry("500x550")
        config_window.transient(self.root)
        config_window.grab_set()
        
        # API提供商
        ttk.Label(config_window, text="API提供商:").pack(anchor=tk.W, padx=10, pady=5)
        provider_var = tk.StringVar(value=self.project.api_config.provider)
        provider_combo = ttk.Combobox(config_window, textvariable=provider_var,
                                     values=["openai", "anthropic", "ollama", "lm-studio", "localai", "text-generation-webui", "vllm", "custom"])
        provider_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # 預設配置按鈕框架
        preset_frame = ttk.Frame(config_window)
        preset_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(preset_frame, text="快速預設:").pack(side=tk.LEFT)
        ttk.Button(preset_frame, text="Ollama", command=lambda: self.apply_preset("ollama", url_var, model_var, provider_var)).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Button(preset_frame, text="OpenAI", command=lambda: self.apply_preset("openai", url_var, model_var, provider_var)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Anthropic", command=lambda: self.apply_preset("anthropic", url_var, model_var, provider_var)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Openrouter", command=lambda: self.apply_preset("openrouter", url_var, model_var, provider_var)).pack(side=tk.LEFT, padx=2)
        
        # API地址
        ttk.Label(config_window, text="API地址:").pack(anchor=tk.W, padx=10, pady=5)
        url_var = tk.StringVar(value=self.project.api_config.base_url)
        url_entry = ttk.Entry(config_window, textvariable=url_var)
        url_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # 模型
        ttk.Label(config_window, text="模型:").pack(anchor=tk.W, padx=10, pady=5)
        model_var = tk.StringVar(value=self.project.api_config.model)
        model_entry = ttk.Entry(config_window, textvariable=model_var)
        model_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # API密鑰
        ttk.Label(config_window, text="API密鑰:").pack(anchor=tk.W, padx=10, pady=5)
        key_var = tk.StringVar(value=self.project.api_config.api_key)
        key_entry = ttk.Entry(config_window, textvariable=key_var, show="*")
        key_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # 分隔線
        ttk.Separator(config_window, orient='horizontal').pack(fill=tk.X, padx=10, pady=10)
        
        # 語言設定
        ttk.Label(config_window, text="輸出語言:").pack(anchor=tk.W, padx=10, pady=5)
        language_var = tk.StringVar(value=self.project.api_config.language)
        language_combo = ttk.Combobox(config_window, textvariable=language_var,
                                     values=["zh-TW", "zh-CN", "en-US", "ja-JP"])
        language_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # 引號格式設定
        quote_var = tk.BooleanVar(value=self.project.api_config.use_traditional_quotes)
        quote_check = ttk.Checkbutton(config_window, text="使用中文引號「」（取消則使用英文引號\"\"）", 
                                     variable=quote_var)
        quote_check.pack(anchor=tk.W, padx=10, pady=5)
        
        # 關閉thinking設定
        thinking_var = tk.BooleanVar(value=self.project.api_config.disable_thinking)
        thinking_check = ttk.Checkbutton(config_window, text="關閉thinking模式（啟用後傳送thinking: false參數）", 
                                        variable=thinking_var)
        thinking_check.pack(anchor=tk.W, padx=10, pady=5)
        
        def save_config():
            self.project.api_config.provider = provider_var.get()
            self.project.api_config.base_url = url_var.get()
            self.project.api_config.model = model_var.get()
            self.project.api_config.api_key = key_var.get()
            self.project.api_config.language = language_var.get()
            self.project.api_config.use_traditional_quotes = quote_var.get()
            self.project.api_config.disable_thinking = thinking_var.get()
            
            # 保存到文件
            config_data = {
                "provider": self.project.api_config.provider,
                "base_url": self.project.api_config.base_url,
                "model": self.project.api_config.model,
                "api_key": self.project.api_config.api_key,
                "max_retries": self.project.api_config.max_retries,
                "timeout": self.project.api_config.timeout,
                "language": self.project.api_config.language,
                "use_traditional_quotes": self.project.api_config.use_traditional_quotes,
                "disable_thinking": self.project.api_config.disable_thinking
            }
            
            with open("api_config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # 重新初始化服務
            self.api_connector = APIConnector(self.project.api_config)
            self.llm_service = LLMService(self.api_connector, self.debug_log)
            self.core = NovelWriterCore(self.project, self.llm_service)
            
            self.debug_log("✅ API配置已保存")
            config_window.destroy()
        
        ttk.Button(config_window, text="保存", command=save_config).pack(pady=20)
    
    def apply_preset(self, preset_type, url_var, model_var, provider_var):
        """應用預設配置"""
        presets = {
            "ollama": {
                "provider": "custom",
                "base_url": "http://localhost:11434/v1",
                "model": "gemma3:12b-it-qat",
                "description": "Ollama 本地模型服務"
            },
            "openai": {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4.1-mini-2025-04-14",
                "description": "OpenAI 官方服務"
            },
            "anthropic": {
                "provider": "anthropic",
                "base_url": "https://api.anthropic.com",
                "model": "claude-sonnet-4-20250514",
                "description": "Anthropic Claude 服務"
            },
            "openrouter": {
                "provider": "custom",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "deepseek/deepseek-chat-v3-0324",
                "description": "OpenRouter 聚合服務"
            }
        }
        
        if preset_type in presets:
            preset = presets[preset_type]
            
            # 更新UI控件的值
            provider_var.set(preset["provider"])
            url_var.set(preset["base_url"])
            model_var.set(preset["model"])
            
            # 顯示提示信息
            messagebox.showinfo("預設配置", 
                f"已應用 {preset['description']} 的預設配置：\n\n"
                f"API地址：{preset['base_url']}\n"
                f"模型：{preset['model']}\n\n"
                f"請確認設定後點擊保存。")
            
            self.debug_log(f"✅ 已應用 {preset['description']} 預設配置")
    
    def generate_outline(self):
        """生成大綱"""
        if not self.title_entry.get().strip():
            messagebox.showerror("錯誤", "請先輸入小說標題")
            return
        
        if not self.theme_entry.get().strip():
            messagebox.showerror("錯誤", "請先輸入主題/風格")
            return
        
        self.project.title = self.title_entry.get().strip()
        self.project.theme = self.theme_entry.get().strip()
        
        # 保存額外指示到項目數據中
        self.project.outline_additional_prompt = self.outline_prompt_entry.get("1.0", tk.END).strip()
        
        def run_task():
            try:
                self.current_action = "正在生成大綱..."
                self.debug_log("🚀 開始生成大綱")
                
                # 獲取額外的prompt指示
                additional_prompt = self.project.outline_additional_prompt
                if additional_prompt:
                    self.debug_log(f"📝 使用額外指示: {additional_prompt}")
                
                result = self.core.generate_outline(additional_prompt, self.tree_callback)
                
                if result:
                    self.content_text.delete(1.0, tk.END)
                    self.content_text.insert(tk.END, self.project.outline)
                    self.update_world_display()
                    self.debug_log("✅ 大綱生成完成")
                    messagebox.showinfo("成功", "大綱生成完成！")
                else:
                    self.debug_log("❌ 大綱生成失敗")
                    messagebox.showerror("錯誤", "大綱生成失敗")
                    
            except Exception as e:
                self.debug_log(f"❌ 生成大綱時發生錯誤: {str(e)}")
                messagebox.showerror("錯誤", f"生成大綱失敗: {str(e)}")
            finally:
                self.current_action = ""
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def divide_chapters(self):
        """劃分章節"""
        if not self.project.outline:
            messagebox.showerror("錯誤", "請先生成大綱")
            return
        
        # 保存額外指示到項目數據中
        self.project.chapters_additional_prompt = self.chapters_prompt_entry.get("1.0", tk.END).strip()
        
        def run_task():
            try:
                self.current_action = "正在劃分章節..."
                self.debug_log("🚀 開始劃分章節")
                
                # 獲取額外的prompt指示
                additional_prompt = self.project.chapters_additional_prompt
                if additional_prompt:
                    self.debug_log(f"📝 使用額外指示: {additional_prompt}")
                
                chapters = self.core.divide_chapters(additional_prompt, self.tree_callback)
                
                if chapters:
                    self.update_chapter_list()
                    self.debug_log(f"✅ 章節劃分完成，共{len(chapters)}章")
                    messagebox.showinfo("成功", f"章節劃分完成！共{len(chapters)}章")
                else:
                    self.debug_log("❌ 章節劃分失敗")
                    messagebox.showerror("錯誤", "章節劃分失敗")
                    
            except Exception as e:
                self.debug_log(f"❌ 劃分章節時發生錯誤: {str(e)}")
                messagebox.showerror("錯誤", f"劃分章節失敗: {str(e)}")
            finally:
                self.current_action = ""
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def start_writing(self):
        """開始寫作"""
        if not self.project.chapters:
            messagebox.showerror("錯誤", "請先劃分章節")
            return
        
        messagebox.showinfo("提示", "請選擇章節，然後點擊相應的寫作按鈕開始創作")
    
    def update_chapter_list(self):
        """更新章節列表"""
        chapter_list = []
        for i, chapter in enumerate(self.project.chapters):
            chapter_list.append(f"第{i+1}章: {chapter.title}")
        
        self.chapter_combo['values'] = chapter_list
        if chapter_list:
            self.chapter_combo.current(0)
            self.on_chapter_selected(None)
    
    def on_chapter_selected(self, event):
        """章節選擇事件"""
        if not self.chapter_var.get():
            return
        
        chapter_index = self.chapter_combo.current()
        if chapter_index < 0 or chapter_index >= len(self.project.chapters):
            return
        
        chapter = self.project.chapters[chapter_index]
        
        # 如果章節還沒有段落，先生成章節大綱和段落劃分
        if not chapter.paragraphs:
            def run_task():
                try:
                    self.debug_log(f"🚀 為第{chapter_index+1}章生成大綱和段落")
                    
                    # 生成章節大綱
                    self.core.generate_chapter_outline(chapter_index)
                    
                    # 劃分段落
                    self.core.divide_paragraphs(chapter_index)
                    
                    # 更新段落列表
                    self.root.after(0, self.update_paragraph_list)
                    
                    self.debug_log(f"✅ 第{chapter_index+1}章準備完成")
                    
                except Exception as e:
                    self.debug_log(f"❌ 準備第{chapter_index+1}章時發生錯誤: {str(e)}")
            
            threading.Thread(target=run_task, daemon=True).start()
        else:
            self.update_paragraph_list()
    
    def update_paragraph_list(self):
        """更新段落列表"""
        chapter_index = self.chapter_combo.current()
        if chapter_index < 0 or chapter_index >= len(self.project.chapters):
            return
        
        chapter = self.project.chapters[chapter_index]
        paragraph_list = []
        
        for i, paragraph in enumerate(chapter.paragraphs):
            status = paragraph.status.value
            paragraph_list.append(f"第{i+1}段: {paragraph.purpose} [{status}]")
        
        self.paragraph_combo['values'] = paragraph_list
        if paragraph_list:
            self.paragraph_combo.current(0)
    
    def write_current_paragraph(self):
        """寫作當前段落"""
        chapter_index = self.chapter_combo.current()
        paragraph_index = self.paragraph_combo.current()
        
        if chapter_index < 0 or paragraph_index < 0:
            messagebox.showerror("錯誤", "請先選擇章節和段落")
            return
        
        def run_task():
            try:
                self.current_action = f"正在寫作第{chapter_index+1}章第{paragraph_index+1}段..."
                self.debug_log(f"🚀 開始寫作第{chapter_index+1}章第{paragraph_index+1}段")
                
                content = self.core.write_paragraph(chapter_index, paragraph_index, self.tree_callback, self.selected_context_content)
                
                if content:
                    self.root.after(0, lambda: self.display_paragraph_content(content))
                    self.root.after(0, self.update_paragraph_list)
                    self.root.after(0, self.update_world_display)
                    self.debug_log(f"✅ 第{chapter_index+1}章第{paragraph_index+1}段寫作完成")
                else:
                    self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段寫作失敗")
                    
            except Exception as e:
                self.debug_log(f"❌ 寫作段落時發生錯誤: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("錯誤", f"寫作失敗: {str(e)}"))
            finally:
                self.current_action = ""
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def display_paragraph_content(self, content):
        """顯示段落內容"""
        self.content_text.delete(1.0, tk.END)
        self.content_text.insert(tk.END, content)
        self.notebook.select(0)  # 切換到內容編輯頁面
    
    def update_world_display(self):
        """更新世界設定顯示"""
        world = self.project.world_building
        content = []
        
        if world.characters:
            content.append("=== 人物設定 ===")
            for name, desc in world.characters.items():
                content.append(f"{name}: {desc}")
            content.append("")
        
        if world.settings:
            content.append("=== 場景設定 ===")
            for name, desc in world.settings.items():
                content.append(f"{name}: {desc}")
            content.append("")
        
        if world.terminology:
            content.append("=== 專有名詞 ===")
            for term, desc in world.terminology.items():
                content.append(f"{term}: {desc}")
            content.append("")
        
        if world.plot_points:
            content.append("=== 重要情節點 ===")
            for point in world.plot_points:
                content.append(f"• {point}")
            content.append("")
        
        if world.chapter_notes:
            content.append("=== 章節註記 ===")
            for note in world.chapter_notes:
                content.append(f"• {note}")
        
        self.world_text.delete(1.0, tk.END)
        self.world_text.insert(tk.END, "\n".join(content))
    
    def save_world_settings(self):
        """保存世界設定修改"""
        try:
            # 獲取文本框中的內容
            content = self.world_text.get("1.0", tk.END).strip()
            
            if not content:
                messagebox.showwarning("提示", "世界設定內容為空")
                return
            
            # 解析文本內容並更新世界設定
            self._parse_world_content(content)
            
            self.debug_log("✅ 世界設定已保存")
            messagebox.showinfo("成功", "世界設定修改已保存！")
            
        except Exception as e:
            self.debug_log(f"❌ 保存世界設定失敗: {str(e)}")
            messagebox.showerror("錯誤", f"保存失敗: {str(e)}")
    
    def reset_world_settings(self):
        """重置世界設定"""
        if not messagebox.askyesno("確認重置", "確定要重置所有世界設定嗎？\n此操作將清空所有人物、場景、名詞等設定，且不可撤銷。"):
            return
        
        try:
            # 重置世界設定數據
            self.project.world_building = WorldBuilding()
            
            # 更新顯示
            self.update_world_display()
            
            self.debug_log("🔄 世界設定已重置")
            messagebox.showinfo("成功", "世界設定已重置！")
            
        except Exception as e:
            self.debug_log(f"❌ 重置世界設定失敗: {str(e)}")
            messagebox.showerror("錯誤", f"重置失敗: {str(e)}")
    
    def _parse_world_content(self, content: str):
        """解析世界設定文本內容"""
        # 重置世界設定
        world = WorldBuilding()
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 檢查是否是章節標題
            if line.startswith("=== ") and line.endswith(" ==="):
                section_name = line[4:-4].strip()
                if section_name == "人物設定":
                    current_section = "characters"
                elif section_name == "場景設定":
                    current_section = "settings"
                elif section_name == "專有名詞":
                    current_section = "terminology"
                elif section_name == "重要情節點":
                    current_section = "plot_points"
                elif section_name == "章節註記":
                    current_section = "chapter_notes"
                else:
                    current_section = None
                continue
            
            # 根據當前章節解析內容
            if current_section == "characters":
                if ":" in line:
                    name, desc = line.split(":", 1)
                    world.characters[name.strip()] = desc.strip()
            
            elif current_section == "settings":
                if ":" in line:
                    name, desc = line.split(":", 1)
                    world.settings[name.strip()] = desc.strip()
            
            elif current_section == "terminology":
                if ":" in line:
                    term, desc = line.split(":", 1)
                    world.terminology[term.strip()] = desc.strip()
            
            elif current_section == "plot_points":
                if line.startswith("• "):
                    world.plot_points.append(line[2:].strip())
                elif line.startswith("- "):
                    world.plot_points.append(line[2:].strip())
                else:
                    world.plot_points.append(line.strip())
            
            elif current_section == "chapter_notes":
                if line.startswith("• "):
                    world.chapter_notes.append(line[2:].strip())
                elif line.startswith("- "):
                    world.chapter_notes.append(line[2:].strip())
                else:
                    world.chapter_notes.append(line.strip())
        
        # 更新項目的世界設定
        self.project.world_building = world
        self.debug_log("📝 世界設定內容解析完成")
    
    def save_project(self):
        """保存項目"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                # 將項目數據轉換為可序列化的格式
                chapters_data = []
                for chapter in self.project.chapters:
                    chapter_dict = asdict(chapter)
                    # 轉換章節狀態枚舉為字符串
                    chapter_dict["status"] = chapter.status.value
                    
                    # 轉換段落狀態枚舉為字符串
                    for paragraph_dict in chapter_dict["paragraphs"]:
                        if "status" in paragraph_dict:
                            # 找到對應的段落對象來獲取狀態
                            para_index = next(i for i, p in enumerate(chapter.paragraphs) 
                                            if p.order == paragraph_dict["order"])
                            paragraph_dict["status"] = chapter.paragraphs[para_index].status.value
                    
                    chapters_data.append(chapter_dict)
                
                project_data = {
                    "title": self.project.title,
                    "theme": self.project.theme,
                    "outline": self.project.outline,
                    "outline_additional_prompt": self.project.outline_additional_prompt,
                    "chapters_additional_prompt": self.project.chapters_additional_prompt,
                    "chapters": chapters_data,
                    "world_building": asdict(self.project.world_building)
                }
                
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                
                self.debug_log(f"✅ 項目已保存到: {filename}")
                messagebox.showinfo("成功", "項目保存成功！")
                
        except Exception as e:
            self.debug_log(f"❌ 保存項目失敗: {str(e)}")
            messagebox.showerror("錯誤", f"保存失敗: {str(e)}")
    
    def load_project(self):
        """載入項目"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                # 重建項目數據
                self.project.title = project_data.get("title", "")
                self.project.theme = project_data.get("theme", "")
                self.project.outline = project_data.get("outline", "")
                self.project.outline_additional_prompt = project_data.get("outline_additional_prompt", "")
                self.project.chapters_additional_prompt = project_data.get("chapters_additional_prompt", "")
                
                # 重建章節數據
                self.project.chapters = []
                for chapter_data in project_data.get("chapters", []):
                    chapter = Chapter(
                        title=chapter_data["title"],
                        summary=chapter_data["summary"],
                        key_events=chapter_data.get("key_events", []),
                        characters_involved=chapter_data.get("characters_involved", []),
                        estimated_words=chapter_data.get("estimated_words", 3000),
                        outline=chapter_data.get("outline", {}),
                        content=chapter_data.get("content", ""),
                        status=CreationStatus(chapter_data.get("status", "未開始"))
                    )
                    
                    # 重建段落數據
                    chapter.paragraphs = []
                    for para_data in chapter_data.get("paragraphs", []):
                        paragraph = Paragraph(
                            order=para_data["order"],
                            purpose=para_data["purpose"],
                            content_type=para_data.get("content_type", ""),
                            key_points=para_data.get("key_points", []),
                            estimated_words=para_data.get("estimated_words", 0),
                            mood=para_data.get("mood", ""),
                            content=para_data.get("content", ""),
                            status=CreationStatus(para_data.get("status", "未開始")),
                            word_count=para_data.get("word_count", 0)
                        )
                        chapter.paragraphs.append(paragraph)
                    
                    self.project.chapters.append(chapter)
                
                # 重建世界設定
                world_data = project_data.get("world_building", {})
                self.project.world_building = WorldBuilding(
                    characters=world_data.get("characters", {}),
                    settings=world_data.get("settings", {}),
                    terminology=world_data.get("terminology", {}),
                    plot_points=world_data.get("plot_points", []),
                    relationships=world_data.get("relationships", []),
                    style_guide=world_data.get("style_guide", "")
                )
                
                # 更新UI
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, self.project.title)
                self.theme_entry.delete(0, tk.END)
                self.theme_entry.insert(0, self.project.theme)
                
                # 更新額外指示輸入框
                self.outline_prompt_entry.delete("1.0", tk.END)
                self.outline_prompt_entry.insert("1.0", self.project.outline_additional_prompt)
                self.chapters_prompt_entry.delete("1.0", tk.END)
                self.chapters_prompt_entry.insert("1.0", self.project.chapters_additional_prompt)
                
                if self.project.outline:
                    self.content_text.delete(1.0, tk.END)
                    self.content_text.insert(tk.END, self.project.outline)
                
                self.update_chapter_list()
                self.update_world_display()
                
                # 重要：載入項目後刷新樹狀圖
                self.refresh_tree()
                
                self.debug_log(f"✅ 項目已載入: {filename}")
                messagebox.showinfo("成功", "項目載入成功！")
                
        except Exception as e:
            self.debug_log(f"❌ 載入項目失敗: {str(e)}")
            messagebox.showerror("錯誤", f"載入失敗: {str(e)}")
    
    def export_novel(self):
        """導出小說"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                content = []
                content.append(f"《{self.project.title}》")
                content.append("=" * 50)
                content.append("")
                
                for i, chapter in enumerate(self.project.chapters):
                    content.append(f"第{i+1}章 {chapter.title}")
                    content.append("-" * 30)
                    content.append("")
                    
                    for paragraph in chapter.paragraphs:
                        if paragraph.content:
                            content.append(paragraph.content)
                            content.append("")
                    
                    content.append("")
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(content))
                
                self.debug_log(f"✅ 小說已導出到: {filename}")
                messagebox.showinfo("成功", "小說導出成功！")
                
        except Exception as e:
            self.debug_log(f"❌ 導出小說失敗: {str(e)}")
            messagebox.showerror("錯誤", f"導出失敗: {str(e)}")
    
    def toggle_auto_writing(self):
        """切換自動寫作模式"""
        if not self.auto_writing:
            # 開始自動寫作
            if not self.project.chapters:
                messagebox.showerror("錯誤", "請先劃分章節")
                return
            
            self.auto_writing = True
            self.auto_writing_mode = "normal"
            self.auto_button.config(text="停止自動寫作", style="Accent.TButton")
            self.smart_auto_button.config(state="disabled")
            self.progress_var.set("自動寫作已啟動")
            self.debug_log("🤖 自動寫作模式啟動")
            
            # 開始自動寫作線程
            threading.Thread(target=self.auto_writing_worker, daemon=True).start()
        else:
            # 停止自動寫作
            self.auto_writing = False
            self.auto_button.config(text="自動寫作", style="")
            self.smart_auto_button.config(state="normal")
            self.progress_var.set("自動寫作已停止")
            self.debug_log("⏹️ 自動寫作模式停止")
    
    def toggle_smart_auto_writing(self):
        """切換智能自動寫作模式"""
        if not self.auto_writing:
            # 開始智能自動寫作
            if not self.project.chapters:
                messagebox.showerror("錯誤", "請先劃分章節")
                return
            
            self.auto_writing = True
            self.auto_writing_mode = "enhanced"
            self.smart_auto_button.config(text="停止智能自動寫作", style="Accent.TButton")
            self.auto_button.config(state="disabled")
            self.progress_var.set("智能自動寫作已啟動")
            self.debug_log("🧠 智能自動寫作模式啟動")
            
            # 開始自動寫作線程
            threading.Thread(target=self.auto_writing_worker, daemon=True).start()
        else:
            # 停止智能自動寫作
            self.auto_writing = False
            self.smart_auto_button.config(text="智能自動寫作", style="")
            self.auto_button.config(state="normal")
            self.progress_var.set("智能自動寫作已停止")
            self.debug_log("⏹️ 智能自動寫作模式停止")
    
    def auto_writing_worker(self):
        """自動寫作工作線程"""
        try:
            delay = int(self.delay_var.get())
            
            for chapter_index, chapter in enumerate(self.project.chapters):
                if not self.auto_writing:
                    break
                
                # 更新進度顯示
                self.root.after(0, lambda ci=chapter_index: self.progress_var.set(
                    f"處理第{ci+1}章: {self.project.chapters[ci].title}"))
                
                # 確保章節有段落
                if not chapter.paragraphs:
                    self.debug_log(f"🚀 為第{chapter_index+1}章生成大綱和段落")
                    
                    try:
                        # 標記章節為進行中狀態
                        chapter.status = CreationStatus.IN_PROGRESS
                        self.root.after(0, self.refresh_tree)
                        
                        # 生成章節大綱
                        self.core.generate_chapter_outline(chapter_index, self.tree_callback)
                        
                        # 劃分段落
                        self.core.divide_paragraphs(chapter_index, self.tree_callback)
                        
                        # 更新UI和樹狀圖
                        if chapter_index == self.chapter_combo.current():
                            self.root.after(0, self.update_paragraph_list)
                        self.root.after(0, self.refresh_tree)
                        
                        self.debug_log(f"✅ 第{chapter_index+1}章準備完成")
                        
                    except Exception as e:
                        chapter.status = CreationStatus.ERROR
                        self.root.after(0, self.refresh_tree)
                        self.debug_log(f"❌ 準備第{chapter_index+1}章時發生錯誤: {str(e)}")
                        continue
                
                # 寫作所有段落
                for paragraph_index, paragraph in enumerate(chapter.paragraphs):
                    if not self.auto_writing:
                        break
                    
                    # 跳過已完成的段落
                    if paragraph.status == CreationStatus.COMPLETED:
                        continue
                    
                    # 更新進度顯示
                    self.root.after(0, lambda ci=chapter_index, pi=paragraph_index: 
                                   self.progress_var.set(f"寫作第{ci+1}章第{pi+1}段"))
                    
                    # 標記段落為進行中狀態並更新樹狀圖
                    paragraph.status = CreationStatus.IN_PROGRESS
                    self.root.after(0, self.refresh_tree)
                    
                    # 段落寫作重試機制
                    paragraph_retry_max = 2  # 段落寫作重試次數
                    paragraph_success = False
                    
                    for retry_attempt in range(paragraph_retry_max):
                        if not self.auto_writing:
                            break
                        
                        try:
                            if retry_attempt > 0:
                                self.debug_log(f"🔄 重試寫作第{chapter_index+1}章第{paragraph_index+1}段 (嘗試 {retry_attempt + 1}/{paragraph_retry_max})")
                            else:
                                self.debug_log(f"🚀 自動寫作第{chapter_index+1}章第{paragraph_index+1}段")
                            
                            # 根據模式選擇寫作方法
                            if self.auto_writing_mode == "enhanced":
                                # 智能自動寫作模式：使用增強配置
                                self.debug_log(f"🧠 使用智能寫作模式")
                                # 可以在這裡設置智能寫作的特殊配置
                                content = self.core.write_paragraph(chapter_index, paragraph_index, self.tree_callback, self.selected_context_content)
                            else:
                                # 普通自動寫作模式
                                self.debug_log(f"📝 使用普通寫作模式")
                                content = self.core.write_paragraph(chapter_index, paragraph_index, self.tree_callback)
                            
                            if content:
                                # 如果是當前選中的章節和段落，更新顯示
                                if (chapter_index == self.chapter_combo.current() and 
                                    paragraph_index == self.paragraph_combo.current()):
                                    self.root.after(0, lambda c=content: self.display_paragraph_content(c))
                                
                                # 更新段落列表
                                if chapter_index == self.chapter_combo.current():
                                    self.root.after(0, self.update_paragraph_list)
                                
                                # 更新世界設定
                                self.root.after(0, self.update_world_display)
                                
                                # 立即更新樹狀圖以顯示完成狀態
                                self.root.after(0, self.refresh_tree)
                                
                                self.debug_log(f"✅ 第{chapter_index+1}章第{paragraph_index+1}段自動寫作完成")
                                paragraph_success = True
                                
                                # 延遲
                                if self.auto_writing:
                                    import time
                                    time.sleep(delay)
                                break  # 成功後跳出重試循環
                            else:
                                self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段寫作失敗，內容為空")
                                if retry_attempt == paragraph_retry_max - 1:
                                    self.debug_log(f"⚠️ 第{chapter_index+1}章第{paragraph_index+1}段重試次數已用盡，跳過此段落")
                                    # 標記段落為錯誤狀態
                                    paragraph.status = CreationStatus.ERROR
                                    self.root.after(0, self.refresh_tree)
                                
                        except JSONParseException as e:
                            self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段JSON解析失敗: {str(e)}")
                            if retry_attempt == paragraph_retry_max - 1:
                                self.debug_log(f"⚠️ 第{chapter_index+1}章第{paragraph_index+1}段JSON解析重試次數已用盡，跳過此段落")
                                paragraph.status = CreationStatus.ERROR
                                self.root.after(0, self.refresh_tree)
                            else:
                                # JSON解析失敗時稍微延遲再重試
                                import time
                                time.sleep(1)
                                
                        except APIException as e:
                            self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段API調用失敗: {str(e)}")
                            if retry_attempt == paragraph_retry_max - 1:
                                self.debug_log(f"⚠️ 第{chapter_index+1}章第{paragraph_index+1}段API重試次數已用盡，跳過此段落")
                                paragraph.status = CreationStatus.ERROR
                                self.root.after(0, self.refresh_tree)
                            else:
                                # API失敗時延遲更長時間再重試
                                import time
                                time.sleep(3)
                                
                        except Exception as e:
                            self.debug_log(f"❌ 自動寫作第{chapter_index+1}章第{paragraph_index+1}段時發生未預期錯誤: {str(e)}")
                            if retry_attempt == paragraph_retry_max - 1:
                                self.debug_log(f"⚠️ 第{chapter_index+1}章第{paragraph_index+1}段重試次數已用盡，跳過此段落")
                                paragraph.status = CreationStatus.ERROR
                                self.root.after(0, self.refresh_tree)
                            else:
                                import time
                                time.sleep(2)
                    
                    # 如果段落寫作失敗，更新段落列表和樹狀圖以顯示錯誤狀態
                    if not paragraph_success:
                        if chapter_index == self.chapter_combo.current():
                            self.root.after(0, self.update_paragraph_list)
                        self.root.after(0, self.refresh_tree)
                
                # 檢查章節是否完成
                chapter_completed = all(p.status == CreationStatus.COMPLETED for p in chapter.paragraphs)
                if chapter_completed:
                    chapter.status = CreationStatus.COMPLETED
                    self.debug_log(f"🎉 第{chapter_index+1}章全部完成！")
                elif any(p.status == CreationStatus.ERROR for p in chapter.paragraphs):
                    chapter.status = CreationStatus.ERROR
                    self.debug_log(f"⚠️ 第{chapter_index+1}章包含錯誤段落")
                else:
                    chapter.status = CreationStatus.IN_PROGRESS
                
                # 更新樹狀圖以顯示章節狀態
                self.root.after(0, self.refresh_tree)
                
                # 章節完成後的延遲
                if self.auto_writing and chapter_index < len(self.project.chapters) - 1:
                    import time
                    time.sleep(delay * 2)  # 章節間延遲更長
            
            # 自動寫作完成
            if self.auto_writing:
                self.auto_writing = False
                self.root.after(0, lambda: self.auto_button.config(text="開始自動寫作", style=""))
                self.root.after(0, lambda: self.progress_var.set("自動寫作完成！"))
                self.root.after(0, self.refresh_tree)  # 最終更新樹狀圖
                self.debug_log("🎉 自動寫作全部完成！")
                self.root.after(0, lambda: messagebox.showinfo("完成", "自動寫作已完成！"))
                
        except Exception as e:
            self.debug_log(f"❌ 自動寫作工作線程發生錯誤: {str(e)}")
            self.auto_writing = False
            self.root.after(0, lambda: self.auto_button.config(text="開始自動寫作", style=""))
            self.root.after(0, lambda: self.progress_var.set("自動寫作出錯"))
            self.root.after(0, self.refresh_tree)  # 出錯時也更新樹狀圖
    
    def get_writing_progress(self):
        """獲取寫作進度"""
        if not self.project.chapters:
            return 0, 0, 0
        
        total_paragraphs = 0
        completed_paragraphs = 0
        
        for chapter in self.project.chapters:
            total_paragraphs += len(chapter.paragraphs)
            for paragraph in chapter.paragraphs:
                if paragraph.status == CreationStatus.COMPLETED:
                    completed_paragraphs += 1
        
        progress_percent = (completed_paragraphs / total_paragraphs * 100) if total_paragraphs > 0 else 0
        
        return completed_paragraphs, total_paragraphs, progress_percent
    
    # 階層樹視圖相關方法
    def refresh_tree(self):
        """刷新階層樹視圖"""
        # 清空樹
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.project.title:
            return
        
        # 添加根節點（小說標題）
        root_node = self.tree.insert("", "end", text=f"📖 {self.project.title}", 
                                     values=("", ""), tags=("root",))
        
        # 添加大綱節點
        if self.project.outline:
            outline_node = self.tree.insert(root_node, "end", text="📋 整體大綱", 
                                           values=("已完成", len(self.project.outline)), 
                                           tags=("outline",))
        
        # 添加章節節點
        for i, chapter in enumerate(self.project.chapters):
            chapter_status = chapter.status.value if hasattr(chapter, 'status') else "未開始"
            chapter_words = sum(p.word_count for p in chapter.paragraphs)
            
            chapter_node = self.tree.insert(root_node, "end", 
                                           text=f"📚 第{i+1}章: {chapter.title}", 
                                           values=(chapter_status, chapter_words), 
                                           tags=("chapter", f"chapter_{i}"))
            
            # 添加章節大綱節點
            if chapter.outline:
                outline_text = "📝 章節大綱"
                self.tree.insert(chapter_node, "end", text=outline_text, 
                               values=("已完成", len(str(chapter.outline))), 
                               tags=("chapter_outline", f"chapter_{i}"))
            
            # 添加段落節點
            for j, paragraph in enumerate(chapter.paragraphs):
                para_status = paragraph.status.value
                para_words = paragraph.word_count
                
                para_node = self.tree.insert(chapter_node, "end", 
                                           text=f"📄 第{j+1}段: {paragraph.purpose[:20]}...", 
                                           values=(para_status, para_words), 
                                           tags=("paragraph", f"chapter_{i}", f"paragraph_{j}"))
        
        # 展開根節點
        self.tree.item(root_node, open=True)
        
        # 更新樹視圖後，同步更新章節列表
        self.update_chapter_list()
    
    def on_tree_select(self, event):
        """樹視圖選擇事件"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.tree.item(item, "tags")
        
        if not tags:
            return
        
        # 根據標籤類型處理選擇
        if "outline" in tags:
            # 選擇了整體大綱
            self.display_content(self.project.outline, "整體大綱")
        elif "chapter_outline" in tags:
            # 選擇了章節大綱
            chapter_index = self._extract_chapter_index(tags)
            if chapter_index is not None and chapter_index < len(self.project.chapters):
                chapter = self.project.chapters[chapter_index]
                outline_text = json.dumps(chapter.outline, ensure_ascii=False, indent=2)
                self.display_content(outline_text, f"第{chapter_index+1}章大綱")
        elif "paragraph" in tags:
            # 選擇了段落
            chapter_index = self._extract_chapter_index(tags)
            paragraph_index = self._extract_paragraph_index(tags)
            if (chapter_index is not None and paragraph_index is not None and 
                chapter_index < len(self.project.chapters) and 
                paragraph_index < len(self.project.chapters[chapter_index].paragraphs)):
                
                paragraph = self.project.chapters[chapter_index].paragraphs[paragraph_index]
                self.display_content(paragraph.content, f"第{chapter_index+1}章第{paragraph_index+1}段")
                
                # 同步更新下拉選擇框
                self.chapter_combo.current(chapter_index)
                self.update_paragraph_list()
                self.paragraph_combo.current(paragraph_index)
        elif "chapter" in tags:
            # 選擇了章節
            chapter_index = self._extract_chapter_index(tags)
            if chapter_index is not None and chapter_index < len(self.project.chapters):
                chapter = self.project.chapters[chapter_index]
                
                # 顯示章節的所有已完成段落內容
                content_parts = []
                for i, paragraph in enumerate(chapter.paragraphs):
                    if paragraph.content:
                        content_parts.append(f"=== 第{i+1}段 ===\n{paragraph.content}")
                
                full_content = "\n\n".join(content_parts) if content_parts else "此章節尚無內容"
                self.display_content(full_content, f"第{chapter_index+1}章: {chapter.title}")
                
                # 同步更新下拉選擇框
                self.chapter_combo.current(chapter_index)
                self.update_paragraph_list()
    
    def on_tree_double_click(self, event):
        """樹視圖雙擊事件"""
        self.edit_selected_content()
    
    def show_tree_menu(self, event):
        """顯示樹視圖右鍵菜單"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)
    
    def edit_selected_content(self):
        """編輯選中的內容"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "請先選擇要編輯的項目")
            return
        
        item = selection[0]
        tags = self.tree.item(item, "tags")
        
        if not tags:
            return
        
        # 根據選中的項目類型打開編輯窗口
        if "outline" in tags:
            self._edit_outline()
        elif "chapter_outline" in tags:
            chapter_index = self._extract_chapter_index(tags)
            self._edit_chapter_outline(chapter_index)
        elif "paragraph" in tags:
            chapter_index = self._extract_chapter_index(tags)
            paragraph_index = self._extract_paragraph_index(tags)
            self._edit_paragraph_content(chapter_index, paragraph_index)
    
    def regenerate_selected_content(self):
        """重新生成選中的內容"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "請先選擇要重新生成的項目")
            return
        
        item = selection[0]
        tags = self.tree.item(item, "tags")
        
        if not tags:
            return
        
        # 確認重新生成
        if not messagebox.askyesno("確認", "確定要重新生成選中的內容嗎？這將覆蓋現有內容。"):
            return
        
        # 根據選中的項目類型重新生成
        if "chapter_outline" in tags:
            chapter_index = self._extract_chapter_index(tags)
            self._regenerate_chapter_outline(chapter_index)
        elif "paragraph" in tags:
            chapter_index = self._extract_chapter_index(tags)
            paragraph_index = self._extract_paragraph_index(tags)
            self._regenerate_paragraph(chapter_index, paragraph_index)
    
    def expand_all_tree(self):
        """展開所有樹節點"""
        def expand_item(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                expand_item(child)
        
        for item in self.tree.get_children():
            expand_item(item)
    
    def collapse_all_tree(self):
        """收起所有樹節點"""
        def collapse_item(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                collapse_item(child)
        
        for item in self.tree.get_children():
            collapse_item(item)
    
    def display_content(self, content, title):
        """在內容編輯區顯示內容"""
        self.content_text.delete(1.0, tk.END)
        self.content_text.insert(tk.END, content)
        self.notebook.select(0)  # 切換到內容編輯頁面
        
        # 更新選中的上下文內容
        self.selected_context_content = content
        
        self.debug_log(f"📖 顯示內容: {title}")
        self.debug_log(f"🎯 已設定選中內容作為下次生成的參考上下文")
    
    def _extract_chapter_index(self, tags):
        """從標籤中提取章節索引"""
        for tag in tags:
            if tag.startswith("chapter_"):
                try:
                    return int(tag.split("_")[1])
                except (IndexError, ValueError):
                    pass
        return None
    
    def _extract_paragraph_index(self, tags):
        """從標籤中提取段落索引"""
        for tag in tags:
            if tag.startswith("paragraph_"):
                try:
                    return int(tag.split("_")[1])
                except (IndexError, ValueError):
                    pass
        return None
    
    def _edit_outline(self):
        """編輯整體大綱"""
        edit_window = tk.Toplevel(self.root)
        edit_window.title("編輯整體大綱")
        edit_window.geometry("800x600")
        edit_window.transient(self.root)
        
        # 創建文本編輯區
        text_frame = ttk.Frame(edit_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 11))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, self.project.outline)
        
        # 按鈕框架
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def save_outline():
            new_content = text_widget.get(1.0, tk.END).strip()
            self.project.outline = new_content
            self.refresh_tree()
            self.debug_log("✅ 整體大綱已更新")
            edit_window.destroy()
        
        def cancel_edit():
            edit_window.destroy()
        
        ttk.Button(button_frame, text="保存", command=save_outline).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=cancel_edit).pack(side=tk.RIGHT)
    
    def _edit_chapter_outline(self, chapter_index):
        """編輯章節大綱"""
        if chapter_index is None or chapter_index >= len(self.project.chapters):
            return
        
        chapter = self.project.chapters[chapter_index]
        
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"編輯第{chapter_index+1}章大綱")
        edit_window.geometry("800x600")
        edit_window.transient(self.root)
        
        # 創建文本編輯區
        text_frame = ttk.Frame(edit_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 11))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        outline_text = json.dumps(chapter.outline, ensure_ascii=False, indent=2)
        text_widget.insert(tk.END, outline_text)
        
        # 按鈕框架
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def save_outline():
            new_content = text_widget.get(1.0, tk.END).strip()
            try:
                # 嘗試解析為JSON
                chapter.outline = json.loads(new_content)
                self.refresh_tree()
                self.debug_log(f"✅ 第{chapter_index+1}章大綱已更新")
                edit_window.destroy()
            except json.JSONDecodeError:
                messagebox.showerror("錯誤", "大綱格式不正確，請確保是有效的JSON格式")
        
        def cancel_edit():
            edit_window.destroy()
        
        ttk.Button(button_frame, text="保存", command=save_outline).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=cancel_edit).pack(side=tk.RIGHT)
    
    def _edit_paragraph_content(self, chapter_index, paragraph_index):
        """編輯段落內容"""
        if (chapter_index is None or paragraph_index is None or 
            chapter_index >= len(self.project.chapters) or 
            paragraph_index >= len(self.project.chapters[chapter_index].paragraphs)):
            return
        
        chapter = self.project.chapters[chapter_index]
        paragraph = chapter.paragraphs[paragraph_index]
        
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"編輯第{chapter_index+1}章第{paragraph_index+1}段")
        edit_window.geometry("800x600")
        edit_window.transient(self.root)
        
        # 創建文本編輯區
        text_frame = ttk.Frame(edit_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 12))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, paragraph.content)
        
        # 按鈕框架
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def save_content():
            new_content = text_widget.get(1.0, tk.END).strip()
            paragraph.content = new_content
            paragraph.word_count = len(new_content)
            if new_content:
                paragraph.status = CreationStatus.COMPLETED
            else:
                paragraph.status = CreationStatus.NOT_STARTED
            
            self.refresh_tree()
            self.update_paragraph_list()
            self.debug_log(f"✅ 第{chapter_index+1}章第{paragraph_index+1}段內容已更新")
            edit_window.destroy()
        
        def cancel_edit():
            edit_window.destroy()
        
        ttk.Button(button_frame, text="保存", command=save_content).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=cancel_edit).pack(side=tk.RIGHT)
    
    def _regenerate_chapter_outline(self, chapter_index):
        """重新生成章節大綱"""
        if chapter_index is None or chapter_index >= len(self.project.chapters):
            return
        
        def run_task():
            try:
                self.debug_log(f"🔄 重新生成第{chapter_index+1}章大綱")
                self.core.generate_chapter_outline(chapter_index)
                self.root.after(0, self.refresh_tree)
                self.debug_log(f"✅ 第{chapter_index+1}章大綱重新生成完成")
            except Exception as e:
                self.debug_log(f"❌ 重新生成第{chapter_index+1}章大綱失敗: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("錯誤", f"重新生成失敗: {str(e)}"))
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def _regenerate_paragraph(self, chapter_index, paragraph_index):
        """重新生成段落內容"""
        if (chapter_index is None or paragraph_index is None or 
            chapter_index >= len(self.project.chapters) or 
            paragraph_index >= len(self.project.chapters[chapter_index].paragraphs)):
            return
        
        def run_task():
            try:
                self.debug_log(f"🔄 重新生成第{chapter_index+1}章第{paragraph_index+1}段")
                content = self.core.write_paragraph(chapter_index, paragraph_index)
                if content:
                    self.root.after(0, self.refresh_tree)
                    self.root.after(0, self.update_paragraph_list)
                    self.root.after(0, self.update_world_display)
                    self.debug_log(f"✅ 第{chapter_index+1}章第{paragraph_index+1}段重新生成完成")
                else:
                    self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段重新生成失敗")
            except Exception as e:
                self.debug_log(f"❌ 重新生成第{chapter_index+1}章第{paragraph_index+1}段失敗: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("錯誤", f"重新生成失敗: {str(e)}"))
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def initialize_default_tree(self):
        """初始化預設樹結構"""
        # 清空樹
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 創建預設根節點
        project_title = self.project.title if self.project.title else "新小說項目"
        root_node = self.tree.insert("", "end", text=f"📖 {project_title}", 
                                     values=("未開始", "0"), tags=("root",))
        
        # 創建預設大綱節點
        outline_node = self.tree.insert(root_node, "end", text="📋 整體大綱", 
                                       values=("未開始", "0"), tags=("outline",))
        
        # 創建預設章節節點（3個示例章節）
        for i in range(3):
            chapter_node = self.tree.insert(root_node, "end", 
                                           text=f"📚 第{i+1}章: 待定", 
                                           values=("未開始", "0"), 
                                           tags=("chapter", f"chapter_{i}"))
            
            # 為每個章節添加預設大綱節點
            self.tree.insert(chapter_node, "end", text="📝 章節大綱", 
                           values=("未開始", "0"), 
                           tags=("chapter_outline", f"chapter_{i}"))
            
            # 為每個章節添加預設段落節點（3個示例段落）
            for j in range(3):
                self.tree.insert(chapter_node, "end", 
                               text=f"📄 第{j+1}段: 待定", 
                               values=("未開始", "0"), 
                               tags=("paragraph", f"chapter_{i}", f"paragraph_{j}"))
        
        # 展開根節點
        self.tree.item(root_node, open=True)
        
        self.debug_log("🌳 預設樹結構已初始化")
    
    def add_chapter_node(self):
        """添加章節節點"""
        selection = self.tree.selection()
        if not selection:
            # 如果沒有選中項目，添加到根節點
            root_items = self.tree.get_children()
            if root_items:
                parent_item = root_items[0]  # 根節點
            else:
                messagebox.showerror("錯誤", "找不到根節點")
                return
        else:
            item = selection[0]
            tags = self.tree.item(item, "tags")
            
            # 只能在根節點下添加章節
            if "root" in tags:
                parent_item = item
            else:
                # 找到根節點
                root_items = self.tree.get_children()
                if root_items:
                    parent_item = root_items[0]
                else:
                    messagebox.showerror("錯誤", "找不到根節點")
                    return
        
        # 計算新章節的索引
        chapter_count = 0
        for child in self.tree.get_children(parent_item):
            child_tags = self.tree.item(child, "tags")
            if any(tag.startswith("chapter_") for tag in child_tags):
                chapter_count += 1
        
        # 彈出對話框讓用戶輸入章節標題
        title = tk.simpledialog.askstring("添加章節", "請輸入章節標題:", 
                                         initialvalue=f"第{chapter_count+1}章")
        if not title:
            return
        
        # 添加章節節點
        chapter_node = self.tree.insert(parent_item, "end", 
                                       text=f"📚 {title}", 
                                       values=("未開始", "0"), 
                                       tags=("chapter", f"chapter_{chapter_count}"))
        
        # 添加章節大綱節點
        self.tree.insert(chapter_node, "end", text="📝 章節大綱", 
                       values=("未開始", "0"), 
                       tags=("chapter_outline", f"chapter_{chapter_count}"))
        
        # 添加預設段落節點
        for j in range(3):
            self.tree.insert(chapter_node, "end", 
                           text=f"📄 第{j+1}段: 待定", 
                           values=("未開始", "0"), 
                           tags=("paragraph", f"chapter_{chapter_count}", f"paragraph_{j}"))
        
        # 同時在項目數據中添加章節
        if chapter_count >= len(self.project.chapters):
            new_chapter = Chapter(
                title=title,
                summary="",
                estimated_words=3000
            )
            # 添加預設段落
            for j in range(3):
                paragraph = Paragraph(
                    order=j,
                    purpose=f"第{j+1}段內容",
                    estimated_words=400
                )
                new_chapter.paragraphs.append(paragraph)
            
            self.project.chapters.append(new_chapter)
        
        self.debug_log(f"✅ 已添加章節: {title}")
        self.update_chapter_list()
    
    def add_paragraph_node(self):
        """添加段落節點"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "請先選擇一個章節")
            return
        
        item = selection[0]
        tags = self.tree.item(item, "tags")
        
        # 確定父章節
        chapter_index = None
        if "chapter" in tags:
            parent_item = item
            chapter_index = self._extract_chapter_index(tags)
        elif "paragraph" in tags or "chapter_outline" in tags:
            parent_item = self.tree.parent(item)
            parent_tags = self.tree.item(parent_item, "tags")
            chapter_index = self._extract_chapter_index(parent_tags)
        else:
            messagebox.showwarning("提示", "請選擇章節或段落節點")
            return
        
        if chapter_index is None:
            messagebox.showerror("錯誤", "無法確定章節索引")
            return
        
        # 計算新段落的索引
        paragraph_count = 0
        for child in self.tree.get_children(parent_item):
            child_tags = self.tree.item(child, "tags")
            if "paragraph" in child_tags:
                paragraph_count += 1
        
        # 彈出對話框讓用戶輸入段落目的
        purpose = tk.simpledialog.askstring("添加段落", "請輸入段落目的:", 
                                           initialvalue=f"第{paragraph_count+1}段內容")
        if not purpose:
            return
        
        # 添加段落節點
        para_node = self.tree.insert(parent_item, "end", 
                                   text=f"📄 第{paragraph_count+1}段: {purpose[:20]}...", 
                                   values=("未開始", "0"), 
                                   tags=("paragraph", f"chapter_{chapter_index}", f"paragraph_{paragraph_count}"))
        
        # 同時在項目數據中添加段落
        if chapter_index < len(self.project.chapters):
            chapter = self.project.chapters[chapter_index]
            if paragraph_count >= len(chapter.paragraphs):
                new_paragraph = Paragraph(
                    order=paragraph_count,
                    purpose=purpose,
                    estimated_words=400
                )
                chapter.paragraphs.append(new_paragraph)
        
        self.debug_log(f"✅ 已添加段落: {purpose}")
        self.update_paragraph_list()
    
    def delete_selected_node(self):
        """刪除選中的節點"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "請先選擇要刪除的節點")
            return
        
        item = selection[0]
        tags = self.tree.item(item, "tags")
        item_text = self.tree.item(item, "text")
        
        # 不允許刪除根節點和整體大綱
        if "root" in tags:
            messagebox.showwarning("提示", "不能刪除根節點")
            return
        
        if "outline" in tags and "chapter_outline" not in tags:
            messagebox.showwarning("提示", "不能刪除整體大綱節點")
            return
        
        # 確認刪除
        if not messagebox.askyesno("確認刪除", f"確定要刪除「{item_text}」嗎？\n此操作不可撤銷。"):
            return
        
        # 根據節點類型進行刪除
        if "chapter" in tags and "chapter_outline" not in tags:
            # 刪除章節
            chapter_index = self._extract_chapter_index(tags)
            if chapter_index is not None and chapter_index < len(self.project.chapters):
                del self.project.chapters[chapter_index]
                self.debug_log(f"✅ 已刪除章節: {item_text}")
                
                # 重新整理章節索引
                self._reindex_chapters()
                
        elif "paragraph" in tags:
            # 刪除段落
            chapter_index = self._extract_chapter_index(tags)
            paragraph_index = self._extract_paragraph_index(tags)
            if (chapter_index is not None and paragraph_index is not None and 
                chapter_index < len(self.project.chapters) and 
                paragraph_index < len(self.project.chapters[chapter_index].paragraphs)):
                
                del self.project.chapters[chapter_index].paragraphs[paragraph_index]
                self.debug_log(f"✅ 已刪除段落: {item_text}")
                
                # 重新整理段落索引
                self._reindex_paragraphs(chapter_index)
        
        elif "chapter_outline" in tags:
            # 刪除章節大綱（清空大綱內容）
            chapter_index = self._extract_chapter_index(tags)
            if chapter_index is not None and chapter_index < len(self.project.chapters):
                self.project.chapters[chapter_index].outline = {}
                self.debug_log(f"✅ 已清空第{chapter_index+1}章大綱")
        
        # 刪除樹節點
        self.tree.delete(item)
        
        # 更新相關UI
        self.update_chapter_list()
        self.update_paragraph_list()
    
    def _reindex_chapters(self):
        """重新整理章節索引"""
        # 更新樹視圖中的章節標籤
        root_items = self.tree.get_children()
        if not root_items:
            return
        
        root_item = root_items[0]
        chapter_nodes = []
        
        for child in self.tree.get_children(root_item):
            child_tags = self.tree.item(child, "tags")
            if any(tag.startswith("chapter_") for tag in child_tags):
                chapter_nodes.append(child)
        
        # 重新設置章節標籤
        for i, chapter_node in enumerate(chapter_nodes):
            old_tags = list(self.tree.item(chapter_node, "tags"))
            new_tags = []
            for tag in old_tags:
                if tag.startswith("chapter_"):
                    new_tags.append(f"chapter_{i}")
                else:
                    new_tags.append(tag)
            
            self.tree.item(chapter_node, tags=tuple(new_tags))
            
            # 更新子節點的標籤
            for child in self.tree.get_children(chapter_node):
                child_tags = list(self.tree.item(child, "tags"))
                updated_child_tags = []
                for tag in child_tags:
                    if tag.startswith("chapter_"):
                        updated_child_tags.append(f"chapter_{i}")
                    else:
                        updated_child_tags.append(tag)
                
                self.tree.item(child, tags=tuple(updated_child_tags))
    
    def _reindex_paragraphs(self, chapter_index):
        """重新整理指定章節的段落索引"""
        root_items = self.tree.get_children()
        if not root_items:
            return
        
        root_item = root_items[0]
        chapter_node = None
        
        # 找到對應的章節節點
        for child in self.tree.get_children(root_item):
            child_tags = self.tree.item(child, "tags")
            if f"chapter_{chapter_index}" in child_tags:
                chapter_node = child
                break
        
        if not chapter_node:
            return
        
        # 重新整理段落索引
        paragraph_nodes = []
        for child in self.tree.get_children(chapter_node):
            child_tags = self.tree.item(child, "tags")
            if "paragraph" in child_tags:
                paragraph_nodes.append(child)
        
        # 重新設置段落標籤和order
        for i, para_node in enumerate(paragraph_nodes):
            old_tags = list(self.tree.item(para_node, "tags"))
            new_tags = []
            for tag in old_tags:
                if tag.startswith("paragraph_"):
                    new_tags.append(f"paragraph_{i}")
                else:
                    new_tags.append(tag)
            
            self.tree.item(para_node, tags=tuple(new_tags))
            
            # 更新項目數據中的段落order
            if (chapter_index < len(self.project.chapters) and 
                i < len(self.project.chapters[chapter_index].paragraphs)):
                self.project.chapters[chapter_index].paragraphs[i].order = i
    
    # 新增的增強功能方法
    def open_global_config(self):
        """打開全局配置窗口"""
        config_window = tk.Toplevel(self.root)
        config_window.title("全局創作配置")
        config_window.geometry("700x600")
        config_window.transient(self.root)
        config_window.grab_set()
        
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 基本風格頁面
        self.setup_style_tab(notebook)
        
        # 持續要素頁面
        self.setup_continuous_elements_tab(notebook)
        
        # 篇幅控制頁面
        self.setup_length_control_tab(notebook)
        
        # 全局指示頁面
        self.setup_global_instructions_tab(notebook)
        
        # 保存按鈕
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="保存", 
                  command=lambda: self.save_global_config(config_window)).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", 
                  command=config_window.destroy).pack(side=tk.RIGHT)
    
    def setup_style_tab(self, notebook):
        """設置風格配置頁面"""
        style_frame = ttk.Frame(notebook)
        notebook.add(style_frame, text="寫作風格")
        
        # 敘述方式
        ttk.Label(style_frame, text="敘述方式:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.writing_style_var = tk.StringVar(value=self.core.project.global_config.writing_style.value)
        style_combo = ttk.Combobox(style_frame, textvariable=self.writing_style_var,
                                  values=[style.value for style in WritingStyle], state="readonly")
        style_combo.grid(row=0, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # 節奏風格
        ttk.Label(style_frame, text="節奏風格:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.pacing_style_var = tk.StringVar(value=self.core.project.global_config.pacing_style.value)
        pacing_combo = ttk.Combobox(style_frame, textvariable=self.pacing_style_var,
                                   values=[style.value for style in PacingStyle], state="readonly")
        pacing_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # 語調
        ttk.Label(style_frame, text="整體語調:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.tone_var = tk.StringVar(value=self.core.project.global_config.tone)
        tone_entry = ttk.Entry(style_frame, textvariable=self.tone_var)
        tone_entry.grid(row=2, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # 對話風格
        ttk.Label(style_frame, text="對話風格:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.dialogue_style_var = tk.StringVar(value=self.core.project.global_config.dialogue_style)
        dialogue_entry = ttk.Entry(style_frame, textvariable=self.dialogue_style_var)
        dialogue_entry.grid(row=3, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # 描述密度
        ttk.Label(style_frame, text="描述密度:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.description_density_var = tk.StringVar(value=self.core.project.global_config.description_density)
        desc_combo = ttk.Combobox(style_frame, textvariable=self.description_density_var,
                                 values=["簡潔", "適中", "豐富"], state="readonly")
        desc_combo.grid(row=4, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # 情感強度
        ttk.Label(style_frame, text="情感強度:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        self.emotional_intensity_var = tk.StringVar(value=self.core.project.global_config.emotional_intensity)
        emotion_combo = ttk.Combobox(style_frame, textvariable=self.emotional_intensity_var,
                                    values=["克制", "適中", "濃烈"], state="readonly")
        emotion_combo.grid(row=5, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        style_frame.columnconfigure(1, weight=1)
    
    def setup_continuous_elements_tab(self, notebook):
        """設置持續要素頁面"""
        elements_frame = ttk.Frame(notebook)
        notebook.add(elements_frame, text="持續要素")
        
        # 核心主題
        ttk.Label(elements_frame, text="核心主題（每行一個）:").pack(anchor=tk.W, padx=10, pady=5)
        self.themes_text = scrolledtext.ScrolledText(elements_frame, height=4)
        self.themes_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.themes_text.insert(tk.END, '\n'.join(self.core.project.global_config.continuous_themes))
        
        # 必須包含要素
        ttk.Label(elements_frame, text="必須包含要素（每行一個）:").pack(anchor=tk.W, padx=10, pady=5)
        self.must_include_text = scrolledtext.ScrolledText(elements_frame, height=4)
        self.must_include_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.must_include_text.insert(tk.END, '\n'.join(self.core.project.global_config.must_include_elements))
        
        # 避免要素
        ttk.Label(elements_frame, text="避免要素（每行一個）:").pack(anchor=tk.W, padx=10, pady=5)
        self.avoid_text = scrolledtext.ScrolledText(elements_frame, height=4)
        self.avoid_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.avoid_text.insert(tk.END, '\n'.join(self.core.project.global_config.avoid_elements))
    
    def setup_length_control_tab(self, notebook):
        """設置篇幅控制頁面"""
        length_frame = ttk.Frame(notebook)
        notebook.add(length_frame, text="篇幅控制")
        
        # 章節目標字數
        ttk.Label(length_frame, text="章節目標字數:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.target_chapter_words_var = tk.IntVar(value=self.core.project.global_config.target_chapter_words)
        chapter_spinbox = ttk.Spinbox(length_frame, from_=1000, to=10000, increment=500,
                                     textvariable=self.target_chapter_words_var)
        chapter_spinbox.grid(row=0, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # 段落目標字數
        ttk.Label(length_frame, text="段落目標字數:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.target_paragraph_words_var = tk.IntVar(value=self.core.project.global_config.target_paragraph_words)
        paragraph_spinbox = ttk.Spinbox(length_frame, from_=100, to=1000, increment=50,
                                       textvariable=self.target_paragraph_words_var)
        paragraph_spinbox.grid(row=1, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # 段落數量偏好
        ttk.Label(length_frame, text="段落數量偏好:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.paragraph_count_var = tk.StringVar(value=self.core.project.global_config.paragraph_count_preference)
        count_combo = ttk.Combobox(length_frame, textvariable=self.paragraph_count_var,
                                  values=["簡潔", "適中", "詳細"], state="readonly")
        count_combo.grid(row=2, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        length_frame.columnconfigure(1, weight=1)
    
    def setup_global_instructions_tab(self, notebook):
        """設置全局指示頁面"""
        instructions_frame = ttk.Frame(notebook)
        notebook.add(instructions_frame, text="全局指導")
        
        ttk.Label(instructions_frame, text="全局創作指導（會在每個階段都被考慮）:").pack(anchor=tk.W, padx=10, pady=5)
        self.global_instructions_text = scrolledtext.ScrolledText(instructions_frame, wrap=tk.WORD)
        self.global_instructions_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.global_instructions_text.insert(tk.END, self.core.project.global_config.global_instructions)
        
        # 添加一些提示
        tips_text = """
提示：全局指導會在每個創作階段都被考慮，適合放置：
• 整體文風要求（如：「保持幽默輕鬆的語調」）
• 世界觀設定（如：「這是一個魔法與科技並存的世界」）
• 角色性格（如：「主角內向但勇敢，不善表達但行動力強」）
• 創作禁忌（如：「避免過度暴力描寫」）
• 特殊要求（如：「每章都要有成長感悟」）
        """
        
        tips_label = tk.Label(instructions_frame, text=tips_text, justify=tk.LEFT, 
                             fg="gray", font=("Microsoft YaHei", 9))
        tips_label.pack(anchor=tk.W, padx=10, pady=(5, 10))
    
    def save_global_config(self, window):
        """保存全局配置"""
        # 收集所有配置
        themes = [line.strip() for line in self.themes_text.get("1.0", tk.END).split('\n') if line.strip()]
        must_include = [line.strip() for line in self.must_include_text.get("1.0", tk.END).split('\n') if line.strip()]
        avoid = [line.strip() for line in self.avoid_text.get("1.0", tk.END).split('\n') if line.strip()]
        
        # 更新核心配置
        self.core.set_global_config(
            writing_style=WritingStyle(self.writing_style_var.get()),
            pacing_style=PacingStyle(self.pacing_style_var.get()),
            tone=self.tone_var.get(),
            dialogue_style=self.dialogue_style_var.get(),
            description_density=self.description_density_var.get(),
            emotional_intensity=self.emotional_intensity_var.get(),
            continuous_themes=themes,
            must_include_elements=must_include,
            avoid_elements=avoid,
            target_chapter_words=self.target_chapter_words_var.get(),
            target_paragraph_words=self.target_paragraph_words_var.get(),
            paragraph_count_preference=self.paragraph_count_var.get(),
            global_instructions=self.global_instructions_text.get("1.0", tk.END).strip()
        )
        
        # 同步快速設定
        self.quick_style_var.set(self.writing_style_var.get())
        
        self.debug_log("✅ 全局配置已更新")
        messagebox.showinfo("成功", "全局配置已保存！")
        window.destroy()
    
    def open_stage_configs(self):
        """打開階段配置窗口"""
        config_window = tk.Toplevel(self.root)
        config_window.title("階段參數配置")
        config_window.geometry("600x500")
        config_window.transient(self.root)
        config_window.grab_set()
        
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 設置各階段配置標籤頁
        stage_names = {
            TaskType.OUTLINE: "大綱",
            TaskType.CHAPTERS: "章節",
            TaskType.WRITING: "寫作"
        }
        
        self.stage_widgets = {}
        
        for task_type, name in stage_names.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=f"{name}配置")
            
            # 額外指示
            ttk.Label(frame, text=f"{name}階段特別指示:").pack(anchor=tk.W, padx=10, pady=5)
            text_widget = scrolledtext.ScrolledText(frame, height=4)
            text_widget.pack(fill=tk.X, padx=10, pady=5)
            text_widget.insert(tk.END, self.core.stage_configs[task_type].additional_prompt)
            
            # 創意程度
            ttk.Label(frame, text="創意程度:").pack(anchor=tk.W, padx=10, pady=5)
            creativity_var = tk.DoubleVar(value=self.core.stage_configs[task_type].creativity_level)
            creativity_scale = tk.Scale(frame, from_=0.0, to=1.0, resolution=0.1, 
                                      orient=tk.HORIZONTAL, variable=creativity_var)
            creativity_scale.pack(fill=tk.X, padx=10, pady=5)
            
            # 詳細程度
            ttk.Label(frame, text="詳細程度:").pack(anchor=tk.W, padx=10, pady=5)
            detail_var = tk.StringVar(value=self.core.stage_configs[task_type].detail_level)
            detail_combo = ttk.Combobox(frame, textvariable=detail_var,
                                       values=["簡潔", "適中", "詳細"], state="readonly")
            detail_combo.pack(fill=tk.X, padx=10, pady=5)
            
            self.stage_widgets[task_type] = {
                'additional_prompt': text_widget,
                'creativity_level': creativity_var,
                'detail_level': detail_var
            }
        
        # 保存按鈕
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="保存", 
                  command=lambda: self.save_stage_configs(config_window)).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", 
                  command=config_window.destroy).pack(side=tk.RIGHT)
    
    def save_stage_configs(self, window):
        """保存階段配置"""
        # 保存階段配置
        for task_type, widgets in self.stage_widgets.items():
            self.core.set_stage_config(
                task_type,
                additional_prompt=widgets['additional_prompt'].get("1.0", tk.END).strip(),
                creativity_level=widgets['creativity_level'].get(),
                detail_level=widgets['detail_level'].get()
            )
        
        self.debug_log("✅ 階段配置已更新")
        messagebox.showinfo("成功", "階段配置已保存！")
        window.destroy()
    
    def enhanced_write_paragraph(self):
        """增強版段落寫作"""
        chapter_index = self.chapter_combo.current()
        paragraph_index = self.paragraph_combo.current()
        
        if chapter_index < 0 or paragraph_index < 0:
            messagebox.showerror("錯誤", "請先選擇章節和段落")
            return
        
        # 收集當前設定
        additional_prompt = self.current_paragraph_prompt.get("1.0", tk.END).strip()
        target_words = int(self.target_words_var.get())
        strict_words = self.strict_words_var.get()
        
        # 更新段落配置
        self.core.set_stage_config(
            TaskType.WRITING,
            additional_prompt=additional_prompt,
            word_count_strict=strict_words
        )
        
        # 更新段落目標字數
        if chapter_index < len(self.project.chapters):
            if paragraph_index < len(self.project.chapters[chapter_index].paragraphs):
                self.project.chapters[chapter_index].paragraphs[paragraph_index].estimated_words = target_words
        
        def run_task():
            try:
                self.current_action = f"正在智能寫作第{chapter_index+1}章第{paragraph_index+1}段..."
                self.debug_log(f"🚀 開始智能寫作第{chapter_index+1}章第{paragraph_index+1}段")
                self.debug_log(f"📝 使用額外指示: {additional_prompt}")
                self.debug_log(f"📏 目標字數: {target_words}字，嚴格控制: {strict_words}")
                
                content = self.core.write_paragraph(
                    chapter_index, paragraph_index, self.tree_callback, self.selected_context_content
                )
                
                if content:
                    self.root.after(0, lambda: self.display_paragraph_content(content))
                    self.root.after(0, self.update_paragraph_list)
                    self.root.after(0, self.update_world_display)
                    self.root.after(0, self.refresh_tree)
                    self.debug_log(f"✅ 第{chapter_index+1}章第{paragraph_index+1}段智能寫作完成")
                else:
                    self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段智能寫作失敗")
                    
            except Exception as e:
                self.debug_log(f"❌ 智能寫作段落時發生錯誤: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("錯誤", f"智能寫作失敗: {str(e)}"))
            finally:
                self.current_action = ""
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def on_quick_style_change(self, event):
        """快速風格變更"""
        selected_style = self.quick_style_var.get()
        for style in WritingStyle:
            if style.value == selected_style:
                self.core.set_global_config(writing_style=style)
                break
        self.debug_log(f"📝 快速設定敘述方式: {selected_style}")
    
    def on_quick_length_change(self, event):
        """快速篇幅變更"""
        selected_length = self.quick_length_var.get()
        
        # 根據選擇調整目標字數
        base_words = 300
        if selected_length == "簡潔":
            new_words = int(base_words * 0.7)
        elif selected_length == "詳細":
            new_words = int(base_words * 1.3)
        else:
            new_words = base_words
        
        self.target_words_var.set(str(new_words))
        self.core.set_global_config(description_density=selected_length)
        self.debug_log(f"📏 快速設定篇幅: {selected_length}({new_words}字)")
    
    def use_selected_as_reference(self):
        """使用選中內容作為參考"""
        selected_text = ""
        try:
            # 嘗試獲取當前編輯區的選中文本
            if self.content_text.tag_ranges(tk.SEL):
                selected_text = self.content_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            else:
                # 如果沒有選中，使用整個內容
                selected_text = self.content_text.get("1.0", tk.END).strip()
        except tk.TclError:
            selected_text = self.content_text.get("1.0", tk.END).strip()
        
        if selected_text:
            self.selected_context_content = selected_text
            self.debug_log(f"📎 設定參考內容: {selected_text[:50]}...")
            messagebox.showinfo("成功", f"已設定參考內容（{len(selected_text)}字）")
        else:
            messagebox.showwarning("提示", "沒有找到可用的參考內容")
    
    def clear_reference(self):
        """清除參考內容"""
        self.selected_context_content = ""
        self.debug_log("🗑️ 已清除參考內容")
        messagebox.showinfo("成功", "已清除參考內容")
    
    def rewrite_with_optimization(self):
        """重寫優化當前段落"""
        chapter_index = self.chapter_combo.current()
        paragraph_index = self.paragraph_combo.current()
        
        if chapter_index < 0 or paragraph_index < 0:
            messagebox.showerror("錯誤", "請先選擇章節和段落")
            return
        
        current_content = ""
        if (chapter_index < len(self.project.chapters) and 
            paragraph_index < len(self.project.chapters[chapter_index].paragraphs)):
            current_content = self.project.chapters[chapter_index].paragraphs[paragraph_index].content
        
        if not current_content:
            messagebox.showwarning("提示", "此段落尚無內容，請先使用智能寫作")
            return
        
        # 添加優化提示到額外指示中
        optimization_prompt = self.current_paragraph_prompt.get("1.0", tk.END).strip()
        if optimization_prompt:
            optimization_prompt += "\n\n"
        optimization_prompt += f"""【重寫優化任務】
請基於以下原始內容進行優化重寫：

{current_content}

優化要求：
1. 保持原意和情節發展
2. 改善文字表達和流暢度
3. 調整篇幅至目標字數
4. 增強情感表達和畫面感"""
        
        # 臨時更新額外指示
        original_prompt = self.current_paragraph_prompt.get("1.0", tk.END)
        self.current_paragraph_prompt.delete("1.0", tk.END)
        self.current_paragraph_prompt.insert("1.0", optimization_prompt)
        
        # 執行重寫
        self.enhanced_write_paragraph()
        
        # 恢復原始指示
        self.current_paragraph_prompt.delete("1.0", tk.END)
        self.current_paragraph_prompt.insert("1.0", original_prompt)
    
    def toggle_prompt_area(self):
        """切換額外指示區域顯示"""
        if self.show_prompts.get():
            self.prompt_area.pack(fill=tk.X, pady=(5, 0))
            self.debug_log("📝 顯示額外指示區域")
        else:
            self.prompt_area.pack_forget()
            self.debug_log("📝 隱藏額外指示區域")
    
    def toggle_advanced_area(self):
        """切換高級選項區域顯示"""
        if self.show_advanced.get():
            self.advanced_area.pack(fill=tk.X, pady=(5, 0))
            self.debug_log("⚙️ 顯示高級選項區域")
        else:
            self.advanced_area.pack_forget()
            self.debug_log("⚙️ 隱藏高級選項區域")


def main():
    """主函數"""
    root = tk.Tk()
    app = NovelWriterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
