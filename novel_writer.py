"""
重構後的階層式小說編寫器 - 完整版
採用更清晰的架構和更好的錯誤處理
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import threading
import re
import traceback
from dataclasses import dataclass, asdict
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

@dataclass
class NovelProject:
    """小說項目數據類"""
    title: str = ""
    theme: str = ""
    outline: str = ""
    chapters: List[Chapter] = None
    world_building: WorldBuilding = None
    current_context: str = ""
    api_config: APIConfig = None
    
    def __post_init__(self):
        if self.chapters is None:
            self.chapters = []
        if self.world_building is None:
            self.world_building = WorldBuilding()
        if self.api_config is None:
            self.api_config = APIConfig()

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
JSON格式：
{
    "title": "標題",
    "summary": "故事概要",
    "themes": ["主題1", "主題2"],
    "estimated_chapters": 數字,
    "main_characters": [{"name": "角色名", "desc": "角色描述"}],
    "world_setting": "世界觀"
}""",
            
            TaskType.CHAPTERS: """
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
JSON格式：
{
    "outline": {
        "opening": "開場描述",
        "development": "發展部分", 
        "climax": "高潮部分",
        "conclusion": "結尾部分",
        "estimated_paragraphs": 8
    }
}""",
            
            TaskType.PARAGRAPHS: """
JSON格式：
{
    "paragraphs": [
        {
            "number": 1,
            "purpose": "段落目的",
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
    
    @safe_execute
    def generate_outline(self, additional_prompt: str = "") -> Dict:
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
        
        return result
    
    @safe_execute
    def divide_chapters(self, additional_prompt: str = "") -> List[Chapter]:
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
            return chapters
        
        return []
    
    @safe_execute
    def generate_chapter_outline(self, chapter_index: int) -> Dict:
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
            return result["outline"]
        
        return {}
    
    @safe_execute
    def divide_paragraphs(self, chapter_index: int) -> List[Paragraph]:
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
            return paragraphs
        
        return []
    
    @safe_execute
    def write_paragraph(self, chapter_index: int, paragraph_index: int) -> str:
        """寫作段落"""
        if chapter_index >= len(self.project.chapters):
            raise ValueError("章節索引超出範圍")
        
        chapter = self.project.chapters[chapter_index]
        
        if paragraph_index >= len(chapter.paragraphs):
            raise ValueError("段落索引超出範圍")
        
        paragraph = chapter.paragraphs[paragraph_index]
        
        # 獲取API配置中的語言和引號設定
        language = getattr(self.project.api_config, 'language', 'zh-TW')
        use_traditional_quotes = getattr(self.project.api_config, 'use_traditional_quotes', True)
        
        # 根據語言設定調整prompt
        language_instruction = self._get_language_instruction(language, use_traditional_quotes)
        
        prompt = f"""
請寫作第{chapter_index+1}章第{paragraph_index+1}段：

{language_instruction}

段落信息：
- 目的：{paragraph.purpose}
- 類型：{paragraph.content_type}
- 要點：{', '.join(paragraph.key_points)}
- 預計字數：{paragraph.estimated_words}
- 氛圍：{paragraph.mood}

上下文信息：
整體大綱：{self.project.outline}
章節大綱：{json.dumps(chapter.outline, ensure_ascii=False)}

當前世界設定：
{self._get_world_context()}

【重要】以下是前面已經寫好的段落內容，請勿重複，要接續往下寫：
{self._get_previous_paragraphs_content(chapter_index, paragraph_index)}

