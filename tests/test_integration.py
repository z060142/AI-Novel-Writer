"""
整合測試 - 測試各模組之間的協作
"""

import unittest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from novel_writer.models import NovelProject, APIConfig, Chapter, Paragraph, CreationStatus, TaskType
from novel_writer.services import APIConnector, LLMService, TextFormatter
from novel_writer.core import NovelWriterCore, JSONParser, PromptManager
from novel_writer.utils import safe_execute


class TestIntegration(unittest.TestCase):
    """整合測試類"""
    
    def setUp(self):
        """設置測試環境"""
        # 創建測試項目
        self.project = NovelProject()
        self.project.title = "整合測試小說"
        self.project.theme = "測試主題"
        self.project.outline = "這是整合測試的大綱..."
        
        # 創建API配置
        self.api_config = APIConfig(
            api_key="test-key",
            base_url="https://api.test.com/v1",
            model="test-model"
        )
        
        # 創建模擬的服務
        self.debug_callback = Mock()
        self.api_connector = Mock(spec=APIConnector)
        self.llm_service = Mock(spec=LLMService)
        
    def test_project_serialization_roundtrip(self):
        """測試項目序列化往返"""
        # 創建複雜的項目數據
        chapter = Chapter(title="測試章節", summary="測試摘要")
        paragraph = Paragraph(order=1, purpose="測試段落", content="測試內容")
        chapter.paragraphs = [paragraph]
        self.project.chapters = [chapter]
        
        # 序列化
        from dataclasses import asdict
        project_data = asdict(self.project)
        
        # 檢查數據完整性
        self.assertEqual(project_data["title"], "整合測試小說")
        self.assertEqual(len(project_data["chapters"]), 1)
        self.assertEqual(project_data["chapters"][0]["title"], "測試章節")
        self.assertEqual(len(project_data["chapters"][0]["paragraphs"]), 1)
        
        # 反序列化（模擬載入項目的過程）
        new_project = NovelProject()
        new_project.title = project_data["title"]
        new_project.theme = project_data["theme"]
        new_project.outline = project_data["outline"]
        
        # 重建章節
        for chapter_data in project_data["chapters"]:
            new_chapter = Chapter(
                title=chapter_data["title"],
                summary=chapter_data["summary"]
            )
            for para_data in chapter_data["paragraphs"]:
                new_paragraph = Paragraph(
                    order=para_data["order"],
                    purpose=para_data["purpose"],
                    content=para_data["content"]
                )
                new_chapter.paragraphs.append(new_paragraph)
            new_project.chapters.append(new_chapter)
        
        # 驗證重建的項目
        self.assertEqual(new_project.title, self.project.title)
        self.assertEqual(len(new_project.chapters), 1)
        self.assertEqual(new_project.chapters[0].title, "測試章節")
        self.assertEqual(len(new_project.chapters[0].paragraphs), 1)
        self.assertEqual(new_project.chapters[0].paragraphs[0].content, "測試內容")
    
    def test_api_connector_and_llm_service_integration(self):
        """測試API連接器和LLM服務的整合"""
        # 創建真實的API連接器和LLM服務
        real_api_connector = APIConnector(self.api_config, self.debug_callback)
        real_llm_service = LLMService(real_api_connector, self.debug_callback)
        
        # 模擬API響應
        mock_api_response = {
            "content": '''```json
            {
                "title": "測試大綱",
                "chapters": ["第一章", "第二章"],
                "theme": "測試主題"
            }
            ```''',
            "usage": {"total_tokens": 100}
        }
        
        with patch.object(real_api_connector, 'call_api', return_value=mock_api_response):
            result = real_llm_service.call_llm_with_thinking(
                prompt="生成測試大綱",
                task_type=TaskType.OUTLINE
            )
            
            # 檢查結果
            self.assertTrue(result["success"])
            self.assertEqual(result["data"]["title"], "測試大綱")
            self.assertEqual(len(result["data"]["chapters"]), 2)
            self.assertIn("thinking", result)
    
    def test_prompt_builder_integration(self):
        """測試提示詞建構器整合"""
        from novel_writer.core.prompt_builder import DynamicPromptBuilder
        
        # 創建章節和段落
        chapter = Chapter(title="第一章：開始", summary="故事的開始")
        paragraph = Paragraph(order=1, purpose="場景描述", estimated_words=300)
        
        # 創建提示詞建構器
        builder = DynamicPromptBuilder(self.project)
        
        # 生成不同類型的提示詞
        outline_prompt = builder.build_outline_prompt("請包含冒險元素")
        chapter_prompt = builder.build_chapter_division_prompt("每章3000字")
        writing_prompt = builder.build_paragraph_writing_prompt(
            chapter=chapter,
            paragraph=paragraph,
            chapter_index=0,
            paragraph_index=0
        )
        
        # 檢查提示詞內容
        self.assertIn(self.project.title, outline_prompt)
        self.assertIn("冒險元素", outline_prompt)
        self.assertIn("3000字", chapter_prompt)
        self.assertIn("場景描述", writing_prompt)
        self.assertIn("第一章：開始", writing_prompt)
    
    def test_text_formatter_integration(self):
        """測試文字格式化器整合"""
        # 測試不同格式的文本
        test_texts = [
            '角色說："你好世界！"這是一個測試。',
            '這是第一句。這是第二句！還有問句嗎？',
            '「中文引號測試。」他說道。',
            '段落一。\n\n\n\n段落二。\n\n段落三。'
        ]
        
        for text in test_texts:
            # 測試繁體引號格式化
            traditional_result = TextFormatter.format_novel_content(text, use_traditional_quotes=True)
            self.assertIsInstance(traditional_result, str)
            
            # 測試英文引號格式化  
            english_result = TextFormatter.format_novel_content(text, use_traditional_quotes=False)
            self.assertIsInstance(english_result, str)
            
            # 檢查格式化結果不為空
            self.assertGreater(len(traditional_result.strip()), 0)
            self.assertGreater(len(english_result.strip()), 0)
    
    def test_json_parser_integration(self):
        """測試JSON解析器整合"""
        # 測試不同格式的JSON內容
        test_contents = [
            '```json\n{"title": "測試", "content": "內容"}\n```',
            '這裡有JSON：{"name": "測試名稱", "value": 42}結束',
            '''<thinking>思考中...</thinking>
            
            ```json
            {
                "章節": ["第一章", "第二章"],
                "主題": "冒險"
            }
            ```''',
            '```\n{"result": "success", "data": ["項目1", "項目2"]}\n```'
        ]
        
        for content in test_contents:
            result = JSONParser.extract_json_from_content(content)
            self.assertIsNotNone(result, f"Failed to parse: {content[:50]}...")
            self.assertIsInstance(result, dict)
    
    def test_safe_execute_decorator_integration(self):
        """測試safe_execute裝飾器整合"""
        # 創建測試類
        class TestObject:
            def __init__(self):
                self.show_error = Mock()
            
            @safe_execute
            def successful_method(self):
                return "成功"
            
            @safe_execute
            def failing_method(self):
                raise ValueError("測試錯誤")
        
        test_obj = TestObject()
        
        # 測試成功情況
        result = test_obj.successful_method()
        self.assertEqual(result, "成功")
        test_obj.show_error.assert_not_called()
        
        # 測試失敗情況
        with self.assertRaises(ValueError):
            test_obj.failing_method()
        test_obj.show_error.assert_called_once()
    
    def test_full_workflow_simulation(self):
        """測試完整工作流程模擬"""
        # 模擬完整的小說生成流程
        
        # 1. 創建項目
        project = NovelProject()
        project.title = "模擬小說"
        project.theme = "科幻"
        
        # 2. 創建服務（使用Mock）
        api_connector = Mock()
        llm_service = Mock()
        
        # 3. 模擬大綱生成
        outline_response = {
            "success": True,
            "data": {
                "outline": "這是生成的大綱...",
                "main_characters": ["主角", "配角"],
                "plot_points": ["開始", "發展", "高潮", "結局"]
            },
            "thinking": "思考過程...",
            "usage": {"total_tokens": 200}
        }
        llm_service.call_llm_with_thinking.return_value = outline_response
        
        # 4. 創建核心邏輯
        core = NovelWriterCore(project, llm_service, self.debug_callback)
        
        # 5. 模擬生成大綱
        result = core.generate_outline("請生成科幻大綱")
        
        # 檢查結果（由於使用Mock，這裡主要測試調用是否正確）
        llm_service.call_llm_with_thinking.assert_called()
        call_args = llm_service.call_llm_with_thinking.call_args
        self.assertEqual(call_args.kwargs["task_type"], TaskType.OUTLINE)
        
        # 6. 模擬章節劃分
        chapters_response = {
            "success": True,
            "data": {
                "chapters": [
                    {"title": "第一章", "summary": "開始"},
                    {"title": "第二章", "summary": "發展"}
                ]
            }
        }
        llm_service.call_llm_with_thinking.return_value = chapters_response
        
        chapters_result = core.divide_chapters("每章3000字")
        
        # 檢查章節劃分調用
        self.assertEqual(llm_service.call_llm_with_thinking.call_count, 2)
    
    def test_load_sample_project(self):
        """測試載入範例項目"""
        # 載入範例項目文件
        sample_file = os.path.join(os.path.dirname(__file__), 'data', 'simple_project.json')
        
        with open(sample_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # 檢查數據完整性
        self.assertEqual(project_data["title"], "簡單測試小說")
        self.assertEqual(project_data["theme"], "測試主題")
        self.assertIn("chapters", project_data)
        self.assertIn("world_building", project_data)
        self.assertIn("api_config", project_data)
        
        # 測試重建項目對象
        project = NovelProject()
        project.title = project_data["title"]
        project.theme = project_data["theme"]
        project.outline = project_data["outline"]
        
        # 重建章節
        for chapter_data in project_data["chapters"]:
            chapter = Chapter(
                title=chapter_data["title"],
                summary=chapter_data["summary"],
                key_events=chapter_data.get("key_events", []),
                characters_involved=chapter_data.get("characters_involved", [])
            )
            
            # 重建段落
            for para_data in chapter_data.get("paragraphs", []):
                paragraph = Paragraph(
                    order=para_data["order"],
                    purpose=para_data["purpose"],
                    content=para_data.get("content", ""),
                    status=CreationStatus(para_data.get("status", "未開始"))
                )
                chapter.paragraphs.append(paragraph)
            
            project.chapters.append(chapter)
        
        # 驗證重建的項目
        self.assertEqual(project.title, "簡單測試小說")
        self.assertEqual(len(project.chapters), 1)
        self.assertEqual(project.chapters[0].title, "第一章：開始")
        self.assertEqual(len(project.chapters[0].paragraphs), 1)
        self.assertEqual(project.chapters[0].paragraphs[0].order, 1)
    
    def test_error_handling_across_modules(self):
        """測試跨模組的錯誤處理"""
        # 測試各種錯誤情況
        
        # 1. JSON解析錯誤
        invalid_json = "這不是有效的JSON"
        result = JSONParser.extract_json_from_content(invalid_json)
        self.assertIsNone(result)
        
        # 2. API連接器錯誤處理
        with patch('novel_writer.services.api_connector.requests.post') as mock_post:
            mock_post.side_effect = Exception("網絡錯誤")
            
            api_connector = APIConnector(self.api_config)
            
            with self.assertRaises(Exception):
                api_connector.call_api([{"role": "user", "content": "測試"}])
        
        # 3. 提示詞管理器對無效任務類型的處理
        # 這裡測試系統對邊界情況的處理能力
        for task_type in TaskType:
            prompt = PromptManager.create_system_prompt(task_type)
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 0)
    
    def test_performance_considerations(self):
        """測試性能相關考慮"""
        # 測試大量數據的處理
        
        # 1. 創建大型項目數據
        large_project = NovelProject()
        large_project.title = "大型測試項目"
        
        # 創建多個章節
        for i in range(10):
            chapter = Chapter(title=f"第{i+1}章", summary=f"第{i+1}章摘要")
            
            # 每章創建多個段落
            for j in range(10):
                paragraph = Paragraph(
                    order=j+1,
                    purpose=f"段落{j+1}目的",
                    content=f"這是第{j+1}段的內容..." * 10  # 較長的內容
                )
                chapter.paragraphs.append(paragraph)
            
            large_project.chapters.append(chapter)
        
        # 2. 測試序列化性能
        from dataclasses import asdict
        import time
        
        start_time = time.time()
        project_data = asdict(large_project)
        serialization_time = time.time() - start_time
        
        # 檢查序列化在合理時間內完成（1秒內）
        self.assertLess(serialization_time, 1.0)
        
        # 3. 測試數據完整性
        self.assertEqual(len(project_data["chapters"]), 10)
        self.assertEqual(len(project_data["chapters"][0]["paragraphs"]), 10)
        
        # 4. 測試文字格式化性能
        long_text = "這是一個很長的文本測試。" * 1000
        
        start_time = time.time()
        formatted_text = TextFormatter.format_novel_content(long_text)
        formatting_time = time.time() - start_time
        
        # 檢查格式化在合理時間內完成
        self.assertLess(formatting_time, 1.0)
        self.assertIsInstance(formatted_text, str)


if __name__ == '__main__':
    # 設置詳細的測試輸出
    unittest.main(verbosity=2)