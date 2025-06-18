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
{self._get_world_context(chapter_index)}

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

輸出格式：
{{
    "paragraphs": [
        {{
            "order": 1,
            "purpose": "段落目的說明",
            "content_type": "內容類型（如：對話、描述、動作等）",
            "key_points": ["要點1", "要點2"],
            "estimated_words": 300,
            "mood": "情感氛圍"
        }}
    ]
}}
        """
        
        result = self.llm_service.call_llm_with_thinking(prompt, TaskType.PARAGRAPHS, use_planning_model=True)
        
        if result and "paragraphs" in result:
            paragraphs = []
            for para_data in result["paragraphs"]:
                paragraph = Paragraph(
                    order=para_data.get("order", 0),
                    purpose=para_data.get("purpose", ""),
                    content_type=para_data.get("content_type", ""),
                    key_points=para_data.get("key_points", []),
                    estimated_words=para_data.get("estimated_words", 0),
                    mood=para_data.get("mood", "")
                )
                paragraphs.append(paragraph)
            
            chapter.paragraphs = paragraphs
            
            # 調試信息：確認段落已添加
            self.debug_log(f"📝 第{chapter_index+1}章成功劃分出{len(paragraphs)}個段落")
            for i, p in enumerate(paragraphs):
                self.debug_log(f"   段落{i+1}: {p.purpose} (order={p.order}, status={p.status.value})")
            
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
            
            # 調試信息：確認段落已寫作完成
            self.debug_log(f"✅ 第{chapter_index+1}章第{paragraph_index+1}段寫作完成 (字數:{paragraph.word_count}, 狀態:{paragraph.status.value})")
            
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
        """段落分析 - 純添加模式，不修改既有條目，並支援章節情節點分組"""
        
        # 初始化當前章節的情節點區域
        self._ensure_chapter_plot_area(chapter_index)
        
        prompt = f"""
分析以下段落，從中提取新的世界設定元素。請嚴格遵循純添加原則：

【當前已存在的設定】
角色：{list(self.project.world_building.characters.keys())}
場景：{list(self.project.world_building.settings.keys())}
名詞：{list(self.project.world_building.terminology.keys())}

【第{chapter_index + 1}章段落內容】
{content}

【純添加規則】
1. 只添加全新的角色/場景/名詞，絕對不修改已存在的條目
2. 如果角色/場景/名詞已在列表中，跳過，不要添加到輸出
3. 只添加在段落中明確出現的新元素
4. 描述控制在15字內，基於段落實際內容
5. 不要推測或創作未明確提及的信息

【情節點處理要求】
6. 重要情節點要寫得更細更完整，包含具體發生了什麼
7. 關注劇情進程、角色行動、對話要點、環境變化
8. 每個情節點應該是完整的描述，方便之後彙整

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
    "detailed_plot_points": ["該段落中的詳細重要情節點，包含具體情況和發展"]
}}

