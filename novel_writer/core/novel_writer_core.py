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
        """段落分析 - 純添加模式，不修改既有條目"""
        
        prompt = f"""
分析以下段落，從中提取新的世界設定元素。請嚴格遵循純添加原則：

【當前已存在的設定】
角色：{list(self.project.world_building.characters.keys())}
場景：{list(self.project.world_building.settings.keys())}
名詞：{list(self.project.world_building.terminology.keys())}

【新段落內容】
{content}

【純添加規則】
1. 只添加全新的角色/場景/名詞，絕對不修改已存在的條目
2. 如果角色/場景/名詞已在列表中，跳過，不要添加到輸出
3. 只添加在段落中明確出現的新元素
4. 描述控制在15字內，基於段落實際內容
5. 不要推測或創作未明確提及的信息

輸出格式：
{{
    "new_characters": [
        {{"name": "新角色名", "desc": "基於段落的簡短描述"}}
    ],
    "new_settings": [
        {{"name": "新場景名", "desc": "基於段落的簡短描述"}}
    ],
    "new_terms": [
        {{"name": "新名詞", "desc": "基於段落的簡短定義"}}
    ],
    "plot_points": ["段落中的重要情節點"]
}}

注意：只輸出真正新增的項目，不要重複已存在的設定。
        """
        
        try:
            # 導入logger
            import logging
            logger = logging.getLogger(__name__)
            
            result = self.llm_service.call_llm_with_thinking(prompt, TaskType.WORLD_BUILDING, use_planning_model=False)
            
            if result:
                world = self.project.world_building
                
                # 純添加新角色（不修改既有）
                for char in result.get("new_characters", []):
                    name = char.get("name", "")
                    desc = char.get("desc", "")
                    if name and name not in world.characters:
                        world.characters[name] = desc
                        self.debug_log(f"📝 添加新角色: {name}")

                # 純添加新場景（不修改既有）
                for setting in result.get("new_settings", []):
                    name = setting.get("name", "")
                    desc = setting.get("desc", "")
                    if name and name not in world.settings:
                        world.settings[name] = desc
                        self.debug_log(f"🏗️ 添加新場景: {name}")

                # 純添加新名詞（不修改既有）
                for term in result.get("new_terms", []):
                    name = term.get("name", "")
                    desc = term.get("desc", "")
                    if name and name not in world.terminology:
                        world.terminology[name] = desc
                        self.debug_log(f"📚 添加新名詞: {name}")

                # 添加新情節點
                for plot in result.get("plot_points", []):
                    if plot and plot not in world.plot_points:
                        world.plot_points.append(plot)
                        self.debug_log(f"📖 添加情節點: {plot}")
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"世界設定添加失敗: {str(e)}")
    
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
        """執行全面的世界設定整理 - 嚴格合併模式，由解析器處理"""
        
        consolidation_prompt = f"""
執行世界設定條目的嚴格合併與整理。請嚴格按照以下規則進行：

【當前完整設定】
角色：{json.dumps(self.project.world_building.characters, ensure_ascii=False, indent=2)}
場景：{json.dumps(self.project.world_building.settings, ensure_ascii=False, indent=2)}
名詞：{json.dumps(self.project.world_building.terminology, ensure_ascii=False, indent=2)}
情節點：{json.dumps(self.project.world_building.plot_points, ensure_ascii=False)}

【嚴格合併規則】
1. 重複識別：找出指稱同一事物的多個條目（如："疤面男"、"疤面大漢"、"有疤的男人"）
2. 合併原則：保留最完整的描述，融合其他條目的核心信息
3. 命名標準：選擇最常用或最準確的名稱作為標準名
4. 內容約束：只能基於現有條目內容進行合併，絕對不可創作新內容
5. 無創作規則：不得添加任何未在原始條目中明確提及的信息

【處理步驟】
第一步：識別重複項目
第二步：選定標準名稱
第三步：合併描述內容（僅基於現有內容）
第四步：生成變更日誌

【輸出要求】
- 只輸出確實需要合併的項目
- 描述必須完全基於原始內容，不得增添任何新信息
- 變更日誌必須具體說明合併的依據和過程
- 不限制輸出字數，確保合併後的描述完整準確

輸出格式：
{{
    "characters": {{"標準角色名": "基於原始條目的合併描述"}},
    "settings": {{"標準場景名": "基於原始條目的合併描述"}},
    "terminology": {{"標準名詞": "基於原始條目的合併定義"}},
    "plot_points": ["去重後的情節點"],
    "changes_log": [
        "合併角色：'疤面男'+'疤面大漢' -> '疤面男'（基於頻率選擇）",
        "合併場景：'下水道入口'+'下水道通道' -> '下水道系統'（基於範圍整合）"
    ]
}}

注意：如果沒有發現需要合併的重複項目，請返回原始設定並在changes_log中說明"未發現需要合併的重複項目"。
        """
        
        try:
            # 使用規劃模型進行嚴格的設定整理
            result = self.llm_service.call_llm_with_thinking(
                consolidation_prompt, TaskType.WORLD_BUILDING, use_planning_model=True
            )
            
            if result:
                # 記錄詳細的變更日誌
                if "changes_log" in result:
                    self.debug_log("🔧 開始設定整理變更記錄:")
                    for change in result["changes_log"]:
                        self.debug_log(f"   📋 {change}")
                
                # 建立合併後的世界設定
                consolidated_world = WorldBuilding(
                    characters=result.get("characters", self.project.world_building.characters),
                    settings=result.get("settings", self.project.world_building.settings),
                    terminology=result.get("terminology", self.project.world_building.terminology),
                    plot_points=result.get("plot_points", self.project.world_building.plot_points),
                    relationships=self.project.world_building.relationships,  # 保持不變
                    style_guide=self.project.world_building.style_guide,      # 保持不變
                    chapter_notes=self.project.world_building.chapter_notes   # 保持不變
                )
                
                # 統計合併效果
                original_count = (len(self.project.world_building.characters) + 
                                len(self.project.world_building.settings) + 
                                len(self.project.world_building.terminology) +
                                len(self.project.world_building.plot_points))
                
                new_count = (len(consolidated_world.characters) + 
                           len(consolidated_world.settings) + 
                           len(consolidated_world.terminology) +
                           len(consolidated_world.plot_points))
                
                if original_count != new_count:
                    self.debug_log(f"🧹 設定整理完成：{original_count} -> {new_count} 項目")
                else:
                    self.debug_log("🧹 設定整理完成：未發現需要合併的項目")
                
                return consolidated_world
            
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