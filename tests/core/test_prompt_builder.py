"""
測試 core.prompt_builder 模組
"""

import unittest
import sys
import os
from unittest.mock import Mock

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.core.prompt_builder import DynamicPromptBuilder, PromptManager
from novel_writer.models import NovelProject, TaskType, Chapter, Paragraph, GlobalWritingConfig, StageSpecificConfig
from novel_writer.models.enums import WritingStyle, PacingStyle


class TestPromptManager(unittest.TestCase):
    """測試提示詞管理器"""
    
    def test_token_limits(self):
        """測試token限制設定"""
        # 檢查所有任務類型都有token限制
        for task_type in TaskType:
            limit = PromptManager.get_token_limit(task_type)
            self.assertIsInstance(limit, int)
            self.assertGreater(limit, 0)
        
        # 檢查具體的token限制
        self.assertEqual(PromptManager.get_token_limit(TaskType.OUTLINE), 8000)
        self.assertEqual(PromptManager.get_token_limit(TaskType.CHAPTERS), 6000)
        self.assertEqual(PromptManager.get_token_limit(TaskType.WRITING), 4000)
    
    def test_system_prompts(self):
        """測試系統提示詞創建"""
        for task_type in TaskType:
            prompt = PromptManager.create_system_prompt(task_type)
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 0)
            
            # 檢查是否包含任務類型相關的關鍵詞
            if task_type == TaskType.OUTLINE:
                self.assertIn("大綱", prompt)
            elif task_type == TaskType.CHAPTERS:
                self.assertIn("章節", prompt)
            elif task_type == TaskType.WRITING:
                self.assertIn("寫作", prompt)
    
    def test_system_prompt_consistency(self):
        """測試系統提示詞的一致性"""
        # 多次調用應該返回相同的結果
        for task_type in TaskType:
            prompt1 = PromptManager.create_system_prompt(task_type)
            prompt2 = PromptManager.create_system_prompt(task_type)
            self.assertEqual(prompt1, prompt2)


