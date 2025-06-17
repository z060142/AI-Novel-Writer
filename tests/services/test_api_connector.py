"""
測試 services.api_connector 模組
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.services.api_connector import APIConnector
from novel_writer.models import APIConfig, APIException


class TestAPIConnector(unittest.TestCase):
    """測試API連接器"""
    
    def setUp(self):
        """設置測試環境"""
        self.config = APIConfig(
            api_key="test-key",
            base_url="https://api.test.com/v1",
            model="test-model",
            provider="openai"
        )
        self.debug_callback = Mock()
        self.connector = APIConnector(self.config, self.debug_callback)
    
    def test_initialization(self):
        """測試初始化"""
        self.assertEqual(self.connector.config, self.config)
        self.assertEqual(self.connector.debug_callback, self.debug_callback)
    
    def test_initialization_without_callback(self):
        """測試無回調函數的初始化"""
        connector = APIConnector(self.config)
        # 應該有預設的空回調函數
        self.assertIsNotNone(connector.debug_callback)
        # 呼叫不應該拋出錯誤
        connector.debug_callback("test message")
    
    @patch('novel_writer.services.api_connector.requests.post')
    def test_openai_api_success(self, mock_post):
        """測試OpenAI API成功調用"""
        # 模擬成功響應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "測試回應"}
            }],
            "usage": {"total_tokens": 100},
            "model": "test-model"
        }
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "測試訊息"}]
        result = self.connector.call_api(messages)
        
        # 檢查結果
        self.assertEqual(result["content"], "測試回應")
        self.assertEqual(result["usage"]["total_tokens"], 100)
        self.assertEqual(result["model"], "test-model")
        
        # 檢查API調用參數
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("json", call_args.kwargs)
        self.assertEqual(call_args.kwargs["json"]["model"], "test-model")
        self.assertEqual(call_args.kwargs["json"]["messages"], messages)
    
    @patch('novel_writer.services.api_connector.requests.post')
    def test_openai_api_with_thinking_disabled(self, mock_post):
        """測試禁用thinking的OpenAI API調用"""
        # 設置禁用thinking
        self.config.disable_thinking = True
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "回應"}}],
            "usage": {},
            "model": "test-model"
        }
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "測試"}]
        self.connector.call_api(messages)
        
        # 檢查thinking參數被添加
        call_args = mock_post.call_args
        self.assertFalse(call_args.kwargs["json"]["thinking"])
    
    @patch('novel_writer.services.api_connector.requests.post')
    def test_api_error_response(self, mock_post):
        """測試API錯誤響應"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "測試"}]
        
        with self.assertRaises(APIException) as context:
            self.connector.call_api(messages)
        
        self.assertIn("400", str(context.exception))
        self.assertIn("Bad Request", str(context.exception))
    
    @patch('novel_writer.services.api_connector.requests.post')
    def test_retry_logic(self, mock_post):
        """測試重試邏輯"""
        # 設置重試次數
        self.config.max_retries = 2
        
        # 模擬連接錯誤
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("連接失敗")
        
        messages = [{"role": "user", "content": "測試"}]
        
        with self.assertRaises(APIException) as context:
            self.connector.call_api(messages)
        
        # 檢查重試了指定次數
        self.assertEqual(mock_post.call_count, 2)
        self.assertIn("已重試 2 次", str(context.exception))
    
    @patch('novel_writer.services.api_connector.requests.post')
    def test_planning_model_usage(self, mock_post):
        """測試規劃模型使用"""
        # 啟用規劃模型
        self.config.use_planning_model = True
        self.config.planning_model = "planning-model"
        self.config.planning_api_key = "planning-key"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "規劃回應"}}],
            "usage": {},
            "model": "planning-model"
        }
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "規劃請求"}]
        result = self.connector.call_api(messages, use_planning_model=True)
        
        # 檢查使用了規劃模型
        self.assertEqual(result["content"], "規劃回應")
        call_args = mock_post.call_args
        self.assertEqual(call_args.kwargs["json"]["model"], "planning-model")
        
        # 檢查debug回調被調用
        self.debug_callback.assert_called()
        debug_calls = [call.args[0] for call in self.debug_callback.call_args_list]
        self.assertTrue(any("規劃模型" in call for call in debug_calls))
    
    def test_unsupported_provider(self):
        """測試不支持的提供商"""
        self.config.provider = "unsupported"
        
        messages = [{"role": "user", "content": "測試"}]
        
        with self.assertRaises(APIException) as context:
            self.connector.call_api(messages)
        
        self.assertIn("不支持的API提供商", str(context.exception))
    
    @patch('novel_writer.services.api_connector.requests.post')
    def test_anthropic_api_call(self, mock_post):
        """測試Anthropic API調用"""
        self.config.provider = "anthropic"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Anthropic回應"}],
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }
        mock_post.return_value = mock_response
        
        messages = [
            {"role": "system", "content": "系統提示"},
            {"role": "user", "content": "用戶訊息"}
        ]
        
        result = self.connector.call_api(messages)
        
        # 檢查結果
        self.assertEqual(result["content"], "Anthropic回應")
        
        # 檢查API調用格式
        call_args = mock_post.call_args
        json_data = call_args.kwargs["json"]
        
        # Anthropic格式應該分離system和messages
        self.assertIn("system", json_data)
        self.assertEqual(json_data["system"], "系統提示")
        self.assertEqual(len(json_data["messages"]), 1)
        self.assertEqual(json_data["messages"][0]["content"], "用戶訊息")
    
    @patch('novel_writer.services.api_connector.requests.post')
    def test_custom_api_call(self, mock_post):
        """測試自定義API調用"""
        self.config.provider = "custom"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "自定義回應"}}],
            "usage": {}
        }
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "測試"}]
        result = self.connector.call_api(messages)
        
        self.assertEqual(result["content"], "自定義回應")
    
    def test_timeout_configuration(self):
        """測試超時配置"""
        self.config.timeout = 30
        
        with patch('novel_writer.services.api_connector.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "回應"}}],
                "usage": {}
            }
            mock_post.return_value = mock_response
            
            messages = [{"role": "user", "content": "測試"}]
            self.connector.call_api(messages)
            
            # 檢查timeout參數
            call_args = mock_post.call_args
            self.assertEqual(call_args.kwargs["timeout"], 30)


if __name__ == '__main__':
    unittest.main()