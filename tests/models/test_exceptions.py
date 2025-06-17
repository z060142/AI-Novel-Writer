"""
測試 models.exceptions 模組
"""

import unittest
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from novel_writer.models.exceptions import APIException, JSONParseException


class TestExceptions(unittest.TestCase):
    """測試例外類型"""
    
    def test_api_exception(self):
        """測試 APIException"""
        # 測試基本創建
        exc = APIException("API調用失敗")
        self.assertIsInstance(exc, Exception)
        self.assertEqual(str(exc), "API調用失敗")
        
        # 測試拋出和捕獲
        with self.assertRaises(APIException) as context:
            raise APIException("測試錯誤訊息")
        
        self.assertEqual(str(context.exception), "測試錯誤訊息")
    
    def test_json_parse_exception(self):
        """測試 JSONParseException"""
        # 測試基本創建
        exc = JSONParseException("JSON解析失敗")
        self.assertIsInstance(exc, Exception)
        self.assertEqual(str(exc), "JSON解析失敗")
        
        # 測試拋出和捕獲
        with self.assertRaises(JSONParseException) as context:
            raise JSONParseException("無效的JSON格式")
        
        self.assertEqual(str(context.exception), "無效的JSON格式")
    
    def test_exception_inheritance(self):
        """測試例外繼承關係"""
        # 確保都是Exception的子類
        self.assertTrue(issubclass(APIException, Exception))
        self.assertTrue(issubclass(JSONParseException, Exception))
        
        # 測試isinstance檢查
        api_exc = APIException("API錯誤")
        json_exc = JSONParseException("JSON錯誤")
        
        self.assertIsInstance(api_exc, Exception)
        self.assertIsInstance(json_exc, Exception)
        self.assertIsInstance(api_exc, APIException)
        self.assertIsInstance(json_exc, JSONParseException)
        
        # 確保不會混淆
        self.assertNotIsInstance(api_exc, JSONParseException)
        self.assertNotIsInstance(json_exc, APIException)


if __name__ == '__main__':
    unittest.main()