"""
提示詞建構和管理模組
負責動態構建各種任務類型的提示詞以及統一管理提示詞模板
"""

import json
from typing import Dict, Any, Optional, Callable

from ..models.enums import TaskType
from ..models.data_models import NovelProject, StageSpecificConfig


class DynamicPromptBuilder:
    """動態Prompt構建器"""
    
    def __init__(self, project: NovelProject):
        self.project = project
        self.global_config = project.global_config
    
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
- 預計章節數：10-20章
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
- 章節數量：10-20章
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

        # 強化世界設定用詞約束（requirement #3）
        naming_constraints = self._build_enhanced_naming_constraints()

        if naming_constraints:
            base_prompt += f"""

{naming_constraints}

【⚠️ 關鍵要求】必須嚴格按照以上世界設定用詞進行寫作。這些設定經過多章節整理與合併，是故事的核心框架，絕對不可偏離。任何人物、地點、名詞都必須使用標準設定中的確切名稱和描述。"""

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

    def _build_enhanced_naming_constraints(self) -> str:
        """構建強化的世界設定用詞約束"""
        world_building = self.project.world_building
        constraints = []
        
        # 如果沒有任何世界設定，返回基本提醒
        if not (world_building.characters or world_building.settings or world_building.terminology):
            return "【📝 世界設定提醒】目前世界設定檔為空，寫作時請注意建立一致的人物和場景命名。"
        
        constraints.append("🌍【世界設定框架 - 必須嚴格遵守】")
        constraints.append("以下設定經過多章節累積與整理，是故事的標準框架：")
        constraints.append("")
        
        # 角色設定 - 強化版
        if world_building.characters:
            constraints.append("👥【標準角色設定】")
            char_count = 0
            for name, desc in world_building.characters.items():
                if char_count >= 15:  # 增加顯示數量
                    constraints.append(f"... (還有{len(world_building.characters) - 15}個角色)")
                    break
                constraints.append(f"✓ {name}：{desc}")
                char_count += 1
            constraints.append("")
            constraints.append("🚨 角色命名鐵律：")
            constraints.append("  - 必須使用上述確切名稱，一字不差")
            constraints.append("  - 禁止創造變體、別名、昵稱")
            constraints.append("  - 禁止修改角色設定描述")
            constraints.append("")
        
        # 場景設定 - 強化版
        if world_building.settings:
            constraints.append("🏞️【標準場景設定】")
            setting_count = 0
            for name, desc in world_building.settings.items():
                if setting_count >= 12:  # 增加顯示數量
                    constraints.append(f"... (還有{len(world_building.settings) - 12}個場景)")
                    break
                constraints.append(f"✓ {name}：{desc}")
                setting_count += 1
            constraints.append("")
            constraints.append("🚨 場景命名鐵律：")
            constraints.append("  - 必須使用上述標準場景名稱")
            constraints.append("  - 禁止創造相似或變體名稱")
            constraints.append("  - 場景描述必須與設定一致")
            constraints.append("")
        
        # 專有名詞 - 強化版
        if world_building.terminology:
            constraints.append("📚【標準術語設定】")
            term_count = 0
            for term, definition in world_building.terminology.items():
                if term_count >= 12:  # 增加顯示數量
                    constraints.append(f"... (還有{len(world_building.terminology) - 12}個術語)")
                    break
                constraints.append(f"✓ {term}：{definition}")
                term_count += 1
            constraints.append("")
            constraints.append("🚨 術語使用鐵律：")
            constraints.append("  - 必須使用標準術語的確切定義")
            constraints.append("  - 禁止創造同義詞或相似概念")
            constraints.append("  - 術語含義不可隨意擴展")
            constraints.append("")
        
        # 重要情節線索
        if world_building.plot_points:
            plot_display = world_building.plot_points[:8]  # 顯示前8個
            constraints.append("📖【重要情節線索】")
            for i, plot in enumerate(plot_display, 1):
                constraints.append(f"{i}. {plot}")
            if len(world_building.plot_points) > 8:
                constraints.append(f"... (還有{len(world_building.plot_points) - 8}個情節點)")
            constraints.append("")
        
        # 總結約束
        constraints.append("🔒【終極約束原則】")
        constraints.append("1. 世界設定 = 故事DNA，不可變動")
        constraints.append("2. 人物、地點、術語 = 已定義標準，嚴格執行")
        constraints.append("3. 任何偏離 = 破壞故事連貫性")
        constraints.append("4. 寫作創意 = 在標準框架內發揮")
        
        return "\n".join(constraints)
    
    def _build_naming_constraints(self, world_building) -> str:
        """構建命名約束指導（保留舊版本以維持兼容性）"""
        return self._build_enhanced_naming_constraints()


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
    "estimated_chapters": 15,
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
    "word_count": 500
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