"""
測試 models.enums 模組
"""

import unittest
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.models.enums import TaskType, CreationStatus, WritingStyle, PacingStyle


class TestEnums(unittest.TestCase):
    """測試枚舉類型"""
    
    def test_task_type_enum(self):
        """測試 TaskType 枚舉"""
        # 測試所有值存在
        self.assertEqual(TaskType.OUTLINE.value, "outline")
        self.assertEqual(TaskType.CHAPTERS.value, "chapters") 
        self.assertEqual(TaskType.CHAPTER_OUTLINE.value, "chapter_outline")
        self.assertEqual(TaskType.PARAGRAPHS.value, "paragraphs")
        self.assertEqual(TaskType.WRITING.value, "writing")
        self.assertEqual(TaskType.WORLD_BUILDING.value, "world_building")
        
        # 測試枚舉可以比較
        self.assertNotEqual(TaskType.OUTLINE, TaskType.WRITING)
        self.assertEqual(TaskType.OUTLINE, TaskType.OUTLINE)
    
    def test_creation_status_enum(self):
        """測試 CreationStatus 枚舉"""
        # 測試所有狀態
        self.assertEqual(CreationStatus.NOT_STARTED.value, "未開始")
        self.assertEqual(CreationStatus.IN_PROGRESS.value, "進行中")
        self.assertEqual(CreationStatus.COMPLETED.value, "已完成")
        self.assertEqual(CreationStatus.ERROR.value, "錯誤")
        
        # 測試狀態轉換邏輯
        self.assertNotEqual(CreationStatus.NOT_STARTED, CreationStatus.COMPLETED)
    
    def test_writing_style_enum(self):
        """測試 WritingStyle 枚舉"""
        styles = [
            WritingStyle.FIRST_PERSON,
            WritingStyle.THIRD_PERSON_LIMITED,
            WritingStyle.THIRD_PERSON_OMNISCIENT,
            WritingStyle.MULTIPLE_POV
        ]
        
        # 確保所有風格都有中文值
        for style in styles:
            self.assertIsInstance(style.value, str)
            self.assertTrue(len(style.value) > 0)
    
    def test_pacing_style_enum(self):
        """測試 PacingStyle 枚舉"""
        pacing_styles = [
            PacingStyle.SLOW_BURN,
            PacingStyle.FAST_PACED,
            PacingStyle.BALANCED,
            PacingStyle.EPISODIC
        ]
        
        # 確保所有節奏都有中文值
        for pacing in pacing_styles:
            self.assertIsInstance(pacing.value, str)
            self.assertTrue(len(pacing.value) > 0)
    
    def test_enum_membership(self):
        """測試枚舉成員檢查"""
        # 測試值是否在枚舉中
        self.assertIn(TaskType.OUTLINE, TaskType)
        self.assertIn(CreationStatus.COMPLETED, CreationStatus)
        
        # 測試無效值
        with self.assertRaises(ValueError):
            CreationStatus("invalid_status")


if __name__ == '__main__':
    unittest.main()