class TestDynamicPromptBuilder(unittest.TestCase):
    """測試動態提示詞建構器"""
    
    def setUp(self):
        """設置測試環境"""
        self.project = NovelProject()
        self.project.title = "測試小說"
        self.project.theme = "科幻冒險"
        self.project.outline = "這是一個關於太空探險的故事..."
        
        # 設置全局配置
        self.project.global_config = GlobalWritingConfig()
        self.project.global_config.writing_style = WritingStyle.THIRD_PERSON_LIMITED
        self.project.global_config.pacing_style = PacingStyle.FAST_PACED
        self.project.global_config.target_chapter_words = 2500
        self.project.global_config.continuous_themes = ["友情", "成長"]
        
        self.builder = DynamicPromptBuilder(self.project)
    
    def test_initialization(self):
        """測試初始化"""
        self.assertEqual(self.builder.project, self.project)
    
    def test_build_outline_prompt(self):
        """測試大綱提示詞建構"""
        from novel_writer.models import StageSpecificConfig
        stage_config = StageSpecificConfig()
        stage_config.additional_prompt = "請確保故事有懸疑元素"
        
        prompt = self.builder.build_outline_prompt(
            title=self.project.title,
            theme=self.project.theme, 
            stage_config=stage_config
        )
        
        # 檢查包含基本信息
        self.assertIn(self.project.title, prompt)
        self.assertIn(self.project.theme, prompt)
        self.assertIn("懸疑元素", prompt)
        
        # 檢查包含風格信息
        self.assertIn("第三人稱限制視角", prompt)
        self.assertIn("快節奏", prompt)
        
        # 檢查包含主題
        self.assertIn("友情", prompt)
        self.assertIn("成長", prompt)
        
        # 檢查JSON格式要求
        self.assertIn("JSON", prompt)
    
    def test_build_chapter_division_prompt(self):
        """測試章節劃分提示詞建構"""
        additional_prompt = "每章約2500字"
        prompt = self.builder.build_chapter_division_prompt(additional_prompt)
        
        # 檢查包含大綱
        self.assertIn(self.project.outline, prompt)
        self.assertIn(additional_prompt, prompt)
        
        # 檢查字數要求
        self.assertIn("2500", prompt)
        
        # 檢查JSON格式
        self.assertIn("JSON", prompt)
    
    def test_build_paragraph_writing_prompt_basic(self):
        """測試基本段落寫作提示詞"""
        # 創建測試章節和段落
        chapter = Chapter(title="第一章：啟程", summary="主角開始冒險")
        paragraph = Paragraph(order=1, purpose="場景描述", estimated_words=300)
        
        prompt = self.builder.build_paragraph_writing_prompt(
            chapter=chapter,
            paragraph=paragraph,
            chapter_index=0,
            paragraph_index=0
        )
        
        # 檢查包含章節信息
        self.assertIn(chapter.title, prompt)
        self.assertIn(chapter.summary, prompt)
        
        # 檢查包含段落信息
        self.assertIn(paragraph.purpose, prompt)
        self.assertIn("300", prompt)
        
        # 檢查包含風格指導
        self.assertIn("第三人稱限制視角", prompt)
    
    def test_build_paragraph_writing_prompt_with_context(self):
        """測試包含上下文的段落寫作提示詞"""
        chapter = Chapter(title="第二章：挑戰", summary="面對困難")
        paragraph = Paragraph(order=2, purpose="人物對話", estimated_words=250)
        
        # 模擬前文內容
        previous_content = "主角走進了神秘的洞穴。"
        
        prompt = self.builder.build_paragraph_writing_prompt(
            chapter=chapter,
            paragraph=paragraph,
            chapter_index=1,
            paragraph_index=1,
            previous_content=previous_content,
            selected_context="特定上下文內容"
        )
        
        # 檢查包含前文內容
        self.assertIn(previous_content, prompt)
        self.assertIn("特定上下文內容", prompt)
        
        # 檢查對話相關指導
        self.assertIn("對話", prompt)
    
    def test_creativity_instructions(self):
        """測試創意指導"""
        creativity_levels = [0.3, 0.5, 0.7, 0.9]
        
        for level in creativity_levels:
            instruction = self.builder._get_creativity_instruction(level)
            self.assertIsInstance(instruction, str)
            self.assertGreater(len(instruction), 0)
            
            if level < 0.5:
                self.assertIn("保守", instruction)
            elif level > 0.7:
                self.assertIn("創新", instruction)
    
    def test_word_count_calculation(self):
        """測試字數計算"""
        test_cases = [
            ("short", 200),
            ("medium", 400), 
            ("long", 600),
            ("auto", 300)  # 預設值
        ]
        
        for length_pref, expected_min in test_cases:
            words = self.builder._calculate_paragraph_words(length_pref, 300)
            if length_pref != "auto":
                self.assertGreaterEqual(words, expected_min)
            else:
                self.assertEqual(words, expected_min)
    
    def test_length_guidance(self):
        """測試長度指導"""
        guidance = self.builder._get_length_guidance(250, True)
        self.assertIn("250", guidance)
        self.assertIn("嚴格", guidance)
        
        guidance = self.builder._get_length_guidance(300, False)
        self.assertIn("300", guidance)
        self.assertNotIn("嚴格", guidance)
    
    def test_naming_constraints(self):
        """測試命名約束"""
        # 添加世界設定
        self.project.world_building.characters = {
            "主角": "勇敢的少年",
            "反派": "邪惡巫師"
        }
        self.project.world_building.settings = {
            "王國": "和平的王國",
            "森林": "神秘森林"
        }
        
        constraints = self.builder._build_naming_constraints()
        
        self.assertIn("主角", constraints)
        self.assertIn("反派", constraints)
        self.assertIn("王國", constraints)
        self.assertIn("森林", constraints)
    
    def test_common_suffix(self):
        """測試通用後綴"""
        base_prompt = "基礎提示詞"
        suffix = self.builder._add_common_suffix(base_prompt)
        
        # 檢查包含原始提示詞
        self.assertIn(base_prompt, suffix)
        
        # 檢查包含通用指導
        self.assertIn("JSON", suffix)
        self.assertIn("格式", suffix)
    
    def test_with_stage_config(self):
        """測試階段特定配置"""
        # 創建階段配置
        stage_config = StageSpecificConfig()
        stage_config.additional_prompt = "特別指示：注意節奏"
        stage_config.creativity_level = 0.8
        stage_config.detail_level = "詳細"
        
        chapter = Chapter(title="測試章節", summary="測試")
        paragraph = Paragraph(order=1, purpose="測試段落")
        
        prompt = self.builder.build_paragraph_writing_prompt(
            chapter=chapter,
            paragraph=paragraph,
            chapter_index=0,
            paragraph_index=0,
            stage_config=stage_config
        )
        
        # 檢查包含階段特定指示
        self.assertIn("特別指示：注意節奏", prompt)
        self.assertIn("詳細", prompt)
        
        # 檢查創意等級的影響
        self.assertIn("創新", prompt)  # 0.8 是高創意等級
    
    def test_empty_project_handling(self):
        """測試空項目處理"""
        empty_project = NovelProject()
        empty_builder = DynamicPromptBuilder(empty_project)
        
        # 即使項目為空，也應該能生成提示詞
        prompt = empty_builder.build_outline_prompt()
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
    
    def test_special_characters_in_content(self):
        """測試內容中的特殊字符"""
        self.project.title = "《魔法學院》第一部：啟程"
        self.project.theme = "奇幻冒險——友情與成長的故事"
        
        prompt = self.builder.build_outline_prompt()
        
        # 檢查特殊字符被正確處理
        self.assertIn("《魔法學院》", prompt)
        self.assertIn("——", prompt)


if __name__ == '__main__':
    unittest.main()