注意：只輸出真正新增的項目，不要重複已存在的設定。情節點要詳細完整。
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

                # 處理詳細情節點 - 分別加入全域和章節專屬區域
                for plot in result.get("detailed_plot_points", []):
                    if plot:
                        # 加入全域情節點（向後兼容）
                        if plot not in world.plot_points:
                            world.plot_points.append(plot)
                        
                        # 加入當前章節的情節點區域
                        if plot not in world.current_chapter_plot_points:
                            world.current_chapter_plot_points.append(plot)
                            self.debug_log(f"📖 第{chapter_index + 1}章新增情節點: {plot}")
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"世界設定添加失敗: {str(e)}")
    
    def _ensure_chapter_plot_area(self, chapter_index: int):
        """確保當前章節的情節點區域已初始化"""
        if chapter_index is None:
            return
            
        world = self.project.world_building
        
        # 如果這是新章節，清空當前章節情節點累積區
        if chapter_index not in world.chapter_plot_summaries:
            world.current_chapter_plot_points = []  # 重置當前章節累積
            
            # 創建章節標題
            chapter_title = ""
            if chapter_index < len(self.project.chapters):
                chapter_title = self.project.chapters[chapter_index].title
            
            # 初始化該章節的情節摘要區域
            from ..models.data_models import ChapterPlotSummary
            world.chapter_plot_summaries[chapter_index] = ChapterPlotSummary(
                chapter_index=chapter_index,
                chapter_title=chapter_title
            )
            self.debug_log(f"🔄 初始化第{chapter_index + 1}章情節追蹤區域")

    def _get_world_context(self, current_chapter_index: int = None) -> str:
        """獲取世界設定上下文，包含前面章節的情節摘要"""
        world = self.project.world_building
        context = []
        
        # 基本世界設定
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
        
        # 添加前面章節的情節摘要（如果有指定當前章節）
        if current_chapter_index is not None and world.chapter_plot_summaries:
            context.append("\n=== 前面章節情節流水帳 ===")
            
            for chapter_idx in range(current_chapter_index):
                if chapter_idx in world.chapter_plot_summaries:
                    summary = world.chapter_plot_summaries[chapter_idx]
                    context.append(f"\n【第{chapter_idx + 1}章《{summary.chapter_title}》】")
                    if summary.summary:
                        context.append(summary.summary)
        
        # 添加當前章節正在累積的情節點（如果有）
        if current_chapter_index is not None and world.current_chapter_plot_points:
            context.append(f"\n=== 第{current_chapter_index + 1}章目前情節點 ===")
            for i, point in enumerate(world.current_chapter_plot_points):
                context.append(f"{i + 1}. {point}")
        
        return "\n".join(context)
    
    def check_chapter_completion(self, chapter_index: int, trigger_consolidation: bool = True) -> bool:
        """檢查章節是否完成"""
        
        if chapter_index >= len(self.project.chapters):
            return False
        
        chapter = self.project.chapters[chapter_index]
        
        # 檢查所有段落是否完成
        completed_paragraphs = sum(1 for p in chapter.paragraphs if p.status == CreationStatus.COMPLETED)
        total_paragraphs = len(chapter.paragraphs)
        
        # 調試信息：檢測狀態
        self.debug_log(f"🔍 第{chapter_index+1}章完成檢測: {completed_paragraphs}/{total_paragraphs} 段落完成")
        
        if completed_paragraphs == total_paragraphs and total_paragraphs > 0:
            # 檢查章節是否已經完成處理，避免重複觸發
            was_already_completed = chapter.status == CreationStatus.COMPLETED
            
            # 標記章節狀態為完成
            chapter.status = CreationStatus.COMPLETED
            
            # 只有在首次完成且允許觸發整理時才執行整理
            if not was_already_completed and trigger_consolidation:
                self.consolidate_world_after_chapter(chapter_index)
                self.debug_log(f"🎉 第{chapter_index+1}章《{chapter.title}》完成！")
            
            return True
        
        return False

    def consolidate_world_after_chapter(self, chapter_index: int, sync_mode: bool = False):
        """章節完成後執行世界設定整理和情節摘要生成"""
        
        def run_consolidation():
            try:
                self.debug_log(f"🧹 開始處理第{chapter_index+1}章完成後的整理工作...")
                
                # 步驟1: 生成該章節的情節摘要
                self.debug_log(f"📝 步驟1: 生成第{chapter_index+1}章情節摘要")
                self._generate_chapter_plot_summary(chapter_index)
                
                # 步驟2: 整理世界設定（只處理角色、場景、專有名詞）
                self.debug_log(f"🌍 步驟2: 整理第{chapter_index+1}章世界設定")
                consolidated_world = self._consolidate_world_only()
                
                if consolidated_world:
                    # 保留情節點和章節摘要
                    consolidated_world.plot_points = self.project.world_building.plot_points
                    consolidated_world.current_chapter_plot_points = self.project.world_building.current_chapter_plot_points
                    consolidated_world.chapter_plot_summaries = self.project.world_building.chapter_plot_summaries
                    
                    self.project.world_building = consolidated_world
                    self.debug_log(f"✅ 第{chapter_index+1}章世界設定整理完成")
                
                # 步驟3: 獨立處理本章節的情節點縮減
                self.debug_log(f"📋 步驟3: 處理第{chapter_index+1}章情節點縮減")
                self._consolidate_chapter_plot_points(chapter_index)
                
                self.debug_log(f"🎉 第{chapter_index+1}章所有整理工作完成")
                
            except Exception as e:
                self.debug_log(f"❌ 第{chapter_index+1}章整理工作失敗: {str(e)}")
        
        if sync_mode:
            # 同步模式：直接執行，等待完成
            run_consolidation()
        else:
            # 異步模式：背景線程執行
            threading.Thread(target=run_consolidation, daemon=True).start()
    
    def _generate_chapter_plot_summary(self, chapter_index: int):
        """為完成的章節生成詳細情節摘要"""
        
        try:
            world = self.project.world_building
            chapter = self.project.chapters[chapter_index]
            
            # 檢查是否已經生成過摘要，避免重複處理
            if (chapter_index in world.chapter_plot_summaries and 
                world.chapter_plot_summaries[chapter_index].summary):
                self.debug_log(f"📝 第{chapter_index+1}章摘要已存在，跳過重複生成")
                return
            
            # 獲取該章節累積的所有情節點
            current_plot_points = world.current_chapter_plot_points
            
            if not current_plot_points:
                self.debug_log(f"📝 第{chapter_index+1}章沒有情節點，跳過摘要生成")
                return
            
            # 獲取章節完整內容
            chapter_content = self._get_chapter_full_content(chapter_index)
            
            plot_summary_prompt = f"""
基於以下章節的情節點，生成一份簡潔的情節摘要流水帳：

【章節資訊】
章節：第{chapter_index + 1}章《{chapter.title}》

【該章節累積的情節點】
{chr(10).join(f"{i+1}. {point}" for i, point in enumerate(current_plot_points))}

【情節摘要要求】
1. 依照情節點順序，產出簡潔的劇情流水帳
2. 快速帶過情節，不要冗長描述
3. 劇情進程要清楚呈現（按時間順序）
4. 包含劇情中登場的所有元素（角色、物品、場景等）
5. 用簡短語句串連，像看電影快轉的感覺
6. 控制總字數在200字以內

輸出格式：
{{
    "plot_summary": "簡潔的情節流水帳，按時間順序快速帶過劇情發展",
    "characters_involved": ["涉及的角色名"],
    "settings_involved": ["涉及的場景名"],
    "key_items": ["重要物品或道具"]
}}

注意：摘要要簡潔明快，像劇情大綱一樣直接了當。
            """
            
            result = self.llm_service.call_llm_with_thinking(
                plot_summary_prompt, TaskType.WORLD_BUILDING, use_planning_model=True
            )
            
            if result and chapter_index in world.chapter_plot_summaries:
                summary = world.chapter_plot_summaries[chapter_index]
                
                # 更新章節摘要數據
                summary.plot_points = current_plot_points.copy()
                summary.summary = result.get("plot_summary", "")
                summary.key_developments = []  # 簡化版本不使用
                summary.characters_introduced = result.get("characters_involved", [])
                summary.settings_introduced = result.get("settings_involved", [])
                
                self.debug_log(f"📋 第{chapter_index+1}章情節摘要生成完成")
                self.debug_log(f"   摘要長度: {len(summary.summary)}字")
                self.debug_log(f"   涉及角色: {len(summary.characters_introduced)}個")
                self.debug_log(f"   涉及場景: {len(summary.settings_introduced)}個")
                if result.get("key_items"):
                    self.debug_log(f"   重要物品: {', '.join(result.get('key_items', []))}")
                
                # 清空當前章節累積區，為下一章準備
                world.current_chapter_plot_points = []
                
        except Exception as e:
            self.debug_log(f"❌ 第{chapter_index+1}章情節摘要生成失敗: {str(e)}")

    def _consolidate_world_only(self) -> Optional[WorldBuilding]:
        """只整理世界設定（角色、場景、專有名詞），不處理情節點"""
        
        consolidation_prompt = f"""
執行世界設定條目的嚴格合併與整理。請嚴格按照以下規則進行：

【當前世界設定】
角色：{json.dumps(self.project.world_building.characters, ensure_ascii=False, indent=2)}
場景：{json.dumps(self.project.world_building.settings, ensure_ascii=False, indent=2)}
名詞：{json.dumps(self.project.world_building.terminology, ensure_ascii=False, indent=2)}

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

輸出格式：
{{
    "characters": {{"標準角色名": "基於原始條目的合併描述"}},
    "settings": {{"標準場景名": "基於原始條目的合併描述"}},
    "terminology": {{"標準名詞": "基於原始條目的合併定義"}},
    "changes_log": [
        "合併角色：'疤面男'+'疤面大漢' -> '疤面男'（基於頻率選擇）",
        "合併場景：'下水道入口'+'下水道通道' -> '下水道系統'（基於範圍整合）"
    ]
}}

注意：如果沒有發現需要合併的重複項目，請返回原始設定並在changes_log中說明「未發現需要合併的重複項目」。
        """
        
        try:
            # 使用規劃模型進行嚴格的設定整理
            result = self.llm_service.call_llm_with_thinking(
                consolidation_prompt, TaskType.WORLD_BUILDING, use_planning_model=True
            )
            
            if result:
                # 記錄詳細的變更日誌
                if "changes_log" in result:
                    self.debug_log("🔧 世界設定整理變更記錄:")
                    for change in result["changes_log"]:
                        self.debug_log(f"   📋 {change}")
                
                # 建立合併後的世界設定（不包含情節點，這些會被調用者手動設置）
                consolidated_world = WorldBuilding(
                    characters=result.get("characters", self.project.world_building.characters),
                    settings=result.get("settings", self.project.world_building.settings),
                    terminology=result.get("terminology", self.project.world_building.terminology),
                    plot_points=[],  # 將由調用者設置
                    relationships=self.project.world_building.relationships,
                    style_guide=self.project.world_building.style_guide,
                    chapter_notes=self.project.world_building.chapter_notes
                )
                
                # 統計合併效果
                original_count = (len(self.project.world_building.characters) + 
                                len(self.project.world_building.settings) + 
                                len(self.project.world_building.terminology))
                
                new_count = (len(consolidated_world.characters) + 
                           len(consolidated_world.settings) + 
                           len(consolidated_world.terminology))
                
                if original_count != new_count:
                    self.debug_log(f"🧹 世界設定整理完成：{original_count} -> {new_count} 項目")
                else:
                    self.debug_log("🧹 世界設定整理完成：未發現需要合併的項目")
                
                return consolidated_world
            
            return None
            
        except Exception as e:
            self.debug_log(f"❌ 世界設定整理失敗: {str(e)}")
            return None

    def _consolidate_chapter_plot_points(self, chapter_index: int):
        """獨立處理本章節的情節點縮減摘要"""
        
        try:
            world = self.project.world_building
            
            # 獲取本章節的情節點
            if chapter_index not in world.chapter_plot_summaries:
                self.debug_log(f"⚠️ 第{chapter_index+1}章沒有情節摘要，跳過情節點處理")
                return
                
            chapter_summary = world.chapter_plot_summaries[chapter_index]
            if not chapter_summary.plot_points:
                self.debug_log(f"⚠️ 第{chapter_index+1}章沒有情節點，跳過處理")
                return
            
            plot_consolidation_prompt = f"""
對第{chapter_index+1}章的情節點進行縮減和摘要處理：

【本章節情節點】
{chr(10).join(f"{i+1}. {point}" for i, point in enumerate(chapter_summary.plot_points))}

【處理要求】
1. 將相似或重複的情節點合併
2. 保留最關鍵的劇情轉折點
3. 確保劇情邏輯完整
4. 縮減到3-5個核心情節點
5. 每個情節點要簡潔明確

輸出格式：
{{
    "consolidated_plot_points": ["核心情節點1", "核心情節點2", "核心情節點3"],
    "reduction_log": ["合併了xxx情節點", "保留了關鍵轉折xxx"]
}}

注意：標示這是第{chapter_index+1}章的情節點。
            """
            
            result = self.llm_service.call_llm_with_thinking(
                plot_consolidation_prompt, TaskType.WORLD_BUILDING, use_planning_model=True
            )
            
            if result:
                consolidated_points = result.get("consolidated_plot_points", [])
                
                # 更新全域情節點（加上章節標示）
                tagged_points = [f"【第{chapter_index+1}章】{point}" for point in consolidated_points]
                
                # 移除舊的該章節情節點
                existing_plot_points = []
                for plot in world.plot_points:
                    if not plot.startswith(f"【第{chapter_index+1}章】"):
                        existing_plot_points.append(plot)
                
                # 添加新的縮減後情節點
                world.plot_points = existing_plot_points + tagged_points
                
                self.debug_log(f"📋 第{chapter_index+1}章情節點縮減完成：{len(chapter_summary.plot_points)} -> {len(consolidated_points)}個")
                
                if result.get("reduction_log"):
                    for log in result["reduction_log"]:
                        self.debug_log(f"   📝 {log}")
                
        except Exception as e:
            self.debug_log(f"❌ 第{chapter_index+1}章情節點處理失敗: {str(e)}")

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