【當前任務】現在請寫第{paragraph_index+1}段，要承接上文但不重複前面的內容。
請寫作這個段落，確保內容流暢易讀，適當分行，並使用指定的引號格式。
        """
        
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
            self._update_world_building_from_content(formatted_content)
            
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
    
    def _update_world_building_from_content(self, content: str):
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
                # 更新角色
                for char in result.get("new_characters", []):
                    name = char.get("name", "")
                    desc = char.get("desc", char.get("description", ""))
                    if name and name not in self.project.world_building.characters:
                        self.project.world_building.characters[name] = desc
                
                # 更新場景
                for setting in result.get("new_settings", []):
                    name = setting.get("name", "")
                    desc = setting.get("desc", setting.get("description", ""))
                    if name and name not in self.project.world_building.settings:
                        self.project.world_building.settings[name] = desc
                
                # 更新名詞
                for term in result.get("new_terms", []):
                    term_name = term.get("term", "")
                    definition = term.get("def", term.get("definition", ""))
                    if term_name and term_name not in self.project.world_building.terminology:
                        self.project.world_building.terminology[term_name] = definition
                
                # 更新情節點
                for plot in result.get("plot_points", []):
                    if plot and plot not in self.project.world_building.plot_points:
                        self.project.world_building.plot_points.append(plot)
        
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
        
        # 先設置UI
        self.setup_ui()
        
        # 然後載入配置和初始化服務
        self.load_api_config()
        self.api_connector = APIConnector(self.project.api_config)
        self.llm_service = LLMService(self.api_connector, self.debug_log)
        self.core = NovelWriterCore(self.project, self.llm_service)
    
    def setup_ui(self):
        """設置UI"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側控制面板
        left_panel = ttk.Frame(main_frame, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # 右側工作區域
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)
    
    def setup_left_panel(self, parent):
        """設置左側控制面板"""
        # 項目信息
        project_frame = ttk.LabelFrame(parent, text="項目信息", padding=10)
        project_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(project_frame, text="小說標題:").pack(anchor=tk.W)
        self.title_entry = ttk.Entry(project_frame, width=30)
        self.title_entry.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(project_frame, text="主題/風格:").pack(anchor=tk.W)
        self.theme_entry = ttk.Entry(project_frame, width=30)
        self.theme_entry.pack(fill=tk.X, pady=(0, 5))
        
        # API配置
        api_frame = ttk.LabelFrame(parent, text="API配置", padding=10)
        api_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(api_frame, text="配置API", command=self.configure_api).pack(fill=tk.X)
        
        # 創作流程
        workflow_frame = ttk.LabelFrame(parent, text="創作流程", padding=10)
        workflow_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(workflow_frame, text="1. 生成大綱", 
                  command=self.generate_outline).pack(fill=tk.X, pady=2)
        
        # 生成大綱的額外prompt輸入框
        ttk.Label(workflow_frame, text="大綱生成額外指示:", font=("Microsoft YaHei", 8)).pack(anchor=tk.W, pady=(5, 0))
        self.outline_prompt_entry = tk.Text(workflow_frame, height=3, wrap=tk.WORD, font=("Microsoft YaHei", 9))
        self.outline_prompt_entry.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(workflow_frame, text="2. 劃分章節", 
                  command=self.divide_chapters).pack(fill=tk.X, pady=2)
        
        # 劃分章節的額外prompt輸入框
        ttk.Label(workflow_frame, text="章節劃分額外指示:", font=("Microsoft YaHei", 8)).pack(anchor=tk.W, pady=(5, 0))
        self.chapters_prompt_entry = tk.Text(workflow_frame, height=3, wrap=tk.WORD, font=("Microsoft YaHei", 9))
        self.chapters_prompt_entry.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(workflow_frame, text="3. 開始寫作", 
                  command=self.start_writing).pack(fill=tk.X, pady=2)
        
        # 章節選擇
        chapter_frame = ttk.LabelFrame(parent, text="章節選擇", padding=10)
        chapter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.chapter_var = tk.StringVar()
        self.chapter_combo = ttk.Combobox(chapter_frame, textvariable=self.chapter_var, 
                                         state="readonly", width=25)
        self.chapter_combo.pack(fill=tk.X, pady=2)
        self.chapter_combo.bind('<<ComboboxSelected>>', self.on_chapter_selected)
        
        # 段落選擇
        paragraph_frame = ttk.LabelFrame(parent, text="段落選擇", padding=10)
        paragraph_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.paragraph_var = tk.StringVar()
        self.paragraph_combo = ttk.Combobox(paragraph_frame, textvariable=self.paragraph_var,
                                           state="readonly", width=25)
        self.paragraph_combo.pack(fill=tk.X, pady=2)
        
        ttk.Button(paragraph_frame, text="寫作此段落", 
                  command=self.write_current_paragraph).pack(fill=tk.X, pady=2)
        
        # 自動化寫作控制
        auto_frame = ttk.LabelFrame(parent, text="自動化寫作", padding=10)
        auto_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_writing = False
        self.auto_button = ttk.Button(auto_frame, text="開始自動寫作", 
                                     command=self.toggle_auto_writing)
        self.auto_button.pack(fill=tk.X, pady=2)
        
        # 自動寫作設置
        settings_frame = ttk.Frame(auto_frame)
        settings_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(settings_frame, text="延遲(秒):").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="2")
        delay_spinbox = ttk.Spinbox(settings_frame, from_=1, to=10, width=5, 
                                   textvariable=self.delay_var)
        delay_spinbox.pack(side=tk.RIGHT)
        
        # 進度顯示
        self.progress_var = tk.StringVar(value="準備就緒")
        ttk.Label(auto_frame, textvariable=self.progress_var, 
                 font=("Microsoft YaHei", 9)).pack(fill=tk.X, pady=2)
        
        # 文件操作
        file_frame = ttk.LabelFrame(parent, text="文件操作", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="保存項目", command=self.save_project).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="載入項目", command=self.load_project).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="導出小說", command=self.export_novel).pack(fill=tk.X, pady=2)
    
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
                self.project.api_config.model = config_data.get("model", "gpt-4")
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
        config_window.geometry("450x450")
        config_window.transient(self.root)
        config_window.grab_set()
        
        # API提供商
        ttk.Label(config_window, text="API提供商:").pack(anchor=tk.W, padx=10, pady=5)
        provider_var = tk.StringVar(value=self.project.api_config.provider)
        provider_combo = ttk.Combobox(config_window, textvariable=provider_var,
                                     values=["openai", "anthropic", "custom"])
        provider_combo.pack(fill=tk.X, padx=10, pady=5)
        
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
        
        def run_task():
            try:
                self.current_action = "正在生成大綱..."
                self.debug_log("🚀 開始生成大綱")
                
                # 獲取額外的prompt指示
                additional_prompt = self.outline_prompt_entry.get("1.0", tk.END).strip()
                if additional_prompt:
                    self.debug_log(f"📝 使用額外指示: {additional_prompt}")
                
                result = self.core.generate_outline(additional_prompt)
                
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
        
        def run_task():
            try:
                self.current_action = "正在劃分章節..."
                self.debug_log("🚀 開始劃分章節")
                
                # 獲取額外的prompt指示
                additional_prompt = self.chapters_prompt_entry.get("1.0", tk.END).strip()
                if additional_prompt:
                    self.debug_log(f"📝 使用額外指示: {additional_prompt}")
                
                chapters = self.core.divide_chapters(additional_prompt)
                
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
                
                content = self.core.write_paragraph(chapter_index, paragraph_index)
                
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
        
        self.world_text.delete(1.0, tk.END)
        self.world_text.insert(tk.END, "\n".join(content))
    
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
                
                if self.project.outline:
                    self.content_text.delete(1.0, tk.END)
                    self.content_text.insert(tk.END, self.project.outline)
                
                self.update_chapter_list()
                self.update_world_display()
                
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
            self.auto_button.config(text="停止自動寫作", style="Accent.TButton")
            self.progress_var.set("自動寫作已啟動")
            self.debug_log("🤖 自動寫作模式啟動")
            
            # 開始自動寫作線程
            threading.Thread(target=self.auto_writing_worker, daemon=True).start()
        else:
            # 停止自動寫作
            self.auto_writing = False
            self.auto_button.config(text="開始自動寫作", style="")
            self.progress_var.set("自動寫作已停止")
            self.debug_log("⏹️ 自動寫作模式停止")
    
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
                        # 生成章節大綱
                        self.core.generate_chapter_outline(chapter_index)
                        
                        # 劃分段落
                        self.core.divide_paragraphs(chapter_index)
                        
                        # 更新UI
                        if chapter_index == self.chapter_combo.current():
                            self.root.after(0, self.update_paragraph_list)
                        
                        self.debug_log(f"✅ 第{chapter_index+1}章準備完成")
                        
                    except Exception as e:
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
                            
                            # 寫作段落
                            content = self.core.write_paragraph(chapter_index, paragraph_index)
                            
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
                                
                        except JSONParseException as e:
                            self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段JSON解析失敗: {str(e)}")
                            if retry_attempt == paragraph_retry_max - 1:
                                self.debug_log(f"⚠️ 第{chapter_index+1}章第{paragraph_index+1}段JSON解析重試次數已用盡，跳過此段落")
                                paragraph.status = CreationStatus.ERROR
                            else:
                                # JSON解析失敗時稍微延遲再重試
                                import time
                                time.sleep(1)
                                
                        except APIException as e:
                            self.debug_log(f"❌ 第{chapter_index+1}章第{paragraph_index+1}段API調用失敗: {str(e)}")
                            if retry_attempt == paragraph_retry_max - 1:
                                self.debug_log(f"⚠️ 第{chapter_index+1}章第{paragraph_index+1}段API重試次數已用盡，跳過此段落")
                                paragraph.status = CreationStatus.ERROR
                            else:
                                # API失敗時延遲更長時間再重試
                                import time
                                time.sleep(3)
                                
                        except Exception as e:
                            self.debug_log(f"❌ 自動寫作第{chapter_index+1}章第{paragraph_index+1}段時發生未預期錯誤: {str(e)}")
                            if retry_attempt == paragraph_retry_max - 1:
                                self.debug_log(f"⚠️ 第{chapter_index+1}章第{paragraph_index+1}段重試次數已用盡，跳過此段落")
                                paragraph.status = CreationStatus.ERROR
                            else:
                                import time
                                time.sleep(2)
                    
                    # 如果段落寫作失敗，更新段落列表以顯示錯誤狀態
                    if not paragraph_success and chapter_index == self.chapter_combo.current():
                        self.root.after(0, self.update_paragraph_list)
                
                # 章節完成後的延遲
                if self.auto_writing and chapter_index < len(self.project.chapters) - 1:
                    import time
                    time.sleep(delay * 2)  # 章節間延遲更長
            
            # 自動寫作完成
            if self.auto_writing:
                self.auto_writing = False
                self.root.after(0, lambda: self.auto_button.config(text="開始自動寫作", style=""))
                self.root.after(0, lambda: self.progress_var.set("自動寫作完成！"))
                self.debug_log("🎉 自動寫作全部完成！")
                self.root.after(0, lambda: messagebox.showinfo("完成", "自動寫作已完成！"))
                
        except Exception as e:
            self.debug_log(f"❌ 自動寫作工作線程發生錯誤: {str(e)}")
            self.auto_writing = False
            self.root.after(0, lambda: self.auto_button.config(text="開始自動寫作", style=""))
            self.root.after(0, lambda: self.progress_var.set("自動寫作出錯"))
    
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


def main():
    """主函數"""
    root = tk.Tk()
    app = NovelWriterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
