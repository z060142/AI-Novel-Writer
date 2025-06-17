"""
小說編寫器核心邏輯
核心業務邏輯類別，負責處理小說生成的所有階段
"""

import json
import threading
from typing import Dict, List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.llm_service import LLMService

from ..models.enums import TaskType, CreationStatus
from ..models.data_models import NovelProject, Chapter, Paragraph, WorldBuilding, StageSpecificConfig
# LLMService 將在初始化時注入，避免循環導入
from ..utils.decorators import safe_execute
from .prompt_builder import DynamicPromptBuilder
from ..services.text_formatter import TextFormatter


class NovelWriterCore:
    """小說編寫器核心邏輯"""
    
    def __init__(self, project: NovelProject, llm_service: 'LLMService', debug_callback: Callable = None):
        self.project = project
        self.llm_service = llm_service
        self.current_chapter = 0
        self.current_paragraph = 0
        self.debug_callback = debug_callback or (lambda x: None)
        
        # 初始化動態Prompt構建器
        self.prompt_builder = DynamicPromptBuilder(self.project)
        
        # 各階段配置
        self.stage_configs = {
            TaskType.OUTLINE: StageSpecificConfig(),
            TaskType.CHAPTERS: StageSpecificConfig(),
            TaskType.CHAPTER_OUTLINE: StageSpecificConfig(),
            TaskType.PARAGRAPHS: StageSpecificConfig(),
            TaskType.WRITING: StageSpecificConfig(),
        }
    
    def debug_log(self, message):
        """調試日誌方法"""
        if self.debug_callback:
            self.debug_callback(message)
    
    def set_global_config(self, **kwargs):
        """設置全局配置"""
        for key, value in kwargs.items():
            if hasattr(self.project.global_config, key):
                setattr(self.project.global_config, key, value)
        
        # 重新初始化prompt構建器
        self.prompt_builder = DynamicPromptBuilder(self.project)
    
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
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.OUTLINE, use_planning_model=True)
        
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
基於以下大綱，請劃分出10-20個章節：

{self.project.outline}

要求：
1. 每章標題要具體且吸引人
2. 章節摘要控制在150字以內
3. 確保情節發展有邏輯性
4. 每章預計3000-5000字

請直接輸出JSON格式。"""
        
        # 如果有額外的prompt指示，添加到prompt中
        if additional_prompt.strip():
            prompt += f"""

額外指示：
{additional_prompt.strip()}"""
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.CHAPTERS, use_planning_model=True)
        
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
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.CHAPTER_OUTLINE, use_planning_model=True)
        
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
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.PARAGRAPHS, use_planning_model=True)
        
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
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.WRITING, use_planning_model=False) # 寫作使用主要模型
        
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
            
            # 添加章節完成檢測
            self.check_chapter_completion(chapter_index)
            
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
        """簡化版世界設定更新 - 智能檢測重複和更新"""
        
        prompt = f"""
分析以下段落，更新世界設定。請遵循以下規則：

【當前世界設定】
角色：{json.dumps(self.project.world_building.characters, ensure_ascii=False)}
場景：{json.dumps(self.project.world_building.settings, ensure_ascii=False)}
名詞：{json.dumps(self.project.world_building.terminology, ensure_ascii=False)}

【新段落內容】
{content}

【更新規則】
1. 如果角色/場景/名詞已存在但有新信息，請在原描述基礎上補充或修正
2. 如果是全新的項目，才添加到new_*陣列中
3. 如果是更新既有項目，請放到update_*陣列中
4. 每個描述控制在15字內
5. 忽略不重要的細節

