"""
測試 models.data_models 模組
"""

import unittest
import sys
import os
from dataclasses import asdict

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.models.data_models import (
    APIConfig, Paragraph, Chapter, WorldBuilding, 
    GlobalWritingConfig, StageSpecificConfig, NovelProject
)
from novel_writer.models.enums import CreationStatus, WritingStyle, PacingStyle


class TestDataModels(unittest.TestCase):
    """測試數據模型"""
    
    def test_api_config_defaults(self):
        """測試 APIConfig 預設值"""
        config = APIConfig()
        
        # 測試預設值
        self.assertEqual(config.base_url, "https://api.openai.com/v1")
        self.assertEqual(config.model, "gpt-4")
        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.api_key, "")
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.timeout, 60)
        self.assertEqual(config.language, "zh-TW")
        self.assertTrue(config.use_traditional_quotes)
        self.assertFalse(config.disable_thinking)
        
        # 測試規劃模型設定
        self.assertFalse(config.use_planning_model)
        self.assertEqual(config.planning_model, "gpt-4-turbo")
    
    def test_api_config_serialization(self):
        """測試 APIConfig 序列化"""
        config = APIConfig(
            api_key="test-key",
            model="gpt-3.5-turbo",
            use_planning_model=True
        )
        
        # 測試序列化
        data = asdict(config)
        self.assertIsInstance(data, dict)
        self.assertEqual(data['api_key'], "test-key")
        self.assertEqual(data['model'], "gpt-3.5-turbo")
        self.assertTrue(data['use_planning_model'])
    
    def test_paragraph_creation(self):
        """測試 Paragraph 創建"""
        paragraph = Paragraph(
            order=1,
            purpose="開場描述",
            content_type="描述",
            estimated_words=200
        )
        
        self.assertEqual(paragraph.order, 1)
        self.assertEqual(paragraph.purpose, "開場描述")
        self.assertEqual(paragraph.content_type, "描述")
        self.assertEqual(paragraph.estimated_words, 200)
        self.assertEqual(paragraph.status, CreationStatus.NOT_STARTED)
        self.assertIsInstance(paragraph.key_points, list)
        self.assertEqual(len(paragraph.key_points), 0)
    
    def test_paragraph_with_content(self):
        """測試包含內容的 Paragraph"""
        paragraph = Paragraph(
            order=2,
            purpose="人物介紹",
            content="小明是一個活潑的少年...",
            key_points=["活潑", "少年", "夢想"],
            status=CreationStatus.COMPLETED
        )
        
        self.assertEqual(paragraph.content, "小明是一個活潑的少年...")
        self.assertEqual(len(paragraph.key_points), 3)
        self.assertEqual(paragraph.status, CreationStatus.COMPLETED)
    
    def test_chapter_creation(self):
        """測試 Chapter 創建"""
        chapter = Chapter(
            title="第一章：開始",
            summary="故事的開始，介紹主人公",
            estimated_words=3000
        )
        
        self.assertEqual(chapter.title, "第一章：開始")
        self.assertEqual(chapter.summary, "故事的開始，介紹主人公")
        self.assertEqual(chapter.estimated_words, 3000)
        self.assertEqual(chapter.status, CreationStatus.NOT_STARTED)
        self.assertIsInstance(chapter.key_events, list)
        self.assertIsInstance(chapter.characters_involved, list)
        self.assertIsInstance(chapter.outline, dict)
        self.assertIsInstance(chapter.paragraphs, list)
    
    def test_chapter_with_paragraphs(self):
        """測試包含段落的 Chapter"""
        paragraph1 = Paragraph(order=1, purpose="開場")
        paragraph2 = Paragraph(order=2, purpose="發展")
        
        chapter = Chapter(
            title="測試章節",
            summary="測試摘要",
            key_events=["事件1", "事件2"],
            characters_involved=["主角", "配角"]
        )
        chapter.paragraphs = [paragraph1, paragraph2]
        
        self.assertEqual(len(chapter.paragraphs), 2)
        self.assertEqual(chapter.paragraphs[0].order, 1)
        self.assertEqual(chapter.paragraphs[1].order, 2)
        self.assertEqual(len(chapter.key_events), 2)
        self.assertEqual(len(chapter.characters_involved), 2)
    
    def test_world_building_creation(self):
        """測試 WorldBuilding 創建"""
        world = WorldBuilding()
        
        # 測試預設值
        self.assertIsInstance(world.characters, dict)
        self.assertIsInstance(world.settings, dict)
        self.assertIsInstance(world.terminology, dict)
        self.assertIsInstance(world.plot_points, list)
        self.assertIsInstance(world.relationships, list)
        self.assertIsInstance(world.chapter_notes, list)
        self.assertEqual(world.style_guide, "")
    
    def test_world_building_with_data(self):
        """測試包含數據的 WorldBuilding"""
        world = WorldBuilding(
            characters={"主角": "勇敢的少年", "反派": "邪惡巫師"},
            settings={"城堡": "古老的石頭城堡", "森林": "神秘的魔法森林"},
            terminology={"魔法": "操控元素的力量"},
            plot_points=["英雄啟程", "遇到導師", "戰勝邪惡"]
        )
        
        self.assertEqual(len(world.characters), 2)
        self.assertEqual(len(world.settings), 2)
        self.assertEqual(len(world.terminology), 1)
        self.assertEqual(len(world.plot_points), 3)
        self.assertIn("主角", world.characters)
        self.assertIn("城堡", world.settings)
    
    def test_global_writing_config(self):
        """測試 GlobalWritingConfig"""
        config = GlobalWritingConfig()
        
        # 測試預設值
        self.assertEqual(config.writing_style, WritingStyle.THIRD_PERSON_LIMITED)
        self.assertEqual(config.pacing_style, PacingStyle.BALANCED)
        self.assertEqual(config.tone, "溫暖")
        self.assertEqual(config.target_chapter_words, 3000)
        self.assertEqual(config.target_paragraph_words, 300)
        self.assertIsInstance(config.continuous_themes, list)
        self.assertIsInstance(config.must_include_elements, list)
        self.assertIsInstance(config.avoid_elements, list)
    
    def test_stage_specific_config(self):
        """測試 StageSpecificConfig"""
        config = StageSpecificConfig(
            additional_prompt="特別指示",
            creativity_level=0.8,
            detail_level="詳細"
        )
        
        self.assertEqual(config.additional_prompt, "特別指示")
        self.assertEqual(config.creativity_level, 0.8)
        self.assertEqual(config.detail_level, "詳細")
        self.assertIsInstance(config.focus_aspects, list)
    
    def test_novel_project_creation(self):
        """測試 NovelProject 創建"""
        project = NovelProject()
        
        # 測試預設值和自動初始化
        self.assertEqual(project.title, "")
        self.assertEqual(project.theme, "")
        self.assertEqual(project.outline, "")
        self.assertIsInstance(project.chapters, list)
        self.assertIsInstance(project.world_building, WorldBuilding)
        self.assertIsInstance(project.api_config, APIConfig)
        self.assertIsInstance(project.global_config, GlobalWritingConfig)
    
    def test_novel_project_with_data(self):
        """測試包含數據的 NovelProject"""
        chapter1 = Chapter(title="第一章", summary="開始")
        chapter2 = Chapter(title="第二章", summary="發展")
        
        project = NovelProject(
            title="測試小說",
            theme="冒險",
            outline="這是一個關於冒險的故事..."
        )
        project.chapters = [chapter1, chapter2]
        
        self.assertEqual(project.title, "測試小說")
        self.assertEqual(project.theme, "冒險")
        self.assertEqual(len(project.chapters), 2)
        self.assertEqual(project.chapters[0].title, "第一章")
    
    def test_serialization_roundtrip(self):
        """測試序列化往返"""
        # 創建複雜的專案
        paragraph = Paragraph(order=1, purpose="測試段落", content="測試內容")
        chapter = Chapter(title="測試章節", summary="測試摘要")
        chapter.paragraphs = [paragraph]
        
        project = NovelProject(title="測試專案", theme="測試主題")
        project.chapters = [chapter]
        
        # 序列化
        data = asdict(project)
        self.assertIsInstance(data, dict)
        self.assertEqual(data['title'], "測試專案")
        self.assertEqual(len(data['chapters']), 1)
        self.assertEqual(data['chapters'][0]['title'], "測試章節")
        self.assertEqual(len(data['chapters'][0]['paragraphs']), 1)


if __name__ == '__main__':
    unittest.main()