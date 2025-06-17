"""
測試 services.llm_service 模組
"""

import unittest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.services.llm_service import LLMService
from novel_writer.models import TaskType, JSONParseException


class TestLLMService(unittest.TestCase):
    """測試LLM服務"""
    
    def setUp(self):
        """設置測試環境"""
        self.api_connector = Mock()
        self.debug_callback = Mock()
        self.llm_service = LLMService(self.api_connector, self.debug_callback)
    
    def test_initialization(self):
        """測試初始化"""
        self.assertEqual(self.llm_service.api_connector, self.api_connector)
        self.assertEqual(self.llm_service.debug_callback, self.debug_callback)
    
    def test_initialization_without_callback(self):
        """測試無回調函數的初始化"""
        service = LLMService(self.api_connector)
        self.assertIsNotNone(service.debug_callback)
        # 呼叫不應該拋出錯誤
        service.debug_callback("test message")
    
    def test_successful_json_response(self):
        """測試成功的JSON響應"""
        # 模擬API響應
        json_response = {
            "title": "測試標題",
            "content": "測試內容",
            "chapters": ["第一章", "第二章"]
        }
        
        self.api_connector.call_api.return_value = {
            "content": f"```json\n{json.dumps(json_response, ensure_ascii=False)}\n```",
            "usage": {"total_tokens": 100}
        }
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="生成小說大綱",
            task_type=TaskType.OUTLINE
        )
        
        # 檢查結果
        self.assertEqual(result["success"], True)
        self.assertEqual(result["data"], json_response)
        self.assertEqual(result["usage"]["total_tokens"], 100)
        self.assertIn("thinking", result)
    
    def test_json_with_thinking_content(self):
        """測試包含思考內容的響應"""
        json_response = {"title": "測試"}
        api_response = f"""
        <thinking>
        我需要生成一個小說大綱...
        考慮故事結構...
        </thinking>
        
        根據您的要求，我生成了以下大綱：
        
        ```json
        {json.dumps(json_response, ensure_ascii=False)}
        ```
        """
        
        self.api_connector.call_api.return_value = {
            "content": api_response,
            "usage": {"total_tokens": 150}
        }
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="生成大綱",
            task_type=TaskType.OUTLINE
        )
        
        # 檢查思考內容被提取
        self.assertIn("我需要生成一個小說大綱", result["thinking"])
        self.assertIn("考慮故事結構", result["thinking"])
        self.assertEqual(result["data"], json_response)
    
    def test_json_parse_retry(self):
        """測試JSON解析重試機制"""
        # 第一次返回無效JSON，第二次返回有效JSON
        invalid_response = "這不是有效的JSON格式"
        valid_json = {"title": "修正後的標題"}
        valid_response = f"```json\n{json.dumps(valid_json, ensure_ascii=False)}\n```"
        
        self.api_connector.call_api.side_effect = [
            {"content": invalid_response, "usage": {"total_tokens": 50}},
            {"content": valid_response, "usage": {"total_tokens": 80}}
        ]
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="生成內容",
            task_type=TaskType.WRITING
        )
        
        # 檢查重試成功
        self.assertEqual(result["success"], True)
        self.assertEqual(result["data"], valid_json)
        self.assertEqual(self.api_connector.call_api.call_count, 2)
        
        # 檢查debug回調被調用
        self.assertTrue(self.debug_callback.called)
    
    def test_max_retries_exceeded(self):
        """測試超過最大重試次數"""
        # 所有嘗試都返回無效JSON
        invalid_response = "無效內容"
        self.api_connector.call_api.return_value = {
            "content": invalid_response,
            "usage": {"total_tokens": 30}
        }
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="生成內容",
            task_type=TaskType.WRITING
        )
        
        # 檢查失敗結果
        self.assertEqual(result["success"], False)
        self.assertIn("error", result)
        self.assertIsInstance(result["error"], JSONParseException)
        
        # 檢查重試了3次
        self.assertEqual(self.api_connector.call_api.call_count, 3)
    
    def test_different_thinking_formats(self):
        """測試不同的思考內容格式"""
        test_cases = [
            # 標準格式
            {
                "content": "<thinking>標準思考</thinking>\n結果",
                "expected": "標準思考"
            },
            # 帶換行的格式
            {
                "content": "<thinking>\n多行\n思考內容\n</thinking>\n結果",
                "expected": "多行\n思考內容"
            },
            # 無思考標籤
            {
                "content": "直接結果內容",
                "expected": ""
            },
            # 不完整的標籤
            {
                "content": "<thinking>未閉合的思考\n結果",
                "expected": "未閉合的思考\n結果"
            }
        ]
        
        for case in test_cases:
            with self.subTest(content=case["content"][:20]):
                extracted = self.llm_service._extract_thinking_content(case["content"])
                self.assertEqual(extracted.strip(), case["expected"].strip())
    
    def test_json_enhancement(self):
        """測試JSON提示詞增強"""
        original_prompt = "生成一個故事大綱"
        enhanced = self.llm_service._enhance_json_prompt(original_prompt)
        
        # 檢查增強內容
        self.assertIn("JSON", enhanced)
        self.assertIn("```json", enhanced)
        self.assertIn(original_prompt, enhanced)
        self.assertIn("格式", enhanced)
    
    def test_use_planning_model(self):
        """測試使用規劃模型"""
        json_response = {"plan": "規劃內容"}
        self.api_connector.call_api.return_value = {
            "content": f"```json\n{json.dumps(json_response, ensure_ascii=False)}\n```",
            "usage": {"total_tokens": 120}
        }
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="生成規劃",
            task_type=TaskType.OUTLINE,
            use_planning_model=True
        )
        
        # 檢查API調用參數
        call_args = self.api_connector.call_api.call_args
        self.assertTrue(call_args.kwargs.get("use_planning_model", False))
        
        self.assertEqual(result["success"], True)
        self.assertEqual(result["data"], json_response)
    
    def test_custom_parameters(self):
        """測試自定義參數"""
        json_response = {"result": "自定義結果"}
        self.api_connector.call_api.return_value = {
            "content": f"```json\n{json.dumps(json_response, ensure_ascii=False)}\n```",
            "usage": {"total_tokens": 200}
        }
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="自定義請求",
            task_type=TaskType.WRITING,
            max_tokens=4000,
            temperature=0.8
        )
        
        # 檢查API調用參數
        call_args = self.api_connector.call_api.call_args
        self.assertEqual(call_args.kwargs.get("max_tokens"), 4000)
        self.assertEqual(call_args.kwargs.get("temperature"), 0.8)
        
        self.assertEqual(result["success"], True)
        self.assertEqual(result["data"], json_response)
    
    def test_api_exception_handling(self):
        """測試API例外處理"""
        from novel_writer.models import APIException
        
        # 模擬API例外
        self.api_connector.call_api.side_effect = APIException("API調用失敗")
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="測試",
            task_type=TaskType.WRITING
        )
        
        # 檢查例外被正確處理
        self.assertEqual(result["success"], False)
        self.assertIsInstance(result["error"], APIException)
        self.assertIn("API調用失敗", str(result["error"]))
    
    def test_complex_json_extraction(self):
        """測試複雜JSON提取"""
        # 包含多個JSON塊的響應
        complex_response = """
        這是一些說明文字。
        
        ```json
        {"type": "outline", "title": "主要大綱"}
        ```
        
        還有更多說明。
        
        ```json
        {"type": "detail", "content": "詳細內容"}
        ```
        
        最後的總結。
        """
        
        self.api_connector.call_api.return_value = {
            "content": complex_response,
            "usage": {"total_tokens": 180}
        }
        
        result = self.llm_service.call_llm_with_thinking(
            prompt="生成複雜內容",
            task_type=TaskType.OUTLINE
        )
        
        # 應該提取第一個有效的JSON
        self.assertEqual(result["success"], True)
        self.assertEqual(result["data"]["type"], "outline")
        self.assertEqual(result["data"]["title"], "主要大綱")


if __name__ == '__main__':
    unittest.main()