輸出格式：
{{
    "new_characters": [
        {{"name": "新角色名", "desc": "描述"}}
    ],
    "update_characters": [
        {{"name": "既有角色名", "desc": "更新後的完整描述"}}
    ],
    "new_settings": [],
    "update_settings": [],
    "new_terms": [],
    "update_terms": [],
    "plot_points": ["重要情節點"]
}}
        """
        
        try:
            # 導入logger
            import logging
            logger = logging.getLogger(__name__)
            
            result = self.llm_service.call_llm_with_thinking(prompt, TaskType.WORLD_BUILDING, use_planning_model=False)
            
            if result:
                world = self.project.world_building
                
                # Update characters
                for char in result.get("new_characters", []):
                    if char.get("name") and char.get("name") not in world.characters:
                        world.characters[char["name"]] = char.get("desc", "")
                for char in result.get("update_characters", []):
                    if char.get("name") in world.characters:
                        world.characters[char["name"]] = char.get("desc", "")

                # Update settings
                for setting in result.get("new_settings", []):
                    if setting.get("name") and setting.get("name") not in world.settings:
                        world.settings[setting["name"]] = setting.get("desc", "")
                for setting in result.get("update_settings", []):
                    if setting.get("name") in world.settings:
                        world.settings[setting["name"]] = setting.get("desc", "")

                # Update terminology
                for term in result.get("new_terms", []):
                    if term.get("term") and term.get("term") not in world.terminology:
                        world.terminology[term["term"]] = term.get("def", "")
                for term in result.get("update_terms", []):
                    if term.get("term") in world.terminology:
                        world.terminology[term["term"]] = term.get("def", "")

                # Update plot points
                for plot in result.get("plot_points", []):
                    if plot and plot not in world.plot_points:
                        world.plot_points.append(plot)
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
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
    
    def check_chapter_completion(self, chapter_index: int) -> bool:
        """檢查章節是否完成"""
        
        if chapter_index >= len(self.project.chapters):
            return False
        
        chapter = self.project.chapters[chapter_index]
        
        # 檢查所有段落是否完成
        completed_paragraphs = sum(1 for p in chapter.paragraphs if p.status == CreationStatus.COMPLETED)
        total_paragraphs = len(chapter.paragraphs)
        
        if completed_paragraphs == total_paragraphs and total_paragraphs > 0:
            # 章節完成，標記狀態
            chapter.status = CreationStatus.COMPLETED
            
            # 添加這行：觸發世界設定整理
            self.consolidate_world_after_chapter(chapter_index)
            
            self.debug_log(f"🎉 第{chapter_index+1}章《{chapter.title}》完成！")
            return True
        
        return False

    def consolidate_world_after_chapter(self, chapter_index: int):
        """章節完成後執行世界設定整理"""
        
        def run_consolidation():
            try:
                self.debug_log(f"🧹 開始整理第{chapter_index+1}章後的世界設定...")
                
                # 調用LLM進行設定整理
                consolidated_world = self._consolidate_world_comprehensive()
                
                if consolidated_world:
                    self.project.world_building = consolidated_world
                    self.debug_log(f"✅ 第{chapter_index+1}章世界設定整理完成")
                
            except Exception as e:
                self.debug_log(f"❌ 第{chapter_index+1}章設定整理失敗: {str(e)}")
        
        threading.Thread(target=run_consolidation, daemon=True).start()

    def _consolidate_world_comprehensive(self) -> Optional[WorldBuilding]:
        """執行全面的世界設定整理"""
        
        consolidation_prompt = f"""
請整理以下世界設定，解決重複和命名不一致問題：

【當前完整設定】
角色：{json.dumps(self.project.world_building.characters, ensure_ascii=False, indent=2)}
場景：{json.dumps(self.project.world_building.settings, ensure_ascii=False, indent=2)}
名詞：{json.dumps(self.project.world_building.terminology, ensure_ascii=False, indent=2)}

【整理要求】
1. 合併重複角色：如"疤面男"、"疤面大漢"合併為一個主要項目
2. 統一場景命名：相關場景合併，如"下水道"系列
3. 歸類相似名詞：如各種"霧氣"歸類到主要術語
4. 建立標準命名：每類事物確立一個標準名稱

輸出格式：
{{
    "characters": {{"林恩曦": "女主角描述", "疤面男": "合併後描述"}},
    "settings": {{"上庄": "主要舞台", "下水道系統": "合併後場景"}},
    "terminology": {{"陰陽眼": "特殊能力", "黑霧": "合併後術語"}},
    "plot_points": ["重要情節點1", "重要情節點2"],
    "changes_log": ["合併了3個重複角色", "整合了5個場景"]
}}
        """
        
        try:
            result = self.llm_service.call_llm_with_thinking(
                consolidation_prompt, TaskType.WORLD_BUILDING, use_planning_model=True
            )
            
            if result:
                # 記錄變更
                if "changes_log" in result:
                    for change in result["changes_log"]:
                        self.debug_log(f"🔧 設定整理: {change}")
                
                # 創建新的世界設定對象
                return WorldBuilding(
                    characters=result.get("characters", {}),
                    settings=result.get("settings", {}),
                    terminology=result.get("terminology", {}),
                    plot_points=result.get("plot_points", []),
                    chapter_notes=self.project.world_building.chapter_notes
                )
            
            return None
            
        except Exception as e:
            self.debug_log(f"❌ 世界設定整理失敗: {str(e)}")
            return None

    def _get_chapter_full_content(self, chapter_index: int) -> str:
        """獲取章節完整內容"""
        chapter = self.project.chapters[chapter_index]
        content_parts = []
        
        for i, paragraph in enumerate(chapter.paragraphs):
            if paragraph.content:
                content_parts.append(paragraph.content)
        
        return "\n\n".join(content_parts)

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